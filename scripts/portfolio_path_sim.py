#!/usr/bin/env python3
"""Path-level portfolio proxy over exported MT5 trade CSVs.

This is still not a valid MT5 portfolio backtest. It keeps the original trade
PnL from each full-window run and only simulates account-level month guards by
dropping later trades in a month after a guard fires. Use it to rank account
orchestration ideas before implementing a real runner.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Trade:
    source: str
    time: str
    month: str
    monthnum: int
    day: int
    pnl: float
    signal_type: str
    direction: str
    hour: str


@dataclass
class MonthState:
    month: str
    start_balance: float
    profit: float = 0.0
    trades: int = 0
    skipped: int = 0
    stopped: bool = False
    stop_reason: str = ""
    blocked_signals: set[str] | None = None

    @property
    def end_balance(self) -> float:
        return self.start_balance + self.profit


def parse_series(raw: str) -> tuple[str, Path, float]:
    scale = 1.0
    if "*" in raw:
        raw, scale_raw = raw.rsplit("*", 1)
        scale = float(scale_raw)
    if "=" in raw:
        name, path = raw.split("=", 1)
        return name.strip(), Path(path.strip()), scale
    path = Path(raw)
    return path.name.replace(".trades.csv", ""), path, scale


def load_trades(raw_series: list[str]) -> list[Trade]:
    trades: list[Trade] = []
    for raw in raw_series:
        name, path, scale = parse_series(raw)
        if not path.exists():
            raise SystemExit(f"missing series file: {path}")
        with path.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                time = row.get("time") or ""
                if not time:
                    continue
                trades.append(
                    Trade(
                        source=name,
                        time=time,
                        month=time[:7],
                        monthnum=int(time[5:7]),
                        day=int(time[8:10]),
                        pnl=float(row.get("pnl_proxy") or 0.0) * scale,
                        signal_type=row.get("signal_type") or "",
                        direction=row.get("dir") or "",
                        hour=str(row.get("hour") or ""),
                    )
                )
    trades.sort(key=lambda item: (item.time, item.source))
    return trades


def parse_filter(raw: str) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    if not raw:
        return result
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise SystemExit(f"bad filter part: {part}")
        key, value = part.split("=", 1)
        result[key.strip()] = {item.strip() for item in value.split(",") if item.strip()}
    return result


def parse_filters(raw_items: list[str]) -> list[dict[str, set[str]]]:
    return [parse_filter(raw) for raw in raw_items if raw]


def trade_matches_filter(trade: Trade, filters: dict[str, set[str]]) -> bool:
    values = {
        "month": trade.month,
        "monthnum": str(trade.monthnum),
        "src": trade.source,
        "signal": trade.signal_type,
        "dir": trade.direction,
        "hour": trade.hour,
        "day": str(trade.day),
    }
    for key, allowed in filters.items():
        if key in {
            "min_start",
            "max_start",
            "max_day",
            "before_profit",
            "monthly_negative",
        }:
            continue
        if key not in values:
            raise SystemExit(f"unknown filter key: {key}")
        if allowed and values[key] not in allowed:
            return False
    return True


def trade_matches_any_filter(trade: Trade, filters: list[dict[str, set[str]]]) -> bool:
    return any(trade_matches_filter(trade, item) for item in filters)


def trade_matches_context_filter(
    trade: Trade,
    state: MonthState,
    filters: dict[str, set[str]],
    args: argparse.Namespace,
) -> bool:
    if not trade_matches_filter(trade, filters):
        return False

    min_start = first_float(filters, "min_start", args.drop_min_month_start_balance)
    max_start = first_float(filters, "max_start", args.drop_max_month_start_balance)
    max_day = first_int(filters, "max_day", args.drop_max_day)
    before_profit = first_bool(filters, "before_profit", args.drop_only_before_month_profit)
    monthly_negative = first_bool(filters, "monthly_negative", args.drop_only_monthly_negative)

    if min_start > 0 and state.start_balance < min_start:
        return False
    if max_start > 0 and state.start_balance > max_start:
        return False
    if max_day > 0 and trade.day > max_day:
        return False
    if before_profit and state.profit > 0:
        return False
    if monthly_negative and state.profit >= 0:
        return False
    return True


def trade_matches_any_context_filter(
    trade: Trade,
    state: MonthState,
    filters: list[dict[str, set[str]]],
    args: argparse.Namespace,
) -> bool:
    return any(trade_matches_context_filter(trade, state, item, args) for item in filters)


def threshold(balance: float, pct: float) -> float:
    return balance * pct / 100.0


def first_value(filters: dict[str, set[str]], key: str) -> str | None:
    values = filters.get(key)
    if not values:
        return None
    return next(iter(values))


def first_float(filters: dict[str, set[str]], key: str, default: float) -> float:
    value = first_value(filters, key)
    return float(value) if value is not None else default


def first_int(filters: dict[str, set[str]], key: str, default: int) -> int:
    value = first_value(filters, key)
    return int(value) if value is not None else default


def first_bool(filters: dict[str, set[str]], key: str, default: bool) -> bool:
    value = first_value(filters, key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y"}


def should_stop_after_trade(state: MonthState, args: argparse.Namespace) -> str:
    if profit_target_slot_hit(
        state,
        args.profit_target_stop_pct,
        args.profit_target_min_trades,
        args.guard_months,
        args.guard_monthnums,
        args.guard_min_month_start_balance,
        args.guard_max_month_start_balance,
    ):
        return f"profit_target_{args.profit_target_stop_pct:g}%"

    if profit_target_slot_hit(
        state,
        getattr(args, "profit_target_stop2_pct", 0.0),
        getattr(args, "profit_target2_min_trades", 1),
        getattr(args, "guard2_months", set()),
        getattr(args, "guard2_monthnums", set()),
        getattr(args, "guard2_min_month_start_balance", 0.0),
        getattr(args, "guard2_max_month_start_balance", 0.0),
    ):
        return f"profit_target2_{args.profit_target_stop2_pct:g}%"

    if loss_guard_matches(state, args):
        if args.loss_stop_pct > 0 and state.trades >= args.loss_stop_min_trades:
            if state.profit <= -threshold(state.start_balance, args.loss_stop_pct):
                return f"loss_stop_{args.loss_stop_pct:g}%"

        if args.early_loss_stop_trades > 0 and state.trades >= args.early_loss_stop_trades:
            if state.profit <= -threshold(state.start_balance, args.early_loss_stop_pct):
                return f"early_loss_{args.early_loss_stop_trades}tr_{args.early_loss_stop_pct:g}%"

    return ""


def guard_matches(
    state: MonthState,
    months: set[str],
    monthnums: set[str],
    min_start: float,
    max_start: float,
) -> bool:
    if months and state.month not in months:
        return False
    if monthnums and state.month[-2:] not in monthnums:
        return False
    if min_start > 0 and state.start_balance < min_start:
        return False
    if max_start > 0 and state.start_balance > max_start:
        return False
    return True


def profit_target_slot_hit(
    state: MonthState,
    pct: float,
    min_trades: int,
    months: set[str],
    monthnums: set[str],
    min_start: float,
    max_start: float,
) -> bool:
    if pct <= 0 or state.trades < min_trades:
        return False
    if not guard_matches(state, months, monthnums, min_start, max_start):
        return False
    return state.profit >= threshold(state.start_balance, pct)


def loss_guard_matches(state: MonthState, args: argparse.Namespace) -> bool:
    return guard_matches(
        state,
        args.guard_months,
        args.guard_monthnums,
        args.guard_min_month_start_balance,
        args.guard_max_month_start_balance,
    )


def should_block_signal_after_trade(
    state: MonthState,
    trade: Trade,
    args: argparse.Namespace,
) -> str:
    if not args.signal_block_signal:
        return ""
    if args.signal_block_monthnums and trade.month[-2:] not in args.signal_block_monthnums:
        return ""
    if args.signal_block_min_month_start_balance > 0 and state.start_balance < args.signal_block_min_month_start_balance:
        return ""
    if args.signal_block_max_day > 0 and trade.day > args.signal_block_max_day:
        return ""
    if trade.signal_type != args.signal_block_signal:
        return ""
    if state.profit <= -threshold(state.start_balance, args.signal_block_loss_pct):
        return f"block_{args.signal_block_signal}_{args.signal_block_loss_pct:g}%"
    return ""


def simulate(trades: list[Trade], args: argparse.Namespace) -> list[MonthState]:
    months = sorted({trade.month for trade in trades})
    states: dict[str, MonthState] = {}
    running_balance = args.deposit
    for month in months:
        states[month] = MonthState(month=month, start_balance=running_balance)
        month_trades = [trade for trade in trades if trade.month == month]
        state = states[month]
        state.blocked_signals = set()
        for trade in month_trades:
            if trade_matches_any_context_filter(trade, state, args.drop_filters, args):
                state.skipped += 1
                continue
            if state.blocked_signals and trade.signal_type in state.blocked_signals:
                state.skipped += 1
                continue
            if state.stopped:
                state.skipped += 1
                continue
            state.trades += 1
            state.profit += trade.pnl
            block_reason = should_block_signal_after_trade(state, trade, args)
            if block_reason:
                state.blocked_signals.add(trade.signal_type)
                if state.stop_reason:
                    state.stop_reason += "," + block_reason
                else:
                    state.stop_reason = block_reason
            reason = should_stop_after_trade(state, args)
            if reason:
                state.stopped = True
                state.stop_reason = reason
        running_balance = state.end_balance
    return [states[month] for month in months]


def print_rows(rows: list[MonthState], days: int) -> None:
    total_profit = sum(row.profit for row in rows)
    total_trades = sum(row.trades for row in rows)
    bad = [row for row in rows if row.profit < 0]
    print(
        f"total={total_profit:.2f} final={rows[-1].end_balance if rows else 0:.2f} "
        f"daily~{(total_trades / days if days else 0):.2f} bad={len(bad)}"
    )
    print("| month | trades | skipped | profit | start | end | stop |")
    print("|---|---:|---:|---:|---:|---:|---|")
    for row in rows:
        marker = "*" if row.profit < 0 else ""
        print(
            f"| {row.month}{marker} | {row.trades} | {row.skipped} | {row.profit:.2f} | "
            f"{row.start_balance:.2f} | {row.end_balance:.2f} | {row.stop_reason} |"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate simple account-level month guards over merged MT5 trade CSVs. "
            "Proxy only; not a valid MT5 portfolio backtest."
        )
    )
    parser.add_argument("--series", action="append", required=True, help="NAME=path.trades.csv or NAME=path*scale")
    parser.add_argument("--deposit", type=float, default=200.0)
    parser.add_argument("--days", type=int, default=720)
    parser.add_argument("--profit-target-stop-pct", type=float, default=0.0)
    parser.add_argument("--profit-target-min-trades", type=int, default=1)
    parser.add_argument("--profit-target-stop2-pct", type=float, default=0.0)
    parser.add_argument("--profit-target2-min-trades", type=int, default=1)
    parser.add_argument("--guard2-months", default="")
    parser.add_argument("--guard2-monthnums", default="")
    parser.add_argument("--guard2-min-month-start-balance", type=float, default=0.0)
    parser.add_argument("--guard2-max-month-start-balance", type=float, default=0.0)
    parser.add_argument("--loss-stop-pct", type=float, default=0.0)
    parser.add_argument("--loss-stop-min-trades", type=int, default=1)
    parser.add_argument("--early-loss-stop-trades", type=int, default=0)
    parser.add_argument("--early-loss-stop-pct", type=float, default=0.0)
    parser.add_argument("--guard-months", default="", help="Comma-separated months where guards are active")
    parser.add_argument("--guard-monthnums", default="", help="Comma-separated calendar month numbers where guards are active, e.g. 10,12")
    parser.add_argument("--guard-min-month-start-balance", type=float, default=0.0)
    parser.add_argument("--guard-max-month-start-balance", type=float, default=0.0)
    parser.add_argument("--signal-block-signal", default="", help="After this signal causes early loss, skip later same-signal trades in the month")
    parser.add_argument("--signal-block-loss-pct", type=float, default=0.0)
    parser.add_argument("--signal-block-monthnums", default="")
    parser.add_argument("--signal-block-min-month-start-balance", type=float, default=0.0)
    parser.add_argument("--signal-block-max-day", type=int, default=0)
    parser.add_argument(
        "--drop-filter",
        action="append",
        default=[],
        help="Drop matching trades before month guards. Example: month=2024-11;signal=ob;hour=13,14",
    )
    parser.add_argument("--drop-min-month-start-balance", type=float, default=0.0)
    parser.add_argument("--drop-max-month-start-balance", type=float, default=0.0)
    parser.add_argument("--drop-max-day", type=int, default=0)
    parser.add_argument("--drop-only-before-month-profit", action="store_true")
    parser.add_argument("--drop-only-monthly-negative", action="store_true")
    args = parser.parse_args()
    args.guard_months = {part.strip() for part in args.guard_months.split(",") if part.strip()}
    args.guard_monthnums = {
        f"{int(part.strip()):02d}"
        for part in args.guard_monthnums.split(",")
        if part.strip()
    }
    args.guard2_months = {part.strip() for part in args.guard2_months.split(",") if part.strip()}
    args.guard2_monthnums = {
        f"{int(part.strip()):02d}"
        for part in args.guard2_monthnums.split(",")
        if part.strip()
    }
    args.signal_block_monthnums = {
        f"{int(part.strip()):02d}"
        for part in args.signal_block_monthnums.split(",")
        if part.strip()
    }
    args.drop_filters = parse_filters(args.drop_filter)

    trades = load_trades(args.series)
    rows = simulate(trades, args)
    print("# 账户级逐单组合 proxy")
    print("警告: 不模拟共享保证金、成交重算、EA状态、复利重算或被停机策略的后续路径变化。")
    print_rows(rows, args.days)


if __name__ == "__main__":
    main()
