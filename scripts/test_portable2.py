#!/usr/bin/env python3
"""Debug portable terminal backtest."""
import os, sys, subprocess, time
from pathlib import Path

MT5_HOME = Path(r'D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = MT5_HOME

print(f'Terminal: {MT5_TERMINAL}')
print(f'Exists: {Path(MT5_TERMINAL).exists()}')

# Write ini
ini_path = MT5_DATA / 'Tester' / 'backtest.ini'
ini_path.parent.mkdir(parents=True, exist_ok=True)
ini_path.write_text(
    "[Common]\nLogin=\nServer=\n"
    "[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\n"
    "ExpertParameters=v11xau-qs3.set\n"
    "Symbol=XAUUSDm\nPeriod=M1\nModel=4\n"
    "Optimization=0\n"
    "FromDate=2026.05.01\nToDate=2026.05.03\n"
    "Deposit=200\nCurrency=USD\nLeverage=2000\n"
    "ExecutionMode=0\nShutdownTerminal=1\n"
    "Report=ptest_debug\n", encoding='utf-8')
print(f'INI: {ini_path}')
print(f'INI content: {ini_path.read_text()[:200]}')

# Verify .set exists
set_path = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester' / 'v11xau-qs3.set'
print(f'.set exists: {set_path.exists()} (size: {set_path.stat().st_size if set_path.exists() else 0})')

# Verify .ex5 exists
ex5_path = MT5_DATA / 'MQL5' / 'Experts' / 'WaiTrade2' / 'WaiTrade_OB.ex5'
print(f'.ex5 exists: {ex5_path.exists()} (size: {ex5_path.stat().st_size if ex5_path.exists() else 0})')

# Run NOT silent to see errors
print('\nLaunching terminal64 (visible mode for debug)...')
proc = subprocess.Popen(
    [MT5_TERMINAL, '/portable', f'/config:{ini_path}'],
    creationflags=0)  # visible!
print(f'PID: {proc.pid}')

# Wait max 60s
t0 = time.time()
report = MT5_DATA / 'ptest_debug.htm'
while time.time() - t0 < 60:
    if proc.poll() is not None:
        print(f'Process exited with code {proc.returncode} at {time.time()-t0:.0f}s')
        break
    if report.exists() and report.stat().st_size > 1000:
        print(f'Report generated at {time.time()-t0:.0f}s: {report.stat().st_size} bytes')
        break
    time.sleep(1)

if proc.poll() is None:
    print('Still running after 60s - killing')
    proc.kill()

# Check logs
log_dir = MT5_DATA / 'Tester' / 'logs'
log_files = sorted(log_dir.glob('*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
if log_files:
    latest = log_files[0]
    print(f'\nLatest log: {latest.name}')
    try:
        text = latest.read_bytes().decode('utf-16-le', errors='replace')
        errors = [l for l in text.split('\n') if 'error' in l.lower() or 'fail' in l.lower()][:5]
        for e in errors:
            print(f'  {e[:200]}')
    except:
        print('  (cannot read)')

print('\nDONE')
