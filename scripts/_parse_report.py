#!/usr/bin/env python3
"""Quick parse of a portable terminal backtest report."""
import sys, re
from pathlib import Path

rpt = Path(r'D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt\24m_S2_2408.htm')
if not rpt.exists():
    print(f'NOT FOUND: {rpt}')
    sys.exit(1)

with open(rpt, 'rb') as f:
    raw = f.read()
text = raw.decode('utf-16-le', errors='replace')

# Extract key metrics
def extract(label, text, pattern):
    m = re.search(pattern, text)
    if m:
        val = m.group(1).strip()
        print(f'  {label}: {val}')
        return val
    return None

print(f'Report: {rpt.name} ({rpt.stat().st_size/1024:.0f}KB)')
extract('Symbol/Period', text, r'交易品种:</td><td[^>]*>([^<]+)')
extract('Date Range', text, r'期间:</td><td[^>]*>([^<]+)')
extract('Model', text, r'Mode[l]\d*</td><td[^>]*>([^<]+)')
extract('Deposit', text, r'Deposit</td><td[^>]*>([^<]+)')

# Find trades summary
m = re.search(r'Profit</td><td[^>]*>(-?\d+\.?\d*)', text)
if m: print(f'  Profit: {m.group(1)}')

m = re.search(r'Total[\s\S]{0,100}?<td[^>]*>(\d+)</td>', text)
if m: print(f'  Total trades: {m.group(1)}')

m = re.search(r'Profit[\s\S]{0,50}?<td[^>]*>(-?\d[\d.]*)', text)
if m: print(f'  Gross Profit: {m.group(1)}')

m = re.search(r'Gross Loss[\s\S]{0,50}?<td[^>]*>(-?\d[\d.]*)', text)
if m: print(f'  Gross Loss: {m.group(1)}')

print('\n=== All report files ===')
for f in sorted(rpt.parent.glob('24m_*.htm')):
    sz = f.stat().st_size
    print(f'  {f.name} ({sz/1024:.0f}KB)')
