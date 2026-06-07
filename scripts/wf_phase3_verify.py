#!/usr/bin/env python3
"""Phase 3: Verify P0/P1 hypotheses with backtests."""
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5'}
H5 = {'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0'}

S2 = {**NOISE, 'InpEnableMTF':'false', 'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    **H5}

SWP = {**S2, 'InpEnableLiquiditySweep':'true', 'InpEnableStateFilter':'true'}

# Base PathB
PATH_B = {**SWP,
    'InpEnableDoubleSweepConfirm':'true',
    'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true',
}

# P0 H2: Block sweep OB entries after double-sweep confirmed
H2_BLOCK = {**PATH_B, 'InpDoubleSweepBlockSweepEntry':'true'}

# P0 H3: decay=0.7 + PathB
H3_DECAY7 = {**PATH_B, 'InpAdaptiveNoiseDefBoostMult':'0.7'}

# P0 H2+H3 combined: block SWP + decay 0.7
H2H3 = {**PATH_B, 'InpDoubleSweepBlockSweepEntry':'true', 'InpAdaptiveNoiseDefBoostMult':'0.7'}

# P1 H1: decay SWP signal multiplier in defensive
# (no code change needed - reuse existing InpSweepPosMult with defensive check)
# Tested via decay already

# P2 H4: window 15 bars
H4_W15 = {**PATH_B, 'InpDoubleSweepWindowBars':'15'}

VARIANTS = [
    ('S2','S2原版',S2,{}),
    ('B','PathB(REF)',PATH_B,{}),
    ('H2','H2_BlockSWP',H2_BLOCK,{}),
    ('H3','H3_decay0.7',H3_DECAY7,{}),
    ('H23','H2+H3_combo',H2H3,{}),
    ('H4','H4_window15',H4_W15,{}),
]

# P0: only test 2605 for fast hypothesis validation
# P1: add 2505 for cross-validation
results={}
for month,mfrom,mto in [('2605','2026.05.01','2026.05.31'),
                          ('2505','2025.05.01','2025.05.31')]:
    print(f'\n=== {month} ===')
    for vkey,vlabel,base,ov in VARIANTS:
        m = dict(base); m.update(ov)
        sn = make_set(f'ph3_{vkey}', m, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'ph3_{vkey}_{month}', sn, mfrom, mto)
        results[f'{vkey}_{month}']=r
        if r: print(f'  {vlabel:<20}: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+10.2f}')
        else: print(f'  {vlabel}: FAILED')

# Summary
ref_s2_25 = results.get('S2_2505',{}).get('pnl',0)
ref_s2_26 = results.get('S2_2605',{}).get('pnl',0)
ref_b_26 = results.get('B_2605',{}).get('pnl',0)
ref_b_25 = results.get('B_2505',{}).get('pnl',0)

print(f'\n{"="*80}')
print(f'  Phase 3: 假说验证结果')
print(f'  S2基线: 2605=${ref_s2_26:.2f}  2505=${ref_s2_25:,.0f}')
print(f'  PathB:  2605=${ref_b_26:.2f}  2505=${ref_b_25:,.0f}')
print(f'{"="*80}')
print(f'  {"假说":<20} | {"2605":>18} | {"2505":>18} | 结论')
print(f'  {"-"*20}-+-{"-"*18}-+-{"-"*18}-+------')

for vkey,vlabel,_,_ in VARIANTS:
    r26=results.get(f'{vkey}_2605',{}); r25=results.get(f'{vkey}_2505',{})
    if not r26: continue
    s26 = f'{r26["count"]:>3}T ${r26["pnl"]:>+8.2f}'
    s25 = f'{r25["count"]:>4}T ${r25.get("pnl",0):>+10,.0f}' if r25 else 'N/A'
    # Evaluate
    verdict = ''
    if vkey != 'S2' and vkey != 'B':
        d26 = r26['pnl'] - ref_b_26
        d25 = r25.get('pnl',0) - ref_b_25 if r25 else 0
        if d26 > 0: verdict += '2605✅'
        else: verdict += '2605❌'
        if r25 and d25 < 0 and abs(d25) > abs(ref_b_25) * 0.05:
            verdict += ' 2505⚠️'
        elif r25 and d25 >= 0:
            verdict += ' 2505✅'
        else:
            verdict += ' 2505-'
    print(f'  {vlabel:<20} | {s26:>18} | {s25:>18} | {verdict}')

# Find best for 2605
best_26 = min([(vkey,vlabel) for vkey,vlabel,_,_ in VARIANTS if vkey != 'S2'],
    key=lambda x: results.get(f'{x[0]}_2605',{}).get('pnl',999))
best_r = results.get(f'{best_26[0]}_2605',{})
print(f'\n  最佳2605: {best_26[1]} ({best_r.get("count",0)}T, ${best_r.get("pnl",0):+.2f})')
if best_r.get('pnl',0) > 0:
    print(f'  ✅✅✅ 2605转盈达成! ✅✅✅')

print('\n[DONE]')
