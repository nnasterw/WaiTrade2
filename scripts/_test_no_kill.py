#!/usr/bin/env python3
"""Test 2025.05.29 WITHOUT killing the running terminal."""
import sys, os
if 'MT5_HOME' in os.environ: del os.environ['MT5_HOME']
if 'MT5_DATA' in os.environ: del os.environ['MT5_DATA']
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

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
PB07 = {**BASE,
    'InpEnableLiquiditySweep':'true', 'InpEnableStateFilter':'true',
    'InpEnableDoubleSweepConfirm':'true', 'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true', 'InpAdaptiveNoiseDefBoostMult':'0.7',
}

# DON'T call kill_mt5() - preserves the running terminal's Exness connection
print(f'Skipping kill_mt5() - keeping Live terminal alive')
sn = make_set('nk0529', PB07, base='v11xau-qs3.set')

# Custom run_bt that doesn't kill mt5
r = run_bt_silent('nk0529', sn, '2025.05.29', '2025.05.29')
if r:
    print(f'\n2505.05.29: {r["count"]}T WR={r["wr"]:.1f}% PF={r["pf"]:.2f} PnL=${r["pnl"]:+.2f}')
else:
    print('\n0529 FAILED')
print('DONE')
