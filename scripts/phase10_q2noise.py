#!/usr/bin/env python3
"""Phase 10: Q2+NOISE vs QS3+NOISE vs OFF full comparison."""
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
    total = len(MONTHS)
    print(f"Phase 10: Q2+NOISE ({total} backtests)")
    print("=" * 55)

    results = {}
    for i, (m_label, date_from, date_to) in enumerate(MONTHS):
        name = f'p10_{m_label}_q2noise'
        print(f"[{i+1}/{total}] {m_label}-q2noise ", end='', flush=True)
        kill_mt5()
        r = run_one(name, 'v11xau-q2-noise.set', date_from, date_to)
        results[m_label] = r
        if r:
            print(f"{r['count']}T PnL=${r['pnl']:.2f} ({r['elapsed']})")
        else:
            print(f"FAIL")
        time.sleep(2)

    # Load Phase 9 results for comparison
    p9 = {}
    for m in ['jan','feb','mar','apr','may']:
        for cfg in ['off','noise']:
            htm = MT5_DATA / f'p9_{m}_{cfg}.htm'
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
                p9[f'{m}_{cfg}'] = {
                    'count': len(trades), 'pnl': sum(trades),
                    'wins': len(wins), 'losses': len(losses),
                    'wr': f"{len(wins)/len(trades)*100:.1f}%" if trades else '0%',
                    'avg_win': f"{sum(wins)/len(wins):.2f}" if wins else '-',
                    'avg_loss': f"{sum(losses)/len(losses):.2f}" if losses else '-',
                    'pf': f"{sum(wins)/abs(sum(losses)):.2f}" if losses and sum(losses)!=0 else ('inf' if wins else '0.00'),
                }

    months_cn = {'jan':'1月','feb':'2月','mar':'3月','apr':'4月','may':'5月'}

    # Standard table
    print("\n" + "=" * 105)
    print("  Q2+NOISE vs QS3+NOISE vs OFF — 2026年1-5月对比")
    print("=" * 105)

    print(f"\n{'Month':<6} {'Config':<12} {'Trades':>6} {'W':>4} {'L':>4} {'WR%':>7} "
          f"{'Net$':>10} {'PF':>6} {'AvgW$':>7} {'AvgL$':>7}")
    print("-" * 85)

    totals = {'off': {'t':0,'pnl':0}, 'noise': {'t':0,'pnl':0}, 'q2noise': {'t':0,'pnl':0}}

    for m in ['jan','feb','mar','apr','may']:
        for cfg_key, cfg_label in [('off','OFF'), ('noise','NOISE(QS3)'), ('q2noise','Q2+NOISE')]:
            if cfg_key == 'q2noise':
                r = results.get(m, {})
            else:
                r = p9.get(f'{m}_{cfg_key}', {})

            if not r:
                continue
            totals[cfg_key]['t'] += r['count']
            totals[cfg_key]['pnl'] += r['pnl']
            print(f"{months_cn[m]:<6} {cfg_label:<12} {r['count']:>6} {r['wins']:>4} {r['losses']:>4} "
                  f"{r['wr']:>7} ${float(r['pnl']):>9.2f} {r['pf']:>6} "
                  f"${float(r['avg_win']):>6} ${float(r['avg_loss']):>6}")

    print("-" * 85)
    for cfg_key, cfg_label in [('off','OFF'), ('noise','NOISE(QS3)'), ('q2noise','Q2+NOISE')]:
        t = totals[cfg_key]
        print(f"{'合计':<6} {cfg_label:<12} {t['t']:>6} {'':>4} {'':>4} {'':>7} "
              f"${t['pnl']:>9.2f} {'':>6} {'':>7} {'':>7}")

    # Balance comparison
    print(f"\n\n  每月余额对比 (初始$200)")
    print(f"  {'Month':<6} {'OFF':>10} {'NOISE(QS3)':>11} {'Q2+NOISE':>10} "
          f"{'QS3 vs OFF':>11} {'Q2 vs OFF':>10}")
    print(f"  {'-'*55}")
    for m in ['jan','feb','mar','apr','may']:
        off_bal = 200 + p9.get(f'{m}_off', {}).get('pnl', 0)
        noise_bal = 200 + p9.get(f'{m}_noise', {}).get('pnl', 0)
        q2_bal = 200 + results.get(m, {}).get('pnl', 0)
        print(f"  {months_cn[m]:<6} ${off_bal:>9.2f} ${noise_bal:>10.2f} ${q2_bal:>9.2f} "
              f"${noise_bal-off_bal:>+10.2f} ${q2_bal-off_bal:>+9.2f}")

    print(f"\n[DONE]")


if __name__ == '__main__':
    main()
