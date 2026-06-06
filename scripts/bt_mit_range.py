#!/usr/bin/env python3
"""Targeted test: Mitigation with OnlyRange=true to protect trend months."""
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5'}
H5_EXIT = {'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0'}

S2 = {**NOISE, 'InpEnableMTF':'false',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    **H5_EXIT}

# SWP baseline (no mitigation, sweep enabled)
SWP = {**S2, 'InpEnableLiquiditySweep':'true', 'InpEnableStateFilter':'true'}

# Core mitigation: OnlyRange=true (only range markets)
MIT_RANGE = {'InpEnableMitigationEntry':'true', 'InpMitigationEntryMaxBars':'10',
    'InpMitigationEntryOnlyRange':'true', 'InpMitigationEntrySignalTypes':'sweep'}

# Also test: mitigation for ALL signal types, range-only
MIT_ALL_RANGE = {**MIT_RANGE, 'InpMitigationEntrySignalTypes':'all'}

VARIANTS = [
    ('S2','S2原版(H5+AD)',S2,{}),
    ('SWP','SWP基准',SWP,{}),
    ('MTR','Mit+RangeOnly',SWP,MIT_RANGE),
    ('MAR','MitAll+RangeOnly',SWP,MIT_ALL_RANGE),
]

for month,mfrom,mto in [('2605','2026.05.01','2026.05.31'),
                          ('2505','2025.05.01','2025.05.31')]:
    print(f'\n=== {month} ===')
    for vkey,vlabel,base,ov in VARIANTS:
        m = dict(base); m.update(ov)
        sn = make_set(f'mr_{vkey}', m, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'mr_{vkey}_{month}', sn, mfrom, mto)
        if r: print(f'  {vlabel:<22}: {r["count"]:>5}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+10.2f}')
        else: print(f'  {vlabel}: FAILED')
print('DONE')
