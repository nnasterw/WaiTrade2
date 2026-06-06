#!/usr/bin/env python3
"""Verify Mitigation Entry: S2 baseline vs S2+Mitigation on 2605+2505."""
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5'}

H5_EXIT = {'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0'}

# S2 baseline: H5+AD-LOOSE (no sweep, no mitigation)
S2_ORIG = {**NOISE, 'InpEnableMTF':'false',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    **H5_EXIT}

# S2+sweep: 启用扫荡OB作为mitigation测试基准(公平对比)
S2_SWP = {**S2_ORIG, 'InpEnableLiquiditySweep':'true', 'InpEnableStateFilter':'true'}

# Mitigation enabled + state filter (needed for OnlyRange check)
MIT_ENABLE = {
    'InpEnableMitigationEntry':'true',
    'InpMitigationEntryMaxBars':'10',
    'InpMitigationEntryOnlyRange':'false',   # 先不限制震荡市,验证代码功能
    'InpMitigationEntrySignalTypes':'sweep',
    'InpEnableStateFilter':'true',
    'InpEnableLiquiditySweep':'true',
    'InpEnableEntryDebug':'true',   # 打印Mitigation诊断日志
}

VARIANTS = [
    ('S2','S2_原版(H5+AD)',S2_ORIG,{}),
    ('SWP','S2+SWP(扫荡基准)',S2_SWP,{}),
    ('MIT','S2+SWP+Mitigation',S2_SWP,MIT_ENABLE),
    # No OnlyRange restriction: mitigation for ALL sweep OBs regardless of market state
    ('MNR','S2+SWP+MitNoRange',S2_SWP,{**MIT_ENABLE,'InpMitigationEntryOnlyRange':'false'}),
    # Mitigation for ALL OB types
    ('MAL','S2+SWP+MitAll',S2_SWP,{**MIT_ENABLE,'InpMitigationEntrySignalTypes':'all','InpMitigationEntryOnlyRange':'false'}),
    # Short return window
    ('M05','S2+SWP+Mit5b',S2_SWP,{**MIT_ENABLE,'InpMitigationEntryMaxBars':'5','InpMitigationEntryOnlyRange':'false'}),
]

MONTHS = [('2605','2026.05.01','2026.05.31'),
           ('2505','2025.05.01','2025.05.31'),
           ('2604','2026.04.01','2026.04.30')]

total = len(VARIANTS)*len(MONTHS)
print(f'Mitigation Entry Verification: {len(VARIANTS)}v x {len(MONTHS)}m = {total} BTs')
done=0
results={}

for vkey,vlabel,base,ov in VARIANTS:
    m = dict(base); m.update(ov)
    sn = make_set(f'mit_{vkey}', m, base='v11xau-qs3.set')
    for mkey,mfrom,mto in MONTHS:
        done+=1; key=f'{vkey}_{mkey}'
        print(f'[{done:>3}/{total}] {vlabel:<35} {mkey} ',end='',flush=True)
        kill_mt5()
        r=run_bt_silent(f'mit_{vkey}_{mkey}', sn, mfrom, mto)
        results[key]=r
        if r: print(f'{r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+9.2f}')
        else: print('FAILED')

print(f"\n{'='*100}")
print(f"  MITIGATION ENTRY VERIFICATION")
ref_s2_26 = results.get('S2_2605',{}).get('pnl',0)
ref_s2_25 = results.get('S2_2505',{}).get('pnl',0)
ref_swp_26 = results.get('SWP_2605',{}).get('pnl',0)
ref_swp_25 = results.get('SWP_2505',{}).get('pnl',0)
print(f"  S2 原版: 2505=${ref_s2_25:,.0f}  2605=${ref_s2_26:,.2f}")
print(f"  SWP基准: 2505=${ref_swp_25:,.0f}  2605=${ref_swp_26:,.2f}")
print(f"{'='*100}")

for month in ['2505','2605','2604']:
    print(f"\n--- {month} ---")
    print(f"  {'Config':<30} {'T':>4} {'WR':>5} {'PF':>5} {'PnL':>10} | vsSWP | vs原版")
    for vkey,vlabel,_,_ in VARIANTS:
        r=results.get(f'{vkey}_{month}',{})
        if r:
            d_swp = r['pnl']-ref_swp_26 if month=='2605' else (r['pnl']-ref_swp_25 if month=='2505' else 0)
            d_orig = r['pnl']-ref_s2_26 if month=='2605' else (r['pnl']-ref_s2_25 if month=='2505' else 0)
            flag = ''
            if month=='2605' and r['pnl']>ref_swp_26: flag=f' +{d_swp:+.2f}'
            if month=='2605' and r['pnl']>0: flag+=' ✅'
            if month=='2505' and d_swp<0 and ref_swp_25>0 and abs(d_swp)>abs(ref_swp_25)*0.05: flag+=' ⚠️'
            print(f"  {vlabel:<30} {r['count']:>4} {r['wr']:>4.1f}% {r['pf']:>4.2f} ${r['pnl']:>+9.2f}{flag}")

print(f"\n[DONE]")
