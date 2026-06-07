#!/usr/bin/env python3
"""Final test: proper run_bt_silent with C: terminal."""
import sys, os
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

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

# Test full month (2605) with C: terminal
print(f'Terminal: {MT5_TERMINAL}')
print(f'Data: {MT5_DATA}')
print()

sn = make_set('final_test', PB07, base='v11xau-qs3.set')
# Skip kill_mt5 - keep existing Exness connection alive
# kill_mt5()
r = run_bt_silent('final_test', sn, '2026.05.01', '2026.05.31')
if r:
    print(f'✅ SUCCESS: {r["count"]}T WR={r["wr"]:.1f}% PF={r["pf"]:.2f} PnL=${r["pnl"]:+.2f}')
else:
    print('FAILED')

# Also check log for "tester" errors
log_dir = Path(str(MT5_DATA)) / 'Tester' / 'logs'
log_files = sorted(log_dir.glob('*.log'), key=os.path.getmtime)
if log_files:
    with open(log_files[-1], 'rb') as f:
        text = f.read().decode('utf-16-le', errors='replace')
    for l in text.split('\n'):
        if 'tester' in l.lower() and ('fail' in l.lower() or 'error' in l.lower() or 'didn' in l.lower()):
            import re
            lc = re.sub(r'[^\x20-\x7E\[\]\{\}\(\)\<\>\=\:\;\,\.\/\\\\]', '', l).strip()
            print(f'  TESTER: {lc[:120]}')

print('DONE')
