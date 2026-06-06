#!/usr/bin/env python3
"""Deep loss analysis: direction-hour patterns, loss clustering, price levels,
S1 vs S2 comparison to understand what the adaptive filter saves."""
import re, sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta

MT5_DATA = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075')

def parse_trades_full(htm_path):
    if not htm_path.exists(): return []
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    pending = []; trades = []
    for r in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
        if len(cells) != 13: continue
        if cells[3].strip().lower() == 'balance': continue
        io = cells[4].strip().lower()
        t_str = cells[0].strip()[:19]
        direction = cells[3].strip().lower()
        price_str = cells[6].strip().replace(' ','').replace(',','')
        pnl_str = cells[10].strip().replace(' ','').replace(',','')
        comment = cells[12].strip()
        try: price = float(price_str)
        except: price = 0.0
        try: pnl = float(pnl_str)
        except: pnl = 0.0

        if 'in' in io:
            try: et = datetime.strptime(t_str, '%Y.%m.%d %H:%M:%S')
            except: et = None
            pending.append({'time': et, 'price': price, 'dir': direction, 'comment': comment})
        elif 'out' in io and pending:
            entry = pending.pop(0)
            try: xt = datetime.strptime(t_str, '%Y.%m.%d %H:%M:%S')
            except: xt = None
            hold_sec = (xt - entry['time']).total_seconds() if entry['time'] and xt else 0
            if hold_sec < 0: hold_sec = 0

            cl = comment.lower()
            if 'sl' in cl or 'stop' in cl: exit_reason = 'sl'
            elif 'be' in cl or 'breakeven' in cl: exit_reason = 'be'
            elif 'dtp' in cl: exit_reason = 'dtp'
            elif 'tp' in cl: exit_reason = 'tp'
            else: exit_reason = 'other'

            # Price move direction (positive = favorable)
            if entry['dir'] in ('buy',):
                price_move = price - entry['price']
            else:
                price_move = entry['price'] - price

            trades.append({
                'entry_time': entry['time'],
                'exit_time': xt,
                'hold_sec': hold_sec,
                'direction': entry['dir'],
                'pnl': pnl,
                'exit_reason': exit_reason,
                'entry_price': entry['price'],
                'exit_price': price,
                'price_move': price_move,
                'hour': entry['time'].hour if entry['time'] else -1,
                'dow': entry['time'].weekday() if entry['time'] else -1,
                'day': entry['time'].day if entry['time'] else -1,
                'comment_in': entry['comment'],
            })
    return trades


def analyze_losses_deep(trades, label):
    """Deep loss analysis: what do losing trades look like?"""
    losses = [t for t in trades if t['pnl'] <= 0]
    wins = [t for t in trades if t['pnl'] > 0]
    nl = len(losses); nw = len(wins)
    if nl == 0: return

    total_loss = sum(t['pnl'] for t in losses)
    avg_l = abs(total_loss) / nl

    print(f"\n{'='*70}")
    print(f"  [{label}] LOSSES: {nl}T, total=${total_loss:+,.0f}, avg=${avg_l:.2f}")
    print(f"{'='*70}")

    # 1. Direction of losses
    buy_losses = [t for t in losses if t.get('direction') == 'buy']
    sell_losses = [t for t in losses if t.get('direction') == 'sell']
    print(f"\n  Direction: Buy={len(buy_losses)}T/${sum(t['pnl'] for t in buy_losses):+.0f}, "
          f"Sell={len(sell_losses)}T/${sum(t['pnl'] for t in sell_losses):+.0f}")

    # 2. Exit reason of losses
    reason_stats = defaultdict(lambda: {'count':0, 'pnl':0.0})
    for t in losses:
        r = t['exit_reason']
        reason_stats[r]['count'] += 1
        reason_stats[r]['pnl'] += t['pnl']
    print(f"\n  Exit Reasons:")
    for r in sorted(reason_stats.keys()):
        s = reason_stats[r]
        print(f"    {r:<8}: {s['count']:>4}T ${s['pnl']:>+9.2f} ({s['count']/nl*100:.0f}% of losses)")

    # 3. Hold time of losses
    l_holds = sorted([t['hold_sec'] for t in losses if t['hold_sec'] > 0])
    if l_holds:
        print(f"\n  Hold Time: p10={l_holds[len(l_holds)//10]:.0f}s p50={l_holds[len(l_holds)//2]:.0f}s "
              f"p90={l_holds[len(l_holds)*9//10]:.0f}s")
        fast = len([h for h in l_holds if h < 10])
        print(f"  Ultra-fast (<10s): {fast}/{nl} ({fast/nl*100:.0f}%) — tick noise kills")
        medium = len([h for h in l_holds if 10 <= h < 60])
        print(f"  Fast (10-60s): {medium}/{nl} ({medium/nl*100:.0f}%) — micro reversals")
        slow = len([h for h in l_holds if h >= 300])
        print(f"  Slow (>5min): {slow}/{nl} ({slow/nl*100:.0f}%) — trend failures")

    # 4. Hourly pattern of losses
    hour_losses = defaultdict(list)
    for t in losses:
        if t['hour'] >= 0:
            hour_losses[t['hour']].append(t['pnl'])
    hour_all = defaultdict(list)
    for t in trades:
        if t['hour'] >= 0:
            hour_all[t['hour']].append(t['pnl'])

    print(f"\n  Worst Hours (by loss PnL):")
    ranked = sorted(hour_losses.items(), key=lambda x: sum(x[1]))
    for h, pnls in ranked[:5]:
        if len(pnls) >= 3:
            all_t = hour_all.get(h, [])
            all_wr = len([p for p in all_t if p > 0])/len(all_t)*100 if all_t else 0
            print(f"    H{h:02d}: {len(pnls)} losses/${sum(pnls):+.0f}, all={len(all_t)}T WR={all_wr:.0f}%")

    # 5. DOW pattern
    dow_losses = defaultdict(list)
    for t in losses:
        if 0 <= t['dow'] <= 4:
            dow_losses[t['dow']].append(t['pnl'])
    dow_names = ['Mon','Tue','Wed','Thu','Fri']
    print(f"\n  DOW Loss Pattern:")
    for d in range(5):
        pnls = dow_losses.get(d, [])
        if pnls:
            print(f"    {dow_names[d]}: {len(pnls)} losses/${sum(pnls):+.0f}")

    # 6. Sequential clustering: do losses cluster?
    seq = [0 if t['pnl'] <= 0 else 1 for t in trades]
    loss_streaks = []
    cur = 0
    for s in seq:
        if s == 0: cur += 1
        else:
            if cur > 0: loss_streaks.append(cur); cur = 0
    if cur > 0: loss_streaks.append(cur)

    if loss_streaks:
        print(f"\n  Loss Streaks: max={max(loss_streaks)}, avg={sum(loss_streaks)/len(loss_streaks):.1f}")
        # Distribution
        streak_dist = Counter(loss_streaks)
        for k in sorted(streak_dist.keys()):
            print(f"    {k}-loss streak: {streak_dist[k]}x")

    # 7. Price level analysis: do losses cluster around specific price levels?
    # Look at entry prices of consecutive losses
    loss_prices = [t['entry_price'] for t in losses]
    if len(loss_prices) >= 3:
        # Check if consecutive losses are at similar prices (within 0.2%)
        same_level_losses = 0
        for i in range(1, len(loss_prices)):
            if abs(loss_prices[i] - loss_prices[i-1]) / loss_prices[i-1] < 0.002:
                same_level_losses += 1
        print(f"\n  Same-level consecutive losses (<0.2% price diff): {same_level_losses}/{len(loss_prices)-1}")

    # 8. Loss magnitude distribution
    loss_mags = sorted([abs(t['pnl']) for t in losses])
    if loss_mags:
        print(f"\n  Loss Magnitude: p10=${loss_mags[len(loss_mags)//10]:.2f} p50=${loss_mags[len(loss_mags)//2]:.2f} "
              f"p90=${loss_mags[len(loss_mags)*9//10]:.2f}")

    return losses


# ===== MAIN =====
print("=" * 90)
print("  DEEP LOSS ANALYSIS: 2026 Losing Months (S2: H5+AD-LOOSE)")
print("=" * 90)

# All four losing months
s2_2602 = parse_trades_full(MT5_DATA / '24m_S2_H5ADL_2602.htm')
s2_2603 = parse_trades_full(MT5_DATA / '24m_S2_H5ADL_2603.htm')
s2_2604 = parse_trades_full(MT5_DATA / '24m_S2_H5ADL_2604.htm')
s2_2605 = parse_trades_full(MT5_DATA / '24m_S2_H5ADL_2605.htm')

# Winning months for comparison
s2_2504 = parse_trades_full(MT5_DATA / '24m_S2_H5ADL_2504.htm')
s2_2505 = parse_trades_full(MT5_DATA / '24m_S2_H5ADL_2505.htm')

# Analyze each
for label, trades in [('2602 +$18', s2_2602), ('2603 -$117', s2_2603),
                       ('2604 -$93', s2_2604), ('2605 -$66', s2_2605)]:
    analyze_losses_deep(trades, label)

# Cross-comparison: losses in winning vs losing months
print(f"\n{'='*90}")
print(f"  CROSS-COMPARISON: Loss Characteristics — Winning vs Losing Months")
print(f"{'='*90}")

for label, trades in [('2504 WIN', s2_2504), ('2505 WIN', s2_2505),
                       ('2603 WORST', s2_2603), ('2604 BAD', s2_2604)]:
    losses = [t for t in trades if t['pnl'] <= 0]
    wins = [t for t in trades if t['pnl'] > 0]
    if not losses: continue

    l_holds = [t['hold_sec'] for t in losses if t['hold_sec'] > 0]
    w_holds = [t['hold_sec'] for t in wins if t['hold_sec'] > 0]

    # Exit reason of losses
    sl_losses = len([t for t in losses if t['exit_reason'] == 'sl'])
    dtp_losses_impossible = len([t for t in losses if t['exit_reason'] == 'dtp'])  # DTP should never lose

    print(f"\n  [{label}]")
    print(f"    Losses: {len(losses)}T, avg_L=${sum(abs(t['pnl']) for t in losses)/len(losses):.2f}")
    print(f"    SL as loss exit: {sl_losses}/{len(losses)} ({sl_losses/len(losses)*100:.0f}%)")
    if l_holds:
        print(f"    Loss hold: p50={sorted(l_holds)[len(l_holds)//2]:.0f}s")
    if w_holds:
        print(f"    Win hold:  p50={sorted(w_holds)[len(w_holds)//2]:.0f}s")
    # Buy vs sell loss ratio
    buy_l = [t for t in losses if t.get('direction')=='buy']
    sell_l = [t for t in losses if t.get('direction')=='sell']
    print(f"    Buy losses: {len(buy_l)}T/${sum(t['pnl'] for t in buy_l):+.0f}, "
          f"Sell losses: {len(sell_l)}T/${sum(t['pnl'] for t in sell_l):+.0f}")

# S1 vs S2: What did the adaptive filter save?
print(f"\n{'='*90}")
print(f"  S1 vs S2: Adaptive Filter Impact on Losses")
print(f"{'='*90}")

for month, mlabel in [('2604','Worst'), ('2605','Last')]:
    s1_trades = parse_trades_full(MT5_DATA / f'24m_S1_H5L_{month}.htm')
    s2_trades = parse_trades_full(MT5_DATA / f'24m_S2_H5ADL_{month}.htm')

    s1_losses = len([t for t in s1_trades if t['pnl'] <= 0])
    s2_losses = len([t for t in s2_trades if t['pnl'] <= 0])
    s1_loss_pnl = sum(t['pnl'] for t in s1_trades if t['pnl'] <= 0)
    s2_loss_pnl = sum(t['pnl'] for t in s2_trades if t['pnl'] <= 0)

    print(f"\n  [{mlabel} {month}]")
    print(f"    S1 (no adaptive): {len(s1_trades)}T, {s1_losses} losses/${s1_loss_pnl:+.0f}")
    print(f"    S2 (adaptive):    {len(s2_trades)}T, {s2_losses} losses/${s2_loss_pnl:+.0f}")
    print(f"    Trades filtered:  {len(s1_trades)-len(s2_trades)}")
    print(f"    Losses avoided:   {s1_losses-s2_losses}")
    print(f"    Loss $ saved:     ${abs(s1_loss_pnl)-abs(s2_loss_pnl):+.0f}")
    # Efficiency: $ saved per trade filtered
    filtered = len(s1_trades)-len(s2_trades)
    if filtered > 0:
        efficiency = (abs(s1_loss_pnl)-abs(s2_loss_pnl)) / filtered
        print(f"    Efficiency:       ${efficiency:+.2f} saved per filtered trade")

    # S1 losses by exit reason vs S2
    s1_sl = len([t for t in s1_trades if t['pnl']<=0 and t['exit_reason']=='sl'])
    s2_sl = len([t for t in s2_trades if t['pnl']<=0 and t['exit_reason']=='sl'])
    print(f"    SL losses: S1={s1_sl} → S2={s2_sl} (filtered {s1_sl-s2_sl})")

print(f"\n[DONE]")
