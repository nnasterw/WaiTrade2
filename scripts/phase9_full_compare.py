#!/usr/bin/env python3
"""Phase 9: Full 5-month OFF / NOISE / MTF comparison."""
import os, subprocess, time, re
from pathlib import Path

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(
    r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

MONTHS = [
    ('jan', '2026.01.01', '2026.01.31'),
    ('feb', '2026.02.01', '2026.02.28'),
    ('mar', '2026.03.01', '2026.03.31'),
    ('apr', '2026.04.01', '2026.04.30'),
    ('may', '2026.05.01', '2026.05.31'),
]

CONFIGS = [
    ('off',   'v11xau-qs3-mtf-off.set'),
    ('noise', 'v11xau-qs3-noise.set'),
    ('mtf',   'v11xau-qs3-mtf-all.set'),
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
    elapsed = time.time() - t0
    htm = MT5_DATA / f'{name}.htm'
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
        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t < 0]
        return {
            'count': len(trades), 'pnl': sum(trades),
            'wins': len(wins), 'losses': len(losses),
            'wr': f"{len(wins)/len(trades)*100:.1f}%" if trades else '0%',
            'avg_win': f"{sum(wins)/len(wins):.2f}" if wins else '-',
            'avg_loss': f"{sum(losses)/len(losses):.2f}" if losses else '-',
            'gross_profit': f"{sum(wins):.2f}" if wins else '0.00',
            'gross_loss': f"{sum(losses):.2f}" if losses else '0.00',
            'pf': f"{sum(wins)/abs(sum(losses)):.2f}" if losses and sum(losses)!=0 else ('inf' if wins else '0.00'),
            'elapsed': f"{elapsed:.0f}s",
        }
    return None


def main():
    total = len(MONTHS) * len(CONFIGS)
    current = 0
    print(f"Phase 9: Full 5-month comparison ({total} backtests)")
    print("=" * 55)

    results = {}
    for m_label, date_from, date_to in MONTHS:
        for cfg_label, set_name in CONFIGS:
            current += 1
            name = f'p9_{m_label}_{cfg_label}'
            label = f'{m_label}-{cfg_label}'
            print(f"[{current}/{total}] {label} ", end='', flush=True)
            kill_mt5()
            r = run_one(name, set_name, date_from, date_to)
            results[f'{m_label}_{cfg_label}'] = r
            if r:
                print(f"{r['count']}T PnL=${r['pnl']:.2f} ({r['elapsed']})")
            else:
                print(f"FAIL")
            time.sleep(2)

    # === STANDARD TABLE ===
    months_cn = {'jan':'1月','feb':'2月','mar':'3月','apr':'4月','may':'5月'}

    print("\n" + "=" * 110)
    print("  2026年 1-5月 策略对比汇总 (Model 4 / Real Ticks / $200 account)")
    print("=" * 110)

    # Table 1: Main metrics
    print(f"\n{'Month':<6} {'Config':<8} {'Trades':>6} {'W':>4} {'L':>4} {'WR%':>7} "
          f"{'Net$':>10} {'PF':>6} {'Gross+':>9} {'Gross-':>9} {'AvgW$':>7} {'AvgL$':>7}")
    print("-" * 100)

    totals = {'off': {'t':0,'pnl':0}, 'noise': {'t':0,'pnl':0}, 'mtf': {'t':0,'pnl':0}}

    for m in ['jan','feb','mar','apr','may']:
        for cfg in ['off','noise','mtf']:
            key = f'{m}_{cfg}'
            r = results.get(key, {})
            if not r:
                continue
            totals[cfg]['t'] += r['count']
            totals[cfg]['pnl'] += r['pnl']
            print(f"{months_cn[m]:<6} {cfg:<8} {r['count']:>6} {r['wins']:>4} {r['losses']:>4} "
                  f"{r['wr']:>7} ${float(r['pnl']):>9.2f} {r['pf']:>6} "
                  f"${float(r['gross_profit']):>8} ${float(r['gross_loss']):>8} "
                  f"${float(r['avg_win']):>6} ${float(r['avg_loss']):>6}")

    # Totals row
    print("-" * 100)
    for cfg in ['off','noise','mtf']:
        t = totals[cfg]
        print(f"{'合计':<6} {cfg:<8} {t['t']:>6} {'':>4} {'':>4} {'':>7} "
              f"${t['pnl']:>9.2f} {'':>6} {'':>9} {'':>9} {'':>7} {'':>7}")

    # Table 2: Monthly balance comparison
    print(f"\n\n  每月独立$200账户余额对比")
    print(f"  {'Month':<6} {'OFF Bal':>10} {'NOISE Bal':>10} {'MTF Bal':>10} "
          f"{'NOISE vs OFF':>13} {'MTF vs OFF':>12}")
    print(f"  {'-'*55}")
    for m in ['jan','feb','mar','apr','may']:
        off_bal = 200 + results.get(f'{m}_off', {}).get('pnl', 0)
        noise_bal = 200 + results.get(f'{m}_noise', {}).get('pnl', 0)
        mtf_bal = 200 + results.get(f'{m}_mtf', {}).get('pnl', 0)
        noise_diff = noise_bal - off_bal
        mtf_diff = mtf_bal - off_bal
        print(f"  {months_cn[m]:<6} ${off_bal:>9.2f} ${noise_bal:>9.2f} ${mtf_bal:>9.2f} "
              f"${noise_diff:>+12.2f} ${mtf_diff:>+11.2f}")

    # Table 3: Trade reduction rates
    print(f"\n\n  交易拦截率对比")
    print(f"  {'Month':<6} {'OFF Trades':>10} {'NOISE Trades':>12} {'NOISE Cut%':>10} "
          f"{'MTF Trades':>10} {'MTF Cut%':>9}")
    print(f"  {'-'*55}")
    for m in ['jan','feb','mar','apr','may']:
        off_t = results.get(f'{m}_off', {}).get('count', 0)
        noise_t = results.get(f'{m}_noise', {}).get('count', 0)
        mtf_t = results.get(f'{m}_mtf', {}).get('count', 0)
        noise_cut = (1 - noise_t/off_t)*100 if off_t > 0 else 0
        mtf_cut = (1 - mtf_t/off_t)*100 if off_t > 0 else 0
        print(f"  {months_cn[m]:<6} {off_t:>10} {noise_t:>12} {noise_cut:>9.1f}% "
              f"{mtf_t:>10} {mtf_cut:>9.1f}%")

    print(f"\n[DONE]")


if __name__ == '__main__':
    main()
