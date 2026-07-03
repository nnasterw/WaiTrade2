#!/usr/bin/env python3
"""Phase 13: 24-month QS3+NOISE / QS4-orig / Q2-orig comparison ($300 deposit)."""
import os, subprocess, time, re
from pathlib import Path
from collections import defaultdict

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

DATE_FROM = '2024.06.01'
DATE_TO = '2026.05.31'
DEPOSIT = 300

CONFIGS = [
    ('p13_qs3noise', 'v11xau-qs3-noise.set'),
    ('p13_qs4orig',  'CRY4A.set'),
    ('p13_q2orig',   'CRY2B.set'),
]

def kill_mt5():
    subprocess.run(["powershell","-NoProfile","-Command",
        "Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and $_.Path.StartsWith('C:\\Program Files\\MetaTrader 5') } | "
        "Stop-Process -Force"], capture_output=True)
    time.sleep(4)

def run_backtest(name, set_name):
    os.makedirs(INI_DIR, exist_ok=True)
    (INI_DIR/'backtest.ini').write_text(f"""[Common]
Login=
Server=
[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters={set_name}
Symbol=XAUUSDm
Period=M1
Model=4
Optimization=0
FromDate={DATE_FROM}
ToDate={DATE_TO}
Deposit={DEPOSIT}
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report={name}
""", encoding='utf-8')
    ini = INI_DIR / 'backtest.ini'
    print(f"  Running...", end='', flush=True)
    proc = subprocess.Popen([MT5_TERMINAL, f'/config:{ini}'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    t0 = time.time()
    while proc.poll() is None:
        elapsed = time.time() - t0
        if elapsed > 900: proc.kill(); return None
        if int(elapsed) % 30 == 0: print('.', end='', flush=True)
        time.sleep(5)
    print(f' ({time.time()-t0:.0f}s)')
    htm = MT5_DATA / f'{name}.htm'
    return htm if htm.exists() else None

def parse_monthly(htm_path):
    """Parse HTML, return monthly stats + overall summary."""
    raw = htm_path.read_bytes()
    html = raw.decode('utf-16-le', errors='replace')
    all_rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)

    monthly = defaultdict(lambda: {'trades':0,'wins':0,'losses':0,'pnl':0.0,'gross_w':0.0,'gross_l':0.0})
    total_trades = 0

    # Extract trades from 13-cell DEAL rows
    ins = {}
    for row_html in all_rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html)
        if len(cells) != 13 or cells[3] == 'balance': continue
        time_str = cells[0].strip()
        direction = cells[3].strip()
        in_out = cells[4].strip()
        order_num = cells[7].strip()
        profit = cells[10].strip()
        comment = cells[12].strip()

        if in_out == 'in':
            ins[order_num] = time_str
        elif in_out == 'out':
            try: p = float(profit)
            except: p = 0.0
            # Get month from entry time (or exit if no entry)
            entry_time = ins.get(order_num, time_str)
            try:
                # Parse YYYY.MM.DD HH:MM:SS
                parts = entry_time.split()
                date_parts = parts[0].split('.')
                month_key = f"{date_parts[0]}-{date_parts[1]}"
            except:
                month_key = 'unknown'

            m = monthly[month_key]
            m['trades'] += 1
            m['pnl'] += p
            if p > 0:
                m['wins'] += 1
                m['gross_w'] += p
            elif p < 0:
                m['losses'] += 1
                m['gross_l'] += abs(p)
            total_trades += 1

    # Summary stats
    total_pnl = sum(m['pnl'] for m in monthly.values())
    total_wins = sum(m['wins'] for m in monthly.values())
    total_losses = sum(m['losses'] for m in monthly.values())
    gross_w = sum(m['gross_w'] for m in monthly.values())
    gross_l = sum(m['gross_l'] for m in monthly.values())
    wr = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0
    pf = gross_w / gross_l if gross_l > 0 else (999 if gross_w > 0 else 0)
    final_balance = DEPOSIT + total_pnl

    # Sort months
    sorted_months = sorted(monthly.keys())

    return {
        'monthly': {k: monthly[k] for k in sorted_months},
        'summary': {
            'total_trades': total_trades,
            'total_wins': total_wins,
            'total_losses': total_losses,
            'win_rate': wr,
            'profit_factor': pf,
            'total_pnl': total_pnl,
            'final_balance': final_balance,
            'gross_w': gross_w,
            'gross_l': gross_l,
        }
    }

def main():
    print(f"Phase 13: 24-Month Comparison ({DATE_FROM} -> {DATE_TO}, ${DEPOSIT})")
    print("=" * 60)

    all_results = {}
    for name, set_name in CONFIGS:
        label = name.replace('p13_', '')
        print(f"\n[{label}] {set_name}")
        kill_mt5()
        htm = run_backtest(name, set_name)
        if htm:
            print(f"  Parsing {htm.stat().st_size/1024:.0f}KB report...")
            r = parse_monthly(htm)
            all_results[label] = r

            s = r['summary']
            print(f"  Total: {s['total_trades']}T, WR={s['win_rate']:.1f}%, "
                  f"PF={s['profit_factor']:.2f}, PnL=${s['total_pnl']:.2f}, "
                  f"Balance=${s['final_balance']:.2f}")
        else:
            print(f"  FAILED")
        time.sleep(2)

    # === STANDARD TABLE ===
    print(f"\n\n{'='*120}")
    print(f"  24月对比汇总 ({DATE_FROM} -> {DATE_TO}, 初始${DEPOSIT})")
    print(f"{'='*120}")

    labels_map = {
        'qs3noise': 'QS3+NOISE',
        'qs4orig': 'QS4(原版)',
        'q2orig': 'Q2(原版)',
    }

    print(f"\n{'Month':<9} | {'QS3+NOISE':^35} | {'QS4(原版)':^35} | {'Q2(原版)':^35}")
    print(f"{'':<9} | {'Trades WR%    PnL      Bal':<35} | {'Trades WR%    PnL      Bal':<35} | {'Trades WR%    PnL      Bal':<35}")
    print("-" * 120)

    # Get all month keys
    all_months = set()
    for r in all_results.values():
        all_months.update(r['monthly'].keys())
    sorted_months = sorted(all_months)

    running_bal = {k: DEPOSIT for k in all_results}

    for month in sorted_months:
        row = f"{month:<9} |"
        for key in ['qs3noise', 'qs4orig', 'q2orig']:
            r = all_results.get(key)
            if r and month in r['monthly']:
                m = r['monthly'][month]
                wr = m['wins']/m['trades']*100 if m['trades']>0 else 0
                running_bal[key] += m['pnl']
                row += f" {m['trades']:>4}T {wr:>4.0f}% ${m['pnl']:>8.2f} ${running_bal[key]:>9.2f} |"
            else:
                row += f" {'':>4}  {'':>4}  {'':>8} {'':>9} |"
        print(row)

    # Summary row
    print("-" * 120)
    row = f"{'合计':<9} |"
    for key in ['qs3noise', 'qs4orig', 'q2orig']:
        r = all_results.get(key)
        if r:
            s = r['summary']
            row += f" {s['total_trades']:>4}T {s['win_rate']:>4.1f}% ${s['total_pnl']:>8.2f} ${s['final_balance']:>9.2f} |"
        else:
            row += f" {'':>4}  {'':>4}  {'':>8} {'':>9} |"
    print(row)

    # Final summary table
    print(f"\n\n{'指标':<20} {'QS3+NOISE':>15} {'QS4(原版)':>15} {'Q2(原版)':>15}")
    print("-" * 70)
    for metric, attr in [('总交易数','total_trades'),('胜率%','win_rate'),('盈亏比','profit_factor'),
                          ('总盈亏$','total_pnl'),('最终余额$','final_balance'),
                          ('总盈利$','gross_w'),('总亏损$','gross_l'),
                          ('日均交易','daily_trades')]:
        row = f"{metric:<20}"
        for key in ['qs3noise','qs4orig','q2orig']:
            r = all_results.get(key)
            if r:
                s = r['summary']
                if attr == 'daily_trades':
                    val = s['total_trades'] / 730  # ~2 years
                    row += f" {val:>14.1f}"
                elif attr == 'win_rate':
                    row += f" {s[attr]:>14.1f}%"
                else:
                    row += f" ${s[attr]:>14.2f}" if 'balance' in attr or 'pnl' in attr or 'gross' in attr else f" {s[attr]:>14.2f}" if attr == 'profit_factor' else f" {s[attr]:>14}"
            else:
                row += f" {'':>14}"
        print(row)

    print(f"\n[DONE]")


if __name__ == '__main__':
    main()
