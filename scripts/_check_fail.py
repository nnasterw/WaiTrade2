#!/usr/bin/env python3
"""Check why the 3 single-day tests failed."""
import re

logfile = r'D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt\Tester\logs\20260607.log'
with open(logfile, 'rb') as f:
    raw = f.read()
text = raw.decode('utf-16-le', errors='replace')
lines = text.split('\n')

# Find tester-related log entries near the end (our 3 tests)
print('=== Tester errors (last 50 tester lines) ===')
tester_lines = []
for l in lines:
    lc = re.sub(r'[^\x20-\x7E\[\]\{\}\(\)\<\>\=\:\;\,\.\/\\\\]', '', l).strip()
    if lc and ('tester' in lc.lower() or 'synchron' in lc.lower()):
        tester_lines.append(lc[:150])

for l in tester_lines[-20:]:
    print(l)

# Check if our test names appear
print('\n=== Test name occurrences ===')
for l in lines:
    if 'stable_' in l:
        lc = re.sub(r'[^\x20-\x7E\[\]\{\}\(\)\<\>\=\:\;\,\.\/\\\\]', '', l).strip()
        print(lc[:150])
        break
else:
    print('(none found - tests may not have started)')

# Check if process is running
import os
print(f'\n=== Terminal process ===')
os.system('ps -W 2>/dev/null | grep terminal64 || echo "not running"')

# Check portable permissions
print(f'\n=== Portable dir permissions ===')
for d in ['Tester', 'Tester/logs', 'Tester/cache', 'bases']:
    p = f'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt/{d}'
    exists = os.path.exists(p)
    writable = os.access(p, os.W_OK) if exists else False
    print(f'  {d}: exists={exists} writable={writable}')
