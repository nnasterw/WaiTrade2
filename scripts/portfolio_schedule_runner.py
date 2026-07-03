#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from portfolio_path_sim import MonthState, load_trades, parse_filters, simulate


DEFAULT_CONFIG = ROOT / "config" / "portfolio_schedules.yaml"


@dataclass(frozen=True)
class TargetAudit:
    total_profit: float
    final_balance: float
    daily_trades: float
    bad_months: list[MonthState]
    monthly_profit_min: float
    profit_pass: bool
    daily_pass: bool
    months_pass: bool

    @property
    def passed(self) -> bool:
        return self.profit_pass and self.daily_pass and self.months_pass


def load_config(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing schedule config: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    schedules = data.get("schedules")
    if not isinstance(schedules, dict) or not schedules:
        raise SystemExit(f"no schedules found in {path}")
    return schedules


def as_series_arg(item: dict) -> str:
    name = str(item["name"])
    path = Path(str(item["path"]))
    if not path.is_absolute():
        path = ROOT / path
    scale = float(item.get("scale", 1.0))
    suffix = f"*{scale:g}" if scale != 1.0 else ""
    return f"{name}={path}{suffix}"


def build_args(schedule: dict) -> SimpleNamespace:
    guards = schedule.get("guards") or {}
    return SimpleNamespace(
        deposit=float(schedule.get("deposit", 200.0)),
        days=int(schedule.get("days", 720)),
        profit_target_stop_pct=float(guards.get("profit_target_stop_pct", 0.0)),
        profit_target_min_trades=int(guards.get("profit_target_min_trades", 1)),
        profit_target_stop2_pct=float(guards.get("profit_target_stop2_pct", 0.0)),
        profit_target2_min_trades=int(guards.get("profit_target2_min_trades", 1)),
        guard2_months={str(item) for item in guards.get("guard2_months", [])},
        guard2_monthnums={f"{int(item):02d}" for item in guards.get("guard2_monthnums", [])},
        guard2_min_month_start_balance=float(guards.get("guard2_min_month_start_balance", 0.0)),
        guard2_max_month_start_balance=float(guards.get("guard2_max_month_start_balance", 0.0)),
        loss_stop_pct=float(guards.get("loss_stop_pct", 0.0)),
        loss_stop_min_trades=int(guards.get("loss_stop_min_trades", 1)),
        early_loss_stop_trades=int(guards.get("early_loss_stop_trades", 0)),
        early_loss_stop_pct=float(guards.get("early_loss_stop_pct", 0.0)),
        guard_months={str(item) for item in guards.get("guard_months", [])},
        guard_monthnums={f"{int(item):02d}" for item in guards.get("guard_monthnums", [])},
        guard_min_month_start_balance=float(guards.get("guard_min_month_start_balance", 0.0)),
        guard_max_month_start_balance=float(guards.get("guard_max_month_start_balance", 0.0)),
        signal_block_signal=str(guards.get("signal_block_signal", "")),
        signal_block_loss_pct=float(guards.get("signal_block_loss_pct", 0.0)),
        signal_block_monthnums={
            f"{int(item):02d}" for item in guards.get("signal_block_monthnums", [])
        },
        signal_block_min_month_start_balance=float(
            guards.get("signal_block_min_month_start_balance", 0.0)
        ),
        signal_block_max_day=int(guards.get("signal_block_max_day", 0)),
        drop_filters=parse_filters(schedule.get("drop_filters") or []),
        drop_min_month_start_balance=float(guards.get("drop_min_month_start_balance", 0.0)),
        drop_max_month_start_balance=float(guards.get("drop_max_month_start_balance", 0.0)),
        drop_max_day=int(guards.get("drop_max_day", 0)),
        drop_only_before_month_profit=bool(guards.get("drop_only_before_month_profit", False)),
        drop_only_monthly_negative=bool(guards.get("drop_only_monthly_negative", False)),
    )


def audit_targets(rows: list[MonthState], args: SimpleNamespace, targets: dict) -> TargetAudit:
    total_profit = sum(row.profit for row in rows)
    total_trades = sum(row.trades for row in rows)
    final_balance = rows[-1].end_balance if rows else args.deposit
    daily_trades = total_trades / args.days if args.days else 0.0
    profit_min = float(targets.get("profit_min", 0.0))
    daily_min = float(targets.get("daily_trades_min", 0.0))
    require_non_negative = bool(targets.get("require_non_negative_months", False))
    monthly_profit_min = float(targets.get("monthly_profit_min", 0.0))
    bad_months = [row for row in rows if row.profit < monthly_profit_min]
    return TargetAudit(
        total_profit=total_profit,
        final_balance=final_balance,
        daily_trades=daily_trades,
        bad_months=bad_months,
        monthly_profit_min=monthly_profit_min,
        profit_pass=total_profit > profit_min,
        daily_pass=daily_trades > daily_min,
        months_pass=(not require_non_negative or len(bad_months) == 0),
    )


def render(schedule_name: str, schedule: dict, rows: list[MonthState], audit: TargetAudit) -> str:
    lines = [
        f"# Portfolio schedule proxy: {schedule_name}",
        "",
        f"description: {schedule.get('description', '')}",
        "",
        "warning: CSV path-level proxy only; not a valid MT5 portfolio backtest.",
        "",
        (
            f"summary: total={audit.total_profit:.2f} "
            f"final={audit.final_balance:.2f} daily={audit.daily_trades:.2f} "
            f"bad={len(audit.bad_months)} pass={str(audit.passed).lower()}"
        ),
        "",
        "| target | result | pass |",
        "|---|---:|---|",
        f"| profit > min | {audit.total_profit:.2f} | {audit.profit_pass} |",
        f"| daily trades > min | {audit.daily_trades:.2f} | {audit.daily_pass} |",
        f"| monthly profit >= {audit.monthly_profit_min:.2f} | {len(audit.bad_months)} bad | {audit.months_pass} |",
        "",
        "| month | trades | skipped | profit | start | end | stop |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        marker = "*" if row.profit < 0 else ""
        lines.append(
            f"| {row.month}{marker} | {row.trades} | {row.skipped} | {row.profit:.2f} | "
            f"{row.start_balance:.2f} | {row.end_balance:.2f} | {row.stop_reason} |"
        )
    return "\n".join(lines) + "\n"


def run_schedule(config_path: Path, schedule_name: str) -> tuple[str, TargetAudit]:
    schedules = load_config(config_path)
    if schedule_name not in schedules:
        names = ", ".join(sorted(schedules))
        raise SystemExit(f"unknown schedule: {schedule_name}; available: {names}")
    schedule = schedules[schedule_name]
    args = build_args(schedule)
    series = [as_series_arg(item) for item in schedule.get("series", [])]
    if not series:
        raise SystemExit(f"schedule has no series: {schedule_name}")
    trades = load_trades(series)
    rows = simulate(trades, args)
    audit = audit_targets(rows, args, schedule.get("targets") or {})
    return render(schedule_name, schedule, rows, audit), audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a YAML-defined portfolio schedule proxy.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--schedule", default="r186_r196_season_guard")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report, audit = run_schedule(args.config, args.schedule)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    raise SystemExit(0 if audit.passed else 2)


if __name__ == "__main__":
    main()
