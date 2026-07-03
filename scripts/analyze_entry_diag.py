#!/usr/bin/env python3
"""Extract ENTRY_DIAG entries from Tester log and correlate with trade outcomes.
Key features: strength, ob_age, touch_count, h1, deep, htf, bounce, hour.
Goal: find which real-time features separate winners from losers in 2605 vs 2505."""
import re, sys
from pathlib import Path
from collections import defaultdict, Counter

LOG_PATH = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/Tester/logs/20260606.log')
MT5_DATA = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075')

def parse_entry_diag(line):
    """Parse ENTRY_DIAG line format:
    ENTRY_DIAG stage=entry_engine ticket=0 dir=-1 hour=8 ob_age=28 touch_count=2261 entry_count=0 strength=3.99 ds=1.00 fresh=0 cont=0 h1=0 deep=1 htf=0 bounce=..."""
    fields = {}
    for m in re.finditer(r'(\w+)=([\d\.\-]+)', line):
        fields[m.group(1)] = float(m.group(2)) if '.' in m.group(2) or m.group(2).startswith('-') else int(m.group(2))
    return fields

def parse_tick_noise(line):
    """Parse TICK_NOISE rejection line."""
    fields = {}
    for m in re.finditer(r'(\w+)=([\d\.\-]+)', line):
        fields[m.group(1)] = float(m.group(2)) if '.' in m.group(2) else int(m.group(2))
    return fields

def parse_final_diag(line):
    """Parse FINAL_DIAG rejection line."""
    fields = {'skip': 'unknown'}
    m = re.search(r'skip=(\S+)', line)
    if m:
        fields['skip'] = m.group(1)
    m = re.search(r'risk=([\d\.]+)', line)
    if m:
        fields['risk'] = float(m.group(1))
    m = re.search(r'spread=([\d\.]+)', line)
    if m:
        fields['spread'] = float(m.group(1))
    m = re.search(r'dir=([\-\d]+)', line)
    if m:
        fields['dir'] = int(m.group(1))
    return fields

# ===== MAIN =====
print("Parsing Tester log (5.8M lines)...")
raw = LOG_PATH.read_bytes()
text = raw.decode('utf-16-le', errors='replace')
lines = text.split('\n')

# Extract all ENTRY_DIAG and FINAL_DIAG entries with timestamps
entry_diags = []    # list of (timestamp, fields)
final_diags = []    # list of (timestamp, fields)
tick_noises = []    # list of (timestamp, fields)
test_starts = []    # list of (timestamp, symbol, from_date, to_date)

for line in lines:
    # Extract timestamp and message
    ts_match = re.search(r'(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})', line)
    ts = ts_match.group(1) if ts_match else ''

    if 'ENTRY_DIAG' in line:
        entry_diags.append((ts, parse_entry_diag(line)))
    elif 'FINAL_DIAG' in line:
        final_diags.append((ts, parse_final_diag(line)))
    elif 'TICK_NOISE' in line and 'z=skip' in line:
        tick_noises.append((ts, parse_tick_noise(line)))
    elif 'testing of Experts' in line and 'from' in line:
        test_starts.append(ts)

print(f"\nFound: {len(entry_diags)} ENTRY_DIAG, {len(final_diags)} FINAL_DIAG, "
      f"{len(tick_noises)} TICK_NOISE, {len(test_starts)} test starts")

# Analyze ENTRY_DIAG features by ticket number (ticket>0 = actual trade)
actual_trades = [e for e in entry_diags if e[1].get('ticket', 0) > 0]
rejected = [e for e in entry_diags if e[1].get('ticket', 0) == 0]

print(f"Actual trades (ticket>0): {len(actual_trades)}")
print(f"Rejected entries (ticket=0): {len(rejected)}")

if actual_trades:
    # Feature distributions for actual trades
    print(f"\n--- Feature Distributions for Actual Trades ---")

    for feat in ['strength', 'ob_age', 'touch_count', 'entry_count', 'hour', 'h1', 'deep', 'htf']:
        values = [t[1].get(feat, 0) for t in actual_trades]
        if values:
            avg = sum(values) / len(values)
            print(f"  {feat:<15}: avg={avg:.2f}, min={min(values)}, max={max(values)}, "
                  f"median={sorted(values)[len(values)//2]}")

# FINAL_DIAG skip reason distribution
skip_counts = Counter(f[1].get('skip', 'unknown') for f in final_diags)
print(f"\n--- FINAL_DIAG Skip Reasons (top 15) ---")
for reason, count in skip_counts.most_common(15):
    print(f"  {reason:<25}: {count:>6} ({count/len(final_diags)*100:.1f}%)")

# TICK_NOISE analysis
if tick_noises:
    range_rejects = [t for t in tick_noises if 'range_ratio' in t[1] and 'max' in t[1]]
    dir_rejects = [t for t in tick_noises if 'dir_ratio' in t[1] and 'min' in t[1]]

    print(f"\n--- TICK_NOISE Analysis ---")
    print(f"  Range rejects: {len(range_rejects)}")
    print(f"  Dir rejects: {len(dir_rejects)}")

    if range_rejects:
        ratios = [t[1]['range_ratio'] for t in range_rejects]
        limits = [t[1]['max'] for t in range_rejects]
        print(f"  Range ratio: avg={sum(ratios)/len(ratios):.3f}, "
              f"min={min(ratios):.3f}, max={max(ratios):.3f}")
        print(f"  Range limit: avg={sum(limits)/len(limits):.3f}")

    if dir_rejects:
        ratios = [t[1]['dir_ratio'] for t in dir_rejects]
        limits = [t[1]['min'] for t in dir_rejects]
        print(f"  Dir ratio: avg={sum(ratios)/len(ratios):.3f}, "
              f"min={min(ratios):.3f}, max={max(ratios):.3f}")

# Now: correlate ENTRY_DIAG features with trade outcomes
# We need to match trades by sequence with HTML reports
# For the REF_OFF_2605 report (497 trades), the first 497 actual_trades in the
# relevant backtest should match

# Let's try to match the last backtest run
# We need to identify which backtest corresponds to which configuration
print(f"\n--- Matching Entry Diags to Trade Outcomes ---")
print(f"Test starts found: {test_starts[:5]}...")

# For a deep analysis, extract all ENTRY_DIAG with ticket>0 for a specific time range
# The cd_REF backtest (P1 baseline) ran around 09:XX today
# Let's find it and extract features

# Simple approach: look at all trades with ticket>0 and show feature stats
trades_with_tickets = [(ts, f) for ts, f in actual_trades]
if trades_with_tickets:
    print(f"\nFirst 10 actual trades:")
    for ts, f in trades_with_tickets[:10]:
        print(f"  {ts} ticket={f.get('ticket')} dir={f.get('dir')} "
              f"strength={f.get('strength')} ob_age={f.get('ob_age')} "
              f"touch_count={f.get('touch_count')} h1={f.get('h1')} deep={f.get('deep')} htf={f.get('htf')}")

print(f"\n[DONE]")
