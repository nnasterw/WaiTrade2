#!/usr/bin/env python3
"""Recalibrate noise params on new .ex5 — SILENT runner."""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

SL5_M2 = {'InpSLBufferATR':'0.5','InpMaxPosMult':'2.0'}

def N(lb, ratio, range_atr):
    return {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
            'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpEnableMTF':'false',
            'InpTickNoiseGateLookback':str(lb),
            'InpTickNoiseGateMinDirRatio':str(ratio),
            'InpTickNoiseGateMaxRangeATR':str(range_atr)}

def AD(dd_pct):
    return {'InpAdaptiveNoiseDrawdownPct':str(dd_pct),
            'InpAdaptiveNoiseDefMinDirRatio':'0.45',
            'InpAdaptiveNoiseDefMaxRangeATR':'0.10',
            'InpAdaptiveNoiseRecoveryPct':'1.0'}

VARIANTS = [
    ('OFF',  'QS3 OFF(新ex5基线)', {}),
    ('N10',  'NK10(lb10/r0.20)', {**SL5_M2, **N(10,0.20,0.25)}),
    ('N15',  'NK15(lb15/r0.25)', {**SL5_M2, **N(15,0.25,0.20)}),
    ('N20',  'NK20(lb20/r0.30)', {**SL5_M2, **N(20,0.30,0.18)}),
    ('N30',  'NK30(lb30/r0.35)', {**SL5_M2, **N(30,0.35,0.15)}),
    ('N15A5','NK15+AdpDD5%', {**SL5_M2, **N(15,0.25,0.20), **AD(5.0)}),
    ('N15A8','NK15+AdpDD8%', {**SL5_M2, **N(15,0.25,0.20), **AD(8.0)}),
    ('N20A5','NK20+AdpDD5%', {**SL5_M2, **N(20,0.30,0.18), **AD(5.0)}),
]

MONTHS = [('2505','2025.05.01','2025.05.31'),('2605','2026.05.01','2026.05.31')]

total = len(VARIANTS) * 2
print(f"\n{'='*70}\n  NEW EX5 CAL: {len(VARIANTS)}v x 2m = {total}BT [SILENT]\n{'='*70}")

set_files = {}
for key, label, ov in VARIANTS:
    set_files[key] = make_set(f'ne_{key}', ov)

results = {}; done = 0
for vkey, vlabel, _ in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1; key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<28} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'ne_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r: print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  PnL=${r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else: print('FAILED')

ref_off_25 = results.get('OFF_2505', {}); ref_off_26 = results.get('OFF_2605', {})
print(f"\n{'='*70}\n  RESULTS\n{'='*70}")
print(f"\n{'Variant':<30} {'2505 T':>5} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'PF':>5} {'PnL':>10} | vsOFF25 vsOFF26")
print('-'*90)
for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {}); r26 = results.get(f'{vkey}_2605', {})
    if not r25 or not r26: continue
    d25 = r25['pnl'] - ref_off_25.get('pnl', 0)
    d26 = r26['pnl'] - ref_off_26.get('pnl', 0)
    tag = ' [+2605]' if r26['pnl'] > 0 else ''
    print(f'{vlabel:<30} {r25["count"]:>5} {r25["pf"]:>5.2f} ${r25["pnl"]:>+9.2f} | {r26["count"]:>5} {r26["pf"]:>5.2f} ${r26["pnl"]:>+9.2f} | ${d25:>+7.0f} ${d26:>+7.2f}{tag}')
print(f'\n[DONE]')
