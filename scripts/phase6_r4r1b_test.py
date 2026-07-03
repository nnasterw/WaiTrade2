#!/usr/bin/env python3
"""Phase 6: R4+R1b only (R5 disabled). Test Jan + May vs old ALL."""
import os, sys, subprocess, time, re
from pathlib import Path

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(
    r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

SET_NAME = 'v11xau-qs3-mtf-r4r1b.set'

TESTS = [
    ('p6_jan_r4r1b', '2026.01.01', '2026.01.31'),
    ('p6_may_r4r1b', '2026.05.01', '2026.05.31'),
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


def write_ini(report_name, date_from, date_to):
    os.makedirs(INI_DIR, exist_ok=True)
    ini_content = f"""[Common]
Login=
Server=
[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters={SET_NAME}
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
    (INI_DIR / 'backtest.ini').write_text(ini_content, encoding='utf-8')


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
    print("Phase 6: R4+R1b only (R5 disabled) — Jan & May")
    print("=" * 50)

    for name, date_from, date_to in TESTS:
        print(f"\n[{name}] {date_from}->{date_to}")
        kill_mt5()
        write_ini(name, date_from, date_to)
        t0 = time.time()
        run_backtest(timeout=600)
        elapsed = time.time() - t0
        htm = MT5_DATA / f'{name}.htm'
        if htm.exists():
            r = parse_one(htm)
            print(f"  OK ({elapsed:.0f}s): {r['count']}T, {r['wins']}W/{r['losses']}L, PnL=${r['pnl']:.2f}")
        else:
            print(f"  FAIL: no report")
        time.sleep(2)

    # Comparison table
    print("\n" + "=" * 80)
    print("COMPARISON: OFF vs ALL(R5+R4+R1b) vs ALL(R4+R1b only)")
    print("=" * 80)

    old = {}
    for key in ['p4_jan_off', 'p4_jan_all', 'p4_may_off', 'p4_may_all']:
        htm = MT5_DATA / f'{key}.htm'
        if htm.exists():
            old[key] = parse_one(htm)

    new = {}
    for name, _, _ in TESTS:
        htm = MT5_DATA / f'{name}.htm'
        if htm.exists():
            new[name] = parse_one(htm)

    print(f"\n{'Month':<6} {'Config':<18} {'Trades':>7} {'W':>5} {'L':>5} {'PnL':>10} {'vs OFF':>10}")
    print("-" * 60)

    for month, off_key, all_key, new_key in [
        ('Jan', 'p4_jan_off', 'p4_jan_all', 'p6_jan_r4r1b'),
        ('May', 'p4_may_off', 'p4_may_all', 'p6_may_r4r1b'),
    ]:
        o = old.get(off_key, {})
        a = old.get(all_key, {})
        n = new.get(new_key, {})

        if o:
            print(f"{month:<6} {'OFF (baseline)':<18} {o.get('count',0):>7} {o.get('wins',0):>5} "
                  f"{o.get('losses',0):>5} ${o.get('pnl',0):>9.2f} {'':>10}")
        if a:
            delta_a = a.get('pnl', 0) - o.get('pnl', 0) if o else 0
            print(f"{month:<6} {'ALL R5+R4+R1b':<18} {a.get('count',0):>7} {a.get('wins',0):>5} "
                  f"{a.get('losses',0):>5} ${a.get('pnl',0):>9.2f} ${delta_a:>+9.2f}")
        if n:
            delta_n = n.get('pnl', 0) - o.get('pnl', 0) if o else 0
            print(f"{month:<6} {'ALL R4+R1b only':<18} {n.get('count',0):>7} {n.get('wins',0):>5} "
                  f"{n.get('losses',0):>5} ${n.get('pnl',0):>9.2f} ${delta_n:>+9.2f}")

    print("\n[DONE]")


if __name__ == '__main__':
    main()
