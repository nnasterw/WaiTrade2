#!/usr/bin/env python3
"""Correlate entry features (from EA log) with trade PnL (from HTML reports).
Key features: bounce_ob, bounce_sec, confirm_pos, direction, position_mult, lot.
Goal: find which features separate winners from losers in 2605 vs 2505."""
import re, sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

LOG_PATH = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/Tester/logs/20260606.log')
MT5_DATA = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075')

def parse_html_trades(htm_path):
    """Extract trades from HTML report with sequence numbers."""
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
        io = cells[4].strip().lower()
        price = float(cells[7].strip().replace(' ','').replace(',','')) if cells[7].strip() else 0
        try: pnl = float(cells[10].strip().replace(' ','').replace(',',''))
        except: pnl = 0.0
        if 'in' in io:
            pending.append(price)
        elif 'out' in io and pending:
            entry_p = pending.pop(0)
            trades.append({'entry_price': entry_p, 'exit_price': price, 'pnl': pnl})
    return trades

def parse_log_entries(log_path, target_from=None, target_to=None):
    """Parse EA log for trade entry features within a time range."""
    raw = log_path.read_bytes()
    text = raw.decode('utf-16-le', errors='replace')
    lines = text.split('\n')

    entries = []  # (timestamp, ticket, features)
    deals_in = []  # (timestamp, ticket)
    deals_out = []  # (timestamp, ticket)

    in_test = False
    test_from = None
    test_to = None

    for line in lines:
        # Detect test start
        m = re.search(r'testing of.*from (\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}) to (\d{4}\.\d{2}\.\d{2} \d{2}:\d{2})', line)
        if m:
            test_from = m.group(1)
            test_to = m.group(2)
            if not target_from:
                continue

        # Extract trade entries (成功 entry with ticket)
        m = re.search(r'(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2}).*ticket=(\d+).*price=([\d\.]+).*lot=([\d\.]+)', line)
        if m:
            ts = m.group(1)
            ticket = int(m.group(2))
            price = float(m.group(3))
            lot = float(m.group(4))

            feat = {'ticket': ticket, 'price': price, 'lot': lot}
            # Parse additional features
            for key in ['bounce_sec', 'bounce_ob', 'confirm_pos']:
                fm = re.search(rf'{key}=([\-\d\.]+)', line)
                if fm: feat[key] = float(fm.group(1))
            # Direction
            if ' S ' in line: feat['dir'] = 'sell'
            elif ' B ' in line: feat['dir'] = 'buy'
            # Position multiplier
            xm = re.search(r'x([\d\.]+)', line)
            if xm: feat['mult'] = float(xm.group(1))

            entries.append((ts, ticket, feat))
            continue

        # Extract deal entries (entry/exit)
        m = re.search(r'(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2}).*deal #(\d+) (buy|sell)', line)
        if m:
            ts = m.group(1)
            ticket = int(m.group(2))
            side = m.group(3)
            if side == 'buy':
                deals_in.append((ts, ticket))
            else:
                deals_out.append((ts, ticket))

    return entries, deals_in, deals_out


# ===== MAIN =====
# Analyze the cd_REF backtest (P1: H5+AD-LOOSE, should be one of the last tests)
# Match with HTML report trades
print("Parsing EA log for trade entries...")
entries, deals_in, deals_out = parse_log_entries(LOG_PATH)
print(f"Trade entries: {len(entries)}, Deals in: {len(deals_in)}, Deals out: {len(deals_out)}")

# Parse HTML reports
ref_2505_trades = parse_html_trades(MT5_DATA / 'cd_REF_2505.htm')
ref_2605_trades = parse_html_trades(MT5_DATA / 'cd_REF_2605.htm')
off_2605_trades = parse_html_trades(MT5_DATA / 'nkss_REF_OFF_2605.htm')
print(f"cd_REF 2505 HTML: {len(ref_2505_trades)} trades")
print(f"cd_REF 2605 HTML: {len(ref_2605_trades)} trades")
print(f"REF_OFF 2605 HTML: {len(off_2605_trades)} trades")

# Try simple correlation: match entries by price with HTML trades
# Since we have entry prices from both sources, we can match them
matched_2505 = []
matched_2605 = []

# For each entry, find closest HTML trade by entry price and time sequence
# We'll match sequentially since trades should be in order
# Let's focus on 2605 where we need the most insight
if ref_2605_trades and entries:
    # Find entries that look like they belong to 2605 (date in 2026.05)
    entries_2605 = [(ts, t, f) for ts, t, f in entries if '2026.05' in ts]
    print(f"\nEntries with 2026.05 date: {len(entries_2605)}")

    # Try sequential matching
    n_match = min(len(entries_2605), len(ref_2605_trades))
    print(f"Sequential matching first {n_match} entries...")

    # Feature correlation
    features_by_pnl = defaultdict(list)

    for i in range(n_match):
        ts, ticket, feat = entries_2605[i]
        trade = ref_2605_trades[i]
        pnl = trade['pnl']

        for key in ['bounce_sec', 'bounce_ob', 'confirm_pos', 'lot', 'mult']:
            if key in feat:
                features_by_pnl[key].append((pnl, feat[key]))

    # Analyze feature correlations
    print(f"\n--- Feature vs PnL Correlation (2605, first {n_match} trades) ---")
    for key, values in features_by_pnl.items():
        if len(values) < 10: continue
        wins = [(p, v) for p, v in values if p > 0]
        losses = [(p, v) for p, v in values if p <= 0]
        if wins and losses:
            avg_v_win = sum(v for _, v in wins) / len(wins)
            avg_v_loss = sum(v for _, v in losses) / len(losses)
            avg_pnl_win = sum(p for p, _ in wins) / len(wins)
            avg_pnl_loss = sum(p for p, _ in losses) / len(losses)
            print(f"  {key:<15}: Win={avg_v_win:.3f} (n={len(wins)}) Loss={avg_v_loss:.3f} (n={len(losses)}) "
                  f"Diff={avg_v_win-avg_v_loss:+.3f}")

    # Bucket analysis: group by feature ranges
    print(f"\n--- Bucket Analysis: bounce_ob vs WR (2605) ---")
    bounce_vals = [(pnl, v) for pnl, v in features_by_pnl.get('bounce_ob', [])]
    if bounce_vals:
        boundaries = [0.20, 0.22, 0.24, 0.26, 0.28]
        for i in range(len(boundaries)-1):
            lo, hi = boundaries[i], boundaries[i+1]
            bucket = [(p, v) for p, v in bounce_vals if lo <= v < hi]
            if bucket:
                wr = len([p for p, v in bucket if p > 0]) / len(bucket) * 100
                avg_pnl = sum(p for p, v in bucket) / len(bucket)
                print(f"  bounce_ob [{lo:.2f}-{hi:.2f}): {len(bucket)}T, WR={wr:.1f}%, avgPnL=${avg_pnl:+.3f}")

    print(f"\n--- Bucket Analysis: bounce_sec vs WR (2605) ---")
    sec_vals = [(pnl, v) for pnl, v in features_by_pnl.get('bounce_sec', [])]
    if sec_vals:
        boundaries = [0, 5, 10, 30, 60, 300]
        for i in range(len(boundaries)-1):
            lo, hi = boundaries[i], boundaries[i+1]
            bucket = [(p, v) for p, v in sec_vals if lo <= v < hi]
            if bucket:
                wr = len([p for p, v in bucket if p > 0]) / len(bucket) * 100
                avg_pnl = sum(p for p, v in bucket) / len(bucket)
                print(f"  bounce_sec [{lo}-{hi}s): {len(bucket)}T, WR={wr:.1f}%, avgPnL=${avg_pnl:+.3f}")

    print(f"\n--- Position Multiplier vs WR (2605) ---")
    mult_vals = [(pnl, v) for pnl, v in features_by_pnl.get('mult', [])]
    if mult_vals:
        multipliers = sorted(set(v for _, v in mult_vals))
        for m in multipliers:
            bucket = [(p, v) for p, v in mult_vals if v == m]
            wr = len([p for p, v in bucket if p > 0]) / len(bucket) * 100
            avg_pnl = sum(p for p, v in bucket) / len(bucket)
            print(f"  mult x{m:.1f}: {len(bucket)}T, WR={wr:.1f}%, avgPnL=${avg_pnl:+.3f}")

    # Direction analysis
    print(f"\n--- Direction vs WR (2605) ---")
    for d in ['buy', 'sell']:
        dir_trades = [(ts, t, f) for ts, t, f in entries_2605[:n_match] if f.get('dir') == d]
        dir_pnls = [ref_2605_trades[i]['pnl'] for i in range(min(len(dir_trades), len(ref_2605_trades)))]
        if dir_pnls:
            wr = len([p for p in dir_pnls if p > 0]) / len(dir_pnls) * 100
            print(f"  {d}: {len(dir_pnls)}T, WR={wr:.1f}%, totalPnL=${sum(dir_pnls):+.2f}")

print(f"\n[DONE]")
