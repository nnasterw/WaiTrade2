#!/usr/bin/env python3
"""TDD: Adaptive Neutral filter. Block neutral (no-trend) entries only when defensive."""
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE_BASE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true','InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5'}

# P1 base with MTF enabled + HTF filter
BASE = {
    **NOISE_BASE, 'InpEnableMTF':'true',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0',
    # HTF filter: M15 NeutralBlock
    'InpEnableHTFNetPushFilter':'true','InpHTFNetPushTF':'15',
    'InpHTFNetPushBars':'4','InpHTFNetPushMinATR':'0.50',
    'InpHTFNetPushAlignedMult':'1.0','InpHTFNetPushNeutralMult':'1.0',
    'InpHTFNetPushCounterMult':'1.0',
}

VARIANTS = [
    ('R','REF(NeutralMult=1)',{}),
    # Adaptive Neutral: normal=1.0, defensive=0.0 (block neutral when losing)
    ('A1','AdaptNeutral-0(def)',{'InpAdaptiveNoiseDefNeutralMult':'0.0'}),
    ('A2','AdaptNeutral-0.5(def)',{'InpAdaptiveNoiseDefNeutralMult':'0.5'}),
    # Also test: static NeutralBlock (all the time, for comparison)
    ('S0','Static-NeutralBlock',{'InpHTFNetPushNeutralMult':'0.0'}),
    ('S5','Static-NeutralHalf',{'InpHTFNetPushNeutralMult':'0.5'}),
]

for month,mfrom,mto in [('2505','2025.05.01','2025.05.31'),('2605','2026.05.01','2026.05.31')]:
    print(f'\n=== {month} ===')
    for key,label,ov in VARIANTS:
        m = dict(BASE); m.update(ov)
        sn = make_set(f'an_{key}', m, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'an_{key}_{month}', sn, mfrom, mto)
        if r: print(f'  {label:<25}: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+9.2f}')
        else: print(f'  {label}: FAILED')
print('DONE')
