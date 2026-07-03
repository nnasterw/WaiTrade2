#!/usr/bin/env python3
"""Verify adaptive noise gate on new .ex5. Uses bt_shared silent runner."""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

SL5_M2 = {'InpSLBufferATR':'0.5','InpMaxPosMult':'2.0'}
HTF_B3 = {'InpHTFNetPushAlignedMult':'1.5','InpHTFNetPushNeutralMult':'0.7','InpHTFNetPushCounterMult':'0.3'}
NOISE_ON = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
            'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpEnableMTF':'false',
            'InpTickNoiseGateLookback':'20','InpTickNoiseGateMinDirRatio':'0.30',
            'InpTickNoiseGateMaxRangeATR':'0.18'}
ADAPTIVE = {'InpAdaptiveNoiseDrawdownPct':'2.0','InpAdaptiveNoiseDefMinDirRatio':'0.45',
            'InpAdaptiveNoiseDefMaxRangeATR':'0.10','InpAdaptiveNoiseRecoveryPct':'1.0'}

TESTS = [
    ('REF_B3',  'B3(HTF强对齐)基线', {**SL5_M2, **HTF_B3}),
    ('B3_AD',   'B3+自适应噪音(DD2%)', {**SL5_M2, **HTF_B3, **NOISE_ON, **ADAPTIVE}),
    ('B3_N20',  'B3+固定噪音NK20', {**SL5_M2, **HTF_B3, **NOISE_ON}),
    ('REF_P1',  'P1(最佳基线)', {**SL5_M2, **NOISE_ON}),
]

MONTHS = [('2505','2025.05.01','2025.05.31'),('2605','2026.05.01','2026.05.31')]

total = len(TESTS) * 2
print(f"\n{'='*70}\n  VERIFY: Adaptive noise gate ({len(TESTS)}v x 2m = {total}BT) [SILENT]\n{'='*70}")

set_files = {}
for key, label, ov in TESTS:
    set_files[key] = make_set(f'av_{key}', ov)

results = {}; done = 0
for vkey, vlabel, _ in TESTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1; key = f'{vkey}_{mkey}'
        print(f'[{done}/{total}] {vlabel:<30} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'av_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r: print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  PnL=${r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else: print('FAILED')

ref_p1_25 = results.get('REF_P1_2505', {}); ref_p1_26 = results.get('REF_P1_2605', {})
print(f"\n{'='*70}\n  Results\n{'='*70}")
print(f"\n{'Variant':<30} {'2505 T':>5} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'PF':>5} {'PnL':>10} | vsP1")
print('-'*85)
for vkey, vlabel, _ in TESTS:
    r25 = results.get(f'{vkey}_2505', {}); r26 = results.get(f'{vkey}_2605', {})
    if not r25 or not r26: continue
    d25 = r25['pnl'] - ref_p1_25.get('pnl', 0)
    d26 = r26['pnl'] - ref_p1_26.get('pnl', 0)
    tag = ' [2605+]' if r26['pnl'] > 0 else ''
    print(f'{vlabel:<30} {r25["count"]:>5} {r25["pf"]:>5.2f} ${r25["pnl"]:>+9.2f} | {r26["count"]:>5} {r26["pf"]:>5.2f} ${r26["pnl"]:>+9.2f} | d25=${d25:+.0f} d26=${d26:+.2f}{tag}')
print(f'\n[DONE]')
