#!/usr/bin/env python3
"""Debug: find the results table in MT5 HTML report."""
from pathlib import Path

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
htm = DATA / 'phase2_mtf-off.htm'
raw = htm.read_bytes()
html = raw.decode('utf-16-le', errors='replace')

# Find the position after "Parameters" or after the long input list
# Look for unique markers of the results section
for marker in ['Bars in test', 'Ticks modelled', 'Modelling quality', 'Initial deposit',
               'Total net', 'Gross profit', 'bars in test', 'ticks modelled']:
    idx = html.lower().find(marker.lower())
    if idx >= 0:
        snippet = html[max(0,idx):idx+500]
        print(f"=== '{marker}' at pos {idx} ===")
        print(repr(snippet[:400]))
        print()

# Also dump the last 2000 chars to see what's at the end
print("=== LAST 2000 CHARS ===")
print(repr(html[-2000:]))
