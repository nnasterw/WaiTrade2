#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from yaml_to_set import FLAT_MAP, TRAIL_MAP, format_value


DEFAULT_SCHEDULE_CONFIG = ROOT / "config" / "portfolio_schedules.yaml"
DEFAULT_STRATEGY_CONFIG = ROOT / "config" / "strategies.yaml"
DEFAULT_OUTPUT_ROOT = ROOT / "temp" / "portfolio_profiles"
EA_NAME = "WaiTrade2\\WaiTrade_OB"
SHARED_GUARD_KEYS = {
    "shared_monthly_guard",
    "shared_monthly_guard_key",
    "shared_monthly_guard_debug",
}


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing config: {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def safe_name(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("_")


def resolve_schedule(config_path: Path, schedule_name: str) -> dict:
    data = load_yaml(config_path)
    schedules = data.get("schedules") or {}
    if schedule_name not in schedules:
        raise SystemExit(f"unknown schedule: {schedule_name}")
    return schedules[schedule_name]


def merge_stream_config(stream: dict, schedule: dict, strategies: dict) -> dict:
    strategy_name = stream.get("strategy")
    if not strategy_name:
        raise SystemExit(f"stream {stream.get('name', '')} has no strategy")
    if strategy_name not in strategies:
        raise SystemExit(f"strategy not found: {strategy_name}")

    cfg = dict(strategies[strategy_name])
    guard_overrides = schedule.get("live_profile", {}).get("guard_overrides") or {}
    mode = stream.get("guard_override_mode", "all")
    if mode == "all":
        cfg.update(guard_overrides)
    elif mode == "shared_only":
        cfg.update({key: value for key, value in guard_overrides.items() if key in SHARED_GUARD_KEYS})
    else:
        raise SystemExit(f"unknown guard_override_mode for stream {stream.get('name', '')}: {mode}")
    cfg.update(stream.get("overrides") or {})
    cfg["version"] = stream.get("version") or f"{cfg.get('version', strategy_name)}-{stream.get('name', strategy_name)}"
    return cfg


def apply_no_entry_month(cfg: dict, month: int | None) -> dict:
    if month is None:
        return cfg
    if month < 1 or month > 12:
        raise SystemExit(f"no-entry month must be 1..12: {month}")
    cfg = dict(cfg)
    cfg["entry_months"] = str(month)
    return cfg


def apply_guard_key_suffix(cfg: dict, suffix: str) -> dict:
    if not suffix or not cfg.get("shared_monthly_guard_key"):
        return cfg
    cfg = dict(cfg)
    cfg["shared_monthly_guard_key"] = f"{cfg['shared_monthly_guard_key']}_{safe_name(suffix)}"
    return cfg


def write_utf16(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-16")


def generate_inputs_block(cfg: dict) -> str:
    lines = []
    for yaml_key, inp_name in FLAT_MAP.items():
        if yaml_key in cfg:
            lines.append(f"{inp_name}={format_value(cfg[yaml_key])}")

    trail_levels = cfg.get("trail_levels", [])
    for idx, level in enumerate(trail_levels):
        if not isinstance(level, dict):
            continue
        for sub_key, val in level.items():
            inp_name = TRAIL_MAP.get((idx, sub_key))
            if inp_name:
                lines.append(f"{inp_name}={format_value(val)}")
    return "\n".join(lines)


def generate_chart_chr(symbol: str, period_size: int, inputs_block: str, chart_id: int) -> str:
    return f"""<chart>
id={chart_id}
symbol={symbol}
period_type=0
period_size={period_size}
digits=2
tick_size=0.000000
position_time=0
scale_fix=0
scale_fixed_min=0.000000
scale_fixed_max=0.000000
scale_fix11=0
scale_bar=0
scale_bar_val=1.000000
scale=16
mode=1
fore=0
grid=1
volume=1
expertmode=1
scroll=1
shift=1
shift_size=20.000000
ohlc=1
one_click=0
bidline=1
askline=1
lastline=0
tradehistory=1
windows_total=1

<window>
height=100.000000
objects=0

<indicator>
name=Main
path=
apply=1
show_data=1
scale_inherit=0
scale_line=0
scale_line_percent=50
scale_line_value=0.000000
scale_fix_min=0
scale_fix_min_val=0.000000
scale_fix_max=0
scale_fix_max_val=0.000000
expertmode=1
fixed_height=-1
</indicator>

<expert>
name={EA_NAME}
path=
flags=339
window_num=0

<inputs>
{inputs_block}
</inputs>
</expert>

</window>
</chart>
"""


def generate_order_wnd(chart_count: int) -> str:
    return "".join(f"chart{i:02d}.chr\n" for i in range(1, chart_count + 1))


def create_profile(
    schedule_name: str,
    schedule_config: Path,
    strategy_config: Path,
    output_dir: Path,
    guard_key_suffix: str = "",
    no_entry_month: int | None = None,
) -> Path:
    schedule = resolve_schedule(schedule_config, schedule_name)
    strategies = load_yaml(strategy_config)
    live_profile = schedule.get("live_profile") or {}
    symbol = live_profile.get("symbol")
    if not symbol:
        raise SystemExit(f"schedule {schedule_name} has no live_profile.symbol")

    streams = schedule.get("series") or []
    if not streams:
        raise SystemExit(f"schedule {schedule_name} has no series")

    profile_dir = output_dir / safe_name(schedule_name)
    if profile_dir.exists():
        for child in profile_dir.iterdir():
            if child.is_file():
                child.unlink()
    profile_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schedule": schedule_name,
        "symbol": symbol,
        "guard_key_suffix": guard_key_suffix,
        "no_entry_month": no_entry_month,
        "charts": [],
        "warning": "Generated profile only. Account-level behavior still requires forward/live validation.",
    }

    for index, stream in enumerate(streams, 1):
        cfg = apply_guard_key_suffix(
            apply_no_entry_month(merge_stream_config(stream, schedule, strategies), no_entry_month),
            guard_key_suffix,
        )
        period_size = int(cfg.get("bar_period_min", 1))
        chart_content = generate_chart_chr(
            symbol,
            period_size,
            generate_inputs_block(cfg),
            chart_id=910000000000000000 + index,
        )
        chart_name = f"chart{index:02d}.chr"
        write_utf16(profile_dir / chart_name, chart_content)
        manifest["charts"].append(
            {
                "chart": chart_name,
                "stream": stream.get("name"),
                "strategy": stream.get("strategy"),
                "symbol": symbol,
                "period_size": period_size,
                "magic_number": cfg.get("magic_number"),
                "version": cfg.get("version"),
                "shared_monthly_guard": cfg.get("shared_monthly_guard"),
                "shared_monthly_guard_key": cfg.get("shared_monthly_guard_key"),
            }
        )

    write_utf16(profile_dir / "order.wnd", generate_order_wnd(len(streams)))
    (profile_dir / "portfolio_manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return profile_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a multi-strategy MT5 live profile from a portfolio schedule.")
    parser.add_argument("--schedule", default="r186_r196_season_guard")
    parser.add_argument("--schedule-config", type=Path, default=DEFAULT_SCHEDULE_CONFIG)
    parser.add_argument("--strategy-config", type=Path, default=DEFAULT_STRATEGY_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--guard-key-suffix",
        default="",
        help="Append a run/session suffix to shared_monthly_guard_key to avoid stale MT5 Global Variables.",
    )
    parser.add_argument(
        "--no-entry-month",
        type=int,
        help="Override all streams with InpEntryMonths=N. Useful for a guarded load-only audit profile.",
    )
    args = parser.parse_args()

    profile_dir = create_profile(
        args.schedule,
        args.schedule_config,
        args.strategy_config,
        args.output_dir,
        args.guard_key_suffix,
        args.no_entry_month,
    )
    print(f"profile_dir={profile_dir}")
    for path in sorted(profile_dir.iterdir()):
        print(path.name)


if __name__ == "__main__":
    main()
