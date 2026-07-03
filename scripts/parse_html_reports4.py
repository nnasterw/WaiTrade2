#!/usr/bin/env python3
"""解析 MT5 HTML - 找汇总结果表（通常在文件末尾）"""
import re, os
from pathlib import Path

MT5D = Path(os.path.expandvars(r'%APPDATA%')) / 'MetaQuotes' / 'Terminal' / 'D0E8209F77C8CF37AD8BF550E51FF075'

f = sorted(MT5D.glob('v11xau-qs3-d4a_XAUUSDm_20260604.htm'), key=lambda p: p.stat().st_mtime)[0]
raw = f.read_bytes()
text = raw.decode('utf-16-le')

lines = text.split('\n')

# Find "Results" section - typically near the end
for i, line in enumerate(lines):
    clean = re.sub(r'<[^>]+>', ' | ', line).strip()
    if re.search(r'result|total|bars.*ticks|final|balance|drawdown|profit.*factor|recovery|expected|sharp', clean, re.IGNORECASE):
        print(f'L{i}: [{clean[:300]}]')

print("\n\n=== Last 100 lines ===")
for i in range(max(0, len(lines)-100), len(lines)):
    clean = re.sub(r'<[^>]+>', ' | ', lines[i]).strip()
    if clean and clean != '|  |  |  |  |  |  |':
        print(f'L{i}: [{clean[:300]}]')
