#!/usr/bin/env python3
"""Deep analysis of S2 (H5+AD-LOOSE) losing months in 2026.
Compare per-trade patterns vs winning months (2504, 2505).
Goal: find preventable loss patterns for strategy optimization."""
import re, sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

MT5_DATA = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075')

def parse_trades_detailed(htm_path):
    if not htm_path.exists(): return []
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    pending = []; trades = []
    for r in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
        if len(cells) != 13: continue
        if cells[3].strip().lower() == 'balance': continue
        io = cells[4].strip().lower()
        time_str = cells[0].strip()[:19]
        direction = cells[3].strip().lower()
        price_str = cells[6].strip().replace(' ','').replace(',','')
        pnl_str = cells[10].strip().replace(' ','').replace(',','')
        comment = cells[12].strip()
        try: price = float(price_str)
        except: price = 0.0
        try: pnl = float(pnl_str)
        except: pnl = 0.0

        if 'in' in io:
            try: et = datetime.strptime(time_str, '%Y.%m.%d %H:%M:%S')
            except: et = None
            pending.append({'time': et, 'price': price, 'dir': direction, 'comment': comment})
        elif 'out' in io and pending:
            entry = pending.pop(0)
            try: xt = datetime.strptime(time_str, '%Y.%m.%d %H:%M:%S')
            except: xt = None
            hold_sec = (xt - entry['time']).total_seconds() if entry['time'] and xt else 0
            if hold_sec < 0: hold_sec = 0

            # Exit reason
            cl = comment.lower()
            if 'sl' in cl or 'stop' in cl: exit_reason = 'sl'
            elif 'be' in cl or 'breakeven' in cl: exit_reason = 'be'
            elif 'dtp' in cl: exit_reason = 'dtp'
            elif 'tp' in cl: exit_reason = 'tp'
            elif 'trail' in cl: exit_reason = 'trail'
            else: exit_reason = 'other'

            trades.append({
                'entry_time': entry['time'],
                'exit_time': xt,
                'hold_sec': hold_sec,
                'direction': entry['dir'],
                'pnl': pnl,
                'exit_reason': exit_reason,
                'entry_price': entry['price'],
                'exit_price': price,
                'hour': entry['time'].hour if entry['time'] else -1,
                'dow': entry['time'].weekday() if entry['time'] else -1,
                'day': entry['time'].day if entry['time'] else -1,
            })
    return trades


def analyze_month(trades, label):
    """Deep per-trade analysis for a single month."""
    if not trades: return None
    n = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    nw, nl = len(wins), len(losses)
    total_pnl = sum(t['pnl'] for t in trades)
    wr = nw/n*100 if n else 0

    win_pnls = sorted([t['pnl'] for t in wins])
    loss_pnls = sorted([abs(t['pnl']) for t in losses])

    # Per-trade avg
    avg_w = sum(t['pnl'] for t in wins)/nw if nw else 0
    avg_l = sum(abs(t['pnl']) for t in losses)/nl if nl else 0

    print(f"\n{'='*70}")
    print(f"  [{label}] {n}T, {nw}W/{nl}L, WR={wr:.1f}%, PnL=${total_pnl:+,.2f}")
    print(f"  avg_W=${avg_w:.2f}  avg_L=${avg_l:.2f}  W/L={avg_w/avg_l if avg_l else 0:.2f}")
    print(f"{'='*70}")

    # Exit reason breakdown
    exit_stats = defaultdict(lambda: {'count':0, 'wins':0, 'pnl':0.0})
    for t in trades:
        r = t['exit_reason']
        exit_stats[r]['count'] += 1
        if t['pnl'] > 0: exit_stats[r]['wins'] += 1
        exit_stats[r]['pnl'] += t['pnl']

    print(f"\n  --- Exit Reason ---")
    print(f"  {'Reason':<10} {'Count':>6} {'%':>5} {'WR':>6} {'PnL':>10} {'Avg':>8}")
    for reason in sorted(exit_stats.keys()):
        e = exit_stats[reason]
        wr_r = e['wins']/e['count']*100 if e['count'] else 0
        avg = e['pnl']/e['count'] if e['count'] else 0
        print(f"  {reason:<10} {e['count']:>6} {e['count']/n*100:>4.1f}% {wr_r:>5.1f}% ${e['pnl']:>+9.2f} ${avg:>+7.2f}")

    # Hold time
    w_holds = [t['hold_sec'] for t in wins if t['hold_sec'] > 0]
    l_holds = [t['hold_sec'] for t in losses if t['hold_sec'] > 0]
    if w_holds and l_holds:
        print(f"\n  --- Hold Time ---")
        print(f"  Wins:  med={sorted(w_holds)[len(w_holds)//2]:.0f}s, avg={sum(w_holds)/len(w_holds):.0f}s")
        print(f"  Losses: med={sorted(l_holds)[len(l_holds)//2]:.0f}s, avg={sum(l_holds)/len(l_holds):.0f}s")
        # Fast losses (< 30s)
        fast_losses = len([h for h in l_holds if h < 30])
        print(f"  Losses <30s: {fast_losses}/{nl} ({fast_losses/nl*100:.0f}%)")

    # Direction
    buys = [t for t in trades if t.get('direction') == 'buy']
    sells = [t for t in trades if t.get('direction') == 'sell']
    buy_wr = len([t for t in buys if t['pnl']>0])/len(buys)*100 if buys else 0
    sell_wr = len([t for t in sells if t['pnl']>0])/len(sells)*100 if sells else 0
    print(f"\n  --- Direction ---")
    print(f"  Buy:  {len(buys)}T WR={buy_wr:.1f}% PnL=${sum(t['pnl'] for t in buys):+.2f}")
    print(f"  Sell: {len(sells)}T WR={sell_wr:.1f}% PnL=${sum(t['pnl'] for t in sells):+.2f}")

    # Hourly
    hour_stats = defaultdict(list)
    for t in trades:
        if t['hour'] >= 0: hour_stats[t['hour']].append(t['pnl'])
    if hour_stats:
        print(f"\n  --- Hourly ---")
        for h in sorted(hour_stats.keys()):
            vals = hour_stats[h]
            if len(vals) >= 3:
                wr_h = len([v for v in vals if v>0])/len(vals)*100
                print(f"  H{h:02d}: {len(vals):>3}T WR={wr_h:>5.1f}% PnL=${sum(vals):>+8.0f}")

    # PnL distribution
    print(f"\n  --- PnL Distribution ---")
    if win_pnls:
        print(f"  Win:  p10=${win_pnls[len(win_pnls)//10]:.2f} p50=${win_pnls[len(win_pnls)//2]:.2f} p90=${win_pnls[len(win_pnls)*9//10]:.2f}")
    if loss_pnls:
        print(f"  Loss: p10=${loss_pnls[len(loss_pnls)//10]:.2f} p50=${loss_pnls[len(loss_pnls)//2]:.2f} p90=${loss_pnls[len(loss_pnls)*9//10]:.2f}")

    return {
        'n': n, 'nw': nw, 'nl': nl, 'wr': wr, 'total_pnl': total_pnl,
        'avg_w': avg_w, 'avg_l': avg_l, 'exit_stats': dict(exit_stats),
        'win_pnls': win_pnls, 'loss_pnls': loss_pnls,
    }


# ===== MAIN =====
print("=" * 90)
print("  2026 LOSING MONTHS: Per-Trade Deep Analysis (S2: H5+AD-LOOSE)")
print("=" * 90)

# Analyze S2 losing months
r2602 = analyze_month(parse_trades_detailed(MT5_DATA / '24m_S2_H5ADL_2602.htm'), '2602 (+$18)')
r2603 = analyze_month(parse_trades_detailed(MT5_DATA / '24m_S2_H5ADL_2603.htm'), '2603 (-$117)')
r2604 = analyze_month(parse_trades_detailed(MT5_DATA / '24m_S2_H5ADL_2604.htm'), '2604 (-$93)')
r2605 = analyze_month(parse_trades_detailed(MT5_DATA / '24m_S2_H5ADL_2605.htm'), '2605 (-$66)')

# Compare with winning months
print(f"\n{'='*90}")
print(f"  COMPARISON: Winning vs Losing Months (S2)")
print(f"{'='*90}")
r2504 = analyze_month(parse_trades_detailed(MT5_DATA / '24m_S2_H5ADL_2504.htm'), '2504 (+$11,525) WIN')
r2505 = analyze_month(parse_trades_detailed(MT5_DATA / '24m_S2_H5ADL_2505.htm'), '2505 (+$5,964) WIN')

# Cross comparison
print(f"\n{'='*90}")
print(f"  CROSS-COMPARISON: What Changed in 2026?")
print(f"{'='*90}")

print(f"\n  {'Metric':<20} {'2504 WIN':>12} {'2505 WIN':>12} {'2602':>12} {'2603':>12} {'2604':>12} {'2605':>12}")
print(f"  {'-'*90}")
for metric, key in [('Trades', 'n'), ('WR%', 'wr'), ('Total PnL', 'total_pnl'),
                     ('avg_W', 'avg_w'), ('avg_L', 'avg_l')]:
    row = f"  {metric:<20}"
    for r in [r2504, r2505, r2602, r2603, r2604, r2605]:
        if r:
            val = r[key]
            if key == 'total_pnl': row += f" ${val:>+11,.0f}"
            elif key == 'wr': row += f" {val:>10.1f}%"
            else: row += f" {val:>11.1f}" if isinstance(val, float) else f" {val:>11}"
    print(row)

# Exit reason shift
print(f"\n  --- Exit Reason Shift (2505 → 2605) ---")
for reason in ['sl', 'dtp', 'tp', 'be', 'other', 'trail']:
    pct_2505 = r2505['exit_stats'].get(reason, {}).get('count', 0) / r2505['n'] * 100 if r2505 else 0
    pct_2605 = r2605['exit_stats'].get(reason, {}).get('count', 0) / r2605['n'] * 100 if r2605 else 0
    if pct_2505 > 0 or pct_2605 > 0:
        print(f"  {reason:<10}: {pct_2505:>5.1f}% → {pct_2605:>5.1f}% (delta={pct_2605-pct_2505:+.1f}%)")

# S1 vs S2 comparison in worst month
print(f"\n{'='*90}")
print(f"  S1 vs S2 in Worst Month (2604)")
print(f"{'='*90}")
r2604_s1 = analyze_month(parse_trades_detailed(MT5_DATA / '24m_S1_H5L_2604.htm'), 'S1 2604 (-$160)')
r2604_s2_trades = parse_trades_detailed(MT5_DATA / '24m_S2_H5ADL_2604.htm')

# How many trades did S2's adaptive filter save?
if r2604_s1:
    s1_trades = r2604_s1['n']
    s2_trades = len(r2604_s2_trades)
    print(f"\n  S1 (no adaptive): {s1_trades}T, S2 (adaptive): {s2_trades}T")
    print(f"  Adaptive filtered: {s1_trades - s2_trades} trades ({ (s1_trades-s2_trades)/s1_trades*100:.0f}%)")
    print(f"  S1 loss: ${r2604_s1['total_pnl']:+,.0f}, S2 loss: ${sum(t['pnl'] for t in r2604_s2_trades):+,.0f}")
    print(f"  Adaptive saved: ${abs(r2604_s1['total_pnl']) - abs(sum(t['pnl'] for t in r2604_s2_trades)):+,.0f}")

print(f"\n[DONE]")
