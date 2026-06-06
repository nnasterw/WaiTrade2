#!/usr/bin/env python3
"""Test defensive OB reentry cooldown on 2026 losing months + 2505 verification."""
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
    ('D5','DefOB-5min',{'InpAdaptiveNoiseDefOBReentryCd':'5'}),
    ('D10','DefOB-10min',{'InpAdaptiveNoiseDefOBReentryCd':'10'}),
    ('D15','DefOB-15min',{'InpAdaptiveNoiseDefOBReentryCd':'15'}),
]

for month,mfrom,mto in [('2604','2026.04.01','2026.04.30'),
                          ('2605','2026.05.01','2026.05.31'),
                          ('2505','2025.05.01','2025.05.31')]:
    print(f'\n--- {month} ---')
    for key,label,ov in VARIANTS:
        m=dict(BASE); m.update(ov)
        sn = make_set(f'obcd_{key}', m, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'obcd_{key}_{month}', sn, mfrom, mto)
        if r: print(f'  {label:<15}: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PnL=${r["pnl"]:>+8.2f}')
        else: print(f'  {label}: FAILED')
print('DONE')
