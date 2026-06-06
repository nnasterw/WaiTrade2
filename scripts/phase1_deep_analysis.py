#!/usr/bin/env python3
"""Phase 1 Deep: Per-trade feature extraction with fixed parsing.
Key question: What real-time observable features differentiate big winners from losers?"""
import re, sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timedelta

MT5_DATA = Path('C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075')

# Focus on the most informative reports
REPORTS = {
    'OFF_2505':    MT5_DATA / 'nkss_REF_OFF_2505.htm',     # baseline good month
    'OFF_2605':    MT5_DATA / 'nkss_REF_OFF_2605.htm',     # baseline bad month
    'LOOSE_2505':  MT5_DATA / 'nkss_REF_LOOSE_2505.htm',   # best 2505 performer
    'LOOSE_2605':  MT5_DATA / 'nkss_REF_LOOSE_2605.htm',
    'C4_2605':     MT5_DATA / 'nkss_C4_2605.htm',          # loose noise 2605
    'C2_2605':     MT5_DATA / 'nkss_C2_2605.htm',          # strict noise 2605 (profitable)
    'A2_2505':     MT5_DATA / 'nkss_A2_2505.htm',          # moderate noise 2505
    'A2_2605':     MT5_DATA / 'nkss_A2_2605.htm',
}

def parse_time_cells(cells, idx):
    """Parse MT5 time format: '2025.05.15 14:30:02'"""
    try:
        ts = cells[idx].strip()[:19]
        return datetime.strptime(ts, '%Y.%m.%d %H:%M:%S')
    except:
        return None

def parse_float(cell_val):
    try:
        return float(cell_val.strip().replace(' ', '').replace(',', ''))
    except:
        return 0.0

def parse_trades(htm_path):
    """Extract per-trade data with fixed time/direction parsing."""
    if not htm_path.exists():
        return []

    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)

    pending = []
    trades = []

    for r in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
        if len(cells) != 13:
            continue
        if cells[3].strip().lower() == 'balance':
            continue

        io_type = cells[4].strip().lower()   # 'in' or 'in/deal' or 'out' or 'out/deal'
        time_dt = parse_time_cells(cells, 1)
        direction = cells[5].strip().lower()  # 'buy' or 'sell'
        price = parse_float(cells[7])
        pnl = parse_float(cells[10])
        comment = cells[12].strip() if len(cells) > 12 else ''

        if 'in' in io_type:
            pending.append({
                'entry_time': time_dt,
                'entry_price': price,
                'direction': direction,
                'comment_in': comment,
            })
        elif 'out' in io_type and pending:
            entry = pending.pop(0)

            # Hold time
            hold_sec = 0
            if entry['entry_time'] and time_dt:
                hold_sec = (time_dt - entry['entry_time']).total_seconds()
                if hold_sec < 0:
                    hold_sec = 0  # timezone issue

            # Exit reason from comment
            exit_reason = 'unknown'
            cl = comment.lower()
            if 'sl' in cl or 'stop' in cl:
                exit_reason = 'sl'
            elif 'be' in cl or 'breakeven' in cl:
                exit_reason = 'be'
            elif 'dtp' in cl:
                exit_reason = 'dtp'
            elif 'tp' in cl:
                exit_reason = 'tp'
            elif 'trail' in cl:
                exit_reason = 'trail'
            elif 'time' in cl or 'bar' in cl:
                exit_reason = 'timeout'
            elif 'reverse' in cl:
                exit_reason = 'reverse'
            elif 'mfe' in cl:
                exit_reason = 'mfe'

            # Price move (positive = favorable direction)
            if entry['direction'] in ('buy', 'buy_deal'):
                price_move = price - entry['entry_price']
            else:
                price_move = entry['entry_price'] - price

            # Hour and day of week
            hour = entry['entry_time'].hour if entry['entry_time'] else -1
            dow = entry['entry_time'].weekday() if entry['entry_time'] else -1  # 0=Mon
            day_of_month = entry['entry_time'].day if entry['entry_time'] else -1

            trades.append({
                'entry_time': entry['entry_time'],
                'exit_time': time_dt,
                'hold_sec': hold_sec,
                'direction': entry['direction'],
                'pnl': pnl,
                'entry_price': entry['entry_price'],
                'exit_price': price,
                'price_move': price_move,
                'exit_reason': exit_reason,
                'comment': comment,
                'hour': hour,
                'dow': dow,
                'day': day_of_month,
            })

    return trades


def percentile(arr, p):
    """p-th percentile of sorted array."""
    if not arr: return 0
    idx = int(len(arr) * p / 100)
    return sorted(arr)[min(idx, len(arr)-1)]


def analyze_deep(trades, label):
    """Deep per-trade analysis."""
    if not trades: return None

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    n = len(trades)
    nw, nl = len(wins), len(losses)
    wr = nw / n * 100 if n else 0

    total_pnl = sum(t['pnl'] for t in trades)
    gw = sum(t['pnl'] for t in wins) if wins else 0
    gl = abs(sum(t['pnl'] for t in losses)) if losses else 0

    avg_w = gw / nw if nw else 0
    avg_l = gl / nl if nl else 0

    # Win/Loss PnL distributions
    win_pnls = sorted([t['pnl'] for t in wins])
    loss_pnls = sorted([abs(t['pnl']) for t in losses])

    # Hold time distributions
    win_holds = sorted([t['hold_sec'] for t in wins if t['hold_sec'] > 0])
    loss_holds = sorted([t['hold_sec'] for t in losses if t['hold_sec'] > 0])

    # Price move distributions
    win_moves = sorted([t['price_move'] for t in wins if t['price_move'] != 0])
    loss_moves = sorted([abs(t['price_move']) for t in losses if t['price_move'] != 0])

    # Exit reason breakdown
    exit_wr = {}
    for reason in set(t['exit_reason'] for t in trades):
        rt = [t for t in trades if t['exit_reason'] == reason]
        rw = [t for t in rt if t['pnl'] > 0]
        exit_wr[reason] = {
            'count': len(rt), 'pct': len(rt)/n*100,
            'wr': len(rw)/len(rt)*100 if rt else 0,
            'total_pnl': sum(t['pnl'] for t in rt),
            'avg_pnl': sum(t['pnl'] for t in rt)/len(rt) if rt else 0,
        }

    # Hourly patterns
    hour_stats = {}
    for h in range(24):
        ht = [t for t in trades if t['hour'] == h]
        if ht:
            hw = len([t for t in ht if t['pnl'] > 0])
            hour_stats[h] = {
                'count': len(ht), 'wr': hw/len(ht)*100,
                'total_pnl': sum(t['pnl'] for t in ht),
                'avg_pnl': sum(t['pnl'] for t in ht)/len(ht) if ht else 0,
            }

    # Day of week patterns
    dow_names = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    dow_stats = {}
    for d in range(7):
        dt = [t for t in trades if t['dow'] == d]
        if dt:
            dw = len([t for t in dt if t['pnl'] > 0])
            dow_stats[d] = {
                'count': len(dt), 'wr': dw/len(dt)*100,
                'total_pnl': sum(t['pnl'] for t in dt),
            }

    # Consecutive win/loss patterns
    seq = [1 if t['pnl'] > 0 else 0 for t in trades]  # 1=win, 0=loss
    streak_wins = []
    streak_losses = []
    cur_w, cur_l = 0, 0
    for s in seq:
        if s == 1:
            cur_w += 1
            if cur_l > 0: streak_losses.append(cur_l); cur_l = 0
        else:
            cur_l += 1
            if cur_w > 0: streak_wins.append(cur_w); cur_w = 0
    if cur_w > 0: streak_wins.append(cur_w)
    if cur_l > 0: streak_losses.append(cur_l)

    # "Big winners" (> p80 of win PnL) vs "big losers" (< p20 of loss PnL)
    big_win_threshold = percentile(win_pnls, 80) if win_pnls else 0
    big_loss_threshold = percentile(loss_pnls, 80) if loss_pnls else 0
    big_winners = [t for t in wins if t['pnl'] >= big_win_threshold]
    big_losers = [t for t in losses if abs(t['pnl']) >= big_loss_threshold]

    # Print
    print(f"\n{'='*80}")
    print(f"  [{label}] {n}T {nw}W/{nl}L WR={wr:.1f}% PnL=${total_pnl:+,.2f}")
    print(f"  avg_W=${avg_w:.2f} avg_L=${avg_l:.2f} W/L_ratio={avg_w/avg_l if avg_l>0 else 0:.2f}")
    print(f"{'='*80}")

    # Hold time
    if win_holds and loss_holds:
        print(f"\n  --- Hold Time (sec) ---")
        print(f"  Wins:  p50={percentile(win_holds,50):.0f}s p90={percentile(win_holds,90):.0f}s")
        print(f"  Losses: p50={percentile(loss_holds,50):.0f}s p90={percentile(loss_holds,90):.0f}s")
        # % of losses < 5s (tick-noise kills)
        pct_lt5 = len([h for h in loss_holds if h < 5]) / len(loss_holds) * 100
        pct_lt30 = len([h for h in loss_holds if h < 30]) / len(loss_holds) * 100
        print(f"  Losses <5s: {pct_lt5:.1f}%  <30s: {pct_lt30:.1f}%")

    # Price moves
    if win_moves and loss_moves:
        print(f"\n  --- Price Move (points, favorable) ---")
        print(f"  Wins:  p50={percentile(win_moves,50):.4f} p90={percentile(win_moves,90):.4f}")
        print(f"  Losses: p50={percentile(loss_moves,50):.4f} p90={percentile(loss_moves,90):.4f}")

    # Exit reasons
    print(f"\n  --- Exit Reason ---")
    print(f"  {'Reason':<12} {'Count':>6} {'%':>5} {'WR':>6} {'TotPnL':>10} {'AvgPnL':>8}")
    for reason in sorted(exit_wr.keys()):
        e = exit_wr[reason]
        print(f"  {reason:<12} {e['count']:>6} {e['pct']:>4.1f}% {e['wr']:>5.1f}% ${e['total_pnl']:>+9.2f} ${e['avg_pnl']:>+7.2f}")

    # Hourly WR
    print(f"\n  --- Hourly WR (server time) ---")
    bad_hours = []
    good_hours = []
    for h in sorted(hour_stats.keys()):
        hs = hour_stats[h]
        bar = '#' * max(1, int(abs(hs['total_pnl']) / 10))
        sign = '+' if hs['total_pnl'] > 0 else '-'
        print(f"  H{h:02d}: {hs['count']:>4}T WR={hs['wr']:>5.1f}% PnL=${hs['total_pnl']:>+8.0f} {sign}{bar}")
        if hs['wr'] < 40 and hs['count'] >= 5:
            bad_hours.append(h)
        if hs['wr'] > 65 and hs['count'] >= 10:
            good_hours.append(h)

    # Big winners vs big losers comparison
    print(f"\n  --- Big Winners (>{big_win_threshold:.1f}) vs Big Losers (<{big_loss_threshold:.1f}) ---")
    print(f"  Big Winners: {len(big_winners)} trades, total=${sum(t['pnl'] for t in big_winners):,.0f}")
    print(f"  Big Losers:  {len(big_losers)} trades, total=${sum(t['pnl'] for t in big_losers):,.0f}")

    if big_winners and big_losers:
        bw_hours = Counter(t['hour'] for t in big_winners)
        bl_hours = Counter(t['hour'] for t in big_losers)
        bw_dow = Counter(t['dow'] for t in big_winners)
        bl_dow = Counter(t['dow'] for t in big_losers)
        print(f"  BW top hours: {bw_hours.most_common(4)}")
        print(f"  BL top hours: {bl_hours.most_common(4)}")

    # Streak analysis
    print(f"\n  --- Streak Analysis ---")
    print(f"  Win streaks:  max={max(streak_wins) if streak_wins else 0}, avg={sum(streak_wins)/len(streak_wins) if streak_wins else 0:.1f}")
    print(f"  Loss streaks: max={max(streak_losses) if streak_losses else 0}, avg={sum(streak_losses)/len(streak_losses) if streak_losses else 0:.1f}")
    # After N consecutive losses, what's the next trade WR?
    for n in [1,2,3,4]:
        post_loss_trades = []
        for i in range(len(seq)-n):
            if all(s == 0 for s in seq[i:i+n]):
                post_loss_trades.append(seq[i+n])
        if post_loss_trades:
            wr_after = sum(post_loss_trades)/len(post_loss_trades)*100
            print(f"  WR after {n} consecutive losses: {wr_after:.1f}% ({len(post_loss_trades)} samples)")

    return {
        'n': n, 'nw': nw, 'nl': nl, 'wr': wr, 'total_pnl': total_pnl,
        'avg_w': avg_w, 'avg_l': avg_l,
        'win_pnls': win_pnls, 'loss_pnls': loss_pnls,
        'exit_wr': exit_wr, 'hour_stats': hour_stats,
        'bad_hours': bad_hours, 'good_hours': good_hours,
        'big_win_threshold': big_win_threshold,
        'big_loss_threshold': big_loss_threshold,
    }


# ===== MAIN =====
print("PHASE 1 DEEP: Per-Trade Feature Extraction")
print("="*100)

r_off_25 = analyze_deep(parse_trades(REPORTS['OFF_2505']), 'QS3-OFF 2505 (good)')
r_off_26 = analyze_deep(parse_trades(REPORTS['OFF_2605']), 'QS3-OFF 2605 (bad)')
r_loose_25 = analyze_deep(parse_trades(REPORTS['LOOSE_2505']), 'REF_LOOSE 2505 (+$6,691)')
r_loose_26 = analyze_deep(parse_trades(REPORTS['LOOSE_2605']), 'REF_LOOSE 2605 (-$112)')
r_c4_26 = analyze_deep(parse_trades(REPORTS['C4_2605']), 'C4 2605 loose(-$56, a=0.22)')
r_c2_26 = analyze_deep(parse_trades(REPORTS['C2_2605']), 'C2 2605 strict(+$5, a=0.14)')

# ===== CROSS-COMPARISON =====
print(f"\n{'='*100}")
print(f"  CROSS-COMPARISON: What separates wins from losses?")
print(f"{'='*100}")

for label, r in [('2505 OFF', r_off_25), ('2605 OFF', r_off_26)]:
    if not r: continue
    print(f"\n  [{label}]")
    # Win PnL distribution
    if r['win_pnls']:
        print(f"  Win PnL:  p10=${percentile(r['win_pnls'],10):.2f} p50=${percentile(r['win_pnls'],50):.2f} "
              f"p90=${percentile(r['win_pnls'],90):.2f} p95=${percentile(r['win_pnls'],95):.2f}")
    if r['loss_pnls']:
        print(f"  Loss PnL: p10=${percentile(r['loss_pnls'],10):.2f} p50=${percentile(r['loss_pnls'],50):.2f} "
              f"p90=${percentile(r['loss_pnls'],90):.2f} p95=${percentile(r['loss_pnls'],95):.2f}")
    if r['bad_hours']:
        print(f"  Bad hours (WR<40%): {r['bad_hours']}")
    if r['good_hours']:
        print(f"  Good hours (WR>65%): {r['good_hours']}")

# Key insight: what % of winning PnL comes from big winners?
print(f"\n{'='*80}")
print(f"  BIG WINNER CONTRIBUTION (what % of total profit from top 20% of wins?)")
print(f"{'='*80}")
for label, r in [('2505 OFF', r_off_25), ('2605 OFF', r_off_26),
                  ('LOOSE 2505', r_loose_25), ('LOOSE 2605', r_loose_26),
                  ('C2 2605', r_c2_26)]:
    if not r or not r['win_pnls']: continue
    thresh = r['big_win_threshold']
    bigs = [p for p in r['win_pnls'] if p >= thresh]
    big_contrib = sum(bigs) / sum(r['win_pnls']) * 100 if r['win_pnls'] else 0
    print(f"  {label:<18}: {len(bigs)}/{r['nw']} big wins (>{thresh:.1f}) = {big_contrib:.0f}% of total win PnL")

print(f"\n[DONE - Phase 1 Deep]")
