#!/usr/bin/env python3
"""Debug 720d HTML structure"""
import re, os
from pathlib import Path

MT5D = Path(os.path.expandvars(r'%APPDATA%')) / 'MetaQuotes' / 'Terminal' / 'D0E8209F77C8CF37AD8BF550E51FF075'

# Look at D5B 720d
for f in sorted(MT5D.glob('v11xau-qs3-d5b*[2].htm'), key=lambda p: p.stat().st_mtime):
    raw = f.read_bytes()
    text = raw.decode('utf-16-le')
    lines = text.split('\n')

    # Find first 5 deal lines with XAUUSDm
    count = 0
    for i, line in enumerate(lines):
        clean = re.sub(r'<[^>]+>', ' | ', line).strip()
        if 'XAUUSDm' in clean and 'out' in clean:
            count += 1
            if count <= 3:
                parts = [p.strip() for p in clean.split('|')]
                # Filter empty
                non_empty = [p for p in parts if p]
                print(f"Deal {count} (line {i}): {len(parts)} parts, non-empty: {len(non_empty)}")
                print(f"  Parts: {non_empty[:20]}")
                print(f"  Full: {clean[:300]}")
                print()

    # Find summary at end
    print("=== Last 30 lines ===")
    for i in range(max(0, len(lines)-30), len(lines)):
        clean = re.sub(r'<[^>]+>', ' | ', lines[i]).strip()
        if clean:
            print(f"L{i}: [{clean[:200]}]")
    break
