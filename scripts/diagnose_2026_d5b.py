#!/usr/bin/env python3
"""D5B 2026年坏月诊断：提取逐笔交易数据，分析失败模式"""
import os, sys, re, time, subprocess
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
MT5_TESTER_DIR = MT5_DATA / 'Tester'
MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
BASE_SET = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'

D5B_PARAMS = {
    'InpBouncePct': '0.30', 'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4', 'InpMaxCounterRiskATR': '0.5',
    'InpMaxEntriesPerOB': '2', 'InpEnableDeepestPullbackSL': 'true',
    'InpDeepestPullbackBuffer': '0.5',
}

# 对比：好的2025月份
GOOD_MONTHS = [("2025.10.01", "2025.10.31", "2025-10_good")]
BAD_MONTHS = [
    ("2026.01.01", "2026.01.31", "2026-01"),
    ("2026.02.01", "2026.02.28", "2026-02"),
    ("2026.03.01", "2026.03.31", "2026-03"),
    ("2026.04.01", "2026.04.30", "2026-04"),
    ("2026.05.01", "2026.05.31", "2026-05"),
]

def replace_param(content, key, val):
    pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
    if pattern.search(content):
        return pattern.sub(f'{key}={val}', content)
    return content + f'\n{key}={val}\n'

def make_set():
    dst = MT5_PROFILES_DIR / 'v11xau-qs3-d5b-diag.set'
    content = BASE_SET.read_text(encoding='utf-8')
    content = replace_param(content, 'InpVersion', 'V11XAU-QS3-D5B-DIAG')
    content = replace_param(content, 'InpMagicNumber', '204866')
    content = replace_param(content, 'InpEnableEntryDebug', 'true')
    content = replace_param(content, 'InpEnableExitDebug', 'true')  # 开启出场诊断
    for key, val in D5B_PARAMS.items():
        content = replace_param(content, key, val)
    dst.write_text(content)
    return dst

def kill_mt5_tester():
    try:
        subprocess.run(['powershell', '-Command',
            "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"
        ], capture_output=True, timeout=10)
    except:
        pass
    time.sleep(3)

def run_and_save_html(label, date_from, date_to):
    """Run backtest and save HTML for analysis"""
    ini_file = MT5_TESTER_DIR / 'backtest.ini'
    report_name = f'd5b_diag_{label}'

    ini_content = f"""[Common]
Login=
Server=

[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters=v11xau-qs3-d5b-diag.set
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
    ini_file.write_text(ini_content)
    kill_mt5_tester()

    # Clean old reports
    for old in MT5_DATA.glob('d5b_diag*.htm'):
        try: old.unlink()
        except: pass

    print(f"    回测 {date_from}~{date_to}...", end=' ', flush=True)
    subprocess.Popen([MT5_TERMINAL, f'/config:{ini_file}'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for i in range(60):
        time.sleep(5)
        try:
            result = subprocess.run(['powershell', '-Command',
                "(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
                "Where-Object { $_.Path -like '*Program Files*' }).Count"
            ], capture_output=True, text=True, timeout=5)
            if result.stdout.strip() == '0':
                break
        except:
            pass
    time.sleep(2)

    html_files = sorted(MT5_DATA.glob('d5b_diag*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    if html_files:
        print(f"OK ({html_files[0].stat().st_size} bytes)")
        return html_files[0]
    print("FAILED")
    return None

def parse_trades(html_path):
    """Extract individual trade data from HTML"""
    raw = html_path.read_bytes()
    try:
        text = raw.decode('utf-16-le')
    except:
        text = raw.decode('utf-8', errors='ignore')

    lines = text.split('\n')
    trades = []
    open_positions = {}  # deal# -> entry info

    for line in lines:
        if 'XAUUSDm' not in line:
            continue
        clean = re.sub(r'<[^>]+>', ' | ', line).strip()
        parts = [p.strip() for p in clean.split('|')]
        non_empty = [p for p in parts if p]

        try:
            sym_idx = non_empty.index('XAUUSDm')
        except ValueError:
            continue

        if sym_idx + 4 >= len(non_empty):
            continue

        direction = non_empty[sym_idx + 1]  # buy/sell
        inout = non_empty[sym_idx + 2]      # in/out
        if inout not in ('in', 'out'):
            continue

        try:
            deal_num = int(non_empty[sym_idx - 1]) if sym_idx > 0 else 0
        except:
            continue

        if inout == 'in':
            # Entry: store for later
            try:
                lot = float(non_empty[sym_idx + 3])
                price = float(non_empty[sym_idx + 4])
                # Comment is last non-empty
                comment = non_empty[-1] if non_empty[-1] != 'XAUUSDm' else ''
                # Time is first non-empty
                time_str = non_empty[0]

                open_positions[deal_num] = {
                    'time': time_str,
                    'direction': direction,
                    'lot': lot,
                    'entry_price': price,
                    'comment': comment,
                }
            except (ValueError, IndexError):
                pass

        elif inout == 'out':
            try:
                exit_price = float(non_empty[sym_idx + 4])
                profit = float(non_empty[-3].replace(' ', ''))
                balance = float(non_empty[-2].replace(' ', ''))
                exit_reason = non_empty[-1] if non_empty[-1] not in ('XAUUSDm', '') else 'unknown'

                # Try to find matching entry
                # For MT5 hedging, the out deal references the in deal position
                # We'll match by proximity (first unmatched in gets matched)
                entry_info = None
                for dnum in sorted(open_positions.keys()):
                    if open_positions[dnum]['direction'] != direction:
                        entry_info = open_positions.pop(dnum)
                        break

                time_str = non_empty[0]
                trades.append({
                    'time': time_str,
                    'direction': direction,
                    'entry_price': entry_info['entry_price'] if entry_info else 0,
                    'exit_price': exit_price,
                    'lot': entry_info['lot'] if entry_info else 0,
                    'profit': profit,
                    'balance': balance,
                    'exit_reason': exit_reason,
                    'entry_comment': entry_info['comment'] if entry_info else '',
                    'deal': deal_num,
                })
            except (ValueError, IndexError):
                pass

    return trades


# ── Main ──────────────────────────────────────────────────────
print("=" * 60)
print("  D5B 2026年坏月交易诊断")
print("=" * 60)

make_set()
all_data = {}

for date_from, date_to, label in GOOD_MONTHS + BAD_MONTHS:
    print(f"\n[{label}]")
    html = run_and_save_html(label, date_from, date_to)
    if html:
        trades = parse_trades(html)
        all_data[label] = trades
        # Keep HTML for reference
        print(f"    提取 {len(trades)} 笔交易")
    else:
        all_data[label] = []

# ── Analysis ──────────────────────────────────────────────────
print(f"\n{'='*80}")
print(f"  逐月交易分析")
print(f"{'='*80}")

for label, trades in all_data.items():
    if not trades:
        continue
    wins = [t for t in trades if t['profit'] > 0]
    losses = [t for t in trades if t['profit'] < 0]
    wr = len(wins)/len(trades)*100 if trades else 0

    # Exit reasons
    exit_counts = Counter(t['exit_reason'] for t in trades)
    loss_exits = Counter(t['exit_reason'] for t in losses)

    # Direction
    buys = [t for t in trades if t['direction'] == 'buy']
    sells = [t for t in trades if t['direction'] == 'sell']
    buy_wr = len([t for t in buys if t['profit']>0])/len(buys)*100 if buys else 0
    sell_wr = len([t for t in sells if t['profit']>0])/len(sells)*100 if sells else 0

    # Consecutive losses
    max_consec_loss = 0
    consec = 0
    loss_runs = []
    for t in trades:
        if t['profit'] < 0:
            consec += 1
        else:
            if consec >= 2:
                loss_runs.append(consec)
            max_consec_loss = max(max_consec_loss, consec)
            consec = 0
    if consec >= 2:
        loss_runs.append(consec)
    max_consec_loss = max(max_consec_loss, consec)

    # Avg win/loss
    avg_win = sum(t['profit'] for t in wins)/len(wins) if wins else 0
    avg_loss = sum(t['profit'] for t in losses)/len(losses) if losses else 0
    pf = abs(avg_win/avg_loss) if avg_loss != 0 else 99

    # Profit by exit reason
    profit_by_exit = defaultdict(float)
    for t in trades:
        profit_by_exit[t['exit_reason']] += t['profit']

    print(f"\n{'─'*60}")
    print(f"  {label}: {len(trades)}t, WR={wr:.1f}%, PF={pf:.2f}")
    print(f"  Avg Win: ${avg_win:.2f}, Avg Loss: ${avg_loss:.2f}")
    print(f"  Buy WR={buy_wr:.1f}% ({len(buys)}t), Sell WR={sell_wr:.1f}% ({len(sells)}t)")
    print(f"  Max Consec Losses: {max_consec_loss}")
    if loss_runs:
        print(f"  Loss Clusters (>=2): {loss_runs}")

    print(f"\n  所有出场原因: {dict(exit_counts.most_common())}")
    print(f"  亏损出场原因: {dict(loss_exits.most_common())}")
    print(f"  出场原因盈亏: ", end='')
    for reason, pnl in sorted(profit_by_exit.items(), key=lambda x: x[1]):
        print(f"{reason}:${pnl:.1f} ", end='')
    print()

    # Top 5 worst losses
    worst = sorted(trades, key=lambda t: t['profit'])[:5]
    print(f"\n  Top 5 最大亏损:")
    for t in worst:
        print(f"    {t['time']} {t['direction']} profit=${t['profit']:.2f} reason={t['exit_reason']} "
              f"lot={t['lot']:.2f} entry_comment={t['entry_comment'][:40]}")

# ── Cross-month comparison ────────────────────────────────────
print(f"\n{'='*80}")
print(f"  好月(2025-10) vs 坏月(2026) 对比")
print(f"{'='*80}")

good_trades = all_data.get('2025-10_good', [])
bad_trades = []
for label in ['2026-01', '2026-02', '2026-03', '2026-04', '2026-05']:
    bad_trades.extend(all_data.get(label, []))

if good_trades and bad_trades:
    good_wins = [t for t in good_trades if t['profit'] > 0]
    good_losses = [t for t in good_trades if t['profit'] < 0]
    bad_wins = [t for t in bad_trades if t['profit'] > 0]
    bad_losses = [t for t in bad_trades if t['profit'] < 0]

    good_wr = len(good_wins)/len(good_trades)*100
    bad_wr = len(bad_wins)/len(bad_trades)*100

    good_exits = Counter(t['exit_reason'] for t in good_trades)
    bad_exits = Counter(t['exit_reason'] for t in bad_trades)
    good_loss_exits = Counter(t['exit_reason'] for t in good_losses)
    bad_loss_exits = Counter(t['exit_reason'] for t in bad_losses)

    print(f"\n  好月: {len(good_trades)}t, WR={good_wr:.1f}%")
    print(f"  坏月: {len(bad_trades)}t, WR={bad_wr:.1f}%")

    print(f"\n  出场原因对比:")
    print(f"  {'原因':<25} {'好月(总计)':>12} {'坏月(总计)':>12} {'好月(亏损)':>12} {'坏月(亏损)':>12}")
    all_reasons = set(list(good_exits.keys()) + list(bad_exits.keys()))
    for reason in sorted(all_reasons):
        g = good_exits.get(reason, 0)
        b = bad_exits.get(reason, 0)
        gl = good_loss_exits.get(reason, 0)
        bl = bad_loss_exits.get(reason, 0)
        flag = " ← ⚠️" if bl > gl * 1.5 else ""
        print(f"  {reason:<25} {g:>12} {b:>12} {gl:>12} {bl:>12}{flag}")

    print(f"\n  好月 Avg Win: ${sum(t['profit'] for t in good_wins)/len(good_wins):.2f}" if good_wins else "")
    print(f"  好月 Avg Loss: ${sum(t['profit'] for t in good_losses)/len(good_losses):.2f}" if good_losses else "")
    print(f"  坏月 Avg Win: ${sum(t['profit'] for t in bad_wins)/len(bad_wins):.2f}" if bad_wins else "")
    print(f"  坏月 Avg Loss: ${sum(t['profit'] for t in bad_losses)/len(bad_losses):.2f}" if bad_losses else "")

    # Avg lot comparison
    good_avg_lot = sum(t['lot'] for t in good_trades)/len(good_trades)
    bad_avg_lot = sum(t['lot'] for t in bad_trades)/len(bad_trades)
    print(f"\n  好月 Avg Lot: {good_avg_lot:.3f}, 坏月 Avg Lot: {bad_avg_lot:.3f}")

print(f"\n诊断完成!")
