#!/usr/bin/env python3
"""ZD(M3) + QS(M1) 24月独立回测 — 匹配Live TF"""
import subprocess, sys, re
from pathlib import Path
from calendar import monthrange
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / 'results' / 'backtest'

months = []
for year in (2024, 2025, 2026):
    sm = 6 if year == 2024 else 1
    em = 5 if year == 2026 else 12
    for m in range(sm, em + 1):
        _, ld = monthrange(year, m)
        months.append((f"{year}.{m:02d}.01", f"{year}.{m:02d}.{ld:02d}", f"{year}-{m:02d}"))

strategies = [
    ('v11xau-zd', 'ZD', 'M3'),
    ('v11xau-qs', 'QS', 'M1'),
]

all_results = {}

for strat, label, tf in strategies:
    print(f"\n{'='*60}")
    print(f"  {label} ({strat}) @ {tf} — 24-month independent backtests")
    print(f"{'='*60}")
    print(f"{'Month':<10} {'Trades':>5} {'WR':>7} {'Balance':>10} {'Return':>8}  Win?")
    print("-" * 55)

    profitable = 0
    total_t = 0
    month_data = []

    for date_from, date_to, ml in months:
        fc = date_from.replace('.', ''); tc = date_to.replace('.', '')
        print(f"  [{ml}] ", end='', flush=True)

        result = subprocess.run([
            sys.executable, str(ROOT / 'scripts' / 'mt5_backtest_win.py'),
            '--strategy', strat, '--symbol', 'XAUUSDm',
            '--from', date_from, '--to', date_to,
            '--model', '4', '--timeout', '300',
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(ROOT))

        text = result.stdout + result.stderr
        m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', text)
        if m:
            t = int(m.group(1)); wr = float(m.group(2)); bal = float(m.group(3))
            ret = (bal - 200) / 200 * 100
            win = "WIN" if bal > 200 else "LOSS"
            if bal > 200: profitable += 1
            total_t += t
            month_data.append((ml, t, wr, bal, ret))
            print(f"\r{ml:<10} {t:>5} {wr:>6.1f}% ${bal:>9.2f} {ret:>+7.1f}%  {win}")
        else:
            print(f"\r{ml:<10}   ERR")

    avg_ret = sum(d[4] for d in month_data) / len(month_data) if month_data else 0
    min_ret = min(d[4] for d in month_data) if month_data else 0
    print("-" * 55)
    print(f"  {label}: {profitable}/{len(months)} profitable | Avg: {avg_ret:+.1f}% | Min: {min_ret:+.1f}% | Total: {total_t}t")

    all_results[label] = {
        'profitable': profitable,
        'total_months': len(months),
        'avg_ret': avg_ret,
        'min_ret': min_ret,
        'total_trades': total_t,
        'months': month_data,
    }

# Cross-comparison
print(f"\n{'='*60}")
print(f"  ZD vs QS Monthly Comparison")
print(f"{'='*60}")
print(f"{'Month':<10} {'ZD Ret':>8} {'QS Ret':>8} {'Winner':>6}")
print("-" * 40)
zd_data = {d[0]: d for d in all_results.get('ZD', {}).get('months', [])}
qs_data = {d[0]: d for d in all_results.get('QS', {}).get('months', [])}
zd_wins = qs_wins = 0
for ml, _, _, _, _ in months:
    zd_r = zd_data.get(ml, (None, None, None, None, 0))[4]
    qs_r = qs_data.get(ml, (None, None, None, None, 0))[4]
    w = "ZD" if zd_r > qs_r else "QS"
    if zd_r > qs_r: zd_wins += 1
    else: qs_wins += 1
    print(f"{ml:<10} {zd_r:>+7.1f}% {qs_r:>+7.1f}% {w:>6}")
print("-" * 40)
print(f"ZD wins: {zd_wins}/{len(months)} | QS wins: {qs_wins}/{len(months)}")
