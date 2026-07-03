#!/usr/bin/env python3
"""Test global defensive position decay in CalcPositionMultiplier."""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

P1 = {
    'InpEnableTickNoiseGate': 'true', 'InpEnableDynamicSpread': 'true',
    'InpMinSLSpreadMult': '5.0', 'InpOBTouchConfirmTicks': '5',
    'InpEnableMTF': 'false',
    'InpSLBufferATR': '0.4', 'InpMaxPosMult': '2.0',
    'InpTickNoiseGateLookback': '10', 'InpTickNoiseGateMinDirRatio': '0.20',
    'InpTickNoiseGateMaxRangeATR': '0.25',
    'InpAdaptiveNoiseDrawdownPct': '3.0', 'InpAdaptiveNoiseDefMinDirRatio': '0.30',
    'InpAdaptiveNoiseDefMaxRangeATR': '0.16', 'InpAdaptiveNoiseRecoveryPct': '1.0',
    'InpDTPTriggerR': '1.0', 'InpDTPRetrace': '0.20', 'InpDTPPartialPct': '50',
    'InpBreakevenR': '0.0', 'InpBreakevenLockR': '0.0',
}

VARIANTS = [
    ('REF', 'REF-P1(无全局衰减)', {'InpAdaptiveNoiseDefBoostMult': '1.0'}),
    ('G1',  'GlobalDecay-0.7',     {'InpAdaptiveNoiseDefBoostMult': '0.7'}),
    ('G2',  'GlobalDecay-0.5',     {'InpAdaptiveNoiseDefBoostMult': '0.5'}),
    ('G3',  'GlobalDecay-0.3',     {'InpAdaptiveNoiseDefBoostMult': '0.3'}),
]

MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]
total = len(VARIANTS) * 2
print(f"Global Decay: {total} BTs")

set_files = {}
for key, label, ov in VARIANTS:
    m = dict(P1); m.update(ov)
    set_files[key] = make_set(f'gd_{key}', m, base='v11xau-qs3.set')

results = {}; done = 0
for vkey, vlabel, ov in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1; key = f'{vkey}_{mkey}'
        print(f'[{done}/{total}] {vlabel:<30} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'gd_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r: print(f'{r["count"]:>5}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=$ {r["pnl"]:>+9.2f}')
        else: print('FAILED')

ref_25 = results.get('REF_2505', {}).get('pnl', 0)
ref_26 = results.get('REF_2605', {}).get('pnl', 0)
print(f"\nREF: 2505=${ref_25:,.0f} 2605=${ref_26:,.2f}")

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        d26 = r26['pnl'] - ref_26
        mark = ' [2605+]' if r26['pnl'] > 0 else ''
        print(f"{vlabel:<30} 2505={r25['count']:>4}T ${r25['pnl']:>+9,.0f} | 2605={r26['count']:>4}T ${r26['pnl']:>+9.2f} | d26={d26:+.2f}{mark}")
print("[DONE]")
