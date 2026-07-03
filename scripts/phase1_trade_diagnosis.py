#!/usr/bin/env python3
"""Phase 1: Per-trade diagnosis — extract independent features from MT5 HTML reports.
Features: hold_time, direction, pnl, exit_reason, time_of_day, price_move.
Compare: 2505 vs 2605 (REF_OFF baseline), C4 vs C2 (2605 noise gate loose vs tight)."""
import re, sys
from pathlib import Path
from collections import Counter, defaultdict

MT5_DATA = Path('C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075')

REPORTS = {
    'REF_OFF_2505': MT5_DATA / 'nkss_REF_OFF_2505.htm',
    'REF_OFF_2605': MT5_DATA / 'nkss_REF_OFF_2605.htm',
    'C2_2605':      MT5_DATA / 'nkss_C2_2605.htm',      # strict filter: range=0.14, profitable
    'C4_2605':      MT5_DATA / 'nkss_C4_2605.htm',      # loose filter: range=0.22, losing
    'C4_2505':      MT5_DATA / 'nkss_C4_2505.htm',      # loose filter: 2505 baseline
    'C2_2505':      MT5_DATA / 'nkss_C2_2505.htm',      # strict filter: 2505 killed
    'REF_LOOSE_2505': MT5_DATA / 'nkss_REF_LOOSE_2505.htm',
    'REF_LOOSE_2605': MT5_DATA / 'nkss_REF_LOOSE_2605.htm',
    'A2_2505':      MT5_DATA / 'nkss_A2_2505.htm',      # lb15/r30/a18
    'A2_2605':      MT5_DATA / 'nkss_A2_2605.htm',
}

EXIT_PATTERNS = {
    'sl': re.compile(r'\[sl\]', re.I),
    'be': re.compile(r'\[be\]|\[breakeven\]', re.I),
    'tp': re.compile(r'\[tp\]', re.I),
    'dtp': re.compile(r'\[dtp\]', re.I),
    'trail': re.compile(r'\[trail\]|\[trailing\]', re.I),
    'timeout': re.compile(r'\[timeout\]|\[time.?exit\]|bar.?exit', re.I),
    'reverse': re.compile(r'\[reverse\]', re.I),
    'mfe': re.compile(r'\[mfe\]', re.I),
}

def parse_trades(htm_path):
    """Extract per-trade data from MT5 HTML report.
    Returns list of dicts: {entry_time, exit_time, hold_sec, direction, pnl,
                            entry_price, exit_price, exit_reason, comment, hour}"""
    if not htm_path.exists():
        print(f"MISSING: {htm_path}")
        return []

    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)

    pending = []  # FIFO queue of (entry_time, entry_price, direction, comment)
    trades = []

    for r in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
        if len(cells) != 13:
            continue
        if cells[3].strip().lower() == 'balance':
            continue

        io = cells[4].strip()           # in/deal / out/deal
        time_str = cells[1].strip()     # entry/exit time
        price_str = cells[7].strip()    # price
        comment = cells[12].strip()     # comment
        direction = cells[5].strip().lower()  # buy/sell

        try:
            pnl = float(cells[10].strip().replace(' ', '').replace(',', ''))
        except ValueError:
            pnl = 0.0

        try:
            price = float(price_str.replace(' ', '').replace(',', ''))
        except ValueError:
            price = 0.0

        if io.lower() in ('in', 'in/deal'):
            pending.append({
                'entry_time': time_str,
                'entry_price': price,
                'direction': direction,
                'comment_in': comment,
            })
        elif io.lower() in ('out', 'out/deal') and pending:
            entry = pending.pop(0)

            # Parse hold time
            try:
                et_parts = entry['entry_time'].replace('.', '-').replace(' ', ':').split(':')
                xt_parts = time_str.replace('.', '-').replace(' ', ':').split(':')
                # Format: "2025.05.15 14:30:02"
                from datetime import datetime
                et = datetime.strptime(entry['entry_time'][:19], '%Y.%m.%d %H:%M:%S')
                xt = datetime.strptime(time_str[:19], '%Y.%m.%d %H:%M:%S')
                hold_sec = (xt - et).total_seconds()
            except:
                hold_sec = 0

            # Parse exit reason from comment
            exit_reason = 'unknown'
            for reason, pattern in EXIT_PATTERNS.items():
                if pattern.search(comment):
                    exit_reason = reason
                    break
            if exit_reason == 'unknown' and 'sl' in comment.lower():
                exit_reason = 'sl'

            # Parse hour of day (server time)
            try:
                hour = int(entry['entry_time'][11:13])
            except:
                hour = -1

            # Price move (positive = favorable)
            if entry['direction'] == 'buy':
                price_move = price - entry['entry_price']
            else:
                price_move = entry['entry_price'] - price

            trades.append({
                'entry_time': entry['entry_time'],
                'exit_time': time_str,
                'hold_sec': hold_sec,
                'direction': entry['direction'],
                'pnl': pnl,
                'entry_price': entry['entry_price'],
                'exit_price': price,
                'price_move': price_move,
                'exit_reason': exit_reason,
                'comment': comment,
                'hour': hour,
            })

    return trades


def analyze(trades, label):
    """Print per-trade diagnosis for a dataset."""
    if not trades:
        print(f"\n  [{label}] NO TRADES")
        return None

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]
    flat = [t for t in trades if t['pnl'] == 0]

    n = len(trades)
    nw, nl = len(wins), len(losses)
    wr = nw / n * 100 if n else 0

    total_pnl = sum(t['pnl'] for t in trades)
    gw = sum(t['pnl'] for t in wins) if wins else 0
    gl = abs(sum(t['pnl'] for t in losses)) if losses else 0
    pf = gw / gl if gl > 0 else (999 if gw > 0 else 0)

    avg_w = gw / nw if nw else 0
    avg_l = gl / nl if nl else 0
    wl_ratio = avg_w / avg_l if avg_l > 0 else 0

    # Hold time distribution
    hold_buckets = Counter()
    for t in trades:
        h = t['hold_sec']
        if h < 10: hold_buckets['<10s'] += 1
        elif h < 60: hold_buckets['10-60s'] += 1
        elif h < 300: hold_buckets['1-5min'] += 1
        elif h < 1800: hold_buckets['5-30min'] += 1
        else: hold_buckets['>30min'] += 1

    # Hold time for losses
    loss_hold = Counter()
    for t in losses:
        h = t['hold_sec']
        if h < 10: loss_hold['<10s'] += 1
        elif h < 60: loss_hold['10-60s'] += 1
        elif h < 300: loss_hold['1-5min'] += 1
        elif h < 1800: loss_hold['5-30min'] += 1
        else: loss_hold['>30min'] += 1

    # Exit reason distribution
    exit_dist = Counter(t['exit_reason'] for t in trades)
    exit_win = Counter(t['exit_reason'] for t in wins)
    exit_loss = Counter(t['exit_reason'] for t in losses)

    # Hour of day distribution
    hour_dist = Counter(t['hour'] for t in trades if t['hour'] >= 0)
    hour_wr = {}
    for h in sorted(set(t['hour'] for t in trades if t['hour'] >= 0)):
        ht = [t for t in trades if t['hour'] == h]
        hw = len([t for t in ht if t['pnl'] > 0])
        hour_wr[h] = hw / len(ht) * 100 if ht else 0

    # Direction distribution
    buys = [t for t in trades if t['direction'] == 'buy']
    sells = [t for t in trades if t['direction'] == 'sell']
    buy_wr = len([t for t in buys if t['pnl'] > 0]) / len(buys) * 100 if buys else 0
    sell_wr = len([t for t in sells if t['pnl'] > 0]) / len(sells) * 100 if sells else 0

    # Print diagnosis
    print(f"\n{'='*80}")
    print(f"  [{label}] {n} trades, {nw}W/{nl}L/{len(flat)}F, WR={wr:.1f}%, PF={pf:.2f}")
    print(f"  Total PnL=${total_pnl:+,.2f}, avg_W=${avg_w:,.2f}, avg_L=${avg_l:,.2f}, W/L_ratio={wl_ratio:.2f}")
    print(f"{'='*80}")

    print(f"\n  --- Hold Time Distribution ---")
    print(f"  {'Bucket':<12} {'All':>6} {'%':>5}  {'Losses':>6} {'%':>5}")
    for b in ['<10s', '10-60s', '1-5min', '5-30min', '>30min']:
        a = hold_buckets.get(b, 0)
        l = loss_hold.get(b, 0)
        print(f"  {b:<12} {a:>6} {a/n*100:>4.1f}%  {l:>6} {l/nl*100 if nl else 0:>4.1f}%")

    # Loss hold time median
    loss_holds_sorted = sorted([t['hold_sec'] for t in losses])
    if loss_holds_sorted:
        med = loss_holds_sorted[len(loss_holds_sorted)//2]
        print(f"  Loss median hold: {med:.0f}s")
        # % losses < 10s
        pct_lt10 = len([h for h in loss_holds_sorted if h < 10]) / len(loss_holds_sorted) * 100
        print(f"  Losses <10s: {pct_lt10:.1f}% (noise kill indicator, >20% = SL too tight)")

    print(f"\n  --- Exit Reason Distribution ---")
    print(f"  {'Reason':<12} {'All':>6} {'%':>5}  {'Wins':>6} {'Losses':>6}")
    for reason in sorted(set(list(exit_dist.keys()) + list(exit_win.keys()) + list(exit_loss.keys()))):
        a = exit_dist.get(reason, 0)
        wc = exit_win.get(reason, 0)
        lc = exit_loss.get(reason, 0)
        print(f"  {reason:<12} {a:>6} {a/n*100:>4.1f}%  {wc:>6} {lc:>6}")

    print(f"\n  --- Direction ---")
    print(f"  Buy: {len(buys)} trades, WR={buy_wr:.1f}%")
    print(f"  Sell: {len(sells)} trades, WR={sell_wr:.1f}%")

    # Hourly WR
    print(f"\n  --- Hourly WR (server time) ---")
    for h in sorted(hour_wr.keys()):
        cnt = hour_dist.get(h, 0)
        wr_h = hour_wr[h]
        bar = '#' * int(wr_h / 5)
        print(f"  H{h:02d}: {cnt:>4}T  WR={wr_h:>5.1f}%  {bar}")

    return {
        'n': n, 'wr': wr, 'pf': pf, 'total_pnl': total_pnl,
        'avg_w': avg_w, 'avg_l': avg_l, 'wl_ratio': wl_ratio,
        'loss_median_hold': loss_holds_sorted[len(loss_holds_sorted)//2] if loss_holds_sorted else 0,
        'pct_lt10s': pct_lt10 if loss_holds_sorted else 0,
        'exit_dist': dict(exit_dist),
        'hour_wr': hour_wr,
    }


# ===== MAIN =====
print("PHASE 1: Per-Trade Diagnosis — REF_OFF + Key Noise Gate Variants")
print("="*100)

# 1. Baselines: 2505 vs 2605
print("\n" + "="*100)
print("  [A] BASELINE: QS3 OFF — 2505(good) vs 2605(bad)")
print("="*100)
r_off_25 = analyze(parse_trades(REPORTS['REF_OFF_2505']), 'REF_OFF 2505 (good)')
r_off_26 = analyze(parse_trades(REPORTS['REF_OFF_2605']), 'REF_OFF 2605 (bad)')

# 2. Noise gate effect: C4(loose) vs C2(strict) in 2605
print("\n" + "="*100)
print("  [B] 2605 NOISE GATE: C4(loose a=0.22) vs C2(strict a=0.14)")
print("="*100)
r_c4_26 = analyze(parse_trades(REPORTS['C4_2605']), 'C4 2605 (loose, a=0.22, -$56)')
r_c2_26 = analyze(parse_trades(REPORTS['C2_2605']), 'C2 2605 (strict, a=0.14, +$5)')

# 3. Noise gate effect in 2505
print("\n" + "="*100)
print("  [C] 2505 NOISE GATE: C4(loose) vs C2(strict) vs REF_LOOSE")
print("="*100)
r_c4_25 = analyze(parse_trades(REPORTS['C4_2505']), 'C4 2505 (loose, a=0.22, +$1,699)')
r_c2_25 = analyze(parse_trades(REPORTS['C2_2505']), 'C2 2505 (strict, a=0.14, +$350)')
r_rl_25 = analyze(parse_trades(REPORTS['REF_LOOSE_2505']), 'REF_LOOSE 2505 (very loose, +$6,691)')
r_rl_26 = analyze(parse_trades(REPORTS['REF_LOOSE_2605']), 'REF_LOOSE 2605 (very loose, -$112)')

# 4. A2 in both months (moderate)
print("\n" + "="*100)
print("  [D] MODERATE: A2(lb15/r30/a18) in both months")
print("="*100)
r_a2_25 = analyze(parse_trades(REPORTS['A2_2505']), 'A2 2505 (moderate, +$1,383)')
r_a2_26 = analyze(parse_trades(REPORTS['A2_2605']), 'A2 2605 (moderate, -$48)')

# ===== Cross-comparison =====
print("\n" + "="*100)
print("  CROSS-COMPARISON: Key Diagnostics")
print("="*100)

# W/L ratio comparison
print(f"\n  {'Report':<32} {'Trades':>6} {'WR':>6} {'PF':>6} {'avg_W':>8} {'avg_L':>8} {'W/L':>6} {'LossMed':>8} {'<10s%':>6}")
print(f"  {'-'*95}")
for label, r in [('REF_OFF 2505 (good)', r_off_25), ('REF_OFF 2605 (bad)', r_off_26),
                  ('C4 2605 (loose a=0.22)', r_c4_26), ('C2 2605 (strict a=0.14)', r_c2_26),
                  ('C4 2505 (loose a=0.22)', r_c4_25), ('C2 2505 (strict a=0.14)', r_c2_25),
                  ('REF_LOOSE 2505', r_rl_25), ('REF_LOOSE 2605', r_rl_26),
                  ('A2 2505 (moderate)', r_a2_25), ('A2 2605 (moderate)', r_a2_26)]:
    if r:
        print(f"  {label:<32} {r['n']:>6} {r['wr']:>5.1f}% {r['pf']:>5.2f} "
              f"${r['avg_w']:>7.2f} ${r['avg_l']:>7.2f} {r['wl_ratio']:>5.2f} "
              f"{r['loss_median_hold']:>7.0f}s {r['pct_lt10s']:>5.1f}%")

# Key insights
print(f"\n{'='*80}")
print(f"  KEY FINDINGS")
print(f"{'='*80}")

if r_off_25 and r_off_26:
    print(f"\n  1. W/L RATIO SHIFT:")
    print(f"     2505: avg_W=${r_off_25['avg_w']:.2f}, avg_L=${r_off_25['avg_l']:.2f}, W/L={r_off_25['wl_ratio']:.2f}")
    print(f"     2605: avg_W=${r_off_26['avg_w']:.2f}, avg_L=${r_off_26['avg_l']:.2f}, W/L={r_off_26['wl_ratio']:.2f}")
    print(f"     DIFF: avg_W shift={r_off_26['avg_w']-r_off_25['avg_w']:+.2f}, avg_L shift={r_off_26['avg_l']-r_off_25['avg_l']:+.2f}")

if r_c4_26 and r_c2_26:
    print(f"\n  2. NOISE GATE EFFECT IN 2605:")
    print(f"     C4(loose a=0.22): {r_c4_26['n']}T, WR={r_c4_26['wr']:.1f}%, W/L={r_c4_26['wl_ratio']:.2f}")
    print(f"     C2(strict a=0.14): {r_c2_26['n']}T, WR={r_c2_26['wr']:.1f}%, W/L={r_c2_26['wl_ratio']:.2f}")
    print(f"     Filtered out {r_c4_26['n'] - r_c2_26['n']} trades, WR improved {r_c2_26['wr']-r_c4_26['wr']:+.1f}%")

if r_off_25 and r_off_26:
    # Exit reason comparison
    print(f"\n  3. EXIT REASON SHIFT (2505 -> 2605):")
    for reason in sorted(set(list(r_off_25['exit_dist'].keys()) + list(r_off_26['exit_dist'].keys()))):
        a = r_off_25['exit_dist'].get(reason, 0)
        b = r_off_26['exit_dist'].get(reason, 0)
        pa = a / r_off_25['n'] * 100
        pb = b / r_off_26['n'] * 100
        print(f"     {reason:<12}: {pa:>5.1f}% -> {pb:>5.1f}% (delta={pb-pa:+.1f}%)")

    # Loss median hold shift
    print(f"\n  4. LOSS HOLD TIME:")
    print(f"     2505 median loss hold: {r_off_25['loss_median_hold']:.0f}s, <10s%: {r_off_25['pct_lt10s']:.1f}%")
    print(f"     2605 median loss hold: {r_off_26['loss_median_hold']:.0f}s, <10s%: {r_off_26['pct_lt10s']:.1f}%")

print(f"\n[DONE - Phase 1 Diagnosis]")
