#!/usr/bin/env python3
"""Check if installed terminal is connected to Exness."""
import re

logfile = r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\logs\20260607.log'
with open(logfile, 'rb') as f:
    text = f.read().decode('utf-16-le', errors='replace')

lines = text.split('\n')
print(f'Total log entries: {len(lines)}')

# Check connection status
for l in lines:
    lc = re.sub(r'[^\x20-\x7E\[\]\{\}\(\)\<\>\=\:\;\,\.\/\\\\]', '', l).strip()
    if not lc: continue
    if any(kw in lc for kw in ['connect', 'login', 'authoriz', 'disconnect', 'synchron', 'fail']):
        print(lc[:150])

print('\n---')
# Last 5 lines
for l in lines[-5:]:
    lc = re.sub(r'[^\x20-\x7E\[\]\{\}\(\)\<\>\=\:\;\,\.\/\\\\]', '', l).strip()
    if lc: print(lc[:150])
