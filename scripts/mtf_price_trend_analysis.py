#!/usr/bin/env python3
"""多周期对齐v2: 用入场价格趋势推断M15/H1方向"""
import os, sys, re, time, subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import math

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
MT5_TESTER_DIR = MT5_DATA / 'Tester'; MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
BASE_SET = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'

QS4 = {'InpBouncePct':'0.30','InpBounceSweetMinPct':'0.35','InpOutsideBounceSweetMult':'0.4',
       'InpMaxCounterRiskATR':'0.5','InpMaxEntriesPerOB':'2',
       'InpEnableDeepestPullbackSL':'true','InpDeepestPullbackBuffer':'0.5'}

def rep(c,k,v):
    p=re.compile(rf'^{k}=.*$',re.MULTILINE)
    return p.sub(f'{k}={v}',c) if p.search(c) else c+f'\n{k}={v}\n'

def make_set():
    dst=MT5_PROFILES_DIR/'v11xau-mtf2.set'
    c=BASE_SET.read_text(encoding='utf-8')
    for k,v in {'InpVersion':'V11XAU-MTF2','InpMagicNumber':'204866','InpEnableEntryDebug':'true'}.items():c=rep(c,k,v)
    for k,v in QS4.items():c=rep(c,k,v)
    dst.write_text(c)

def kill_mt5():
    try:subprocess.run(['powershell','-Command',"Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"],capture_output=True,timeout=10)
    except:pass;time.sleep(3)

def run_bt(df,dt,to=300):
    ini=MT5_TESTER_DIR/'backtest.ini';ts=datetime.now().strftime('%Y%m%d')
    ini.write_text(f"[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\nExpertParameters=v11xau-mtf2.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0\nFromDate={df}\nToDate={dt}\nDeposit=200\nCurrency=USD\nLeverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport=mtf2_{ts}\n")
    kill_mt5()
    for o in MT5_DATA.glob('mtf2_*.htm'):
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
    fs=sorted(MT5_DATA.glob('mtf2_*.htm'),key=lambda p:p.stat().st_mtime,reverse=True)
    return fs[0] if fs else None

def slope(prices):
    """Linear regression slope of prices"""
    n=len(prices)
    if n<3:return 0
    x_mean=(n-1)/2;y_mean=sum(prices)/n
    num=sum((i-x_mean)*(prices[i]-y_mean) for i in range(n))
    den=sum((i-x_mean)**2 for i in range(n))
    return num/den if den!=0 else 0

def classify_trend(eps, n):
    """Classify trend direction from last N entry prices"""
    if len(eps)<max(5,n//2):return 'WARMUP',0
    prices=eps[-n:]
    s=slope(prices)
    avg=sum(prices)/len(prices)
    strength=abs(s)/avg*100 if avg>0 else 0  # % change per trade
    if strength>0.02:return ('UP',strength) if s>0 else ('DOWN',strength)
    return 'CHOP',strength

def analyze_month(trades,label):
    """For each trade, classify M15(100t) and H1(400t) trend from entry prices"""
    eps=[t['ep'] for t in trades]
    results=defaultdict(lambda:{'t':0,'w':0,'pnl':0.0})
    details=[]

    warmup=50
    for i in range(warmup,len(trades)):
        t=trades[i]
        # M15 trend from last ~100 entry prices (~15 min of trading)
        m15_dir,m15_str=classify_trend(eps[:i+1],min(100,i))
        # H1 trend from last ~400 entry prices (~60 min)
        h1_dir,h1_str=classify_trend(eps[:i+1],min(400,i))

        trade_dir=t['dir']
        # Alignment
        if h1_dir=='UP' and trade_dir=='buy':h1_align='ALIGNED'
        elif h1_dir=='DOWN' and trade_dir=='sell':h1_align='ALIGNED'
        elif h1_dir in ('CHOP','WARMUP'):h1_align='NEUTRAL'
        else:h1_align='COUNTER'

        if m15_dir=='UP' and trade_dir=='buy':m15_align='ALIGNED'
        elif m15_dir=='DOWN' and trade_dir=='sell':m15_align='ALIGNED'
        elif m15_dir in ('CHOP','WARMUP'):m15_align='NEUTRAL'
        else:m15_align='COUNTER'

        # Combined
        if h1_align=='COUNTER':cat='H1_COUNTER'
        elif m15_align=='COUNTER' and h1_align!='ALIGNED':cat='M15_COUNTER'
        elif m15_align=='ALIGNED' and h1_align=='ALIGNED':cat='FULL_ALIGNED'
        elif h1_align=='ALIGNED':cat='H1_ALIGNED'
        else:cat='NEUTRAL'

        results[cat]['t']+=1;results[cat]['pnl']+=t['profit']
        if t['profit']>0:results[cat]['w']+=1
        details.append({'cat':cat,'profit':t['profit'],'h1_dir':h1_dir,'m15_dir':m15_dir,'dir':trade_dir})

    print(f"\n  MTF对齐 vs WR (价格趋势法):")
    print(f"  {'类别':<20} {'交易':>6} {'WR':>8} {'PnL':>12} {'占比':>8}")
    print(f"  {'-'*54}")
    total_t=sum(d['t'] for d in results.values())
    for cat in ['FULL_ALIGNED','H1_ALIGNED','NEUTRAL','M15_COUNTER','H1_COUNTER']:
        d=results[cat]
        if d['t']==0:continue
        wr=d['w']/d['t']*100
        print(f"  {cat:<20} {d['t']:>6} {wr:>7.1f}% ${d['pnl']:>10.1f} {d['t']/total_t*100:>7.1f}%")

    # Key metrics
    counter_t=results['H1_COUNTER']['t']+results['M15_COUNTER']['t']
    counter_pnl=results['H1_COUNTER']['pnl']+results['M15_COUNTER']['pnl']
    aligned_t=results['FULL_ALIGNED']['t']+results['H1_ALIGNED']['t']
    aligned_pnl=results['FULL_ALIGNED']['pnl']+results['H1_ALIGNED']['pnl']
    neutral_t=results['NEUTRAL']['t'];neutral_pnl=results['NEUTRAL']['pnl']

    print(f"\n  逆周期: {counter_t}t ${counter_pnl:.1f} avg=${counter_pnl/max(1,counter_t):.1f}/t")
    print(f"  顺周期: {aligned_t}t ${aligned_pnl:.1f} avg=${aligned_pnl/max(1,aligned_t):.1f}/t")
    print(f"  中性:   {neutral_t}t ${neutral_pnl:.1f} avg=${neutral_pnl/max(1,neutral_t):.1f}/t")

    # If we blocked counter-trend
    saved=-(results['H1_COUNTER']['pnl']+results['M15_COUNTER']['pnl'])
    print(f"  若阻止逆周期: 节省${saved:.1f}")

    return results,details

# ── Main ──────────────────────────────────────────────────
print("MTF价格趋势分析: 2025-10 vs 2026-05")
make_set()

all_data={}
for label,df,dt in [("2025-10_GOOD","2025.10.01","2025.10.31"),("2026-05_BAD","2026.05.01","2026.05.31")]:
    print(f"\n{'='*60}\n[{label}]")
    html=run_bt(df,dt)
    if not html:print("FAILED");continue
    trades=[]
    raw=html.read_bytes()
    try:text=raw.decode('utf-16-le')
    except:text=raw.decode('utf-8',errors='ignore')
    lines=text.split('\n');op={}
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
                trades.append({'time':ts_str,'dir':d,'profit':profit,'bal':bal,'reason':reason,'lot':lot,'mult':mult,'ep':ei['ep']})
            except:pass
    print(f"  {len(trades)}笔")
    all_data[label]=analyze_month(trades,label)

# ── Cross-month comparison ──────────────────────────────
print(f"\n{'='*60}\n跨月对比总结")
good_r,good_d=all_data.get('2025-10_GOOD',({},[]))
bad_r,bad_d=all_data.get('2026-05_BAD',({},[]))

if good_r and bad_r:
    print(f"\n  {'类别':<20} {'好月WR':>10} {'好月PnL':>12} {'坏月WR':>10} {'坏月PnL':>12}")
    print(f"  {'-'*65}")
    for cat in ['FULL_ALIGNED','H1_ALIGNED','NEUTRAL','M15_COUNTER','H1_COUNTER']:
        g=good_r.get(cat);b=bad_r.get(cat)
        gw=g['w']/g['t']*100 if g and g['t']>0 else 0
        bw=b['w']/b['t']*100 if b and b['t']>0 else 0
        gp=g['pnl'] if g else 0;bp=b['pnl'] if b else 0
        gt=g['t'] if g else 0;bt=b['t'] if b else 0
        print(f"  {cat:<20} {gw:>9.1f}%({gt}t) ${gp:>10.1f} {bw:>9.1f}%({bt}t) ${bp:>10.1f}")

sf=MT5_PROFILES_DIR/'v11xau-mtf2.set'
if sf.exists():sf.unlink()
print("\n完成!")
