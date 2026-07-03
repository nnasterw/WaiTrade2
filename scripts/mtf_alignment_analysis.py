#!/usr/bin/env python3
"""多周期对齐分析: 好月vs坏月 — 每笔交易的M1/M15/H1方向对齐度 vs WR"""
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
    dst=MT5_PROFILES_DIR/'v11xau-mtf.set'
    c=BASE_SET.read_text(encoding='utf-8')
    for k,v in {'InpVersion':'V11XAU-MTF','InpMagicNumber':'204866','InpEnableEntryDebug':'true','InpEnableExitDebug':'true'}.items():c=replace_param(c,k,v)
    for k,v in QS4.items():c=replace_param(c,k,v)
    dst.write_text(c)

def kill_mt5():
    try:subprocess.run(['powershell','-Command',"Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"],capture_output=True,timeout=10)
    except:pass;time.sleep(3)

def run_bt(df,dt,to=300):
    ini=MT5_TESTER_DIR/'backtest.ini';ts=datetime.now().strftime('%Y%m%d')
    ini.write_text(f"[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\nExpertParameters=v11xau-mtf.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0\nFromDate={df}\nToDate={dt}\nDeposit=200\nCurrency=USD\nLeverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport=mtf_{ts}\n")
    kill_mt5()
    for o in MT5_DATA.glob('mtf_*.htm'):
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
    fs=sorted(MT5_DATA.glob('mtf_*.htm'),key=lambda p:p.stat().st_mtime,reverse=True)
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
                trades.append({'time':ts_str,'dir':d,'profit':profit,'bal':bal,'reason':reason,'lot':lot,'mult':mult,'dur':dur})
            except:pass
    return trades

# ── Infer M15 and H1 direction from trade sequence ────────
def infer_mtf_direction(trades, i, window_min):
    """At trade i, infer the prevailing M15/H1 direction from surrounding trades"""
    t_time = datetime.strptime(trades[i]['time'], '%Y.%m.%d %H:%M:%S')

    # M15: look at last 15 minutes of trades
    m15_buys = 0; m15_sells = 0
    for j in range(max(0,i-100), i):
        try:
            jt = datetime.strptime(trades[j]['time'], '%Y.%m.%d %H:%M:%S')
            if (t_time - jt).total_seconds() <= 900:  # 15 min
                if trades[j]['dir'] == 'buy': m15_buys += 1
                else: m15_sells += 1
        except: pass

    # H1: look at last 60 minutes
    h1_buys = 0; h1_sells = 0
    for j in range(max(0,i-500), i):
        try:
            jt = datetime.strptime(trades[j]['time'], '%Y.%m.%d %H:%M:%S')
            if (t_time - jt).total_seconds() <= 3600:
                if trades[j]['dir'] == 'buy': h1_buys += 1
                else: h1_sells += 1
        except: pass

    total_m15 = m15_buys + m15_sells
    total_h1 = h1_buys + h1_sells

    # Classify M15 direction
    if total_m15 >= 10:
        if m15_buys/total_m15 >= 0.65: m15_dir = 'UP'
        elif m15_sells/total_m15 >= 0.65: m15_dir = 'DOWN'
        else: m15_dir = 'CHOP'
    else: m15_dir = 'WARMUP'

    # Classify H1 direction
    if total_h1 >= 20:
        if h1_buys/total_h1 >= 0.65: h1_dir = 'UP'
        elif h1_sells/total_h1 >= 0.65: h1_dir = 'DOWN'
        else: h1_dir = 'CHOP'
    else: h1_dir = 'WARMUP'

    # Trade alignment
    trade_dir = trades[i]['dir']  # 'buy' or 'sell'

    # Alignment with M15
    if m15_dir == 'UP' and trade_dir == 'buy': m15_align = 'ALIGNED'
    elif m15_dir == 'DOWN' and trade_dir == 'sell': m15_align = 'ALIGNED'
    elif m15_dir == 'CHOP' or m15_dir == 'WARMUP': m15_align = 'NEUTRAL'
    else: m15_align = 'COUNTER'

    # Alignment with H1
    if h1_dir == 'UP' and trade_dir == 'buy': h1_align = 'ALIGNED'
    elif h1_dir == 'DOWN' and trade_dir == 'sell': h1_align = 'ALIGNED'
    elif h1_dir == 'CHOP' or h1_dir == 'WARMUP': h1_align = 'NEUTRAL'
    else: h1_align = 'COUNTER'

    # Combined alignment category
    if h1_align == 'COUNTER':
        combined = 'H1_COUNTER'        # 逆大周期 — 最危险
    elif m15_align == 'COUNTER' and h1_align != 'ALIGNED':
        combined = 'M15_COUNTER'       # 逆中周期
    elif m15_align == 'ALIGNED' and h1_align == 'ALIGNED':
        combined = 'FULL_ALIGNED'      # 全共振 — 最安全
    elif h1_align == 'ALIGNED':
        combined = 'H1_ALIGNED'        # 跟大周期
    else:
        combined = 'NEUTRAL'           # 无明确方向

    return {
        'm15_dir': m15_dir, 'h1_dir': h1_dir,
        'm15_align': m15_align, 'h1_align': h1_align,
        'combined': combined,
        'm15_buys': m15_buys, 'm15_sells': m15_sells,
        'h1_buys': h1_buys, 'h1_sells': h1_sells,
    }

# ── Main ──────────────────────────────────────────────────
print("多周期对齐分析: 2025-10 vs 2026-05")
make_set()

for label,df,dt in [("2025-10_GOOD","2025.10.01","2025.10.31"),("2026-05_BAD","2026.05.01","2026.05.31")]:
    print(f"\n[{label}] 回测...",end=' ',flush=True)
    html=run_bt(df,dt)
    if not html:print("FAILED");continue
    trades=parse(html)
    print(f"{len(trades)}笔")

    # Infer MTF alignment for each trade (skip first N for warmup)
    align_data=defaultdict(lambda:{'t':0,'w':0,'pnl':0.0})
    skip=50  # warmup period
    for i in range(skip, len(trades)):
        mtf=infer_mtf_direction(trades,i,15)
        cat=mtf['combined']
        align_data[cat]['t']+=1
        align_data[cat]['pnl']+=trades[i]['profit']
        if trades[i]['profit']>0:align_data[cat]['w']+=1

    print(f"\n  多周期对齐 vs WR/PnL:")
    print(f"  {'类别':<20} {'交易':>6} {'WR':>8} {'PnL':>12} {'占比':>8}")
    print(f"  {'-'*54}")
    total_t=sum(d['t'] for d in align_data.values())
    for cat in ['FULL_ALIGNED','H1_ALIGNED','NEUTRAL','M15_COUNTER','H1_COUNTER']:
        d=align_data[cat]
        if d['t']==0:continue
        wr=d['w']/d['t']*100
        print(f"  {cat:<20} {d['t']:>6} {wr:>7.1f}% ${d['pnl']:>10.1f} {d['t']/total_t*100:>7.1f}%")

    # Counter-trend trade analysis
    counter_t=align_data['H1_COUNTER']['t']+align_data['M15_COUNTER']['t']
    counter_pnl=align_data['H1_COUNTER']['pnl']+align_data['M15_COUNTER']['pnl']
    aligned_t=align_data['FULL_ALIGNED']['t']+align_data['H1_ALIGNED']['t']
    aligned_pnl=align_data['FULL_ALIGNED']['pnl']+align_data['H1_ALIGNED']['pnl']
    print(f"\n  逆大周期: {counter_t}t PnL=${counter_pnl:.1f} ({counter_t/total_t*100:.0f}%)")
    print(f"  顺大周期: {aligned_t}t PnL=${aligned_pnl:.1f} ({aligned_t/total_t*100:.0f}%)")

    # If we blocked all H1_COUNTER trades
    blocked_pnl=align_data['H1_COUNTER']['pnl']
    print(f"  若阻止H1_COUNTER: 节省 ${-blocked_pnl:.1f} 亏损")

sf=MT5_PROFILES_DIR/'v11xau-mtf.set'
if sf.exists():sf.unlink()
print("\n分析完成!")
