#!/usr/bin/env python3
"""Debug: dump relevant parts of HTML report to understand structure."""
import re
from pathlib import Path

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
htm = DATA / 'phase2_mtf-off.htm'

raw = htm.read_bytes()
html = raw.decode('utf-16-le', errors='replace')

# Find all td elements with numeric content
# First, let's see what the report looks like around "balance" / "trades"
for keyword in ['balance', 'trades', 'profit', 'factor', 'drawdown']:
    idx = html.lower().find(keyword)
    if idx >= 0:
        snippet = html[max(0,idx-100):idx+200]
        # Clean for display
        clean = snippet.replace('\r','\\r').replace('\n','\\n').replace('\t','\\t')
        print(f"=== Around '{keyword}' (pos {idx}) ===")
        print(clean[:300])
        print()

# Also dump the report structure near the Summary table
# Look for common table markers
for marker in ['Summary', 'Total', 'Result']:
    idx = html.find(marker)
    if idx >= 0:
        snippet = html[max(0,idx-50):idx+500]
        print(f"=== Around '{marker}' ===")
        print(snippet[:500])
        print()
