#!/usr/bin/env python3
"""Test Model 0 (no Exness connection needed)."""
import sys, os
os.environ['MT5_HOME'] = 'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_xau'
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

BASE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
}
PB07 = {**BASE,
    'InpEnableLiquiditySweep':'true', 'InpEnableStateFilter':'true',
    'InpEnableDoubleSweepConfirm':'true', 'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true', 'InpAdaptiveNoiseDefBoostMult':'0.7',
}

# Test with Model 0 (no Exness needed)
print('Testing Model 0 (Offline mode, no Exness)...')
sn = make_set('m0test', PB07, base='v11xau-qs3.set')

# Modify ini to force Model 0 instead of Model 4
ini_path = MT5_DATA / 'Tester' / 'backtest.ini'
ini_text = ini_path.read_text('utf-8').replace('Model=4', 'Model=0')
ini_path.write_text(ini_text, 'utf-8')

kill_mt5()
r = run_bt_silent('m0test', sn, '2026.06.01', '2026.06.01')
if r:
    htm = MT5_DATA / 'm0test.htm'
    print(f'Model 0 OK: {r["count"]}T WR={r["wr"]:.1f}% PnL=${r["pnl"]:+.2f}')
else:
    print('Model 0 FAILED')
print('DONE')
