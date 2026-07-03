#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建 24 月 CSV: 按 close_time 归因 PnL."""
import csv
import sys
from collections import defaultdict
from pathlib import Path

def rebuild_24m(trades_csv, deposit):
    trades = []
    with trades_csv.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            close_time = row.get('close_time', '').strip()
            pnl = row.get('pnl_proxy', '').strip()
            if not close_time or not pnl:
                continue
            try:
                pnl_f = float(pnl)
            except ValueError:
                continue
            month = close_time[:7]
            trades.append((month, pnl_f, close_time))

    if not trades:
        raise ValueError('no valid trades')

    by_month = defaultdict(float)
    for month, pnl, _ in trades:
        by_month[month] += pnl

    rows = []
    running = deposit
    for month in sorted(by_month.keys()):
        net = by_month[month]
        start = running
        end = start + net
        running = end
        rows.append({'month': month, 'net': round(net, 2), 'balance': round(end, 2), 'trades': sum(1 for m, _, _ in trades if m == month)})

    out_path = trades_csv.with_name(trades_csv.stem + '_closetime_24m.csv')
    with out_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['month', 'net', 'balance', 'trades'])
        for row in rows:
            writer.writerow([row['month'], row['net'], row['balance'], row['trades']])
    print('WROTE', out_path, len(rows), 'months, final balance $%.2f' % rows[-1]['balance'])
    return out_path


if __name__ == '__main__':
    csv_path = Path(sys.argv[1])
    deposit = float(sys.argv[2]) if len(sys.argv) > 2 else 200.0
    rebuild_24m(csv_path, deposit)