#!/usr/bin/env python3
"""Phase 2: MTF rule validation backtests. Runs 5 tests sequentially."""
import os, sys, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(
    r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

TESTS = [
    ('phase2_mtf-off', 'v11xau-qs3-mtf-off.set'),
    ('phase2_mtf-all', 'v11xau-qs3-mtf-all.set'),
    ('phase2_mtf-r5',  'v11xau-qs3-mtf-r5.set'),
    ('phase2_mtf-r4',  'v11xau-qs3-mtf-r4.set'),
    ('phase2_mtf-r1b', 'v11xau-qs3-mtf-r1b.set'),
]

SYMBOL, PERIOD = 'XAUUSDm', 'M1'
DATE_FROM, DATE_TO = '2026.05.22', '2026.05.30'


def kill_mt5():
    """Kill Program Files terminal64 processes"""
    cmd = (
        "Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and $_.Path.StartsWith('C:\\Program Files\\MetaTrader 5', "
        "[System.StringComparison]::OrdinalIgnoreCase) } | "
        "Stop-Process -Force"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)
    time.sleep(3)


def write_ini(report_name, set_name):
    """Write backtest INI to MT5 Tester dir"""
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
    """Run MT5 terminal with /config: parameter"""
    ini_path = INI_DIR / 'backtest.ini'
    config_arg = f'/config:{ini_path}'  # NO quotes around path!

    cmd = [MT5_TERMINAL, config_arg]
    print(f"  CMD: {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    start = time.time()
    while proc.poll() is None:
        elapsed = time.time() - start
        if elapsed > timeout:
            proc.kill()
            print(f'  [TIMEOUT] {timeout}s exceeded')
            return False
        if int(elapsed) % 15 == 0:
            print(f'  ...{int(elapsed)}s')
        time.sleep(3)

    print(f'  Exit: {proc.returncode} (took {time.time()-start:.0f}s)')
    return True


def read_report(report_name):
    """Extract key metrics from backtest report"""
    report = INI_DIR / f'{report_name}.txt'
    if not report.exists():
        print(f'  [WARN] Report not found: {report}')
        return None

    lines = report.read_text(encoding='utf-8', errors='replace').split('\n')
    metrics = {}
    for line in lines:
        low = line.lower().strip()
        if 'final balance' in low:
            metrics['balance'] = line.strip()
        elif 'total trades' in low:
            metrics['trades'] = line.strip()
        elif 'total net profit' in low:
            metrics['net_profit'] = line.strip()
        elif 'profit factor' in low:
            metrics['pf'] = line.strip()
        elif 'maximal drawdown' in low:
            metrics['dd'] = line.strip()
        elif 'gross profit' in low:
            metrics['gross'] = line.strip()
        elif 'gross loss' in low:
            metrics['loss'] = line.strip()
        elif 'short trades' in low:
            metrics['shorts'] = line.strip()
        elif 'long trades' in low:
            metrics['longs'] = line.strip()
        elif 'model' in low and ('tick' in low or 'open' in low):
            metrics['model'] = line.strip()

    return metrics


def main():
    print("=" * 70)
    print(f"Phase 2: MTF Rule Validation ({DATE_FROM} -> {DATE_TO})")
    print("=" * 70)

    results = []

    for name, set_name in TESTS:
        print(f"\n--- {name} ---")
        kill_mt5()
        ini = write_ini(name, set_name)
        print(f"  INI: {ini.name} -> ExpertParameters={set_name}")

        ok = run_backtest(timeout=300)
        if not ok:
            print(f"  [SKIP] Backtest failed")
            continue

        metrics = read_report(name)
        if metrics:
            metrics['name'] = name
            results.append(metrics)
            for k, v in metrics.items():
                print(f"  {v}")
        else:
            # Try to find any txt file
            txt_files = list(INI_DIR.glob('*.txt'))
            print(f"  Tester .txt files: {[f.name for f in txt_files]}")

        time.sleep(2)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    header = f"{'Test':<20} {'Trades':>6} {'Net Profit':>12} {'Balance':>12} {'PF':>6} {'DD':>8}"
    print(header)
    print("-" * len(header))
    for r in results:
        trades = r.get('trades', '').split()[-1] if r.get('trades') else '?'
        net = r.get('net_profit', '').split()[-1] if r.get('net_profit') else '?'
        bal = r.get('balance', '').split()[-1] if r.get('balance') else '?'
        pf = r.get('pf', '').split()[-1] if r.get('pf') else '?'
        dd = r.get('dd', '').split()[-1] if r.get('dd') else '?'
        print(f"{r.get('name','?'):<20} {trades:>6} {net:>12} {bal:>12} {pf:>6} {dd:>8}")

    print("\n[DONE]")


if __name__ == '__main__':
    main()
