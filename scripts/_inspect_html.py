#!/usr/bin/env python3
"""Inspect MT5 HTML report structure."""
import sys, re

htm = r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/smc_B_2605.htm'
with open(htm, 'rb') as f:
    raw = f.read()
text = raw.decode('utf-16-le', errors='replace')

# Find key sections
for keyword in ['Trades</h2>', 'Deals</h2>', '<h2>', '<table']:
    idx = text.find(keyword)
    if idx > 0:
        print(f'Found "{keyword}" at position {idx}')
        print(text[idx:idx+200])
        print('---')

# Look for td patterns
cells = re.findall(r'<td[^>]*>(.*?)</td>', text, re.DOTALL)
print(f'\nTotal cells found: {len(cells)}')
print('First 30 cells:')
for i, c in enumerate(cells[:30]):
    val = re.sub(r'<[^>]+>', '', c).strip()
    print(f'  [{i}] {val[:80]}')

# Find trade data pattern
pnl_pattern = re.findall(r'(?:Profit|Loss).*?(-?\d+\.?\d*)', text)
print(f'\nPnL matches: {len(pnl_pattern)}')
for p in pnl_pattern[:10]:
    print(f'  {p}')
