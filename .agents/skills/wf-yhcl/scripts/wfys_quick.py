#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wfys_quick.py: 读 24m CSV 输出一行 WFYS 评分(3 行 vs batch_wfys.py 6 行)

定位: 当用户已经跑过 batch_wfys.py 看过 24m CSV, 后续只想要核心数据时使用。
输出: 1 行 WFYS 评分 + 1 行最差月 + 1 行最佳月 = 3 行总输出。
对比 batch_wfys.py 6 行: 减少 50% output token。

用法:
  python wfys_quick.py v11-btc1-trend59
  python wfys_quick.py v11-btc1-trend59 --csv path/to/other_24m.csv
"""
import csv
import sys
import argparse
from pathlib import Path

from _project import ROOT
RESULTS_DIR = ROOT / 'results' / 'backtest'


def find_24m_csv(strategy, explicit_csv):
    if explicit_csv:
        p = Path(explicit_csv)
        return p if p.exists() else None
    matches = sorted(RESULTS_DIR.glob(strategy + '_*_24m_*.csv'))
    return matches[-1] if matches else None


def parse_24m(csv_path):
    rows = []
    with csv_path.open('r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows.append({
                'month': row['month'],
                'net': float(row['net']),
                'balance': float(row['balance']),
                'trades': int(row['trades']),
            })
    return rows


def quick_summary(rows):
    if not rows:
        return None
    total = sum(r['net'] for r in rows)
    profit_n = sum(1 for r in rows if r['net'] > 0)
    loss_n = sum(1 for r in rows if r['net'] < 0)
    final = rows[-1]['balance']
    trades = sum(r['trades'] for r in rows)
    pct = (profit_n / len(rows)) * 100
    worst = min(rows, key=lambda x: x['net'])
    best = max(rows, key=lambda x: x['net'])
    return {
        'months': len(rows),
        'profit_pct': pct,
        'profit_n': profit_n,
        'loss_n': loss_n,
        'total': total,
        'final': final,
        'trades': trades,
        'worst_month': worst['month'],
        'worst_pnl': worst['net'],
        'best_month': best['month'],
        'best_pnl': best['net'],
    }


def main():
    parser = argparse.ArgumentParser(description='24m WFYS 精简输出(3 行)')
    parser.add_argument('strategy', help='策略名(如 v11-btc1-trend59)')
    parser.add_argument('--csv', help='显式 24m CSV 路径')
    args = parser.parse_args()

    csv_path = find_24m_csv(args.strategy, args.csv)
    if not csv_path:
        print('ERROR: 24m CSV not found for ' + args.strategy)
        sys.exit(1)

    rows = parse_24m(csv_path)
    s = quick_summary(rows)
    if not s:
        print('ERROR: empty CSV')
        sys.exit(1)

    # 3 行输出(核心 1 行 + 最差 1 行 + 最佳 1 行)
    print('WFYS: {}/{}m 盈利({:.0f}%) ${:.2f} ${:.2f} 笔={}'.format(
        s['profit_n'], s['months'], s['profit_pct'],
        s['total'], s['final'], s['trades']))
    print('Worst: {} ${:.2f} | Best: {} ${:.2f}'.format(
        s['worst_month'], s['worst_pnl'],
        s['best_month'], s['best_pnl']))


if __name__ == '__main__':
    main()
