#!/usr/bin/env python3
"""解析所有 D4/D5 MT5 HTML 回测报告 — 修正版"""
import re, os
from pathlib import Path

MT5D = Path(os.path.expandvars(r'%APPDATA%')) / 'MetaQuotes' / 'Terminal' / 'D0E8209F77C8CF37AD8BF550E51FF075'

def parse_html(filepath):
    raw = filepath.read_bytes()
    try:
        text = raw.decode('utf-16-le')
    except:
        text = raw.decode('utf-8', errors='ignore')

    # Date range
    date_m = re.search(r'M1\s*\((\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})\)', text)
    date_from = date_m.group(1) if date_m else '?'
    date_to = date_m.group(2) if date_m else '?'

    # Parse deal lines
    # HTML table format (after strip): |  | date |  | deal# |  | Symbol |  | dir |  | in/out |  | lot |  | price |  | ... |  | profit |  | balance |  | comment |  |
    # Indices:                           0  1  2     3  4  5    6  7  8    9  10 11   12 13 14  15 16   17    18     19    20     21   22    23     24   25
    # Values at: date=1, deal=3, sym=5, dir=7, inout=9, lot=11, price=13, profit=21, balance=23, comment=25

    trades = 0
    wins = 0
    losses = 0
    total_profit = 0.0
    final_balance = None

    lines = text.split('\n')
    for line in lines:
        clean = re.sub(r'<[^>]+>', ' | ', line).strip()
        if 'XAUUSDm' not in clean:
            continue

        parts = [p.strip() for p in clean.split('|')]

        # Find XAUUSDm index
        try:
            sym_idx = parts.index('XAUUSDm')
        except ValueError:
            continue

        # Verify we have enough parts
        if sym_idx + 16 >= len(parts):
            continue

        direction = parts[sym_idx + 2]   # buy/sell
        inout = parts[sym_idx + 4]       # in/out

        if inout not in ('in', 'out'):
            continue

        if inout == 'out':
            trades += 1
            try:
                profit_val = float(parts[sym_idx + 16])  # profit
                balance_val = float(parts[sym_idx + 18])  # balance
                total_profit += profit_val
                final_balance = balance_val
                if profit_val > 0.01:
                    wins += 1
                elif profit_val < -0.01:
                    losses += 1
            except (ValueError, IndexError):
                pass

    wr = (wins / trades * 100) if trades > 0 else 0.0

    return {
        'date_from': date_from,
        'date_to': date_to,
        'trades': trades,
        'wins': wins,
        'losses': losses,
        'wr': wr,
        'total_profit': round(total_profit, 2),
        'balance': round(final_balance, 2) if final_balance is not None else None,
    }

# Parse all D4/D5 reports
print(f"{'Report':<45} {'Window':<22} {'Trades':>6} {'W/L':>8} {'WR':>7} {'PnL':>9} {'Balance':>10}")
print("-" * 110)

for f in sorted(MT5D.glob('v11xau-qs3-d[45]*.htm'), key=lambda p: (p.stem, p.stat().st_mtime)):
    r = parse_html(f)
    name = f.stem.replace('_XAUUSDm_20260604', '').replace('[1]', '-W2').replace('[2]', '-W3')
    window = f"{r['date_from']}~{r['date_to']}"
    if r['balance'] is not None:
        print(f"{name:<45} {window:<22} {r['trades']:>4}t {r['wins']:>2}W/{r['losses']:>2}L {r['wr']:>5.1f}% {r['total_profit']:>8.2f} ${r['balance']:>9.2f}")
    else:
        print(f"{name:<45} {window:<22} {r['trades']:>4}t {r['wins']:>2}W/{r['losses']:>2}L {'?':>5} {'?':>8} NO_BAL")
