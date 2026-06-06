#!/usr/bin/env python3
"""TDD: Test MTF/HTF trend alignment filter.
H8: Blocking counter-trend entries helps 2605 (ranging) without hurting 2505 (trending)."""
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

# P1 base with MTF enabled instead of disabled
P1_MTF_BASE = {
    **{k:v for k,v in NOISE_BASE.items() if k != 'InpEnableMTF'},
    'InpEnableMTF': 'true',  # Enable MTF context
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
    # Baseline: P1 without HTF (current best)
    ('REF', 'REF-P1(MTF=off, 基准)', {**P1_MTF_BASE, 'InpEnableMTF': 'false'}),

    # MTF: block counter-trend (CounterMult=0)
    ('M1', 'MTF-CounterBlock(M15,Aligned=1,Neutral=1)', {
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '15',
        'InpHTFNetPushBars': '4',
        'InpHTFNetPushMinATR': '0.50',
        'InpHTFNetPushAlignedMult': '1.0',
        'InpHTFNetPushNeutralMult': '1.0',
        'InpHTFNetPushCounterMult': '0.0',  # BLOCK counter-trend
    }),

    # MTF: reduce counter-trend (CounterMult=0.5)
    ('M2', 'MTF-CounterHalf(M15,Aligned=1,Neutral=1,Counter=0.5)', {
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '15',
        'InpHTFNetPushBars': '4',
        'InpHTFNetPushMinATR': '0.50',
        'InpHTFNetPushAlignedMult': '1.0',
        'InpHTFNetPushNeutralMult': '1.0',
        'InpHTFNetPushCounterMult': '0.5',
    }),

    # MTF: XAU Trend style (Aligned=1.2, Neutral=0.45, Counter=0)
    ('M3', 'MTF-XAUTrend(Aligned=1.2,Neutral=0.45,Counter=0)', {
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '60',  # H1
        'InpHTFNetPushBars': '3',
        'InpHTFNetPushMinATR': '0.45',
        'InpHTFNetPushAlignedMult': '1.20',
        'InpHTFNetPushNeutralMult': '0.45',
        'InpHTFNetPushCounterMult': '0.0',
    }),

    # MTF: H1 alignment only (stronger filter)
    ('M4', 'MTF-H1(Aligned=1,Neutral=0.5,Counter=0)', {
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '60',
        'InpHTFNetPushBars': '3',
        'InpHTFNetPushMinATR': '0.40',
        'InpHTFNetPushAlignedMult': '1.0',
        'InpHTFNetPushNeutralMult': '0.5',
        'InpHTFNetPushCounterMult': '0.0',
    }),
]

MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]
total = len(VARIANTS) * 2
print(f"\n{'='*70}")
print(f"  MTF/HTF Trend Filter: {len(VARIANTS)}v x 2m = {total} BTs")
print(f"{'='*70}")

set_files = {}
for key, label, ov in VARIANTS:
    merged = dict(P1_MTF_BASE)
    merged.update(ov)
    set_files[key] = make_set(f'mtf_{key}', merged, base='v11xau-qs3.set')

results = {}
done = 0
for vkey, vlabel, ov in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1; key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<48} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'mtf_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=$ {r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:
            print('FAILED')

ref_25 = results.get('REF_2505', {}).get('pnl', 0)
ref_26 = results.get('REF_2605', {}).get('pnl', 0)

print(f"\n{'='*110}")
print(f"  MTF/HTF TREND FILTER RESULTS")
print(f"  REF: 2505=${ref_25:,.0f}({results.get('REF_2505',{}).get('count','?')}T)")
print(f"       2605=${ref_26:,.2f}({results.get('REF_2605',{}).get('count','?')}T)")
print(f"{'='*110}")

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        net = r25['pnl'] + r26['pnl']
        d25 = r25['pnl'] - ref_25
        d26 = r26['pnl'] - ref_26
        goal = []
        if r26['pnl'] > 0: goal.append('2605+!')
        if r25['pnl'] >= ref_25 * 0.80: goal.append('2505=')
        print(f"{vlabel:<48} {r25['count']:>5} {r25['pf']:>5.2f} ${r25['pnl']:>+9.2f} | "
              f"{r26['count']:>5} {r26['pf']:>5.2f} ${r26['pnl']:>+9.2f} | "
              f"${net:>+9,.0f} d25={d25:+.0f} d26={d26:+.2f} {' '.join(goal)}")

print(f"\n[DONE]")
