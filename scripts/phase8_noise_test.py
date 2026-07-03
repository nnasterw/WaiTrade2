#!/usr/bin/env python3
"""Phase 8: Noise-adaptive entry — OFF / NOISE / MTF / MTF+NOISE comparison."""
import os, subprocess, time, re
from pathlib import Path

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(
    r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

CONFIGS = [
    ('p8_jan_off',       'v11xau-qs3-mtf-off.set',   '2026.01.01', '2026.01.31'),
    ('p8_jan_noise',     'v11xau-qs3-noise.set',      '2026.01.01', '2026.01.31'),
    ('p8_jan_mtf',       'v11xau-qs3-mtf-all.set',    '2026.01.01', '2026.01.31'),
    ('p8_jan_mtf_noise', 'v11xau-qs3-mtf-noise.set',  '2026.01.01', '2026.01.31'),
    ('p8_may_off',       'v11xau-qs3-mtf-off.set',    '2026.05.01', '2026.05.31'),
    ('p8_may_noise',     'v11xau-qs3-noise.set',       '2026.05.01', '2026.05.31'),
    ('p8_may_mtf',       'v11xau-qs3-mtf-all.set',     '2026.05.01', '2026.05.31'),
    ('p8_may_mtf_noise', 'v11xau-qs3-mtf-noise.set',   '2026.05.01', '2026.05.31'),
]


def kill_mt5():
    subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and $_.Path.StartsWith('C:\\Program Files\\MetaTrader 5') } | "
        "Stop-Process -Force"], capture_output=True)
    time.sleep(4)


def run_one(name, set_name, date_from, date_to):
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
    print("Phase 8: Noise-Adaptive Entry — 4-config comparison")
    print("=" * 55)

    results = {}
    for name, set_name, date_from, date_to in CONFIGS:
        label = name.replace('p8_', '')
        print(f"\n[{label}] {date_from}->{date_to}")
        # Clear cache for this specific test
        cache = MT5_DATA / 'Tester' / 'cache'
        if cache.exists():
            import shutil
            shutil.rmtree(cache)
            cache.mkdir()
        kill_mt5()
        r = run_one(name, set_name, date_from, date_to)
        results[name] = r
        if r:
            print(f"  OK: {r['count']}T, {r['wins']}W/{r['losses']}L, PnL=${r['pnl']:.2f}")
        else:
            print(f"  FAIL")
        time.sleep(2)

    print("\n" + "=" * 90)
    print("COMPARISON: OFF | NOISE | MTF | MTF+NOISE")
    print("=" * 90)

    for month in ['jan', 'may']:
        off = results.get(f'p8_{month}_off', {})
        noise = results.get(f'p8_{month}_noise', {})
        mtf = results.get(f'p8_{month}_mtf', {})
        both = results.get(f'p8_{month}_mtf_noise', {})

        print(f"\n--- {month.upper()} 2026 ---")
        print(f"{'Config':<16} {'Trades':>7} {'W':>5} {'L':>5} {'PnL':>10} {'vs OFF':>10}")
        print("-" * 55)

        for label, r in [('OFF', off), ('NOISE', noise), ('MTF', mtf), ('MTF+NOISE', both)]:
            if r:
                delta = r.get('pnl', 0) - off.get('pnl', 0) if off else 0
                print(f"{label:<16} {r.get('count',0):>7} {r.get('wins',0):>5} "
                      f"{r.get('losses',0):>5} ${r.get('pnl',0):>9.2f} ${delta:>+9.2f}")

    print("\n[DONE]")


if __name__ == '__main__':
    main()
