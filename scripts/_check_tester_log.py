#!/usr/bin/env python3
"""Read installed terminal tester log."""
import re
path = r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\Tester\logs\20260607.log'
try:
    with open(path, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-16-le', errors='replace')
    for l in text.split('\n')[-15:]:
        lc = re.sub(r'[^\x20-\x7E\[\]\{\}\(\)\<\>\=\:\;\,\.\/\\\\]', '', l).strip()
        if lc:
            print(lc[:150])
except FileNotFoundError:
    print('LOG NOT FOUND')
