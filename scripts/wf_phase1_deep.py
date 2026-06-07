#!/usr/bin/env python3
"""Phase 1: Per-trade deep analysis from MT5 HTML deal tables."""
import re, sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

MT5_DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')

def parse_deals(htm_path):
    """Parse MT5 HTML report deal table into entry/exit pairs."""
    with open(htm_path, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-16-le', errors='replace')

    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    if len(tables) < 2:
        return []

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tables[1], re.DOTALL)
    entries = []  # (time, type, price, comment)
    exits = []    # (time, type, price, comment)

    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        vals = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        if len(vals) < 11:
            continue
        # Skip header row
        if not re.match(r'\d{4}\.\d{2}\.\d{2}', vals[0]):
            continue

        time_str = vals[0]
        order_type = vals[3]  # buy/sell
        price_str = vals[5]
        comment = vals[10] if len(vals) > 10 else ''

        # Determine if entry or exit
        is_exit = any(kw in comment for kw in ['sl ', 'dtp', 'mfe_fail', 'be ', 'tp ', 'timeout'])

        try:
            price = float(price_str)
        except ValueError:
            continue

        if is_exit:
            exits.append({'time': time_str, 'type': order_type, 'price': price, 'comment': comment})
        elif 'WT ' in comment:
            entries.append({'time': time_str, 'type': order_type, 'price': price, 'comment': comment})

    # Match entries to exits (in order)
    trades = []
    exit_idx = 0
    for entry in entries:
        if exit_idx >= len(exits):
            break
        exit_deal = exits[exit_idx]
        exit_idx += 1

        # Calculate PnL
        if entry['type'] == 'buy':
            pnl = exit_deal['price'] - entry['price']
        else:
            pnl = entry['price'] - exit_deal['price']

        # Parse entry time and hold duration
        try:
            et = datetime.strptime(entry['time'], '%Y.%m.%d %H:%M:%S')
            xt = datetime.strptime(exit_deal['time'], '%Y.%m.%d %H:%M:%S')
            hold_sec = (xt - et).total_seconds()
        except:
            hold_sec = 0

        # Parse exit reason
        exit_reason = 'unknown'
        for reason in ['sl', 'dtp', 'mfe_fail', 'be', 'tp', 'timeout']:
            if reason in exit_deal['comment']:
                exit_reason = reason
                break

        # Parse signal type from entry comment
        sig_type = 'OB'
        if 'SWP' in entry['comment']:
            sig_type = 'SWP'
        elif 'RB' in entry['comment']:
            sig_type = 'RB'

        # Parse position multiplier
        pos_mult = 1.0
        mult_match = re.search(r'x(\d+\.?\d*)', entry['comment'])
        if mult_match:
            pos_mult = float(mult_match.group(1))

        trades.append({
            'entry_time': entry['time'],
            'exit_time': exit_deal['time'],
            'direction': entry['type'],
            'entry_price': entry['price'],
            'exit_price': exit_deal['price'],
            'pnl': round(pnl, 2),
            'hold_sec': hold_sec,
            'exit_reason': exit_reason,
            'signal_type': sig_type,
            'pos_mult': pos_mult,
        })

    return trades

def analyze(label, trades):
    if not trades:
        print(f'{label}: NO TRADES')
        return None

    n = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    wr = len(wins)/n*100 if n>0 else 0
    total_pnl = sum(t['pnl'] for t in trades)
    avg_w = sum(t['pnl'] for t in wins)/len(wins) if wins else 0
    avg_l = sum(t['pnl'] for t in losses)/len(losses) if losses else 0
    wl_r = avg_w/abs(avg_l) if avg_l != 0 else 999

    print(f'\n{"="*55}')
    print(f'  {label}  ({n}T, PnL=${total_pnl:+.2f})')
    print(f'{"="*55}')

    # Exit reason distribution
    reasons = Counter(t['exit_reason'] for t in trades)
    print(f'\n  出口原因分布:')
    for r, c in reasons.most_common():
        r_trades = [t for t in trades if t['exit_reason'] == r]
        r_wr = len([t for t in r_trades if t['pnl']>0])/len(r_trades)*100 if r_trades else 0
        r_pnl = sum(t['pnl'] for t in r_trades)
        print(f'    {r:<10}: {c:>3}T ({c/n*100:>4.0f}%) WR={r_wr:>4.0f}% PnL=${r_pnl:+.2f}')

    # Hold duration analysis
    hold_buckets = {'<10s':0, '10-60s':0, '1-5min':0, '5-30min':0, '>30min':0}
    hold_pnl = defaultdict(float)
    for t in trades:
        h = t['hold_sec']
        if h < 10: k = '<10s'
        elif h < 60: k = '10-60s'
        elif h < 300: k = '1-5min'
        elif h < 1800: k = '5-30min'
        else: k = '>30min'
        hold_buckets[k] += 1
        hold_pnl[k] += t['pnl']

    print(f'\n  持仓时长分布:')
    for k in ['<10s','10-60s','1-5min','5-30min','>30min']:
        c = hold_buckets[k]
        if c > 0:
            k_trades = [t for t in trades if (
                (k=='<10s' and t['hold_sec']<10) or
                (k=='10-60s' and 10<=t['hold_sec']<60) or
                (k=='1-5min' and 60<=t['hold_sec']<300) or
                (k=='5-30min' and 300<=t['hold_sec']<1800) or
                (k=='>30min' and t['hold_sec']>=1800)
            )]
            k_wr = len([t for t in k_trades if t['pnl']>0])/len(k_trades)*100
            print(f'    {k:<8}: {c:>3}T ({c/n*100:>4.0f}%) WR={k_wr:>4.0f}% PnL=${hold_pnl[k]:+.2f}')

    # Direction analysis
    for d in ['buy', 'sell']:
        d_trades = [t for t in trades if t['direction']==d]
        if not d_trades: continue
        d_wr = len([t for t in d_trades if t['pnl']>0])/len(d_trades)*100
        d_pnl = sum(t['pnl'] for t in d_trades)
        d_reasons = Counter(t['exit_reason'] for t in d_trades)
        print(f'\n  {d.upper()} {len(d_trades)}T: WR={d_wr:.0f}% PnL=${d_pnl:+.2f} | exits: {dict(d_reasons)}')

    # Signal type analysis
    sig_types = Counter(t['signal_type'] for t in trades)
    print(f'\n  信号类型分布:')
    for st, c in sig_types.most_common():
        st_trades = [t for t in trades if t['signal_type']==st]
        st_wr = len([t for t in st_trades if t['pnl']>0])/len(st_trades)*100 if st_trades else 0
        st_pnl = sum(t['pnl'] for t in st_trades)
        print(f'    {st:<5}: {c:>3}T WR={st_wr:>4.0f}% PnL=${st_pnl:+.2f}')

    # Position multiplier analysis
    mults = defaultdict(list)
    for t in trades:
        m = round(t['pos_mult'], 1)
        mults[m].append(t)
    print(f'\n  仓位乘数分布:')
    for m in sorted(mults.keys()):
        mt = mults[m]
        m_wr = len([t for t in mt if t['pnl']>0])/len(mt)*100 if mt else 0
        m_pnl = sum(t['pnl'] for t in mt)
        print(f'    x{m:.1f}: {len(mt):>3}T WR={m_wr:>4.0f}% PnL=${m_pnl:+.2f}')

    return {
        'n':n, 'wr':wr, 'avg_w':avg_w, 'avg_l':avg_l, 'wl_r':wl_r,
        'total_pnl':total_pnl, 'trades':trades,
        'exit_reasons': dict(reasons)
    }

# ── Main ──
for htm_name, label in [
    ('smc_B_2605.htm', 'PathB 2605'),
    ('smc_S2_2605.htm', 'S2 2605'),
    ('smc_B_2505.htm', 'PathB 2505'),
    ('smc_S2_2505.htm', 'S2 2505'),
    ('smc_B_2604.htm', 'PathB 2604'),
]:
    fpath = MT5_DATA / htm_name
    if fpath.exists():
        trades = parse_deals(str(fpath))
        results = analyze(label, trades)
        if results:
            # Print worst trades
            sorted_trades = sorted(trades, key=lambda t: t['pnl'])
            print(f'\n  最差5笔:')
            for t in sorted_trades[:5]:
                print(f'    {t["entry_time"]} {t["direction"]:>4} hold={t["hold_sec"]:>5.0f}s exit={t["exit_reason"]:<8} sig={t["signal_type"]} mult=x{t["pos_mult"]:.1f} PnL=${t["pnl"]:+.2f}')
            # Print best trades
            print(f'  最佳5笔:')
            for t in sorted_trades[-5:]:
                print(f'    {t["entry_time"]} {t["direction"]:>4} hold={t["hold_sec"]:>5.0f}s exit={t["exit_reason"]:<8} sig={t["signal_type"]} mult=x{t["pos_mult"]:.1f} PnL=${t["pnl"]:+.2f}')
    else:
        print(f'MISSING: {fpath}')

print('\n[DONE]')
