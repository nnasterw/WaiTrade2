#!/usr/bin/env python3
"""Parse HTM report content."""
import re

path = r'D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt\24m_S2_2408.htm'
with open(path, 'rb') as f:
    text = f.read().decode('utf-16-le', errors='replace')

# Find all numeric data-value attributes (MT5 report format)
data_vals = re.findall(r'data-value="(-?\d+\.?\d*)"', text)
print('data-value attributes found:', len(data_vals))
# These should be in order: balance, equity, deposit, gross profit, gross loss, net profit, etc.
if data_vals:
    print('First 20 data-values:', data_vals[:20])

# Find section headers
for header in ['Results', 'Profit', 'Total', 'Gross', 'Balance', 'Symbol']:
    idx = text.find(header)
    if idx >= 0:
        # Get surrounding text
        around = text[max(0,idx-50):idx+500]
        clean = re.sub(r'<[^>]+>', ' | ', around).replace('&nbsp;', ' ').strip()
        print(f'\n--- {header} ---')
        print(clean[:600])
