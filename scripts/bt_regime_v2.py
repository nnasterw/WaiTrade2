#!/usr/bin/env python3
"""Regime-Adaptive v2: 双重门控(体制检测+防守态)."""
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
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0', **H5}
SWP = {**S2, 'InpEnableLiquiditySweep':'true', 'InpEnableStateFilter':'true'}

BEST = {**SWP, 'InpEnableDoubleSweepConfirm':'true','InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true','InpAdaptiveNoiseDefBoostMult':'0.7'}

# v2: 双重门控 — RegimePos仅在双扫+防守态时生效
RPV2  = {**BEST, 'InpDoubleSweepRegimePosMult':'0.6'}  # 代码已加IsAdaptiveNoiseGateDefensive门控
RDV2  = {**BEST, 'InpDoubleSweepDTPTriggerR':'0.5'}     # 代码已加IsAdaptiveNoiseGateDefensive门控
RDPV2 = {**BEST, 'InpDoubleSweepRegimePosMult':'0.6', 'InpDoubleSweepDTPTriggerR':'0.5'}

results={}
for month,mfrom,mto in [('2605','2026.05.01','2026.05.31'),
                          ('2505','2025.05.01','2025.05.31')]:
    print(f'\n=== {month} ===')
    for vkey,vlabel,cfg in [('S2','S2基线',S2),('REF','BEST',BEST),
        ('RP2','RegimePos0.6(双重门控)',RPV2),
        ('RD2','RegimeDTP0.5(双重门控)',RDV2),
        ('RA2','RegimeBoth(双重门控)',RDPV2)]:
        sn = make_set(f'rv2_{vkey}', cfg, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'rv2_{vkey}_{month}', sn, mfrom, mto)
        results[f'{vkey}_{month}']=r
        if r: print(f'  {vlabel:<25}: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+10.2f}')
        else: print(f'  {vlabel}: FAILED')

ref26=results.get('REF_2605',{}).get('pnl',0); ref25=results.get('REF_2505',{}).get('pnl',0)
print(f'\n{"="*75}')
print(f'  体制自适应 v2: 双重门控(双扫活跃 AND 防守态)')
print(f'  BEST基线: 2605=${ref26:.2f}  2505=${ref25:,.0f}')
print(f'{"="*75}')
for vkey,vlabel in [('RP2','RegimePos0.6'),('RD2','RegimeDTP0.5'),('RA2','RegimeBoth')]:
    r26=results.get(f'{vkey}_2605',{}); r25=results.get(f'{vkey}_2505',{})
    if not r26: continue
    d26=r26['pnl']-ref26; d25=r25.get('pnl',0)-ref25
    ok26='✅' if d26>0 else '❌'; ok25='✅' if d25>=0 else '⚠️'
    print(f'  {vlabel}: 2605=${r26["pnl"]:+.2f}({d26:+.2f}){ok26} | 2505=${r25.get("pnl",0):+,.0f}({d25:+,.0f}){ok25}')
    if r26['pnl']>0: print(f'  ✅✅✅ 2605转盈!')
print('DONE')
