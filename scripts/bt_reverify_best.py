#!/usr/bin/env python3
"""Re-verify best configs with CORRECT ex5."""
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5'}

# S1: H5+LOOSE (no MTF, no adaptive)
S1 = {**NOISE, 'InpEnableMTF':'false',
    'InpSLBufferATR':'0.5','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0'}

# S2: H5+AD-LOOSE (adaptive, no MTF)
S2 = {**NOISE, 'InpEnableMTF':'false',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0'}

# S2+MTF: S2 with MTF enabled + Adaptive Neutral
S2_MTF = {**S2, 'InpEnableMTF':'true',
    'InpEnableHTFNetPushFilter':'true','InpHTFNetPushTF':'15',
    'InpHTFNetPushBars':'4','InpHTFNetPushMinATR':'0.50',
    'InpHTFNetPushAlignedMult':'1.0','InpHTFNetPushNeutralMult':'1.0',
    'InpHTFNetPushCounterMult':'1.0'}

VARIANTS = [
    ('S1','S1(H5+LOOSE)',S1,{}),
    ('S2','S2(H5+AD-LOOSE)',S2,{}),
    ('S2M','S2+MTF(ref)',S2_MTF,{}),
    ('S2MN','S2+MTF+AdaptN0',S2_MTF,{'InpAdaptiveNoiseDefNeutralMult':'0.0'}),
    # Also test: OB cooldown with new ex5
    ('S2MO','S2+MTF+AdaptOB-5',S2_MTF,{'InpAdaptiveNoiseDefOBReentryCd':'5'}),
    # Combined: Neutral + OB cooldown
    ('S2MC','S2+MTF+AdaptN0+OB5',S2_MTF,{'InpAdaptiveNoiseDefNeutralMult':'0.0','InpAdaptiveNoiseDefOBReentryCd':'5'}),
]

for month,mfrom,mto in [('2505','2025.05.01','2025.05.31'),('2605','2026.05.01','2026.05.31')]:
    print(f'\n=== {month} ===')
    for key,label,base,ov in VARIANTS:
        m = dict(base); m.update(ov)
        sn = make_set(f'rv_{key}', m, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'rv_{key}_{month}', sn, mfrom, mto)
        if r: print(f'  {label:<25}: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+9.2f}')
        else: print(f'  {label}: FAILED')
print('DONE')
