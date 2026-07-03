#!/usr/bin/env python3
"""Phase 14: Verify real QS4(d3) and QS4(d3)+NOISE after default fix."""
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
        trades=[]
        for r in rows:
            cells=re.findall(r'<td[^>]*>(.*?)</td>',r)
            if len(cells)==13 and cells[3]!='balance' and cells[4].strip()=='out':
                try: trades.append(float(cells[10].strip()))
                except: pass
        wins=[t for t in trades if t>0]; losses=[t for t in trades if t<0]
        return {'count':len(trades),'pnl':sum(trades),'wins':len(wins),'losses':len(losses),
                'wr':f"{len(wins)/len(trades)*100:.1f}%" if trades else '0%'}
    return None

# Create QS4(d3)+NOISE
BT = Path(r'D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt')
import shutil
d3_set = BT/'MQL5/Profiles/Tester/v11xau-qs3-d3-noise.set'
shutil.copy(r'D:\Code\codexProject\WaiTrade2\mql5\Presets\v11xau-qs3-d3.set', str(d3_set))
with open(d3_set,'a') as f:
    f.write('\nInpEnableTickNoiseGate=true\nInpTickNoiseGateLookback=30\n')
    f.write('InpTickNoiseGateMinDirRatio=0.35\nInpTickNoiseGateMaxRangeATR=0.15\n')
    f.write('InpMinSLSpreadMult=5.0\nInpOBTouchConfirmTicks=5\n')
    f.write('InpEnableDynamicSpread=true\n')
    f.write('InpEnableMTF=false\n')
shutil.copy(str(d3_set), str(MT5_DATA/'MQL5/Profiles/Tester/v11xau-qs3-d3-noise.set'))

# Copy CRY2B as Q2-orig (but now with safe defaults)
shutil.copy(r'D:\Code\codexProject\WaiTrade2\mql5\Presets\CRY2B.set',
            str(MT5_DATA/'MQL5/Profiles/Tester/CRY2B.set'))

TESTS = [
    ('p14_qs4real', 'v11xau-qs3-d3.set'),
    ('p14_qs4noise', 'v11xau-qs3-d3-noise.set'),
]

print("Phase 14: Real QS4 verification (5 months, $200)")
print("=" * 55)

results = {}
for m,df,dt in MONTHS:
    for cfg,set_name in TESTS:
        name = f'p14_{m}_{cfg.replace("p14_","")}'
        label = f'{m}-{cfg.replace("p14_","")}'
        print(f"[{label}] ",end='',flush=True)
        kill_mt5()
        r = run_one(name, set_name, df, dt)
        results[f'{m}_{cfg}'] = r
        print(f"{r['count']}T PnL=${r['pnl']:.2f}" if r else "FAIL")
        time.sleep(2)

# Also load p9 off/noise for comparison
p9 = {}
for m in ['jan','feb','mar','apr','may']:
    for cfg in ['off','noise']:
        htm = MT5_DATA/f'p9_{m}_{cfg}.htm'
        if htm.exists():
            raw=htm.read_bytes();html=raw.decode('utf-16-le',errors='replace')
            rows=re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>',html,re.DOTALL)
            trades=[float(re.findall(r'<td[^>]*>(.*?)</td>',r)[10].strip()) for r in rows
                    if len(re.findall(r'<td[^>]*>(.*?)</td>',r))==13
                    and re.findall(r'<td[^>]*>(.*?)</td>',r)[3]!='balance'
                    and re.findall(r'<td[^>]*>(.*?)</td>',r)[4].strip()=='out']
            wins=[t for t in trades if t>0]; losses=[t for t in trades if t<0]
            p9[f'{m}_{cfg}']={'count':len(trades),'pnl':sum(trades),'wins':len(wins),'losses':len(losses)}

mc={'jan':'1月','feb':'2月','mar':'3月','apr':'4月','may':'5月'}

print(f"\n{'Month':<6} {'OFF':>8} {'NOISE':>8} {'QS4-real':>10} {'QS4+NOISE':>10}")
print("-"*50)
tot_off=tot_noise=tot_q4=tot_q4n=0
for m in ['jan','feb','mar','apr','may']:
    off=p9.get(f'{m}_off',{})
    noi=p9.get(f'{m}_noise',{})
    q4=results.get(f'{m}_p14_qs4real',{})
    q4n=results.get(f'{m}_p14_qs4noise',{})
    tot_off+=off.get('pnl',0); tot_noise+=noi.get('pnl',0)
    tot_q4+=q4.get('pnl',0); tot_q4n+=q4n.get('pnl',0)
    print(f"{mc[m]:<6} {off.get('count',0):>3}T${off.get('pnl',0):>+6.0f} "
          f"{noi.get('count',0):>3}T${noi.get('pnl',0):>+6.0f} "
          f"{q4.get('count',0):>3}T${q4.get('pnl',0):>+6.0f} "
          f"{q4n.get('count',0):>3}T${q4n.get('pnl',0):>+6.0f}")
print("-"*50)
print(f"{'合计':<6} ${tot_off:>+7.0f} ${tot_noise:>+7.0f} ${tot_q4:>+7.0f} ${tot_q4n:>+7.0f}")

# QS4-real trades should be in the hundreds per month (not 0-3!)
print(f"\n[FIX VERIFICATION] QS4-real should have 200-600 trades/month (like OFF)")
print(f"QS4-real actual: {sum(results.get(f'{m}_p14_qs4real',{}).get('count',0) for m in ['jan','feb','mar','apr','may'])} trades total")
print(f"[DONE]")
