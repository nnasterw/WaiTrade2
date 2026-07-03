#!/usr/bin/env python3
"""批量逐月回测 v12xau-mp1，解析报告生成汇总表"""
import subprocess, sys, os, re
from datetime import datetime, timedelta
from pathlib import Path
from calendar import monthrange

# Fix encoding on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / 'results' / 'backtest'

# 日期范围: 2024-06 到 2026-05
months = []
for year in (2024, 2025, 2026):
    start_m = 6 if year == 2024 else 1
    end_m = 6 if year == 2026 else 13  # 13 means up to Dec
    for month in range(start_m, end_m):
        _, last_day = monthrange(year, month)
        months.append((
            f"{year}.{month:02d}.01",
            f"{year}.{month:02d}.{last_day:02d}",
            f"{year}-{month:02d}"
        ))

print(f"Total {len(months)} months to process")
print("=" * 70)

today_str = datetime.now().strftime('%Y%m%d')
results = []

for date_from, date_to, label in months:
    from_clean = date_from.replace('.', '')
    to_clean = date_to.replace('.', '')
    report_path = RESULTS_DIR / f"v12xau-mp1_{from_clean}_{to_clean}_{today_str}.txt"

    # Check if report already exists (any date suffix)
    existing = list(RESULTS_DIR.glob(f"v12xau-mp1_{from_clean}_{to_clean}_*.txt"))
    if existing:
        report_path = existing[0]
        print(f"[{label}] Report exists, skip -> {report_path.name}")
    else:
        print(f"[{label}] Running backtest...", end=' ', flush=True)
        cmd = [
            sys.executable, str(ROOT / 'scripts' / 'mt5_backtest_win.py'),
            '--strategy', 'v12xau-mp1',
            '--symbol', 'XAUUSDm',
            '--from', date_from,
            '--to', date_to,
            '--model', '4',
            '--timeout', '300',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        # Find newly generated report
        existing = list(RESULTS_DIR.glob(f"v12xau-mp1_{from_clean}_{to_clean}_*.txt"))
        if existing:
            report_path = max(existing, key=lambda p: p.stat().st_mtime)
            print("done")
        else:
            print(f"FAILED (returncode={result.returncode})")
            results.append((label, 'N/A', 'N/A', 'N/A', 'N/A', 'FAIL'))
            continue

    # Parse report
    try:
        content = report_path.read_text(encoding='utf-8')
        # Match: XAUUSDm      44    1.5   47.7   %0.57    N/A     $121.83
        m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', content)
        if m:
            trades = int(m.group(1))
            win_rate = float(m.group(2))
            balance = float(m.group(3))
            return_pct = (balance - 200) / 200 * 100
            if balance > 200:
                profitable = "WIN"
            elif abs(balance - 200) < 0.5:
                profitable = "EVN"
            else:
                profitable = "LOSS"
            results.append((label, str(trades), f"{win_rate:.1f}%", f"${balance:.2f}", f"{return_pct:+.1f}%", profitable))
            print(f"  -> {trades}t, WR{win_rate:.1f}%, Bal${balance:.2f}, Ret{return_pct:+.1f}% {profitable}")
        else:
            print(f"  -> Parse failed: {content[:200]}")
            results.append((label, '?', '?', '?', '?', '?'))
    except Exception as e:
        print(f"  -> Read error: {e}")
        results.append((label, 'ERR', 'ERR', 'ERR', 'ERR', 'ERR'))

# Summary
print()
print("=" * 70)
print("v12xau-mp1 2-Year Monthly Backtest Summary (Model 4 / Real Ticks / $200)")
print("=" * 70)
print(f"{'Month':<10} {'Trades':>5} {'WR':>7} {'Balance':>10} {'Return':>8}  Win?")
print("-" * 52)
profitable_count = 0
total_trades = 0
for r in results:
    label, trades, wr, bal, ret, prof = r
    print(f"{label:<10} {trades:>5} {wr:>7} {bal:>10} {ret:>8}  {prof}")
    if trades.isdigit():
        total_trades += int(trades)
    if prof == 'WIN':
        profitable_count += 1
print("-" * 52)
print(f"Profitable months: {profitable_count}/{len(results)} | Total trades: {total_trades}")
print("=" * 70)
