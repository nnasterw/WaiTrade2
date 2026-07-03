#!/usr/bin/env python3
"""QS3+NOISE deep loss analysis — Phase 1 diagnosis."""
from pathlib import Path
import re, statistics
from collections import defaultdict, Counter
from datetime import datetime

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')

MONTH_FILES_25 = [
    ('2025-01', 'bt6x5_qs3_noise_2025-01.htm'),
    ('2025-02', 'bt6x5_qs3_noise_2025-02.htm'),
    ('2025-03', 'bt6x5_qs3_noise_2025-03.htm'),
    ('2025-04', 'bt6x5_qs3_noise_2025-04.htm'),
    ('2025-05', 'bt6x5_qs3_noise_2025-05.htm'),
]
MONTH_FILES_26 = [
    ('2026-01', 'bt6x5_26_qs3_noise_2026-01.htm'),
    ('2026-02', 'bt6x5_26_qs3_noise_2026-02.htm'),
    ('2026-03', 'bt6x5_26_qs3_noise_2026-03.htm'),
    ('2026-04', 'bt6x5_26_qs3_noise_2026-04.htm'),
    ('2026-05', 'bt6x5_26_qs3_noise_2026-05.htm'),
]

def parse_trades(htm_path):
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows_raw = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    pending_ins = []  # sequential: FIFO queue of entry deals
    trades = []
    for row_html in rows_raw:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html)
        if len(cells) != 13:
            continue
        ctype = cells[3].strip()
        if ctype == 'balance':
            continue
        io = cells[4].strip()
        time_str = cells[0].strip()
        try:
            pnl = float(cells[10].strip().replace(' ', '').replace(',', ''))
        except:
            pnl = 0.0
        if io == 'in':
            pending_ins.append({
                'time': time_str, 'direction': ctype,
                'lot': float(cells[5].strip()) if cells[5].strip() else 0.01,
            })
        elif io == 'out' and pending_ins:
            entry = pending_ins.pop(0)  # FIFO: match with oldest pending entry
            et = parse_dt(entry['time'])
            xt = parse_dt(time_str)
            hold = (xt - et).total_seconds() if et and xt else 0
            trades.append({
                'pnl': pnl, 'hold_sec': hold,
                'direction': entry['direction'],
                'comment': cells[12].strip(),
                'month': time_str[:7],
            })
    return trades

def parse_dt(s):
    try:
        parts = s.split()
        d = parts[0].split('.')
        t = parts[1].split(':')
        return datetime(int(d[0]), int(d[1]), int(d[2]), int(t[0]), int(t[1]), int(t[2]))
    except:
        return None

def exit_reason(comment, hold_sec):
    c = comment.lower()
    if 'be' in c:
        return 'BE'
    if 'sl' in c:
        if hold_sec < 10: return 'SL(<10s)'
        if hold_sec < 60: return 'SL(<1m)'
        if hold_sec < 300: return 'SL(<5m)'
        return 'SL(>5m)'
    if 'tp' in c:
        return 'TP'
    if 'dtp' in c:
        return 'DTP'
    if 'time' in c:
        return 'TIMEOUT'
    return 'OTHER'

# ===== LOAD ALL =====
all_2025 = []
all_2026 = []
monthly_25 = {}
monthly_26 = {}

for label, fname in MONTH_FILES_25:
    p = DATA / fname
    if p.exists():
        t = parse_trades(p)
        all_2025.extend(t)
        monthly_25[label] = t
        print(f"2025 {label}: {len(t)}T")

for label, fname in MONTH_FILES_26:
    p = DATA / fname
    if p.exists():
        t = parse_trades(p)
        all_2026.extend(t)
        monthly_26[label] = t
        print(f"2026 {label}: {len(t)}T")

# ===== PHASE 1.1: Loss Detail Analysis =====
print(f"\n{'='*70}")
print(f"  Phase 1.1: QS3+NOISE 亏损单出口原因")
print(f"{'='*70}")

for year_label, all_trades in [('2025', all_2025), ('2026', all_2026)]:
    losses = [t for t in all_trades if t['pnl'] < 0]
    wins = [t for t in all_trades if t['pnl'] > 0]
    total = len(all_trades)
    if total == 0:
        continue

    # Classify exit reasons for all losses
    for t in losses:
        t['exit_cat'] = exit_reason(t['comment'], t['hold_sec'])

    exit_cnt = Counter(t['exit_cat'] for t in losses)

    print(f"\n--- {year_label} (共{total}笔, 亏损{len(losses)}笔/{total*100:.1f}%) "
          f"盈利{len(wins)}笔 ---")

    print(f"  亏损出口原因:")
    for reason, cnt in exit_cnt.most_common(8):
        avg_p = sum(t['pnl'] for t in losses if t['exit_cat'] == reason) / cnt
        print(f"    {reason:<15} {cnt:>4}笔 ({cnt/len(losses)*100:>5.1f}%)  "
              f"avg=${avg_p:>7.2f}")

    # Hold time distribution
    buckets = {'<5s':0, '5-10s':0, '10-30s':0, '30s-1m':0,
               '1-5m':0, '5-30m':0, '>30m':0}
    for t in losses:
        s = t['hold_sec']
        if s < 5: buckets['<5s']+=1
        elif s < 10: buckets['5-10s']+=1
        elif s < 30: buckets['10-30s']+=1
        elif s < 60: buckets['30s-1m']+=1
        elif s < 300: buckets['1-5m']+=1
        elif s < 1800: buckets['5-30m']+=1
        else: buckets['>30m']+=1

    print(f"\n  亏损持仓时长:")
    for label, cnt in buckets.items():
        pct = cnt/len(losses)*100 if losses else 0
        bar = '█' * int(pct/3)
        print(f"    {label:<8} {cnt:>4} ({pct:>5.1f}%) {bar}")

    # Direction
    for d in ['buy', 'sell']:
        dt = [t for t in all_trades if t['direction'] == d]
        dw = [t for t in dt if t['pnl'] > 0]
        dl = [t for t in dt if t['pnl'] < 0]
        if dt:
            wr = len(dw)/len(dt)*100
            np = sum(t['pnl'] for t in dt)
            print(f"    {d.upper():<5} {len(dt):>4}T  WR={wr:.0f}%  "
                  f"avg_win=${sum(t['pnl'] for t in dw)/len(dw):.2f}" if dw else '',
                  f"avg_loss=${sum(t['pnl'] for t in dl)/len(dl):.2f}" if dl else '',
                  f"PnL=${np:.2f}")

    # Win/loss strength
    if wins and losses:
        aw = sum(t['pnl'] for t in wins)/len(wins)
        al = abs(sum(t['pnl'] for t in losses)/len(losses))
        print(f"\n  盈亏强度: avg_win=${aw:.2f}  avg_loss=${al:.2f}  "
              f"W/L={aw/al:.2f}x")

    # Consecutive losses
    sorted_t = sorted(all_trades, key=lambda t: t.get('month',''))
    max_cl = cur = 0
    cl_runs = []
    for t in sorted_t:
        if t['pnl'] < 0:
            cur += 1
            max_cl = max(max_cl, cur)
        else:
            if cur > 0:
                cl_runs.append(cur)
            cur = 0
    if cur > 0:
        cl_runs.append(cur)
    print(f"  连亏: MaxCL={max_cl}  连亏簇={sorted(cl_runs, reverse=True)[:6]}  "
          f"avg_cl={sum(cl_runs)/len(cl_runs):.1f}" if cl_runs else f"  连亏: MaxCL={max_cl}")

# ===== PHASE 1.2: Good vs Bad cluster =====
print(f"\n{'='*70}")
print(f"  Phase 1.2: 好簇 vs 坏簇 交叉验证")
print(f"{'='*70}")

clusters = [
    ('2025-04 好簇', monthly_25.get('2025-04', [])),
    ('2026-03 坏簇', monthly_26.get('2026-03', [])),
]

for label, trades in clusters:
    if not trades:
        continue
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]
    total = len(trades)

    # Classify losses
    for t in losses:
        t['exit_cat'] = exit_reason(t['comment'], t['hold_sec'])

    gw = sum(t['pnl'] for t in wins)
    gl = abs(sum(t['pnl'] for t in losses))
    wr = len(wins)/total*100
    pf = gw/gl if gl > 0 else 999

    print(f"\n  {label}: {total}T  WR={wr:.0f}%  PF={pf:.2f}  PnL=${gw-gl:.2f}")

    # Exit reasons
    ec = Counter(t.get('exit_cat','?') for t in losses)
    print(f"    亏损出口: " + ' '.join(f"{k}:{v}" for k,v in ec.most_common(4)))

    # Hold times
    lh = [t['hold_sec'] for t in losses]
    wh = [t['hold_sec'] for t in wins]
    if lh:
        print(f"    持仓: 亏损mid={statistics.median(lh):.0f}s  "
              f"盈利mid={statistics.median(wh):.0f}s" if wh else "")
    if wins and losses:
        aw = gw/len(wins)
        al = gl/len(losses)
        print(f"    avg_win=${aw:.2f}  avg_loss=${al:.2f}  W/L={aw/al:.2f}x")

# ===== Compare: OFF vs NOISE for a losing month =====
print(f"\n{'='*70}")
print(f"  Phase 1.3: OFF vs NOISE 同月对比 (2026-03 坏簇)")
print(f"{'='*70}")

# Load OFF QS3 for March 2026
off_file = DATA / 'bt6x5_26_qs3_2026-03.htm'
if off_file.exists():
    off_t = parse_trades(off_file)
    off_losses = [t for t in off_t if t['pnl'] < 0]
    off_wins = [t for t in off_t if t['pnl'] > 0]
    for t in off_losses:
        t['exit_cat'] = exit_reason(t['comment'], t['hold_sec'])

    print(f"\n  OFF: {len(off_t)}T  WR={len(off_wins)/len(off_t)*100:.0f}%  "
          f"PnL=${sum(t['pnl'] for t in off_t):.2f}")
    ec = Counter(t.get('exit_cat','?') for t in off_losses)
    print(f"  亏损出口: " + ' '.join(f"{k}:{v}" for k,v in ec.most_common(4)))
    lh = [t['hold_sec'] for t in off_losses]
    if lh:
        print(f"  亏损持仓中位: {statistics.median(lh):.0f}s")

else:
    print("  OFF file not found")

print(f"\n[DONE]")
