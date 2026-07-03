#!/usr/bin/env python3
"""/diagnose ultra: 2026-05 趋势方向+OB+出场时机 超深度诊断"""
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

QS4_PARAMS = {  # D5B = QS4
    'InpBouncePct': '0.30', 'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4', 'InpMaxCounterRiskATR': '0.5',
    'InpMaxEntriesPerOB': '2', 'InpEnableDeepestPullbackSL': 'true',
    'InpDeepestPullbackBuffer': '0.5',
}

def replace_param(content, key, val):
    pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
    if pattern.search(content): return pattern.sub(f'{key}={val}', content)
    return content + f'\n{key}={val}\n'

def make_set(name, version, magic, params, extra=None):
    dst = MT5_PROFILES_DIR / f'{name}.set'
    content = BASE_SET.read_text(encoding='utf-8')
    content = replace_param(content, 'InpVersion', version)
    content = replace_param(content, 'InpMagicNumber', str(magic))
    content = replace_param(content, 'InpEnableEntryDebug', 'true')
    content = replace_param(content, 'InpEnableExitDebug', 'true')
    for key, val in params.items():
        content = replace_param(content, key, val)
    if extra:
        for key, val in extra.items():
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

def run_bt(set_filename, date_from, date_to, timeout=300):
    ini_file = MT5_TESTER_DIR / 'backtest.ini'
    today_str = datetime.now().strftime('%Y%m%d')
    ini_content = f"""[Common]
Login=
Server=
[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters={set_filename}
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
Report=ultra_may_{today_str}
"""
    ini_file.write_text(ini_content)
    kill_mt5_tester()
    for old in MT5_DATA.glob('ultra_may*.htm'):
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
    html_files = sorted(MT5_DATA.glob('ultra_may*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    return html_files[0] if html_files else None

def parse_trades_ultra(html_path):
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
        direction = non_empty[sym_idx + 1]; inout = non_empty[sym_idx + 2]
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
                pos_mult = 1.0
                mult_m = re.search(r'x([\d.]+)$', entry_info['comment'] if entry_info else '')
                if mult_m: pos_mult = float(mult_m.group(1))

                # Calculate duration
                try:
                    entry_dt = datetime.strptime(entry_info['time'], '%Y.%m.%d %H:%M:%S')
                    exit_dt = datetime.strptime(time_str, '%Y.%m.%d %H:%M:%S')
                    duration_min = (exit_dt - entry_dt).total_seconds() / 60
                except: duration_min = 0

                # Calculate R-multiple (profit relative to risk = lot * price distance)
                entry_price = entry_info['entry_price'] if entry_info else 0
                if entry_price > 0 and exit_price > 0:
                    if direction == 'buy':
                        r_mult = (exit_price - entry_price) / (entry_price * 0.001) * 100
                    else:
                        r_mult = (entry_price - exit_price) / (entry_price * 0.001) * 100
                else: r_mult = 0

                trades.append({
                    'time': time_str, 'direction': direction,
                    'profit': profit, 'balance': balance,
                    'exit_reason': exit_reason, 'lot': lot,
                    'pos_mult': pos_mult, 'duration_min': duration_min,
                    'r_mult': r_mult,
                    'entry_price': entry_price, 'exit_price': exit_price,
                })
            except: pass
    return trades

# ── Phase 1-2: Reproduce ─────────────────────────────────────
print("=" * 70)
print("  /diagnose ultra: QS4(D5B) 2026-05 趋势+OB+出场深度诊断")
print("=" * 70)

print("\n[Phase 1-2] QS4 2026-05 复现...")
make_set('v11xau-qs4-may', 'V11XAU-QS4-MAY', 204866, QS4_PARAMS)
html = run_bt('v11xau-qs4-may.set', "2026.05.01", "2026.05.31")
if not html: print("FAILED"); sys.exit(1)
trades = parse_trades_ultra(html)
print(f"提取 {len(trades)} 笔交易")

# ── H1: Trade duration & R-multiple ───────────────────────────
print(f"\n{'='*60}")
print("H1: 持仓时长 vs 盈亏")
wins = [t for t in trades if t['profit'] > 0]
losses = [t for t in trades if t['profit'] < 0]
win_dur = sum(t['duration_min'] for t in wins)/len(wins) if wins else 0
loss_dur = sum(t['duration_min'] for t in losses)/len(losses) if losses else 0
print(f"  盈利交易: avg持仓={win_dur:.0f}min, avg R={sum(t['r_mult'] for t in wins)/len(wins):.2f}" if wins else "")
print(f"  亏损交易: avg持仓={loss_dur:.0f}min, avg R={sum(t['r_mult'] for t in losses)/len(losses):.2f}" if losses else "")

# --- Duration buckets ---
buckets = [(0,5),(5,15),(15,30),(30,60),(60,120),(120,9999)]
print(f"\n  持仓时长分布:")
for lo, hi in buckets:
    b_trades = [t for t in trades if lo <= t['duration_min'] < hi]
    if not b_trades: continue
    b_wr = len([t for t in b_trades if t['profit']>0])/len(b_trades)*100
    b_pnl = sum(t['profit'] for t in b_trades)
    print(f"    {lo}-{hi}min: {len(b_trades):>3}t WR={b_wr:.0f}% PnL=${b_pnl:.1f}")

# ── H2: Direction sequence analysis ───────────────────────────
print(f"\n{'='*60}")
print("H2: 方向切换序列 (寻找whipsaw)")
# Group trades into direction runs
runs = []; cur_dir = None; cur_run = []
for t in trades:
    if t['direction'] != cur_dir:
        if cur_run:
            r_pnl = sum(x['profit'] for x in cur_run)
            r_wr = len([x for x in cur_run if x['profit']>0])/len(cur_run)*100
            runs.append((cur_dir, len(cur_run), r_wr, r_pnl))
        cur_dir = t['direction']; cur_run = [t]
    else: cur_run.append(t)
if cur_run:
    r_pnl = sum(x['profit'] for x in cur_run)
    r_wr = len([x for x in cur_run if x['profit']>0])/len(cur_run)*100
    runs.append((cur_dir, len(cur_run), r_wr, r_pnl))

print(f"  方向切换次数: {len(runs)}")
for i, (d, n, wr, pnl) in enumerate(runs):
    marker = " <- KILLER" if (n >= 8 and wr < 35) else ""
    if n >= 5 or abs(pnl) > 10:
        print(f"  Run#{i}: {d} x{n} WR={wr:.0f}% PnL=${pnl:.1f}{marker}")

# ── H3: Entry quality — MFE analysis ──────────────────────────
print(f"\n{'='*60}")
print("H3: 入场质量 — MFE分析")
mfe_fails = [t for t in trades if t['exit_reason'] == 'mfe_fail']
no_mfes = [t for t in trades if t['exit_reason'] == 'no_mfe']
sl_hits = [t for t in trades if t['exit_reason'].startswith('sl')]
dtp_wins = [t for t in trades if t['exit_reason'] == 'dtp']

print(f"  曾盈利但反转(mfe_fail): {len(mfe_fails)}t, avg loss=${sum(t['profit'] for t in mfe_fails)/len(mfe_fails):.2f}" if mfe_fails else "")
print(f"  从未盈利(no_mfe):       {len(no_mfes)}t, avg loss=${sum(t['profit'] for t in no_mfes)/len(no_mfes):.2f}" if no_mfes else "")
print(f"  直接止损(sl):           {len(sl_hits)}t, avg loss=${sum(t['profit'] for t in sl_hits)/len(sl_hits):.2f}" if sl_hits else "")
print(f"  跟踪止盈(dtp):          {len(dtp_wins)}t, avg win=${sum(t['profit'] for t in dtp_wins)/len(dtp_wins):.2f}" if dtp_wins else "")
print(f"  入场质量问题占比: {(len(sl_hits)+len(no_mfes))/len(trades)*100:.0f}% (直接亏损,从未盈利)")

# ── H4: Hourly direction bias ─────────────────────────────────
print(f"\n{'='*60}")
print("H4: 逐时方向偏差")
hourly_dir = defaultdict(lambda: {'buy': [], 'sell': []})
for t in trades:
    try: h = int(t['time'].split(' ')[1].split(':')[0])
    except: continue
    hourly_dir[h][t['direction']].append(t)

for h in sorted(hourly_dir.keys()):
    b_trades = hourly_dir[h]['buy']; s_trades = hourly_dir[h]['sell']
    b_wr = len([t for t in b_trades if t['profit']>0])/len(b_trades)*100 if b_trades else 0
    s_wr = len([t for t in s_trades if t['profit']>0])/len(s_trades)*100 if s_trades else 0
    b_pnl = sum(t['profit'] for t in b_trades); s_pnl = sum(t['profit'] for t in s_trades)
    best = 'B' if b_pnl > s_pnl else 'S'
    if len(b_trades)+len(s_trades) >= 10:
        print(f"  {h:02d}:00 B:{b_wr:.0f}%({len(b_trades)}t/${b_pnl:.1f}) S:{s_wr:.0f}%({len(s_trades)}t/${s_pnl:.1f}) -> best={best}")

# ── H5: pos_mult during loss clusters ─────────────────────────
print(f"\n{'='*60}")
print("H5: 亏损簇中仓位倍率变化")
# Find loss runs >=5 and track pos_mult
cl = 0; cl_mults = []
for t in trades:
    if t['profit'] < 0:
        cl += 1; cl_mults.append(t['pos_mult'])
    else:
        if cl >= 5:
            avg_mult = sum(cl_mults)/len(cl_mults)
            print(f"  {cl}连亏: avg pos_mult={avg_mult:.2f}, mults={[f'{x:.1f}' for x in cl_mults[:8]]}...")
        cl = 0; cl_mults = []

# ── H6: Win characteristics ───────────────────────────────────
print(f"\n{'='*60}")
print("H6: 盈利交易特征 (vs 亏损)")
win_t = [t for t in trades if t['profit'] > 0]
loss_t = [t for t in trades if t['profit'] < 0]
# Hour distribution of wins
win_hours = Counter(int(t['time'].split(' ')[1].split(':')[0]) for t in win_t)
loss_hours = Counter(int(t['time'].split(' ')[1].split(':')[0]) for t in loss_t)
print(f"  盈利集中时段: {win_hours.most_common(5)}")
print(f"  亏损集中时段: {loss_hours.most_common(5)}")
print(f"  盈利 avg duration: {sum(t['duration_min'] for t in win_t)/len(win_t):.0f}min" if win_t else "")
print(f"  亏损 avg duration: {sum(t['duration_min'] for t in loss_t)/len(loss_t):.0f}min" if loss_t else "")
print(f"  盈利 avg pos_mult: {sum(t['pos_mult'] for t in win_t)/len(win_t):.2f}" if win_t else "")
print(f"  亏损 avg pos_mult: {sum(t['pos_mult'] for t in loss_t)/len(loss_t):.2f}" if loss_t else "")

# ── I-series improvement design ───────────────────────────────
print(f"\n{'='*60}")
print("I系列改进设计 (基于诊断)")
print(f"{'='*60}")
print("""
I1: 趋势确认增强 — 减少whipsaw
  TrendLookback: 80→160 (更长趋势确认)
  SwingStrength: 3→4 (更严格摆动)

I2: OB质量提升 — 过滤弱OB
  MinOBBodyPct: 50→65 (更大实体)
  MinImpulseBodyPct: 50→65
  MinImpulseVolRatio: 1.0→1.3

I3: 双确认入场 — 必须两次触及OB
  RequireDoubleTch: false→true
  DoubleTchWindowMin: 60→120

I4: 严格逆势限制
  MaxCounterRiskATR: 0.5→0.3
  EntryBlockCounterStrong: 保持true

I5: 仅优质时段
  基于H4发现,只在最佳小时交易

I6: 综合 (I1+I2+I4)
""")

# Cleanup
sf = MT5_PROFILES_DIR / 'v11xau-qs4-may.set'
if sf.exists(): sf.unlink()
print("诊断完成!")
