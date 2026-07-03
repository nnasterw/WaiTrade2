#!/usr/bin/env python3
"""3 top strategies × 24 months (2024.06-2026.05) = 72 BTs.
Strategies: H5+LOOSE (max profit), H5+AD-LOOSE (balanced), QS3 OFF (baseline)."""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE_BASE = {
    'InpEnableTickNoiseGate': 'true', 'InpEnableDynamicSpread': 'true',
    'InpMinSLSpreadMult': '5.0', 'InpOBTouchConfirmTicks': '5', 'InpEnableMTF': 'false',
}

# Strategy 1: H5+LOOSE — highest single-month profit
S1_H5_LOOSE = {
    **NOISE_BASE,
    'InpSLBufferATR': '0.5', 'InpMaxPosMult': '2.0',
    'InpTickNoiseGateLookback': '10', 'InpTickNoiseGateMinDirRatio': '0.20',
    'InpTickNoiseGateMaxRangeATR': '0.25',
    'InpDTPTriggerR': '1.0', 'InpDTPRetrace': '0.20', 'InpDTPPartialPct': '50',
    'InpBreakevenR': '0.0', 'InpBreakevenLockR': '0.0',
}

# Strategy 2: H5+AD-LOOSE — best balanced with adaptive
S2_H5_AD_LOOSE = {
    **NOISE_BASE,
    'InpSLBufferATR': '0.4', 'InpMaxPosMult': '2.0',
    'InpTickNoiseGateLookback': '10', 'InpTickNoiseGateMinDirRatio': '0.20',
    'InpTickNoiseGateMaxRangeATR': '0.25',
    'InpAdaptiveNoiseDrawdownPct': '3.0', 'InpAdaptiveNoiseDefMinDirRatio': '0.30',
    'InpAdaptiveNoiseDefMaxRangeATR': '0.16', 'InpAdaptiveNoiseRecoveryPct': '1.0',
    'InpDTPTriggerR': '1.0', 'InpDTPRetrace': '0.20', 'InpDTPPartialPct': '50',
    'InpBreakevenR': '0.0', 'InpBreakevenLockR': '0.0',
}

# Strategy 3: QS3 OFF — original baseline
S3_QS3_OFF = {}

STRATEGIES = [
    ('S1_H5L',   'H5+LOOSE(lb10/a25,DTP=1R,BE=0,SL=0.5)', S1_H5_LOOSE),
    ('S2_H5ADL', 'H5+AD-LOOSE(dd3%,DTP=1R,BE=0,SL=0.4)', S2_H5_AD_LOOSE),
    ('S3_OFF',   'QS3-OFF(original DTP=1.5R,BE=0.5/0.4)', S3_QS3_OFF),
]

# Generate 24 months: 2024.06 - 2026.05
MONTHS = []
for y in [2024, 2025, 2026]:
    start_m = 6 if y == 2024 else 1
    end_m = 6 if y == 2026 else 13
    for m in range(start_m, end_m):
        m_str = f'{y % 100:02d}{m:02d}'
        from_d = f'{y}.{m:02d}.01'
        # Last day of month
        if m == 12: to_d = f'{y}.12.31'
        elif m in [1,3,5,7,8,10,12]: to_d = f'{y}.{m:02d}.31'
        elif m == 2:
            leap = (y % 4 == 0 and y % 100 != 0) or y % 400 == 0
            to_d = f'{y}.02.{29 if leap else 28}'
        else: to_d = f'{y}.{m:02d}.30'
        MONTHS.append((m_str, from_d, to_d))

total = len(STRATEGIES) * len(MONTHS)
print(f"\n{'='*70}")
print(f"  3 Strategies x {len(MONTHS)} Months = {total} BTs")
print(f"  Range: {MONTHS[0][1]} ~ {MONTHS[-1][2]}")
print(f"{'='*70}")

# Generate .set files
set_files = {}
for key, label, ov in STRATEGIES:
    base = 'v11xau-qs3.set' if key == 'S3_OFF' else 'v11xau-qs3.set'
    set_files[key] = make_set(f'24m_{key}', ov, base=base)

results = {}
done = 0
failed = []
for skey, slabel, _ in STRATEGIES:
    for mkey, mfrom, mto in MONTHS:
        done += 1
        key = f'{skey}_{mkey}'
        print(f'[{done:>3}/{total}] {slabel:<45} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'24m_{skey}_{mkey}', set_files[skey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+8.2f}')
        else:
            print('FAILED')
            failed.append(key)

# ===== SUMMARY =====
print(f"\n{'='*120}")
print(f"  24-MONTH SWEEP: 3 Strategies x 24 Months")
print(f"  Failed: {len(failed)}/{total}")
print(f"{'='*120}")

# Monthly PnL table
print(f"\n--- Monthly PnL Table ---")
header = f"  {'Month':<8}"
for skey, slabel, _ in STRATEGIES:
    header += f" {'S'+skey[1]:>12}"
header += f" {'Best':>12}"
print(header)
print(f"  {'-'*8}{'-'*40}")

monthly_totals = {skey: [] for skey, _, _ in STRATEGIES}
for mkey, _, _ in MONTHS:
    row = f"  {mkey:<8}"
    best = -99999
    for skey, _, _ in STRATEGIES:
        r = results.get(f'{skey}_{mkey}', {})
        pnl = r.get('pnl', 0) if r else 0
        row += f" ${pnl:>+11.0f}"
        if pnl > best: best = pnl
        monthly_totals[skey].append(pnl)
    row += f" ${best:>+11.0f}"
    print(row)

# Aggregate stats
print(f"\n--- Aggregate Statistics ---")
print(f"  {'Strategy':<45} {'Sum PnL':>12} {'Mean':>10} {'Median':>10} {'Worst':>10} {'Best':>10} {'WinRate':>8}")
print(f"  {'-'*100}")
for skey, slabel, _ in STRATEGIES:
    pnls = monthly_totals[skey]
    if pnls:
        total = sum(pnls)
        mean = total / len(pnls)
        med = sorted(pnls)[len(pnls)//2]
        worst = min(pnls)
        best_m = max(pnls)
        win_months = len([p for p in pnls if p > 0])
        print(f"  {slabel:<45} ${total:>+11,.0f} ${mean:>+9,.0f} ${med:>+9,.0f} ${worst:>+9,.0f} ${best_m:>+9,.0f} {win_months:>4}/{len(pnls)}")

# Monthly net comparison vs baseline
print(f"\n--- vs QS3-OFF Baseline ---")
for mkey, _, _ in MONTHS:
    off_pnl = results.get(f'S3_OFF_{mkey}', {}).get('pnl', 0)
    s1_pnl = results.get(f'S1_H5L_{mkey}', {}).get('pnl', 0)
    s2_pnl = results.get(f'S2_H5ADL_{mkey}', {}).get('pnl', 0)
    d1 = s1_pnl - off_pnl
    d2 = s2_pnl - off_pnl
    best_mark = ''
    if d1 > 0 and d2 > 0: best_mark = ' ← both better'
    elif d1 > 0: best_mark = ' ← S1 better'
    elif d2 > 0: best_mark = ' ← S2 better'
    if abs(d1) > 5 or abs(d2) > 5:
        print(f"  {mkey}: S1={d1:+.0f} S2={d2:+.0f}{best_mark}")

print(f"\n[DONE] Failed: {len(failed)}/{total}")
