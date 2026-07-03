#!/usr/bin/env python3
"""Find the summary/results table in MT5 HTML report."""
from pathlib import Path

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
htm = DATA / 'phase2_mtf-off.htm'
raw = htm.read_bytes()
html = raw.decode('utf-16-le', errors='replace')

# The summary appears before the trade list. Let me find the summary table
# by looking for known markers in MT5 reports
for marker in ['Bars in test', 'Ticks modelled', 'Modelling', 'Initial', 'Total net',
               'Short positions', 'Long positions', 'maximal', 'consecutive',
               'largest', 'average', 'expected', 'Sharpe', 'Z-score',
               'bars modelled', 'quality']:
    idx = html.lower().find(marker.lower())
    if idx >= 0:
        surrounding = html[max(0,idx-50):idx+300]
        # Strip HTML tags for readability
        clean = surrounding.replace('\r\n', ' ')
        print(f"=== '{marker}' (pos {idx}) ===")
        print(clean[:400])
        print()

# Also try to find the summary by looking right before the trade list
trade_start = html.find('bgcolor="#F7F7F7"')
if trade_start > 0:
    # Summary should be in the ~5000 chars before the trade list starts
    before = html[max(0,trade_start-15000):trade_start]
    print("=== 15000 chars before trade list ===")
    print(repr(before[-2000:]))
