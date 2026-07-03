#!/usr/bin/env python3
"""解析 MT5 HTML 回测报告（UTF-16 LE 编码）"""
import re, os
from pathlib import Path

MT5D = Path(os.path.expandvars(r'%APPDATA%')) / 'MetaQuotes' / 'Terminal' / 'D0E8209F77C8CF37AD8BF550E51FF075'

for f in sorted(MT5D.glob('v11xau-qs3-d[45]*.htm'), key=lambda p: p.stat().st_mtime):
    raw = f.read_bytes()
    try:
        text = raw.decode('utf-16-le')
    except:
        text = raw.decode('utf-8', errors='ignore')

    # Date range
    date_m = re.search(r'M1\s*\((\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})\)', text)
    date_str = f'{date_m.group(1)}~{date_m.group(2)}' if date_m else 'no-date'

    # Result line
    result_m = re.search(r'(XAUUSDm)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+', text)
    if result_m:
        trades = int(result_m.group(2))
        daily = float(result_m.group(3))
        wr = float(result_m.group(4))
        print(f'{f.stem}: {date_str} | {trades}t {daily}t/d WR={wr}%')
    else:
        print(f'{f.stem}: {date_str} | NO_RESULT')
