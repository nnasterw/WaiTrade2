#!/usr/bin/env python3
"""Phase 1: Order-level feature analysis for QS3 OFF (2505 + 2605).
Extracts per-trade observable characteristics: pos_mult, exit_reason, hold_time, R-multiple.
NO monthly/hour grouping — only trade-level features."""
from pathlib import Path
import re, statistics
from collections import defaultdict, Counter
from datetime import datetime

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
FILES = {
    '2505': DATA / 'bt6x5_qs3_2025-05.htm',
    '2605': DATA / 'bt6x5_26_qs3_2026-05.htm',
}

def parse_trades(htm_path):
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows_raw = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    pending = []; trades = []
    for row_html in rows_raw:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html)
        if len(cells) != 13: continue
        ct = cells[3].strip()
        if ct == 'balance': continue
        io = cells[4].strip()
        try: pnl = float(cells[10].strip().replace(' ','').replace(',',''))
        except: pnl = 0.0
        if io == 'in':
            pending.append({
                'time': cells[0].strip(), 'dir': ct,
                'price': float(cells[6].strip()) if cells[6].strip() else 0,
                'lot': float(cells[5].strip()) if cells[5].strip() else 0.01,
                'comment': cells[12].strip(),
            })
        elif io == 'out' and pending:
            entry = pending.pop(0)
            et = parse_dt(entry['time']); xt = parse_dt(cells[0].strip())
            hold = (xt - et).total_seconds() if et and xt else 0
            exit_comment = cells[12].strip()
            # Parse entry comment for position multiplier
            pos_mult = 1.0
            em = entry['comment'] if entry['comment'] else ''
            xm = re.search(r'x([\d.]+)', em)
            if xm: pos_mult = float(xm.group(1))

            trades.append({
                'pnl': pnl, 'hold_sec': hold, 'direction': entry['dir'],
                'entry_time': entry['time'], 'exit_time': cells[0].strip(),
                'entry_comment': em, 'exit_comment': exit_comment,
                'pos_mult': pos_mult, 'lot': entry['lot'],
            })
    return trades

def parse_dt(s):
    try:
        parts = s.split(); d = parts[0].split('.'); t = parts[1].split(':')
        return datetime(int(d[0]),int(d[1]),int(d[2]),int(t[0]),int(t[1]),int(t[2]))
    except: return None

def classify_exit(comment, hold_sec):
    c = (comment or '').lower()
    if 'be' in c: return 'BE'
    if 'sl' in c:
        if hold_sec < 10: return 'SL<10s'
        if hold_sec < 60: return 'SL<1m'
        if hold_sec < 300: return 'SL<5m'
        return 'SL>5m'
    if 'tp' in c: return 'TP'
    if 'dtp' in c: return 'DTP'
    if 'mfe' in c: return 'MFE_FAIL'
    if 'decay' in c: return 'DECAY'
    if 'time' in c: return 'TIMEOUT'
    if 'reverse' in c: return 'REVERSE'
    return 'OTHER'

# ===== LOAD =====
all_trades = {}
for label, path in FILES.items():
    t = parse_trades(path)
    all_trades[label] = t
    print(f"Loaded {label}: {len(t)}T")

# ===== 1. Exit reason + hold time for all trades (NO month grouping) =====
print(f"\n{'='*70}")
print(f"  1. Exit Reason x Hold Time (ALL trades, NO month split)")
print(f"{'='*70}")

all_combined = all_trades['2505'] + all_trades['2605']
for t in all_combined: t['exit_cat'] = classify_exit(t['exit_comment'], t['hold_sec'])

losses = [t for t in all_combined if t['pnl'] < 0]
wins = [t for t in all_combined if t['pnl'] > 0]

print(f"\n  Total: {len(all_combined)}T, Losses: {len(losses)}, Wins: {len(wins)}")

print(f"\n  Loss Exit Reasons (ALL):")
lec = Counter(t['exit_cat'] for t in losses)
for reason, cnt in lec.most_common(8):
    subset = [t for t in losses if t['exit_cat'] == reason]
    avg_p = sum(t['pnl'] for t in subset)/cnt
    mid_h = statistics.median([t['hold_sec'] for t in subset])
    print(f"    {reason:<12} {cnt:>5}T ({cnt/len(losses)*100:>5.1f}%)  "
          f"avg_L=${avg_p:>7.2f}  mid_hold={mid_h:.0f}s")

print(f"\n  Win Exit Reasons (ALL):")
wec = Counter(t['exit_cat'] for t in wins)
for reason, cnt in wec.most_common(6):
    subset = [t for t in wins if t['exit_cat'] == reason]
    avg_p = sum(t['pnl'] for t in subset)/cnt if cnt else 0
    mid_h = statistics.median([t['hold_sec'] for t in subset]) if subset else 0
    print(f"    {reason:<12} {cnt:>5}T ({cnt/len(wins)*100:>5.1f}%)  "
          f"avg_W=${avg_p:>7.2f}  mid_hold={mid_h:.0f}s")

# ===== 2. Hold-time-based loss diagnosis =====
print(f"\n{'='*70}")
print(f"  2. Hold-Time Loss Diagnosis (Skill 1.2)")
print(f"{'='*70}")

buckets = [
    ('<10s (noise kill)', lambda s: s < 10),
    ('10-60s (micro-counter)', lambda s: 10 <= s < 60),
    ('1-5m (entry depth)', lambda s: 60 <= s < 300),
    ('5-30m (direction ok)', lambda s: 300 <= s < 1800),
    ('>30m (trend)', lambda s: s >= 1800),
]

for label, cond in buckets:
    sub = [t for t in losses if cond(t['hold_sec'])]
    if not sub: continue
    avg_l = sum(t['pnl'] for t in sub)/len(sub)
    print(f"\n  {label}: {len(sub)}T ({len(sub)/len(losses)*100:.1f}% of losses)")
    print(f"    avg_L=${avg_l:.2f}  mid_hold={statistics.median([t['hold_sec'] for t in sub]):.0f}s")

    # What should be done?
    if label == '<10s (noise kill)' and len(sub)/len(losses) > 0.15:
        print(f"    -> DIAGNOSIS: Noise kill > 15%. Action: widen SL buffer or add confirm ticks")
    elif label == '10-60s (micro-counter)' and len(sub)/len(losses) > 0.3:
        print(f"    -> DIAGNOSIS: Micro-counter-trend. Action: check HTF alignment, tighten entry")
    elif label in ('1-5m (entry depth)', '5-30m (direction ok)') and avg_l < -sum(t['pnl'] for t in wins)/len(wins)*0.8 if wins else 0:
        print(f"    -> DIAGNOSIS: avg_L > avg_W. Structural -W/L ratio problem.")

# ===== 3. Position Multiplier vs WR (EA's own quality assessment) =====
print(f"\n{'='*70}")
print(f"  3. Position Multiplier vs Outcome (EA self-assessment)")
print(f"{'='*70}")

# Group by pos_mult buckets
pm_buckets = defaultdict(lambda: {'trades':[], 'wins':0, 'pnl':0})
for t in all_combined:
    pm = t['pos_mult']
    # Bucket: <0.5, 0.5-0.7, 0.7-1.0, 1.0-2.0, >2.0
    if pm < 0.5: key = '<0.5 (low conf)'
    elif pm < 0.7: key = '0.5-0.7'
    elif pm < 1.0: key = '0.7-1.0'
    elif pm < 2.0: key = '1.0-2.0'
    else: key = '>2.0 (high conf)'
    pm_buckets[key]['trades'].append(t)
    pm_buckets[key]['pnl'] += t['pnl']
    if t['pnl'] > 0: pm_buckets[key]['wins'] += 1

print(f"\n  EA's pos_mult vs actual WR (should be monotonic if EA is calibrated):")
prev_wr = None
for key in ['<0.5 (low conf)', '0.5-0.7', '0.7-1.0', '1.0-2.0', '>2.0 (high conf)']:
    b = pm_buckets.get(key)
    if not b or not b['trades']: continue
    wr = b['wins']/len(b['trades'])*100
    avg_p = b['pnl']/len(b['trades'])
    arrow = ''
    if prev_wr is not None:
        if wr > prev_wr: arrow = ' (monotonic)'
        elif wr < prev_wr: arrow = ' (REVERSED - EA miscalibrated!)'
    print(f"    {key:<20} {len(b['trades']):>5}T  WR={wr:>5.1f}%  avg_PnL=${avg_p:>+7.2f}{arrow}")
    prev_wr = wr

# ===== 4. W/L Ratio analysis =====
print(f"\n{'='*70}")
print(f"  4. W/L Ratio and R-multiple Distribution")
print(f"{'='*70}")

for label in ['2505', '2605']:
    trades = all_trades[label]
    w = [t for t in trades if t['pnl'] > 0]
    l = [t for t in trades if t['pnl'] < 0]
    if not w or not l: continue
    avg_w = sum(t['pnl'] for t in w)/len(w)
    avg_l = abs(sum(t['pnl'] for t in l)/len(l))
    wl = avg_w/avg_l
    wr = len(w)/len(trades)*100

    # R-multiple distribution for wins
    # Use avg_loss as approximate 1R
    r_wins = [t['pnl']/avg_l for t in w]
    r_losses = [abs(t['pnl'])/avg_l for t in l]

    micro_wins = sum(1 for r in r_wins if r < 0.5)
    big_wins = sum(1 for r in r_wins if r > 3)

    print(f"\n  {label}: {len(trades)}T  WR={wr:.1f}%  avg_W=${avg_w:.2f}  avg_L=${avg_l:.2f}  W/L={wl:.2f}x")
    print(f"    盈利R分布: micro(<0.5R)={micro_wins}T ({micro_wins/len(w)*100:.0f}%)  "
          f"big(>3R)={big_wins}T ({big_wins/len(w)*100:.0f}%)  "
          f"median={statistics.median(r_wins):.2f}R")
    print(f"    亏损R分布: median={statistics.median(r_losses):.2f}R  "
          f"max={max(r_losses):.2f}R")
    if wl < 0.8:
        print(f"    -> DIAGNOSIS: W/L<0.8, structural negative expectancy. "
              f"Need {1/(wl+1)*100:.0f}%+ WR to break even (current: {wr:.0f}%)")
    elif wl < 1.2:
        print(f"    -> DIAGNOSIS: W/L~1.0, relies purely on WR. WR>{100/(1+wl):.0f}% needed.")

# ===== 5. Direction asymmetry =====
print(f"\n{'='*70}")
print(f"  5. Direction Bias (Buy vs Sell asymmetry)")
print(f"{'='*70}")

for label in ['2505', '2605']:
    trades = all_trades[label]
    for d in ['buy', 'sell']:
        sub = [t for t in trades if t['direction'] == d]
        if not sub: continue
        sub_w = [t for t in sub if t['pnl'] > 0]
        sub_l = [t for t in sub if t['pnl'] < 0]
        wr = len(sub_w)/len(sub)*100
        pnl = sum(t['pnl'] for t in sub)
        avg_w = sum(t['pnl'] for t in sub_w)/len(sub_w) if sub_w else 0
        avg_l = abs(sum(t['pnl'] for t in sub_l)/len(sub_l)) if sub_l else 0
        wl = avg_w/avg_l if avg_l else 999
        print(f"  {label} {d.upper():<5} {len(sub):>4}T  WR={wr:>5.1f}%  "
              f"avg_W=${avg_w:>6.2f}  avg_L=${avg_l:>6.2f}  W/L={wl:.2f}x  PnL=${pnl:+.2f}")

# ===== 6. Loss exit mechanism details =====
print(f"\n{'='*70}")
print(f"  6. Exit Mechanism Efficiency")
print(f"{'='*70}")

for label in ['2505', '2605']:
    trades = all_trades[label]
    exits = defaultdict(lambda: {'count':0,'pnl':0,'wins':0,'hold_sum':0})
    for t in trades:
        ec = classify_exit(t['exit_comment'], t['hold_sec'])
        exits[ec]['count'] += 1
        exits[ec]['pnl'] += t['pnl']
        exits[ec]['hold_sum'] += t['hold_sec']
        if t['pnl'] > 0: exits[ec]['wins'] += 1

    print(f"\n  {label}:")
    for ec in sorted(exits.keys()):
        d = exits[ec]
        wr = d['wins']/d['count']*100 if d['count'] else 0
        avg_h = d['hold_sum']/d['count'] if d['count'] else 0
        print(f"    {ec:<12} {d['count']:>5}T  WR={wr:>5.1f}%  "
              f"PnL=${d['pnl']:>+9.2f}  avg_hold={avg_h:.0f}s")

# ===== 7. Consecutive loss pattern =====
print(f"\n{'='*70}")
print(f"  7. Consecutive Loss Pattern (Skill: cooldown analysis)")
print(f"{'='*70}")

for label in ['2505', '2605']:
    trades = sorted(all_trades[label], key=lambda t: t['exit_time'])
    cl_runs = []; cur = 0; max_cl = 0
    cl_pnl_tot = 0
    for t in trades:
        if t['pnl'] < 0:
            cur += 1; max_cl = max(max_cl, cur); cl_pnl_tot += t['pnl']
        else:
            if cur > 0: cl_runs.append(cur)
            cur = 0
    if cur > 0: cl_runs.append(cur)
    cl_dist = Counter(cl_runs)
    print(f"\n  {label}: MaxCL={max_cl}, total_cl={sum(cl_runs)}, "
          f"avg_cl_len={sum(cl_runs)/len(cl_runs):.1f}" if cl_runs else f"  {label}: no losses")
    print(f"    连亏长度分布: {dict(sorted(cl_dist.items())[:8])}")
    # What would cooldown after N losses save?
    for n in [3, 5]:
        saved = 0
        for rlen in cl_runs:
            if rlen > n:
                # Trades after position n in a run of length rlen are "excess"
                pass  # Need individual trade tracking
        total_cl_pnl = sum(t['pnl'] for t in trades if t['pnl'] < 0)
        print(f"    After {n} consecutive losses: total loss PnL = ${total_cl_pnl:.2f} "
              f"(would need per-trade run tracking for exact savings)")

print(f"\n[DONE]")
