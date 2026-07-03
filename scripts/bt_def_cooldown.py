#!/usr/bin/env python3
"""Test defensive cooldown: when adaptive triggers, impose LONG cooldown (20-30 bars).
Only active in bad months (2605). Good months (2505) unaffected."""
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
    ('REF', 'REF-noDefCooldown(基准)', {}),

    # Defensive cooldown: long pause when in defensive mode
    ('D1', 'DefCd20(dd3%→20bar冷卻)', {'InpAdaptiveNoiseDefCooldownBars': '20'}),
    ('D2', 'DefCd30(dd3%→30bar冷卻)', {'InpAdaptiveNoiseDefCooldownBars': '30'}),
    ('D3', 'DefCd15(dd3%→15bar冷卻)', {'InpAdaptiveNoiseDefCooldownBars': '15'}),
    ('D4', 'DefCd40(dd3%→40bar冷卻)', {'InpAdaptiveNoiseDefCooldownBars': '40'}),
]

MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]
total = len(VARIANTS) * 2
print(f"\n{'='*70}")
print(f"  Defensive Cooldown: {len(VARIANTS)}v x 2m = {total} BTs")
print(f"{'='*70}")

set_files = {}
for key, label, ov in VARIANTS:
    merged = dict(P1_BASE)
    merged.update(ov)
    set_files[key] = make_set(f'dcd_{key}', merged, base='v11xau-qs3.set')

results = {}
done = 0
for vkey, vlabel, ov in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1; key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<42} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'dcd_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=$ {r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:
            print('FAILED')

ref_25 = results.get('REF_2505', {}).get('pnl', 0)
ref_26 = results.get('REF_2605', {}).get('pnl', 0)

print(f"\n{'='*100}")
print(f"  DEFENSIVE COOLDOWN RESULTS")
print(f"  REF: 2505=${ref_25:,.0f}, 2605=${ref_26:,.2f}")
print(f"{'='*100}")

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
              f"${net:>+9,.0f} {d26:>+7.2f} {' '.join(goal)}")

print(f"\n[DONE]")
