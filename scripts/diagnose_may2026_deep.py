#!/usr/bin/env python3
"""/diagnose: 2026-05 D5B 逐日/逐时/方向/OB 深度交易诊断"""
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

def replace_param(content, key, val):
    pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
    if pattern.search(content): return pattern.sub(f'{key}={val}', content)
    return content + f'\n{key}={val}\n'

def make_set():
    dst = MT5_PROFILES_DIR / 'v11xau-d5b-may-diag.set'
    content = BASE_SET.read_text(encoding='utf-8')
    content = replace_param(content, 'InpVersion', 'V11XAU-D5B-MAY-DIAG')
    content = replace_param(content, 'InpMagicNumber', '204866')
    content = replace_param(content, 'InpEnableEntryDebug', 'true')
    content = replace_param(content, 'InpEnableExitDebug', 'true')
    for key, val in D5B_PARAMS.items():
        content = replace_param(content, key, val)
    dst.write_text(content)

def kill_mt5_tester():
    try:
        subprocess.run(['powershell', '-Command',
            "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"
        ], capture_output=True, timeout=10)
    except: pass
    time.sleep(3)

def run_bt(date_from, date_to, timeout=300):
    ini_file = MT5_TESTER_DIR / 'backtest.ini'
    today_str = datetime.now().strftime('%Y%m%d')
    ini_content = f"""[Common]
Login=
Server=
[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters=v11xau-d5b-may-diag.set
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
Report=d5b_may_diag_{today_str}
"""
    ini_file.write_text(ini_content)
    kill_mt5_tester()
    for old in MT5_DATA.glob('d5b_may_diag*.htm'):
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
            if result.stdout.strip() == '0': break
        except: pass
    time.sleep(2)
    html_files = sorted(MT5_DATA.glob('d5b_may_diag*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    return html_files[0] if html_files else None

def parse_trades_detailed(html_path):
    """Extract every trade with timestamp, direction, profit, exit_reason, entry_comment (pos_mult)"""
    raw = html_path.read_bytes()
    try: text = raw.decode('utf-16-le')
    except: text = raw.decode('utf-8', errors='ignore')
    lines = text.split('\n')
    trades = []
    open_positions = {}
    for line in lines:
        if 'XAUUSDm' not in line: continue
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
                open_positions[deal_num] = {'time': time_str, 'direction': direction,
                    'lot': lot, 'entry_price': price, 'comment': comment}
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
                        entry_info = open_positions.pop(dnum); break
                time_str = non_empty[0]
                # Parse pos_mult from entry comment (e.g., "WT V11XAU-... S x2.3")
                pos_mult = 1.0
                mult_m = re.search(r'x([\d.]+)$', entry_info['comment'] if entry_info else '')
                if mult_m: pos_mult = float(mult_m.group(1))
                trades.append({
                    'time': time_str, 'direction': direction,
                    'profit': profit, 'balance': balance,
                    'exit_reason': exit_reason,
                    'lot': entry_info['lot'] if entry_info else 0,
                    'pos_mult': pos_mult,
                    'entry_price': entry_info['entry_price'] if entry_info else 0,
                    'exit_price': exit_price,
                })
            except: pass
    return trades

# ── Phase 1+2: Reproduce the failure ─────────────────────────
print("=" * 70)
print("  /diagnose: 2026-05 D5B 逐日趋势+OB深度诊断")
print("=" * 70)

print("\n[Phase 1-2] 复现2026-05崩溃...")
make_set()
html = run_bt("2026.05.01", "2026.05.31")
if not html:
    print("FAILED to run backtest!")
    sys.exit(1)

trades = parse_trades_detailed(html)
print(f"提取 {len(trades)} 笔交易")

# ── Phase 3: Hypothesize ─────────────────────────────────────
print("""
[Phase 3] 假设排序:

H1: 5月有好日子和毒日子混合 — 毒日子的连续亏损簇吞噬好日子利润
  预测: 按日分组后,某些天WR<30%且大亏,某些天WR>60%且盈利

H2: 趋势方向在月内频繁切换 — 状态过滤器追逐错误方向导致双杀
  预测: Buy/Sell WR在不同周之间有显著差异

H3: 特定时段(如亚洲盘)是毒时段 — 某些小时的交易系统性地亏损
  预测: 按小时分组后,某些时段的WR显著低于其他时段

H4: OB反弹质量随时间衰减 — 月初的OB比月底的OB更可靠
  预测: 按周分组,WR逐周递减

H5: 高pos_mult交易集中在亏损簇中 — 评分系统在FAIL日子给了FAIL交易更高倍率
  预测: 亏损交易的avg pos_mult > 盈利交易的avg pos_mult
""")

# ── Phase 4: Instrument ───────────────────────────────────────
print("=" * 70)
print("[Phase 4] 逐维度分析")

# --- H1: Daily breakdown ---
print(f"\n{'─'*60}")
print("H1: 逐日分析")
print(f"{'─'*60}")

daily = defaultdict(list)
for t in trades:
    day = t['time'][:10]  # "2026.05.01"
    daily[day].append(t)

print(f"{'日期':<12} {'交易':>5} {'WR':>7} {'盈亏':>10} {'余额':>10} {'方向B/S':>12} {'最大连亏':>6}")
print("-" *70)

all_days = sorted(daily.keys())
toxic_days = []
good_days = []

for day in all_days:
    day_trades = daily[day]
    wins = [t for t in day_trades if t['profit'] > 0]
    losses = [t for t in day_trades if t['profit'] < 0]
    wr = len(wins)/len(day_trades)*100 if day_trades else 0
    pnl = sum(t['profit'] for t in day_trades)
    bal = day_trades[-1]['balance'] if day_trades else 0

    buys = len([t for t in day_trades if t['direction']=='buy'])
    sells = len([t for t in day_trades if t['direction']=='sell'])
    buy_wr = len([t for t in day_trades if t['direction']=='buy' and t['profit']>0])/max(1,buys)*100
    sell_wr = len([t for t in day_trades if t['direction']=='sell' and t['profit']>0])/max(1,sells)*100

    # Max consecutive losses
    max_cl = 0; cl = 0
    for t in day_trades:
        if t['profit'] < 0: cl += 1
        else: max_cl = max(max_cl, cl); cl = 0
    max_cl = max(max_cl, cl)

    marker = ""
    if wr < 35 and len(day_trades) >= 5: marker = " TOXIC"; toxic_days.append(day)
    elif wr > 60 and len(day_trades) >= 5: marker = " GOOD"; good_days.append(day)

    print(f"{day:<12} {len(day_trades):>5} {wr:>6.1f}% ${pnl:>9.2f} ${bal:>9.2f} B:{buy_wr:.0f}%({buys})S:{sell_wr:.0f}%({sells}) {max_cl:>4}L{marker}")

# --- Daily summary ---
toxic_pnl = sum(sum(t['profit'] for t in daily[d]) for d in toxic_days)
good_pnl = sum(sum(t['profit'] for t in daily[d]) for d in good_days)
print(f"\n毒日({len(toxic_days)}天): {toxic_days}  总盈亏: ${toxic_pnl:.2f}")
print(f"好日({len(good_days)}天): {good_days}  总盈亏: ${good_pnl:.2f}")
print(f"毒日占比: {len(toxic_days)}/{len(all_days)} = {len(toxic_days)/len(all_days)*100:.0f}%")

# --- H2: Weekly trend direction ---
print(f"\n{'─'*60}")
print("H2: 逐周趋势方向分析")
print(f"{'─'*60}")

# Define weeks of May 2026
weeks = [
    ("W1:05.01-07", "2026.05.01", "2026.05.07"),
    ("W2:05.08-14", "2026.05.08", "2026.05.14"),
    ("W3:05.15-21", "2026.05.15", "2026.05.21"),
    ("W4:05.22-31", "2026.05.22", "2026.05.31"),
]

for wname, wstart, wend in weeks:
    w_trades = [t for t in trades if wstart <= t['time'][:10] <= wend]
    if not w_trades: continue
    wins = [t for t in w_trades if t['profit'] > 0]
    wr = len(wins)/len(w_trades)*100
    pnl = sum(t['profit'] for t in w_trades)
    buys = [t for t in w_trades if t['direction']=='buy']
    sells = [t for t in w_trades if t['direction']=='sell']
    buy_wr = len([t for t in buys if t['profit']>0])/len(buys)*100 if buys else 0
    sell_wr = len([t for t in sells if t['profit']>0])/len(sells)*100 if sells else 0

    # What exit reasons dominate?
    exits = Counter(t['exit_reason'] for t in w_trades if t['profit'] < 0)
    top_exits = exits.most_common(3)

    # Avg pos_mult
    avg_mult = sum(t['pos_mult'] for t in w_trades)/len(w_trades)

    print(f"  {wname}: {len(w_trades):>3}t WR={wr:.1f}% PnL=${pnl:.1f} "
          f"B:{buy_wr:.0f}%({len(buys)}) S:{sell_wr:.0f}%({len(sells)}) "
          f"avgMult={avg_mult:.2f} 亏损Top3:{top_exits}")

# --- H3: Hourly analysis ---
print(f"\n{'─'*60}")
print("H3: 逐小时分析 (UTC, MT5时间)")
print(f"{'─'*60}")

hourly = defaultdict(list)
for t in trades:
    try:
        h = int(t['time'].split(' ')[1].split(':')[0])
        hourly[h].append(t)
    except: pass

print(f"{'小时':<6} {'交易':>5} {'WR':>7} {'盈亏':>10} {'B WR':>7} {'S WR':>7}")
print("-" * 50)
for h in sorted(hourly.keys()):
    h_trades = hourly[h]
    wins = [t for t in h_trades if t['profit'] > 0]
    wr = len(wins)/len(h_trades)*100 if h_trades else 0
    pnl = sum(t['profit'] for t in h_trades)
    buys = [t for t in h_trades if t['direction']=='buy']
    sells = [t for t in h_trades if t['direction']=='sell']
    buy_wr = len([t for t in buys if t['profit']>0])/len(buys)*100 if buys else 0
    sell_wr = len([t for t in sells if t['profit']>0])/len(sells)*100 if sells else 0
    marker = " <-TOXIC" if (wr < 35 and len(h_trades) >= 10) else ""
    print(f"{h:02d}:00  {len(h_trades):>5} {wr:>6.1f}% ${pnl:>9.2f} {buy_wr:>6.1f}% {sell_wr:>6.1f}%{marker}")

# --- H4: Week-over-week WR decay ---
print(f"\n{'─'*60}")
print("H4: 逐周OB质量衰减")
print(f"{'─'*60}")
for wname, wstart, wend in weeks:
    w_trades = [t for t in trades if wstart <= t['time'][:10] <= wend]
    if not w_trades: continue
    wins = [t for t in w_trades if t['profit'] > 0]
    losses = [t for t in w_trades if t['profit'] < 0]
    wr = len(wins)/len(w_trades)*100
    avg_win = sum(t['profit'] for t in wins)/len(wins) if wins else 0
    avg_loss = sum(t['profit'] for t in losses)/len(losses) if losses else 0
    pf = abs(avg_win/avg_loss) if avg_loss != 0 else 0

    # Exit reason breakdown
    exits = Counter(t['exit_reason'] for t in w_trades)
    # Simplify exit reasons
    sl_count = sum(c for r, c in exits.items() if r.startswith('sl'))
    mfe_count = exits.get('mfe_fail', 0)
    dtp_count = exits.get('dtp', 0)
    decay_count = exits.get('decay', 0)

    print(f"  {wname}: WR={wr:.1f}% PF={pf:.2f} AvgW=${avg_win:.1f} AvgL=${avg_loss:.1f}  "
          f"SL:{sl_count} MFE:{mfe_count} DTP:{dtp_count} Decay:{decay_count}")

# --- H5: Position sizing vs outcome ---
print(f"\n{'─'*60}")
print("H5: 仓位倍率 vs 盈亏")
print(f"{'─'*60}")

win_trades = [t for t in trades if t['profit'] > 0]
loss_trades = [t for t in trades if t['profit'] < 0]

win_avg_mult = sum(t['pos_mult'] for t in win_trades)/len(win_trades) if win_trades else 0
loss_avg_mult = sum(t['pos_mult'] for t in loss_trades)/len(loss_trades) if loss_trades else 0

print(f"  盈利交易 avg pos_mult: {win_avg_mult:.2f}")
print(f"  亏损交易 avg pos_mult: {loss_avg_mult:.2f}")
print(f"  差值: {loss_avg_mult - win_avg_mult:+.2f} ", end='')
if loss_avg_mult > win_avg_mult:
    print("<- FAIL交易被放大! 评分系统在FAIL月失效!")
else:
    print("<- OK")

# --- Consecutive loss deep dive ---
print(f"\n{'─'*60}")
print("连续亏损簇深度分析")
print(f"{'─'*60}")

# Find all loss runs >= 5
cl = 0; cl_start = None; cl_trades_list = []
for t in trades:
    if t['profit'] < 0:
        if cl == 0: cl_start = t['time']
        cl += 1
        cl_trades_list.append(t)
    else:
        if cl >= 5:
            cl_pnl = sum(tt['profit'] for tt in cl_trades_list)
            cl_dirs = Counter(tt['direction'] for tt in cl_trades_list)
            cl_reasons = Counter(tt['exit_reason'] for tt in cl_trades_list)
            print(f"  {cl_start} {cl}连亏 ${cl_pnl:.1f} 方向:{dict(cl_dirs)} 原因:{dict(cl_reasons)}")
        cl = 0; cl_start = None; cl_trades_list = []
if cl >= 5:
    cl_pnl = sum(tt['profit'] for tt in cl_trades_list)
    cl_dirs = Counter(tt['direction'] for tt in cl_trades_list)
    print(f"  {cl_start} {cl}连亏 ${cl_pnl:.1f} 方向:{dict(cl_dirs)} 原因:{dict(cl_reasons)}")

# --- Comparison with good windows ---
print(f"\n{'─'*60}")
print("对比: 2026-05全月 vs 0529(2天好窗) vs 0602(1天好窗)")
print(f"{'─'*60}")

# 0529 window trades (May 28-29, 2025) — we don't have live data, use known results
# 0602 window trades (June 2, 2026) — known: 12t, 66.7%, $206
# May 2026 full month: just analyzed

may_total_pnl = sum(t['profit'] for t in trades)
may_total_trades = len(trades)
may_wr = len([t for t in trades if t['profit']>0])/may_total_trades*100

print(f"  2026-05全月: {may_total_trades}t WR={may_wr:.1f}% PnL=${may_total_pnl:.1f}")
print(f"  0529 好窗:   16t WR=75.0% PnL=$20.4 (已知)")
print(f"  0602 好窗:   12t WR=66.7% PnL=$6.2 (已知)")
print(f"")
print(f"  关键差异: 全月有{len(toxic_days)}个毒日,占总交易{sum(len(daily[d]) for d in toxic_days)}笔")
print(f"  毒日交易占比: {sum(len(daily[d]) for d in toxic_days)/may_total_trades*100:.0f}%")
print(f"  毒日盈亏占比: {toxic_pnl/may_total_pnl*100:.0f}% (总亏损的{abs(toxic_pnl)/(abs(toxic_pnl)+good_pnl)*100:.0f}%)")

# Cleanup
for f in MT5_PROFILES_DIR.glob('v11xau-d5b-may-diag*'):
    try: f.unlink()
    except: pass

print(f"\n诊断完成!")
