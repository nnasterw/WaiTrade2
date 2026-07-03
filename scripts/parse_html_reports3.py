#!/usr/bin/env python3
"""解析 MT5 HTML - 找汇总表格"""
import re, os
from pathlib import Path

MT5D = Path(os.path.expandvars(r'%APPDATA%')) / 'MetaQuotes' / 'Terminal' / 'D0E8209F77C8CF37AD8BF550E51FF075'

f = sorted(MT5D.glob('v11xau-qs3-d4a_XAUUSDm_20260604.htm'), key=lambda p: p.stat().st_mtime)[0]
raw = f.read_bytes()
text = raw.decode('utf-16-le')

# Find around line 42 with more context
lines = text.split('\n')
for i in range(30, 80):
    clean = re.sub(r'<[^>]+>', '', lines[i]).strip()
    if clean:
        print(f'L{i}: [{clean}]')

# Also find "final balance" or "balance"
for i, line in enumerate(lines):
    if re.search(r'balance|deposit|profit|total.*trades| net ', line, re.IGNORECASE):
        clean = re.sub(r'<[^>]+>', ' | ', line).strip()
        print(f'BL{i}: [{clean[:200]}]')
