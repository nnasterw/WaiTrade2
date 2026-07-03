#!/usr/bin/env python3
"""Test with C: installed terminal WITHOUT killing existing processes first."""
import sys, os
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

# Check if any MT5 terminal is already running
import subprocess, re
result = subprocess.run(['tasklist', '/fi', 'IMAGENAME eq terminal64.exe', '/nh'],
  capture_output=True, text=True, shell=True)
running = 'terminal64' in result.stdout
print(f'C: terminal64.exe already running: {running}')

BASE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0'}
PB07 = {**BASE,
    'InpEnableLiquiditySweep':'true','InpEnableStateFilter':'true',
    'InpEnableDoubleSweepConfirm':'true','InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true','InpAdaptiveNoiseDefBoostMult':'0.7'}

print(f'Terminal: {MT5_TERMINAL}')
print(f'Data: {MT5_DATA}')
print()

# Don't kill_mt5 - use existing connection
# Create INI and run BT
sn = make_set('cdirect', PB07, base='v11xau-qs3.set')
proc = subprocess.Popen([MT5_TERMINAL, f'/config:{os.path.join(str(MT5_DATA), "Tester", "backtest.ini")}'],
    creationflags=subprocess.CREATE_NO_WINDOW)

import time, threading
def _hide_all():
    import win32gui
    def enum_cb(hwnd, _):
        t = win32gui.GetWindowText(hwnd)
        if 'MetaTrader' in t or 'Strategy Tester' in t or 'Agent' in t:
            win32gui.ShowWindow(hwnd, 0)
            win32gui.SetWindowPos(hwnd, 0, -10000, -10000, 0, 0, 0x0001)
    win32gui.EnumWindows(enum_cb, None)

# Phase 1: 3 seconds of fast polling
t0 = time.time()
while time.time() - t0 < 3.0:
    try: _hide_all()
    except: pass
    time.sleep(0.001)

# Phase 2: background
def _poller(p):
    while p.poll() is None:
        try: _hide_all()
        except: pass
        time.sleep(0.1)
threading.Thread(target=_poller, args=(proc,), daemon=True).start()

# Wait for report
htm = MT5_DATA / 'cdirect.htm'
if htm.exists(): htm.unlink()
t0 = time.time()
r = None
while time.time() - t0 < 120:
    if proc.poll() is not None: break
    if htm.exists() and htm.stat().st_size > 1000:
        from bt_shared import parse_report
        r = parse_report(str(htm))
        break
    time.sleep(1)

if r:
    print(f'SUCCESS: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PnL=${r["pnl"]:>+9.2f}')
else:
    print('FAILED')
    # Check log
    logs = sorted([p for p in Path(str(MT5_DATA)).glob('Tester/logs/*.log')], key=os.path.getmtime)
    if logs:
        with open(logs[-1], 'rb') as f: text = f.read().decode('utf-16-le', errors='replace')
        for l in text.split('\n')[-10:]:
            lc = re.sub(r'[^\x20-\x7E\[\]\{\}\(\)\<\>\=\:\;\,\.\/\\\\]', '', l) if l else ''
            if lc.strip(): print(f'  LOG: {lc.strip()[:120]}')
print('DONE')
