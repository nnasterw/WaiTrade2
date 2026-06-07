#!/usr/bin/env python3
"""H5 hypothesis: defensive DTP=0.5R on PathB+decay0.7 base."""
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

# Current best: PathB + decay0.7
BEST = {**SWP,
    'InpEnableDoubleSweepConfirm':'true',
    'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true',
    'InpAdaptiveNoiseDefBoostMult':'0.7',
}

# H5: + defensive DTP=0.5R
DTP05 = {**BEST, 'InpDoubleSweepDTPTriggerR':'0.5'}
DTP07 = {**BEST, 'InpDoubleSweepDTPTriggerR':'0.7'}
DTP03 = {**BEST, 'InpDoubleSweepDTPTriggerR':'0.3'}

results={}
for month,mfrom,mto in [('2605','2026.05.01','2026.05.31'),
                          ('2505','2025.05.01','2025.05.31')]:
    print(f'\n=== {month} ===')
    for vkey,vlabel,cfg in [
        ('S2','S2基线',S2),
        ('REF','PathB+d07(BEST)',BEST),
        ('05','+DTP=0.5R',DTP05),
        ('07','+DTP=0.7R',DTP07),
        ('03','+DTP=0.3R',DTP03),
    ]:
        sn = make_set(f'h5_{vkey}', cfg, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'h5_{vkey}_{month}', sn, mfrom, mto)
        results[f'{vkey}_{month}']=r
        if r: print(f'  {vlabel:<20}: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+10.2f}')
        else: print(f'  {vlabel}: FAILED')

ref_26 = results.get('REF_2605',{}).get('pnl',0)
ref_25 = results.get('REF_2505',{}).get('pnl',0)

print(f'\n{"="*70}')
print(f'  H5: 防守态DTP降低 (PathB+decay0.7基础上)')
print(f'  REF: 2605=${ref_26:.2f}  2505=${ref_25:,.0f}')
print(f'{"="*70}')

for vkey,vlabel in [('05','DTP=0.5R'),('07','DTP=0.7R'),('03','DTP=0.3R')]:
    r26 = results.get(f'{vkey}_2605',{})
    r25 = results.get(f'{vkey}_2505',{})
    if not r26: continue
    d26 = r26['pnl']-ref_26
    d25 = r25.get('pnl',0)-ref_25 if r25 else 0
    flag26 = '✅' if d26 > 0 else '❌'
    flag25 = '✅' if d25 >= 0 else '⚠️'
    pnl_26_str = f'${r26["pnl"]:+.2f} ({d26:+.2f})'
    pnl_25_str = f'${r25.get("pnl",0):+,.0f} ({d25:+,.0f})' if r25 else 'N/A'
    print(f'  {vlabel:<10}: 2605={pnl_26_str:>20} {flag26} | 2505={pnl_25_str:>20} {flag25}')
    if r26['pnl'] > 0:
        print(f'\n  ✅✅✅ H5验证成功! 2605转盈! DTP={vlabel} ✅✅✅')

print('\n[DONE]')
