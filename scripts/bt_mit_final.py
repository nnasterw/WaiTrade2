#!/usr/bin/env python3
"""Final: Mitigation with OnlyDefensive=true (自适应防守触发)."""
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5'}
H5_EXIT = {'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0'}

S2 = {**NOISE, 'InpEnableMTF':'false',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    **H5_EXIT}

SWP = {**S2, 'InpEnableLiquiditySweep':'true', 'InpEnableStateFilter':'true'}

# Mitigation: 防守态触发(OnlyDefensive=true, OnlyRange=false)
MIT = {**SWP,
    'InpEnableMitigationEntry':'true',
    'InpMitigationEntryMaxBars':'10',
    'InpMitigationEntryOnlyRange':'false',     # 不用state filter
    'InpMitigationEntryOnlyDefensive':'true',  # 核心: 权益回撤>3%才启用
    'InpMitigationEntrySignalTypes':'sweep',
}

VARIANTS = [
    ('S2','S2原版',S2,{}),
    ('SWP','S2+SWP',SWP,{}),
    ('DEF','S2+SWP+MitDef',SWP,MIT),
    # 同时测试: 全局decay(已验证有效) + mitigation 组合
    ('CMB','S2+SWP+MitDef+decay0.5',SWP,{**MIT,'InpAdaptiveNoiseDefBoostMult':'0.5'}),
]

results={}
for month,mfrom,mto in [('2605','2026.05.01','2026.05.31'),
                          ('2505','2025.05.01','2025.05.31'),
                          ('2604','2026.04.01','2026.04.30')]:
    print(f'\n=== {month} ===')
    for vkey,vlabel,base,ov in VARIANTS:
        m = dict(base); m.update(ov)
        sn = make_set(f'mf_{vkey}', m, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'mf_{vkey}_{month}', sn, mfrom, mto)
        if r: print(f'  {vlabel:<25}: {r["count"]:>5}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+10.2f}')
        else: print(f'  {vlabel}: FAILED')

print('\n=== 核心指标汇总 ===')
print(f'  {"策略":<25} {"2605":>12} {"2505":>12} {"2604":>12}')
for vkey,vlabel,_,_ in VARIANTS:
    r26=results.get(f'{vkey}_2605',{}); r25=results.get(f'{vkey}_2505',{}); r24=results.get(f'{vkey}_2604',{})
    s26=f'${r26.get("pnl",0):+.2f}' if r26 else 'N/A'
    s25=f'${r25.get("pnl",0):+.0f}' if r25 else 'N/A'
    s24=f'${r24.get("pnl",0):+.2f}' if r24 else 'N/A'
    print(f'  {vlabel:<25} {s26:>12} {s25:>12} {s24:>12}')
print('DONE')
