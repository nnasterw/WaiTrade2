#!/usr/bin/env python3
"""Final: H5(DTP=1.0R,BE=off) + loose noise gate + adaptive variants.
Goal: 2505>$5K AND 2605>0 using the BE-off breakthrough."""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE_BASE = {
    'InpEnableTickNoiseGate': 'true',
    'InpEnableDynamicSpread': 'true',
    'InpMinSLSpreadMult': '5.0',
    'InpOBTouchConfirmTicks': '5',
    'InpEnableMTF': 'false',
}
SL5_M2 = {'InpSLBufferATR': '0.5', 'InpMaxPosMult': '2.0'}

# H5 exit: DTP=1.0R, BE=off
H5_EXIT = {
    'InpDTPTriggerR': '1.0', 'InpDTPRetrace': '0.20',
    'InpDTPPartialPct': '50',
    'InpBreakevenR': '0.0', 'InpBreakevenLockR': '0.0',
}

VARIANTS = [
    # Reference baselines
    ('REF_OFF', 'REF-QS3-OFF(原始DTP=1.5R,BE=0.5)', {}),
    ('REF_LOOSE', 'REF-LOOSE(lb10/r20/a25)', {
        **NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '10',
        'InpTickNoiseGateMinDirRatio': '0.20',
        'InpTickNoiseGateMaxRangeATR': '0.25',
    }),
    ('REF_BEST', 'REF-BEST(H5 DTP=1.0R,BE=off,lb20/r25/a18)', {
        **NOISE_BASE, **SL5_M2, **H5_EXIT,
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.25',
        'InpTickNoiseGateMaxRangeATR': '0.18',
    }),

    # H5 exits + LOOSE noise gate (target: 2505>$5K + 2605>0)
    ('F1', 'H5+LOOSE(lb10/r20/a25)', {
        **NOISE_BASE, **SL5_M2, **H5_EXIT,
        'InpTickNoiseGateLookback': '10',
        'InpTickNoiseGateMinDirRatio': '0.20',
        'InpTickNoiseGateMaxRangeATR': '0.25',
    }),
    ('F2', 'H5+MID(lb15/r25/a22)', {
        **NOISE_BASE, **SL5_M2, **H5_EXIT,
        'InpTickNoiseGateLookback': '15',
        'InpTickNoiseGateMinDirRatio': '0.25',
        'InpTickNoiseGateMaxRangeATR': '0.22',
    }),

    # H5 exits + Adaptive noise gate
    ('F3', 'H5+AD(dd3% a22->a16)', {
        **NOISE_BASE, **SL5_M2, **H5_EXIT,
        'InpTickNoiseGateLookback': '15',
        'InpTickNoiseGateMinDirRatio': '0.25',
        'InpTickNoiseGateMaxRangeATR': '0.22',
        'InpAdaptiveNoiseDrawdownPct': '3.0',
        'InpAdaptiveNoiseDefMinDirRatio': '0.30',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
        'InpAdaptiveNoiseRecoveryPct': '1.0',
    }),

    # H5+AD with LOOSE normal
    ('F4', 'H5+AD-LOOSE(dd3% a25->a16)', {
        **NOISE_BASE, **SL5_M2, **H5_EXIT,
        'InpTickNoiseGateLookback': '10',
        'InpTickNoiseGateMinDirRatio': '0.20',
        'InpTickNoiseGateMaxRangeATR': '0.25',
        'InpAdaptiveNoiseDrawdownPct': '3.0',
        'InpAdaptiveNoiseDefMinDirRatio': '0.30',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
        'InpAdaptiveNoiseRecoveryPct': '1.0',
    }),
]

MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]
total = len(VARIANTS) * 2
print(f"\n{'='*70}")
print(f"  FINAL: H5(DTP=1.0R,BE=off) + Loose/Adaptive Noise Gate")
print(f"  {len(VARIANTS)}v x 2m = {total} BTs")
print(f"{'='*70}")

set_files = {}
for key, label, ov in VARIANTS:
    set_files[key] = make_set(f'fin_{key}', ov, base='v11xau-qs3.set')

results = {}
done = 0
for vkey, vlabel, ov in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1
        key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<42} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'fin_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=$ {r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:
            print('FAILED')

# ===== SUMMARY =====
ref_off_25 = results.get('REF_OFF_2505', {}).get('pnl', 0)
ref_off_26 = results.get('REF_OFF_2605', {}).get('pnl', 0)
ref_loose_25 = results.get('REF_LOOSE_2505', {}).get('pnl', 0)
ref_loose_26 = results.get('REF_LOOSE_2605', {}).get('pnl', 0)

print(f"\n{'='*130}")
print(f"  FINAL RESULTS: H5(DTP=1.0R, BE=off) combined with noise gate")
print(f"  REF_OFF: 2505=${ref_off_25:,.0f}, 2605=${ref_off_26:,.0f}")
print(f"  REF_LOOSE: 2505=${ref_loose_25:,.0f}, 2605=${ref_loose_26:,.0f}")
print(f"{'='*130}")
print(f"\n{'Variant':<42} {'2505 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'Net':>10} | vsOFF  | vsLOOSE")
print('-' * 135)

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        net = r25['pnl'] + r26['pnl']
        d_off = (r25['pnl'] - ref_off_25) + (r26['pnl'] - ref_off_26)
        d_loose = (r25['pnl'] - ref_loose_25) + (r26['pnl'] - ref_loose_26)
        mark = ''
        if r26['pnl'] > 0: mark += ' [2605+]'
        if r25['pnl'] >= ref_off_25 * 0.80: mark += ' [2505=]'
        print(f"{vlabel:<42} {r25['count']:>5} {r25['daily']:>4.1f} {r25['pf']:>5.2f} "
              f"${r25['pnl']:>+9.2f} | {r26['count']:>5} {r26['daily']:>4.1f} {r26['pf']:>5.2f} "
              f"${r26['pnl']:>+9.2f} | ${net:>+9,.0f} | ${d_off:>+6,.0f} | ${d_loose:>+7,.0f}{mark}")

# Achieved goal?
print(f"\n{'='*70}")
print(f"  GOAL CHECK: 2505不退化 & 2605盈利")
print(f"{'='*70}")
for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {}).get('pnl', -99999)
    r26 = results.get(f'{vkey}_2605', {}).get('pnl', -99999)
    goal_25 = r25 >= ref_off_25 * 0.85  # within 15% of OFF baseline
    goal_26 = r26 > 0
    status = []
    if goal_25: status.append('2505不退')
    if goal_26: status.append('2605盈利')
    if goal_25 and goal_26: status.append('★★★ 双目标达成!')
    print(f"  {vlabel:<50} 2505=${r25:>+9,.0f}  2605=${r26:>+9.2f}  {' '.join(status)}")

print(f"\n[DONE]")
