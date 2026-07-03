#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from portfolio_path_sim import MonthState, load_trades, simulate  # noqa: E402
from portfolio_schedule_runner import DEFAULT_CONFIG, as_series_arg, build_args, load_config  # noqa: E402


@dataclass(frozen=True)
class MonthlyReturnRow:
    month: str
    trades: int
    skipped: int
    profit: float
    start_balance: float
    end_balance: float
    return_pct: float
    shortfall: float
    stop_reason: str


def row_return_pct(row: MonthState) -> float:
    if row.start_balance <= 0:
        return 0.0
    return row.profit / row.start_balance * 100.0


def audit_schedule(config_path: Path, schedule_name: str, target_pct: float) -> list[MonthlyReturnRow]:
    schedules = load_config(config_path)
    if schedule_name not in schedules:
        names = ", ".join(sorted(schedules))
        raise SystemExit(f"unknown schedule: {schedule_name}; available: {names}")
    schedule = schedules[schedule_name]
    args = build_args(schedule)
    trades = load_trades([as_series_arg(item) for item in schedule.get("series", [])])
    rows = simulate(trades, args)
    result: list[MonthlyReturnRow] = []
    for row in rows:
        return_pct = row_return_pct(row)
        target_profit = row.start_balance * target_pct / 100.0
        result.append(
            MonthlyReturnRow(
                month=row.month,
                trades=row.trades,
                skipped=row.skipped,
                profit=row.profit,
                start_balance=row.start_balance,
                end_balance=row.end_balance,
                return_pct=return_pct,
                shortfall=max(0.0, target_profit - row.profit),
                stop_reason=row.stop_reason,
            )
        )
    return result


def render(schedule_name: str, rows: list[MonthlyReturnRow], target_pct: float) -> str:
    below = [row for row in rows if row.return_pct < target_pct]
    weakest = min(rows, key=lambda row: row.return_pct) if rows else None
    lines = [
        f"# Portfolio monthly return audit: {schedule_name}",
        "",
        "warning: CSV path-level proxy only; not a valid MT5 portfolio backtest.",
        "",
        (
            f"summary: target_pct={target_pct:.2f} below={len(below)} "
            f"months={len(rows)} total_shortfall={sum(row.shortfall for row in below):.2f} "
            f"min_return={'-' if weakest is None else f'{weakest.month}:{weakest.return_pct:.2f}%'}"
        ),
        "",
        "| month | return_pct | shortfall | trades | skipped | profit | start | end | stop |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        marker = "*" if row.return_pct < target_pct else ""
        lines.append(
            f"| {row.month}{marker} | {row.return_pct:.2f} | {row.shortfall:.2f} | "
            f"{row.trades} | {row.skipped} | {row.profit:.2f} | "
            f"{row.start_balance:.2f} | {row.end_balance:.2f} | {row.stop_reason} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit monthly return percent for a portfolio schedule proxy.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--schedule", default="v11a")
    parser.add_argument("--target-pct", type=float, default=35.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = audit_schedule(args.config, args.schedule, args.target_pct)
    report = render(args.schedule, rows, args.target_pct)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
