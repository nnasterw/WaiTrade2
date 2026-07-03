"""Phase 2: Falsifiable hypothesis — exit mechanism test.
Root cause from Phase 1: 2605 avg_W=$1.07, avg_L=$1.72, 83% SL rate.
Market doesn't move far enough to hit DTP=1.5R. Hypothesis: lowering DTP
trigger improves 2605 without proportionally harming 2505."""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

# Best static noise gate baseline
NOISE_B2 = {
    'InpEnableTickNoiseGate': 'true',
    'InpEnableDynamicSpread': 'true',
    'InpMinSLSpreadMult': '5.0',
    'InpOBTouchConfirmTicks': '5',
    'InpEnableMTF': 'false',
    'InpSLBufferATR': '0.5',
    'InpMaxPosMult': '2.0',
    'InpTickNoiseGateLookback': '20',
    'InpTickNoiseGateMinDirRatio': '0.25',
    'InpTickNoiseGateMaxRangeATR': '0.18',
}

VARIANTS = [
    # Reference: B2 baseline (best static)
    ('REF', 'REF-B2(DTP=1.5R,BE=0.5/0.4)', {
        **NOISE_B2,
        'InpDTPTriggerR': '1.5', 'InpDTPRetrace': '0.25',
        'InpDTPPartialPct': '50',
        'InpBreakevenR': '0.5', 'InpBreakevenLockR': '0.4',
    }),

    # Hypothesis test: lower DTP trigger
    ('H1', 'H1-DTP=1.0R(BE=0.5/0.4)', {
        **NOISE_B2,
        'InpDTPTriggerR': '1.0', 'InpDTPRetrace': '0.20',
        'InpDTPPartialPct': '50',
        'InpBreakevenR': '0.5', 'InpBreakevenLockR': '0.4',
    }),
    ('H2', 'H2-DTP=0.75R(BE=0.5/0.4)', {
        **NOISE_B2,
        'InpDTPTriggerR': '0.75', 'InpDTPRetrace': '0.15',
        'InpDTPPartialPct': '50',
        'InpBreakevenR': '0.5', 'InpBreakevenLockR': '0.4',
    }),

    # Hypothesis test: lower BE threshold (easier to trigger)
    ('H3', 'H3-DTP=1.5R(BE=0.3/0.2)', {
        **NOISE_B2,
        'InpDTPTriggerR': '1.5', 'InpDTPRetrace': '0.25',
        'InpDTPPartialPct': '50',
        'InpBreakevenR': '0.3', 'InpBreakevenLockR': '0.2',
    }),

    # Combined: lower both
    ('H4', 'H4-DTP=1.0R+BE=0.3/0.2', {
        **NOISE_B2,
        'InpDTPTriggerR': '1.0', 'InpDTPRetrace': '0.20',
        'InpDTPPartialPct': '50',
        'InpBreakevenR': '0.3', 'InpBreakevenLockR': '0.2',
    }),

    # Zero BE: disable BE lock to see if it hurts or helps
    ('H5', 'H5-DTP=1.0R(BE=0=off)', {
        **NOISE_B2,
        'InpDTPTriggerR': '1.0', 'InpDTPRetrace': '0.20',
        'InpDTPPartialPct': '50',
        'InpBreakevenR': '0.0', 'InpBreakevenLockR': '0.0',
    }),
]

MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]
total = len(VARIANTS) * 2
print(f"\n{'='*70}")
print(f"  Phase 2: Exit mechanism hypothesis — {len(VARIANTS)}v x 2m = {total} BTs")
print(f"  H0: DTP too far (1.5R) is root cause of 2605 losses")
print(f"{'='*70}")

set_files = {}
for key, label, ov in VARIANTS:
    set_files[key] = make_set(f'h_{key}', ov, base='v11xau-qs3.set')

results = {}
done = 0
for vkey, vlabel, ov in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1
        key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<42} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'h_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=$ {r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:
            print('FAILED')

# ===== SUMMARY =====
ref_25 = results.get('REF_2505', {}).get('pnl', 0)
ref_26 = results.get('REF_2605', {}).get('pnl', 0)

print(f"\n{'='*120}")
print(f"  PHASE 2 RESULTS: Exit mechanism hypothesis")
print(f"  REF-B2 baseline: 2505=${ref_25:,.0f}, 2605=${ref_26:,.2f}")
print(f"{'='*120}")
print(f"\n{'Variant':<42} {'2505 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'d25':>9} {'d26':>9}")
print('-' * 120)

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        d25 = r25['pnl'] - ref_25
        d26 = r26['pnl'] - ref_26
        mark = ''
        if r26['pnl'] > 0: mark += ' [2605+]'
        if r25['pnl'] >= ref_25 * 0.90: mark += ' [2505=]'
        print(f"{vlabel:<42} {r25['count']:>5} {r25['daily']:>4.1f} {r25['pf']:>5.2f} "
              f"${r25['pnl']:>+9.2f} | {r26['count']:>5} {r26['daily']:>4.1f} {r26['pf']:>5.2f} "
              f"${r26['pnl']:>+9.2f} | ${d25:>+8.0f} ${d26:>+8.2f}{mark}")

# Hypothesis verdict
print(f"\n--- Hypothesis Verdict ---")
print(f"H0: 'DTP=1.5R too far for 2605 → lowering improves 2605 PnL'")
best_26 = max([k for k in results if '2605' in k], key=lambda k: results[k]['pnl'])
best_key_26 = best_26.replace('_2605', '')
for vkey, vlabel, _ in VARIANTS:
    if vkey == best_key_26:
        print(f"  Best 2605: {vlabel} = ${results[best_26]['pnl']:+.2f}")
        if results[best_26]['pnl'] > ref_26:
            print(f"  Improvement: +${results[best_26]['pnl'] - ref_26:.2f} vs REF-B2")

print(f"\n[DONE]")
