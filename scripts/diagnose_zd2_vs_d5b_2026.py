#!/usr/bin/env python3
"""/diagnose: ZD2 vs D5B 2026年对比 — 排查方向偏差 + 体制切换信号"""
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

# ── 测试月份 ──────────────────────────────────────────────────
MONTHS = [
    ("2025.10.01", "2025.10.31", "2025-10_good"),
    ("2026.01.01", "2026.01.31", "2026-01"),
    ("2026.02.01", "2026.02.28", "2026-02"),
    ("2026.03.01", "2026.03.31", "2026-03"),
    ("2026.04.01", "2026.04.30", "2026-04"),
    ("2026.05.01", "2026.05.31", "2026-05"),
]

# ── 策略定义 ──────────────────────────────────────────────────
# Use existing .set files directly (no modification needed)
STRATEGIES = {
    'ZD2': {
        'set_file': ROOT / 'mql5' / 'Presets' / 'V11XAU-ZD2.set',
        'version': 'V11XAU-ZD2',
        'label': 'ZD2振荡',
    },
    'D5B': {
        'set_file': None,  # Will create from QS3 base
        'version': 'V11XAU-QS3-D5B',
        'label': 'D5B趋势',
    },
}

def create_d5b_set():
    """Create D5B .set from QS3 baseline"""
    base = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'
    dst = MT5_PROFILES_DIR / 'v11xau-d5b-diag2.set'
    content = base.read_text(encoding='utf-8')
    overrides = {
        'InpVersion': 'V11XAU-QS3-D5B-DIAG2',
        'InpMagicNumber': '204866',
        'InpBouncePct': '0.30',
        'InpBounceSweetMinPct': '0.35',
        'InpOutsideBounceSweetMult': '0.4',
        'InpMaxCounterRiskATR': '0.5',
        'InpMaxEntriesPerOB': '2',
        'InpEnableDeepestPullbackSL': 'true',
        'InpDeepestPullbackBuffer': '0.5',
        'InpEnableEntryDebug': 'true',
    }
    for key, val in overrides.items():
        pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(f'{key}={val}', content)
        else:
            content += f'\n{key}={val}\n'
    dst.write_text(content)
    return dst

def kill_mt5_tester():
    try:
        subprocess.run(['powershell', '-Command',
            "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"
        ], capture_output=True, timeout=10)
    except: pass
    time.sleep(3)

def run_bt(set_name, date_from, date_to, timeout=180):
    ini_file = MT5_TESTER_DIR / 'backtest.ini'
    today_str = datetime.now().strftime('%Y%m%d')
    report_name = f'diag2_{set_name}_{today_str}'

    ini_content = f"""[Common]
Login=
Server=

[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters={set_name}.set
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
    for old in MT5_DATA.glob(f'diag2_{set_name}*.htm'):
        try: old.unlink()
        except: pass

    subprocess.Popen([MT5_TERMINAL, f'/config:{ini_file}'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for i in range(timeout // 5):
        time.sleep(5)
        try:
            result = subprocess.run(['powershell', '-Command',
                "(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
                "Where-Object { $_.Path -like '*Program Files*' }).Count"
            ], capture_output=True, text=True, timeout=5)
            if result.stdout.strip() == '0':
                break
        except: pass
    time.sleep(2)

    html_files = sorted(MT5_DATA.glob(f'diag2_{set_name}*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not html_files:
        return None
    return html_files[0]

def parse_trades(html_path):
    """Extract trades with direction, profit, exit reason"""
    raw = html_path.read_bytes()
    try:
        text = raw.decode('utf-16-le')
    except:
        text = raw.decode('utf-8', errors='ignore')

    lines = text.split('\n')
    trades = []
    open_positions = {}

    for line in lines:
        if 'XAUUSDm' not in line:
            continue
        clean = re.sub(r'<[^>]+>', ' | ', line).strip()
        parts = [p.strip() for p in clean.split('|')]
        non_empty = [p for p in parts if p]

        try: sym_idx = non_empty.index('XAUUSDm')
        except ValueError: continue

        if sym_idx + 4 >= len(non_empty): continue

        direction = non_empty[sym_idx + 1]
        inout = non_empty[sym_idx + 2]
        if inout not in ('in', 'out'): continue

        try: deal_num = int(non_empty[sym_idx - 1]) if sym_idx > 0 else 0
        except: continue

        if inout == 'in':
            try:
                lot = float(non_empty[sym_idx + 3])
                price = float(non_empty[sym_idx + 4])
                comment = non_empty[-1] if non_empty[-1] != 'XAUUSDm' else ''
                time_str = non_empty[0]
                open_positions[deal_num] = {
                    'time': time_str, 'direction': direction,
                    'lot': lot, 'entry_price': price, 'comment': comment,
                }
            except: pass
        elif inout == 'out':
            try:
                exit_price = float(non_empty[sym_idx + 4])
                profit = float(non_empty[-3].replace(' ', ''))
                balance = float(non_empty[-2].replace(' ', ''))
                exit_reason = non_empty[-1] if non_empty[-1] not in ('XAUUSDm', '') else 'unknown'
                entry_info = None
                for dnum in sorted(open_positions.keys()):
                    if open_positions[dnum]['direction'] != direction:
                        entry_info = open_positions.pop(dnum)
                        break
                time_str = non_empty[0]
                trades.append({
                    'time': time_str, 'direction': direction,
                    'profit': profit, 'balance': balance,
                    'exit_reason': exit_reason,
                    'lot': entry_info['lot'] if entry_info else 0,
                    'entry_comment': entry_info['comment'] if entry_info else '',
                })
            except: pass

    return trades

# ── Main ──────────────────────────────────────────────────────
print("=" * 70)
print("  /diagnose: ZD2 vs D5B 2026年方向+体制对比诊断")
print("=" * 70)

# Create D5B .set
create_d5b_set()

# Copy ZD2 .set to profiles dir
import shutil
zd2_src = ROOT / 'mql5' / 'Presets' / 'V11XAU-ZD2.set'
zd2_dst = MT5_PROFILES_DIR / 'v11xau-zd2-diag.set'
shutil.copy(zd2_src, zd2_dst)

all_data = {}  # {strategy: {month_label: [trades]}}

for sname, sinfo in [('ZD2', {'set_name': 'v11xau-zd2-diag'}), ('D5B', {'set_name': 'v11xau-d5b-diag2'})]:
    print(f"\n{'─'*50}")
    print(f"  {STRATEGIES[sname]['label']}")
    print(f"{'─'*50}")
    all_data[sname] = {}

    for date_from, date_to, label in MONTHS:
        print(f"  {label} ", end='', flush=True)
        html = run_bt(sinfo['set_name'], date_from, date_to)
        if html:
            trades = parse_trades(html)
            all_data[sname][label] = trades

            wins = [t for t in trades if t['profit'] > 0]
            losses = [t for t in trades if t['profit'] < 0]
            wr = len(wins)/len(trades)*100 if trades else 0
            bal = trades[-1]['balance'] if trades else 0

            # Direction breakdown
            buys = [t for t in trades if t['direction'] == 'buy']
            sells = [t for t in trades if t['direction'] == 'sell']
            buy_wr = len([t for t in buys if t['profit']>0])/len(buys)*100 if buys else 0
            sell_wr = len([t for t in sells if t['profit']>0])/len(sells)*100 if sells else 0

            # Exit reasons
            exit_counts = Counter(t['exit_reason'] for t in trades)
            top_exits = exit_counts.most_common(5)

            print(f"{len(trades):>4}t {wr:>5.1f}% ${bal:>9.2f} B:{buy_wr:.0f}%({len(buys)}) S:{sell_wr:.0f}%({len(sells)}) "
                  f"Exits:{','.join(f'{r}={c}' for r,c in top_exits[:3])}")
        else:
            print(f"FAILED")
            all_data[sname][label] = []

# ── Comparison Analysis ───────────────────────────────────────
print(f"\n{'='*70}")
print(f"  逐月对比: ZD2 vs D5B")
print(f"{'='*70}")
print(f"{'月份':<16} {'ZD2交易':>8} {'ZD2 WR':>7} {'ZD2余额':>10} | {'D5B交易':>8} {'D5B WR':>7} {'D5B余额':>10} | {'优胜':>6}")
print("-" * 75)

for _, _, label in MONTHS:
    zd2_trades = all_data.get('ZD2', {}).get(label, [])
    d5b_trades = all_data.get('D5B', {}).get(label, [])

    if zd2_trades and d5b_trades:
        zd2_wins = [t for t in zd2_trades if t['profit'] > 0]
        zd2_wr = len(zd2_wins)/len(zd2_trades)*100
        zd2_bal = zd2_trades[-1]['balance']

        d5b_wins = [t for t in d5b_trades if t['profit'] > 0]
        d5b_wr = len(d5b_wins)/len(d5b_trades)*100
        d5b_bal = d5b_trades[-1]['balance']

        winner = 'ZD2' if zd2_bal > d5b_bal else 'D5B'
        print(f"{label:<16} {len(zd2_trades):>8} {zd2_wr:>6.1f}% ${zd2_bal:>9.2f} | {len(d5b_trades):>8} {d5b_wr:>6.1f}% ${d5b_bal:>9.2f} | {winner:>6}")
    else:
        print(f"{label:<16} {'N/A':>8} {'N/A':>7} {'N/A':>10} | {'N/A':>8} {'N/A':>7} {'N/A':>10} |")

# ── WR Divergence Analysis ────────────────────────────────────
print(f"\n{'='*70}")
print(f"  WR背离分析 (寻找切换信号)")
print(f"{'='*70}")

for _, _, label in MONTHS:
    zd2_trades = all_data.get('ZD2', {}).get(label, [])
    d5b_trades = all_data.get('D5B', {}).get(label, [])

    if not zd2_trades or not d5b_trades:
        continue

    # Rolling 10-trade WR for both
    zd2_rolling = []
    d5b_rolling = []
    for trades_list, rolling_list in [(zd2_trades, zd2_rolling), (d5b_trades, d5b_rolling)]:
        window = 10
        for i in range(window, len(trades_list)+1):
            w = sum(1 for t in trades_list[i-window:i] if t['profit'] > 0)
            rolling_list.append((i, w/window*100))

    # Find first point where D5B rolling WR drops below 50% and ZD2 stays above
    switch_signals = []
    for (i_d, wr_d), (i_z, wr_z) in zip(d5b_rolling[::5], zd2_rolling[::5] if len(zd2_rolling) >= len(d5b_rolling) else zd2_rolling):
        if wr_d < 50 and wr_z > 50:
            switch_signals.append(i_d)

    # Find sustained divergence: D5B < 50% for 20+ trades while ZD2 > 60%
    d5b_below_50 = 0
    for i, wr in d5b_rolling:
        if wr < 50:
            d5b_below_50 += 1
    d5b_pct_below = d5b_below_50 / len(d5b_rolling) * 100 if d5b_rolling else 0

    zd2_above_60 = sum(1 for _, wr in zd2_rolling if wr > 60)
    zd2_pct_above = zd2_above_60 / len(zd2_rolling) * 100 if zd2_rolling else 0

    print(f"  {label}: D5B rolling WR<50%: {d5b_pct_below:.0f}% of time, "
          f"ZD2 rolling WR>60%: {zd2_pct_above:.0f}% of time"
          f"  | Switch signals: {len(switch_signals)}")

# ── Exit Reason Comparison ────────────────────────────────────
print(f"\n{'='*70}")
print(f"  出场原因对比: 2025-10(好月) vs 2026(坏月)")
print(f"{'='*70}")

for label in ['2025-10_good'] + [l for _,_,l in MONTHS if '2026' in l]:
    for sname in ['ZD2', 'D5B']:
        trades = all_data.get(sname, {}).get(label, [])
        if not trades:
            continue
        exits = Counter(t['exit_reason'] for t in trades if t['profit'] < 0)  # loss exits only
        top3 = exits.most_common(3)
        wr = len([t for t in trades if t['profit']>0])/len(trades)*100 if trades else 0
        print(f"  {label} {sname}: WR={wr:.1f}%, 亏损Top3: {top3}")

# ── Cleanup ───────────────────────────────────────────────────
for f in MT5_PROFILES_DIR.glob('v11xau-d5b-diag2*'):
    try: f.unlink()
    except: pass
for f in MT5_PROFILES_DIR.glob('v11xau-zd2-diag*'):
    try: f.unlink()
    except: pass

print(f"\n诊断完成!")
