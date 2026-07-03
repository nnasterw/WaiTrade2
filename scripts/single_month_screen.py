#!/usr/bin/env python3
"""Generate MT5 single-month screening commands from a full-window trade CSV.

This is a speed-up helper only. A passing single-month screen is not a valid
replacement for the fixed-window 720-day Real Ticks backtest.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class MonthRow:
    month: str
    trades: int
    pnl_proxy: float
    profit: float
    start_balance: float
    end_balance: float


def read_text_auto(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "utf-16-le", "utf-16"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def parse_report(path: Path) -> tuple[float | None, float | None]:
    text = read_text_auto(path)
    deposit = None
    final_balance = None

    deposit_match = re.search(r"(?:资金|璧勯噾)\s*:\s*\$(-?[\d.]+)", text)
    if deposit_match:
        deposit = float(deposit_match.group(1))

    for line in text.splitlines():
        if "合计" in line or "鍚堣" in line or "Total" in line:
            balances = re.findall(r"\$(-?[\d.]+)", line)
            if balances:
                final_balance = float(balances[-1])

    if final_balance is None:
        balances = re.findall(r"\$(-?[\d.]+)", text)
        if balances:
            final_balance = float(balances[-1])

    return deposit, final_balance


def load_month_rows(trades_path: Path, deposit: float, final_balance: float) -> list[MonthRow]:
    buckets: dict[str, list[float]] = defaultdict(list)
    with trades_path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            month = (row.get("date") or row.get("time") or "")[:7]
            if not month:
                continue
            buckets[month].append(float(row.get("pnl_proxy") or 0.0))

    proxy_total = sum(sum(values) for values in buckets.values())
    actual_total = final_balance - deposit
    scale = actual_total / proxy_total if proxy_total else 0.0

    rows = []
    running = deposit
    for month in sorted(buckets):
        values = buckets[month]
        pnl_proxy = sum(values)
        profit = pnl_proxy * scale
        start_balance = running
        end_balance = start_balance + profit
        rows.append(
            MonthRow(
                month=month,
                trades=len(values),
                pnl_proxy=pnl_proxy,
                profit=profit,
                start_balance=start_balance,
                end_balance=end_balance,
            )
        )
        running = end_balance

    if rows:
        drift = final_balance - rows[-1].end_balance
        rows[-1].profit += drift
        rows[-1].end_balance += drift
    return rows


def next_month_start(month: str) -> str:
    year, mon = [int(part) for part in month.split("-")]
    if mon == 12:
        return f"{year + 1}.01.01"
    return f"{year}.{mon + 1:02d}.01"


def month_start(month: str) -> str:
    year, mon = [int(part) for part in month.split("-")]
    return date(year, mon, 1).strftime("%Y.%m.%d")


def infer_strategy(path: Path) -> str:
    stem = path.name.replace(".trades.csv", "")
    match = re.search(r"_(\d{8})_(\d{8})_\d{8}$", stem)
    if match:
        return stem[: match.start()]
    return stem


def format_command(args: argparse.Namespace, row: MonthRow, strategy: str) -> str:
    return (
        f"python {args.runner} --strategy {strategy} --symbol {args.symbol} "
        f"--from {month_start(row.month)} --to {next_month_start(row.month)} "
        f"--deposit {row.start_balance:.2f} --timeout {args.timeout}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build bad-month MT5 screening commands using the full-window month-start balance. "
            "Use this to reject candidates quickly; accept only after full-window validation."
        )
    )
    parser.add_argument("--trades", required=True, type=Path, help="Full-window .trades.csv")
    parser.add_argument("--report", type=Path, help="Matching full-window report .txt")
    parser.add_argument("--deposit", type=float, help="Initial full-window deposit override")
    parser.add_argument("--final-balance", type=float, help="Final full-window balance override")
    parser.add_argument("--strategy", help="Candidate strategy to place in generated commands")
    parser.add_argument("--symbol", default="BTCUSDm")
    parser.add_argument("--runner", default=r"scripts\mt5_backtest_win.py")
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--months", default="", help="Comma-separated months to print; default=negative months")
    parser.add_argument("--all", action="store_true", help="Print all months instead of only negative months")
    args = parser.parse_args()

    deposit = args.deposit
    final_balance = args.final_balance
    if args.report:
        parsed_deposit, parsed_final = parse_report(args.report)
        deposit = deposit if deposit is not None else parsed_deposit
        final_balance = final_balance if final_balance is not None else parsed_final

    if deposit is None or final_balance is None:
        raise SystemExit("need --report or both --deposit and --final-balance")

    rows = load_month_rows(args.trades, deposit, final_balance)
    requested_months = {part.strip() for part in args.months.split(",") if part.strip()}
    strategy = args.strategy or infer_strategy(args.trades)

    selected = []
    for row in rows:
        if requested_months and row.month not in requested_months:
            continue
        if not requested_months and not args.all and row.profit >= 0:
            continue
        selected.append(row)

    print("# 单月快速筛选命令")
    print("警告: 这是坏月前置筛选工具，不是有效的完整回测。通过后仍需跑固定窗口 Real Ticks。")
    print(f"source={args.trades}")
    print(f"deposit={deposit:.2f} final_balance={final_balance:.2f} strategy={strategy}")
    print()
    for row in selected:
        print(
            f"{row.month}: trades={row.trades} profit={row.profit:.2f} "
            f"start={row.start_balance:.2f} end={row.end_balance:.2f}"
        )
        print(format_command(args, row, strategy))
        print()


if __name__ == "__main__":
    main()
