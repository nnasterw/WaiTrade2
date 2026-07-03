#!/usr/bin/env python3
"""深挖方向问题: 方向切换时机/运行位置WR/状态过滤器滞后"""
import os, sys, re, time, subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict

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
    dst=MT5_PROFILES_DIR/'v11xau-dir-deep.set'
    c=BASE_SET.read_text(encoding='utf-8')
    for k,v in {'InpVersion':'V11XAU-DIR','InpMagicNumber':'204866','InpEnableEntryDebug':'true','InpEnableExitDebug':'true'}.items():c=replace_param(c,k,v)
    for k,v in QS4.items():c=replace_param(c,k,v)
    dst.write_text(c)

def kill_mt5():
    try:subprocess.run(['powershell','-Command',"Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"],capture_output=True,timeout=10)
    except:pass;time.sleep(3)

def run_bt(df,dt,to=300):
    ini=MT5_TESTER_DIR/'backtest.ini';ts=datetime.now().strftime('%Y%m%d')
    ini.write_text(f"[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\nExpertParameters=v11xau-dir-deep.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0\nFromDate={df}\nToDate={dt}\nDeposit=200\nCurrency=USD\nLeverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport_dirdeep_{ts}\n")
    kill_mt5()
    for o in MT5_DATA.glob('dirdeep*.htm'):
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
    fs=sorted(MT5_DATA.glob('dirdeep*.htm'),key=lambda p:p.stat().st_mtime,reverse=True)
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
                cmt=ne[-1] if ne[-1]!='XAUUSDm' else '';ts_str=ne[0]
                op[dn]={'time':ts_str,'dir':d,'lot':lot,'ep':price,'cmt':cmt}
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
                try:
                    et=datetime.strptime(ei['time'],'%Y.%m.%d %H:%M:%S')
                    xt=datetime.strptime(ts_str,'%Y.%m.%d %H:%M:%S')
                    dur=(xt-et).total_seconds()/60
                except:dur=0
                trades.append({'time':ts_str,'dir':d,'profit':profit,'bal':bal,'reason':reason,'lot':lot,'mult':mult,'dur':dur,'ep':ei['ep'],'xp':xp})
            except:pass
    return trades

# ── Run both months ──────────────────────────────────────
print("QS4 方向深度分析: 2025-10 vs 2026-05")
make_set()

for label,df,dt in [("2025-10_GOOD","2025.10.01","2025.10.31"),("2026-05_BAD","2026.05.01","2026.05.31")]:
    print(f"\n{'='*60}\n[{label}]")
    html=run_bt(df,dt)
    if not html:print("FAILED");continue
    trades=parse(html)
    print(f"{len(trades)}笔")

    # === 1. 方向运行分析: 运行位置 vs WR ===
    runs=[];cur_dir=None;cur=[]
    for t in trades:
        if t['dir']!=cur_dir:
            if cur:runs.append((cur_dir,cur))
            cur_dir=t['dir'];cur=[t]
        else:cur.append(t)
    if cur:runs.append((cur_dir,cur))

    # WR by position in run
    pos_data=defaultdict(lambda:{'w':0,'l':0})
    for d,run in runs:
        for i,t in enumerate(run):
            pos=i+1
            if t['profit']>0:pos_data[pos]['w']+=1
            else:pos_data[pos]['l']+=1

    print(f"\n  方向切换次数: {len(runs)}")
    print(f"  运行位置 vs WR (好月应递减,坏月应全低):")
    print(f"  {'位置':<6} {'交易':>5} {'WR':>7} {'PnL':>10}")
    for pos in sorted(pos_data.keys()):
        d=pos_data[pos];total=d['w']+d['l']
        wr=d['w']/total*100 if total>0 else 0
        pos_trades=[t for d,run in runs for i,t in enumerate(run) if i+1==pos]
        pnl=sum(t['profit'] for t in pos_trades)
        print(f"  #{pos:<5} {total:>5} {wr:>6.1f}% ${pnl:>9.1f}")

    # === 2. 方向切换后的首个交易 ===
    first_trades=[run[0] for d,run in runs]
    first_wr=len([t for t in first_trades if t['profit']>0])/len(first_trades)*100
    first_pnl=sum(t['profit'] for t in first_trades)
    later_trades=[t for d,run in runs for t in run[1:]]
    later_wr=len([t for t in later_trades if t['profit']>0])/len(later_trades)*100 if later_trades else 0
    print(f"\n  切换后首笔: {len(first_trades)}t WR={first_wr:.1f}% PnL=${first_pnl:.1f}")
    print(f"  运行后续笔: {len(later_trades)}t WR={later_wr:.1f}%")

    # === 3. 方向运行长度 vs 总盈亏 ===
    print(f"\n  运行长度 vs 盈亏:")
    for min_len in [1,3,5,10,20]:
        long_runs=[(d,run) for d,run in runs if len(run)>=min_len]
        total_pnl=sum(sum(t['profit'] for t in run) for d,run in long_runs)
        total_t=sum(len(run) for d,run in long_runs)
        avg_wr=sum(len([t for t in run if t['profit']>0])/len(run)*100 for d,run in long_runs)/len(long_runs)*100 if long_runs else 0
        print(f"    >={min_len}笔的运行: {len(long_runs)}个, {total_t}t, avgWR={avg_wr/100:.1f}%, PnL=${total_pnl:.1f}")

    # === 4. 两个方向对比 ===
    for dname in ['buy','sell']:
        d_trades=[t for t in trades if t['dir']==dname]
        d_wins=len([t for t in d_trades if t['profit']>0])
        d_wr=d_wins/len(d_trades)*100 if d_trades else 0
        d_pnl=sum(t['profit'] for t in d_trades)
        d_runs=[(d,run) for d,run in runs if d==dname]
        avg_run_len=sum(len(run) for d,run in d_runs)/len(d_runs) if d_runs else 0
        print(f"\n  {dname}: {len(d_trades)}t WR={d_wr:.1f}% PnL=${d_pnl:.1f} 平均运行长度={avg_run_len:.1f}笔")

        # WR by run position for this direction
        d_pos=defaultdict(lambda:{'w':0,'l':0})
        for d,run in d_runs:
            for i,t in enumerate(run):
                if t['profit']>0:d_pos[i+1]['w']+=1
                else:d_pos[i+1]['l']+=1
        print(f"    运行位置WR: ",end='')
        for pos in sorted(d_pos.keys())[:10]:
            dd=d_pos[pos];total=dd['w']+dd['l']
            wr=dd['w']/total*100 if total>0 else 0
            print(f"#{pos}={wr:.0f}% ",end='')
        print()

    # === 5. 方向切换间隔 ===
    switch_times=[]
    for i in range(1,len(runs)):
        prev_last=datetime.strptime(runs[i-1][1][-1]['time'],'%Y.%m.%d %H:%M:%S')
        curr_first=datetime.strptime(runs[i][1][0]['time'],'%Y.%m.%d %H:%M:%S')
        gap=(curr_first-prev_last).total_seconds()/60
        switch_times.append(gap)
    if switch_times:
        print(f"\n  方向切换间隔: 中位={sorted(switch_times)[len(switch_times)//2]:.0f}min 平均={sum(switch_times)/len(switch_times):.0f}min")

sf=MT5_PROFILES_DIR/'v11xau-dir-deep.set'
if sf.exists():sf.unlink()
print("\n方向分析完成!")
