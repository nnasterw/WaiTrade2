#!/usr/bin/env python3
"""Deep dive: QS3 OFF 2505 vs 2605 — what makes 2605 toxic?"""
from pathlib import Path
import re, statistics
from collections import defaultdict, Counter
from datetime import datetime

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
FILES = {
    '2505_good': DATA / 'bt6x5_qs3_2025-05.htm',
    '2605_bad':  DATA / 'bt6x5_26_qs3_2026-05.htm',
    '2505_n':    DATA / 'bt6x5_qs3_noise_2025-05.htm',
    '2605_n':    DATA / 'bt6x5_26_qs3_noise_2026-05.htm',
}

def parse_trades(htm_path):
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows_raw = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    pending = []
    trades = []
    for row_html in rows_raw:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html)
        if len(cells) != 13: continue
        ct = cells[3].strip()
        if ct == 'balance': continue
        io = cells[4].strip()
        time_str = cells[0].strip()
        try: pnl = float(cells[10].strip().replace(' ','').replace(',',''))
        except: pnl = 0.0
        if io == 'in':
            pending.append({'time': time_str, 'dir': ct, 'price': float(cells[6].strip()),
                           'comment': cells[12].strip()})
        elif io == 'out' and pending:
            entry = pending.pop(0)
            et = parse_dt(entry['time'])
            xt = parse_dt(time_str)
            hold = (xt - et).total_seconds() if et and xt else 0
            trades.append({
                'pnl': pnl, 'hold_sec': hold, 'direction': entry['dir'],
                'comment': cells[12].strip(), 'entry_time': entry['time'],
                'exit_time': time_str, 'entry_comment': entry['comment'],
                'entry_price': entry['price'],
                'exit_price': float(cells[6].strip()) if cells[6].strip() else 0,
            })
    return trades

def parse_dt(s):
    try:
        parts = s.split(); d = parts[0].split('.'); t = parts[1].split(':')
        return datetime(int(d[0]),int(d[1]),int(d[2]),int(t[0]),int(t[1]),int(t[2]))
    except: return None

def exit_reason(comment, hold_sec):
    c = (comment or '').lower()
    if 'sl' in c:
        if hold_sec < 10: return 'SL<10s'
        if hold_sec < 60: return 'SL<1m'
        if hold_sec < 300: return 'SL<5m'
        return 'SL>5m'
    if 'be' in c: return 'BE'
    if 'tp' in c: return 'TP'
    if 'dtp' in c: return 'DTP'
    if 'time' in c: return 'TIMEOUT'
    if 'decay' in c: return 'DECAY'
    if 'mfe' in c: return 'MFE_FAIL'
    if 'reverse' in c: return 'REVERSE'
    return 'OTHER'

# ===== Load all =====
all_data = {}
for key, path in FILES.items():
    if path.exists():
        all_data[key] = parse_trades(path)
        print(f"Loaded {key}: {len(all_data[key])}T")

off_25 = all_data.get('2505_good', [])
off_26 = all_data.get('2605_bad', [])
n_25 = all_data.get('2505_n', [])
n_26 = all_data.get('2605_n', [])

# ===== 1. Exit reason comparison =====
print(f"\n{'='*70}")
print(f"  1. QS3 OFF: 2505 vs 2605 Exit Reason Distribution")
print(f"{'='*70}")

for label, trades in [('2505 GOOD', off_25), ('2605 BAD', off_26)]:
    if not trades: continue
    losses = [t for t in trades if t['pnl'] < 0]
    wins = [t for t in trades if t['pnl'] > 0]
    for t in losses: t['exit_cat'] = exit_reason(t['comment'], t['hold_sec'])
    for t in wins: t['exit_cat'] = exit_reason(t['comment'], t['hold_sec'])

    print(f"\n  {label}: {len(trades)}T, WR={len(wins)/len(trades)*100:.1f}%, "
          f"PnL=${sum(t['pnl'] for t in trades):.2f}")

    # Loss exits
    ec = Counter(t['exit_cat'] for t in losses)
    print(f"  亏损出口 Top6:")
    for reason, cnt in ec.most_common(6):
        subt = [t for t in losses if t['exit_cat'] == reason]
        avg_p = sum(t['pnl'] for t in subt)/cnt
        avg_h = statistics.median([t['hold_sec'] for t in subt]) if subt else 0
        print(f"    {reason:<12} {cnt:>4}T ({cnt/len(losses)*100:>5.1f}%)  "
              f"avg=${avg_p:>7.2f}  mid_hold={avg_h:.0f}s")

    # Win exits
    wec = Counter(t['exit_cat'] for t in wins)
    print(f"  盈利出口 Top4:")
    for reason, cnt in wec.most_common(4):
        subt = [t for t in wins if t['exit_cat'] == reason]
        avg_p = sum(t['pnl'] for t in subt)/cnt if cnt else 0
        avg_h = statistics.median([t['hold_sec'] for t in subt]) if subt else 0
        print(f"    {reason:<12} {cnt:>4}T ({cnt/len(wins)*100:>5.1f}%)  "
              f"avg=${avg_p:>7.2f}  mid_hold={avg_h:.0f}s")

# ===== 2. PnL by hour of day =====
print(f"\n{'='*70}")
print(f"  2. PnL by Entry Hour (UTC)")
print(f"{'='*70}")

for label, trades in [('2505', off_25), ('2605', off_26)]:
    if not trades: continue
    hourly = defaultdict(lambda: {'pnl':0,'count':0,'wins':0})
    for t in trades:
        try:
            h = int(t['entry_time'].split()[1].split(':')[0])
        except:
            continue
        hourly[h]['pnl'] += t['pnl']
        hourly[h]['count'] += 1
        if t['pnl'] > 0: hourly[h]['wins'] += 1

    print(f"\n  {label} PnL by hour:")
    for h in sorted(hourly.keys()):
        d = hourly[h]
        wr = d['wins']/d['count']*100 if d['count'] else 0
        bar = '█'*min(int(abs(d['pnl'])/10), 20)
        sign = '+' if d['pnl'] >= 0 else '-'
        print(f"    H{h:02d}: {d['count']:>4}T  WR={wr:>5.1f}%  "
              f"PnL=${d['pnl']:>+8.2f} {bar}")

# ===== 3. Consecutive loss depth =====
print(f"\n{'='*70}")
print(f"  3. Consecutive Loss Analysis")
print(f"{'='*70}")

for label, trades in [('2505', off_25), ('2605', off_26)]:
    if not trades: continue
    sorted_t = sorted(trades, key=lambda t: t['exit_time'])
    cl_runs = []; cur = 0; max_cl = 0; cl_pnl_sum = 0
    for t in sorted_t:
        if t['pnl'] < 0:
            cur += 1; max_cl = max(max_cl, cur); cl_pnl_sum += t['pnl']
        else:
            if cur > 0: cl_runs.append(cur)
            cur = 0
    if cur > 0: cl_runs.append(cur)
    print(f"  {label}: MaxCL={max_cl}, 连亏簇数={len(cl_runs)}, "
          f"avg_连亏长度={sum(cl_runs)/len(cl_runs):.1f}" if cl_runs else f"  {label}: no losses")

# ===== 4. Win/Loss magnitude distribution =====
print(f"\n{'='*70}")
print(f"  4. PnL Magnitude Distribution")
print(f"{'='*70}")

for label, trades in [('2505', off_25), ('2605', off_26)]:
    if not trades: continue
    wins = [t['pnl'] for t in trades if t['pnl'] > 0]
    losses = [t['pnl'] for t in trades if t['pnl'] < 0]

    # Bucket by $ ranges
    def bucket(vals, step=1):
        b = defaultdict(lambda: {'cnt':0,'sum':0})
        for v in vals:
            k = int(abs(v)/step)*step
            b[k]['cnt'] += 1
            b[k]['sum'] += abs(v)
        return b

    wb = bucket(wins, 2)
    lb = bucket(losses, 1)

    print(f"\n  {label} 盈利分布:")
    for k in sorted(wb.keys())[:8]:
        print(f"    ${k}-{k+2}: {wb[k]['cnt']:>3}T  sum=${wb[k]['sum']:.0f}")

    print(f"  亏损分布:")
    for k in sorted(lb.keys())[:8]:
        print(f"    ${k}-{k+1}: {lb[k]['cnt']:>3}T  sum=${lb[k]['sum']:.0f}")

# ===== 5. Hour-based win rate (finding toxic hours) =====
print(f"\n{'='*70}")
print(f"  5. 2605 Toxic Hours Detection (WR < 40% + count >= 10)")
print(f"{'='*70}")

for label, trades in [('2505', off_25), ('2605', off_26)]:
    if not trades: continue
    hourly = defaultdict(lambda: {'pnl':0,'count':0,'wins':0})
    for t in trades:
        try:
            h = int(t['entry_time'].split()[1].split(':')[0])
        except: continue
        hourly[h]['pnl'] += t['pnl']
        hourly[h]['count'] += 1
        if t['pnl'] > 0: hourly[h]['wins'] += 1

    toxic = [(h,d) for h,d in hourly.items()
             if d['count']>=5 and d['wins']/d['count']*100 < 40]
    if toxic:
        print(f"\n  {label} 有毒时段 (WR<40%):")
        for h, d in sorted(toxic):
            wr = d['wins']/d['count']*100
            print(f"    H{h:02d}: {d['count']:>4}T  WR={wr:.0f}%  PnL=${d['pnl']:.2f}")

# ===== 6. Compare OFF vs NOISE for same entries =====
print(f"\n{'='*70}")
print(f"  6. 2605: OFF losses key stats vs NOISE")
print(f"{'='*70}")

for label, trades in [('QS3 OFF 2605', off_26), ('QS3 NOISE 2605', n_26)]:
    if not trades: continue
    losses = [t for t in trades if t['pnl'] < 0]
    wins = [t for t in trades if t['pnl'] > 0]
    if losses:
        lh = [t['hold_sec'] for t in losses]
        print(f"  {label}: {len(trades)}T  losses={len(losses)}  "
              f"loss_mid_hold={statistics.median(lh):.0f}s  "
              f"avg_loss=${sum(t['pnl'] for t in losses)/len(losses):.2f}")
    if wins:
        wh = [t['hold_sec'] for t in wins]
        print(f"    wins={len(wins)}  win_mid_hold={statistics.median(wh):.0f}s  "
              f"avg_win=${sum(t['pnl'] for t in wins)/len(wins):.2f}")

print(f"\n[DONE]")
