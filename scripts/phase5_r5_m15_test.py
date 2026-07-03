#!/usr/bin/env python3
"""Phase 5: R5 M15 fix — test Jan + May, compare with old R5 H1."""
import os, sys, subprocess, time, re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(
    r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'
REPORT_ROOT = MT5_DATA

TESTS = [
    ('p5_jan_off', 'v11xau-qs3-mtf-off.set', '2026.01.01', '2026.01.31'),
    ('p5_jan_all', 'v11xau-qs3-mtf-all.set', '2026.01.01', '2026.01.31'),
    ('p5_may_off', 'v11xau-qs3-mtf-off.set', '2026.05.01', '2026.05.31'),
    ('p5_may_all', 'v11xau-qs3-mtf-all.set', '2026.05.01', '2026.05.31'),
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
Symbol=XAUUSDm
Period=M1
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
        if time.time() - start > timeout:
            proc.kill()
            return False
        time.sleep(3)
    return True


def parse_one(htm_path):
    """Quick parse: trades + P&L."""
    raw = htm_path.read_bytes()
    html = raw.decode('utf-16-le', errors='replace')
    all_rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    trades = []
    for row_html in all_rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html)
        if len(cells) == 13 and cells[3] != 'balance' and cells[4].strip() == 'out':
            try:
                trades.append(float(cells[10].strip()))
            except:
                pass
    return {
        'count': len(trades),
        'pnl': sum(trades),
        'wins': len([t for t in trades if t > 0]),
        'losses': len([t for t in trades if t < 0]),
    }


def main():
    print("Phase 5: R5 M15 fix — Jan & May retest")
    print("=" * 50)

    for name, set_name, date_from, date_to in TESTS:
        print(f"\n[{name}] {date_from}->{date_to}")
        kill_mt5()
        write_ini(name, set_name, date_from, date_to)
        t0 = time.time()
        run_backtest(timeout=600)
        elapsed = time.time() - t0
        htm = REPORT_ROOT / f'{name}.htm'
        if htm.exists():
            r = parse_one(htm)
            print(f"  OK ({elapsed:.0f}s): {r['count']}T, {r['wins']}W/{r['losses']}L, PnL=${r['pnl']:.2f}")
        else:
            print(f"  FAIL: no report")
        time.sleep(2)

    # Comparison
    print("\n" + "=" * 70)
    print("COMPARISON: Old R5(H1) vs New R5(M15)")
    print("=" * 70)

    # Old results from Phase 4
    old = {
        'p4_jan_off': parse_one(REPORT_ROOT / 'p4_jan_off.htm'),
        'p4_jan_all': parse_one(REPORT_ROOT / 'p4_jan_all.htm'),
        'p4_may_off': parse_one(REPORT_ROOT / 'p4_may_off.htm'),
        'p4_may_all': parse_one(REPORT_ROOT / 'p4_may_all.htm'),
    }
    new = {}
    for name, _, _, _ in TESTS:
        htm = REPORT_ROOT / f'{name}.htm'
        if htm.exists():
            new[name] = parse_one(htm)

    print(f"\n{'Month':<6} {'Config':<5} {'Version':<8} {'Trades':>7} {'W':>5} {'L':>5} {'PnL':>10} {'Delta':>10}")
    print("-" * 55)
    for prefix, month in [('p4', 'Jan-old'), ('p5', 'Jan-new'), ('p4', 'May-old'), ('p5', 'May-new')]:
        for cfg in ['jan_off', 'jan_all', 'may_off', 'may_all']:
            key = f'{prefix}_{cfg}'
            if prefix == 'p4':
                r = old.get(key, {})
            else:
                r = new.get(key, {})
            if not r:
                continue
            # calculate delta vs old
            old_key = f'p4_{cfg}'
            old_r = old.get(old_key, {})
            delta = r.get('pnl', 0) - old_r.get('pnl', 0) if prefix == 'p5' else 0
            label = f"{prefix.split('_')[0]}-{cfg.replace('_','-')}"
            ver = 'R5-H1' if prefix == 'p4' else 'R5-M15'
            print(f"{month:<6} {cfg.replace('jan_','').replace('may_',''):<5} {ver:<8} "
                  f"{r.get('count',0):>7} {r.get('wins',0):>5} {r.get('losses',0):>5} "
                  f"${r.get('pnl',0):>9.2f} {'':>10}" if prefix == 'p4' else
                  f"{month:<6} {cfg.replace('jan_','').replace('may_',''):<5} {ver:<8} "
                  f"{r.get('count',0):>7} {r.get('wins',0):>5} {r.get('losses',0):>5} "
                  f"${r.get('pnl',0):>9.2f} ${delta:>+9.2f}")

    print("\n[DONE]")


if __name__ == '__main__':
    main()
