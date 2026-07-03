#!/usr/bin/env python3
"""Phase 18: QS4 / Q2 / QS4+NOISE / Q2+NOISE — 720-day comparison."""
import os, subprocess, time, re
from pathlib import Path
from collections import defaultdict

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

DEPOSIT = 300
DATE_FROM = '2024.06.01'
DATE_TO = '2026.05.31'
TOTAL_DAYS = 730

STRATEGIES = [
    ('qs4',  'v11xau-qs4.set',             'QS4'),
    ('q2',   'v11xau-q2.set',              'Q2'),
    ('qs4n', 'v11xau-realqs4-noise.set',   'QS4+NOISE'),
    ('q2n',  'v11xau-q2-noise.set',        'Q2+NOISE'),
]

def kill_mt5():
    subprocess.run(["powershell","-NoProfile","-Command",
        "Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and $_.Path.StartsWith('C:\\Program Files\\MetaTrader 5') } | "
        "Stop-Process -Force"], capture_output=True)
    time.sleep(4)

def run_720(name, set_name):
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
FromDate={DATE_FROM}
ToDate={DATE_TO}
Deposit={DEPOSIT}
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report={name}
""", encoding='utf-8')
    ini=INI_DIR/'backtest.ini'
    print(f"  Running...", end='', flush=True)
    proc=subprocess.Popen([MT5_TERMINAL,f'/config:{ini}'],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    t0=time.time()
    while proc.poll() is None:
        if time.time()-t0>900: proc.kill(); return None
        if int(time.time()-t0)%30==0: print('.',end='',flush=True)
        time.sleep(5)
    elapsed=time.time()-t0
    print(f' ({elapsed:.0f}s)')
    return MT5_DATA/f'{name}.htm'

def parse_720(htm_path):
    raw=htm_path.read_bytes();html=raw.decode('utf-16-le',errors='replace')
    rows=re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>',html,re.DOTALL)
    monthly=defaultdict(lambda: {'trades':0,'wins':0,'losses':0,'pnl':0.0,'gross_w':0.0,'gross_l':0.0})
    ins={}
    for row_html in rows:
        cells=re.findall(r'<td[^>]*>(.*?)</td>',row_html)
        if len(cells)!=13 or cells[3]=='balance': continue
        time_str=cells[0].strip();direction=cells[3].strip()
        in_out=cells[4].strip();order_num=cells[7].strip()
        profit=cells[10].strip()
        if in_out=='in': ins[order_num]=time_str
        elif in_out=='out':
            try: p=float(profit)
            except: p=0.0
            entry_time=ins.get(order_num,time_str)
            try:
                parts=entry_time.split();date_parts=parts[0].split('.')
                month_key=f"{date_parts[0]}-{date_parts[1]}"
            except: month_key='unknown'
            m=monthly[month_key]
            m['trades']+=1;m['pnl']+=p
            if p>0: m['wins']+=1;m['gross_w']+=p
            elif p<0: m['losses']+=1;m['gross_l']+=abs(p)
    total_t=sum(m['trades'] for m in monthly.values())
    total_p=sum(m['pnl'] for m in monthly.values())
    total_w=sum(m['wins'] for m in monthly.values())
    total_l=sum(m['losses'] for m in monthly.values())
    gw=sum(m['gross_w'] for m in monthly.values())
    gl=sum(m['gross_l'] for m in monthly.values())
    wr=total_w/(total_w+total_l)*100 if (total_w+total_l)>0 else 0
    pf=gw/gl if gl>0 else (999 if gw>0 else 0)
    return {'count':total_t,'pnl':total_p,'wins':total_w,'losses':total_l,
            'wr':wr,'pf':pf,'gross_w':gw,'gross_l':gl,
            'daily':total_t/TOTAL_DAYS,'balance':DEPOSIT+total_p,'monthly':dict(monthly)}

print(f"Phase 18: QS4 / Q2 / QS4+NOISE / Q2+NOISE — 720-day")
print(f"({DATE_FROM} -> {DATE_TO}, ${DEPOSIT})")
print("=" * 60)

results={}
for key,set_name,label in STRATEGIES:
    name=f'p18_720_{key}'
    print(f"\n[{label}] ",end='',flush=True)
    kill_mt5()
    htm=run_720(name,set_name)
    if htm:
        print(f"  Parsing {htm.stat().st_size/1024:.0f}KB...")
        r=parse_720(htm)
        results[key]=r
        print(f"  {r['count']}T, WR={r['wr']:.1f}%, PF={r['pf']:.2f}, "
              f"PnL=${r['pnl']:.2f}, Bal=${r['balance']:.2f}")
    else:
        print(f"  FAILED")

# Load QS3+NOISE from Phase 13 for reference
p13=MT5_DATA/'p13_qs3noise.htm'
if p13.exists():
    r=parse_720(p13)
    results['qs3n']=r
    print(f"\n[NOISE+QS3] (reused): {r['count']}T, Bal=${r['balance']:.2f}")

# === STANDARD TABLE ===
print(f"\n\n{'='*130}")
print(f"  720天对比 ({DATE_FROM} -> {DATE_TO}, 初始${DEPOSIT})")
print(f"{'='*130}")

STRATS=[('qs3n','NOISE+QS3'),('qs4','QS4'),('q2','Q2'),('qs4n','QS4+NOISE'),('q2n','Q2+NOISE')]

print(f"\n{'指标':<16}", end='')
for _,label in STRATS: print(f" | {label:>18}", end='')
print(f"\n{'-'*115}")

for metric,attr,fmt in [
    ('日均交易','daily','.1f'),('胜率%','wr','.1f%%'),('盈亏比(PF)','pf','.2f'),
    ('净盈亏($)','pnl','.2f'),('最终余额($)','balance','.0f'),
]:
    print(f"{metric:<16}", end='')
    best_val=-999999;best_key=None
    for key,_ in STRATS:
        r=results.get(key,{})
        if r:
            if attr=='balance': val=r['balance']
            elif attr=='pnl': val=r['pnl']
            elif attr=='pf': val=r['pf']
            else: val=r.get(attr,0)
            if val>best_val and attr not in ('daily',): best_val=val;best_key=key
    for key,_ in STRATS:
        r=results.get(key,{})
        if not r: print(f" | {'':>18}", end=''); continue
        if attr=='daily': print(f" | {r['daily']:>17.1f}", end='')
        elif attr=='wr': print(f" | {r['wr']:>16.1f}%", end='')
        elif attr=='pf': print(f" | {r['pf']:>17.2f}", end='')
        elif attr=='balance' or attr=='pnl':
            mark=' *' if key==best_key else ''
            print(f" | ${r['balance']:>16,.0f}{mark}", end='')
        else:
            mark=' *' if key==best_key else ''
            print(f" | ${r['pnl']:>16,.0f}{mark}", end='')
    print()

print(f"{'初始金额($)':<16} | ${DEPOSIT:>17} | ${DEPOSIT:>17} | ${DEPOSIT:>17} | ${DEPOSIT:>17} | ${DEPOSIT:>17}")
print(f"{'总交易数':<16}", end='')
for key,_ in STRATS:
    r=results.get(key,{})
    print(f" | {r.get('count',0):>17,}", end='')
print()

# Monthly balance curve
print(f"\n\n  月度余额 (连续复利)")
all_months=set()
for r in results.values():
    if r.get('monthly'): all_months.update(r['monthly'].keys())
sorted_months=sorted(all_months)
print(f"  {'Month':<9}", end='')
for _,label in STRATS: print(f" | {label:>12}", end='')
print(f"\n  {'-'*75}")
running={key:DEPOSIT for key,_ in STRATS}
for month in sorted_months:
    print(f"  {month:<9}", end='')
    for key,_ in STRATS:
        r=results.get(key,{})
        m=r.get('monthly',{}).get(month,{}) if r else {}
        p=m.get('pnl',0) if m else 0
        running[key]+=p
        print(f" | ${running[key]:>10,.0f}", end='')
    print()

print(f"\n[DONE]")
