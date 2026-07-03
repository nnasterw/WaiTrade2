#!/usr/bin/env python3
"""Read portable terminal tester log."""
import re

logfile = r'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt/Tester/logs/20260607.log'
with open(logfile, 'rb') as f:
    raw = f.read()
text = raw.decode('utf-16-le', errors='replace')
lines = text.split('\n')

# Find tester errors/summaries
for l in lines:
    lc = re.sub(r'[^\x20-\x7E\[\]\{\}\(\)\<\>\=\:\;\,\.\/\\\\]', '', l).strip()
    if not lc:
        continue
    # Only print tester-related entries
    if any(kw in lc for kw in ['Tester', 'tester', 'error', 'Error', 'fail', 'Expert', 'expert']):
        print(lc[:150])

# Print last 10 lines
print('\n=== LAST LINES ===')
for l in lines[-10:]:
    lc = re.sub(r'[^\x20-\x7E\[\]\{\}\(\)\<\>\=\:\;\,\.\/\\\\]', '', l).strip()
    if lc:
        print(lc[:150])
