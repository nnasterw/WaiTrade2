#!/usr/bin/env python3
"""run_24m_independent.py - 24 次独立 30 天回测 (WFYS v2.0)

按 WFYS v2.0 标准, 24 独立月 = 24 次独立 30 天回测
"""
import sys, csv, subprocess
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(r"D:\Code\codexProject\WaiTrade2")
SCRIPTS = ROOT / "scripts"
RESULTS = ROOT / "results" / "backtest"


def get_months(start_year=2024, start_month=7, count=24):
    """生成 24 个连续月份 (2024-07 到 2026-06)"""
    months = []
    y, m = start_year, start_month
    for _ in range(count):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def run_month_backtest(strategy, symbol, year, month, timeout=600):
    """跑单月 30 天回测"""
    from_date = f"{year}-{month:02d}-01"
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    to_date = f"{next_year}-{next_month:02d}-01"
    # 减 1 天 (最后一天)
    to_dt = datetime(next_year, next_month, 1) - timedelta(days=1)
    to_date = to_dt.strftime("%Y-%m-%d")

    cmd = [
        "python", str(SCRIPTS / "mt5_backtest_win.py"),
        "--strategy", strategy, "--symbol", symbol,
        "--from", from_date, "--to", to_date,
        "--model", "4", "--deposit", "200", "--timeout", str(timeout),
    ]
    print(f"  Running {year}-{month:02d}: {from_date} to {to_date}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+60)
    return r.returncode == 0


def main():
    parser_args = sys.argv[1:]
    strategy = "v11-btc1-bv1"
    symbol = "BTCUSDm"
    start_year = 2024
    start_month = 7
    months_count = 24

    for arg in parser_args:
        if arg.startswith("--strategy="):
            strategy = arg.split("=")[1]
        elif arg.startswith("--symbol="):
            symbol = arg.split("=")[1]
        elif arg.startswith("--year-start="):
            start_year = int(arg.split("=")[1])
        elif arg.startswith("--month-start="):
            start_month = int(arg.split("=")[1])
        elif arg.startswith("--count="):
            months_count = int(arg.split("=")[1])

    print(f"WFYS v2.0 - 24m Independent Backtest")
    print(f"Strategy: {strategy}")
    print(f"Symbol: {symbol}")
    print(f"Period: {start_year}-{start_month:02d} + {months_count} months")
    print()

    out_dir = RESULTS / f"{strategy}_24m_independent"
    out_dir.mkdir(parents=True, exist_ok=True)

    months = get_months(start_year, start_month, months_count)
    success_count = 0
    for i, (y, m) in enumerate(months):
        ok = run_month_backtest(strategy, symbol, y, m)
        if ok:
            success_count += 1
        print(f"  Progress: {i+1}/{len(months)} (success: {success_count})")
        print()

    print(f"Done: {success_count}/{len(months)} months successful")
    print(f"Output dir: {out_dir}")


if __name__ == "__main__":
    main()

