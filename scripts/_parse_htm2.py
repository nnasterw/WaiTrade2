#!/usr/bin/env python3
"""Dump report structure."""
import re
text = open('D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt/24m_S2_2408.htm','rb').read().decode('utf-16-le',errors='replace')
idx = text.find('<table')
chunk = text[idx:idx+5000]
clean = re.sub(r'<[^>]+>','\n',chunk)
lines = [l.strip() for l in clean.split('\n') if l.strip()]
for l in lines[:40]:
    print(l[:120])
