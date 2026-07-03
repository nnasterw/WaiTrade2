#!/usr/bin/env python3
"""Phase 3: MTF on GOOD month (2025.10) — verify MTF doesn't kill good trades."""
import os, sys, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(
    r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

TESTS = [
    ('phase3_mtf-off', 'v11xau-qs3-mtf-off.set'),
    ('phase3_mtf-all', 'v11xau-qs3-mtf-all.set'),
]

SYMBOL, PERIOD = 'XAUUSDm', 'M1'
DATE_FROM, DATE_TO = '2025.10.01', '2025.10.07'  # 7 days to match Phase 2


def kill_mt5():
    cmd = (
        "Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and $_.Path.StartsWith('C:\\Program Files\\MetaTrader 5', "
        "[System.StringComparison]::OrdinalIgnoreCase) } | "
        "Stop-Process -Force"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)
    time.sleep(3)


def write_ini(report_name, set_name):
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
FromDate={DATE_FROM}
ToDate={DATE_TO}
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
    print(f"  CMD: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    start = time.time()
    while proc.poll() is None:
        elapsed = time.time() - start
        if elapsed > timeout:
            proc.kill()
            print(f'  [TIMEOUT]')
            return False
        if int(elapsed) % 15 == 0:
            print(f'  ...{int(elapsed)}s')
        time.sleep(3)
    print(f'  Done in {time.time()-start:.0f}s')
    return True


def main():
    print("=" * 70)
    print(f"Phase 3: Good Month Test ({DATE_FROM} -> {DATE_TO})")
    print("=" * 70)

    for name, set_name in TESTS:
        print(f"\n--- {name} ---")
        kill_mt5()
        write_ini(name, set_name)
        run_backtest(timeout=300)
        time.sleep(2)

    # Check reports
    DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
    for name, _ in TESTS:
        htm = DATA / f'{name}.htm'
        if htm.exists():
            print(f"  {name}: {htm.stat().st_size} bytes")
        else:
            print(f"  {name}: MISSING")

    print("\n[DONE] Phase 3 baselines ready.")


if __name__ == '__main__':
    main()
