#!/usr/bin/env python3
"""方向分析: 从已有的May 2026回测HTML提取方向运行位置vs WR"""
import os, sys, re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))

# Find the latest QS4 May 2026 HTML from earlier runs
html_files = sorted(MT5_DATA.glob('*may*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
html_files = [h for h in html_files if h.stat().st_size > 500000]  # only full month reports

if not html_files:
    # Try any recent backtest HTML
    html_files = sorted(MT5_DATA.glob('*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
    html_files = [h for h in html_files if h.stat().st_size > 500000]

if not html_files:
    print("No suitable HTML found. Need to re-run a backtest.")
    # Quick re-run
    import subprocess, time
    ROOT2 = Path(__file__).resolve().parent.parent
    MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
    MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
    MT5_TESTER_DIR = MT5_DATA / 'Tester'
    MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
    BASE_SET = ROOT2 / 'mql5' / 'Presets' / 'V11XAU-QS3.set'

    # Copy QS3 as base and modify manually
    import shutil
    dst = MT5_PROFILES_DIR / 'v11xau-dir2.set'
    content = BASE_SET.read_text(encoding='utf-8')
    for key, val in [('InpVersion','V11XAU-DIR2'),('InpMagicNumber','204866'),
                     ('InpBouncePct','0.30'),('InpBounceSweetMinPct','0.35'),
                     ('InpOutsideBounceSweetMult','0.4'),('InpMaxCounterRiskATR','0.5'),
                     ('InpMaxEntriesPerOB','2'),('InpEnableDeepestPullbackSL','true'),
                     ('InpDeepestPullbackBuffer','0.5'),('InpEnableEntryDebug','true')]:
        p = re.compile(rf'^{key}=.*$', re.MULTILINE)
        content = p.sub(f'{key}={val}', content) if p.search(content) else content + f'\n{key}={val}\n'
    dst.write_text(content)

    # Kill and run
    try:
        subprocess.run(['powershell','-Command',"Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"],capture_output=True,timeout=10)
    except: pass
    time.sleep(3)

    ts = datetime.now().strftime('%Y%m%d')
    ini = MT5_TESTER_DIR / 'backtest.ini'
    ini.write_text(f"[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\nExpertParameters=v11xau-dir2.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0\nFromDate=2026.05.01\nToDate=2026.05.31\nDeposit=200\nCurrency=USD\nLeverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport=dir2_{ts}\n")
    for old in MT5_DATA.glob('dir2*.htm'):
        try: old.unlink()
        except: pass
    subprocess.Popen([MT5_TERMINAL, f'/config:{ini}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Running 2026-05 backtest...")
    for i in range(60):
        time.sleep(5)
        try:
            r = subprocess.run(['powershell','-Command',"(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' }).Count"],capture_output=True,text=True,timeout=5)
            if r.stdout.strip() == '0': break
        except: pass
    time.sleep(2)
    html_files = sorted(MT5_DATA.glob('dir2*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)

if not html_files:
    print("STILL no HTML. Aborting.")
    sys.exit(1)

html_path = html_files[0]
print(f"Using: {html_path.name} ({html_path.stat().st_size} bytes)")

# Parse trades
raw = html_path.read_bytes()
try: text = raw.decode('utf-16-le')
except: text = raw.decode('utf-8', errors='ignore')
lines = text.split('\n')
trades = []; op = {}
for line in lines:
    if 'XAUUSDm' not in line: continue
    clean = re.sub(r'<[^>]+>',' | ',line).strip()
    parts = [p.strip() for p in clean.split('|')]
    ne = [p for p in parts if p]
    try: si = ne.index('XAUUSDm')
    except ValueError: continue
    if si+4 >= len(ne): continue
    d = ne[si+1]; io = ne[si+2]
    if io not in ('in','out'): continue
    try: dn = int(ne[si-1]) if si>0 else 0
    except: continue
    if io == 'in':
        try:
            lot = float(ne[si+3]); price = float(ne[si+4])
            cmt = ne[-1] if ne[-1]!='XAUUSDm' else ''; ts_str = ne[0]
            op[dn] = {'time':ts_str,'dir':d,'lot':lot,'ep':price,'cmt':cmt}
        except: pass
    else:
        try:
            xp = float(ne[si+4]); profit = float(ne[-3].replace(' ',''))
            bal = float(ne[-2].replace(' ','')); reason = ne[-1] if ne[-1]!='XAUUSDm' else '?'
            ei = None
            for k in sorted(op.keys()):
                if op[k]['dir'] != d: ei = op.pop(k); break
            ts_str = ne[0]
            mult = 1.0; mm = re.search(r'x([\d.]+)$', ei['cmt'] if ei else '')
            if mm: mult = float(mm.group(1))
            try:
                et = datetime.strptime(ei['time'],'%Y.%m.%d %H:%M:%S')
                xt = datetime.strptime(ts_str,'%Y.%m.%d %H:%M:%S')
                dur = (xt-et).total_seconds()/60
            except: dur = 0
            trades.append({'time':ts_str,'dir':d,'profit':profit,'bal':bal,'reason':reason,'lot':lot,'mult':mult,'dur':dur})
        except: pass

print(f"Parsed {len(trades)} trades")

# === Direction Run Analysis ===
runs = []; cur_dir = None; cur = []
for t in trades:
    if t['dir'] != cur_dir:
        if cur: runs.append((cur_dir, cur))
        cur_dir = t['dir']; cur = [t]
    else: cur.append(t)
if cur: runs.append((cur_dir, cur))

print(f"\n{'='*60}")
print(f"方向切换次数: {len(runs)}")

# WR by position in run
pos_data = defaultdict(lambda: {'w':0,'l':0,'pnl':0.0})
for d, run in runs:
    for i, t in enumerate(run):
        pos = i + 1
        if t['profit'] > 0: pos_data[pos]['w'] += 1
        else: pos_data[pos]['l'] += 1
        pos_data[pos]['pnl'] += t['profit']

print(f"\n运行位置 vs WR (核心发现):")
print(f"{'位置':<8} {'交易':>6} {'WR':>8} {'PnL':>12} {'解读':>30}")
print("-"*70)
for pos in sorted(pos_data.keys()):
    d = pos_data[pos]; total = d['w'] + d['l']
    wr = d['w']/total*100 if total > 0 else 0
    note = ""
    if pos == 1: note = "<- 切换后首笔"
    elif pos <= 3: note = "<- 运行早期"
    elif pos <= 8: note = "<- 运行中期"
    else: note = "<- 运行晚期(已锁死方向)"
    print(f"#{pos:<7} {total:>6} {wr:>7.1f}% ${d['pnl']:>10.1f} {note}")

# Buy vs Sell position WR
for dname in ['buy','sell']:
    d_runs = [(d,run) for d,run in runs if d == dname]
    d_pos = defaultdict(lambda: {'w':0,'l':0})
    for d, run in d_runs:
        for i, t in enumerate(run):
            if t['profit'] > 0: d_pos[i+1]['w'] += 1
            else: d_pos[i+1]['l'] += 1
    print(f"\n{dname}方向 位置WR: ", end='')
    for pos in sorted(d_pos.keys())[:12]:
        dd = d_pos[pos]; total = dd['w'] + dd['l']
        wr = dd['w']/total*100 if total > 0 else 0
        print(f"#{pos}={wr:.0f}%({total}t) ", end='')
    print()

# First vs later trades
first_trades = [run[0] for d,run in runs]
later_trades = [t for d,run in runs for t in run[1:]]
first_wr = len([t for t in first_trades if t['profit']>0])/len(first_trades)*100
later_wr = len([t for t in later_trades if t['profit']>0])/len(later_trades)*100 if later_trades else 0
first_pnl = sum(t['profit'] for t in first_trades)
later_pnl = sum(t['profit'] for t in later_trades)
print(f"\n切换首笔: {len(first_trades)}t WR={first_wr:.1f}% PnL=${first_pnl:.1f}")
print(f"运行后续: {len(later_trades)}t WR={later_wr:.1f}% PnL=${later_pnl:.1f}")

# Cleanup
sf = MT5_PROFILES_DIR / 'v11xau-dir2.set'
if sf.exists(): sf.unlink()
print("\nDone!")
