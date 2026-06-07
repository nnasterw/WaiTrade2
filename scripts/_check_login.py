#!/usr/bin/env python3
"""Check if portable terminal has login/symbol data."""
import os, re
from pathlib import Path

portable = Path('D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt')

# 1. Check recent terminal logs
log = portable / 'logs' / '20260607.log'
if log.exists():
    with open(log, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-16-le', errors='replace')
    lines = text.split('\n')
    # Find login/connection status
    for l in lines:
        lc = re.sub(r'[^\x20-\x7E\[\]\{\}\(\)\<\>]', '', l).strip()
        if any(kw in lc.lower() for kw in ['login', 'account', 'connected', 'success']):
            print(f'LOG: {lc[:120]}')

# 2. Check if Exness-MT5Trial5 symbol data exists
bases = portable / 'bases' / 'Exness-MT5Trial5' / 'symbols'
if bases.exists():
    files = list(bases.iterdir())
    print(f'\nSymbol files: {len(files)}')
    for f in files:
        print(f'  {f.name} ({f.stat().st_size/1024:.0f}K)')

# 3. Check tick data
ticks = portable / 'bases' / 'Exness-MT5Trial5' / 'ticks'
if ticks.exists():
    tick_files = list(ticks.iterdir())
    print(f'\nTick data dirs: {len(tick_files)}')
    for d in tick_files:
        if d.is_dir():
            files = list(d.iterdir())
            print(f'  {d.name}: {len(files)} files')

# 4. Verify the portable terminal exe exists
print(f'\nTerminal: {portable/"terminal64.exe"} exists={portable/"terminal64.exe"=}')
print(f'Config dir: {len(list((portable/"config").iterdir())) if (portable/"config").exists() else 0} files')

# 5. Check the portable terminal has the accounts.dat (credentials)
acct = portable / 'config' / 'accounts.dat'
print(f'accounts.dat: {acct.exists()} ({acct.stat().st_size/1024:.0f}K)' if acct.exists() else 'accounts.dat: MISSING')

# 6. Does it have symbol XAUUSDm?
hist_dir = portable / 'bases' / 'Exness-MT5Trial5' / 'history' / 'XAUUSDm'
if hist_dir.exists():
    h_files = list(hist_dir.iterdir())
    print(f'\nXAUUSDm history: {len(h_files)} files')
    for f in h_files:
        print(f'  {f.name} ({f.stat().st_size/1024:.0f}K)')
else:
    print('\nXAUUSDm history: MISSING (login needed to download)')

print('\nDone')
