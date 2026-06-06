#!/usr/bin/env python3
"""Parse all 72 HTML reports, show full 24-month details for all 3 strategies."""
import re, sys
from pathlib import Path
from datetime import datetime

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
    return {'count': len(trades), 'pnl': sum(trades), 'wins': len(wins), 'losses': len(losses),
            'wr': len(wins)/len(trades)*100 if trades else 0,
            'pf': gw/gl if gl > 0 else (999 if gw > 0 else 0),
            'avg_w': gw/len(wins) if wins else 0, 'avg_l': gl/len(losses) if losses else 0}

STRATS = [('S1_H5L', 'H5+LOOSE'), ('S2_H5ADL', 'H5+AD-LOOSE'), ('S3_OFF', 'QS3-OFF')]

MONTHS = []
for y in [2024,2025,2026]:
    for m in range(1,13):
        if y==2024 and m<6: continue
        if y==2026 and m>=6: break
        MONTHS.append(f'{y%100:02d}{m:02d}')

# Parse all
all_r = {}
for skey,_ in STRATS:
    for m in MONTHS:
        all_r[f'{skey}_{m}'] = parse_report(MT5_DATA / f'24m_{skey}_{m}.htm')

# Group by half-year
half_years = [('2024H2', MONTHS[:7]), ('2025H1', MONTHS[7:13]), ('2025H2', MONTHS[13:19]), ('2026H1', MONTHS[19:])]

print("=" * 145)
print("  24-MONTH DETAIL: S1(H5+LOOSE) vs S2(H5+AD-LOOSE) vs S3(QS3-OFF)")
print("  XAUUSDm M1 | Model 4 Real Ticks | $200 initial per month")
print("=" * 145)

for hy_label, hy_months in half_years:
    print(f"\n  ▸ {hy_label}")
    print(f"  {'Month':<8} {'H5+LOOSE':>18} {'H5+AD-LOOSE':>18} {'QS3-OFF':>18}")
    print(f"  {'':<8} {'Count':>6} {'PnL':>10} {'Count':>6} {'PnL':>10} {'Count':>6} {'PnL':>10}")
    print(f"  {'-'*8} {'-'*18} {'-'*18} {'-'*18}")
    for m in hy_months:
        row = [f"  {m:<8}"]
        for skey, _ in STRATS:
            r = all_r.get(f'{skey}_{m}')
            if r: row.append(f"{r['count']:>6} ${r['pnl']:>+9,.2f}")
            else: row.append(f"{'':>6} {'n/a':>10}")
        m_mark = ' *' if any((all_r.get(f'{skey}_{m}') or {}).get('pnl',1)<0 for skey,_ in STRATS) else ''
        print(' '.join(row) + m_mark)

    # Half-year totals
    print(f"  {'Total':<8}", end='')
    for skey,slabel in STRATS:
        pnls = [(all_r.get(f'{skey}_{m}') or {}).get('pnl',0) for m in hy_months]
        cnts = [(all_r.get(f'{skey}_{m}') or {}).get('count',0) for m in hy_months]
        if any(True for p in pnls if p):
            print(f" {sum(cnts):>6} ${sum(pnls):>+9,.0f}", end='')
        else:
            print(f"{'':>6} {'n/a':>10}", end='')
    print()

print(f"\n  {'─'*80}")
print(f"  {'24-MONTH TOTAL':^80}")
print(f"  {'─'*80}")
print(f"  {'Month':<8} {'S1 Trades':>8} {'S1 PnL':>12} {'S2 Trades':>10} {'S2 PnL':>12} {'S3 Trades':>10} {'S3 PnL':>12}")
print(f"  {'-'*8} {'-'*8} {'-'*12} {'-'*10} {'-'*12} {'-'*10} {'-'*12}")
for m in MONTHS:
    row = [f"  {m:<8}"]
    for skey,_ in STRATS:
        r = all_r.get(f'{skey}_{m}')
        if r: row.append(f"{r['count']:>8} ${r['pnl']:>+10,.2f}")
        else: row.append(f"{'':>8} {'':>12}")
    print(' '.join(row))

# Block 2: Full monthly balance table
print(f"\n  {'='*100}")
print(f"  第二块：24个月完整余额表（每月初始$200，独立计算，不退仓）")
print(f"  {'='*100}")
print(f"  {'Month':<8} {'S1 H5+LOOSE':>15} {'S2 H5+AD-LOOSE':>18} {'S3 QS3-OFF':>15} {'最佳':>10}")
print(f"  {'-'*8} {'-'*15} {'-'*18} {'-'*15} {'-'*10}")
for m in MONTHS:
    r1 = all_r.get(f'S1_H5L_{m}')
    r2 = all_r.get(f'S2_H5ADL_{m}')
    r3 = all_r.get(f'S3_OFF_{m}')
    p1 = r1['pnl'] if r1 else None
    p2 = r2['pnl'] if r2 else None
    p3 = r3['pnl'] if r3 else None
    b1 = f"${200+p1:>10,.0f}" if p1 is not None else f"{'n/a':>15}"
    b2 = f"${200+p2:>10,.0f}" if p2 is not None else f"{'n/a':>18}"
    b3 = f"${200+p3:>10,.0f}" if p3 is not None else f"{'n/a':>15}"
    best = max([v for v in [p1,p2,p3] if v is not None])
    bst = f"${200+best:>10,.0f}" if best != 0 else f"{'$       200':>10}"
    m_mark = ' *' if (p1 is not None and p1<0) else ''
    print(f"  {m:<8} {b1:>15} {b2:>18} {b3:>15} {bst:>10}{m_mark}")

# Win rate detail
print(f"\n  {'='*100}")
print(f"  第二块补充：各策略月明细完整数据")
print(f"  {'='*100}")
print(f"  {'Month':<8} {'S1 T':>5} {'WR%':>5} {'PF':>5} {'avgW':>7} {'avgL':>7} | "
      f"{'S2 T':>5} {'WR%':>5} {'PF':>5} {'avgW':>7} {'avgL':>7} | "
      f"{'S3 T':>5} {'WR%':>5} {'PF':>5} {'avgW':>7} {'avgL':>7}")
print(f"  {'-'*105}")
for m in MONTHS:
    row = [f"  {m:<8}"]
    for skey,_ in STRATS:
        r = all_r.get(f'{skey}_{m}')
        if r:
            row.append(f"{r['count']:>5} {r['wr']:>4.1f}% {r['pf']:>4.2f} ${r['avg_w']:>5.2f} ${r['avg_l']:>5.2f}")
        else:
            row.append(f"{'':>5} {'':>5} {'':>5} {'':>7} {'':>7}")
    print(' | '.join(row))

print(f"\n[DONE]")
