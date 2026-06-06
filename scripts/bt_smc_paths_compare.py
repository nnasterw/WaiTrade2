#!/usr/bin/env python3
"""SMC路径对比: A=Mitigation, B=双扫确认, A+B=组合. 防守触发."""
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

# Base params for all three SMC paths
SMC_BASE = {**SWP, 'InpAdaptiveNoiseDrawdownPct':'3.0',  # 防守触发=3%
    'InpEnableEntryDebug':'true'}

# Path A: Mitigation Entry (defensive trigger)
PATH_A = {**SMC_BASE,
    'InpEnableMitigationEntry':'true',
    'InpMitigationEntryMaxBars':'10',
    'InpMitigationEntryOnlyRange':'false',
    'InpMitigationEntryOnlyDefensive':'true',
    'InpMitigationEntrySignalTypes':'sweep',
}

# Path B: Double Sweep Confirm (defensive trigger)
PATH_B = {**SMC_BASE,
    'InpEnableDoubleSweepConfirm':'true',
    'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true',
}

# Path A+B: Combined
PATH_AB = {**SMC_BASE,
    'InpEnableMitigationEntry':'true',
    'InpMitigationEntryMaxBars':'10',
    'InpMitigationEntryOnlyRange':'false',
    'InpMitigationEntryOnlyDefensive':'true',
    'InpMitigationEntrySignalTypes':'sweep',
    'InpEnableDoubleSweepConfirm':'true',
    'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true',
}

VARIANTS = [
    ('S2','S2原版',S2,{}),
    ('SWP','SWP基准',SWP,{}),
    ('A','PathA_Mitigation',PATH_A,{}),
    ('B','PathB_DoubleSweep',PATH_B,{}),
    ('AB','PathAB_Combined',PATH_AB,{}),
    # With decay boost for max filtering
    ('ABD','PathAB+decay0.5',PATH_AB,{'InpAdaptiveNoiseDefBoostMult':'0.5'}),
]

results={}
for month,mfrom,mto in [('2605','2026.05.01','2026.05.31'),
                          ('2505','2025.05.01','2025.05.31'),
                          ('2604','2026.04.01','2026.04.30')]:
    print(f'\n=== {month} ===')
    for vkey,vlabel,base,ov in VARIANTS:
        m = dict(base); m.update(ov)
        sn = make_set(f'smc_{vkey}', m, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'smc_{vkey}_{month}', sn, mfrom, mto)
        results[f'{vkey}_{month}']=r
        if r: print(f'  {vlabel:<25}: {r["count"]:>5}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+10.2f}')
        else: print(f'  {vlabel}: FAILED')

# ── Summary ──
print(f'\n{"="*95}')
print(f'  SMC 双路径对比: A=Mitigation Entry | B=双扫确认 | A+B=组合')
print(f'  (全部使用防守触发, 仅在权益回撤>=3%时激活)')
print(f'{"="*95}')

s2_26 = results['S2_2605']['pnl']
s2_25 = results['S2_2505']['pnl']
swp_26 = results['SWP_2605']['pnl']

print(f'\n  {"策略":<25} | {"2605":>15} | {"2505":>15} | {"2604":>15}')
print(f'  {"-"*25}-+-{"-"*15}-+-{"-"*15}-+-{"-"*15}')
for vkey,vlabel,_,_ in VARIANTS:
    r26=results.get(f'{vkey}_2605',{})
    r25=results.get(f'{vkey}_2505',{})
    r24=results.get(f'{vkey}_2604',{})
    s26=f'{r26.get("count",0):>4}T ${r26.get("pnl",0):>+8.2f}' if r26 else 'N/A'
    s25=f'{r25.get("count",0):>4}T ${r25.get("pnl",0):>+10,.0f}' if r25 else 'N/A'
    s24=f'{r24.get("count",0):>4}T ${r24.get("pnl",0):>+8.2f}' if r24 else 'N/A'
    print(f'  {vlabel:<25} | {s26:>15} | {s25:>15} | {s24:>15}')

# Key metrics
rA=results.get('A_2605',{}); rB=results.get('B_2605',{}); rAB=results.get('AB_2605',{})
rA25=results.get('A_2505',{}); rB25=results.get('B_2505',{}); rAB25=results.get('AB_2505',{})

print(f'\n  ── 2605 改善分析 (vs SWP基准={swp_26:+.2f}) ──')
for label, r in [('PathA_Mitigation', rA), ('PathB_DoubleSweep', rB), ('PathAB_Combined', rAB)]:
    if r:
        delta = r['pnl']-swp_26
        pct = (r['count']-results['SWP_2605']['count'])/results['SWP_2605']['count']*100
        print(f'  {label}: ΔPnL={delta:+.2f} | ΔT={pct:+.0f}% | WR={r["wr"]:.1f}%')

print(f'\n  ── 2505 保护分析 (vs SWP基准) ──')
for label, r in [('PathA_Mitigation', rA25), ('PathB_DoubleSweep', rB25), ('PathAB_Combined', rAB25)]:
    if r:
        delta = r['pnl']-results['SWP_2505']['pnl']
        pct_delta = delta/results['SWP_2505']['pnl']*100
        print(f'  {label}: ΔPnL={delta:+,.0f} ({pct_delta:+.1f}%) | T={r["count"]}')

print('\n[DONE]')
