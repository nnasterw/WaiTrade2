#!/usr/bin/env python3
"""QS4+NOISE quick test — all 5 months."""
import os, subprocess, time, re
from pathlib import Path

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))

MONTHS = [('jan','2026.01.01','2026.01.31'),('feb','2026.02.01','2026.02.28'),
          ('mar','2026.03.01','2026.03.31'),('apr','2026.04.01','2026.04.30'),
          ('may','2026.05.01','2026.05.31')]

def kill_mt5():
    subprocess.run(["powershell","-NoProfile","-Command",
        "Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and $_.Path.StartsWith('C:\\Program Files\\MetaTrader 5') } | "
        "Stop-Process -Force"], capture_output=True)
    time.sleep(4)

def run(name, set_name, df, dt):
    (MT5_DATA/'Tester').mkdir(exist_ok=True)
    (MT5_DATA/'Tester'/'backtest.ini').write_text(f"""[Common]
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
    ini_path = MT5_DATA / 'Tester' / 'backtest.ini'
    proc = subprocess.Popen([MT5_TERMINAL, f'/config:{ini_path}'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    t0=time.time()
    while proc.poll() is None:
        if time.time()-t0>600: proc.kill(); return None
        time.sleep(3)
    htm=MT5_DATA/f'{name}.htm'
    if htm.exists():
        raw=htm.read_bytes(); html=raw.decode('utf-16-le',errors='replace')
        rows=re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>',html,re.DOTALL)
        trades=[float(re.findall(r'<td[^>]*>(.*?)</td>',r)[10].strip()) for r in rows
                if len(re.findall(r'<td[^>]*>(.*?)</td>',r))==13
                and re.findall(r'<td[^>]*>(.*?)</td>',r)[3]!='balance'
                and re.findall(r'<td[^>]*>(.*?)</td>',r)[4].strip()=='out']
        wins=[t for t in trades if t>0]; losses=[t for t in trades if t<0]
        return {'count':len(trades),'pnl':sum(trades),'wins':len(wins),'losses':len(losses),
                'wr':f"{len(wins)/len(trades)*100:.1f}%" if trades else '0%',
                'avg_win':f"{sum(wins)/len(wins):.2f}" if wins else '-',
                'avg_loss':f"{sum(losses)/len(losses):.2f}" if losses else '-',
                'pf':f"{sum(wins)/abs(sum(losses)):.2f}" if losses and sum(losses)!=0 else '0.00'}
    return None

results={}
for i,(m,df,dt) in enumerate(MONTHS):
    print(f"[{i+1}/5] {m}-qs4noise ",end='',flush=True)
    kill_mt5()
    r=run(f'qs4_{m}','v11xau-qs4-noise.set',df,dt)
    results[m]=r
    print(f"{r['count']}T PnL=${r['pnl']:.2f}" if r else "FAIL")
    time.sleep(2)

# Also load p9 off/noise for comparison
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
print(f"\n{'Month':<6} {'Config':<12} {'Trades':>6} {'W':>4} {'L':>4} {'WR%':>7} {'Net$':>10} {'PF':>6} {'AvgW$':>7} {'AvgL$':>7}")
print("-"*85)
totals={'off':[0,0],'noise':[0,0],'qs4noise':[0,0]}
for m in ['jan','feb','mar','apr','may']:
    for k,lbl in [('off','OFF'),('noise','NOISE(QS3)'),('qs4noise','QS4+NOISE')]:
        r=p9.get(f'{m}_{k}') if k!='qs4noise' else results.get(m)
        if not r: continue
        totals[k][0]+=r['count']; totals[k][1]+=r['pnl']
        print(f"{mc[m]:<6} {lbl:<12} {r['count']:>6} {r['wins']:>4} {r['losses']:>4} {r['wr']:>7} ${r['pnl']:>9.2f} {r['pf']:>6} ${r['avg_win']:>6} ${r['avg_loss']:>6}")
print("-"*85)
for k,lbl in [('off','OFF'),('noise','NOISE(QS3)'),('qs4noise','QS4+NOISE')]:
    print(f"{'合计':<6} {lbl:<12} {totals[k][0]:>6} {'':>4} {'':>4} {'':>7} ${totals[k][1]:>9.2f}")

# Balance
print(f"\n{'Month':<6} {'OFF':>10} {'NOISE(QS3)':>11} {'QS4+NOISE':>10}")
print("-"*40)
for m in ['jan','feb','mar','apr','may']:
    ob=200+p9.get(f'{m}_off',{}).get('pnl',0)
    nb=200+p9.get(f'{m}_noise',{}).get('pnl',0)
    qb=200+results.get(m,{}).get('pnl',0)
    print(f"{mc[m]:<6} ${ob:>9.2f} ${nb:>10.2f} ${qb:>9.2f}")
print("\n[DONE]")
