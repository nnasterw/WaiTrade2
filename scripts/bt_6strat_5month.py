#!/usr/bin/env python3
"""回测6策略(Q2/QS3/QS4 × OFF/NOISE) × 2025年1-5月对比"""
import os, subprocess, time, re, sys, shutil
from pathlib import Path
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from bt_shared import run_bt_silent, kill_mt5

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

DEPOSIT = 200
SYMBOL = 'XAUUSDm'

MONTHS = [
    ('2026-01', '2026.01.01', '2026.01.31'),
    ('2026-02', '2026.02.01', '2026.02.28'),
    ('2026-03', '2026.03.01', '2026.03.31'),
    ('2026-04', '2026.04.01', '2026.04.30'),
    ('2026-05', '2026.05.01', '2026.05.31'),
]

STRATEGIES = [
    ('q2',       'v11xau-qs2.set',       'Q2'),
    ('qs3',      'v11xau-qs3.set',       'QS3'),
    ('qs4',      'v11xau-qs4.set',       'QS4'),
    ('q2_noise',  'v11xau-qs2-noise.set',  'Q2+NOISE'),
    ('qs3_noise', 'v11xau-qs3-noise.set',  'QS3+NOISE'),
    ('qs4_noise', 'v11xau-qs4-noise.set',  'QS4+NOISE'),
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRESETS_DIR = PROJECT_ROOT / 'mql5' / 'Presets'
MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'

def copy_sets():
    """Copy all required .set files to MT5 Tester directory."""
    MT5_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    for _, set_name, _ in STRATEGIES:
        src = PRESETS_DIR / set_name
        dst = MT5_PROFILES_DIR / set_name
        if src.exists():
            shutil.copy2(str(src), str(dst))
        else:
            print(f"  WARNING: {set_name} not found in Presets!")
    print(f"  .set 文件已同步到 MT5 Tester 目录\n")

# kill_mt5 from bt_shared

def run_backtest(name, set_name, date_from, date_to):
    return run_bt_silent(name, set_name, df, dt, deposit=DEPOSIT)

def parse_report(htm_path, elapsed):
    raw = htm_path.read_bytes()
    html = raw.decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    trades = []
    for row_html in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html)
        if len(cells) == 13 and cells[3] != 'balance' and cells[4].strip() == 'out':
            try:
                p = float(cells[10].strip().replace(' ', '').replace(',', ''))
                trades.append(p)
            except:
                pass
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    gw = sum(wins) if wins else 0
    gl = abs(sum(losses)) if losses else 0
    pf = gw / gl if gl > 0 else (999 if gw > 0 else 0)
    wr = len(wins) / len(trades) * 100 if trades else 0
    return {
        'count': len(trades), 'pnl': sum(trades), 'wins': len(wins), 'losses': len(losses),
        'wr': wr, 'pf': pf, 'gross_w': gw, 'gross_l': gl,
        'balance': DEPOSIT + sum(trades), 'elapsed': elapsed,
    }

# --- MAIN ---
total = len(STRATEGIES) * len(MONTHS)
print(f"\n{'='*65}")
print(f"  6策略 × 5个月 = {total} 回测 (2026年1-5月, ${DEPOSIT}初始)")
print(f"{'='*65}\n")

copy_sets()

results = {}
done = 0
for s_key, s_set, s_label in STRATEGIES:
    for m_label, m_from, m_to in MONTHS:
        done += 1
        name = f'bt6x5_26_{s_key}_{m_label}'
        key = f'{s_key}_{m_label}'
        print(f'[{done}/{total}] {s_label:>12} {m_label} ', end='', flush=True)
        kill_mt5()
        r = run_backtest(name, s_set, m_from, m_to)
        results[key] = r
        if r:
            print(f' {r["count"]:>4}T  WR={r["wr"]:.0f}%  PF={r["pf"]:.2f}  PnL=${r["pnl"]:+.2f}  ({r["elapsed"]:.0f}s)')
        else:
            print(' FAILED')

# --- SUMMARY: Monthly comparison ---
S_KEYS = [s[0] for s in STRATEGIES]
S_LABELS = [s[2] for s in STRATEGIES]
M_KEYS = [m[0] for m in MONTHS]
MONTH_CN = {'2026-01':'1月','2026-02':'2月','2026-03':'3月','2026-04':'4月','2026-05':'5月'}

# Table 1: Monthly PnL
print(f"\n\n{'='*120}")
print(f"  月净盈亏对比 (2026年, ${DEPOSIT}初始)")
print(f"{'='*120}")
print(f"\n{'月份':<8}", end='')
for lbl in S_LABELS:
    print(f" | {lbl:>18}", end='')
print()
print('-' * (8 + 21 * len(S_LABELS)))

monthly_totals = {k: {'pnl': 0, 'trades': 0, 'wins': 0, 'losses': 0} for k in S_KEYS}
for m_key in M_KEYS:
    print(f"{MONTH_CN[m_key]:<8}", end='')
    for s_key in S_KEYS:
        r = results.get(f'{s_key}_{m_key}')
        if r:
            print(f" | ${r['pnl']:>16,.2f}", end='')
            monthly_totals[s_key]['pnl'] += r['pnl']
            monthly_totals[s_key]['trades'] += r['count']
            monthly_totals[s_key]['wins'] += r['wins']
            monthly_totals[s_key]['losses'] += r['losses']
        else:
            print(f" | {'FAIL':>18}", end='')
    print()

# Totals row
print('-' * (8 + 21 * len(S_LABELS)))
print(f"{'合计':<8}", end='')
for s_key in S_KEYS:
    print(f" | ${monthly_totals[s_key]['pnl']:>16,.2f}", end='')
print()

# Table 2: Monthly balance (cumulative)
print(f"\n\n{'='*120}")
print(f"  月度余额曲线 (连续复利, ${DEPOSIT}初始)")
print(f"{'='*120}")
print(f"\n{'月份':<8}", end='')
for lbl in S_LABELS:
    print(f" | {lbl:>12}", end='')
print()
print('-' * (8 + 15 * len(S_LABELS)))

running = {k: DEPOSIT for k in S_KEYS}
for m_key in M_KEYS:
    print(f"{MONTH_CN[m_key]:<8}", end='')
    for s_key in S_KEYS:
        r = results.get(f'{s_key}_{m_key}')
        p = r['pnl'] if r else 0
        running[s_key] += p
        print(f" | ${running[s_key]:>10,.0f}", end='')
    print()

# Table 3: 5-month aggregate metrics
print(f"\n\n{'='*120}")
print(f"  5个月汇总对比 (2026.01-2026.05, ${DEPOSIT}初始)")
print(f"{'='*120}")
print(f"\n{'指标':<16}", end='')
for lbl in S_LABELS:
    print(f" | {lbl:>18}", end='')
print(f"\n{'-'*120}")

# Determine best for highlighting
best_pnl = max(monthly_totals[k]['pnl'] for k in S_KEYS)
best_pf = max(
    (monthly_totals[k]['wins'] / max(monthly_totals[k]['losses'], 1)) if monthly_totals[k]['losses'] else 999
    for k in S_KEYS
)

for metric_label, attr in [
    ('总交易数', 'trades'),
    ('总胜率(%)', 'wr_derived'),
    ('盈亏比(PF)', 'pf_derived'),
    ('净盈亏($)', 'pnl'),
]:
    print(f"{metric_label:<16}", end='')
    best_val = -999999
    best_key = None
    if attr == 'pnl':
        best_key = max(monthly_totals, key=lambda k: monthly_totals[k]['pnl'])
    elif attr == 'pf_derived':
        best_key = max(monthly_totals, key=lambda k: (
            monthly_totals[k]['wins'] / max(monthly_totals[k]['losses'], 1)) if monthly_totals[k]['losses'] else 999)

    for s_key in S_KEYS:
        t = monthly_totals[s_key]
        if attr == 'trades':
            val = f"{t['trades']:>17,}"
        elif attr == 'wr_derived':
            total_t = t['wins'] + t['losses']
            wr = t['wins'] / total_t * 100 if total_t > 0 else 0
            val = f"{wr:>17.1f}%"
        elif attr == 'pf_derived':
            pf = t['wins'] / max(t['losses'], 1) if t['losses'] else (999 if t['wins'] else 0)
            mark = ' *' if s_key == best_key else ''
            val = f"{pf:>16.2f}{mark}"
        elif attr == 'pnl':
            mark = ' *' if s_key == best_key else ''
            val = f"${t['pnl']:>16,.2f}{mark}"
        print(f" | {val}", end='')
    print()

print(f"\n{'初始资金($)':<16}", end='')
for _ in S_KEYS:
    print(f" | ${DEPOSIT:>17}", end='')
print()

# Monthly per-strategy detail
print(f"\n\n{'='*120}")
print(f"  各策略月度明细")
print(f"{'='*120}")
for s_key, s_set, s_label in STRATEGIES:
    print(f"\n--- {s_label} ---")
    print(f"  {'月份':<8} {'交易':>5} {'胜':>4} {'负':>4} {'胜率':>7} {'PF':>6} {'PnL':>10} {'余额':>10}")
    print(f"  {'-'*60}")
    bal = DEPOSIT
    for m_key in M_KEYS:
        r = results.get(f'{s_key}_{m_key}')
        if r:
            bal += r['pnl']
            print(f"  {MONTH_CN[m_key]:<8} {r['count']:>5} {r['wins']:>4} {r['losses']:>4} "
                  f"{r['wr']:>6.1f}% {r['pf']:>5.2f} "
                  f"${r['pnl']:>9,.2f} ${bal:>9,.0f}")
        else:
            print(f"  {MONTH_CN[m_key]:<8} FAILED")

print(f"\n[DONE] {done}/{total} completed")

# --- CHART: Monthly balance curve ---
print(f"\n生成折线图...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Color scheme
COLORS = {
    'q2': '#2196F3', 'qs3': '#4CAF50', 'qs4': '#FF9800',
    'q2_noise': '#90CAF9', 'qs3_noise': '#A5D6A7', 'qs4_noise': '#FFCC80',
}
STYLES = {
    'q2': '-', 'qs3': '-', 'qs4': '-',
    'q2_noise': '--', 'qs3_noise': '--', 'qs4_noise': '--',
}
LW = {'q2': 2, 'qs3': 2.5, 'qs4': 2,
      'q2_noise': 1.5, 'qs3_noise': 1.5, 'qs4_noise': 1.5}

x_labels = [MONTH_CN[m] for m in M_KEYS]
x = list(range(len(x_labels)))

# Panel 1: All 6 strategies (split scale for readability)
for s_key, _, s_label in STRATEGIES:
    balances = [DEPOSIT]
    for m_key in M_KEYS:
        r = results.get(f'{s_key}_{m_key}')
        balances.append(balances[-1] + (r['pnl'] if r else 0))
    ax1.plot([0] + [i+1 for i in x], balances,
             color=COLORS[s_key], linestyle=STYLES[s_key],
             linewidth=LW[s_key], marker='o', markersize=5, label=s_label)

ax1.axhline(y=DEPOSIT, color='gray', linestyle=':', alpha=0.5)
ax1.set_title('2026 Jan-May Balance Curve (all strategies)', fontsize=13, fontweight='bold')
ax1.set_xlabel('Month')
ax1.set_ylabel('Balance ($)')
ax1.set_xticks([0] + [i+1 for i in x])
ax1.set_xticklabels(['Start'] + x_labels)
ax1.legend(fontsize=8, loc='upper left')
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'${v:,.0f}'))
ax1.grid(True, alpha=0.3)

# Panel 2: OFF strategies only (linear scale)
for s_key, _, s_label in STRATEGIES:
    if 'noise' in s_key:
        continue
    balances = [DEPOSIT]
    for m_key in M_KEYS:
        r = results.get(f'{s_key}_{m_key}')
        balances.append(balances[-1] + (r['pnl'] if r else 0))
    ax2.plot([0] + [i+1 for i in x], balances,
             color=COLORS[s_key], linewidth=2.5, marker='o',
             markersize=7, label=s_label)

# Add NOISE variants on secondary y-axis for panel 2
ax2b = ax2.twinx()
for s_key, _, s_label in STRATEGIES:
    if 'noise' not in s_key:
        continue
    balances = [DEPOSIT]
    for m_key in M_KEYS:
        r = results.get(f'{s_key}_{m_key}')
        balances.append(balances[-1] + (r['pnl'] if r else 0))
    ax2b.plot([0] + [i+1 for i in x], balances,
              color=COLORS[s_key], linestyle='--', linewidth=1.5,
              marker='s', markersize=4, label=s_label)

ax2.axhline(y=DEPOSIT, color='gray', linestyle=':', alpha=0.5)
ax2.set_title('2026 Jan-May Balance (OFF vs NOISE split scale)', fontsize=13, fontweight='bold')
ax2.set_xlabel('Month')
ax2.set_ylabel('OFF Balance ($)')
ax2b.set_ylabel('NOISE Balance ($)')
ax2.set_xticks([0] + [i+1 for i in x])
ax2.set_xticklabels(['Start'] + x_labels)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'${v:,.0f}'))
ax2b.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'${v:,.0f}'))
ax2.grid(True, alpha=0.3)

# Combined legend
lines1 = ax2.get_lines() + ax2b.get_lines()
labels1 = [l.get_label() for l in lines1]
ax2.legend(lines1, labels1, fontsize=8, loc='upper left')

plt.tight_layout()
chart_path = PROJECT_ROOT / 'results' / 'bt_6x5_2026_balance.png'
chart_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(str(chart_path), dpi=150, bbox_inches='tight')
print(f"  图表已保存: {chart_path}")
plt.close()
