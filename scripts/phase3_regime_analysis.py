#!/usr/bin/env python3
"""Phase 3: Regime detection analysis.
Extract trade sequences with EA log features + HTML PnL.
Analyze: regime transitions, consecutive patterns, feature shifts.
Goal: design a real-time regime detector that doesn't use month labels."""
import re, sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta

LOG_PATH = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/Tester/logs/20260606.log')
MT5_DATA = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075')

def parse_html_trades_detailed(htm_path):
    """Extract trades with full detail from HTML report."""
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
        time_str = cells[1].strip()[:19]
        direction = cells[5].strip().lower()
        try: price = float(cells[7].strip().replace(' ','').replace(',',''))
        except: price = 0.0
        try: pnl = float(cells[10].strip().replace(' ','').replace(',',''))
        except: pnl = 0.0
        comment = cells[12].strip()

        if 'in' in io:
            try: et = datetime.strptime(time_str, '%Y.%m.%d %H:%M:%S')
            except: et = None
            pending.append({'entry_time': et, 'entry_price': price, 'direction': direction, 'comment': comment})
        elif 'out' in io and pending:
            entry = pending.pop(0)
            try: xt = datetime.strptime(time_str, '%Y.%m.%d %H:%M:%S')
            except: xt = None
            hold_sec = (xt - entry['entry_time']).total_seconds() if entry['entry_time'] and xt else 0
            if hold_sec < 0: hold_sec = 0

            # Exit reason
            cl = comment.lower()
            if 'sl' in cl or 'stop' in cl: exit_reason = 'sl'
            elif 'be' in cl or 'breakeven' in cl: exit_reason = 'be'
            elif 'dtp' in cl: exit_reason = 'dtp'
            elif 'tp' in cl: exit_reason = 'tp'
            elif 'trail' in cl: exit_reason = 'trail'
            else: exit_reason = 'other'

            trades.append({
                'entry_time': entry['entry_time'],
                'exit_time': xt,
                'hold_sec': hold_sec,
                'direction': entry['direction'],
                'pnl': pnl,
                'exit_reason': exit_reason,
                'entry_price': entry['entry_price'],
                'exit_price': price,
                'hour': entry['entry_time'].hour if entry['entry_time'] else -1,
                'dow': entry['entry_time'].weekday() if entry['entry_time'] else -1,
                'day': entry['entry_time'].day if entry['entry_time'] else -1,
            })
    return trades


def parse_log_entries_with_features(log_path):
    """Parse EA log: extract ENTRY_DIAG features for trades."""
    raw = log_path.read_bytes()
    text = raw.decode('utf-16-le', errors='replace')
    lines = text.split('\n')

    entries = []
    in_2605 = False
    in_2505 = False

    for line in lines:
        # Track which backtest we're in
        if 'testing of' in line and 'from 2026.05' in line:
            in_2605 = True; in_2505 = False
        elif 'testing of' in line and 'from 2025.05' in line:
            in_2505 = True; in_2605 = False
        elif 'testing of' in line and 'from' in line:
            in_2505 = False; in_2605 = False

        # Parse ENTRY_DIAG lines
        if 'ENTRY_DIAG' not in line: continue

        feat = {}
        for m in re.finditer(r'(\w+)=([\d\.\-]+)', line):
            val = m.group(2)
            try: feat[m.group(1)] = float(val) if '.' in val else int(val)
            except: feat[m.group(1)] = val

        # Only keep entries with useful features
        if 'stage' not in feat: continue

        # Timestamp
        ts_match = re.search(r'(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})', line)
        ts_str = ts_match.group(1) if ts_match else ''
        try: ts = datetime.strptime(ts_str, '%Y.%m.%d %H:%M:%S')
        except: ts = None

        feat['month_tag'] = '2605' if in_2605 else ('2505' if in_2505 else 'unknown')
        feat['ts'] = ts
        entries.append(feat)

    return entries


def analyze_trade_sequence(trades, label):
    """Analyze sequential patterns in trade outcomes."""
    if not trades: return

    n = len(trades)
    pnls = [t['pnl'] for t in trades]
    total_pnl = sum(pnls)

    # Rolling WR analysis
    print(f"\n--- [{label}] Rolling WR Analysis ({n} trades) ---")
    for window in [10, 20, 30]:
        rolling_wrs = []
        for i in range(window, n):
            wins_in_window = sum(1 for j in range(i-window, i) if pnls[j] > 0)
            rolling_wrs.append(wins_in_window / window * 100)

        if rolling_wrs:
            min_wr = min(rolling_wrs)
            max_wr = max(rolling_wrs)
            # How often does rolling WR drop below thresholds?
            below_40 = sum(1 for w in rolling_wrs if w < 40)
            below_30 = sum(1 for w in rolling_wrs if w < 30)
            print(f"  Window={window:>2}: WR range [{min_wr:.0f}%-{max_wr:.0f}%], "
                  f"below40={below_40}/{len(rolling_wrs)} ({below_40/len(rolling_wrs)*100:.0f}%), "
                  f"below30={below_30}/{len(rolling_wrs)} ({below_30/len(rolling_wrs)*100:.0f}%)")

    # Regime detection: identify "bad regimes" (rolling WR < 40%)
    window = 15
    bad_regimes = []
    in_bad = False
    bad_start = 0
    for i in range(window, n):
        wins_in_window = sum(1 for j in range(i-window, i) if pnls[j] > 0)
        wr = wins_in_window / window * 100
        if wr < 40 and not in_bad:
            in_bad = True
            bad_start = i
        elif wr >= 50 and in_bad:
            in_bad = False
            bad_regimes.append((bad_start, i))

    if in_bad:
        bad_regimes.append((bad_start, n))

    if bad_regimes:
        print(f"\n  Bad regimes (rolling WR<40% for {window}-trade window): {len(bad_regimes)}")
        total_bad_trades = sum(e - s for s, e in bad_regimes)
        total_bad_pnl = sum(sum(pnls[s:e]) for s, e in bad_regimes)
        print(f"  Bad regime trades: {total_bad_trades}/{n} ({total_bad_trades/n*100:.0f}%)")
        print(f"  Bad regime PnL: ${total_bad_pnl:+,.2f}")
        print(f"  If we stopped trading during bad regimes, PnL would be: ${total_pnl - total_bad_pnl:+,.2f}")

        # Show bad regime details
        for idx, (s, e) in enumerate(bad_regimes[:5]):
            bad_pnl = sum(pnls[s:e])
            print(f"  Regime {idx+1}: trades {s}-{e} ({e-s}T), PnL=${bad_pnl:+,.2f}, "
                  f"WR={sum(1 for j in range(s,e) if pnls[j]>0)/(e-s)*100:.0f}%")

    # Win/Loss streak transition analysis
    print(f"\n  --- Streak Transition Analysis ---")
    # After a loss streak of N, what's the next trade's PnL distribution?
    for streak_len in [1, 2, 3, 5]:
        next_trades = []
        cur_streak = 0
        for i in range(n):
            if pnls[i] <= 0:
                cur_streak += 1
            else:
                if cur_streak >= streak_len:
                    next_trades.append(pnls[i])  # PnL of the winning trade that breaks the streak
                cur_streak = 0
        if next_trades:
            avg_pnl = sum(next_trades) / len(next_trades)
            wr_break = len([p for p in next_trades if p > 0]) / len(next_trades) * 100
            print(f"  After {streak_len}+ loss streak: {len(next_trades)} breakouts, "
                  f"avgPnL=${avg_pnl:+.2f}, WR={wr_break:.0f}%")

    # DTP hit rate over time (are DTPs clustered?)
    dtp_indices = [i for i, t in enumerate(trades) if t['exit_reason'] == 'dtp']
    if dtp_indices:
        gaps = [dtp_indices[i+1] - dtp_indices[i] for i in range(len(dtp_indices)-1)]
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        print(f"\n  DTP trades: {len(dtp_indices)}, avg gap={avg_gap:.0f} trades between DTPs")
        # DTP rate over time (first half vs second half)
        mid = n // 2
        dtp_first = sum(1 for i in dtp_indices if i < mid)
        dtp_second = len(dtp_indices) - dtp_first
        print(f"  DTP first half: {dtp_first}, second half: {dtp_second}")

    return {
        'n': n, 'total_pnl': total_pnl,
        'bad_regimes': bad_regimes,
        'rolling_wrs': None,
    }


def correlate_ob_features(entries, trades, label):
    """Correlate OB features (strength, ob_age, touch_count) with trade PnL."""
    # Match entries to trades by time sequence
    # We'll use the ENTRY_DIAG entries and trades in sequence order
    n = min(len(entries), len(trades))

    print(f"\n--- [{label}] OB Feature vs PnL ({n} matched) ---")

    for feat_name in ['strength', 'ob_age', 'touch_count', 'entry_count', 'hour']:
        buckets = defaultdict(list)
        for i in range(n):
            if feat_name in entries[i]:
                buckets[entries[i][feat_name]].append(trades[i]['pnl'])

        if not buckets: continue

        # Group into ranges for readability
        values = list(buckets.keys())
        if feat_name in ['strength', 'ob_age', 'touch_count', 'entry_count']:
            # For numeric features, group into buckets
            all_vals = sorted(values)
            n_buckets = min(5, len(set(int(v) if isinstance(v, (int, float)) else 0 for v in all_vals)))
            print(f"  {feat_name}: {len(all_vals)} unique values, range [{min(all_vals)}, {max(all_vals)}]")

        # Top 5 values by count
        top_items = sorted(buckets.items(), key=lambda x: len(x[1]), reverse=True)[:8]
        for val, pnls_list in top_items:
            wr = len([p for p in pnls_list if p > 0]) / len(pnls_list) * 100 if pnls_list else 0
            total = sum(pnls_list)
            print(f"    {feat_name}={val}: {len(pnls_list)}T WR={wr:.1f}% PnL=${total:+.2f}")


# ===== MAIN =====
print("=" * 90)
print("  PHASE 3: Regime Detection Analysis")
print("=" * 90)

# Load data
off_2505 = parse_html_trades_detailed(MT5_DATA / 'nkss_REF_OFF_2505.htm')
off_2605 = parse_html_trades_detailed(MT5_DATA / 'nkss_REF_OFF_2605.htm')
loose_2505 = parse_html_trades_detailed(MT5_DATA / 'nkss_REF_LOOSE_2505.htm')
loose_2605 = parse_html_trades_detailed(MT5_DATA / 'nkss_REF_LOOSE_2605.htm')

print(f"Loaded: 2505 OFF={len(off_2505)}T, 2605 OFF={len(off_2605)}T, "
      f"2505 LOOSE={len(loose_2505)}T, 2605 LOOSE={len(loose_2605)}T")

# Sequential analysis
r_off_25 = analyze_trade_sequence(off_2505, "2505 OFF")
r_off_26 = analyze_trade_sequence(off_2605, "2605 OFF")
r_loose_25 = analyze_trade_sequence(loose_2505, "2505 LOOSE")
r_loose_26 = analyze_trade_sequence(loose_2605, "2605 LOOSE")

# EA log feature analysis
print(f"\n{'=' * 90}")
print(f"  EA LOG FEATURE CORRELATION")
print(f"{'=' * 90}")
entries = parse_log_entries_with_features(LOG_PATH)
print(f"Parsed {len(entries)} ENTRY_DIAG entries from log")

# Separate by month
e_2505 = [e for e in entries if e.get('month_tag') == '2505']
e_2605 = [e for e in entries if e.get('month_tag') == '2605']
print(f"2505 entries: {len(e_2505)}, 2605 entries: {len(e_2605)}")

if e_2505:
    correlate_ob_features(e_2505, off_2505, "2505 OFF OB Features")
if e_2605:
    correlate_ob_features(e_2605, off_2605, "2605 OFF OB Features")

# Hourly analysis (fixed)
print(f"\n{'=' * 90}")
print(f"  HOURLY WR ANALYSIS (FIXED)")
print(f"{'=' * 90}")

for label, trades in [("2505 OFF", off_2505), ("2605 OFF", off_2605)]:
    if not trades: continue
    hour_stats = defaultdict(list)
    for t in trades:
        if t['hour'] >= 0:
            hour_stats[t['hour']].append(t['pnl'])

    print(f"\n  [{label}]")
    for h in sorted(hour_stats.keys()):
        pnls = hour_stats[h]
        wr = len([p for p in pnls if p > 0]) / len(pnls) * 100
        total = sum(pnls)
        bar = '#' * max(1, int(abs(total) / max(5, abs(total)/10 or 1)))
        sign = '+' if total > 0 else '-'
        if len(pnls) >= 3:  # Only show statistically meaningful
            print(f"  H{h:02d}: {len(pnls):>4}T WR={wr:>5.1f}% PnL=${total:>+8.0f} {sign}{bar}")

# Regime detection effectiveness comparison
print(f"\n{'=' * 90}")
print(f"  REGIME DETECTION: What if we stopped trading when rolling WR < 40%?")
print(f"{'=' * 90}")
print(f"  {'Dataset':<20} {'Total PnL':>10} {'Saved PnL':>10} {'New PnL':>10} {'Trades Saved':>10}")

for label, r, trades in [("2505 OFF", r_off_25, off_2505), ("2605 OFF", r_off_26, off_2605),
                           ("2505 LOOSE", r_loose_25, loose_2505), ("2605 LOOSE", r_loose_26, loose_2605)]:
    total_pnl = r['total_pnl'] if r else 0
    if r and r['bad_regimes']:
        bad_pnl = sum(sum(t['pnl'] for t in trades[s:e]) for s, e in r['bad_regimes'])
        new_pnl = total_pnl - bad_pnl
        bad_trades = sum(e - s for s, e in r['bad_regimes'])
        print(f"  {label:<20} ${total_pnl:>+9,.0f} ${bad_pnl:>+9,.0f} ${new_pnl:>+9,.0f} {bad_trades:>10}")

print(f"\n[DONE - Phase 3]")
