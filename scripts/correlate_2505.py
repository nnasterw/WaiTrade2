#!/usr/bin/env python3
"""Correlate entry features with trade PnL for 2505 (good month).
Critical: ensure proposed changes don't hurt big winners in 2505."""
import re, sys
from pathlib import Path
from collections import defaultdict, Counter

LOG_PATH = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/Tester/logs/20260606.log')
MT5_DATA = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075')

def parse_html_trades(htm_path):
    if not htm_path.exists(): return []
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    pending, trades = [], []
    for r in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
        if len(cells) != 13: continue
        if cells[3].strip().lower() == 'balance': continue
        io = cells[4].strip().lower()
        price = float(cells[7].strip().replace(' ','').replace(',','')) if cells[7].strip() else 0
        try: pnl = float(cells[10].strip().replace(' ','').replace(',',''))
        except: pnl = 0.0
        if 'in' in io: pending.append(price)
        elif 'out' in io and pending:
            pending.pop(0)
            trades.append({'pnl': pnl})
    return trades

def parse_log_entries_2505(log_path):
    raw = log_path.read_bytes()
    text = raw.decode('utf-16-le', errors='replace')
    lines = text.split('\n')
    entries = []
    for line in lines:
        m = re.search(r'(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2}).*ticket=(\d+).*price=([\d\.]+).*lot=([\d\.]+)', line)
        if not m: continue
        ts, ticket, price, lot = m.group(1), int(m.group(2)), float(m.group(3)), float(m.group(4))
        feat = {'ticket': ticket, 'price': price, 'lot': lot, 'ts': ts}
        for key in ['bounce_sec', 'bounce_ob', 'confirm_pos']:
            fm = re.search(rf'{key}=([\-\d\.]+)', line)
            if fm: feat[key] = float(fm.group(1))
        xm = re.search(r'x([\d\.]+)', line)
        if xm: feat['mult'] = float(xm.group(1))
        if ' S ' in line: feat['dir'] = 'sell'
        elif ' B ' in line: feat['dir'] = 'buy'
        entries.append((ts, ticket, feat))
    return entries

# ===== MAIN =====
entries = parse_log_entries_2505(LOG_PATH)
ref_2505_trades = parse_html_trades(MT5_DATA / 'cd_REF_2505.htm')
ref_2605_trades = parse_html_trades(MT5_DATA / 'cd_REF_2605.htm')

print(f"Trade entries: {len(entries)}")
print(f"2505 HTML trades: {len(ref_2505_trades)}")
print(f"2605 HTML trades: {len(ref_2605_trades)}")

# Analyze 2505
entries_2505 = [(ts, t, f) for ts, t, f in entries if '2025.05' in ts]
print(f"Entries with 2025.05 date: {len(entries_2505)}")
n25 = min(len(entries_2505), len(ref_2505_trades))

# Also analyze 2605
entries_2605 = [(ts, t, f) for ts, t, f in entries if '2026.05' in ts]
n26 = min(len(entries_2605), len(ref_2605_trades))

for label, entry_list, trades, n in [('2505', entries_2505, ref_2505_trades, n25),
                                       ('2605', entries_2605, ref_2605_trades, n26)]:
    print(f"\n{'='*70}")
    print(f"  [{label}] Feature vs PnL — {n} matched trades")
    print(f"{'='*70}")

    # bounce_sec buckets
    print(f"\n--- bounce_sec vs WR ---")
    sec_buckets = defaultdict(list)
    for i in range(n):
        if i >= len(entry_list): break
        _, _, feat = entry_list[i]
        pnl = trades[i]['pnl']
        bs = feat.get('bounce_sec', 0)
        if bs < 5: sec_buckets['<5s'].append(pnl)
        elif bs < 10: sec_buckets['5-10s'].append(pnl)
        elif bs < 30: sec_buckets['10-30s'].append(pnl)
        else: sec_buckets['30s+'].append(pnl)
    for bkt in ['<5s', '5-10s', '10-30s', '30s+']:
        vals = sec_buckets[bkt]
        if not vals: continue
        wr = len([v for v in vals if v > 0]) / len(vals) * 100
        total = sum(vals)
        # BIG winners: > p80 of all wins
        all_wins = sorted([trades[i]['pnl'] for i in range(n) if trades[i]['pnl'] > 0])
        big_thresh = all_wins[len(all_wins)*4//5] if all_wins else 0
        big_wins = [v for v in vals if v >= big_thresh]
        print(f"  {bkt:<10}: {len(vals):>4}T WR={wr:>5.1f}% PnL=${total:>+8.2f} big_wins={len(big_wins)} (>{big_thresh:.1f})")

    # bounce_ob buckets
    print(f"\n--- bounce_ob vs WR ---")
    ob_buckets = defaultdict(list)
    for i in range(n):
        if i >= len(entry_list): break
        _, _, feat = entry_list[i]
        pnl = trades[i]['pnl']
        bo = feat.get('bounce_ob', 0)
        if bo < 0.22: ob_buckets['<0.22'].append(pnl)
        elif bo < 0.24: ob_buckets['0.22-0.24'].append(pnl)
        elif bo < 0.26: ob_buckets['0.24-0.26'].append(pnl)
        elif bo < 0.28: ob_buckets['0.26-0.28'].append(pnl)
        else: ob_buckets['0.28+'].append(pnl)
    for bkt in ['<0.22', '0.22-0.24', '0.24-0.26', '0.26-0.28', '0.28+']:
        vals = ob_buckets[bkt]
        if not vals: continue
        wr = len([v for v in vals if v > 0]) / len(vals) * 100
        total = sum(vals)
        all_wins_all = sorted([trades[i]['pnl'] for i in range(n) if trades[i]['pnl'] > 0])
        big_thresh = all_wins_all[len(all_wins_all)*4//5] if all_wins_all else 0
        big_wins = [v for v in vals if v >= big_thresh]
        print(f"  {bkt:<12}: {len(vals):>4}T WR={wr:>5.1f}% PnL=${total:>+8.2f} big_wins={len(big_wins)}")

    # Position multiplier buckets
    print(f"\n--- Position Multiplier vs WR ---")
    mult_buckets = defaultdict(list)
    for i in range(n):
        if i >= len(entry_list): break
        _, _, feat = entry_list[i]
        pnl = trades[i]['pnl']
        m = feat.get('mult', 0)
        mult_buckets[m].append(pnl)
    for m in sorted(mult_buckets.keys()):
        vals = mult_buckets[m]
        wr = len([v for v in vals if v > 0]) / len(vals) * 100
        total = sum(vals)
        print(f"  x{m:.1f}: {len(vals):>4}T WR={wr:>5.1f}% PnL=${total:>+8.2f}")

    # Direction
    print(f"\n--- Direction ---")
    dir_pnls = {'buy': [], 'sell': []}
    for i in range(n):
        if i >= len(entry_list): break
        _, _, feat = entry_list[i]
        pnl = trades[i]['pnl']
        d = feat.get('dir', '?')
        dir_pnls[d].append(pnl)
    for d in ['buy', 'sell']:
        vals = dir_pnls[d]
        if vals:
            wr = len([v for v in vals if v > 0]) / len(vals) * 100
            print(f"  {d}: {len(vals)}T WR={wr:.1f}% PnL=${sum(vals):+.2f}")

# Cross-month comparison: does filtering by bounce_sec [5-10s] help 2605 without hurting 2505?
print(f"\n{'='*70}")
print(f"  CROSS-MONTH: Impact of bounce_sec filter [5-15s]")
print(f"{'='*70}")

for label, entry_list, trades, n in [('2505', entries_2505, ref_2505_trades, n25),
                                       ('2605', entries_2605, ref_2605_trades, n26)]:
    kept = []
    removed = []
    for i in range(n):
        if i >= len(entry_list): break
        _, _, feat = entry_list[i]
        pnl = trades[i]['pnl']
        bs = feat.get('bounce_sec', 0)
        if 2 <= bs <= 15:
            kept.append(pnl)
        else:
            removed.append(pnl)

    kept_wr = len([v for v in kept if v > 0]) / len(kept) * 100 if kept else 0
    removed_wr = len([v for v in removed if v > 0]) / len(removed) * 100 if removed else 0
    print(f"  [{label}] Kept({len(kept)}T): WR={kept_wr:.1f}%, PnL=${sum(kept):+.2f} | "
          f"Removed({len(removed)}T): WR={removed_wr:.1f}%, PnL=${sum(removed):+.2f}")
    print(f"    Net change vs all: ${sum(kept) - sum(trades[i]['pnl'] for i in range(len(kept)+len(removed))):+.2f}")

print(f"\n[DONE]")
