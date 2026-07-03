#!/usr/bin/env python3
"""Backtest 2025.05.29 using installed terminal (has 2025 data)."""
import sys, os
# Use installed terminal (not portable)
if 'MT5_HOME' in os.environ: del os.environ['MT5_HOME']
if 'MT5_DATA' in os.environ: del os.environ['MT5_DATA']
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *
print(f'MT5_TERMINAL={MT5_TERMINAL}')
print(f'MT5_DATA={MT5_DATA}')

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

for label, f, t in [('0529_1d', '2025.05.29', '2025.05.29'),
                     ('2605_1d', '2026.05.01', '2026.05.01')]:
    sn = make_set(f'it_{label}', PB07, base='v11xau-qs3.set')
    kill_mt5()
    r = run_bt_silent(f'it_{label}', sn, f, t)
    if r:
        print(f'{label}: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+9.2f}')
    else:
        print(f'{label}: FAILED')
print('DONE')
