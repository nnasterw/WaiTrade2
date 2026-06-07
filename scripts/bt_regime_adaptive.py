#!/usr/bin/env python3
"""Regime-Adaptive: 双扫体制检测驱动参数切换(市场结构驱动, 非结果驱动)."""
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

# Base: PathB + decay0.7 (current best)
BASE = {**SWP,
    'InpEnableDoubleSweepConfirm':'true',
    'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true',
    'InpAdaptiveNoiseDefBoostMult':'0.7',
}

# Regime-Adaptive variants
# RD: Regime DTP (0.5R when double-sweep active)
RD = {**BASE, 'InpDoubleSweepDTPTriggerR':'0.5'}
# RP: Regime Position (0.6x when double-sweep active)
RP = {**BASE, 'InpDoubleSweepRegimePosMult':'0.6'}
# RDP: Both DTP + Position
RDP = {**BASE, 'InpDoubleSweepDTPTriggerR':'0.5', 'InpDoubleSweepRegimePosMult':'0.6'}
# RD7: DTP=0.7R
RD7 = {**BASE, 'InpDoubleSweepDTPTriggerR':'0.7'}

VARIANTS = [
    ('S2','S2基线',S2,{}),
    ('REF','PathB+d07(BEST)',BASE,{}),
    ('RD','+RegimeDTP0.5',RD,{}),
    ('RP','+RegimePos0.6',RP,{}),
    ('RDP','+RegimeDTP+Pos',RDP,{}),
    ('RD7','+RegimeDTP0.7',RD7,{}),
]

results={}
for month,mfrom,mto in [('2605','2026.05.01','2026.05.31'),
                          ('2505','2025.05.01','2025.05.31'),
                          ('2604','2026.04.01','2026.04.30')]:
    print(f'\n=== {month} ===')
    for vkey,vlabel,base,ov in VARIANTS:
        m = dict(base); m.update(ov)
        sn = make_set(f'ra_{vkey}', m, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'ra_{vkey}_{month}', sn, mfrom, mto)
        results[f'{vkey}_{month}']=r
        if r: print(f'  {vlabel:<22}: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+10.2f}')
        else: print(f'  {vlabel}: FAILED')

ref_25 = results.get('REF_2505',{}).get('pnl',0)
ref_26 = results.get('REF_2605',{}).get('pnl',0)
ref_24 = results.get('REF_2604',{}).get('pnl',0)

print(f'\n{"="*85}')
print(f'  体制自适应: 双扫活跃→震荡区间参数 | 双扫不活跃→趋势参数')
print(f'  BEST基线: 2605=${ref_26:.2f}  2505=${ref_25:,.0f}  2604=${ref_24:.2f}')
print(f'{"="*85}')
print(f'  {"策略":<22} | {"2605 Δ":>15} | {"2505 Δ":>15} | {"2604 Δ":>12} | 评估')
print(f'  {"-"*22}-+-{"-"*15}-+-{"-"*15}-+-{"-"*12}-+------')

for vkey,vlabel,_,_ in VARIANTS:
    if vkey == 'S2' or vkey == 'REF': continue
    r26=results.get(f'{vkey}_2605',{}); r25=results.get(f'{vkey}_2505',{}); r24=results.get(f'{vkey}_2604',{})
    if not r26: continue
    d26=r26['pnl']-ref_26; d25=r25.get('pnl',0)-ref_25; d24=r24.get('pnl',0)-ref_24
    v26 = f'${r26["pnl"]:+.2f} ({d26:+.2f})'
    v25 = f'${r25.get("pnl",0):+,.0f} ({d25:+,.0f})' if r25 else 'ERR'
    v24 = f'${r24.get("pnl",0):+.2f} ({d24:+.2f})' if r24 else 'ERR'
    # Evaluate
    ok26 = '✅' if d26>0 else ('➖' if abs(d26)<1 else '❌')
    ok25 = '✅' if d25>=0 else '⚠️'
    ok24 = '✅' if d24>0 else ('➖' if abs(d24)<1 else '❌')
    print(f'  {vlabel:<22} | {v26:>15} {ok26}| {v25:>15} {ok25}| {v24:>12} {ok24}|')
    if r26['pnl'] > 0:
        print(f'\n  ✅✅✅ 体制自适应成功! 2605转盈! ✅✅✅')

# Show actual regime detection rate
print(f'\n  ── 体制检测分析 ──')
print(f'  双扫体制=震荡区间: DTP降低/仓位衰减')
print(f'  双扫不活跃=趋势: 保持正常参数')
print(f'  体制检测是市场结构驱动的(实时价格行为), 非结果驱动的(权益回撤)')

print('\n[DONE]')
