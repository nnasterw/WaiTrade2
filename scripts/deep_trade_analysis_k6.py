#!/usr/bin/env python3
"""深入单子: K6 2026-05 逐笔分析 — 盈亏分布/出场原因/序列模式/改进方向"""
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

K6_PARAMS = {
    'InpBouncePct': '0.30', 'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4', 'InpMaxCounterRiskATR': '0.5',
    'InpMaxEntriesPerOB': '2',
    'InpEnableDeepestPullbackSL': 'true', 'InpDeepestPullbackBuffer': '0.5',
    'InpBreakevenR': '0.25', 'InpBreakevenLockR': '0.08',
    'InpDTPTriggerR': '8.0', 'InpAdaptiveDTP': 'false',
    'InpDTPRetrace': '0.2', 'InpTimeExitBars': '999',
}

def replace_param(c, k, v):
    p = re.compile(rf'^{k}=.*$', re.MULTILINE)
    return p.sub(f'{k}={v}', c) if p.search(c) else c + f'\n{k}={v}\n'

def make_set():
    dst = MT5_PROFILES_DIR / 'v11xau-k6-deep.set'
    content = BASE_SET.read_text(encoding='utf-8')
    content = replace_param(content, 'InpVersion', 'V11XAU-K6-DEEP')
    content = replace_param(content, 'InpMagicNumber', '204775')
    content = replace_param(content, 'InpEnableEntryDebug', 'true')
    content = replace_param(content, 'InpEnableExitDebug', 'true')
    for k, v in K6_PARAMS.items(): content = replace_param(content, k, v)
    dst.write_text(content)

def kill_mt5_tester():
    try:
        subprocess.run(['powershell', '-Command',
            "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"
        ], capture_output=True, timeout=10)
    except: pass; time.sleep(3)

def run_bt(date_from, date_to, timeout=300):
    ini = MT5_TESTER_DIR / 'backtest.ini'
    ts = datetime.now().strftime('%Y%m%d')
    ini.write_text(f"""[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB
ExpertParameters=v11xau-k6-deep.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4
Optimization=0\nFromDate={date_from}\nToDate={date_to}\nDeposit=200\nCurrency=USD
Leverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport=k6deep_{ts}\n""")
    kill_mt5_tester()
    for old in MT5_DATA.glob('k6deep*.htm'):
        try: old.unlink()
        except: pass
    subprocess.Popen([MT5_TERMINAL, f'/config:{ini}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(timeout//5):
        time.sleep(5)
        try:
            r = subprocess.run(['powershell', '-Command',
                "(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
                "Where-Object { $_.Path -like '*Program Files*' }).Count"],
                capture_output=True, text=True, timeout=5)
            if r.stdout.strip() == '0': break
        except: pass
    time.sleep(2)
    files = sorted(MT5_DATA.glob('k6deep*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def parse_trades(html_path):
    raw = html_path.read_bytes()
    try: text = raw.decode('utf-16-le')
    except: text = raw.decode('utf-8', errors='ignore')
    lines = text.split('\n')
    trades = []; open_pos = {}
    for line in lines:
        if 'XAUUSDm' not in line: continue
        clean = re.sub(r'<[^>]+>', ' | ', line).strip()
        parts = [p.strip() for p in clean.split('|')]
        ne = [p for p in parts if p]
        try: si = ne.index('XAUUSDm')
        except ValueError: continue
        if si + 4 >= len(ne): continue
        d = ne[si+1]; io = ne[si+2]
        if io not in ('in','out'): continue
        try: dn = int(ne[si-1]) if si>0 else 0
        except: continue
        if io == 'in':
            try:
                lot = float(ne[si+3]); price = float(ne[si+4])
                cmt = ne[-1] if ne[-1]!='XAUUSDm' else ''
                ts_str = ne[0]
                open_pos[dn] = {'time':ts_str,'dir':d,'lot':lot,'ep':price,'cmt':cmt}
            except: pass
        else:
            try:
                xp = float(ne[si+4]); profit = float(ne[-3].replace(' ',''))
                bal = float(ne[-2].replace(' ','')); reason = ne[-1] if ne[-1]!='XAUUSDm' else '?'
                ei = None
                for k in sorted(open_pos.keys()):
                    if open_pos[k]['dir'] != d: ei = open_pos.pop(k); break
                ts_str = ne[0]
                mult = 1.0
                mm = re.search(r'x([\d.]+)$', ei['cmt'] if ei else '')
                if mm: mult = float(mm.group(1))
                try:
                    et = datetime.strptime(ei['time'],'%Y.%m.%d %H:%M:%S')
                    xt = datetime.strptime(ts_str,'%Y.%m.%d %H:%M:%S')
                    dur = (xt-et).total_seconds()/60
                except: dur = 0
                # Classify
                if reason == 'dtp': cat = 'DTP_WIN'
                elif profit > 0 and 'sl' not in reason: cat = 'BE_WIN'
                elif profit > 0: cat = 'OTHER_WIN'
                elif reason == 'mfe_fail': cat = 'MFE_FAIL'
                elif reason == 'no_mfe': cat = 'NO_MFE'
                elif 'sl' in reason: cat = 'SL'
                elif 'decay' in reason: cat = 'DECAY'
                else: cat = 'OTHER_LOSS'
                trades.append({
                    'time':ts_str,'dir':d,'profit':profit,'bal':bal,
                    'reason':reason,'lot':lot,'mult':mult,'dur':dur,'cat':cat,
                    'ep':ei['ep'] if ei else 0,'xp':xp
                })
            except: pass
    return trades

# ── Main ──────────────────────────────────────────────────────
print("K6 2026-05 逐笔深度分析")
make_set()
html = run_bt("2026.05.01", "2026.05.31")
if not html: print("FAILED"); sys.exit(1)
trades = parse_trades(html)
print(f"\n提取 {len(trades)} 笔交易")

# === 1. 盈亏分布 ===
print(f"\n{'='*60}\n1. 盈亏分布")
wins = [t for t in trades if t['profit']>0]; losses = [t for t in trades if t['profit']<0]
print(f"  盈利: {len(wins)}笔  max=${max(t['profit'] for t in wins):.1f}  avg=${sum(t['profit'] for t in wins)/len(wins):.1f}")
print(f"  亏损: {len(losses)}笔  min=${min(t['profit'] for t in losses):.1f}  avg=${sum(t['profit'] for t in losses)/len(losses):.1f}")

# Profit histogram
buckets = [(-999,-10),(-10,-5),(-5,-2),(-2,-1),(-1,0),(0,1),(1,2),(2,5),(5,10),(10,50),(50,999)]
print(f"\n  盈亏分布直方图:")
for lo, hi in buckets:
    b = [t for t in trades if lo <= t['profit'] < hi]
    if b:
        bar = '#' * min(len(b), 50)
        print(f"  ${lo:>5}~${hi:<5}: {len(b):>3}t {bar}")

# === 2. 出场原因 ===
print(f"\n{'='*60}\n2. 出场原因")
cats = Counter(t['cat'] for t in trades)
for c, n in cats.most_common():
    c_trades = [t for t in trades if t['cat']==c]
    c_pnl = sum(t['profit'] for t in c_trades)
    c_avg = c_pnl/n
    print(f"  {c:<15} {n:>4}t  PnL=${c_pnl:>8.1f}  avg=${c_avg:>6.1f}")

# === 3. 持仓时长 vs 盈亏 ===
print(f"\n{'='*60}\n3. 持仓时长 vs 结果")
dur_buckets = [(0,5),(5,15),(15,30),(30,60),(60,120),(120,9999)]
for lo, hi in dur_buckets:
    b = [t for t in trades if lo <= t['dur'] < hi]
    if not b: continue
    bw = len([t for t in b if t['profit']>0])
    wr = bw/len(b)*100; pnl = sum(t['profit'] for t in b)
    print(f"  {lo}-{hi}min: {len(b):>3}t WR={wr:.0f}% PnL=${pnl:.1f}")

# === 4. 连续盈亏序列 ===
print(f"\n{'='*60}\n4. 盈亏序列模式")
seq = []; cur_type = None; cur_trades = []
for t in trades:
    typ = 'W' if t['profit']>0 else 'L'
    if typ != cur_type:
        if cur_trades:
            pnl = sum(x['profit'] for x in cur_trades)
            seq.append((cur_type, len(cur_trades), pnl))
        cur_type = typ; cur_trades = [t]
    else: cur_trades.append(t)
if cur_trades:
    pnl = sum(x['profit'] for x in cur_trades)
    seq.append((cur_type, len(cur_trades), pnl))

# Find killer sequences
print(f"  序列总数: {len(seq)}")
for typ, n, pnl in seq:
    if n >= 8:
        marker = " <-- KILLER" if (typ=='L' and n>=10) else ""
        print(f"  {typ} x{n:<3} PnL=${pnl:>8.1f}{marker}")

# === 5. 大赢单特征 ===
print(f"\n{'='*60}\n5. 大赢单(>$5)特征")
big_wins = [t for t in trades if t['profit'] > 5]
if big_wins:
    for t in sorted(big_wins, key=lambda x: -x['profit'])[:10]:
        print(f"  {t['time']} {t['dir']} +${t['profit']:.1f} dur={t['dur']:.0f}min "
              f"reason={t['reason']} mult={t['mult']:.1f}")
    bw_hours = Counter(int(t['time'].split(' ')[1].split(':')[0]) for t in big_wins)
    bw_dirs = Counter(t['dir'] for t in big_wins)
    print(f"  大赢时段: {bw_hours.most_common(5)}")
    print(f"  大赢方向: {dict(bw_dirs)}")
else:
    print(f"  无>$5的盈利单!")

# === 6. 大亏单特征 ===
print(f"\n{'='*60}\n6. 大亏单(<-$5)特征")
big_losses = [t for t in trades if t['profit'] < -5]
if big_losses:
    for t in sorted(big_losses, key=lambda x: x['profit'])[:10]:
        print(f"  {t['time']} {t['dir']} -${abs(t['profit']):.1f} dur={t['dur']:.0f}min "
              f"reason={t['reason']} mult={t['mult']:.1f}")
    bl_hours = Counter(int(t['time'].split(' ')[1].split(':')[0]) for t in big_losses)
    print(f"  大亏时段: {bl_hours.most_common(5)}")
else:
    print(f"  无<-$5的亏损单! 所有亏损都是小额!")

# === 7. 改进思路 ===
print(f"\n{'='*60}\n7. 基于单子分析的改进方向")

# Calculate key ratios
win_pct = len(wins)/len(trades)*100
big_win_pnl = sum(t['profit'] for t in big_wins)
big_loss_pnl = sum(t['profit'] for t in big_losses)
small_win_pnl = sum(t['profit'] for t in wins if t['profit'] <= 5)
small_loss_pnl = sum(t['profit'] for t in losses if t['profit'] >= -5)
total_pnl = sum(t['profit'] for t in trades)

print(f"""
  K6 2026-05 逐笔画像:
  - 总PnL: ${total_pnl:.1f} ({len(trades)}笔)
  - 大赢(>$5): {len(big_wins)}笔, 贡献${big_win_pnl:.1f} ({big_win_pnl/total_pnl*100:.0f}% of PnL)
  - 大亏(<-$5): {len(big_losses)}笔, 亏损${big_loss_pnl:.1f}
  - 小赢(<=$5): {len(wins)-len(big_wins)}笔, 贡献${small_win_pnl:.1f}
  - 小亏(>=-$5): {len(losses)-len(big_losses)}笔, 亏损${small_loss_pnl:.1f}

  关键发现:
  1. 如果过滤掉所有小额交易(>$5 or <-$5),只保留大赢: PnL={big_win_pnl+big_loss_pnl:.1f}
  2. 大赢集中在特定时段: {bw_hours.most_common(3) if big_wins else 'N/A'}
""")

sf = MT5_PROFILES_DIR / 'v11xau-k6-deep.set'
if sf.exists(): sf.unlink()
print("分析完成!")
