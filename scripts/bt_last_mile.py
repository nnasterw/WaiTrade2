#!/usr/bin/env python3
"""Last mile: H5+AD-LOOSE with faster trigger & tighter defensive.
Target: push 2605 from -$42 to profit while keeping 2505>$4K."""
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

# H5 exit: DTP=1.0R, BE=off (proven best)
H5_EXIT = {
    'InpDTPTriggerR': '1.0', 'InpDTPRetrace': '0.20',
    'InpDTPPartialPct': '50',
    'InpBreakevenR': '0.0', 'InpBreakevenLockR': '0.0',
}

# LOOSE normal base
LOOSE_BASE = {
    **NOISE_BASE, **SL5_M2, **H5_EXIT,
    'InpTickNoiseGateLookback': '10',
    'InpTickNoiseGateMinDirRatio': '0.20',
    'InpTickNoiseGateMaxRangeATR': '0.25',
    'InpAdaptiveNoiseRecoveryPct': '1.0',
}

VARIANTS = [
    # Baseline: H5+AD-LOOSE dd3% (best so far)
    ('REF', 'REF-H5+AD-LO(dd3% a25->a16)', {
        **LOOSE_BASE,
        'InpAdaptiveNoiseDrawdownPct': '3.0',
        'InpAdaptiveNoiseDefMinDirRatio': '0.30',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
    }),

    # Faster trigger
    ('L1', 'H5+AD-LO(dd2% a25->a16)', {
        **LOOSE_BASE,
        'InpAdaptiveNoiseDrawdownPct': '2.0',
        'InpAdaptiveNoiseDefMinDirRatio': '0.30',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
    }),
    ('L2', 'H5+AD-LO(dd1.5% a25->a16)', {
        **LOOSE_BASE,
        'InpAdaptiveNoiseDrawdownPct': '1.5',
        'InpAdaptiveNoiseDefMinDirRatio': '0.30',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
    }),

    # Stricter defensive
    ('L3', 'H5+AD-LO(dd2% a25->a14)', {
        **LOOSE_BASE,
        'InpAdaptiveNoiseDrawdownPct': '2.0',
        'InpAdaptiveNoiseDefMinDirRatio': '0.30',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.14',
    }),
    ('L4', 'H5+AD-LO(dd1.5% a25->a14)', {
        **LOOSE_BASE,
        'InpAdaptiveNoiseDrawdownPct': '1.5',
        'InpAdaptiveNoiseDefMinDirRatio': '0.30',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.14',
    }),

    # With tighter direction ratio too
    ('L5', 'H5+AD-LO(dd2% a25->a14/r35)', {
        **LOOSE_BASE,
        'InpAdaptiveNoiseDrawdownPct': '2.0',
        'InpAdaptiveNoiseDefMinDirRatio': '0.35',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.14',
    }),
]

MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]
total = len(VARIANTS) * 2
print(f"\n{'='*70}")
print(f"  LAST MILE: Push 2605 positive, keep 2505>$4K")
print(f"  {len(VARIANTS)}v x 2m = {total} BTs")
print(f"{'='*70}")

set_files = {}
for key, label, ov in VARIANTS:
    set_files[key] = make_set(f'lm_{key}', ov, base='v11xau-qs3.set')

results = {}
done = 0
for vkey, vlabel, ov in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1
        key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<42} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'lm_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=$ {r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:
            print('FAILED')

# Summary
ref_25 = results.get('REF_2505', {}).get('pnl', 0)
print(f"\n{'='*100}")
print(f"  LAST MILE RESULTS")
print(f"  REF: H5+AD-LO dd3% 2505=${ref_25:,.0f}")
print(f"{'='*100}")
print(f"\n{'Variant':<42} {'2505 T':>5} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'PF':>5} {'PnL':>10} | Net")

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        net = r25['pnl'] + r26['pnl']
        ok = ' *** 双达标!' if (r26['pnl'] > 0 and r25['pnl'] >= 3500) else ''
        ok += ' [2605+]' if r26['pnl'] > 0 else ''
        print(f"{vlabel:<42} {r25['count']:>5} {r25['pf']:>5.2f} ${r25['pnl']:>+9.2f} | "
              f"{r26['count']:>5} {r26['pf']:>5.2f} ${r26['pnl']:>+9.2f} | "
              f"${net:>+9,.0f}{ok}")

print(f"\n[DONE]")
