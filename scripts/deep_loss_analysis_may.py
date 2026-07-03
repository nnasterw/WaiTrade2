#!/usr/bin/env python3
"""深入到每一笔亏损单: 2026-05 QS4 逐笔趋势/压力位/方向规律"""
import os, sys, re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import math

ROOT = Path(__file__).resolve().parent.parent
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))

# Use the existing May 2026 backtest HTML
html_files = sorted(MT5_DATA.glob('rc_may*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
html_files = [h for h in html_files if h.stat().st_size > 500000]
if not html_files:
    # Fallback: run a quick backtest
    import subprocess, time
    MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
    MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
    MT5_TESTER_DIR = MT5_DATA / 'Tester'; MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
    BASE_SET = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'
    dst = MT5_PROFILES_DIR / 'v11xau-lossdeep.set'
    c = BASE_SET.read_text(encoding='utf-8')
    for k,v in {'InpVersion':'V11XAU-LOSSDEEP','InpMagicNumber':'204866','InpEnableEntryDebug':'true'}.items():
        p=re.compile(rf'^{k}=.*$',re.MULTILINE)
        c=p.sub(f'{k}={v}',c) if p.search(c) else c+f'\n{k}={v}\n'
    for k,v in {'InpBouncePct':'0.30','InpBounceSweetMinPct':'0.35','InpOutsideBounceSweetMult':'0.4','InpMaxCounterRiskATR':'0.5','InpMaxEntriesPerOB':'2','InpEnableDeepestPullbackSL':'true','InpDeepestPullbackBuffer':'0.5'}.items():
        p=re.compile(rf'^{k}=.*$',re.MULTILINE)
        c=p.sub(f'{k}={v}',c) if p.search(c) else c+f'\n{k}={v}\n'
    dst.write_text(c)
    try:subprocess.run(['powershell','-Command',"Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"],capture_output=True,timeout=10)
    except:pass;time.sleep(3)
    ts=datetime.now().strftime('%Y%m%d')
    ini=MT5_TESTER_DIR/'backtest.ini'
    ini.write_text(f"[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\nExpertParameters=v11xau-lossdeep.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0\nFromDate=2026.05.01\nToDate=2026.05.31\nDeposit=200\nCurrency=USD\nLeverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport=lossdeep_{ts}\n")
    for o in MT5_DATA.glob('lossdeep*.htm'):
        try:o.unlink()
        except:pass
    subprocess.Popen([MT5_TERMINAL,f'/config:{ini}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print("Running 2026-05 backtest...")
    for i in range(60):
        time.sleep(5)
        try:
            r=subprocess.run(['powershell','-Command',"(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' }).Count"],capture_output=True,text=True,timeout=5)
            if r.stdout.strip()=='0':break
        except:pass
    time.sleep(2)
    html_files=sorted(MT5_DATA.glob('lossdeep*.htm'),key=lambda p:p.stat().st_mtime,reverse=True)

if not html_files:print("NO HTML");sys.exit(1)
html_path=html_files[0]
print(f"Using: {html_path.name}")

# Parse
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
            trades.append({'time':ts_str,'dir':d,'profit':profit,'bal':bal,'reason':reason,'lot':lot,'mult':mult,'ep':ei['ep'],'xp':xp,'dur':dur,'cmt':ei['cmt']})
        except:pass

print(f"{len(trades)}笔交易")

# Classify each trade by trend context
eps=[t['ep'] for t in trades]

def slope(px,n=None):
    if n is None:n=len(px)
    px=px[-n:]
    if len(px)<3:return 0
    xm=(len(px)-1)/2;ym=sum(px)/len(px)
    num=sum((i-xm)*(px[i]-ym) for i in range(len(px)))
    den=sum((i-xm)**2 for i in range(len(px)))
    return num/den if den!=0 else 0

for i,t in enumerate(trades):
    # M15 trend (last ~100 trades)
    s15=slope(eps[:i+1],min(100,i+1))
    avg15=sum(eps[max(0,i-99):i+1])/min(100,i+1)
    str15=abs(s15)/avg15*100 if avg15>0 else 0
    if str15>0.015:t['m15']='UP' if s15>0 else 'DOWN'
    else:t['m15']='CHOP'

    # H1 trend (last ~400 trades)
    s60=slope(eps[:i+1],min(400,i+1))
    avg60=sum(eps[max(0,i-399):i+1])/min(400,i+1)
    str60=abs(s60)/avg60*100 if avg60>0 else 0
    if str60>0.01:t['h1']='UP' if s60>0 else 'DOWN'
    else:t['h1']='CHOP'

    # Pressure zone
    lookback=eps[max(0,i-100):i+1]
    if len(lookback)>5:
        rh=max(lookback);rl=min(lookback)
        t['pos_pct']=(t['ep']-rl)/(rh-rl)*100 if rh!=rl else 50
        if t['pos_pct']>80:t['zone']='HIGH'
        elif t['pos_pct']<20:t['zone']='LOW'
        else:t['zone']='MID'

    # Direction run position
    t['run_pos']=1
    for j in range(i-1,-1,-1):
        if trades[j]['dir']==t['dir']:t['run_pos']+=1
        else:break

    # MTF rule classification
    a15='ALIGNED' if (t['m15']=='UP' and t['dir']=='buy') or (t['m15']=='DOWN' and t['dir']=='sell') else ('COUNTER' if t['m15'] not in ('CHOP','WARMUP') else 'NEUTRAL')
    a60='ALIGNED' if (t['h1']=='UP' and t['dir']=='buy') or (t['h1']=='DOWN' and t['dir']=='sell') else ('COUNTER' if t['h1'] not in ('CHOP','WARMUP') else 'NEUTRAL')

    if a60=='COUNTER':t['mtf_rule']='R5_BLOCK'  # 逆4H+压力位
    elif a15=='COUNTER' and 'zone' in t and t['zone'] in ('HIGH','LOW'):t['mtf_rule']='R4_BLOCK'  # 逆15M+压力位
    elif a15=='COUNTER':t['mtf_rule']='R3_REDUCE'  # 逆15M降权
    elif a15=='ALIGNED' and 'zone' in t and t['zone'] in ('HIGH','LOW') and t['run_pos']>5:t['mtf_rule']='R1_CAUTION'  # 同向但压力位+深追
    else:t['mtf_rule']='OK'

# ── Analysis ──────────────────────────────────────────────
losses=[t for t in trades if t['profit']<0]
wins=[t for t in trades if t['profit']>0]
print(f"\n盈利:{len(wins)}笔 亏损:{len(losses)}笔 WR={len(wins)/len(trades)*100:.1f}%")

# 1. Each losing trade by MTF rule
print(f"\n{'='*90}")
print(f"每笔亏损单的MTF框架分析 ({len(losses)}笔)")
print(f"{'='*90}")
rule_loss=defaultdict(lambda:{'t':0,'pnl':0.0,'examples':[]})
for t in sorted(losses,key=lambda x:x['profit']):
    rule=t['mtf_rule'];rule_loss[rule]['t']+=1;rule_loss[rule]['pnl']+=t['profit']
    if len(rule_loss[rule]['examples'])<3:
        rule_loss[rule]['examples'].append(t)

print(f"\n{'规则':<18} {'亏损数':>6} {'PnL':>10} {'占比':>8} {'示例':>40}")
print(f"{'-'*85}")
for rule in ['R5_BLOCK','R4_BLOCK','R3_REDUCE','R1_CAUTION','OK']:
    d=rule_loss[rule]
    if d['t']==0:continue
    pct=d['t']/len(losses)*100
    examples='; '.join(f"{t['time'][-8:]} {t['dir']} ${t['profit']:.0f}" for t in d['examples'])
    print(f"  {rule:<18} {d['t']:>6} ${d['pnl']:>9.1f} {pct:>7.1f}% {examples}")

# 2. If framework blocked R5+R4
blocked=rule_loss['R5_BLOCK']['t']+rule_loss['R4_BLOCK']['t']
blocked_pnl=rule_loss['R5_BLOCK']['pnl']+rule_loss['R4_BLOCK']['pnl']
reduced=rule_loss['R3_REDUCE']['t'];reduced_pnl=rule_loss['R3_REDUCE']['pnl']
print(f"\n若MTF框架阻止: R5+R4 = {blocked}笔 节省${-blocked_pnl:.1f}")
print(f"若MTF框架降权: R3     = {reduced}笔 可减少${-reduced_pnl:.1f}×降权比例")

# 3. Top 20 worst losses with full context
print(f"\n{'='*120}")
print(f"Top 20 最大亏损 — 完整MTF上下文")
print(f"{'='*120}")
print(f"{'时间':<22} {'方向':>4} {'亏损':>8} {'倍率':>5} {'M15':>5} {'H1':>5} {'压力位':>8} {'运行#':>5} {'MTF规则':<15} {'出场原因':>20}")
print(f"{'-'*120}")
for t in sorted(losses,key=lambda x:x['profit'])[:20]:
    zone_str=f"{t.get('pos_pct',50):.0f}%{t.get('zone','?')}" if 'zone' in t else '?'
    print(f"{t['time']:<22} {t['dir']:>4} ${t['profit']:>7.1f} x{t['mult']:>4.1f} {t.get('m15','?'):>5} {t.get('h1','?'):>5} {zone_str:>8} #{t.get('run_pos',0):>4} {t.get('mtf_rule','?'):<15} {t['reason'][:20]}")

# 4. "本可不亏" — trades that framework would have prevented
saved=[t for t in losses if t['mtf_rule'] in ('R5_BLOCK','R4_BLOCK')]
print(f"\n框架可阻止的亏损单详情 ({len(saved)}笔, ${sum(t['profit'] for t in saved):.1f}):")
for t in sorted(saved,key=lambda x:x['profit']):
    print(f"  {t['time']} {t['dir']} ${t['profit']:>6.1f} M15={t['m15']} H1={t['h1']} zone={t.get('zone','?')} run=#{t['run_pos']} reason={t['reason'][:30]}")

# 5. Win trades that framework would have kept
kept_wins=[t for t in wins if t['mtf_rule'] in ('OK','R1_CAUTION','R3_REDUCE')]
lost_wins=[t for t in wins if t['mtf_rule'] in ('R4_BLOCK','R5_BLOCK')]
print(f"\n框架保留的盈利单: {len(kept_wins)}笔 PnL=${sum(t['profit'] for t in kept_wins):.1f}")
print(f"框架误杀的盈利单: {len(lost_wins)}笔 PnL=${sum(t['profit'] for t in lost_wins):.1f}")

# Cleanup
sf=MT5_PROFILES_DIR/'v11xau-lossdeep.set'
if sf.exists():sf.unlink()
print("\n亏损分析完成!")
