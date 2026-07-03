#!/usr/bin/env python3
"""解析 MT5 HTML 回测报告（UTF-16 LE 编码）— 详细版"""
import re, os
from pathlib import Path

MT5D = Path(os.path.expandvars(r'%APPDATA%')) / 'MetaQuotes' / 'Terminal' / 'D0E8209F77C8CF37AD8BF550E51FF075'

f = sorted(MT5D.glob('v11xau-qs3-d4a_XAUUSDm_20260604.htm'), key=lambda p: p.stat().st_mtime)[0]
raw = f.read_bytes()
text = raw.decode('utf-16-le')

# Find all lines containing XAUUSDm
for i, line in enumerate(text.split('\n')):
    if 'XAUUSDm' in line:
        # Strip HTML tags for readability
        clean = re.sub(r'<[^>]+>', '', line).strip()
        if clean:
            print(f'Line {i}: [{clean}]')
