#!/usr/bin/env python3
"""Phase 4: 2026 Jan-May full month MTF-off vs MTF-all comparison."""
import os, sys, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(
    r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'
REPORT_ROOT = MT5_DATA  # Reports land in DATA root

SYMBOL, PERIOD = 'XAUUSDm', 'M1'

MONTHS = [
    ('2026.01.01', '2026.01.31', 'jan'),
    ('2026.02.01', '2026.02.28', 'feb'),
    ('2026.03.01', '2026.03.31', 'mar'),
    ('2026.04.01', '2026.04.30', 'apr'),
    ('2026.05.01', '2026.05.31', 'may'),
]

CONFIGS = [
    ('off', 'v11xau-qs3-mtf-off.set'),
    ('all', 'v11xau-qs3-mtf-all.set'),
]


def kill_mt5():
    cmd = (
        "Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and $_.Path.StartsWith('C:\\Program Files\\MetaTrader 5', "
        "[System.StringComparison]::OrdinalIgnoreCase) } | "
        "Stop-Process -Force"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)
    time.sleep(3)


def write_ini(report_name, set_name, date_from, date_to):
    os.makedirs(INI_DIR, exist_ok=True)
    ini_content = f"""[Common]
Login=
Server=
[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters={set_name}
Symbol={SYMBOL}
Period={PERIOD}
Model=4
Optimization=0
FromDate={date_from}
ToDate={date_to}
Deposit=200
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report={report_name}
"""
    ini_path = INI_DIR / 'backtest.ini'
    ini_path.write_text(ini_content, encoding='utf-8')
    return ini_path


def run_backtest(timeout=300):
    ini_path = INI_DIR / 'backtest.ini'
    config_arg = f'/config:{ini_path}'
    cmd = [MT5_TERMINAL, config_arg]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    start = time.time()
    while proc.poll() is None:
        elapsed = time.time() - start
        if elapsed > timeout:
            proc.kill()
            return False
        time.sleep(3)
    return True


def main():
    total = len(MONTHS) * len(CONFIGS)
    current = 0
    print(f"Phase 4: 2026 5-month comparison ({total} backtests)")
    print("=" * 60)

    for date_from, date_to, month_label in MONTHS:
        for cfg_label, set_name in CONFIGS:
            current += 1
            report_name = f'p4_{month_label}_{cfg_label}'
            print(f"\n[{current}/{total}] {report_name} ({date_from} -> {date_to})")

            kill_mt5()
            write_ini(report_name, set_name, date_from, date_to)

            t0 = time.time()
            ok = run_backtest(timeout=600)  # full month may need more time
            elapsed = time.time() - t0

            htm = REPORT_ROOT / f'{report_name}.htm'
            if htm.exists():
                size_kb = htm.stat().st_size / 1024
                print(f"  OK ({elapsed:.0f}s, {size_kb:.0f}KB)")
            else:
                print(f"  [WARN] No report ({elapsed:.0f}s)")

            time.sleep(2)

    print(f"\n[DONE] {total} backtests completed.")


if __name__ == '__main__':
    main()
