#!/usr/bin/env python3
"""17-month fast validation using C: installed terminal. 3 configs × 17 months = 51 BTs."""
import sys, calendar, json, time, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Use C: drive installed terminal (faster, ~60s per BT)
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

B_D07 = {**SWP, 'InpEnableDoubleSweepConfirm':'true','InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true', 'InpAdaptiveNoiseDefBoostMult':'0.7'}
RA2 = {**SWP, 'InpEnableDoubleSweepConfirm':'true','InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true', 'InpAdaptiveNoiseDefBoostMult':'0.7',
    'InpDoubleSweepRegimePosMult':'0.6', 'InpDoubleSweepDTPTriggerR':'0.5'}

CONFIGS = [('S2','S2',S2), ('RA2','RegimeBoth',RA2)]  # BD7 removed: .set loading issue

# Key months: Full 2025 + 2026 Q1-Q2
MONTHS = []
for y, start_m, end_m in [(2025,1,13), (2026,1,6)]:  # 2025 full, 2026 Jan-May
    for m in range(start_m, end_m):
        last_day = calendar.monthrange(y, m)[1]
        MONTHS.append((f'{y%100:02d}{m:02d}', f'{y}.{m:02d}.01', f'{y}.{m:02d}.{last_day}'))

total = len(CONFIGS) * len(MONTHS)
print(f'17-Month Fast: {len(CONFIGS)}c × {len(MONTHS)}m = {total} BTs (C: terminal)')
print(f'Target: {MT5_TERMINAL}')
print(f'Range: {MONTHS[0][1]} ~ {MONTHS[-1][2]}')
print()

# Create .set files
set_names = {}
for ckey, clabel, cfg in CONFIGS:
    sn = make_set(f'17m_{ckey}', cfg, base='v11xau-qs3.set')
    set_names[ckey] = sn

results = {}
done = 0
t0_total = time.time()
SAVE_PATH = Path('temp/17m_results.json')

if SAVE_PATH.exists():
    try:
        results = json.loads(SAVE_PATH.read_text())
        print(f'Resumed: {len(results)} results\n')
    except: pass

for mkey, mfrom, mto in MONTHS:
    for ckey, clabel, cfg in CONFIGS:
        key = f'{ckey}_{mkey}'
        if key in results and results[key]:
            done += 1; continue

        print(f'[{done+1:>3}/{total}] {clabel:<12} {mkey} ', end='', flush=True)
        kill_mt5()
        t0 = time.time()
        r = run_bt_silent(f'17m_{ckey}_{mkey}', set_names[ckey], mfrom, mto)
        elapsed = time.time() - t0

        if r:
            results[key] = {'count':r['count'],'wr':r['wr'],'pf':r['pf'],'pnl':r['pnl']}
            print(f'{r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+9.2f} ({elapsed:.0f}s)')
        else:
            results[key] = None
            print(f'FAILED')

        done += 1
        if done % 10 == 0:
            SAVE_PATH.write_text(json.dumps(results))
            elapsed_total = time.time() - t0_total
            eta = elapsed_total/done*(total-done) if done else 0
            print(f'  [{done}/{total} ETA {eta/60:.0f}min]')

SAVE_PATH.write_text(json.dumps(results))

# Summary
print(f'\n{"="*110}')
header = f'  {"Month":>6} |'
for ckey, cl, _ in CONFIGS: header += f' {cl:>18} |'
print(header)
print(f'  {"-"*6}-+-{"-"*18}-+-{"-"*18}-+-{"-"*18}--|')

totals = {c: {'pnl':0,'trades':0,'win':0,'loss':0} for c,_,_ in CONFIGS}
for mkey, mfrom, mto in MONTHS:
    line = f'  {mkey:>6} |'
    for ckey, cl, _ in CONFIGS:
        r = results.get(f'{ckey}_{mkey}')
        if r:
            line += f' ${r["pnl"]:>+7.2f} {r["wr"]:>4.0f}% {r["count"]:>4}T |'
            totals[ckey]['pnl'] += r['pnl']
            totals[ckey]['trades'] += r['count']
            if r['pnl'] > 0: totals[ckey]['win'] += 1
            else: totals[ckey]['loss'] += 1
        else:
            line += f' {"N/A":>18} |'
    print(line)

print(f'  {"-"*6}-+-{"-"*18}-+-{"-"*18}-+-{"-"*18}--|')
sl = f'  {"TOTAL":>6} |'
for ckey, cl, _ in CONFIGS:
    t = totals[ckey]
    sl += f' ${t["pnl"]:>+7.0f} {t["trades"]//t["win"]+t["trades"]//(t["loss"]or 1)}T {t["win"]}/{t["loss"]}月 |'
print(sl)

print(f'\n  总耗时: {(time.time()-t0_total)/60:.1f}min  |  结果: {SAVE_PATH}')
print('DONE')
