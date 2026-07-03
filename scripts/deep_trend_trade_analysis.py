#!/usr/bin/env python3
"""深挖Q2交易趋势细节: 赢单特征/趋势翻转时机/MFE — 找转亏为盈路径"""
import os, sys, re, time, subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
MT5_TESTER_DIR = MT5_DATA / 'Tester'; MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
BASE_SET = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'

Q2_PARAMS = {
    'InpBouncePct':'0.30','InpBounceSweetMinPct':'0.35','InpOutsideBounceSweetMult':'0.4',
    'InpMaxCounterRiskATR':'0.5','InpMaxEntriesPerOB':'2',
    'InpEnableDeepestPullbackSL':'true','InpDeepestPullbackBuffer':'0.5',
    'InpEnableHTFNetPushFilter':'true','InpHTFNetPushTF':'60','InpHTFNetPushBars':'5',
    'InpHTFNetPushMinATR':'0.4','InpHTFNetPushAlignedMult':'1.3',
    'InpHTFNetPushNeutralMult':'1.0','InpHTFNetPushCounterMult':'0.0',
    'InpEnableHTFPullback':'true','InpHTFPullbackOnly':'false','InpHTFPullbackTF':'15',
    'InpHTFPullbackBars':'3','InpHTFPullbackMinATR':'0.8',
    'InpHTFPullbackZoneATR':'0.35','InpHTFPullbackOffsetATR':'0.1','InpHTFPullbackTPMult':'1.0',
}

def rep(c,k,v):
    p=re.compile(rf'^{k}=.*$',re.MULTILINE)
    return p.sub(f'{k}={v}',c) if p.search(c) else c+f'\n{k}={v}\n'

def make_set():
    dst=MT5_PROFILES_DIR/'v11xau-q2deep.set'
    c=BASE_SET.read_text(encoding='utf-8')
    for k,v in {'InpVersion':'V11XAU-Q2DEEP','InpMagicNumber':'204719','InpEnableEntryDebug':'true','InpEnableExitDebug':'true'}.items():c=rep(c,k,v)
    for k,v in Q2_PARAMS.items():c=rep(c,k,v)
    dst.write_text(c)

def kill_mt5():
    try:subprocess.run(['powershell','-Command',"Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"],capture_output=True,timeout=10)
    except:pass;time.sleep(3)

def run_bt(df,dt,to=300):
    ini=MT5_TESTER_DIR/'backtest.ini';ts=datetime.now().strftime('%Y%m%d')
    ini.write_text(f"[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\nExpertParameters=v11xau-q2deep.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0\nFromDate={df}\nToDate={dt}\nDeposit=200\nCurrency=USD\nLeverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport=q2deep_{ts}\n")
    kill_mt5()
    for o in MT5_DATA.glob('q2deep_*.htm'):
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
    fs=sorted(MT5_DATA.glob('q2deep_*.htm'),key=lambda p:p.stat().st_mtime,reverse=True)
    return fs[0] if fs else None

def slope(px,n=None):
    if n is None:n=len(px);px=px[-n:]
    if len(px)<3:return 0
    xm=(len(px)-1)/2;ym=sum(px)/len(px)
    num=sum((i-xm)*(px[i]-ym) for i in range(len(px)))
    den=sum((i-xm)**2 for i in range(len(px)))
    return num/den if den!=0 else 0

# ── Run Q2 2026-05 ──────────────────────────────────────
print("Q2 2026-05 趋势交易深度分析")
make_set()
html=run_bt("2026.05.01","2026.05.31")
if not html:print("FAILED");sys.exit(1)

raw=html.read_bytes()
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
            # MFE: for buys, max favorable = highest price after entry before exit
            # Approximate from exit reason
            if 'sl' in reason:
                sl_m=re.search(r'sl\s+([\d.]+)',reason)
                sl_price=float(sl_m.group(1)) if sl_m else xp
                if d=='buy':mfe_pct=(xp-ei['ep'])/ei['ep']*100 if ei else 0  # exit above entry?
                else:mfe_pct=(ei['ep']-xp)/ei['ep']*100 if ei else 0
            else:
                if d=='buy':mfe_pct=(xp-ei['ep'])/ei['ep']*100 if ei else 0
                else:mfe_pct=(ei['ep']-xp)/ei['ep']*100 if ei else 0

            try:
                et=datetime.strptime(ei['time'],'%Y.%m.%d %H:%M:%S')
                xt=datetime.strptime(ts_str,'%Y.%m.%d %H:%M:%S')
                dur=(xt-et).total_seconds()/60
            except:dur=0

            trades.append({'time':ts_str,'dir':d,'profit':profit,'bal':bal,'reason':reason,
                'lot':lot,'mult':mult,'ep':ei['ep'],'xp':xp,'dur':dur,'mfe_pct':mfe_pct})
        except:pass

print(f"{len(trades)}笔交易")

# Classify
eps=[t['ep'] for t in trades]
for i,t in enumerate(trades):
    s15=slope(eps[:i+1],min(100,i+1))
    a=sum(eps[max(0,i-99):i+1])/min(100,i+1)
    st=abs(s15)/a*100 if a>0 else 0
    t['m15']='UP' if (st>0.015 and s15>0) else ('DOWN' if (st>0.015 and s15<0) else 'CHOP')
    s60=slope(eps[:i+1],min(400,i+1))
    a60=sum(eps[max(0,i-399):i+1])/min(400,i+1)
    st60=abs(s60)/a60*100 if a60>0 else 0
    t['h1']='UP' if (st60>0.01 and s60>0) else ('DOWN' if (st60>0.01 and s60<0) else 'CHOP')
    lb=eps[max(0,i-100):i+1]
    if len(lb)>5:
        rh=max(lb);rl=min(lb)
        t['pos_pct']=(t['ep']-rl)/(rh-rl)*100 if rh!=rl else 50
        t['zone']='HIGH' if t['pos_pct']>80 else ('LOW' if t['pos_pct']<20 else 'MID')
    t['run_pos']=1
    for j in range(i-1,-1,-1):
        if trades[j]['dir']==t['dir']:t['run_pos']+=1
        else:break
    # Is this trade with or against H1?
    a60='ALIGNED' if (t['h1']=='UP' and t['dir']=='buy') or (t['h1']=='DOWN' and t['dir']=='sell') else ('COUNTER' if t['h1'] not in ('CHOP','WARMUP') else 'NEUTRAL')
    t['h1_align']=a60
    a15='ALIGNED' if (t['m15']=='UP' and t['dir']=='buy') or (t['m15']=='DOWN' and t['dir']=='sell') else ('COUNTER' if t['m15'] not in ('CHOP','WARMUP') else 'NEUTRAL')
    t['m15_align']=a15

wins=[t for t in trades if t['profit']>0];losses=[t for t in trades if t['profit']<0]
total_wr=len(wins)/len(trades)*100;total_pnl=sum(t['profit'] for t in trades)
print(f"WR={total_wr:.1f}% PnL=${total_pnl:.1f}")

# === 1. Win characteristics ===
print(f"\n{'='*70}")
print("1. 赢单特征 vs 亏单特征")
for label,tset in [('赢单',wins),('亏单',losses)]:
    if not tset:continue
    # MFE
    avg_mfe=sum(t['mfe_pct'] for t in tset)/len(tset)
    # Duration
    avg_dur=sum(t['dur'] for t in tset)/len(tset)
    # Direction
    dirs=Counter(t['dir'] for t in tset)
    # H1 alignment
    h1a=Counter(t['h1_align'] for t in tset)
    # M15 alignment
    m15a=Counter(t['m15_align'] for t in tset)
    # Zone
    zones=Counter(t.get('zone','?') for t in tset)
    # Exit reasons
    reasons=Counter(t['reason'] for t in tset)
    # Run position
    avg_run=sum(t['run_pos'] for t in tset)/len(tset)
    print(f"\n  {label}({len(tset)}笔): avg持仓={avg_dur:.0f}min MFE={avg_mfe:.3f}% run_pos={avg_run:.1f}")
    print(f"    方向:{dict(dirs)} H1对齐:{dict(h1a)} M15对齐:{dict(m15a)}")
    print(f"    区域:{dict(zones)} 出场:{dict(reasons.most_common(4))}")

# === 2. The "perfect setup" — what combination gives highest WR? ===
print(f"\n{'='*70}")
print("2. 最优组合: M15对齐 + H1对齐 + 区域 (WR排序)")
combo=defaultdict(lambda:{'t':0,'w':0,'pnl':0.0})
for t in trades:
    key=f"M15={t['m15_align']}+H1={t['h1_align']}+{t.get('zone','?')}"
    combo[key]['t']+=1;combo[key]['pnl']+=t['profit']
    if t['profit']>0:combo[key]['w']+=1
for key in sorted(combo.keys(),key=lambda k:-combo[k]['w']/max(1,combo[k]['t'])):
    d=combo[key];wr=d['w']/d['t']*100 if d['t']>0 else 0
    if d['t']>=5:
        print(f"  {key:<35} {d['t']:>4}t WR={wr:.0f}% PnL=${d['pnl']:>8.1f}")

# === 3. MFE analysis: how far do trades go before failing? ===
print(f"\n{'='*70}")
print("3. MFE分布 (价格在有利方向走了多远)")
mfe_buckets=[(-99,-0.1),(-0.1,-0.05),(-0.05,0),(0,0.05),(0.05,0.1),(0.1,0.2),(0.2,0.5),(0.5,99)]
for lo,hi in mfe_buckets:
    b=[t for t in trades if lo<=t['mfe_pct']<hi]
    if not b:continue
    bw=len([t for t in b if t['profit']>0])
    wr=bw/len(b)*100;p=sum(t['profit'] for t in b)
    bar='#'*min(len(b),40)
    print(f"  MFE {lo:>6}~{hi:<6}%: {len(b):>3}t WR={wr:.0f}% PnL=${p:>8.1f} {bar}")

# === 4. Exit reason deep dive ===
print(f"\n{'='*70}")
print("4. 出场原因 vs MTF对齐")
for reason in ['dtp','sl','mfe_fail','no_mfe','decay']:
    rt=[t for t in trades if reason in t['reason']]
    if not rt:continue
    r_wr=len([t for t in rt if t['profit']>0])/len(rt)*100
    r_pnl=sum(t['profit'] for t in rt)
    r_h1=Counter(t['h1_align'] for t in rt)
    print(f"  {reason:<12} {len(rt):>4}t WR={r_wr:.0f}% PnL=${r_pnl:.1f} H1对齐:{dict(r_h1)}")

# === 5. Key insight: can we filter to profitability? ===
print(f"\n{'='*70}")
print("5. 转亏为盈分析")

# Best filter: M15=ALIGNED + H1=ALIGNED (the "共振" setup)
resonance=[t for t in trades if t['m15_align']=='ALIGNED' and t['h1_align']=='ALIGNED']
res_wr=len([t for t in resonance if t['profit']>0])/len(resonance)*100 if resonance else 0
res_pnl=sum(t['profit'] for t in resonance)
print(f"  全共振(M15+H1对齐): {len(resonance)}t WR={res_wr:.1f}% PnL=${res_pnl:.1f}")

# Add zone filter: only MID zone (avoid extremes)
resonance_mid=[t for t in resonance if t.get('zone')=='MID']
res_mid_wr=len([t for t in resonance_mid if t['profit']>0])/len(resonance_mid)*100 if resonance_mid else 0
res_mid_pnl=sum(t['profit'] for t in resonance_mid)
print(f"  全共振+MID区: {len(resonance_mid)}t WR={res_mid_wr:.1f}% PnL=${res_mid_pnl:.1f}")

# Add run position filter: only first 5 in a run
resonance_early=[t for t in resonance_mid if t['run_pos']<=5]
res_early_wr=len([t for t in resonance_early if t['profit']>0])/len(resonance_early)*100 if resonance_early else 0
res_early_pnl=sum(t['profit'] for t in resonance_early)
print(f"  全共振+MID+前5笔: {len(resonance_early)}t WR={res_early_wr:.1f}% PnL=${res_early_pnl:.1f}")

# What if we ONLY took these?
only_best_pnl=res_early_pnl
all_pnl=sum(t['profit'] for t in trades)
print(f"\n  若只做'全共振+MID+前5笔': PnL=${only_best_pnl:.1f} (vs全量${all_pnl:.1f})")
if only_best_pnl>all_pnl:print(f"  >>> 转亏为盈! 改善${only_best_pnl-all_pnl:.1f}")

sf=MT5_PROFILES_DIR/'v11xau-q2deep.set'
if sf.exists():sf.unlink()
print("\n分析完成!")
