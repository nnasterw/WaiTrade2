#!/usr/bin/env python3
"""解析所有 D4/D5 报告的汇总数据（从报告末尾提取）"""
import re, os
from pathlib import Path

MT5D = Path(os.path.expandvars(r'%APPDATA%')) / 'MetaQuotes' / 'Terminal' / 'D0E8209F77C8CF37AD8BF550E51FF075'

def parse_summary(filepath):
    raw = filepath.read_bytes()
    try:
        text = raw.decode('utf-16-le')
    except:
        text = raw.decode('utf-8', errors='ignore')

    lines = text.split('\n')

    # Date range
    date_m = re.search(r'M1\s*\((\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})\)', text)
    date_from = date_m.group(1) if date_m else '?'
    date_to = date_m.group(2) if date_m else '?'

    # Count trades: count all 'out' deals
    trades = 0
    for line in lines:
        if 'XAUUSDm' in line and 'out' in line:
            # Check it's a deal row (not a header)
            if re.search(r'<\s*td[^>]*>\s*out\s*<\s*/td\s*>', line, re.IGNORECASE):
                trades += 1

    # Parse summary from last 30 lines
    # Summary format: Commission, Swap, Gross/Net Profit, Final Balance
    summary_nums = []
    for i in range(max(0, len(lines)-50), len(lines)):
        clean = re.sub(r'<[^>]+>', ' | ', lines[i]).strip()
        # Look for: |  | number |  |  pattern (summary rows)
        m = re.match(r'^\|\s*\|\s*(-?[\d\s]+[\d.]*\d)\s*\|\s*\|$', clean)
        if m:
            val_str = m.group(1).replace(' ', '').replace('\xa0', '')
            try:
                summary_nums.append(float(val_str))
            except ValueError:
                pass

    # The last 4 numbers are typically: commission, swap, gross_profit, final_balance
    # (or: commission, swap, net_profit, final_balance)
    final_balance = summary_nums[-1] if len(summary_nums) >= 1 else None
    gross_or_net = summary_nums[-2] if len(summary_nums) >= 2 else None
    swap = summary_nums[-3] if len(summary_nums) >= 3 else None
    commission = summary_nums[-4] if len(summary_nums) >= 4 else None

    # Count wins/losses from deal lines
    wins = 0
    losses = 0
    for line in lines:
        if 'XAUUSDm' not in line or 'out' not in line:
            continue
        clean = re.sub(r'<[^>]+>', ' | ', line).strip()
        parts = [p.strip() for p in clean.split('|')]
        non_empty = [p for p in parts if p]

        # Find sym index
        try:
            sym_idx = non_empty.index('XAUUSDm')
        except ValueError:
            continue

        # Verify: out should be at sym_idx+2
        if sym_idx + 2 >= len(non_empty) or non_empty[sym_idx + 2] != 'out':
            continue

        # Profit is 3 positions before balance which is 2nd to last
        # Non-empty format: [date, deal#, XAUUSDm, dir, out, lot, price, ..., profit, balance, comment]
        # So profit = -3, balance = -2
        if len(non_empty) >= 3:
            try:
                profit_val = float(non_empty[-3].replace(' ', ''))
                if profit_val > 0.01:
                    wins += 1
                elif profit_val < -0.01:
                    losses += 1
            except (ValueError, IndexError):
                pass

    wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0

    return {
        'date_from': date_from,
        'date_to': date_to,
        'trades': trades,
        'wins': wins,
        'losses': losses,
        'wr': wr,
        'commission': commission,
        'swap': swap,
        'gross_net': gross_or_net,
        'balance': final_balance,
    }


# Parse all D4/D5 reports
print(f"{'Report':<42} {'Window':<22} {'Trades':>6} {'W/L':>8} {'WR':>7} {'Balance':>12}")
print("-" * 100)

for f in sorted(MT5D.glob('v11xau-qs3-d[45]*.htm'), key=lambda p: (p.stem, p.stat().st_mtime)):
    r = parse_summary(f)
    name = f.stem.replace('_XAUUSDm_20260604', '')
    # Annotate [1] and [2] as W2/W3
    name = name.replace('[1]', '-W2').replace('[2]', '-W3')
    window = f"{r['date_from']}~{r['date_to']}"
    if r['balance'] is not None:
        print(f"{name:<42} {window:<22} {r['trades']:>4}t {r['wins']:>3}W/{r['losses']:>3}L {r['wr']:>5.1f}% ${r['balance']:>10,.2f}")
    else:
        print(f"{name:<42} {window:<22} {r['trades']:>4}t {r['wins']:>3}W/{r['losses']:>3}L {'?':>5} NO_BAL")
