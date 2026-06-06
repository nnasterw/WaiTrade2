#!/usr/bin/env python3
"""Deep OB-level analysis: Match EA log entry features with HTML PnL.
Features: bounce_ob, bounce_sec, confirm_pos, touch/confirm price spread,
ob_age, touch_count, entry_count, strength, direction, position_mult.
Goal: find which OB/pressure features separate winners from losers."""
import re, sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

LOG_PATH = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/Tester/logs/20260606.log')
MT5_DATA = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075')

def parse_html_trades_pnl(htm_path):
    """Extract just PnL sequence from HTML report."""
    if not htm_path.exists(): return []
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    pending = []; trades = []
    for r in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
        if len(cells) != 13: continue
        if cells[3].strip().lower() == 'balance': continue
        io = cells[4].strip().lower()
        pnl_str = cells[10].strip().replace(' ','').replace(',','')
        try: pnl = float(pnl_str)
        except: pnl = 0.0
        if 'in' in io: pending.append(1)
        elif 'out' in io and pending:
            pending.pop(0); trades.append(pnl)
    return trades

def parse_log_trades_by_month(log_path):
    """Parse EA log for trade entries, grouped by month.
    Returns {month_tag: [(timestamp, features_dict), ...]}"""
    raw = log_path.read_bytes()
    text = raw.decode('utf-16-le', errors='replace')
    lines = text.split('\n')

    # Track which backtest we're in
    current_month = None
    trades_by_month = defaultdict(list)

    for line in lines:
        # Track backtest date range from "testing of..." lines
        m = re.search(r'testing of.*from (\d{4}\.\d{2}\.\d{2})', line)
        if m:
            from_dt = m.group(1)
            if '2025.05' in from_dt: current_month = '2505'
            elif '2026.05' in from_dt: current_month = '2605'
            else: current_month = None
            continue

        if not current_month: continue

        # Match trade entries: "���ֳɹ�: WT V11XAU-QS3 B x0.4 ticket=8 price=..."
        if 'ticket=' not in line or 'price=' not in line: continue

        feat = {}
        # Must have ticket
        tm = re.search(r'ticket=(\d+)', line)
        if not tm: continue
        feat['ticket'] = int(tm.group(1))

        # Timestamp
        tsm = re.search(r'(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})', line)
        feat['ts'] = tsm.group(1) if tsm else ''

        # Numeric features
        for key in ['price', 'lot', 'bounce_sec', 'bounce_ob', 'confirm_pos', 'touch', 'confirm']:
            km = re.search(rf'{key}=([\-\d\.]+)', line)
            if km:
                try: feat[key] = float(km.group(1))
                except: pass

        # Direction
        if ' B ' in line: feat['dir'] = 'buy'
        elif ' S ' in line: feat['dir'] = 'sell'

        # Position multiplier (x0.4)
        xm = re.search(r'x([\d\.]+)', line)
        if xm:
            try: feat['mult'] = float(xm.group(1))
            except: pass

        # Hour from timestamp
        if feat.get('ts'):
            try: feat['hour'] = int(feat['ts'][11:13])
            except: pass

        # Compute derived features
        if 'confirm' in feat and 'touch' in feat:
            feat['confirm_dist'] = feat['confirm'] - feat['touch']  # distance from touch to confirm
        if 'price' in feat and 'touch' in feat:
            feat['entry_depth'] = feat['price'] - feat['touch']  # how deep into OB

        trades_by_month[current_month].append(feat)

    return trades_by_month


def analyze_features(trades_by_month, html_pnls, label):
    """Correlate entry features with trade PnL."""
    entries = trades_by_month.get(label, [])
    pnls = html_pnls.get(label, [])

    n = min(len(entries), len(pnls))
    if n == 0:
        print(f"  [{label}] No data")
        return

    print(f"\n{'='*80}")
    print(f"  [{label}] {n} matched trades")
    print(f"  Overall: WR={len([p for p in pnls[:n] if p>0])/n*100:.1f}%, PnL=${sum(pnls[:n]):+,.2f}")
    print(f"{'='*80}")

    # Bucket analysis for each feature
    features_to_analyze = {
        'bounce_ob':    ('Bounce OB%', [0.20, 0.22, 0.24, 0.26, 0.28, 0.30]),
        'bounce_sec':   ('Bounce Sec', [0, 2, 5, 10, 30, 60]),
        'confirm_dist': ('Confirm Dist', [-2, -1, -0.5, 0, 0.5, 1]),
        'entry_depth':  ('Entry Depth', [-2, -1, -0.5, 0, 0.5, 1]),
        'mult':         ('Pos Multiplier', [0, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0]),
    }

    for feat_key, (feat_name, boundaries) in features_to_analyze.items():
        # Collect values
        pairs = []
        for i in range(n):
            if feat_key in entries[i]:
                pairs.append((entries[i][feat_key], pnls[i]))

        if len(pairs) < 20: continue

        print(f"\n  --- {feat_name} ---")
        for i in range(len(boundaries)-1):
            lo, hi = boundaries[i], boundaries[i+1]
            bucket = [(v, p) for v, p in pairs if lo <= v < hi]
            if len(bucket) < 3: continue
            wr = len([p for _, p in bucket if p > 0]) / len(bucket) * 100
            total = sum(p for _, p in bucket)
            avg_v = sum(v for v, _ in bucket) / len(bucket)
            bar = '#' * max(1, int(abs(total) / max(2, abs(total)/5 or 1)))
            sign = '+' if total > 0 else '-'
            print(f"  [{lo:>5.2f}-{hi:<5.2f}): {len(bucket):>4}T avg={avg_v:.3f} WR={wr:>5.1f}% PnL=${total:>+8.2f} {sign}{bar}")

    # Direction analysis
    print(f"\n  --- Direction ---")
    for d in ['buy', 'sell']:
        dir_pnls = [pnls[i] for i in range(n) if entries[i].get('dir') == d]
        if dir_pnls:
            wr = len([p for p in dir_pnls if p > 0]) / len(dir_pnls) * 100
            print(f"  {d}: {len(dir_pnls)}T WR={wr:.1f}% PnL=${sum(dir_pnls):+.2f}")

    # Hour analysis
    hour_pnls = defaultdict(list)
    for i in range(n):
        h = entries[i].get('hour', -1)
        if h >= 0: hour_pnls[h].append(pnls[i])
    if hour_pnls:
        print(f"\n  --- Hour ---")
        for h in sorted(hour_pnls.keys()):
            vals = hour_pnls[h]
            if len(vals) >= 3:
                wr = len([p for p in vals if p > 0]) / len(vals) * 100
                print(f"  H{h:02d}: {len(vals):>4}T WR={wr:>5.1f}% PnL=${sum(vals):>+8.0f}")

    # Cross-feature analysis: best combinations
    print(f"\n  --- Feature Combinations ---")
    # bounce_ob + mult interaction
    combos = defaultdict(list)
    for i in range(n):
        bo = entries[i].get('bounce_ob', 0)
        pm = entries[i].get('mult', 0)
        if bo > 0 and pm > 0:
            key = f"ob={bo:.2f}/mult={pm:.1f}"
            combos[key].append(pnls[i])
    # Show top and bottom combos by PnL
    ranked = sorted(combos.items(), key=lambda x: sum(x[1]))
    print(f"  Bottom 5 combos (worst PnL):")
    for key, pvals in ranked[:5]:
        if len(pvals) >= 2:
            wr = len([p for p in pvals if p > 0]) / len(pvals) * 100
            print(f"    {key}: {len(pvals)}T WR={wr:.0f}% PnL=${sum(pvals):+.2f}")
    print(f"  Top 5 combos (best PnL):")
    for key, pvals in ranked[-5:]:
        if len(pvals) >= 2:
            wr = len([p for p in pvals if p > 0]) / len(pvals) * 100
            print(f"    {key}: {len(pvals)}T WR={wr:.0f}% PnL=${sum(pvals):+.2f}")

    return n


# ===== MAIN =====
print("=" * 90)
print("  DEEP OB-LEVEL ANALYSIS: Feature → PnL Correlation")
print("=" * 90)

# Parse log
trades_by_month = parse_log_trades_by_month(LOG_PATH)
for m in ['2505', '2605']:
    print(f"Log entries {m}: {len(trades_by_month.get(m, []))}")

# Parse HTML reports for key configurations
html_pnls = {}
for cfg, fname in [('2505_OFF', 'nkss_REF_OFF_2505.htm'),
                    ('2605_OFF', 'nkss_REF_OFF_2605.htm'),
                    ('2505_LOOSE', 'nkss_REF_LOOSE_2505.htm'),
                    ('2605_LOOSE', 'nkss_REF_LOOSE_2605.htm'),
                    ('2505_P1', 'cd_REF_2505.htm'),
                    ('2605_P1', 'cd_REF_2605.htm')]:
    html_pnls[cfg] = parse_html_trades_pnl(MT5_DATA / fname)
    print(f"HTML {cfg}: {len(html_pnls[cfg])} trades")

# Cross-month comparison on OFF baseline
print(f"\n{'='*90}")
print(f"  CROSS-MONTH: 2505 OFF vs 2605 OFF — Feature Differences")
print(f"{'='*90}")
analyze_features(trades_by_month, html_pnls, '2505_OFF')  # won't work - need to fix mapping
analyze_features(trades_by_month, html_pnls, '2605_OFF')

# Actually, the log entries and HTML are from different backtest configurations.
# The log has entries from cd_REF (P1), not from REF_OFF.
# Let me match: log 2505 entries with P1_2505 HTML, log 2605 entries with P1_2605 HTML
print(f"\n{'='*90}")
print(f"  P1 CONFIG (H5+AD-LOOSE,SL=0.4): Feature Analysis")
print(f"{'='*90}")
# The log entries are from the cd_REF backtest (last P1 backtest)
# They should match the P1 HTML reports
for label, log_key, html_key in [('2505 P1', '2505', '2505_P1'),
                                   ('2605 P1', '2605', '2605_P1')]:
    analyze_features(trades_by_month, html_pnls, '2605_P1')
    break  # Only 2605 for now - most important

# Actually the function expects trades_by_month[label] and html_pnls[label]
# Let me restructure: pass the actual data
print(f"\n{'='*90}")
print(f"  2605 P1 DETAILED ANALYSIS")
print(f"{'='*90}")
entries_2605 = trades_by_month.get('2605', [])
pnls_2605 = html_pnls.get('2605_P1', [])
n = min(len(entries_2605), len(pnls_2605))
if n > 0:
    print(f"Matched: {n} trades")
    wins = [pnls_2605[i] for i in range(n) if pnls_2605[i] > 0]
    losses = [pnls_2605[i] for i in range(n) if pnls_2605[i] <= 0]
    print(f"Wins: {len(wins)}, Losses: {len(losses)}, Net: ${sum(pnls_2605[:n]):+.2f}")

    # Feature comparison: wins vs losses
    for feat_key in ['bounce_ob', 'bounce_sec', 'confirm_dist', 'entry_depth', 'mult']:
        w_vals = [entries_2605[i].get(feat_key, 0) for i in range(n) if pnls_2605[i] > 0 and feat_key in entries_2605[i]]
        l_vals = [entries_2605[i].get(feat_key, 0) for i in range(n) if pnls_2605[i] <= 0 and feat_key in entries_2605[i]]
        if w_vals and l_vals:
            w_avg = sum(w_vals)/len(w_vals)
            l_avg = sum(l_vals)/len(l_vals)
            w_med = sorted(w_vals)[len(w_vals)//2]
            l_med = sorted(l_vals)[len(l_vals)//2]
            print(f"  {feat_key:<15}: Win_avg={w_avg:.4f} Loss_avg={l_avg:.4f} diff={w_avg-l_avg:+.4f}  "
                  f"Win_med={w_med:.4f} Loss_med={l_med:.4f}")

    # Distribution of position multipliers
    mult_dist = Counter()
    mult_pnl = defaultdict(list)
    for i in range(n):
        m = entries_2605[i].get('mult', 0)
        if m > 0:
            mult_dist[m] += 1
            mult_pnl[m].append(pnls_2605[i])
    print(f"\n  --- Mult Distribution ---")
    for m in sorted(mult_dist.keys()):
        vals = mult_pnl[m]
        wr = len([v for v in vals if v > 0])/len(vals)*100
        print(f"  x{m:.1f}: {mult_dist[m]:>4}T WR={wr:>5.1f}% PnL=${sum(vals):>+8.2f}")

print(f"\n[DONE]")
