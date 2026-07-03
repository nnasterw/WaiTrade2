#!/usr/bin/env python3
"""Test cooldown and SL buffer variants with best H5+AD noise gate.
Hypothesis: Cooldown breaks loss clusters. Tighter SL increases position→PnL."""
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

# P1 base: H5+AD-LOOSE (best balanced config from previous)
P1_BASE = {
    **NOISE_BASE,
    'InpSLBufferATR': '0.5',
    'InpMaxPosMult': '2.0',
    'InpTickNoiseGateLookback': '10',
    'InpTickNoiseGateMinDirRatio': '0.20',
    'InpTickNoiseGateMaxRangeATR': '0.25',
    'InpAdaptiveNoiseDrawdownPct': '3.0',
    'InpAdaptiveNoiseDefMinDirRatio': '0.30',
    'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
    'InpAdaptiveNoiseRecoveryPct': '1.0',
    # H5 exits
    'InpDTPTriggerR': '1.0', 'InpDTPRetrace': '0.20',
    'InpDTPPartialPct': '50',
    'InpBreakevenR': '0.0', 'InpBreakevenLockR': '0.0',
}

VARIANTS = [
    # Baseline
    ('REF', 'REF-P1(H5+AD-LO)', {}),

    # Cooldown after every trade (global)
    ('C1', 'P1+CooldownBars=1', {'InpCooldownBars': '1'}),
    ('C2', 'P1+CooldownBars=2', {'InpCooldownBars': '2'}),
    ('C3', 'P1+CooldownBars=3', {'InpCooldownBars': '3'}),
    ('C5', 'P1+CooldownBars=5', {'InpCooldownBars': '5'}),

    # Same-OB reentry cooldown
    ('R5', 'P1+OBReentryCd=5min', {'InpOBReentryCooldownMin': '5'}),
    ('R10', 'P1+OBReentryCd=10min', {'InpOBReentryCooldownMin': '10'}),

    # Tighter SL (bigger position, bigger PnL per move)
    ('S3', 'P1+SL=0.3(tighter)', {'InpSLBufferATR': '0.3'}),
    ('S4', 'P1+SL=0.4', {'InpSLBufferATR': '0.4'}),

    # Combined: cooldown + tighter SL
    ('C2S3', 'P1+Cooldown2+SL0.3', {'InpCooldownBars': '2', 'InpSLBufferATR': '0.3'}),
]

MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]
total = len(VARIANTS) * 2
print(f"\n{'='*70}")
print(f"  Cooldown + SL buffer test: {len(VARIANTS)}v x 2m = {total} BTs")
print(f"  Base: P1(H5+AD-LOOSE dd3% a16)")
print(f"{'='*70}")

set_files = {}
for key, label, ov in VARIANTS:
    merged = dict(P1_BASE)
    merged.update(ov)
    set_files[key] = make_set(f'cd_{key}', merged, base='v11xau-qs3.set')

results = {}
done = 0
for vkey, vlabel, ov in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1
        key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<42} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'cd_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=$ {r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:
            print('FAILED')

# Summary
ref_25 = results.get('REF_2505', {}).get('pnl', 0)
ref_26 = results.get('REF_2605', {}).get('pnl', 0)
ref_t25 = results.get('REF_2505', {}).get('count', 0)
ref_t26 = results.get('REF_2605', {}).get('count', 0)

print(f"\n{'='*120}")
print(f"  COOLDOWN + SL BUFFER RESULTS")
print(f"  REF-P1: 2505=${ref_25:,.0f}({ref_t25}T), 2605=${ref_26:,.2f}({ref_t26}T)")
print(f"{'='*120}")
print(f"\n{'Variant':<42} {'2505 T':>5} {'PF':>5} {'PnL':>10} {'dT':>5} | {'2605 T':>5} {'PF':>5} {'PnL':>10} {'dT':>5} | {'Net':>10}  Goal")
print('-' * 125)

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        net = r25['pnl'] + r26['pnl']
        dt25 = r25.get('count', 0) - ref_t25
        dt26 = r26.get('count', 0) - ref_t26
        goal = []
        if r26['pnl'] > 0: goal.append('2605+')
        if r25['pnl'] >= ref_25 * 0.85: goal.append('2505=')
        print(f"{vlabel:<42} {r25['count']:>5} {r25['pf']:>5.2f} ${r25['pnl']:>+9.2f} {dt25:>+4} | "
              f"{r26['count']:>5} {r26['pf']:>5.2f} ${r26['pnl']:>+9.2f} {dt26:>+4} | "
              f"${net:>+9,.0f}  {' '.join(goal)}")

print(f"\n[DONE]")
