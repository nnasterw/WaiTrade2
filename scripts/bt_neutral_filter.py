#!/usr/bin/env python3
"""Test hypothesis: Block NEUTRAL (no trend) entries, keep COUNTER (pullbacks).
Neutral = ranging market, entries are random → block.
Counter = strong trend exists, just opposite direction → might be OK (pullback)."""
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE_BASE = {
    'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5',
}
P1 = {
    **NOISE_BASE, 'InpEnableMTF':'true',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0',
}

VARIANTS = [
    ('R','REF(无HTF)',{'InpEnableHTFNetPushFilter':'false'}),
    # Block Neutral (no trend = ranging = bad)
    ('N0','NeutralBlock(M15)',{'InpEnableHTFNetPushFilter':'true','InpHTFNetPushTF':'15',
        'InpHTFNetPushBars':'4','InpHTFNetPushMinATR':'0.50',
        'InpHTFNetPushAlignedMult':'1.0','InpHTFNetPushNeutralMult':'0.0',
        'InpHTFNetPushCounterMult':'1.0'}),
    ('N1','NeutralHalf(M15)',{'InpEnableHTFNetPushFilter':'true','InpHTFNetPushTF':'15',
        'InpHTFNetPushBars':'4','InpHTFNetPushMinATR':'0.50',
        'InpHTFNetPushAlignedMult':'1.0','InpHTFNetPushNeutralMult':'0.5',
        'InpHTFNetPushCounterMult':'1.0'}),
    # Block Neutral on H1
    ('N2','NeutralBlock(H1)',{'InpEnableHTFNetPushFilter':'true','InpHTFNetPushTF':'60',
        'InpHTFNetPushBars':'3','InpHTFNetPushMinATR':'0.40',
        'InpHTFNetPushAlignedMult':'1.0','InpHTFNetPushNeutralMult':'0.0',
        'InpHTFNetPushCounterMult':'1.0'}),
    # Block BOTH Neutral AND Counter (strictest)
    ('N3','Neutral0+Counter0(H1)',{'InpEnableHTFNetPushFilter':'true','InpHTFNetPushTF':'60',
        'InpHTFNetPushBars':'3','InpHTFNetPushMinATR':'0.40',
        'InpHTFNetPushAlignedMult':'1.0','InpHTFNetPushNeutralMult':'0.0',
        'InpHTFNetPushCounterMult':'0.0'}),
    # Lower MinATR threshold (more entries classified as trending)
    ('N4','NeutralBlock(lowATR=0.3)',{'InpEnableHTFNetPushFilter':'true','InpHTFNetPushTF':'15',
        'InpHTFNetPushBars':'4','InpHTFNetPushMinATR':'0.30',
        'InpHTFNetPushAlignedMult':'1.0','InpHTFNetPushNeutralMult':'0.0',
        'InpHTFNetPushCounterMult':'1.0'}),
]

for month,mfrom,mto in [('2505','2025.05.01','2025.05.31'),('2605','2026.05.01','2026.05.31')]:
    print(f'\n=== {month} ===')
    for key,label,ov in VARIANTS:
        m = dict(P1); m.update(ov)
        sn = make_set(f'nt_{key}', m, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'nt_{key}_{month}', sn, mfrom, mto)
        if r: print(f'  {label:<25}: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+9.2f}')
        else: print(f'  {label}: FAILED')
print('DONE')
