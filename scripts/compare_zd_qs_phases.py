#!/usr/bin/env python3
"""ZD(M3) vs QS(M1) complete monthly comparison + phase detection"""
import subprocess, sys, re
from pathlib import Path
from calendar import monthrange

ROOT = Path(__file__).resolve().parent.parent

months = []
for year in (2024, 2025, 2026):
    sm = 6 if year == 2024 else 1
    em = 5 if year == 2026 else 12
    for m in range(sm, em + 1):
        _, ld = monthrange(year, m)
        months.append((f"{year}.{m:02d}.01", f"{year}.{m:02d}.{ld:02d}", f"{year}-{m:02d}"))

strategies = [('v11xau-zd', 'ZD'), ('v11xau-qs', 'QS')]
all_data = {}

for strat, label in strategies:
    print(f"\n{'='*60}")
    print(f"  {label} ({strat}) monthly")
    print(f"{'='*60}")
    print(f"{'Month':<10} {'Trades':>5} {'WR':>6} {'Balance':>9} {'Return':>8}")
    print("-" * 50)
    data = []

    for date_from, date_to, ml in months:
        print(f"  [{ml}] ", end='', flush=True)
        result = subprocess.run([
            sys.executable, str(ROOT / 'scripts' / 'mt5_backtest_win.py'),
            '--strategy', strat, '--symbol', 'XAUUSDm',
            '--from', date_from, '--to', date_to,
            '--model', '4', '--timeout', '300',
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(ROOT))
        text = result.stdout + result.stderr
        m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', text)
        if m:
            t = int(m.group(1)); wr = float(m.group(2)); bal = float(m.group(3))
            ret = (bal - 200) / 200 * 100
            data.append((ml, t, wr, bal, ret))
            print(f"\r{ml:<10} {t:>5} {wr:>5.1f}% ${bal:>8.2f} {ret:>+7.1f}%")
        else:
            data.append((ml, 0, 0, 200, 0))
            print(f"\r{ml:<10}   FAILED")

    all_data[label] = data

# Cross comparison
print(f"\n{'='*80}")
print(f"  ZD vs QS Monthly Comparison + WR Trigger Test")
print(f"{'='*80}")
print(f"{'Month':<10} | {'ZD T':>5} {'ZD WR':>6} {'ZD Ret':>8} | {'QS T':>5} {'QS WR':>6} {'QS Ret':>8} | {'Winner':>6} | Trigger")
print("-" * 90)

zd_wins = qs_wins = 0
last_3wr = []  # trailing 3-month WR for QS as trigger

for i, (ml, _, _, _, _) in enumerate(months):
    zd = all_data['ZD'][i]
    qs = all_data['QS'][i]
    zd_t, zd_wr, zd_bal, zd_ret = zd[1], zd[2], zd[3], zd[4]
    qs_t, qs_wr, qs_bal, qs_ret = qs[1], qs[2], qs[3], qs[4]

    winner = "ZD" if zd_ret > qs_ret else "QS"
    if zd_ret > qs_ret: zd_wins += 1
    else: qs_wins += 1

    # WR trigger test: if QS WR < 50% for 3 consecutive months, recommend ZD
    last_3wr.append(qs_wr)
    if len(last_3wr) > 3:
        last_3wr.pop(0)

    trigger = ""
    if len(last_3wr) >= 3:
        avg_wr = sum(last_3wr) / 3
        if avg_wr < 50:
            trigger = "⚠️ WR<50%→SWITCH ZD"
        elif avg_wr > 55:
            trigger = "✅ WR>55%→STAY QS"

    print(f"{ml:<10} | {zd_t:>5} {zd_wr:>5.1f}% {zd_ret:>+7.1f}% | {qs_t:>5} {qs_wr:>5.1f}% {qs_ret:>+7.1f}% | {winner:>6} | {trigger}")

print("-" * 90)
print(f"ZD wins: {zd_wins}/{len(months)} | QS wins: {qs_wins}/{len(months)}")

# Phase summary
print(f"\n{'='*60}")
print(f"  Complementarity Summary")
print(f"{'='*60}")

# Find ZD-wins months vs QS-wins months
zd_months = []
qs_months = []
for i, (ml, _, _, _, _) in enumerate(months):
    if all_data['ZD'][i][4] > all_data['QS'][i][4]:
        zd_months.append(ml)
    else:
        qs_months.append(ml)

print(f"ZD wins ({len(zd_months)}): {', '.join(zd_months)}")
print(f"QS wins ({len(qs_months)}): {', '.join(qs_months)}")

# WR trigger effectiveness
print(f"\n=== WR Trigger Effectiveness ===")
# Count how many months the trigger correctly predicted the winner
correct = 0
total = 0
last_3wr = []
for i, (ml, _, _, _, _) in enumerate(months):
    qs_wr = all_data['QS'][i][2]
    last_3wr.append(qs_wr)
    if len(last_3wr) > 3:
        last_3wr.pop(0)
    if len(last_3wr) >= 3:
        avg_wr = sum(last_3wr) / 3
        pred_zd = avg_wr < 50  # predict ZD wins
        actual_zd = all_data['ZD'][i][4] > all_data['QS'][i][4]
        if pred_zd == actual_zd:
            correct += 1
        total += 1
        # print(f"  {ml}: avgWR={avg_wr:.1f}% pred={'ZD' if pred_zd else 'QS'} actual={'ZD' if actual_zd else 'QS'} {'✓' if pred_zd==actual_zd else '✗'}")

if total > 0:
    print(f"WR Trigger accuracy: {correct}/{total} ({correct/total*100:.0f}%)")
