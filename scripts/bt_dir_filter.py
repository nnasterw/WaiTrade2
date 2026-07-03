#!/usr/bin/env python3
"""Test defensive direction position filter on 2026 losing months."""
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

BASE = {
    'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpEnableMTF':'false',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0',
}

VARIANTS = [
    ('REF','基准',{}),
    ('D1','DefSell=0.5',{'InpAdaptiveNoiseDefSellMult':'0.5'}),
    ('D2','DefSell=0.3',{'InpAdaptiveNoiseDefSellMult':'0.3'}),
]

# Test on 2603 (worst direction skew) and 2605 (balanced direction)
for month, mfrom, mto in [('2603','2026.03.01','2026.03.31'),('2605','2026.05.01','2026.05.31')]:
    print(f"\n--- {month} ---")
    for key, label, ov in VARIANTS:
        m = dict(BASE); m.update(ov)
        sn = make_set(f'dir_{key}', m, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'dir_{key}_{month}', sn, mfrom, mto)
        if r: print(f'  {label:<20}: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PnL=${r["pnl"]:>+8.2f}')
        else: print(f'  {label}: FAILED')
print('DONE')
