# -*- coding: utf-8 -*-
"""
Make 24m CSV using entry date (trade 'date' column) for accurate real 24m WFYS
"""
import csv
import re
from pathlib import Path
from collections import defaultdict

results_dir = Path('results/backtest')
strategy = 'v11-btc1-trend29'
files = sorted(results_dir.glob(f'{strategy}_*_20260702.trades.csv'))
if not files:
    files = sorted(results_dir.glob(f'{strategy}_*_20260703.trades.csv'))

monthly = defaultdict(lambda: {'profit': 0, 'trades': 0, 'wins': 0})

for f in files:
    with f.open('r', encoding='utf-8') as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            pnl_str = row.get('pnl_proxy', '') or row.get('pnl', '')
            if not pnl_str or pnl_str == '':
                continue
            try:
                pnl = float(pnl_str)
            except ValueError:
                continue
            date_str = row.get('date', '')
            if not date_str or len(date_str) < 7:
                continue
            month_key = date_str[:7]
            monthly[month_key]['profit'] += pnl
            monthly[month_key]['trades'] += 1
            if pnl > 0:
                monthly[month_key]['wins'] += 1

output = results_dir / f'{strategy}_BTCUSDm_24m_entry_20260703.csv'
sorted_months = sorted(monthly.keys())
with output.open('w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['month', 'net', 'balance', 'trades', 'wins', 'wr'])
    bal = 200.0
    for m in sorted_months:
        d = monthly[m]
        bal += d['profit']
        wr = (d['wins'] / d['trades'] * 100) if d['trades'] else 0
        w.writerow([m, f'{d["profit"]:.2f}', f'{bal:.2f}', d['trades'], d['wins'], f'{wr:.1f}'])

print(f'CSV: {output.name} ({len(sorted_months)} months)')
print(f'Final balance: ${bal:.2f}')
loss_months = [(m, monthly[m]['profit']) for m in sorted_months if monthly[m]['profit'] < 0]
print(f'Loss months: {len(loss_months)}')
for m, p in loss_months:
    print(f'  {m}: -${abs(p):.2f}')