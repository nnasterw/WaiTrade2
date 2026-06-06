#!/usr/bin/env python3
"""Round 8 Final: MTF CounterHalf + Adaptive noise gate.
Best trade-off found: M2 preserves 2505 (-19%) while helping 2605 (+$42)."""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE_BASE = {
    'InpEnableTickNoiseGate': 'true',
    'InpEnableDynamicSpread': 'true',
    'InpMinSLSpreadMult': '5.0',
    'InpOBTouchConfirmTicks': '5',
}

P1_BASE = {
    **NOISE_BASE,
    'InpEnableMTF': 'true',
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

# M2 MTF: M15 CounterHalf
MTF_M2 = {
    'InpEnableHTFNetPushFilter': 'true',
    'InpHTFNetPushTF': '15',
    'InpHTFNetPushBars': '4',
    'InpHTFNetPushMinATR': '0.50',
    'InpHTFNetPushAlignedMult': '1.0',
    'InpHTFNetPushNeutralMult': '1.0',
    'InpHTFNetPushCounterMult': '0.5',
}

VARIANTS = [
    # Baselines
    ('R1', 'REF-P1(noMTF,基准)', {
        **{k:v for k,v in P1_BASE.items() if k != 'InpEnableMTF'},
        'InpEnableMTF': 'false',
    }),
    ('R2', 'M2-only(CounterHalf=0.5,无自适应)', {
        **P1_BASE, **MTF_M2,
        'InpAdaptiveNoiseDrawdownPct': '0.0',  # disable adaptive
    }),

    # Combined: MTF + Adaptive
    ('F1', 'MTF-M2+AD(dd3%)', {
        **P1_BASE, **MTF_M2,
    }),
    # MTF + Adaptive with tighter defense
    ('F2', 'MTF-M2+AD(dd2%)', {
        **P1_BASE, **MTF_M2,
        'InpAdaptiveNoiseDrawdownPct': '2.0',
    }),
    # Also: MTF CounterBlock + Adaptive
    ('F3', 'MTF-CounterBlock+AD(dd3%)', {
        **P1_BASE,
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '15',
        'InpHTFNetPushBars': '4',
        'InpHTFNetPushMinATR': '0.50',
        'InpHTFNetPushAlignedMult': '1.0',
        'InpHTFNetPushNeutralMult': '1.0',
        'InpHTFNetPushCounterMult': '0.0',
    }),
]

MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]
total = len(VARIANTS) * 2
print(f"\n{'='*70}")
print(f"  Round 8 Final: MTF + Adaptive Combo, {len(VARIANTS)}v x 2m = {total} BTs")
print(f"{'='*70}")

set_files = {}
for key, label, ov in VARIANTS:
    merged = dict(P1_BASE)
    merged.update(ov)
    set_files[key] = make_set(f'v8_{key}', merged, base='v11xau-qs3.set')

results = {}
done = 0
for vkey, vlabel, ov in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1; key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<42} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'v8_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=$ {r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:
            print('FAILED')

r1_25 = results.get('R1_2505', {}).get('pnl', 0)
r1_26 = results.get('R1_2605', {}).get('pnl', 0)

print(f"\n{'='*110}")
print(f"  ROUND 8 FINAL: MTF + Adaptive")
print(f"  R1(基准): 2505=${r1_25:,.0f}, 2605=${r1_26:,.2f}")
print(f"{'='*110}")

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        net = r25['pnl'] + r26['pnl']
        d25 = r25['pnl'] - r1_25
        d26 = r26['pnl'] - r1_26
        goal = []
        if r26['pnl'] > 0: goal.append('2605+')
        if r25['pnl'] >= r1_25 * 0.80: goal.append('2505=')
        print(f"{vlabel:<42} {r25['count']:>5} {r25['pf']:>5.2f} ${r25['pnl']:>+9.2f} | "
              f"{r26['count']:>5} {r26['pf']:>5.2f} ${r26['pnl']:>+9.2f} | "
              f"${net:>+9,.0f} d25={d25:+.0f} d26={d26:+.2f} {' '.join(goal)}")

print(f"\n[DONE]")
