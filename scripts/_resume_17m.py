#!/usr/bin/env python3
"""Resume 17-month validation from save point."""
import sys, calendar, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
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
RA2 = {**SWP, 'InpEnableDoubleSweepConfirm':'true','InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true', 'InpAdaptiveNoiseDefBoostMult':'0.7',
    'InpDoubleSweepRegimePosMult':'0.6', 'InpDoubleSweepDTPTriggerR':'0.5'}

CONFIGS = [('S2','S2',S2), ('RA2','RegimeBoth',RA2)]
MONTHS = []
for y, start_m, end_m in [(2025,1,13), (2026,1,6)]:
    for m in range(start_m, end_m):
        last_day = calendar.monthrange(y, m)[1]
        MONTHS.append((f'{y%100:02d}{m:02d}', f'{y}.{m:02d}.01', f'{y}.{m:02d}.{last_day}'))

SAVE_PATH = Path('temp/17m_results.json')
results = json.loads(SAVE_PATH.read_text()) if SAVE_PATH.exists() else {}
print(f'Loaded {len(results)} existing results')

set_names = {}
for ckey, clabel, cfg in CONFIGS:
    sn = make_set(f'17m_{ckey}', cfg, base='v11xau-qs3.set')
    set_names[ckey] = sn

total = len(CONFIGS) * len(MONTHS)
done = 0
for mkey, mfrom, mto in MONTHS:
    for ckey, clabel, cfg in CONFIGS:
        key = f'{ckey}_{mkey}'
        if key in results:
            done += 1; continue
        print(f'[{done+1}/{total}] {clabel:<12} {mkey} ', end='', flush=True)
        kill_mt5(); time.sleep(3)
        r = run_bt_silent(f'17m_{ckey}_{mkey}', set_names[ckey], mfrom, mto)
        if r:
            results[key] = {'count':r['count'],'wr':r['wr'],'pf':r['pf'],'pnl':r['pnl']}
            print(f'{r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+9.2f}')
        else:
            results[key] = None; print('FAILED')
        done += 1
        if done % 5 == 0:
            SAVE_PATH.write_text(json.dumps(results))

SAVE_PATH.write_text(json.dumps(results))
print(f'\nSaved {len(results)} results')
print('DONE')
