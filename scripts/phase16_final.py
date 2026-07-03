#!/usr/bin/env python3
"""Phase 16: Final 5-strategy comparison — $300, 2026 Jan-May, standard 6 metrics."""
import os, subprocess, time, re
from pathlib import Path

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

MONTHS = [('jan','2026.01.01','2026.01.31'),('feb','2026.02.01','2026.02.28'),
          ('mar','2026.03.01','2026.03.31'),('apr','2026.04.01','2026.04.30'),
          ('may','2026.05.01','2026.05.31')]

DEPOSIT = 300
TOTAL_DAYS = 151  # Jan 1 - May 31 = 151 days

STRATEGIES = [
    ('off',   'v11xau-qs3-mtf-off.set',       'OFF'),
    ('qs3n',  'v11xau-qs3-noise.set',         'NOISE(QS3)'),
    ('qs4r',  'v11xau-qs3-d3.set',            'QS4'),
    ('qs4n',  'v11xau-qs3-d3-noise.set',      'QS4+NOISE'),
    ('q2r',   'V11XAU-QS-HTF-COUNTER0-H1.set','Q2'),
    ('q2n',   'v11xau-q2-noise.set',           'Q2+NOISE'),
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
Deposit={DEPOSIT}
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
    elapsed=time.time()-t0
    htm=MT5_DATA/f'{name}.htm'
    if htm.exists():
        raw=htm.read_bytes();html=raw.decode('utf-16-le',errors='replace')
        rows=re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>',html,re.DOTALL)
        trades=[float(re.findall(r'<td[^>]*>(.*?)</td>',r)[10].strip()) for r in rows
                if len(re.findall(r'<td[^>]*>(.*?)</td>',r))==13
                and re.findall(r'<td[^>]*>(.*?)</td>',r)[3]!='balance'
                and re.findall(r'<td[^>]*>(.*?)</td>',r)[4].strip()=='out']
        wins=[t for t in trades if t>0];losses=[t for t in trades if t<0]
        gross_w=sum(wins) if wins else 0; gross_l=abs(sum(losses)) if losses else 0
        pf=gross_w/gross_l if gross_l>0 else (999 if gross_w>0 else 0)
        wr=len(wins)/len(trades)*100 if trades else 0
        return {'count':len(trades),'pnl':sum(trades),'wins':len(wins),'losses':len(losses),
                'wr':wr,'pf':pf,'gross_w':gross_w,'gross_l':gross_l,'elapsed':f'{elapsed:.0f}s'}
    return None

total=len(MONTHS)*len(STRATEGIES);current=0
print(f"Phase 16: Final 6-Strategy Comparison ({total} backtests, ${DEPOSIT})")
print("=" * 60)

results={}
for m,df,dt in MONTHS:
    for key,set_name,label in STRATEGIES:
        current+=1;name=f'p16_{m}_{key}'
        print(f"[{current}/{total}] {m}-{label:<12} ",end='',flush=True)
        kill_mt5()
        r=run_one(name,set_name,df,dt)
        results[f'{m}_{key}']=r
        if r:
            print(f"{r['count']:>4}T PnL=${r['pnl']:>+8.2f} ({r['elapsed']})")
        else:
            print(f"FAIL")
        time.sleep(2)

# === STANDARD TABLE ===
mc={'jan':'1月','feb':'2月','mar':'3月','apr':'4月','may':'5月'}

print(f"\n\n{'='*140}")
print(f"  2026年1-5月 六策略对比 (初始${DEPOSIT}, Model 4 / Real Ticks / XAUUSDm M1)")
print(f"{'='*140}")

# Monthly detail table
print(f"\n{'Month':<6}", end='')
for _,_,label in STRATEGIES:
    print(f" | {label:^18}", end='')
print(f"\n{'':<6}", end='')
for _ in STRATEGIES:
    print(f" | {'Trades PnL':<18}", end='')
print(f"\n{'-'*140}")

# Monthly data
for m in ['jan','feb','mar','apr','may']:
    print(f"{mc[m]:<6}", end='')
    for key,_,_ in STRATEGIES:
        r=results.get(f'{m}_{key}',{})
        if r:
            print(f" | {r['count']:>4}T ${r['pnl']:>+9.2f}", end='')
        else:
            print(f" | {'':>18}", end='')
    print()

# Totals
print(f"{'-'*140}")
print(f"{'合计':<6}", end='')
for key,_,_ in STRATEGIES:
    tot_t=sum(results.get(f'{m}_{key}',{}).get('count',0) for m in ['jan','feb','mar','apr','may'])
    tot_p=sum(results.get(f'{m}_{key}',{}).get('pnl',0) for m in ['jan','feb','mar','apr','may'])
    print(f" | {tot_t:>4}T ${tot_p:>+9.2f}", end='')
print()

# === THE STANDARD 6-METRIC TABLE ===
print(f"\n\n{'='*140}")
print(f"  标准六指标汇总 (初始${DEPOSIT}, 2026.01.01-2026.05.31, 151天)")
print(f"{'='*140}")

print(f"\n{'指标':<16}", end='')
for _,_,label in STRATEGIES:
    print(f" | {label:>16}", end='')
print(f"\n{'-'*120}")

# Metric 1: Daily trades
print(f"{'日均交易':<16}", end='')
for key,_,_ in STRATEGIES:
    tot=sum(results.get(f'{m}_{key}',{}).get('count',0) for m in ['jan','feb','mar','apr','may'])
    print(f" | {tot/TOTAL_DAYS:>15.1f}", end='')
print()

# Metric 2: Win Rate
print(f"{'胜率%':<16}", end='')
for key,_,_ in STRATEGIES:
    tw=sum(results.get(f'{m}_{key}',{}).get('wins',0) for m in ['jan','feb','mar','apr','may'])
    tl=sum(results.get(f'{m}_{key}',{}).get('losses',0) for m in ['jan','feb','mar','apr','may'])
    total=tw+tl
    wr=tw/total*100 if total>0 else 0
    print(f" | {wr:>15.1f}%", end='')
print()

# Metric 3: Profit Factor
print(f"{'盈亏比(PF)':<16}", end='')
for key,_,_ in STRATEGIES:
    gw=sum(results.get(f'{m}_{key}',{}).get('gross_w',0) for m in ['jan','feb','mar','apr','may'])
    gl=sum(results.get(f'{m}_{key}',{}).get('gross_l',0) for m in ['jan','feb','mar','apr','may'])
    pf=gw/gl if gl>0 else (999 if gw>0 else 0)
    print(f" | {pf:>15.2f}", end='')
print()

# Metric 4: Net P&L
print(f"{'净盈亏($)':<16}", end='')
for key,_,_ in STRATEGIES:
    tot=sum(results.get(f'{m}_{key}',{}).get('pnl',0) for m in ['jan','feb','mar','apr','may'])
    print(f" | ${tot:>14.2f}", end='')
print()

# Metric 5: Final Balance
print(f"{'最终余额($)':<16}", end='')
for key,_,_ in STRATEGIES:
    tot=sum(results.get(f'{m}_{key}',{}).get('pnl',0) for m in ['jan','feb','mar','apr','may'])
    print(f" | ${DEPOSIT+tot:>14.2f}", end='')
print()

# Metric 6: Initial (same for all)
print(f"{'初始金额($)':<16}", end='')
for _ in STRATEGIES:
    print(f" | ${DEPOSIT:>14.0f}", end='')
print()

# Total trades
print(f"{'总交易数':<16}", end='')
for key,_,_ in STRATEGIES:
    tot=sum(results.get(f'{m}_{key}',{}).get('count',0) for m in ['jan','feb','mar','apr','may'])
    print(f" | {tot:>15}", end='')
print()

# Month-by-month balance (running)
print(f"\n\n  每月余额 ($)")
print(f"  {'Month':<6}", end='')
for _,_,label in STRATEGIES:
    print(f" | {label:>10}", end='')
print(f"\n  {'-'*75}")

running={key:DEPOSIT for key,_,_ in STRATEGIES}
for m in ['jan','feb','mar','apr','may']:
    print(f"  {mc[m]:<6}", end='')
    for key,_,_ in STRATEGIES:
        r=results.get(f'{m}_{key}',{})
        running[key]+=r.get('pnl',0)
        best_bal=max(running.values())
        marker='*' if running[key]==best_bal and running[key]>=DEPOSIT else ' '
        print(f" | ${running[key]:>8.2f}{marker}", end='')
    print()

print(f"\n[DONE]")
