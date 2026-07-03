#!/usr/bin/env python3
"""Backtest 2025.05.29 with portable terminal on D:."""
import sys, os
os.environ['MT5_HOME'] = 'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt'
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

print(f'MT5_DATA={MT5_DATA}')

# QS3 base config (from v11xau-qs3.set base)
BASE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
}

# PathB + decay0.7 (current best)
PB07 = {**BASE,
    'InpEnableLiquiditySweep':'true', 'InpEnableStateFilter':'true',
    'InpEnableDoubleSweepConfirm':'true', 'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true', 'InpAdaptiveNoiseDefBoostMult':'0.7',
}

sn = make_set('t0529', PB07, base='v11xau-qs3.set')
kill_mt5()
r = run_bt_silent('t0529', sn, '2025.05.29', '2025.05.29')
if r:
    print(f'\nRESULT: {r["count"]}T WR={r["wr"]:.1f}% PF={r["pf"]:.2f} PnL=${r["pnl"]:+.2f}')
    htm = MT5_DATA / 't0529.htm'
    print(f'Report: {htm}')
else:
    print('FAILED')
print('DONE')
