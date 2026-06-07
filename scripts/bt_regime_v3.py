#!/usr/bin/env python3
"""Regime-Adaptive v3: 双重门控 + 5%回撤阈值."""
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

# v3: 5% drawdown threshold (more breathing room for $200 account)
BEST5 = {**SWP, 'InpEnableDoubleSweepConfirm':'true','InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true','InpAdaptiveNoiseDefBoostMult':'0.7',
    'InpAdaptiveNoiseDrawdownPct':'5.0',  # 5% instead of 3%
}
RA5 = {**BEST5, 'InpDoubleSweepRegimePosMult':'0.6', 'InpDoubleSweepDTPTriggerR':'0.5'}

results={}
for month,mfrom,mto in [('2605','2026.05.01','2026.05.31'),
                          ('2505','2025.05.01','2025.05.31')]:
    print(f'\n=== {month} ===')
    for vkey,vlabel,cfg in [
        ('S2','S2基线',S2),
        ('REF','BEST(dd3%)',{**SWP,'InpEnableDoubleSweepConfirm':'true','InpDoubleSweepWindowBars':'20','InpDoubleSweepOnlyDefensive':'true','InpAdaptiveNoiseDefBoostMult':'0.7'}),
        ('B5','BEST(dd5%)',BEST5),
        ('RA5','RegimeBoth(dd5%)',RA5),
    ]:
        sn = make_set(f'rv3_{vkey}', cfg, base='v11xau-qs3.set')
        kill_mt5()
        r = run_bt_silent(f'rv3_{vkey}_{month}', sn, mfrom, mto)
        results[f'{vkey}_{month}']=r
        if r: print(f'  {vlabel:<20}: {r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+10.2f}')
        else: print(f'  {vlabel}: FAILED')

# Compare
ref26_3 = results.get('REF_2605',{}).get('pnl',0)
ref25_3 = results.get('REF_2505',{}).get('pnl',0)
b5_26 = results.get('B5_2605',{}).get('pnl',0)
b5_25 = results.get('B5_2505',{}).get('pnl',0)
ra5_26 = results.get('RA5_2605',{}).get('pnl',0)
ra5_25 = results.get('RA5_2505',{}).get('pnl',0)

print(f'\n{"="*70}')
print(f'  v3: 回撤阈值 3%→5%')
print(f'  BEST(dd3%): 2605=${ref26_3:.2f}  2505=${ref25_3:,.0f}')
print(f'  BEST(dd5%): 2605=${b5_26:.2f}({b5_26-ref26_3:+.2f})  2505=${b5_25:,.0f}({b5_25-ref25_3:+,.0f})')
print(f'  RegimeBoth(dd5%): 2605=${ra5_26:.2f}({ra5_26-b5_26:+.2f})  2505=${ra5_25:,.0f}({ra5_25-b5_25:+,.0f})')
if ra5_26 > 0: print(f'  ✅✅✅ 2605转盈!')
print('DONE')
