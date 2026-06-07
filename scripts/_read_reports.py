#!/usr/bin/env python3
"""Parse all 24m reports from portable terminal."""
import re
from pathlib import Path

d = Path(r'D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt')
reports = sorted(d.glob('24m_*.htm'))

print(f'{"Config":<15} {"Trades":>6} {"WR":>5} {"Profit":>12}')
print('-'*40)

for rpt in reports:
    with open(rpt, 'rb') as f:
        text = f.read().decode('utf-16-le', errors='replace')

    # Extract config name and month from filename
    name = rpt.stem.replace('24m_', '')

    # Find total trades
    m = re.search(r'Total[\s\S]{0,200}?<td[^>]*>(\d+)</td>', text)
    trades = m.group(1) if m else '?'

    # Find Profit
    m = re.search(r'Profit[\s\S]{0,50}?<td[^>]*>(-?\d[\d.,]*)', text)
    profit = m.group(1) if m else '?'

    # Find Gross Profit and Gross Loss for WR
    m = re.search(r'Gross Profit[\s\S]{0,50}?<td[^>]*>(-?\d[\d.,]*)', text)
    gp = float(m.group(1)) if m else 0

    m = re.search(r'Gross Loss[\s\S]{0,50}?<td[^>]*>(-?\d[\d.,]*)', text)
    gl = float(m.group(1)) if m else 0

    # Count trade rows for WR approximation
    rows = re.findall(r'<tr[^>]*>.*?</tr>', text, re.DOTALL)

    print(f'{name:<15} {trades:>6} {profit:>12}')

print()
for rpt in reports:
    with open(rpt, 'rb') as f:
        text = f.read().decode('utf-16-le', errors='replace')
    name = rpt.stem.replace('24m_', '')
    m = re.search(r'Profit[\s\S]{0,50}?<td[^>]*>(-?\d[\d.,]*)', text)
    profit = m.group(1) if m else '?'
    print(f'{name}: profit={profit}')
