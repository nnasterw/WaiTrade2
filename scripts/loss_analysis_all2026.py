#!/usr/bin/env python3
"""2026全5月亏损单大样本分析 — MTF框架规律"""
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

QS4 = {'InpBouncePct':'0.30','InpBounceSweetMinPct':'0.35','InpOutsideBounceSweetMult':'0.4',
       'InpMaxCounterRiskATR':'0.5','InpMaxEntriesPerOB':'2',
       'InpEnableDeepestPullbackSL':'true','InpDeepestPullbackBuffer':'0.5'}

def rep(c,k,v):
    p=re.compile(rf'^{k}=.*$',re.MULTILINE)
    return p.sub(f'{k}={v}',c) if p.search(c) else c+f'\n{k}={v}\n'

def make_set():
    dst=MT5_PROFILES_DIR/'v11xau-lossall.set'
    c=BASE_SET.read_text(encoding='utf-8')
    for k,v in {'InpVersion':'V11XAU-LOSSALL','InpMagicNumber':'204866','InpEnableEntryDebug':'true'}.items():c=rep(c,k,v)
    for k,v in QS4.items():c=rep(c,k,v)
    dst.write_text(c)

def kill_mt5():
    try:subprocess.run(['powershell','-Command',"Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"],capture_output=True,timeout=10)
    except:pass;time.sleep(3)

def run_bt(df,dt,to=300):
    ini=MT5_TESTER_DIR/'backtest.ini';ts=datetime.now().strftime('%Y%m%d')
    ini.write_text(f"[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\nExpertParameters=v11xau-lossall.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0\nFromDate={df}\nToDate={dt}\nDeposit=200\nCurrency=USD\nLeverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport=lossall_{ts}\n")
    kill_mt5()
    for o in MT5_DATA.glob('lossall_*.htm'):
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
    fs=sorted(MT5_DATA.glob('lossall_*.htm'),key=lambda p:p.stat().st_mtime,reverse=True)
    return fs[0] if fs else None

def slope(px,n=None):
    if n is None:n=len(px);px=px[-n:]
    if len(px)<3:return 0
    xm=(len(px)-1)/2;ym=sum(px)/len(px)
    num=sum((i-xm)*(px[i]-ym) for i in range(len(px)))
    den=sum((i-xm)**2 for i in range(len(px)))
    return num/den if den!=0 else 0

def analyze_month(html_path,label):
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
                trades.append({'time':ts_str,'dir':d,'profit':profit,'bal':bal,'reason':reason,'lot':lot,'mult':mult,'ep':ei['ep'],'xp':xp,'dur':dur})
            except:pass

    # Classify
    eps=[t['ep'] for t in trades]
    for i,t in enumerate(trades):
        # M15
        s15=slope(eps[:i+1],min(100,i+1))
        a=sum(eps[max(0,i-99):i+1])/min(100,i+1)
        st=abs(s15)/a*100 if a>0 else 0
        t['m15']='UP' if (st>0.015 and s15>0) else ('DOWN' if (st>0.015 and s15<0) else 'CHOP')
        # H1
        s60=slope(eps[:i+1],min(400,i+1))
        a60=sum(eps[max(0,i-399):i+1])/min(400,i+1)
        st60=abs(s60)/a60*100 if a60>0 else 0
        t['h1']='UP' if (st60>0.01 and s60>0) else ('DOWN' if (st60>0.01 and s60<0) else 'CHOP')
        # Pressure
        lb=eps[max(0,i-100):i+1]
        if len(lb)>5:
            rh=max(lb);rl=min(lb)
            t['pos_pct']=(t['ep']-rl)/(rh-rl)*100 if rh!=rl else 50
            t['zone']='HIGH' if t['pos_pct']>80 else ('LOW' if t['pos_pct']<20 else 'MID')
        # Run position
        t['run_pos']=1
        for j in range(i-1,-1,-1):
            if trades[j]['dir']==t['dir']:t['run_pos']+=1
            else:break
        # MTF rule
        a15='ALIGNED' if (t['m15']=='UP' and t['dir']=='buy') or (t['m15']=='DOWN' and t['dir']=='sell') else ('COUNTER' if t['m15'] not in ('CHOP','WARMUP') else 'NEUTRAL')
        a60='ALIGNED' if (t['h1']=='UP' and t['dir']=='buy') or (t['h1']=='DOWN' and t['dir']=='sell') else ('COUNTER' if t['h1'] not in ('CHOP','WARMUP') else 'NEUTRAL')
        if a60=='COUNTER':t['rule']='R5_H1_COUNTER'
        elif a15=='COUNTER' and t.get('zone') in ('HIGH','LOW'):t['rule']='R4_M15_COUNTER_ZONE'
        elif a15=='COUNTER':t['rule']='R3_M15_COUNTER'
        elif a15=='ALIGNED' and t.get('zone') in ('HIGH','LOW') and t['run_pos']>5:t['rule']='R1b_ALIGNED_DEEP'
        elif a15=='ALIGNED':t['rule']='R1_ALIGNED_OK'
        else:t['rule']='NEUTRAL'

    losses=[t for t in trades if t['profit']<0 and 'rule' in t]
    wins=[t for t in trades if t['profit']>0 and 'rule' in t]
    total=len(trades)
    wr=len(wins)/total*100 if total>0 else 0
    total_pnl=sum(t['profit'] for t in trades)

    # Rule stats
    rule_stats=defaultdict(lambda:{'loss_t':0,'loss_pnl':0.0,'win_t':0,'win_pnl':0.0,'total_t':0})
    for t in trades:
        if 'rule' not in t:continue
        r=t['rule'];rule_stats[r]['total_t']+=1
        if t['profit']<0:rule_stats[r]['loss_t']+=1;rule_stats[r]['loss_pnl']+=t['profit']
        else:rule_stats[r]['win_t']+=1;rule_stats[r]['win_pnl']+=t['profit']

    return {'trades':trades,'losses':losses,'wins':wins,'total':total,'wr':wr,'pnl':total_pnl,'rule_stats':rule_stats}

# ── Run all 5 months ──────────────────────────────────────
MONTHS=[("2026.01.01","2026.01.31","2026-01"),("2026.02.01","2026.02.28","2026-02"),
        ("2026.03.01","2026.03.31","2026-03"),("2026.04.01","2026.04.30","2026-04"),
        ("2026.05.01","2026.05.31","2026-05")]

print("2026全5月亏损大样本分析")
make_set()

all_data={}
for df,dt,label in MONTHS:
    print(f"\n[{label}] ",end='',flush=True)
    html=run_bt(df,dt)
    if html:all_data[label]=analyze_month(html,label)
    d=all_data[label]
    print(f"{d['total']}t WR={d['wr']:.1f}% PnL=${d['pnl']:.1f} 亏损{d['losses'].__len__()}笔")

# ── Aggregate across all months ────────────────────────────
print(f"\n{'='*80}")
print(f"全5月汇总: MTF规则 vs 亏损分布")
print(f"{'='*80}")

agg_rules=defaultdict(lambda:{'loss_t':0,'loss_pnl':0.0,'win_t':0,'win_pnl':0.0,'total_t':0})
agg_zones=defaultdict(lambda:{'loss_t':0,'loss_pnl':0.0,'win_t':0,'win_pnl':0.0})
agg_dir=defaultdict(lambda:{'loss_t':0,'win_t':0})
agg_run=defaultdict(lambda:{'loss_t':0,'loss_pnl':0.0})
all_losses=[]

for label,data in all_data.items():
    for t in data['trades']:
        if 'rule' not in t:continue
        r=t['rule'];agg_rules[r]['total_t']+=1
        if t['profit']<0:agg_rules[r]['loss_t']+=1;agg_rules[r]['loss_pnl']+=t['profit'];all_losses.append(t)
        else:agg_rules[r]['win_t']+=1;agg_rules[r]['win_pnl']+=t['profit']
        # Zone
        if 'zone' in t:z=t['zone']
        else:z='UNKNOWN'
        if t['profit']<0:agg_zones[z]['loss_t']+=1;agg_zones[z]['loss_pnl']+=t['profit']
        else:agg_zones[z]['win_t']+=1;agg_zones[z]['win_pnl']+=t['profit']
        # Direction+M15
        d=f"{t['dir']}+{t['m15']}";agg_dir[d]['loss_t']+=1 if t['profit']<0 else 0;agg_dir[d]['win_t']+=1 if t['profit']>0 else 0
        # Run position
        rp=t['run_pos'];agg_run[rp]['loss_t']+=1 if t['profit']<0 else 0;agg_run[rp]['loss_pnl']+=t['profit'] if t['profit']<0 else 0

total_losses=len(all_losses);total_loss_pnl=sum(t['profit'] for t in all_losses)
print(f"\n总亏损单: {total_losses}笔, 总亏损: ${total_loss_pnl:.0f}")

# 1. Rule breakdown
print(f"\n{'规则':<22} {'亏损数':>7} {'亏损额':>10} {'占比':>7} {'盈利数':>7} {'净效果':>12}")
print(f"{'-'*65}")
for rule in ['R5_H1_COUNTER','R4_M15_COUNTER_ZONE','R3_M15_COUNTER','R1b_ALIGNED_DEEP','R1_ALIGNED_OK','NEUTRAL']:
    d=agg_rules[rule]
    if d['total_t']==0:continue
    pct=d['loss_t']/total_losses*100
    net=d['win_pnl']+d['loss_pnl']
    print(f"  {rule:<22} {d['loss_t']:>7} ${d['loss_pnl']:>9.0f} {pct:>6.1f}% {d['win_t']:>7} ${net:>10.0f}")

# 2. Pressure zone across all losses
print(f"\n压力位 vs 亏损 (全5月):")
print(f"{'区域':<12} {'亏损数':>7} {'亏损额':>10} {'盈利数':>7} {'盈利额':>10} {'净效果':>10}")
for z in ['HIGH','MID','LOW','UNKNOWN']:
    d=agg_zones[z];net=d['win_pnl']+d['loss_pnl']
    print(f"  {z:<12} {d['loss_t']:>7} ${d['loss_pnl']:>9.0f} {d['win_t']:>7} ${d['win_pnl']:>9.0f} ${net:>9.0f}")

# 3. Direction + M15 cross
print(f"\n方向+M15趋势 vs WR (全5月):")
for dkey in sorted(agg_dir.keys(),key=lambda x:-agg_dir[x]['loss_t']):
    d=agg_dir[dkey];total=d['win_t']+d['loss_t']
    wr=d['win_t']/total*100 if total>0 else 0
    if total>=20:print(f"  {dkey:<12} {total:>5}t WR={wr:.0f}% 亏损={d['loss_t']}笔")

# 4. Run position vs loss concentration
print(f"\n运行位置 vs 亏损集中度 (全5月):")
cum=0
for pos in sorted(agg_run.keys())[:20]:
    d=agg_run[pos];cum+=d['loss_t']
    pct=d['loss_t']/total_losses*100;cum_pct=cum/total_losses*100
    print(f"  #{pos:<4} {d['loss_t']:>5}笔 (${d['loss_pnl']:>8.0f}) {pct:>5.1f}% 累计{cum_pct:.0f}%")

# 5. Key insight: what % can be prevented?
blockable=agg_rules['R5_H1_COUNTER']['loss_pnl']+agg_rules['R4_M15_COUNTER_ZONE']['loss_pnl']
reducible=agg_rules['R1b_ALIGNED_DEEP']['loss_pnl']*0.5  # half reduction
print(f"\n可阻止(R5+R4): ${-blockable:.0f} ({-blockable/total_loss_pnl*100:.0f}% of losses)")
print(f"可降权(R1b):    ${-reducible:.0f} (同向深追降权50%)")
print(f"框架可挽回:     ${-blockable-reducible:.0f}")

sf=MT5_PROFILES_DIR/'v11xau-lossall.set'
if sf.exists():sf.unlink()
print("\n全5月分析完成!")
