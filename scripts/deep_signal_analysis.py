#!/usr/bin/env python3
"""深挖交易信号: SL距离/评分倍率/入场密度/信号类型 — QS4 2026-05"""
import os, sys, re, time, subprocess
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
MT5_TESTER_DIR = MT5_DATA / 'Tester'; MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
BASE_SET = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'

QS4 = {'InpBouncePct':'0.30','InpBounceSweetMinPct':'0.35','InpOutsideBounceSweetMult':'0.4',
       'InpMaxCounterRiskATR':'0.5','InpMaxEntriesPerOB':'2',
       'InpEnableDeepestPullbackSL':'true','InpDeepestPullbackBuffer':'0.5'}

def replace_param(c,k,v):
    p=re.compile(rf'^{k}=.*$',re.MULTILINE)
    return p.sub(f'{k}={v}',c) if p.search(c) else c+f'\n{k}={v}\n'

def make_set():
    dst=MT5_PROFILES_DIR/'v11xau-sig-deep.set'
    c=BASE_SET.read_text(encoding='utf-8')
    for k,v in {'InpVersion':'V11XAU-SIG','InpMagicNumber':'204866','InpEnableEntryDebug':'true','InpEnableExitDebug':'true'}.items():c=replace_param(c,k,v)
    for k,v in QS4.items():c=replace_param(c,k,v)
    dst.write_text(c)

def kill_mt5():
    try:subprocess.run(['powershell','-Command',"Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"],capture_output=True,timeout=10)
    except:pass;time.sleep(3)

def run_bt(df,dt,to=300):
    ini=MT5_TESTER_DIR/'backtest.ini';ts=datetime.now().strftime('%Y%m%d')
    ini.write_text(f"[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\nExpertParameters=v11xau-sig-deep.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0\nFromDate={df}\nToDate={dt}\nDeposit=200\nCurrency=USD\nLeverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport=sigdeep_{ts}\n")
    kill_mt5()
    for o in MT5_DATA.glob('sigdeep*.htm'):
        try:o.unlink()
        except:pass
    subprocess.Popen([MT5_TERMINAL,f'/config:{ini}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for i in range(to//5):
        time.sleep(5)
        try:
            r=subprocess.run(['powershell','-Command',"(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' }).Count"],capture_output=True,text=True,timeout=5)
            if r.stdout.strip()=='0':break
        except:pass
    time.sleep(2)
    fs=sorted(MT5_DATA.glob('sigdeep*.htm'),key=lambda p:p.stat().st_mtime,reverse=True)
    return fs[0] if fs else None

def parse(html_path):
    raw=html_path.read_bytes()
    try:text=raw.decode('utf-16-le')
    except:text=raw.decode('utf-8',errors='ignore')
    lines=text.split('\n')
    trades=[];op={}
    for line in lines:
        if 'XAUUSDm' not in line:continue
        clean=re.sub(r'<[^>]+>',' | ',line).strip()
        parts=[p.strip() for p in clean.split('|')]
        ne=[p for p in parts if p]
        try:si=ne.index('XAUUSDm')
        except ValueError:continue
        if si+4>=len(ne):continue
        d=ne[si+1];io=ne[si+2]
        if io not in ('in','out'):continue
        try:dn=int(ne[si-1]) if si>0 else 0
        except:continue
        if io=='in':
            try:
                lot=float(ne[si+3]);price=float(ne[si+4])
                cmt=ne[-1] if ne[-1]!='XAUUSDm' else ''
                ts_str=ne[0]
                # Parse signal type from comment
                # Format: "WT V11XAU-SIG B x2.3" or "WT V11XAU-SIG S x1.0"
                sig_type='?'
                sig_m=re.search(r'SIG\s+(\w)\s+x',cmt)
                if sig_m:sig_type=sig_m.group(1)
                op[dn]={'time':ts_str,'dir':d,'lot':lot,'ep':price,'cmt':cmt,'sig':sig_type}
            except:pass
        else:
            try:
                xp=float(ne[si+4]);profit=float(ne[-3].replace(' ',''))
                bal=float(ne[-2].replace(' ',''));reason=ne[-1] if ne[-1]!='XAUUSDm' else '?'
                ei=None
                for k in sorted(op.keys()):
                    if op[k]['dir']!=d:ei=op.pop(k);break
                ts_str=ne[0]
                mult=1.0;mm=re.search(r'x([\d.]+)$',ei['cmt'] if ei else '')
                if mm:mult=float(mm.group(1))
                # Parse SL distance
                sl_dist=0
                sl_m=re.search(r'sl\s+([\d.]+)',reason)
                if sl_m:
                    sl_price=float(sl_m.group(1))
                    if d=='buy':sl_dist=ei['ep']-sl_price
                    else:sl_dist=sl_price-ei['ep']
                try:
                    et=datetime.strptime(ei['time'],'%Y.%m.%d %H:%M:%S')
                    xt=datetime.strptime(ts_str,'%Y.%m.%d %H:%M:%S')
                    dur=(xt-et).total_seconds()/60
                except:dur=0
                trades.append({'time':ts_str,'dir':d,'profit':profit,'bal':bal,'reason':reason,
                    'lot':lot,'mult':mult,'dur':dur,'sl_dist':sl_dist,'sig':ei['sig'],
                    'ep':ei['ep'],'xp':xp})
            except:pass
    return trades

# ── Run both months ──────────────────────────────────────
print("QS4 交易信号深度对比: 2025-10 vs 2026-05")
make_set()

for label,df,dt in [("2025-10_GOOD","2025.10.01","2025.10.31"),("2026-05_BAD","2026.05.01","2026.05.31")]:
    print(f"\n[{label}] 回测...",end=' ',flush=True)
    html=run_bt(df,dt)
    if not html:print("FAILED");continue
    trades=parse(html)
    print(f"{len(trades)}笔")

    wins=[t for t in trades if t['profit']>0];losses=[t for t in trades if t['profit']<0]
    wr=len(wins)/len(trades)*100

    # === 1. SL距离分析 ===
    sl_trades=[t for t in trades if t['sl_dist']>0]
    if sl_trades:
        sl_win=[t for t in sl_trades if t['profit']>0];sl_loss=[t for t in sl_trades if t['profit']<0]
        print(f"  SL距离: 赢avg={sum(t['sl_dist'] for t in sl_win)/len(sl_win):.2f}" if sl_win else "")
        print(f"          亏avg={sum(t['sl_dist'] for t in sl_loss)/len(sl_loss):.2f}" if sl_loss else "")
        # SL distance buckets
        for lo,hi in [(0,0.3),(0.3,0.5),(0.5,0.8),(0.8,1.2),(1.2,5)]:
            b=[t for t in sl_trades if lo<=t['sl_dist']<hi]
            if not b:continue
            bw=len([t for t in b if t['profit']>0])
            print(f"    SL {lo}-{hi}: {len(b):>3}t WR={bw/len(b)*100:.0f}%")

    # === 2. 评分倍率 vs 胜率 ===
    mults=defaultdict(list)
    for t in trades: mults[round(t['mult']*10)/10].append(t)
    print(f"\n  评分倍率 vs WR:")
    for m in sorted(mults.keys()):
        ts=mults[m];w=len([t for t in ts if t['profit']>0])
        print(f"    x{m:.1f}: {len(ts):>3}t WR={w/len(ts)*100:.0f}% PnL=${sum(t['profit'] for t in ts):.1f}")

    # === 3. 入场密度 — 每笔间隔时间 ===
    gaps=[]
    for i in range(1,len(trades)):
        try:
            t0=datetime.strptime(trades[i-1]['time'],'%Y.%m.%d %H:%M:%S')
            t1=datetime.strptime(trades[i]['time'],'%Y.%m.%d %H:%M:%S')
            gaps.append((t1-t0).total_seconds())
        except:pass
    if gaps:
        print(f"\n  入场间隔: 中位={sorted(gaps)[len(gaps)//2]:.0f}s, 平均={sum(gaps)/len(gaps):.0f}s")
        # Density vs outcome
        dense=[i for i,g in enumerate(gaps) if g<60]
        dense_wins=[i for i in dense if trades[i+1]['profit']>0]
        print(f"  间隔<60秒的入场: {len(dense)}次, 其中下一笔WR={len(dense_wins)/max(1,len(dense))*100:.0f}%")

    # === 4. 信号类型 (从entry comment解析) ===
    sigs=Counter(t['sig'] for t in trades)
    print(f"\n  信号类型分布: {dict(sigs)}")
    for sig in sigs:
        st=[t for t in trades if t['sig']==sig]
        sw=len([t for t in st if t['profit']>0])
        print(f"    类型'{sig}': {len(st)}t WR={sw/len(st)*100:.0f}% PnL=${sum(t['profit'] for t in st):.1f}")

    # === 5. 连续交易的信号是否相同 ===
    same_sig_runs=[]
    cur_sig=None;cur_run=[]
    for t in trades:
        if t['sig']!=cur_sig:
            if len(cur_run)>=3:same_sig_runs.append((cur_sig,len(cur_run),sum(x['profit'] for x in cur_run)))
            cur_sig=t['sig'];cur_run=[t]
        else:cur_run.append(t)
    if len(cur_run)>=3:same_sig_runs.append((cur_sig,len(cur_run),sum(x['profit'] for x in cur_run)))
    if same_sig_runs:
        print(f"\n  同信号连续簇(>=3笔): {len(same_sig_runs)}个")
        for sig,n,pnl in sorted(same_sig_runs,key=lambda x:-x[1])[:8]:
            print(f"    信号'{sig}' x{n}笔 PnL=${pnl:.1f}")

sf=MT5_PROFILES_DIR/'v11xau-sig-deep.set'
if sf.exists():sf.unlink()
print("\n信号分析完成!")
