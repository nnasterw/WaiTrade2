#!/usr/bin/env python3
"""Fix hourly WR analysis + directional asymmetry + DOW patterns.
Extract from HTML reports, find hours bad in 2605 but OK in 2505."""
import re, sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

MT5_DATA = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075')

REPORTS = {
    'OFF_2505':    MT5_DATA / 'nkss_REF_OFF_2505.htm',
    'OFF_2605':    MT5_DATA / 'nkss_REF_OFF_2605.htm',
    'LOOSE_2505':  MT5_DATA / 'nkss_REF_LOOSE_2505.htm',
    'LOOSE_2605':  MT5_DATA / 'nkss_REF_LOOSE_2605.htm',
    'C4_2605':     MT5_DATA / 'nkss_C4_2605.htm',
    'C2_2605':     MT5_DATA / 'nkss_C2_2605.htm',
    # Our best configs
    'cd_REF_2505': MT5_DATA / 'cd_REF_2505.htm',
    'cd_REF_2605': MT5_DATA / 'cd_REF_2605.htm',
}

def parse_trades_with_hour(htm_path):
    """Extract trades with correct hour, direction, DOW."""
    if not htm_path.exists():
        return []
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    pending = []
    trades = []
    for r in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
        if len(cells) != 13: continue
        if cells[3].strip().lower() == 'balance': continue
        # 13-cell rows: [0]=time [1]=deal# [2]=symbol [3]=direction [4]=in/out
        # [5]=lot [6]=price [10]=profit [12]=comment
        io = cells[4].strip().lower()
        time_str = cells[0].strip()[:19]  # FIXED: time is col 0
        direction = cells[3].strip().lower()  # FIXED: direction is col 3
        try: pnl = float(cells[10].strip().replace(' ','').replace(',',''))
        except: pnl = 0.0

        if 'in' in io:
            pending.append({'time_str': time_str, 'direction': direction})
        elif 'out' in io and pending:
            entry = pending.pop(0)
            try: et = datetime.strptime(entry['time_str'], '%Y.%m.%d %H:%M:%S')
            except: et = None
            trades.append({
                'hour': et.hour if et else -1,
                'dow': et.weekday() if et else -1,
                'day': et.day if et else -1,
                'direction': entry['direction'],
                'pnl': pnl,
            })
    return trades


def analyze(configs, label):
    """Aggregate hourly/directional/DOW stats across configs."""
    all_trades = []
    for cfg in configs:
        all_trades.extend(parse_trades_with_hour(REPORTS.get(f'{cfg}_2505', Path(''))))
        all_trades.extend(parse_trades_with_hour(REPORTS.get(f'{cfg}_2605', Path(''))))

    # Hourly stats by month
    trades_2505 = [t for t in all_trades if t['hour'] >= 0]
    trades_2605 = [t for t in all_trades if t['hour'] >= 0]

    # Actually, separate by filename
    for month_label, cfg_list in [('2505', ['OFF_2505', 'LOOSE_2505', 'cd_REF_2505']),
                                    ('2605', ['OFF_2605', 'LOOSE_2605', 'cd_REF_2605'])]:
        month_trades = []
        for cfg in cfg_list:
            month_trades.extend(parse_trades_with_hour(REPORTS.get(cfg, Path(''))))

        if not month_trades: continue

        n = len(month_trades)
        nw = len([t for t in month_trades if t['pnl'] > 0])

        # Hourly
        hour_stats = defaultdict(list)
        for t in month_trades:
            if t['hour'] >= 0:
                hour_stats[t['hour']].append(t['pnl'])

        print(f"\n{'='*80}")
        print(f"  [{month_label}] {n}T, WR={nw/n*100:.1f}%")
        print(f"{'='*80}")

        print(f"\n  --- Hourly WR ---")
        print(f"  {'H':>4} {'Trades':>6} {'WR':>7} {'PnL':>10} {'AvgPnL':>8}  Bar")
        for h in sorted(hour_stats.keys()):
            pnls = hour_stats[h]
            wr = len([p for p in pnls if p > 0]) / len(pnls) * 100
            total = sum(pnls)
            avg = total / len(pnls)
            bar_len = max(1, int(abs(total) / max(5, abs(total)/10 or 1)))
            bar = '#' * bar_len
            sign = '+' if total > 0 else '-'
            print(f"  {h:>3}:00 {len(pnls):>6} {wr:>6.1f}% ${total:>+9.0f} ${avg:>+7.2f} {sign}{bar}")

        # Directional
        buys = [t for t in month_trades if t['direction'] == 'buy']
        sells = [t for t in month_trades if t['direction'] == 'sell']
        buy_wr = len([t for t in buys if t['pnl'] > 0]) / len(buys) * 100 if buys else 0
        sell_wr = len([t for t in sells if t['pnl'] > 0]) / len(sells) * 100 if sells else 0
        print(f"\n  --- Direction ---")
        print(f"  Buy:  {len(buys):>5}T WR={buy_wr:>5.1f}% PnL=${sum(t['pnl'] for t in buys):>+9.2f}")
        print(f"  Sell: {len(sells):>5}T WR={sell_wr:>5.1f}% PnL=${sum(t['pnl'] for t in sells):>+9.2f}")

        # DOW
        dow_names = ['Mon','Tue','Wed','Thu','Fri']
        dow_stats = defaultdict(list)
        for t in month_trades:
            if 0 <= t['dow'] <= 4:  # weekdays only
                dow_stats[t['dow']].append(t['pnl'])

        print(f"\n  --- Day of Week ---")
        for d in range(5):
            pnls = dow_stats.get(d, [])
            if pnls:
                wr = len([p for p in pnls if p > 0]) / len(pnls) * 100
                total = sum(pnls)
                print(f"  {dow_names[d]}: {len(pnls):>5}T WR={wr:>5.1f}% PnL=${total:>+9.0f}")

        # Hour x Direction
        print(f"\n  --- Worst Hours (by PnL, min 5 trades) ---")
        hour_ranked = sorted(hour_stats.items(), key=lambda x: sum(x[1]))
        for h, pnls in hour_ranked[:5]:
            if len(pnls) >= 5:
                wr = len([p for p in pnls if p > 0]) / len(pnls) * 100
                print(f"  H{h:02d}: {len(pnls)}T WR={wr:.0f}% PnL=${sum(pnls):+.0f}")

    # Cross-month comparison: find hours bad in 2605 but OK in 2505
    print(f"\n{'='*80}")
    print(f"  CROSS-MONTH: Hours bad in 2605 but OK in 2505")
    print(f"{'='*80}")

    # Use OFF configs for clean comparison
    off_2505 = parse_trades_with_hour(REPORTS['OFF_2505'])
    off_2605 = parse_trades_with_hour(REPORTS['OFF_2605'])

    h25 = defaultdict(list)
    h26 = defaultdict(list)
    for t in off_2505:
        if t['hour'] >= 0: h25[t['hour']].append(t['pnl'])
    for t in off_2605:
        if t['hour'] >= 0: h26[t['hour']].append(t['pnl'])

    print(f"  {'Hour':>5} {'2505 T':>7} {'2505 WR':>8} {'2505 PnL':>10} | {'2605 T':>7} {'2605 WR':>8} {'2605 PnL':>10} | {'Candidate?':>10}")
    print(f"  {'-'*80}")

    bad_hours_2605 = []
    for h in sorted(set(list(h25.keys()) + list(h26.keys()))):
        p25 = h25.get(h, [])
        p26 = h26.get(h, [])
        wr25 = len([p for p in p25 if p > 0]) / len(p25) * 100 if p25 else 0
        wr26 = len([p for p in p26 if p > 0]) / len(p26) * 100 if p26 else 0
        total25 = sum(p25) if p25 else 0
        total26 = sum(p26) if p26 else 0

        # Candidate: bad in 2605 (WR<45% or PnL<0) but OK in 2505 (WR>50%)
        is_bad_2605 = (wr26 < 45 and len(p26) >= 5)
        is_ok_2505 = (wr25 >= 50 and len(p25) >= 3) or len(p25) < 3
        candidate = "*** BLOCK" if (is_bad_2605 and is_ok_2505 and len(p26) >= 5) else ""

        if len(p25) >= 3 or len(p26) >= 5:  # meaningful
            print(f"  {h:>4}:00 {len(p25):>7} {wr25:>7.1f}% ${total25:>+9.0f} | {len(p26):>7} {wr26:>7.1f}% ${total26:>+9.0f} | {candidate:>10}")

        if candidate:
            bad_hours_2605.append(str(h))

    if bad_hours_2605:
        csv = ','.join(bad_hours_2605)
        print(f"\n  --> InpNoEntryHours={csv}")
        # Calculate how much PnL blocking these hours would save/earn
        saved_2605 = sum(sum(p26) for h in [int(x) for x in bad_hours_2605] if h in h26)
        lost_2505 = sum(sum(p25) for h in [int(x) for x in bad_hours_2605] if h in h25)
        print(f"  2605 PnL in blocked hours: ${saved_2605:+.0f}")
        print(f"  2505 PnL in blocked hours: ${lost_2505:+.0f}")
        print(f"  Net effect: ${lost_2505 + saved_2605:+.0f}")

# ===== MAIN =====
# Run cross-month comparison
off_2505 = parse_trades_with_hour(REPORTS['OFF_2505'])
off_2605 = parse_trades_with_hour(REPORTS['OFF_2605'])
loose_2505 = parse_trades_with_hour(REPORTS['LOOSE_2505'])
loose_2605 = parse_trades_with_hour(REPORTS['LOOSE_2605'])

print(f"Loaded: OFF_2505={len(off_2505)}T, OFF_2605={len(off_2605)}T")
print(f"        LOOSE_2505={len(loose_2505)}T, LOOSE_2605={len(loose_2605)}T")

for label, trades in [("2505 OFF", off_2505), ("2605 OFF", off_2605),
                       ("2505 LOOSE", loose_2505), ("2605 LOOSE", loose_2605)]:
    if not trades: continue
    n = len(trades)
    nw = len([t for t in trades if t['pnl'] > 0])
    print(f"\n{'='*80}")
    print(f"  [{label}] {n}T, WR={nw/n*100:.1f}%, Total PnL=${sum(t['pnl'] for t in trades):+,.2f}")
    print(f"{'='*80}")

    # Hourly
    hour_stats = defaultdict(list)
    for t in trades:
        if t['hour'] >= 0: hour_stats[t['hour']].append(t['pnl'])

    print(f"\n  --- Hourly WR ---")
    for h in sorted(hour_stats.keys()):
        pnls = hour_stats[h]
        if len(pnls) < 3: continue
        wr = len([p for p in pnls if p > 0]) / len(pnls) * 100
        total = sum(pnls)
        bar_len = max(1, int(abs(total) / max(3, abs(total)/8 or 1)))
        bar = '#' * bar_len
        sign = '+' if total > 0 else '-'
        print(f"  H{h:02d}: {len(pnls):>4}T WR={wr:>5.1f}% PnL=${total:>+8.0f} {sign}{bar}")

    # Direction
    buys = [t for t in trades if t.get('direction') == 'buy']
    sells = [t for t in trades if t.get('direction') == 'sell']
    buy_wr = len([t for t in buys if t['pnl'] > 0]) / len(buys) * 100 if buys else 0
    sell_wr = len([t for t in sells if t['pnl'] > 0]) / len(sells) * 100 if sells else 0
    print(f"\n  Buy:  {len(buys)}T WR={buy_wr:.1f}% PnL=${sum(t['pnl'] for t in buys):+,.2f}")
    print(f"  Sell: {len(sells)}T WR={sell_wr:.1f}% PnL=${sum(t['pnl'] for t in sells):+,.2f}")

    # DOW
    dow_names = ['Mon','Tue','Wed','Thu','Fri']
    dow_stats = defaultdict(list)
    for t in trades:
        if 0 <= t['dow'] <= 4:
            dow_stats[t['dow']].append(t['pnl'])
    print(f"\n  --- Day of Week ---")
    for d in range(5):
        pnls = dow_stats.get(d, [])
        if len(pnls) >= 5:
            wr = len([p for p in pnls if p > 0]) / len(pnls) * 100
            print(f"  {dow_names[d]}: {len(pnls):>4}T WR={wr:>5.1f}% PnL=${sum(pnls):>+8.0f}")

# Cross-month: find hours bad in 2605 but OK in 2505
print(f"\n{'='*80}")
print(f"  CROSS-MONTH HOUR ANALYSIS: 2605-bad + 2505-OK = BLOCK CANDIDATES")
print(f"{'='*80}")
h25 = defaultdict(list)
h26 = defaultdict(list)
for t in off_2505:
    if t['hour'] >= 0: h25[t['hour']].append(t['pnl'])
for t in off_2605:
    if t['hour'] >= 0: h26[t['hour']].append(t['pnl'])

print(f"  {'H':>5} {'2505 T':>7} {'WR%':>7} {'PnL':>10} | {'2605 T':>7} {'WR%':>7} {'PnL':>10} | {'Note'}")
print(f"  {'-'*75}")
bad_hours = []
for h in sorted(set(list(h25.keys()) + list(h26.keys()))):
    p25 = h25.get(h, [])
    p26 = h26.get(h, [])
    wr25 = len([p for p in p25 if p > 0])/len(p25)*100 if p25 else 0
    wr26 = len([p for p in p26 if p > 0])/len(p26)*100 if p26 else 0
    t25 = sum(p25) if p25 else 0
    t26 = sum(p26) if p26 else 0
    is_bad = (t26 < 0 and len(p26) >= 5)
    is_ok = (t25 >= 0 or len(p25) < 5)
    note = "*** BLOCK" if (is_bad and is_ok) else ""
    if len(p25) >= 3 or len(p26) >= 5:
        print(f"  {h:>4}:00 {len(p25):>7} {wr25:>6.1f}% ${t25:>+9.0f} | {len(p26):>7} {wr26:>6.1f}% ${t26:>+9.0f} | {note}")
    if is_bad and is_ok: bad_hours.append(h)

if bad_hours:
    csv = ','.join(str(h) for h in bad_hours)
    total26_bad = sum(sum(p26) for h in bad_hours if h in h26)
    total25_bad = sum(sum(p25) for h in bad_hours if h in h25)
    print(f"\n  Block hours: {csv}")
    print(f"  2605 PnL blocked: ${total26_bad:+.0f} ({len([t for h in bad_hours for t in off_2605 if t['hour']==h])}T)")
    print(f"  2505 PnL blocked: ${total25_bad:+.0f} ({len([t for h in bad_hours for t in off_2505 if t['hour']==h])}T)")
    print(f"  Net: ${total25_bad + total26_bad:+.0f}")

print(f"\n[DONE]")
