#!/usr/bin/env python3
"""验证多周期框架: 用2026-05数据测试每条规则"""
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
    dst=MT5_PROFILES_DIR/'v11xau-verify.set'
    c=BASE_SET.read_text(encoding='utf-8')
    for k,v in {'InpVersion':'V11XAU-VERIFY','InpMagicNumber':'204866','InpEnableEntryDebug':'true'}.items():c=rep(c,k,v)
    for k,v in QS4.items():c=rep(c,k,v)
    dst.write_text(c)

def kill_mt5():
    try:subprocess.run(['powershell','-Command',"Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"],capture_output=True,timeout=10)
    except:pass;time.sleep(3)

def run_bt(df,dt,to=300):
    ini=MT5_TESTER_DIR/'backtest.ini';ts=datetime.now().strftime('%Y%m%d')
    ini.write_text(f"[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\nExpertParameters=v11xau-verify.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0\nFromDate={df}\nToDate={dt}\nDeposit=200\nCurrency=USD\nLeverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport=verify_{ts}\n")
    kill_mt5()
    for o in MT5_DATA.glob('verify_*.htm'):
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
    fs=sorted(MT5_DATA.glob('verify_*.htm'),key=lambda p:p.stat().st_mtime,reverse=True)
    return fs[0] if fs else None

def slope(prices):
    n=len(prices)
    if n<3:return 0
    xm=(n-1)/2;ym=sum(prices)/n
    num=sum((i-xm)*(prices[i]-ym) for i in range(n))
    den=sum((i-xm)**2 for i in range(n))
    return num/den if den!=0 else 0

def classify_trend(eps,n):
    if len(eps)<max(5,n//2):return 'WARMUP',0
    prices=eps[-n:];s=slope(prices);avg=sum(prices)/len(prices)
    strength=abs(s)/avg*100 if avg>0 else 0
    if strength>0.015:return ('UP',strength) if s>0 else ('DOWN',strength)
    return 'CHOP',strength

def parse_trades(html_path):
    raw=html_path.read_bytes()
    try:text=raw.decode('utf-16-le')
    except:text=raw.decode('utf-8',errors='ignore')
    lines=text.split('\n');trades=[];op={}
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
                trades.append({'time':ts_str,'dir':d,'profit':profit,'bal':bal,'reason':reason,'lot':lot,'mult':mult,'ep':ei['ep'],'xp':xp,'dur':dur})
            except:pass
    return trades

# ── Run 2026-05 ──────────────────────────────────────────
print("验证多周期框架: 2026-05亏损规律")
make_set()
html=run_bt("2026.05.01","2026.05.31")
if not html:print("FAILED");sys.exit(1)
trades=parse_trades(html)
print(f"{len(trades)}笔")

eps=[t['ep'] for t in trades]
warmup=50

# Classify each trade
for i in range(warmup,len(trades)):
    t=trades[i]
    m15_dir,_=classify_trend(eps[:i+1],min(100,i))
    h1_dir,_=classify_trend(eps[:i+1],min(400,i))
    trade_dir=t['dir']

    # M15 alignment
    if m15_dir=='UP' and trade_dir=='buy':t['m15_align']='ALIGNED'
    elif m15_dir=='DOWN' and trade_dir=='sell':t['m15_align']='ALIGNED'
    elif m15_dir in ('CHOP','WARMUP'):t['m15_align']='NEUTRAL'
    else:t['m15_align']='COUNTER'

    # H1 alignment (proxy for 15M→4H relationship)
    if h1_dir=='UP' and trade_dir=='buy':t['h1_align']='ALIGNED'
    elif h1_dir=='DOWN' and trade_dir=='sell':t['h1_align']='ALIGNED'
    elif h1_dir in ('CHOP','WARMUP'):t['h1_align']='NEUTRAL'
    else:t['h1_align']='COUNTER'

    # Pressure zone: is entry near recent swing high/low?
    lookback=eps[max(0,i-100):i+1]
    if lookback:
        recent_high=max(lookback);recent_low=min(lookback)
        high_pct=(t['ep']-recent_low)/(recent_high-recent_low)*100 if recent_high!=recent_low else 50
        # Near high = >80% of range; near low = <20%
        if high_pct>80:t['zone']='NEAR_HIGH'
        elif high_pct<20:t['zone']='NEAR_LOW'
        else:t['zone']='MID'
    else:t['zone']='WARMUP'

    # Combined rule classification
    if t['m15_align']=='ALIGNED':
        if t['zone'] in ('NEAR_HIGH','NEAR_LOW'):
            # At pressure zone - need extra caution
            if trade_dir=='buy' and t['zone']=='NEAR_HIGH':t['rule']='RULE2_CAUTION'  # buy at resistance
            elif trade_dir=='sell' and t['zone']=='NEAR_LOW':t['rule']='RULE2_CAUTION'  # sell at support
            else:t['rule']='RULE1_NORMAL'  # buy at support or sell at resistance = normal
        else:t['rule']='RULE1_NORMAL'  # aligned + mid zone
    elif t['m15_align']=='COUNTER':
        if t['zone'] in ('NEAR_HIGH','NEAR_LOW'):
            t['rule']='RULE2_FORBID'  # counter + pressure zone = forbid
        else:t['rule']='RULE2_CAUTION'  # counter but mid zone = caution
    else:t['rule']='NEUTRAL'

    # H1 overlay
    if t['h1_align']=='COUNTER':
        t['rule']=t['rule']+'_H1COUNTER'  # extra danger: counter 4H

# ── Analysis ──────────────────────────────────────────────
analyzed=[t for t in trades if 'rule' in t]

# Rule performance
rule_data=defaultdict(lambda:{'t':0,'w':0,'pnl':0.0})
for t in analyzed:
    rule=t['rule']
    rule_data[rule]['t']+=1;rule_data[rule]['pnl']+=t['profit']
    if t['profit']>0:rule_data[rule]['w']+=1

print(f"\n{'='*60}")
print("框架规则验证 (2026-05):")
print(f"{'规则':<30} {'交易':>6} {'WR':>8} {'PnL':>12} {'均笔':>8}")
print(f"{'-'*65}")
total=sum(d['t'] for d in rule_data.values())
for rule in sorted(rule_data.keys()):
    d=rule_data[rule];wr=d['w']/d['t']*100 if d['t']>0 else 0
    avg=d['pnl']/d['t'] if d['t']>0 else 0
    print(f"  {rule:<30} {d['t']:>6} {wr:>7.1f}% ${d['pnl']:>10.1f} ${avg:>7.1f}")

# Pressure zone analysis
print(f"\n{'='*60}")
print("压力位 vs WR (2026-05):")
zone_data=defaultdict(lambda:{'t':0,'w':0,'pnl':0.0})
for t in analyzed:
    z=t['zone'];zone_data[z]['t']+=1;zone_data[z]['pnl']+=t['profit']
    if t['profit']>0:zone_data[z]['w']+=1
for z in ['NEAR_HIGH','MID','NEAR_LOW']:
    d=zone_data[z];wr=d['w']/d['t']*100 if d['t']>0 else 0
    print(f"  {z:<15} {d['t']:>5}t WR={wr:.1f}% PnL=${d['pnl']:.1f}")

# M15 alignment at pressure zones
print(f"\n{'='*60}")
print("M15对齐+压力位 交叉 (2026-05):")
cross=defaultdict(lambda:{'t':0,'w':0,'pnl':0.0})
for t in analyzed:
    key=f"{t['m15_align']}+{t['zone']}"
    cross[key]['t']+=1;cross[key]['pnl']+=t['profit']
    if t['profit']>0:cross[key]['w']+=1
for key in sorted(cross.keys()):
    d=cross[key];wr=d['w']/d['t']*100 if d['t']>0 else 0
    print(f"  {key:<25} {d['t']:>5}t WR={wr:.1f}% PnL=${d['pnl']:.1f}")

# Direction runs + pressure zones
print(f"\n{'='*60}")
print("亏损单在连续同向运行中的位置:")
runs=[];cur_dir=None;cur=[]
for t in trades:
    if t['dir']!=cur_dir:
        if cur:runs.append((cur_dir,cur))
        cur_dir=t['dir'];cur=[t]
    else:cur.append(t)
if cur:runs.append((cur_dir,cur))

# For losing trades, what position in the run? What zone?
loss_pos=defaultdict(lambda:{'t':0,'pnl':0.0})
for d,run in runs:
    for i,t in enumerate(run):
        if t['profit']<0 and 'zone' in t:
            pos=i+1;loss_pos[pos]['t']+=1;loss_pos[pos]['pnl']+=t['profit']
print(f"  {'运行位置':<10} {'亏损数':>6} {'PnL':>10}")
for pos in sorted(loss_pos.keys())[:20]:
    d=loss_pos[pos];print(f"  #{pos:<9} {d['t']:>6} ${d['pnl']:>9.1f}")

sf=MT5_PROFILES_DIR/'v11xau-verify.set'
if sf.exists():sf.unlink()
print("\n完成!")
