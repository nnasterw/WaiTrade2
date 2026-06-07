#!/usr/bin/env python3
"""Phase 1: Per-trade diagnostic for Path B vs S2 baseline on 2605."""
import sys, re, os
from pathlib import Path
from collections import Counter, defaultdict

MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))

def parse_html_trades(htm_path):
    """Parse MT5 HTML report into trade list."""
    with open(htm_path, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-16-le', errors='replace')

    # Find trades table
    trades = []
    # Match trade rows - they contain time, direction, price, pnl
    pattern = re.compile(
        r'<tr[^>]*>\s*'
        r'<td[^>]*>(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}(?::\d{2})?)</td>\s*'
        r'<td[^>]*>(buy|sell|long|short)</td>\s*'
        r'.*?'
        r'<td[^>]*>([-\d.]+)</td>\s*'  # pnl
        r'.*?</tr>', re.DOTALL | re.IGNORECASE)

    # Simpler: find all table rows and extract
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', text, re.DOTALL)
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(cells) < 8:
            continue
        # Try to identify trade rows (they have numeric PnL)
        try:
            # MT5 report format varies - try different cell positions
            time_cell = cells[0].strip()
            if not re.match(r'\d{4}\.\d{2}\.\d{2}', time_cell):
                continue

            # Look for PnL in last meaningful cell
            pnl_str = None
            for c in reversed(cells):
                c = c.strip().replace('&nbsp;','').replace(' ','')
                if re.match(r'^-?\d+\.?\d*$', c):
                    pnl_str = c
                    break

            if pnl_str is None:
                continue

            pnl = float(pnl_str)
            direction = 'buy' if ('buy' in cells[1].lower() or 'long' in cells[1].lower()) else 'sell'

            trades.append({
                'time': time_cell,
                'direction': direction,
                'pnl': pnl,
                'raw_cells': [c.strip() for c in cells]
            })
        except (ValueError, IndexError):
            continue

    return trades

def analyze_trades(trades, label):
    """Compute diagnostic metrics."""
    if not trades:
        print(f'{label}: NO TRADES FOUND')
        return None

    n = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]

    n_wins = len(wins)
    n_losses = len(losses)
    wr = n_wins / n * 100 if n > 0 else 0

    total_pnl = sum(t['pnl'] for t in trades)
    avg_w = sum(t['pnl'] for t in wins) / n_wins if n_wins > 0 else 0
    avg_l = sum(t['pnl'] for t in losses) / n_losses if n_losses > 0 else 0
    wl_ratio = avg_w / abs(avg_l) if avg_l != 0 else float('inf')

    # Direction breakdown
    buys = [t for t in trades if t['direction'] == 'buy']
    sells = [t for t in trades if t['direction'] == 'sell']
    buy_wr = len([t for t in buys if t['pnl']>0])/len(buys)*100 if buys else 0
    sell_wr = len([t for t in sells if t['pnl']>0])/len(sells)*100 if sells else 0

    # PnL distribution
    pnls = sorted([t['pnl'] for t in trades])

    # Serial correlation (streak analysis)
    streaks = []
    cur_streak = 1
    for i in range(1, len(trades)):
        if (trades[i]['pnl'] > 0) == (trades[i-1]['pnl'] > 0):
            cur_streak += 1
        else:
            streaks.append(cur_streak)
            cur_streak = 1
    streaks.append(cur_streak)

    max_loss_streak = max(
        sum(1 for t in trades[s:s+l] if t['pnl'] <= 0)
        for s in range(len(trades))
        for l in range(1, min(20, len(trades)-s+1))
    ) if trades else 0

    print(f'\n{"="*60}')
    print(f'  {label} 交易诊断 (N={n})')
    print(f'{"="*60}')
    print(f'  总PnL:         ${total_pnl:+.2f}')
    print(f'  胜率(WR):      {wr:.1f}% ({n_wins}W / {n_losses}L)')
    print(f'  avg_W:         ${avg_w:+.2f}')
    print(f'  avg_L:         ${avg_l:+.2f}')
    print(f'  W/L比值:       {wl_ratio:.2f}')
    print(f'  Buy WR:        {buy_wr:.1f}% ({len(buys)}笔)')
    print(f'  Sell WR:       {sell_wr:.1f}% ({len(sells)}笔)')
    print(f'  PnL范围:       ${pnls[0]:+.2f} ~ ${pnls[-1]:+.2f}')
    print(f'  PnL中位:       ${pnls[len(pnls)//2]:+.2f}')
    print(f'  最大连赢:      {max(streaks)}')
    print(f'  最大连亏估算:   {max_loss_streak}')

    # PnL distribution buckets
    buckets = {'<-$2':0, '-$2~-$1':0, '-$1~$0':0, '$0~$1':0, '$1~$2':0, '$2~$5':0, '>$5':0}
    for t in trades:
        p = t['pnl']
        if p < -2: buckets['<-$2'] += 1
        elif p < -1: buckets['-$2~-$1'] += 1
        elif p < 0: buckets['-$1~$0'] += 1
        elif p < 1: buckets['$0~$1'] += 1
        elif p < 2: buckets['$1~$2'] += 1
        elif p < 5: buckets['$2~$5'] += 1
        else: buckets['>$5'] += 1

    print(f'\n  PnL分布:')
    for k, v in buckets.items():
        bar = '█' * v
        print(f'    {k:>8}: {v:>3} {bar}')

    return {
        'n': n, 'wr': wr, 'avg_w': avg_w, 'avg_l': avg_l,
        'wl_ratio': wl_ratio, 'total_pnl': total_pnl,
        'buy_wr': buy_wr, 'sell_wr': sell_wr,
        'trades': trades
    }

# Main
reports = [
    ('smc_B_2605.htm', 'PathB 2605'),
    ('smc_S2_2605.htm', 'S2原版 2605'),
    ('smc_B_2505.htm', 'PathB 2505'),
    ('smc_S2_2505.htm', 'S2原版 2505'),
]

results = {}
for fname, label in reports:
    fpath = MT5_DATA / fname
    if fpath.exists():
        trades = parse_html_trades(str(fpath))
        results[label] = analyze_trades(trades, label)
    else:
        print(f'MISSING: {fpath}')

# Cross-analysis
if 'PathB 2605' in results and 'S2原版 2605' in results:
    b = results['PathB 2605']
    s2 = results['S2原版 2605']

    print(f'\n{"="*60}')
    print(f'  2605 PathB vs S2原版 交叉对比')
    print(f'{"="*60}')
    print(f'  {"指标":<20} {"PathB":>12} {"S2原版":>12} {"Δ":>12}')
    for metric, fmt in [('n','d'), ('wr','.1f'), ('avg_w','+.2f'), ('avg_l','+.2f'), ('wl_ratio','.2f'), ('total_pnl','+.2f')]:
        bv = b[metric]
        sv = s2[metric]
        if fmt == 'd':
            print(f'  {metric:<20} {bv:>12d} {sv:>12d} {bv-sv:>+12d}')
        elif fmt == '.2f':
            print(f'  {metric:<20} {bv:>12.2f} {sv:>12.2f} {bv-sv:>+12.2f}')
        else:
            print(f'  {metric:<20} {bv:>12{fmt}} {sv:>12{fmt}} {bv-sv:>+12{fmt}}')

print('\n[DONE]')
