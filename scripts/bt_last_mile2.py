#!/usr/bin/env python3
"""Last mile 2: Micro-tweaks to close the $42 gap in 2605."""
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
H5_EXIT_BASE = {
    'InpDTPTriggerR': '1.0', 'InpDTPRetrace': '0.20',
    'InpBreakevenR': '0.0', 'InpBreakevenLockR': '0.0',
}

LOOSE_BASE = {
    **NOISE_BASE, **SL5_M2,
    'InpTickNoiseGateLookback': '10',
    'InpTickNoiseGateMinDirRatio': '0.20',
    'InpTickNoiseGateMaxRangeATR': '0.25',
    'InpAdaptiveNoiseDrawdownPct': '3.0',
    'InpAdaptiveNoiseDefMinDirRatio': '0.30',
    'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
    'InpAdaptiveNoiseRecoveryPct': '1.0',
}

VARIANTS = [
    # Baseline
    ('REF', 'REF-H5+AD-LO(dd3% P50 lb10)', {**LOOSE_BASE, **H5_EXIT_BASE, 'InpDTPPartialPct': '50'}),

    # No partial close (keep full position running)
    ('M1', 'H5+AD-LO(dd3% P0=全仓)', {**LOOSE_BASE, **H5_EXIT_BASE, 'InpDTPPartialPct': '0'}),
    ('M2', 'H5+AD-LO(dd3% P25=少分仓)', {**LOOSE_BASE, **H5_EXIT_BASE, 'InpDTPPartialPct': '25'}),

    # Slightly tighter normal (lb12 instead of lb10)
    ('M3', 'H5+AD-LO(dd3% lb12)', {**LOOSE_BASE, **H5_EXIT_BASE, 'InpDTPPartialPct': '50',
        'InpTickNoiseGateLookback': '12'}),

    # Slightly tighter normal ratio (r25 instead of r20)
    ('M4', 'H5+AD-LO(dd3% lb12/r25)', {**LOOSE_BASE, **H5_EXIT_BASE, 'InpDTPPartialPct': '50',
        'InpTickNoiseGateLookback': '12', 'InpTickNoiseGateMinDirRatio': '0.25'}),
]

MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]
total = len(VARIANTS) * 2
print(f"\n{'='*70}")
print(f"  LAST MILE 2: Close the $42 gap")
print(f"  {len(VARIANTS)}v x 2m = {total} BTs")
print(f"{'='*70}")

set_files = {}
for key, label, ov in VARIANTS:
    set_files[key] = make_set(f'lm2_{key}', ov, base='v11xau-qs3.set')

results = {}
done = 0
for vkey, vlabel, ov in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1
        key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<42} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'lm2_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=$ {r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:
            print('FAILED')

# Summary
ref_25 = results.get('REF_2505', {}).get('pnl', 0)
ref_26 = results.get('REF_2605', {}).get('pnl', 0)
print(f"\n{'='*100}")
print(f"  LAST MILE 2 RESULTS")
print(f"  REF: 2505=${ref_25:,.0f}, 2605=${ref_26:,.2f}")
print(f"{'='*100}")

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        net = r25['pnl'] + r26['pnl']
        d25 = r25['pnl'] - ref_25
        d26 = r26['pnl'] - ref_26
        ok = ' *** DUAL GOAL!' if (r26['pnl'] > 0 and r25['pnl'] >= 3500) else ''
        ok += ' [2605+]' if r26['pnl'] > 0 else ''
        print(f"{vlabel:<42} {r25['count']:>5} {r25['pf']:>5.2f} ${r25['pnl']:>+9.2f} | "
              f"{r26['count']:>5} {r26['pf']:>5.2f} ${r26['pnl']:>+9.2f} | "
              f"${net:>+9,.0f} (d25={d25:+.0f} d26={d26:+.2f}){ok}")

print(f"\n[DONE]")
