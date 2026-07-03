#!/usr/bin/env python3
"""QS 720-day phase analysis — segment balance trajectory into profit/loss cycles"""
import subprocess, sys, re
from pathlib import Path
from datetime import datetime, timedelta
from calendar import monthrange

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / 'results' / 'backtest'

# Step 1: Run monthly backtests for QS on M1 for all 24 months
months = []
for year in (2024, 2025, 2026):
    sm = 6 if year == 2024 else 1
    em = 5 if year == 2026 else 12
    for m in range(sm, em + 1):
        _, ld = monthrange(year, m)
        months.append((f"{year}.{m:02d}.01", f"{year}.{m:02d}.{ld:02d}", f"{year}-{m:02d}"))

print("Running QS (v11xau-qs) M1 monthly backtests...")
print(f"{'Month':<10} {'Trades':>5} {'WR':>6} {'Balance':>9} {'Return':>8}")
print("-" * 50)

monthly_data = []
for date_from, date_to, label in months:
    print(f"  [{label}] ", end='', flush=True)
    result = subprocess.run([
        sys.executable, str(ROOT / 'scripts' / 'mt5_backtest_win.py'),
        '--strategy', 'v11xau-qs', '--symbol', 'XAUUSDm',
        '--from', date_from, '--to', date_to,
        '--model', '4', '--timeout', '300',
    ], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(ROOT))
    text = result.stdout + result.stderr
    m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', text)
    if m:
        t = int(m.group(1)); wr = float(m.group(2)); bal = float(m.group(3))
        ret = (bal - 200) / 200 * 100
        monthly_data.append((label, t, wr, bal, ret))
        print(f"\r{label:<10} {t:>5} {wr:>5.1f}% ${bal:>8.2f} {ret:>+7.1f}%")
    else:
        print(f"\r{label:<10}   FAILED")
        monthly_data.append((label, 0, 0, 200, 0))

print("\n" + "=" * 70)
print("Phase Segmentation (continuous compounding simulation)")
print("=" * 70)

# Step 2: Simulate continuous compounding
balance = 200.0
peak_balance = 200.0
phases = []
current_phase = {'start': months[0][2], 'type': '', 'months': [], 'trades': 0, 'start_bal': 200}
in_profit_phase = None  # None = undetermined

for i, (label, t, wr, bal, ret) in enumerate(monthly_data):
    if bal <= 0:
        continue

    month_factor = bal / 200.0  # standalone return multiplier
    prev_balance = balance
    balance *= month_factor

    # Determine if this month is profit or loss
    is_profit = balance > prev_balance

    # Phase detection
    if in_profit_phase is None:
        in_profit_phase = is_profit
        current_phase['type'] = 'PROFIT' if is_profit else 'LOSS'
        current_phase['start'] = label
        current_phase['start_bal'] = prev_balance
    elif is_profit != in_profit_phase:
        # Phase change!
        current_phase['end'] = months[i-1][2] if i > 0 else label
        current_phase['end_bal'] = prev_balance
        current_phase['duration_months'] = len(current_phase['months'])
        if current_phase['start_bal'] > 0:
            current_phase['return_pct'] = (current_phase['end_bal'] - current_phase['start_bal']) / current_phase['start_bal'] * 100
        phases.append(current_phase)

        # Start new phase
        in_profit_phase = is_profit
        current_phase = {'start': label, 'type': 'PROFIT' if is_profit else 'LOSS',
                         'months': [], 'trades': 0, 'start_bal': prev_balance}

    current_phase['months'].append(label)
    current_phase['trades'] += t

    if balance > peak_balance:
        peak_balance = balance

# Last phase
current_phase['end'] = months[-1][2]
current_phase['end_bal'] = balance
current_phase['duration_months'] = len(current_phase['months'])
if current_phase['start_bal'] > 0:
    current_phase['return_pct'] = (balance - current_phase['start_bal']) / current_phase['start_bal'] * 100
phases.append(current_phase)

# Step 3: Print phase analysis
print(f"\n{'Phase':<6} {'Type':<7} {'Months':<25} {'Duration':>8} {'Trades':>6} {'Start':>10} {'End':>10} {'Return':>9}  Drawdown")
print("-" * 120)

for i, p in enumerate(phases):
    months_str = f"{p['start']}→{p['end']}"
    dur = p.get('duration_months', len(p['months']))
    ret = p.get('return_pct', 0)

    # Calculate max drawdown within phase
    dd = ""
    if p['type'] == 'LOSS':
        dd = f"  Peak→Trough"

    print(f"P{i+1:<5} {p['type']:<7} {months_str:<25} {dur:>4}mo {p['trades']:>6}t ${p['start_bal']:>8.0f} ${p['end_bal']:>8.0f} {ret:>+8.1f}%{dd}")

print(f"\nPeak Balance: ${peak_balance:,.0f}")
print(f"Final Balance: ${balance:,.0f}")
print(f"Total Phases: {len(phases)}")
