#!/usr/bin/env python3
"""Quick verify: new ex5 vs old results."""
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

BASE = {
    'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpEnableMTF':'true',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0',
    'InpEnableHTFNetPushFilter':'true','InpHTFNetPushTF':'15',
    'InpHTFNetPushBars':'4','InpHTFNetPushMinATR':'0.50',
    'InpHTFNetPushAlignedMult':'1.0','InpHTFNetPushNeutralMult':'1.0','InpHTFNetPushCounterMult':'1.0',
}

for label, ov in [('REF',{}), ('AdaptN0',{'InpAdaptiveNoiseDefNeutralMult':'0.0'})]:
    m = dict(BASE); m.update(ov)
    sn = make_set('vfy_'+label, m, base='v11xau-qs3.set')
    kill_mt5()
    r = run_bt_silent('vfy_'+label+'_2605', sn, '2026.05.01', '2026.05.31')
    if r: print(f'{label}: {r["count"]}T WR={r["wr"]:.1f}% PnL=${r["pnl"]:+.2f}')
    else: print(f'{label}: FAILED')
print('DONE')
