#!/usr/bin/env python3
"""Stress a portfolio schedule proxy with fixed per-trade execution cost.

This is a robustness screen for path-level CSV schedules. It answers a narrow
question: how much per executed trade can the monthly path absorb before a
month turns negative?
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from portfolio_path_sim import MonthState, load_trades, simulate
from portfolio_schedule_runner import DEFAULT_CONFIG, as_series_arg, build_args, load_config


@dataclass(frozen=True)
class StressRow:
    cost_per_trade: float
    total_profit: float
    daily_trades: float
    bad_months: list[MonthState]
    min_month: MonthState | None


def apply_cost(trades, cost_per_trade: float):
    return [replace(trade, pnl=trade.pnl - cost_per_trade) for trade in trades]


def stress_schedule(config_path: Path, schedule_name: str, costs: list[float]) -> list[StressRow]:
    schedules = load_config(config_path)
    if schedule_name not in schedules:
        names = ", ".join(sorted(schedules))
        raise SystemExit(f"unknown schedule: {schedule_name}; available: {names}")
    schedule = schedules[schedule_name]
    args = build_args(schedule)
    series = [as_series_arg(item) for item in schedule.get("series", [])]
    trades = load_trades(series)
    rows: list[StressRow] = []
    for cost in costs:
        stressed = apply_cost(trades, cost)
        months = simulate(stressed, args)
        total_trades = sum(row.trades for row in months)
        min_month = min(months, key=lambda row: row.profit) if months else None
        rows.append(
            StressRow(
                cost_per_trade=cost,
                total_profit=sum(row.profit for row in months),
                daily_trades=total_trades / args.days if args.days else 0.0,
                bad_months=[row for row in months if row.profit < 0],
                min_month=min_month,
            )
        )
    return rows


def parse_costs(raw: str) -> list[float]:
    values = [float(part.strip()) for part in raw.split(",") if part.strip()]
    if not values:
        raise SystemExit("no stress costs provided")
    return values


def render(rows: list[StressRow]) -> str:
    lines = [
        "# Portfolio schedule stress",
        "",
        "warning: CSV path-level cost screen only; not a valid MT5 portfolio backtest.",
        "",
        "| cost_per_trade | total_profit | daily | bad_months | weakest_month | weakest_profit |",
        "|---:|---:|---:|---:|---|---:|",
    ]
    for row in rows:
        weakest_month = row.min_month.month if row.min_month else ""
        weakest_profit = row.min_month.profit if row.min_month else 0.0
        lines.append(
            f"| {row.cost_per_trade:.2f} | {row.total_profit:.2f} | {row.daily_trades:.2f} | "
            f"{len(row.bad_months)} | {weakest_month} | {weakest_profit:.2f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Stress a YAML-defined portfolio schedule proxy.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--schedule", default="r186_r196_season_guard")
    parser.add_argument("--costs", default="0,0.05,0.1,0.25,0.5,1.0")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = stress_schedule(args.config, args.schedule, parse_costs(args.costs))
    report = render(rows)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
