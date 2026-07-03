#!/usr/bin/env python3
"""Debug 720d HTML structure"""
import re, os
from pathlib import Path

MT5D = Path(os.path.expandvars(r'%APPDATA%')) / 'MetaQuotes' / 'Terminal' / 'D0E8209F77C8CF37AD8BF550E51FF075'

# Find largest D5B report (likely 720d)
files = sorted(MT5D.glob('v11xau-qs3-d5b*htm'), key=lambda p: p.stat().st_size, reverse=True)
f = files[0]
print(f"File: {f.name}, Size: {f.stat().st_size}")

raw = f.read_bytes()
text = raw.decode('utf-16-le')
lines = text.split('\n')

# Count trades
out_count = 0
for line in lines:
    clean = re.sub(r'<[^>]+>', ' | ', line).strip()
    if 'XAUUSDm' in clean and '| out |' in clean:
        out_count += 1
        if out_count <= 2:
            parts = [p.strip() for p in clean.split('|')]
            non_empty = [p for p in parts if p]
            print(f"Deal {out_count}: {len(non_empty)} fields: {non_empty}")
print(f"Total out deals: {out_count}")

# Last 20 lines
print("\n=== Last 20 lines ===")
for i in range(max(0, len(lines)-20), len(lines)):
    clean = re.sub(r'<[^>]+>', ' | ', lines[i]).strip()
    if clean:
        print(f"L{i}: [{clean[:300]}]")
