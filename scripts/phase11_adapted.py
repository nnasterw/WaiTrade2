#!/usr/bin/env python3
"""Phase 11: QS4-Adapted & Q2-Adapted — 5-month comparison."""
import os, subprocess, time, re
from pathlib import Path

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

MONTHS = [('jan','2026.01.01','2026.01.31'),('feb','2026.02.01','2026.02.28'),
          ('mar','2026.03.01','2026.03.31'),('apr','2026.04.01','2026.04.30'),
          ('may','2026.05.01','2026.05.31')]

CONFIGS = [
    ('qs4a', 'v11xau-qs4-adapted.set'),
    ('q2a',  'v11xau-q2-adapted.set'),
]

def kill_mt5():
    subprocess.run(["powershell","-NoProfile","-Command",
        "Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and $_.Path.StartsWith('C:\\Program Files\\MetaTrader 5') } | "
        "Stop-Process -Force"], capture_output=True)
    time.sleep(4)

def run_one(name, set_name, df, dt):
    os.makedirs(INI_DIR, exist_ok=True)
    (INI_DIR/'backtest.ini').write_text(f"""[Common]
Login=
Server=
[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters={set_name}
Symbol=XAUUSDm
Period=M1
Model=4
Optimization=0
FromDate={df}
ToDate={dt}
Deposit=200
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report={name}
""", encoding='utf-8')
    ini_path = INI_DIR / 'backtest.ini'
    proc = subprocess.Popen([MT5_TERMINAL, f'/config:{ini_path}'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    t0=time.time()
    while proc.poll() is None:
        if time.time()-t0>600: proc.kill(); return None
        time.sleep(3)
    elapsed = time.time()-t0
    htm=MT5_DATA/f'{name}.htm'
    if htm.exists():
        raw=htm.read_bytes(); html=raw.decode('utf-16-le',errors='replace')
        rows=re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>',html,re.DOTALL)
        trades=[]
        for r in rows:
            cells=re.findall(r'<td[^>]*>(.*?)</td>',r)
            if len(cells)==13 and cells[3]!='balance' and cells[4].strip()=='out':
                try: trades.append(float(cells[10].strip()))
                except: pass
        wins=[t for t in trades if t>0]; losses=[t for t in trades if t<0]
        return {'count':len(trades),'pnl':sum(trades),'wins':len(wins),'losses':len(losses),
                'wr':f"{len(wins)/len(trades)*100:.1f}%" if trades else '0%',
                'avg_win':f"{sum(wins)/len(wins):.2f}" if wins else '-',
                'avg_loss':f"{sum(losses)/len(losses):.2f}" if losses else '-',
                'pf':f"{sum(wins)/abs(sum(losses)):.2f}" if losses and sum(losses)!=0 else ('inf' if wins else '0.00'),
                'elapsed':f"{elapsed:.0f}s"}
    return None

total=len(MONTHS)*len(CONFIGS)
current=0
print(f"Phase 11: Adapted QS4 & Q2 ({total} backtests)")
print("="*55)

results={}
for m,df,dt in MONTHS:
    for cfg,set_name in CONFIGS:
        current+=1; name=f'p11_{m}_{cfg}'
        print(f"[{current}/{total}] {m}-{cfg} ",end='',flush=True)
        kill_mt5()
        r=run_one(name,set_name,df,dt)
        results[f'{m}_{cfg}']=r
        print(f"{r['count']}T PnL=${r['pnl']:.2f} ({r['elapsed']})" if r else "FAIL")
        time.sleep(2)

# Load p9 baseline
p9={}
for m in ['jan','feb','mar','apr','may']:
    for cfg in ['off','noise']:
        htm=MT5_DATA/f'p9_{m}_{cfg}.htm'
        if htm.exists():
            raw=htm.read_bytes();html=raw.decode('utf-16-le',errors='replace')
            rows=re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>',html,re.DOTALL)
            trades=[float(re.findall(r'<td[^>]*>(.*?)</td>',r)[10].strip()) for r in rows
                    if len(re.findall(r'<td[^>]*>(.*?)</td>',r))==13
                    and re.findall(r'<td[^>]*>(.*?)</td>',r)[3]!='balance'
                    and re.findall(r'<td[^>]*>(.*?)</td>',r)[4].strip()=='out']
            wins=[t for t in trades if t>0]; losses=[t for t in trades if t<0]
            p9[f'{m}_{cfg}']={'count':len(trades),'pnl':sum(trades),'wins':len(wins),'losses':len(losses),
                'wr':f"{len(wins)/len(trades)*100:.1f}%" if trades else '0%',
                'avg_win':f"{sum(wins)/len(wins):.2f}" if wins else '-',
                'avg_loss':f"{sum(losses)/len(losses):.2f}" if losses else '-',
                'pf':f"{sum(wins)/abs(sum(losses)):.2f}" if losses and sum(losses)!=0 else '0.00'}

mc={'jan':'1月','feb':'2月','mar':'3月','apr':'4月','may':'5月'}
print(f"\n{'Month':<6} {'Config':<14} {'Trades':>6} {'W':>4} {'L':>4} {'WR%':>7} {'Net$':>10} {'PF':>6} {'AvgW$':>7} {'AvgL$':>7}")
print("-"*90)
totals={'off':[0,0],'noise':[0,0],'qs4a':[0,0],'q2a':[0,0]}
for m in ['jan','feb','mar','apr','may']:
    for k,lbl in [('off','OFF'),('noise','NOISE(QS3)'),('qs4a','QS4-Adapted'),('q2a','Q2-Adapted')]:
        if k in ('off','noise'): r=p9.get(f'{m}_{k}')
        else: r=results.get(f'{m}_{k}')
        if not r: continue
        totals[k][0]+=r['count']; totals[k][1]+=r['pnl']
        print(f"{mc[m]:<6} {lbl:<14} {r['count']:>6} {r['wins']:>4} {r['losses']:>4} {r['wr']:>7} ${r['pnl']:>9.2f} {r['pf']:>6} ${r['avg_win']:>6} ${r['avg_loss']:>6}")
print("-"*90)
for k,lbl in [('off','OFF'),('noise','NOISE(QS3)'),('qs4a','QS4-Adapted'),('q2a','Q2-Adapted')]:
    print(f"{'合计':<6} {lbl:<14} {totals[k][0]:>6} {'':>4} {'':>4} {'':>7} ${totals[k][1]:>9.2f}")

print(f"\n{'Month':<6} {'OFF':>10} {'NOISE(QS3)':>11} {'QS4-Adapt':>10} {'Q2-Adapt':>10}")
print("-"*50)
for m in ['jan','feb','mar','apr','may']:
    ob=200+p9.get(f'{m}_off',{}).get('pnl',0)
    nb=200+p9.get(f'{m}_noise',{}).get('pnl',0)
    q4b=200+results.get(f'{m}_qs4a',{}).get('pnl',0)
    q2b=200+results.get(f'{m}_q2a',{}).get('pnl',0)
    print(f"{mc[m]:<6} ${ob:>9.2f} ${nb:>10.2f} ${q4b:>9.2f} ${q2b:>9.2f}")
print("\n[DONE]")
