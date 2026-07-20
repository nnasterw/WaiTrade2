import csv
from collections import defaultdict

with open(r'results/backtest/v11-btc1-bv1_20240601_20260531_20260709.trades.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

month_pnl = defaultdict(lambda: [0.0, 0])
for r in rows:
    if r.get('close_time'):
        m = r['close_time'][:7]
        try:
            month_pnl[m][0] += float(r['r'])
            month_pnl[m][1] += 1
        except: pass

for m in sorted(month_pnl.keys()):
    p, n = month_pnl[m]
    bar = '#' * max(0, int(p*3)) if p > 0 else '-' * max(0, int(-p*3))
    sign = '+' if p >= 0 else '-'
    print(f'{m} | {bar:30s} {sign}{abs(p):5.1f}R | n={n:3d}')
