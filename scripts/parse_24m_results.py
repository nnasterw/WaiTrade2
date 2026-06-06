#!/usr/bin/env python3
"""Parse all 24-month HTML reports and produce summary tables."""
import re, sys
from pathlib import Path
from collections import defaultdict

MT5_DATA = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075')

def parse_report(htm_path):
    if not htm_path.exists(): return None
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    pending = []; trades = []
    for r in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
        if len(cells) != 13: continue
        if cells[3].strip().lower() == 'balance': continue
        io = cells[4].strip().lower()
        try: pnl = float(cells[10].strip().replace(' ','').replace(',',''))
        except: pnl = 0.0
        if 'in' in io: pending.append(1)
        elif 'out' in io and pending: pending.pop(0); trades.append(pnl)
    wins = [t for t in trades if t > 0]; losses = [t for t in trades if t < 0]
    gw = sum(wins) if wins else 0; gl = abs(sum(losses)) if losses else 0
    return {
        'count': len(trades), 'pnl': sum(trades),
        'wr': len(wins)/len(trades)*100 if trades else 0,
        'pf': gw/gl if gl > 0 else (999 if gw > 0 else 0),
    }

# Strategies
STRATEGIES = [
    ('S1_H5L',   'H5+LOOSE'),
    ('S2_H5ADL', 'H5+AD-LOOSE'),
    ('S3_OFF',   'QS3-OFF'),
]

# Months
MONTHS = []
for y in [2024, 2025, 2026]:
    start_m = 6 if y == 2024 else 1
    end_m = 6 if y == 2026 else 13
    for m in range(start_m, end_m):
        m_str = f'{y%100:02d}{m:02d}'
        MONTHS.append(m_str)

# Parse all reports
results = {}
for skey, _ in STRATEGIES:
    for mkey in MONTHS:
        r = parse_report(MT5_DATA / f'24m_{skey}_{mkey}.htm')
        results[f'{skey}_{mkey}'] = r

# ===== BLOCK 1: Monthly PnL Table =====
print(f"\n{'='*130}")
print(f"  24-MONTH STRATEGY COMPARISON: S1(H5+LOOSE) vs S2(H5+AD-LOOSE) vs S3(QS3-OFF)")
print(f"  Initial: $200 | Model 4 Real Ticks | XAUUSDm M1")
print(f"{'='*130}")

print(f"\n--- Monthly PnL ---")
header = f"  {'Month':<8}"
for skey, slabel in STRATEGIES:
    header += f" {slabel:>18}"
header += f" {'Best':>12}"
print(header)
print(f"  {'-'*8}{'-'*60}")

s1_pnls = []; s2_pnls = []; s3_pnls = []
for mkey in MONTHS:
    row = f"  {mkey:<8}"
    best = -99999
    pnls = []
    for skey, _ in STRATEGIES:
        r = results.get(f'{skey}_{mkey}')
        pnl = r['pnl'] if r else 0
        pnls.append(pnl)
        row += f" ${pnl:>+17,.0f}"
        if pnl > best: best = pnl
    row += f" ${best:>+11,.0f}"
    s1_pnls.append(pnls[0]); s2_pnls.append(pnls[1]); s3_pnls.append(pnls[2])
    # Mark losing months
    if pnls[0] < 0: row += ' *'
    print(row)

# ===== BLOCK 2: Aggregate Statistics =====
print(f"\n--- Block 2: Aggregate Statistics ---")
print(f"  {'Strategy':<20} {'Sum':>14} {'Mean':>10} {'Med':>10} {'Best':>12} {'Worst':>12} {'+Months':>8} {'WR_avg':>7}")
print(f"  {'-'*95}")
for i, (skey, slabel) in enumerate(STRATEGIES):
    pnls = [s1_pnls, s2_pnls, s3_pnls][i]
    total = sum(pnls)
    mean = total / len(pnls)
    med = sorted(pnls)[len(pnls)//2]
    best_m = max(pnls)
    worst_m = min(pnls)
    pos = len([p for p in pnls if p > 0])

    # Avg WR
    wrs = []
    for mkey in MONTHS:
        r = results.get(f'{skey}_{mkey}')
        if r: wrs.append(r['wr'])
    avg_wr = sum(wrs)/len(wrs) if wrs else 0

    print(f"  {slabel:<20} ${total:>+13,.0f} ${mean:>+9,.0f} ${med:>+9,.0f} "
          f"${best_m:>+11,.0f} ${worst_m:>+11,.0f} {pos:>4}/{len(pnls)} {avg_wr:>6.1f}%")

# ===== BLOCK 3: Monthly Balance Table =====
print(f"\n--- Block 3: Monthly Balance (compound, reset each month at $200) ---")
print(f"  Actually, balances ARE the PnL+200 in the monthly table above.")
print(f"  Compound growth: starting $200, compounding monthly.")
print(f"  {'Month':<8}", end='')
for skey, slabel in STRATEGIES:
    print(f" {slabel:>15}", end='')
print()
print(f"  {'-'*8}{'-'*48}")

for i, (skey, slabel) in enumerate(STRATEGIES):
    bal = 200.0
    balances = []
    for pnl in ([s1_pnls, s2_pnls, s3_pnls][i]):
        bal += pnl
        balances.append(bal)
    print(f"\n  [{slabel}] Compound balance path:")
    for j, mkey in enumerate(MONTHS):
        if j % 6 == 0 or j == len(MONTHS)-1:
            print(f"    {mkey}: ${balances[j]:>15,.0f}")

# ===== BLOCK 4: Key Insights =====
print(f"\n{'='*80}")
print(f"  KEY INSIGHTS")
print(f"{'='*80}")

s1_sum = sum(s1_pnls); s2_sum = sum(s2_pnls); s3_sum = sum(s3_pnls)

# Best/worst quarters
q_labels = ['2024H2','2025H1','2025H2','2026H1']
for qi, (start, end, label) in enumerate([(0,7,'2024H2(Jun-Dec)'),(7,13,'2025H1'),(13,19,'2025H2'),(19,24,'2026H1')]):
    s1_q = sum(s1_pnls[start:end])
    s2_q = sum(s2_pnls[start:end])
    s3_q = sum(s3_pnls[start:end])
    print(f"  {label}: S1=${s1_q:+,.0f}  S2=${s2_q:+,.0f}  S3=${s3_q:+,.0f}")

print(f"\n  S1 (H5+LOOSE) total 24-month: ${s1_sum:+,.0f} (from $200)")
print(f"  S2 (H5+AD-LOOSE) total 24-month: ${s2_sum:+,.0f}")
print(f"  S3 (QS3-OFF) total 24-month: ${s3_sum:+,.0f}")

# Months where S1 out/underperforms S3
s1_vs_s3 = [(s1_pnls[i] - s3_pnls[i], MONTHS[i]) for i in range(24)]
better = [(d, m) for d, m in s1_vs_s3 if d > 0]
worse = [(d, m) for d, m in s1_vs_s3 if d < 0]
print(f"\n  S1 > S3 in {len(better)}/24 months, S1 < S3 in {len(worse)}/24 months")

# Top 3 and bottom 3 months for S1
ranked = sorted([(s1_pnls[i], MONTHS[i]) for i in range(24)], reverse=True)
print(f"\n  S1 Top 3 months: {', '.join(f'{m}=${p:+,.0f}' for p,m in ranked[:3])}")
print(f"  S1 Bottom 3 months: {', '.join(f'{m}=${p:+,.0f}' for p,m in ranked[-3:])}")

print(f"\n[DONE]")
