#!/usr/bin/env python3
"""Re-run Path B and S2 for wf-analyze-cl deep analysis. Preserve HTML reports."""
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5'}
H5 = {'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0'}

S2 = {**NOISE, 'InpEnableMTF':'false', 'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    **H5}

# Path B config
PATH_B = {**S2,
    'InpEnableLiquiditySweep':'true', 'InpEnableStateFilter':'true',
    'InpEnableDoubleSweepConfirm':'true',
    'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true',
    'InpAdaptiveNoiseDrawdownPct':'3.0',
}

for label, cfg, mfrom, mto in [
    ('S2_2605', S2, '2026.05.01', '2026.05.31'),
    ('S2_2505', S2, '2025.05.01', '2025.05.31'),
    ('B_2605', PATH_B, '2026.05.01', '2026.05.31'),
    ('B_2505', PATH_B, '2025.05.01', '2025.05.31'),
    ('B_2604', PATH_B, '2026.04.01', '2026.04.30'),
]:
    sn = make_set(f'wf_{label}', cfg, base='v11xau-qs3.set')
    kill_mt5()
    r = run_bt_silent(f'wf_{label}', sn, mfrom, mto)
    if r: print(f'{label}: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+10.2f}')
    else: print(f'{label}: FAILED')
print('DONE')
