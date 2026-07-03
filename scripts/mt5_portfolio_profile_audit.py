#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from mt5_portfolio_live_profile import (  # noqa: E402
    DEFAULT_SCHEDULE_CONFIG,
    DEFAULT_STRATEGY_CONFIG,
    apply_guard_key_suffix,
    generate_inputs_block,
    load_yaml,
    merge_stream_config,
    resolve_schedule,
)


INPUT_RE = re.compile(r"<inputs>\s*(.*?)\s*</inputs>", re.S)


def read_chr(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-16")
    except UnicodeError:
        return path.read_text(encoding="utf-16-le", errors="replace")


def parse_inputs(content: str) -> dict[str, str]:
    match = INPUT_RE.search(content)
    if not match:
        return {}
    result: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def expected_inputs_for_stream(
    stream: dict,
    schedule: dict,
    strategies: dict,
    suffix: str,
    no_entry_month: int | None = None,
) -> dict[str, str]:
    cfg = merge_stream_config(stream, schedule, strategies)
    if no_entry_month is not None:
        cfg = dict(cfg)
        cfg["entry_months"] = str(no_entry_month)
    cfg = apply_guard_key_suffix(cfg, suffix)
    return parse_inputs(f"<inputs>\n{generate_inputs_block(cfg)}\n</inputs>")


def audit_profile(
    profile_dir: Path,
    schedule_name: str = "",
    schedule_config: Path = DEFAULT_SCHEDULE_CONFIG,
    strategy_config: Path = DEFAULT_STRATEGY_CONFIG,
) -> tuple[list[str], str]:
    errors: list[str] = []
    manifest_path = profile_dir / "portfolio_manifest.yaml"
    if not manifest_path.exists():
        return [f"missing manifest: {manifest_path}"], ""

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    schedule_from_manifest = manifest.get("schedule", "")
    selected_schedule = schedule_name or schedule_from_manifest
    if schedule_name and schedule_from_manifest != schedule_name:
        errors.append(f"manifest schedule {schedule_from_manifest!r} != expected {schedule_name!r}")

    schedule = resolve_schedule(schedule_config, selected_schedule)
    strategies = load_yaml(strategy_config)
    streams = schedule.get("series") or []
    charts = manifest.get("charts") or []
    suffix = manifest.get("guard_key_suffix", "")
    no_entry_month = manifest.get("no_entry_month")

    if len(charts) != len(streams):
        errors.append(f"manifest chart count {len(charts)} != schedule series count {len(streams)}")

    order_path = profile_dir / "order.wnd"
    if not order_path.exists():
        errors.append(f"missing order.wnd: {order_path}")
    else:
        order_text = read_chr(order_path)
        order_charts = [
            line.strip()
            for line in order_text.splitlines()
            if line.strip().lower().endswith(".chr")
        ]
        expected_charts = [f"chart{index:02d}.chr" for index in range(1, len(streams) + 1)]
        if order_charts != expected_charts:
            errors.append("order.wnd chart list does not match schedule")

    seen_magics: set[str] = set()
    seen_versions: set[str] = set()
    seen_keys: set[str] = set()
    lines = ["# MT5 portfolio profile audit", "", f"profile={profile_dir}", f"schedule={selected_schedule}", ""]
    lines.append(
        "| chart | stream | version | magic | shared_key | sweep_months | sweep_no_hours | context_filters | pass |"
    )
    lines.append("|---|---|---|---:|---|---|---|---|---|")

    for index, stream in enumerate(streams, 1):
        chart_name = f"chart{index:02d}.chr"
        chart_path = profile_dir / chart_name
        stream_name = str(stream.get("name", ""))
        chart_errors: list[str] = []
        if not chart_path.exists():
            errors.append(f"missing chart: {chart_path}")
            chart_errors.append("missing")
            actual_inputs: dict[str, str] = {}
        else:
            actual_inputs = parse_inputs(read_chr(chart_path))
            if not actual_inputs:
                chart_errors.append("missing inputs")

        expected = expected_inputs_for_stream(stream, schedule, strategies, suffix, no_entry_month)
        for key, expected_value in expected.items():
            actual_value = actual_inputs.get(key)
            if actual_value != expected_value:
                chart_errors.append(f"{key}: actual={actual_value!r} expected={expected_value!r}")

        version = actual_inputs.get("InpVersion", "")
        magic = actual_inputs.get("InpMagicNumber", "")
        shared_key = actual_inputs.get("InpSharedMonthlyGuardKey", "")
        sweep_months = actual_inputs.get("InpSweepContextMonths", "")
        sweep_no_hours = actual_inputs.get("InpSweepContextNoHours", "")
        context_filters = summarize_context_filters(actual_inputs)
        if magic:
            if magic in seen_magics:
                chart_errors.append(f"duplicate magic {magic}")
            seen_magics.add(magic)
        if version:
            seen_versions.add(version)
        if shared_key:
            seen_keys.add(shared_key)
        if chart_errors:
            errors.extend(f"{chart_name} {item}" for item in chart_errors)
        lines.append(
            f"| {chart_name} | {stream_name} | {version} | {magic} | {shared_key} | "
            f"{sweep_months} | {sweep_no_hours} | {context_filters} | {str(not chart_errors).lower()} |"
        )

    if len(seen_keys) > 1:
        errors.append(f"multiple shared guard keys found: {sorted(seen_keys)}")

    lines.append("")
    lines.append(f"charts={len(streams)} versions={len(seen_versions)} unique_magics={len(seen_magics)} pass={str(not errors).lower()}")
    if errors:
        lines.append("")
        lines.append("## Errors")
        for error in errors:
            lines.append(f"- {error}")
    return errors, "\n".join(lines) + "\n"


def summarize_context_filters(inputs: dict[str, str]) -> str:
    parts: list[str] = []
    for slot in (1, 2, 3, 4, 5):
        months = inputs.get(f"InpContextFilter{slot}Months", "")
        mult = inputs.get(f"InpContextFilter{slot}Mult", "1.0")
        no_hours = inputs.get(f"InpContextFilter{slot}NoHours", "")
        no_buy = inputs.get(f"InpContextFilter{slot}NoBuyHours", "")
        no_sell = inputs.get(f"InpContextFilter{slot}NoSellHours", "")
        min_start = inputs.get(f"InpContextFilter{slot}MinMonthStartBalance", "0.0")
        max_start = inputs.get(f"InpContextFilter{slot}MaxMonthStartBalance", "0.0")
        if not months and not no_hours and not no_buy and not no_sell and mult in {"", "1", "1.0"}:
            continue
        fragments = [f"s{slot}:m={months or '-'}", f"mult={mult}"]
        if no_hours:
            fragments.append(f"h={no_hours}")
        if no_buy:
            fragments.append(f"buy={no_buy}")
        if no_sell:
            fragments.append(f"sell={no_sell}")
        if min_start not in {"", "0", "0.0"}:
            fragments.append(f"min={min_start}")
        if max_start not in {"", "0", "0.0"}:
            fragments.append(f"max={max_start}")
        parts.append(" ".join(fragments))
    return "<br>".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit generated or installed MT5 portfolio .chr profile inputs.")
    parser.add_argument("--profile-dir", type=Path, required=True)
    parser.add_argument("--schedule", default="")
    parser.add_argument("--schedule-config", type=Path, default=DEFAULT_SCHEDULE_CONFIG)
    parser.add_argument("--strategy-config", type=Path, default=DEFAULT_STRATEGY_CONFIG)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    errors, report = audit_profile(args.profile_dir, args.schedule, args.schedule_config, args.strategy_config)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
