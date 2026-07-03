#!/usr/bin/env python3
"""Extract ALL numeric rows from MT5 summary table (before trade list)."""
from pathlib import Path
import re

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')

for test_name in ['phase2_mtf-off', 'phase2_mtf-all', 'phase2_mtf-r5', 'phase2_mtf-r4', 'phase2_mtf-r1b']:
    htm = DATA / f'{test_name}.htm'
    if not htm.exists():
        continue
    raw = htm.read_bytes()
    html = raw.decode('utf-16-le', errors='replace')

    # Find the trade list start
    trade_start = html.find('bgcolor="#F7F7F7"')
    # Summary is in the ~3000 chars before trade list
    summary_section = html[max(0, trade_start - 3000):trade_start]

    # Remove HTML tags to get text content
    text = re.sub(r'<[^>]+>', ' ', summary_section)
    text = re.sub(r'\s+', ' ', text).strip()

    print(f"\n=== {test_name} ===")
    # Print non-garbled parts
    for line in text.split('  '):
        line = line.strip()
        if line and any(c.isdigit() for c in line):
            # Only print lines with numbers
            # Try to show only English characters and numbers
            clean = ''.join(c if ord(c) < 128 else '?' for c in line)
            if any(c.isdigit() for c in clean):
                print(f"  {clean[:120]}")
