#!/usr/bin/env python3
"""ZD vs QS 月度对比 + 0529三天窗口"""
import subprocess, sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / 'results' / 'backtest'

months = [
    ("2024.06.01", "2024.06.30", "2024-06"),
    ("2024.09.01", "2024.09.30", "2024-09"),
    ("2024.12.01", "2024.12.31", "2024-12"),
    ("2025.05.01", "2025.05.31", "2025-05"),
    ("2025.08.01", "2025.08.31", "2025-08"),
    ("2025.12.01", "2025.12.31", "2025-12"),
    ("2026.01.01", "2026.01.31", "2026-01"),
    ("2026.04.01", "2026.04.30", "2026-04"),
    ("2026.05.01", "2026.05.31", "2026-05"),
    # 0529三天窗口
    ("2025.05.28", "2025.05.30", "0529±1d"),
]

def run_bt(strategy, date_from, date_to):
    result = subprocess.run([
        sys.executable, str(ROOT / 'scripts' / 'mt5_backtest_win.py'),
        '--strategy', strategy, '--symbol', 'XAUUSDm',
        '--from', date_from, '--to', date_to,
        '--model', '4', '--timeout', '300',
    ], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(ROOT))
    text = result.stdout + result.stderr
    m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', text)
    if m:
        return int(m.group(1)), float(m.group(2)), float(m.group(3))
    return None

print(f"{'Month':<10} | {'ZD T':>5} {'ZD WR':>6} {'ZD Bal':>8} {'ZD Ret':>7} | {'QS T':>5} {'QS WR':>6} {'QS Bal':>8} {'QS Ret':>7} | Better")
print("-" * 90)

for date_from, date_to, label in months:
    print(f"[{label}] ", end='', flush=True)
    zd = run_bt('v11xau-zd', date_from, date_to)
    qs = run_bt('v11xau-qs', date_from, date_to)

    zd_str = f"{zd[0]:>5} {zd[1]:>5.1f}% ${zd[2]:>7.2f} {(zd[2]-200)/200*100:>+6.1f}%" if zd else "   -    -       -      -"
    qs_str = f"{qs[0]:>5} {qs[1]:>5.1f}% ${qs[2]:>7.2f} {(qs[2]-200)/200*100:>+6.1f}%" if qs else "   -    -       -      -"

    if zd and qs:
        better = "ZD" if zd[2] > qs[2] else "QS"
    else:
        better = "?"

    print(f"\r{label:<10} | {zd_str} | {qs_str} | {better}")

# Also read existing report files for any cached results
print()
print("--- Summary ---")
print("ZD wins when: 震荡/弱趋势 (OB回归), low frequency high quality")
print("QS wins when: 单边强趋势 (OB延续), high frequency trend following")
print("Both lose when: 高波动无方向噪音")
