#!/usr/bin/env python3
"""TDD Tracer Bullet: Verify ATR regime detection.
Test: ATR low-vol detection reduces MaxPosMult + DTP in 2605, spares 2505."""
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

# P1 base: H5+AD-LOOSE with SL=0.4
P1_BASE = {
    **NOISE_BASE,
    'InpSLBufferATR': '0.4',
    'InpMaxPosMult': '2.0',
    'InpTickNoiseGateLookback': '10',
    'InpTickNoiseGateMinDirRatio': '0.20',
    'InpTickNoiseGateMaxRangeATR': '0.25',
    'InpAdaptiveNoiseDrawdownPct': '3.0',
    'InpAdaptiveNoiseDefMinDirRatio': '0.30',
    'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
    'InpAdaptiveNoiseRecoveryPct': '1.0',
    'InpDTPTriggerR': '1.0', 'InpDTPRetrace': '0.20',
    'InpDTPPartialPct': '50',
    'InpBreakevenR': '0.0', 'InpBreakevenLockR': '0.0',
}

VARIANTS = [
    # REF: baseline without ATR regime
    ('REF', 'REF-noATR(基准)', {}),

    # ATR regime: MaxPosMult reduction only
    ('A1', 'ATR-LowVol(MaxPosMult=0.8)', {
        'InpATRRegimePeriod': '100',
        'InpATRRegimeLowThreshold': '0.7',
        'InpATRRegimeLowMaxPosMult': '0.8',
        'InpATRRegimeLowDTPTriggerR': '0.0',
    }),
    ('A2', 'ATR-LowVol(MaxPosMult=0.5)', {
        'InpATRRegimePeriod': '100',
        'InpATRRegimeLowThreshold': '0.7',
        'InpATRRegimeLowMaxPosMult': '0.5',
        'InpATRRegimeLowDTPTriggerR': '0.0',
    }),

    # ATR regime: DTP trigger reduction
    ('A3', 'ATR-LowVol(DTP=0.75)', {
        'InpATRRegimePeriod': '100',
        'InpATRRegimeLowThreshold': '0.7',
        'InpATRRegimeLowMaxPosMult': '1.0',
        'InpATRRegimeLowDTPTriggerR': '0.75',
    }),
    ('A4', 'ATR-LowVol(DTP=0.5)', {
        'InpATRRegimePeriod': '100',
        'InpATRRegimeLowThreshold': '0.7',
        'InpATRRegimeLowMaxPosMult': '1.0',
        'InpATRRegimeLowDTPTriggerR': '0.5',
    }),

    # Combined: MaxPosMult + DTP
    ('A5', 'ATR-LowVol(Max0.8+DTP0.75)', {
        'InpATRRegimePeriod': '100',
        'InpATRRegimeLowThreshold': '0.7',
        'InpATRRegimeLowMaxPosMult': '0.8',
        'InpATRRegimeLowDTPTriggerR': '0.75',
    }),
    ('A6', 'ATR-LowVol(Max0.5+DTP0.75)', {
        'InpATRRegimePeriod': '100',
        'InpATRRegimeLowThreshold': '0.7',
        'InpATRRegimeLowMaxPosMult': '0.5',
        'InpATRRegimeLowDTPTriggerR': '0.75',
    }),

    # Different threshold sensitivity
    ('A7', 'ATR-LowVol(threshold=0.5+Max0.8)', {
        'InpATRRegimePeriod': '100',
        'InpATRRegimeLowThreshold': '0.5',
        'InpATRRegimeLowMaxPosMult': '0.8',
        'InpATRRegimeLowDTPTriggerR': '0.75',
    }),
]

MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]
total = len(VARIANTS) * 2
print(f"\n{'='*70}")
print(f"  ATR Regime Detection: {len(VARIANTS)}v x 2m = {total} BTs")
print(f"  Base: P1(H5+AD-LOOSE, SL=0.4)")
print(f"{'='*70}")

set_files = {}
for key, label, ov in VARIANTS:
    merged = dict(P1_BASE)
    merged.update(ov)
    set_files[key] = make_set(f'atr_{key}', merged, base='v11xau-qs3.set')

results = {}
done = 0
for vkey, vlabel, ov in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1; key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<42} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'atr_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=$ {r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:
            print('FAILED')

# Summary
ref_25 = results.get('REF_2505', {}).get('pnl', 0)
ref_26 = results.get('REF_2605', {}).get('pnl', 0)

print(f"\n{'='*110}")
print(f"  ATR REGIME RESULTS")
print(f"  REF baseline: 2505=${ref_25:,.0f}, 2605=${ref_26:,.2f}")
print(f"{'='*110}")
print(f"\n{'Variant':<42} {'2505 T':>5} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'PF':>5} {'PnL':>10} | {'Net':>10} {'d2605':>8}")
print('-' * 110)

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        net = r25['pnl'] + r26['pnl']
        d26 = r26['pnl'] - ref_26
        goal = []
        if r26['pnl'] > 0: goal.append('2605+!')
        if r25['pnl'] >= ref_25 * 0.85: goal.append('2505=')
        print(f"{vlabel:<42} {r25['count']:>5} {r25['pf']:>5.2f} ${r25['pnl']:>+9.2f} | "
              f"{r26['count']:>5} {r26['pf']:>5.2f} ${r26['pnl']:>+9.2f} | "
              f"${net:>+9,.0f} {d26:>+8.2f} {' '.join(goal)}")

print(f"\n[DONE]")
