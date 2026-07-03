#!/usr/bin/env python3
"""Phase 7: R4v2 H1-aligned override - Jan & May test."""
import os, subprocess, time, re
from pathlib import Path

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(
    r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

TESTS = [
    ('p7_jan_r4v2', 'v11xau-qs3-mtf-all.set', '2026.01.01', '2026.01.31'),
    ('p7_may_r4v2', 'v11xau-qs3-mtf-all.set', '2026.05.01', '2026.05.31'),
]


def kill_mt5():
    subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and $_.Path.StartsWith('C:\\Program Files\\MetaTrader 5') } | "
        "Stop-Process -Force"], capture_output=True)
    time.sleep(3)


def run_test(name, set_name, date_from, date_to):
    os.makedirs(INI_DIR, exist_ok=True)
    ini = f"""[Common]
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
Report={name}
"""
    (INI_DIR / 'backtest.ini').write_text(ini, encoding='utf-8')
    config_arg = f'/config:{INI_DIR / "backtest.ini"}'
    proc = subprocess.Popen(
        [MT5_TERMINAL, config_arg],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    t0 = time.time()
    while proc.poll() is None:
        if time.time() - t0 > 600:
            proc.kill()
            return None
        time.sleep(3)
    elapsed = time.time() - t0
    htm = MT5_DATA / f'{name}.htm'
    if htm.exists():
        raw = htm.read_bytes()
        html = raw.decode('utf-16-le', errors='replace')
        all_rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
        trades = []
        for r in all_rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
            if len(cells) == 13 and cells[3] != 'balance' and cells[4].strip() == 'out':
                try: trades.append(float(cells[10].strip()))
                except: pass
        return {
            'count': len(trades), 'pnl': sum(trades),
            'wins': len([t for t in trades if t > 0]),
            'losses': len([t for t in trades if t < 0]),
        }
    return None


def main():
    print("Phase 7: R4v2 H1-aligned override")
    print("=" * 50)

    results = {}
    for name, set_name, date_from, date_to in TESTS:
        print(f"\n[{name}] {date_from}->{date_to}")
        kill_mt5()
        r = run_test(name, set_name, date_from, date_to)
        results[name] = r
        if r:
            print(f"  OK: {r['count']}T, {r['wins']}W/{r['losses']}L, PnL=${r['pnl']:.2f}")
        else:
            print(f"  FAIL")
        time.sleep(2)

    # Also parse old results
    old = {}
    for key in ['p4_jan_off','p4_jan_all','p4_may_off','p4_may_all']:
        htm = MT5_DATA / f'{key}.htm'
        if htm.exists():
            raw = htm.read_bytes()
            html = raw.decode('utf-16-le', errors='replace')
            all_rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
            trades = []
            for r in all_rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
                if len(cells)==13 and cells[3]!='balance' and cells[4].strip()=='out':
                    try: trades.append(float(cells[10].strip()))
                    except: pass
            old[key] = {'count': len(trades), 'pnl': sum(trades),
                        'wins': len([t for t in trades if t>0]),
                        'losses': len([t for t in trades if t<0])}

    print("\n" + "=" * 80)
    print("COMPARISON: OFF vs ALL(old) vs ALL(R4v2 new)")
    print("=" * 80)
    print(f"\n{'Month':<6} {'Config':<12} {'Trades':>7} {'W':>5} {'L':>5} {'PnL':>10} {'vs OFF':>10}")
    print("-" * 55)

    for month, off_k, all_k, new_k in [
        ('Jan', 'p4_jan_off', 'p4_jan_all', 'p7_jan_r4v2'),
        ('May', 'p4_may_off', 'p4_may_all', 'p7_may_r4v2'),
    ]:
        o = old.get(off_k, {})
        a = old.get(all_k, {})
        n = results.get(new_k, {})

        if o:
            print(f"{month:<6} {'OFF':<12} {o.get('count',0):>7} {o.get('wins',0):>5} "
                  f"{o.get('losses',0):>5} ${o.get('pnl',0):>9.2f} {'':>10}")
        if a:
            d = a.get('pnl',0) - o.get('pnl',0) if o else 0
            print(f"{month:<6} {'ALL old R4':<12} {a.get('count',0):>7} {a.get('wins',0):>5} "
                  f"{a.get('losses',0):>5} ${a.get('pnl',0):>9.2f} ${d:>+9.2f}")
        if n:
            d = n.get('pnl',0) - o.get('pnl',0) if o else 0
            print(f"{month:<6} {'ALL R4v2':<12} {n.get('count',0):>7} {n.get('wins',0):>5} "
                  f"{n.get('losses',0):>5} ${n.get('pnl',0):>9.2f} ${d:>+9.2f}")

    print("\n[DONE]")


if __name__ == '__main__':
    main()
