#!/usr/bin/env python3
"""Phase 15: Real Q2 verification (V11XAU-QS-HTF-COUNTER0-H1) — 5 months."""
import os, subprocess, time, re
from pathlib import Path

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

MONTHS = [('jan','2026.01.01','2026.01.31'),('feb','2026.02.01','2026.02.28'),
          ('mar','2026.03.01','2026.03.31'),('apr','2026.04.01','2026.04.30'),
          ('may','2026.05.01','2026.05.31')]

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
    ini=INI_DIR/'backtest.ini'
    proc=subprocess.Popen([MT5_TERMINAL,f'/config:{ini}'],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    t0=time.time()
    while proc.poll() is None:
        if time.time()-t0>600: proc.kill(); return None
        time.sleep(3)
    htm=MT5_DATA/f'{name}.htm'
    if htm.exists():
        raw=htm.read_bytes();html=raw.decode('utf-16-le',errors='replace')
        rows=re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>',html,re.DOTALL)
        trades=[float(re.findall(r'<td[^>]*>(.*?)</td>',r)[10].strip()) for r in rows
                if len(re.findall(r'<td[^>]*>(.*?)</td>',r))==13
                and re.findall(r'<td[^>]*>(.*?)</td>',r)[3]!='balance'
                and re.findall(r'<td[^>]*>(.*?)</td>',r)[4].strip()=='out']
        wins=[t for t in trades if t>0];losses=[t for t in trades if t<0]
        return {'count':len(trades),'pnl':sum(trades),'wins':len(wins),'losses':len(losses)}
    return None

print("Phase 15: Real Q2 verification")
print("=" * 50)

results={}
for m,df,dt in MONTHS:
    name=f'p15_{m}_realq2'
    print(f"[{m}] ",end='',flush=True)
    kill_mt5()
    r=run_one(name,'V11XAU-QS-HTF-COUNTER0-H1.set',df,dt)
    results[m]=r
    print(f"{r['count']}T PnL=${r['pnl']:.2f}" if r else "FAIL")
    time.sleep(2)

mc={'jan':'1月','feb':'2月','mar':'3月','apr':'4月','may':'5月'}
print(f"\n{'Month':<6} {'Real Q2':>10} {'QS4+NOISE':>12} {'NOISE(QS3)':>12}")
print("-"*50)
for m in ['jan','feb','mar','apr','may']:
    r=results.get(m,{})
    print(f"{mc[m]:<6} {r.get('count',0):>3}T${r.get('pnl',0):>+7.0f}")

tot=sum(results.get(m,{}).get('pnl',0) for m in ['jan','feb','mar','apr','may'])
cnt=sum(results.get(m,{}).get('count',0) for m in ['jan','feb','mar','apr','may'])
print(f"\n合计: {cnt}T ${tot:+.2f}")
print("[DONE]")
