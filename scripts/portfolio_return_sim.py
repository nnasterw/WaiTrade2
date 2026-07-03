#!/usr/bin/env python3
"""Shared-balance return proxy for portfolio schedules.

The older path proxy adds each strategy's absolute MT5 PnL. This script first
reconstructs each source strategy's balance path, converts every trade to a
per-trade return, then applies that return to one shared portfolio balance.

It is still a proxy, not a valid MT5 multi-strategy backtest. It is useful for
detecting whether a schedule only works because independent compounding paths
were added together.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from portfolio_path_sim import (
    MonthState,
    Trade,
    parse_series,
    should_block_signal_after_trade,
    should_stop_after_trade,
    trade_matches_any_context_filter,
)
from portfolio_schedule_runner import (
    DEFAULT_CONFIG,
    as_series_arg,
    audit_targets,
    build_args,
    load_config,
)


@dataclass(frozen=True)
class ReturnTrade:
    trade: Trade
    return_fraction: float
    source_balance_before: float
    source_pnl: float


def load_return_trades(raw_series: list[str], source_deposit: float) -> list[ReturnTrade]:
    trades: list[ReturnTrade] = []
    for raw in raw_series:
        name, path, scale = parse_series(raw)
        if not path.exists():
            raise SystemExit(f"missing series file: {path}")
        source_balance = source_deposit
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = sorted(
                [row for row in csv.DictReader(f) if row.get("time")],
                key=lambda row: row.get("time") or "",
            )
        for row in rows:
            time = row.get("time") or ""
            raw_pnl = float(row.get("pnl_proxy") or 0.0)
            if source_balance <= 0:
                raise SystemExit(f"source balance non-positive before {name} {time}: {source_balance:.2f}")
            return_fraction = (raw_pnl / source_balance) * scale
            trade = Trade(
                source=name,
                time=time,
                month=time[:7],
                monthnum=int(time[5:7]),
                day=int(time[8:10]),
                pnl=raw_pnl * scale,
                signal_type=row.get("signal_type") or "",
                direction=row.get("dir") or "",
                hour=str(row.get("hour") or ""),
            )
            trades.append(
                ReturnTrade(
                    trade=trade,
                    return_fraction=return_fraction,
                    source_balance_before=source_balance,
                    source_pnl=raw_pnl,
                )
            )
            source_balance += raw_pnl
    trades.sort(key=lambda item: (item.trade.time, item.trade.source))
    return trades


def simulate_returns(
    trades: list[ReturnTrade],
    args: argparse.Namespace,
    fixed_cost_per_trade: float = 0.0,
) -> list[MonthState]:
    months = sorted({item.trade.month for item in trades})
    states: dict[str, MonthState] = {}
    running_balance = args.deposit
    for month in months:
        state = MonthState(month=month, start_balance=running_balance, blocked_signals=set())
        states[month] = state
        month_trades = [item for item in trades if item.trade.month == month]
        for item in month_trades:
            trade = item.trade
            if trade_matches_any_context_filter(trade, state, args.drop_filters, args):
                state.skipped += 1
                continue
            if state.blocked_signals and trade.signal_type in state.blocked_signals:
                state.skipped += 1
                continue
            if state.stopped:
                state.skipped += 1
                continue

            current_balance = state.start_balance + state.profit
            pnl = current_balance * item.return_fraction - fixed_cost_per_trade
            state.trades += 1
            state.profit += pnl

            block_reason = should_block_signal_after_trade(state, trade, args)
            if block_reason:
                state.blocked_signals.add(trade.signal_type)
                state.stop_reason = f"{state.stop_reason},{block_reason}" if state.stop_reason else block_reason
            reason = should_stop_after_trade(state, args)
            if reason:
                state.stopped = True
                state.stop_reason = reason
        running_balance = state.end_balance
    return [states[month] for month in months]


def render(schedule_name: str, schedule: dict, rows: list[MonthState], audit) -> str:
    lines = [
        f"# Portfolio shared-return proxy: {schedule_name}",
        "",
        f"description: {schedule.get('description', '')}",
        "",
        "warning: shared-balance return proxy only; not a valid MT5 portfolio backtest.",
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
        marker = "*" if row in audit.bad_months else ""
        lines.append(
            f"| {row.month}{marker} | {row.trades} | {row.skipped} | {row.profit:.2f} | "
            f"{row.start_balance:.2f} | {row.end_balance:.2f} | {row.stop_reason} |"
        )
    return "\n".join(lines) + "\n"


def run_schedule(
    config_path: Path,
    schedule_name: str,
    fixed_cost_per_trade: float = 0.0,
) -> tuple[str, object]:
    schedules = load_config(config_path)
    if schedule_name not in schedules:
        names = ", ".join(sorted(schedules))
        raise SystemExit(f"unknown schedule: {schedule_name}; available: {names}")
    schedule = schedules[schedule_name]
    args = build_args(schedule)
    series = [as_series_arg(item) for item in schedule.get("series", [])]
    trades = load_return_trades(series, args.deposit)
    rows = simulate_returns(trades, args, fixed_cost_per_trade=fixed_cost_per_trade)
    audit = audit_targets(rows, args, schedule.get("targets") or {})
    return render(schedule_name, schedule, rows, audit), audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a shared-balance return proxy for a portfolio schedule.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--schedule", default="r186_r196_r117_season_guard")
    parser.add_argument("--fixed-cost-per-trade", type=float, default=0.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report, audit = run_schedule(
        args.config,
        args.schedule,
        fixed_cost_per_trade=args.fixed_cost_per_trade,
    )
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    raise SystemExit(0 if audit.passed else 2)


if __name__ == "__main__":
    main()
