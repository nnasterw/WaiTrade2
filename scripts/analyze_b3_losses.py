#!/usr/bin/env python3
"""B3 2605 loss pattern analysis: per-trade features for adaptive noise gate design."""
from pathlib import Path
import re, statistics
from collections import defaultdict, Counter
from datetime import datetime

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')

# Find B3 reports
import os
for f in sorted(os.listdir(str(DATA))):
    if 'B3' in f and f.endswith('.htm'):
        print(f"Found: {f}")

# Also check for up1 prefix
B3_2605 = None
B3_2505 = None
for f in sorted(os.listdir(str(DATA))):
    if ('B3_HTFA' in f or 'B3_HTF' in f) and f.endswith('.htm'):
        if '2605' in f: B3_2605 = DATA / f
        if '2505' in f: B3_2505 = DATA / f
    if ('uf_B3' in f) and f.endswith('.htm'):
        if '2605' in f: B3_2605 = DATA / f
        if '2505' in f: B3_2505 = DATA / f

print(f"\nB3 2605: {B3_2605}")
print(f"B3 2505: {B3_2505}")

if not B3_2605:
    # Try broader search
    for f in sorted(os.listdir(str(DATA))):
        if ('_B3' in f or 'B3_' in f) and f.endswith('.htm') and '2605' in f:
            B3_2605 = DATA / f
            print(f"Found B3 2605 (broad): {f}")
            break

if not B3_2605:
    print("B3 2605 report not found! Listing all .htm files...")
    for f in sorted(os.listdir(str(DATA))):
        if f.endswith('.htm') and '2605' in f:
            print(f"  {f}")
    exit(1)

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
                'lot': float(cells[5].strip()) if cells[5].strip() else 0.01,
                'comment': cells[12].strip(),
            })
        elif io == 'out' and pending:
            entry = pending.pop(0)
            et = parse_dt(entry['time']); xt = parse_dt(cells[0].strip())
            hold = (xt - et).total_seconds() if et and xt else 0
            trades.append({
                'pnl': pnl, 'hold_sec': hold, 'direction': entry['dir'],
                'entry_time': entry['time'], 'exit_time': cells[0].strip(),
                'entry_comment': entry['comment'], 'exit_comment': cells[12].strip(),
                'lot': entry['lot'],
            })
    return trades

def parse_dt(s):
    try:
        parts = s.split(); d = parts[0].split('.'); t = parts[1].split(':')
        return datetime(int(d[0]),int(d[1]),int(d[2]),int(t[0]),int(t[1]),int(t[2]))
    except: return None

def exit_reason(comment, hold_sec):
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
    return 'OTHER'

# ===== LOAD =====
trades_2605 = parse_trades(B3_2605)
print(f"\nB3 2605: {len(trades_2605)} trades parsed")

wins = [t for t in trades_2605 if t['pnl'] > 0]
losses = [t for t in trades_2605 if t['pnl'] < 0]

# ===== 1. Exit reason + hold time =====
print(f"\n{'='*70}")
print(f"  1. B3 2605 Loss Exit Reasons + Hold Time")
print(f"{'='*70}")

for t in trades_2605: t['exit_cat'] = exit_reason(t['exit_comment'], t['hold_sec'])

lec = Counter(t['exit_cat'] for t in losses)
wec = Counter(t['exit_cat'] for t in wins)

print(f"\n  Losses ({len(losses)}T):")
for reason, cnt in lec.most_common(8):
    sub = [t for t in losses if t['exit_cat'] == reason]
    avg_p = sum(t['pnl'] for t in sub)/cnt
    mid_h = statistics.median([t['hold_sec'] for t in sub])
    print(f"    {reason:<12} {cnt:>4}T ({cnt/len(losses)*100:>5.1f}%)  "
          f"avg_L=${avg_p:>7.2f}  mid_hold={mid_h:.0f}s")

print(f"\n  Wins ({len(wins)}T):")
for reason, cnt in wec.most_common(6):
    sub = [t for t in wins if t['exit_cat'] == reason]
    avg_p = sum(t['pnl'] for t in sub)/cnt if cnt else 0
    mid_h = statistics.median([t['hold_sec'] for t in sub]) if sub else 0
    print(f"    {reason:<12} {cnt:>4}T ({cnt/len(wins)*100:>5.1f}%)  "
          f"avg_W=${avg_p:>7.2f}  mid_hold={mid_h:.0f}s")

# ===== 2. W/L ratio =====
avg_w = sum(t['pnl'] for t in wins)/len(wins) if wins else 0
avg_l = abs(sum(t['pnl'] for t in losses)/len(losses)) if losses else 0
wl = avg_w/avg_l if avg_l else 999
print(f"\n  W/L ratio: avg_W=${avg_w:.2f} / avg_L=${avg_l:.2f} = {wl:.2f}x")
print(f"  WR={len(wins)/len(trades_2605)*100:.1f}%  "
      f"Break-even WR needed: {1/(1+wl)*100:.0f}%")

# ===== 3. Hold time buckets for losses =====
print(f"\n{'='*70}")
print(f"  2. Loss Hold-Time Buckets (for adaptive noise timing)")
print(f"{'='*70}")

buckets = [
    ('<5s', lambda s: s < 5),
    ('5-10s', lambda s: 5 <= s < 10),
    ('10-30s', lambda s: 10 <= s < 30),
    ('30-60s', lambda s: 30 <= s < 60),
    ('1-5m', lambda s: 60 <= s < 300),
    ('5-30m', lambda s: 300 <= s < 1800),
    ('>30m', lambda s: s >= 1800),
]

for label, cond in buckets:
    sub_l = [t for t in losses if cond(t['hold_sec'])]
    sub_w = [t for t in wins if cond(t['hold_sec'])]
    if not sub_l and not sub_w: continue
    print(f"\n  {label}: {len(sub_l)}L + {len(sub_w)}W")
    if sub_l:
        avg_pl = sum(t['pnl'] for t in sub_l)/len(sub_l)
        print(f"    Losses: avg=${avg_pl:.2f}  exits: {Counter(t['exit_cat'] for t in sub_l).most_common(3)}")
    if sub_w:
        avg_pw = sum(t['pnl'] for t in sub_w)/len(sub_w)
        print(f"    Wins:   avg=${avg_pw:.2f}  exits: {Counter(t['exit_cat'] for t in sub_w).most_common(3)}")

# ===== 4. Entry comment patterns =====
print(f"\n{'='*70}")
print(f"  3. Entry Comment Patterns (EA signal type)")
print(f"{'='*70}")

# Parse entry comments for signal type
comment_stats = defaultdict(lambda: {'trades':[], 'wins':0, 'pnl':0})
for t in trades_2605:
    em = t['entry_comment']
    # Extract signal type: "WT V11XAU-QS3 S x0.5" -> signal type
    # "S" or "B" for sell/buy, plus position multiplier
    signal = 'unknown'
    if 'WT' in em:
        parts = em.split()
        # Find direction indicator
        for p in parts:
            if p in ('B', 'S') and len(p) == 1:
                signal = f"{p}"
            elif p in ('B', 'S'):
                signal = p
        # Find multiplier
        xm = re.search(r'x([\d.]+)', em)
        mult = float(xm.group(1)) if xm else 1.0
        # Also check for sweep/range/HTF keywords
        if 'swp' in em.lower() or 'sweep' in em.lower():
            signal = 'Sweep_' + signal
        elif 'range' in em.lower() or 'rb' in em.lower():
            signal = 'Range_' + signal
        elif 'htf' in em.lower():
            signal = 'HTF_' + signal
        else:
            signal = 'OB_' + signal

    comment_stats[signal]['trades'].append(t)
    comment_stats[signal]['pnl'] += t['pnl']
    if t['pnl'] > 0: comment_stats[signal]['wins'] += 1

print(f"\n  Signal type breakdown:")
for sig in sorted(comment_stats.keys()):
    d = comment_stats[sig]
    if not d['trades']: continue
    wr = d['wins']/len(d['trades'])*100
    avg_p = d['pnl']/len(d['trades'])
    print(f"    {sig:<15} {len(d['trades']):>5}T  WR={wr:>5.1f}%  "
          f"avg_PnL=${avg_p:>+7.2f}  total=${d['pnl']:>+9.2f}")

# ===== 5. Position multiplier distribution =====
print(f"\n{'='*70}")
print(f"  4. Position Multiplier vs Outcome (B3 2605)")
print(f"{'='*70}")

pm_buckets = defaultdict(lambda: {'trades':[], 'wins':0, 'pnl':0})
for t in trades_2605:
    em = t['entry_comment']
    xm = re.search(r'x([\d.]+)', em)
    pm = float(xm.group(1)) if xm else 1.0
    if pm < 0.5: key = '<0.5'
    elif pm < 0.7: key = '0.5-0.7'
    elif pm < 1.0: key = '0.7-1.0'
    elif pm < 1.5: key = '1.0-1.5'
    elif pm < 2.0: key = '1.5-2.0'
    else: key = '>2.0'
    pm_buckets[key]['trades'].append(t)
    pm_buckets[key]['pnl'] += t['pnl']
    if t['pnl'] > 0: pm_buckets[key]['wins'] += 1

print(f"\n  MaxMult=2.0 cap active. Distribution:")
for key in ['<0.5','0.5-0.7','0.7-1.0','1.0-1.5','1.5-2.0','>2.0']:
    b = pm_buckets.get(key)
    if not b or not b['trades']: continue
    wr = b['wins']/len(b['trades'])*100
    avg_p = b['pnl']/len(b['trades'])
    print(f"    {key:<12} {len(b['trades']):>5}T  WR={wr:>5.1f}%  "
          f"avg=${avg_p:>+7.2f}  PnL=${b['pnl']:>+9.2f}")

# ===== 6. Sequential PnL analysis (for adaptive trigger design) =====
print(f"\n{'='*70}")
print(f"  5. Sequential PnL Analysis (for adaptive gate trigger)")
print(f"{'='*70}")

sorted_t = sorted(trades_2605, key=lambda t: t['exit_time'])
running_pnl = 0
peak_pnl = 0
max_dd = 0
sequence = []

for t in sorted_t:
    running_pnl += t['pnl']
    peak_pnl = max(peak_pnl, running_pnl)
    dd = peak_pnl - running_pnl
    max_dd = max(max_dd, dd)
    sequence.append(running_pnl)

print(f"  Running PnL stats:")
print(f"    Peak: ${peak_pnl:.2f}, Terminal: ${running_pnl:.2f}")
print(f"    Max drawdown from peak: ${max_dd:.2f}")

# Split into quartiles
n = len(sequence)
for q, label in [(n//4, 'Q1'), (n//2, 'Q2'), (3*n//4, 'Q3'), (n, 'Q4')]:
    if q < n:
        print(f"    {label} (trade #{q}): running PnL=${sequence[q-1]:.2f}")

# Find the turning point
turning = 0
for i, s in enumerate(sequence):
    if s < 0 and (i == 0 or sequence[i-1] >= 0):
        turning = i
        break
if turning:
    print(f"    Went negative at trade #{turning+1}/{len(sorted_t)}")

# What if we stopped after N consecutive losses?
print(f"\n  Consecutive loss analysis:")
cl_runs = []; cur = 0; max_cl = 0
cl_details = []  # (start_idx, length, total_pnl)
run_start = 0
for i, t in enumerate(sorted_t):
    if t['pnl'] < 0:
        if cur == 0: run_start = i
        cur += 1; max_cl = max(max_cl, cur)
    else:
        if cur > 0:
            cl_runs.append(cur)
            cl_details.append((run_start, cur, sum(sorted_t[j]['pnl'] for j in range(run_start, i))))
        cur = 0
if cur > 0:
    cl_runs.append(cur)
    cl_details.append((run_start, cur, sum(sorted_t[j]['pnl'] for j in range(run_start, len(sorted_t)))))

print(f"  MaxCL={max_cl}, total CL runs={len(cl_runs)}")
# Longest runs
cl_details.sort(key=lambda x: x[1], reverse=True)
for start, length, pnl in cl_details[:5]:
    print(f"    {length}L streak starting at trade#{start+1}: PnL=${pnl:.2f}")

# ===== 7. Simulate adaptive noise gate effect =====
print(f"\n{'='*70}")
print(f"  6. Adaptive Noise Gate Simulation (hypothetical)")
print(f"{'='*70}")

# What if: after N consecutive losses, enable noise gate for next M trades?
# Simulate with after 3L → enable tight noise for next 10 trades
ADAPTIVE_CL_THRESHOLD = 3
ADAPTIVE_COOLDOWN_TRADES = 10

sim_pnl = 0
adaptive_active = False
cooldown_remaining = 0
filtered_out = 0
kept = 0
sim_trades = []

for t in sorted_t:
    real_pnl = t['pnl']

    if adaptive_active:
        # Simulate noise gate effect: filter out trades with noise gate
        # Assuming tight noise (lb30/r45) filters 97% of trades
        # and the filtered trades have outcomes proportional to the overall distribution
        # This is a simplified model
        filtered_out += 1
        # In reality, the noise gate would filter some winners and some losers
        # From our data, noise gate selectivity (WR improvement from OFF→NOISE):
        # 2605 OFF WR=45.9% → NOISE WR=~55%. So noise improves WR by ~10pp.
        # This means it filters more losers than winners.
        # Approximate: 60% of filtered trades would be losers, 40% winners
        pass  # Don't add to PnL (filtered out)

    else:
        sim_pnl += real_pnl
        kept += 1

    # Update adaptive state based on recent outcomes
    if real_pnl < 0 and not adaptive_active:
        # Check for CL trigger
        recent = [t2['pnl'] for t2 in sim_trades[-ADAPTIVE_CL_THRESHOLD+1:]] if len(sim_trades) >= ADAPTIVE_CL_THRESHOLD-1 else []
        if len(recent) >= ADAPTIVE_CL_THRESHOLD-1 and all(p < 0 for p in recent) and real_pnl < 0:
            # This would be the Nth consecutive loss → trigger adaptive defense
            pass  # Can't simulate this properly without running actual backtests

# This simulation is too crude. Let's instead estimate based on data:
print(f"\n  From actual data:")
print(f"    B3 OFF 2605: {len(trades_2605)}T, WR={len(wins)/len(trades_2605)*100:.1f}%, PnL=${sum(t['pnl'] for t in trades_2605):.2f}")
print(f"    Noise gate lb30/r45 on B3 would filter ~95% of trades")
print(f"    Estimated B3+NOISE: ~{int(len(trades_2605)*0.05)}T, WR~?%")

# What if we activate noise gate ONLY during drawdown?
# Parse the equity curve to find periods of drawdown
print(f"\n  Drawdown-based adaptive simulation:")
in_dd = False
dd_start = 0
pnl_with_adaptive = 0
dd_periods = 0
for i, t in enumerate(sorted_t):
    # Check current running PnL vs peak
    current_running = pnl_with_adaptive + t['pnl']
    current_peak = max(pnl_with_adaptive, current_running)

    # If we were in drawdown and recovered, exit defensive mode
    was_in_dd = in_dd
    if in_dd and current_running >= current_peak * 0.98:  # recovered to 98% of peak
        in_dd = False
        dd_periods += 1

    # If NOT in drawdown, always take the trade
    if not in_dd:
        pnl_with_adaptive += t['pnl']
        # Check if we just entered drawdown (lost >2% from peak)
        if current_running < current_peak * 0.98:
            in_dd = True
    else:
        # In drawdown: apply noise gate filtering
        # Model: noise gate lets through 5% of trades during drawdown
        # Simplified: skip this trade
        pass

print(f"    Full-accept PnL: ${sum(t['pnl'] for t in sorted_t):.2f}")
print(f"    DD-filter PnL: ${pnl_with_adaptive:.2f} (skipped during {dd_periods} DD periods)")
print(f"    NOTE: This is hypothetical — actual implementation requires EA code changes")

print(f"\n[DONE]")
