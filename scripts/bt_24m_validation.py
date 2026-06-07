#!/usr/bin/env python3
"""24-month validation: S2 vs PathB+d07 vs RegimeBoth across 2024.06-2026.05."""
import sys, calendar, json, time
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Use D: portable terminal to save C: space
import os
os.environ['MT5_HOME'] = r'D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt'

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

# Config 1: S2 baseline
# Config 2: PathB + decay0.7 (best balanced)
B_D07 = {**SWP,
    'InpEnableDoubleSweepConfirm':'true',
    'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true',
    'InpAdaptiveNoiseDefBoostMult':'0.7',
}
# Config 3: RegimeBoth dd3% (best 2605)
RA2 = {**SWP,
    'InpEnableDoubleSweepConfirm':'true',
    'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true',
    'InpAdaptiveNoiseDefBoostMult':'0.7',
    'InpDoubleSweepRegimePosMult':'0.6',
    'InpDoubleSweepDTPTriggerR':'0.5',
}

CONFIGS = [
    ('S2', 'S2基线', S2),
    ('BD7', 'PathB+d07', B_D07),
    ('RA2', 'RegimeBoth', RA2),
]

# Generate month ranges: 2024.06 through 2026.05
MONTHS = []
for y in [2024, 2025, 2026]:
    end_m = 13 if y < 2026 else 6
    for m in range(1, end_m):
        if y == 2024 and m < 6:
            continue
        last_day = calendar.monthrange(y, m)[1]
        mfrom = f'{y}.{m:02d}.01'
        mto = f'{y}.{m:02d}.{last_day}'
        MONTHS.append((f'{y%100:02d}{m:02d}', mfrom, mto))

total = len(CONFIGS) * len(MONTHS)
print(f'24-Month Validation: {len(CONFIGS)} configs × {len(MONTHS)} months = {total} BTs')
print(f'Range: {MONTHS[0][1]} ~ {MONTHS[-1][2]}')
print(f'Target: D: portable terminal ({MT5_TERMINAL})')
print()

# Create .set files once
set_names = {}
for ckey, clabel, cfg in CONFIGS:
    sn = make_set(f'24m_{ckey}', cfg, base='v11xau-qs3.set')
    set_names[ckey] = sn
print('.set files created\n')

# Progress tracking
results = {}
done = 0
t0_total = time.time()
last_save = time.time()
SAVE_PATH = Path('temp/24m_results.json')

# Load existing progress
if SAVE_PATH.exists():
    try:
        with open(SAVE_PATH) as f:
            results = json.load(f)
        print(f'Resuming: {len(results)} results loaded')
    except:
        pass

for mkey, mfrom, mto in MONTHS:
    for ckey, clabel, cfg in CONFIGS:
        key = f'{ckey}_{mkey}'
        if key in results and results[key] is not None:
            done += 1
            continue

        print(f'[{done+1:>3}/{total}] {clabel:<15} {mkey} ({mfrom}~{mto}) ', end='', flush=True)
        kill_mt5()
        t0 = time.time()
        r = run_bt_silent(f'24m_{ckey}_{mkey}', set_names[ckey], mfrom, mto)
        elapsed = time.time() - t0

        if r:
            results[key] = {'count': r['count'], 'wr': r['wr'], 'pf': r['pf'], 'pnl': r['pnl']}
            print(f'{r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+9.2f} ({elapsed:.0f}s)')
        else:
            results[key] = None
            print(f'FAILED ({elapsed:.0f}s)')

        done += 1

        # Save progress every 10 BTs or 5 minutes
        if done % 10 == 0 or time.time() - last_save > 300:
            with open(SAVE_PATH, 'w') as f:
                json.dump(results, f)
            last_save = time.time()
            elapsed_total = time.time() - t0_total
            eta = elapsed_total / done * (total - done) if done > 0 else 0
            print(f'  [Progress: {done}/{total} ({done/total*100:.0f}%) ETA: {eta/60:.0f}min]')

# Final save
with open(SAVE_PATH, 'w') as f:
    json.dump(results, f)

# ── Generate Summary Tables ──
print(f'\n\n{"="*120}')
print(f'  24-Month Validation: {len(CONFIGS)} Configs × {len(MONTHS)} Months')
print(f'{"="*120}')

# Table: Monthly PnL
header = f'  {"Month":>6} |'
for ckey, clabel, _ in CONFIGS:
    header += f' {clabel:>15} |'
print(header)
print(f'  {"-"*6}-+-{"-"*16}' + '-+-{"-"*16}' * (len(CONFIGS)-1) + '-|')

monthly_totals = {ckey: {'total_pnl': 0, 'total_trades': 0, 'profitable_months': 0, 'losing_months': 0} for ckey, _, _ in CONFIGS}
for mkey, mfrom, mto in MONTHS:
    line = f'  {mkey:>6} |'
    for ckey, clabel, _ in CONFIGS:
        r = results.get(f'{ckey}_{mkey}')
        if r:
            line += f' ${r["pnl"]:>+9.2f} {r["wr"]:>4.0f}% |'
            monthly_totals[ckey]['total_pnl'] += r['pnl']
            monthly_totals[ckey]['total_trades'] += r['count']
            if r['pnl'] > 0:
                monthly_totals[ckey]['profitable_months'] += 1
            else:
                monthly_totals[ckey]['losing_months'] += 1
        else:
            line += f' {"N/A":>15} |'
    print(line)

# Summary row
print(f'  {"-"*6}-+-{"-"*16}' + '-+-{"-"*16}' * (len(CONFIGS)-1) + '-|')
sum_line = f'  {"TOTAL":>6} |'
for ckey, clabel, _ in CONFIGS:
    t = monthly_totals[ckey]
    sum_line += f' ${t["total_pnl"]:>+9.0f} {t["total_trades"]:>4}T |'
print(sum_line)

# Stats row
stats_line = f'  {"Stats":>6} |'
for ckey, clabel, _ in CONFIGS:
    t = monthly_totals[ckey]
    m = t['profitable_months'] + t['losing_months']
    if m > 0:
        avg = t['total_pnl'] / m
        stats_line += f' 盈{t["profitable_months"]}/亏{t["losing_months"]} 月均${avg:+.0f} |'
    else:
        stats_line += f' {"N/A":>15} |'
print(stats_line)

print(f'\n{"="*120}')
print(f'  结果已保存至: {SAVE_PATH}')
print(f'  总耗时: {(time.time()-t0_total)/60:.1f} 分钟')
print(f'{"="*120}')
