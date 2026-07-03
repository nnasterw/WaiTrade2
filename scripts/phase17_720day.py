#!/usr/bin/env python3
"""Phase 17: 720-day + 24-month individual for 3 NOISE strategies."""
import os, subprocess, time, re
from pathlib import Path
from collections import defaultdict

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'

DEPOSIT = 300
DATE_720_FROM = '2024.06.01'
DATE_720_TO = '2026.05.31'
TOTAL_DAYS_720 = 730

STRATEGIES_720 = [
    ('qs3n', 'v11xau-qs3-noise.set',         'NOISE+QS3'),
    ('qs4n', 'v11xau-qs3-d3-noise.set',      'NOISE+QS4'),
    ('q2n',  'v11xau-q2-noise.set',           'NOISE+Q2'),
]

# Individual months: 2024.06 - 2026.05
import calendar
INDIVIDUAL_MONTHS = []
for yr in [2024, 2025, 2026]:
    start_m = 6 if yr == 2024 else 1
    end_m = 13 if yr == 2026 else 13
    if yr == 2026: end_m = 6
    for m in range(start_m, end_m):
        last_day = calendar.monthrange(yr, m)[1]
        INDIVIDUAL_MONTHS.append((f'{yr}-{m:02d}', f'{yr}.{m:02d}.01', f'{yr}.{m:02d}.{last_day}'))

def kill_mt5():
    subprocess.run(["powershell","-NoProfile","-Command",
        "Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and $_.Path.StartsWith('C:\\Program Files\\MetaTrader 5') } | "
        "Stop-Process -Force"], capture_output=True)
    time.sleep(4)

def run_backtest(name, set_name, df, dt):
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
        if time.time()-t0>900: proc.kill(); return None
        time.sleep(5)
    return MT5_DATA/f'{name}.htm'

def parse_htm(htm_path, is_continuous=False):
    """Parse HTML: returns summary dict. If is_continuous, also returns monthly dict."""
    raw=htm_path.read_bytes();html=raw.decode('utf-16-le',errors='replace')
    rows=re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>',html,re.DOTALL)

    monthly=defaultdict(lambda: {'trades':0,'wins':0,'losses':0,'pnl':0.0,'gross_w':0.0,'gross_l':0.0})
    ins={}
    for row_html in rows:
        cells=re.findall(r'<td[^>]*>(.*?)</td>',row_html)
        if len(cells)!=13 or cells[3]=='balance': continue
        time_str=cells[0].strip();direction=cells[3].strip()
        in_out=cells[4].strip();order_num=cells[7].strip()
        profit=cells[10].strip();comment=cells[12].strip()
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
    days=TOTAL_DAYS_720 if is_continuous else sum(1 for m in monthly if m!='unknown')

    result={
        'count':total_t,'pnl':total_p,'wins':total_w,'losses':total_l,
        'wr':wr,'pf':pf,'gross_w':gw,'gross_l':gl,
        'daily':total_t/days if days>0 else 0,
        'balance':DEPOSIT+total_p,
        'monthly':dict(monthly) if is_continuous else None,
    }
    return result

# ===== PART 1: 720-day tests =====
print("=" * 70)
print("PART 1: 720-Day Continuous Backtests (3 strategies)")
print("=" * 70)

results_720 = {}
for key, set_name, label in STRATEGIES_720:
    name = f'p17_720_{key}'
    htm = MT5_DATA / f'{name}.htm'

    if key == 'qs3n':
        # Reuse Phase 13 result
        p13 = MT5_DATA / 'p13_qs3noise.htm'
        if p13.exists():
            print(f"\n[{label}] Reusing Phase 13 result...")
            r = parse_htm(p13, is_continuous=True)
            results_720[key] = r
            print(f"  {r['count']}T, WR={r['wr']:.1f}%, PF={r['pf']:.2f}, PnL=${r['pnl']:.2f}, Bal=${r['balance']:.2f}")
            continue
    print(f"\n[{label}] Running 720-day...")
    kill_mt5()
    htm = run_backtest(name, set_name, DATE_720_FROM, DATE_720_TO)
    if not htm:
        print(f"  FAILED")
        continue
    print(f"  Parsing {htm.stat().st_size/1024:.0f}KB...")
    r = parse_htm(htm, is_continuous=True)
    results_720[key] = r
    print(f"  {r['count']}T, WR={r['wr']:.1f}%, PF={r['pf']:.2f}, PnL=${r['pnl']:.2f}, Bal=${r['balance']:.2f}")

# ===== 720-DAY STANDARD TABLE =====
print(f"\n\n{'='*110}")
print(f"  720天连续回测标准表格 ({DATE_720_FROM} -> {DATE_720_TO}, 初始${DEPOSIT})")
print(f"{'='*110}")

print(f"\n{'指标':<16} | {'NOISE+QS3':>18} | {'NOISE+QS4':>18} | {'NOISE+Q2':>18}")
print(f"{'-'*80}")

STRATS_720_ORDER = [('qs3n','NOISE+QS3'),('qs4n','NOISE+QS4'),('q2n','NOISE+Q2')]

for metric_label, attr in [
    ('日均交易','daily'),('胜率%','wr'),('盈亏比(PF)','pf'),
    ('净盈亏($)','pnl'),('最终余额($)','balance'),
]:
    print(f"{metric_label:<16}", end='')
    for key,_ in STRATS_720_ORDER:
        r=results_720.get(key,{})
        if r:
            if attr=='daily': print(f" | {r[attr]:>17.1f}", end='')
            elif attr=='wr': print(f" | {r[attr]:>16.1f}%", end='')
            elif attr=='pf': print(f" | {r[attr]:>17.2f}", end='')
            elif attr=='balance': print(f" | ${r[attr]:>16.2f}", end='')
            else: print(f" | ${r[attr]:>16.2f}", end='')
        else: print(f" | {'':>17}", end='')
    print()

print(f"{'初始金额($)':<16} | ${DEPOSIT:>17} | ${DEPOSIT:>17} | ${DEPOSIT:>17}")
print(f"{'总交易数':<16}", end='')
for key,_ in STRATS_720_ORDER:
    r=results_720.get(key,{})
    print(f" | {r.get('count',0):>17}", end='')
print()

# Monthly breakdown from 720-day
print(f"\n\n  720天月度余额 (连续复利)")
all_months_720=set()
for r in results_720.values():
    if r.get('monthly'): all_months_720.update(r['monthly'].keys())
sorted_months_720=sorted(all_months_720)
print(f"  {'Month':<9}", end='')
for _,label in STRATS_720_ORDER: print(f" | {label:>12}", end='')
print(f"\n  {'-'*50}")
running_720={key:DEPOSIT for key,_ in STRATS_720_ORDER}
for month in sorted_months_720:
    print(f"  {month:<9}", end='')
    for key,_ in STRATS_720_ORDER:
        r=results_720.get(key,{})
        m=r.get('monthly',{}).get(month,{}) if r else {}
        p=m.get('pnl',0) if m else 0
        running_720[key]+=p
        print(f" | ${running_720[key]:>10.2f}", end='')
    print()

# ===== PART 2: 24 individual monthly tests =====
print(f"\n\n{'='*70}")
print(f"PART 2: 24 Individual Monthly Backtests ({len(INDIVIDUAL_MONTHS)} months × 3 strategies = {len(INDIVIDUAL_MONTHS)*3} tests)")
print(f"{'='*70}")

results_ind={}
total_tests=len(INDIVIDUAL_MONTHS)*3;current=0
for m_label,df,dt in INDIVIDUAL_MONTHS:
    for key,set_name,label in STRATEGIES_720:
        current+=1;name=f'p17_ind_{m_label}_{key}'
        print(f"[{current}/{total_tests}] {m_label} {label} ",end='',flush=True)
        kill_mt5()
        htm=run_backtest(name,set_name,df,dt)
        if htm:
            r=parse_htm(htm)
            results_ind[f'{m_label}_{key}']=r
            print(f"{r['count']:>3}T ${r['pnl']:>+7.2f}")
        else:
            print(f"FAIL")
        time.sleep(1)

# ===== INDIVIDUAL MONTHS STANDARD TABLE =====
print(f"\n\n{'='*110}")
print(f"  24月独立回测标准表格 (每月独立${DEPOSIT}, Model 4 / Real Ticks)")
print(f"{'='*110}")

# Aggregate
ind_agg = {}
for key,label in STRATS_720_ORDER:
    tot_t=sum(results_ind.get(f'{m_label}_{key}',{}).get('count',0) for m_label,_,_ in INDIVIDUAL_MONTHS)
    tot_p=sum(results_ind.get(f'{m_label}_{key}',{}).get('pnl',0) for m_label,_,_ in INDIVIDUAL_MONTHS)
    tot_w=sum(results_ind.get(f'{m_label}_{key}',{}).get('wins',0) for m_label,_,_ in INDIVIDUAL_MONTHS)
    tot_l=sum(results_ind.get(f'{m_label}_{key}',{}).get('losses',0) for m_label,_,_ in INDIVIDUAL_MONTHS)
    gw=sum(results_ind.get(f'{m_label}_{key}',{}).get('gross_w',0) for m_label,_,_ in INDIVIDUAL_MONTHS)
    gl=sum(results_ind.get(f'{m_label}_{key}',{}).get('gross_l',0) for m_label,_,_ in INDIVIDUAL_MONTHS)
    wr=tot_w/(tot_w+tot_l)*100 if (tot_w+tot_l)>0 else 0
    pf=gw/gl if gl>0 else (999 if gw>0 else 0)
    ind_agg[key]={'count':tot_t,'pnl':tot_p,'wins':tot_w,'losses':tot_l,
                   'wr':wr,'pf':pf,'gross_w':gw,'gross_l':gl,
                   'daily':tot_t/730,'balance':DEPOSIT+tot_p}

print(f"\n{'指标':<16} | {'NOISE+QS3':>18} | {'NOISE+QS4':>18} | {'NOISE+Q2':>18}")
print(f"{'-'*80}")
for metric_label, attr in [
    ('日均交易','daily'),('胜率%','wr'),('盈亏比(PF)','pf'),
    ('净盈亏($)','pnl'),('最终余额($)','balance'),
]:
    print(f"{metric_label:<16}", end='')
    for key,_ in STRATS_720_ORDER:
        r=ind_agg.get(key,{})
        if r:
            if attr=='daily': print(f" | {r[attr]:>17.1f}", end='')
            elif attr=='wr': print(f" | {r[attr]:>16.1f}%", end='')
            elif attr=='pf': print(f" | {r[attr]:>17.2f}", end='')
            elif attr=='balance': print(f" | ${r[attr]:>16.2f}", end='')
            else: print(f" | ${r[attr]:>16.2f}", end='')
        else: print(f" | {'':>17}", end='')
    print()

print(f"{'初始金额($)':<16} | ${DEPOSIT:>17} | ${DEPOSIT:>17} | ${DEPOSIT:>17}")
print(f"{'总交易数':<16}", end='')
for key,_ in STRATS_720_ORDER:
    print(f" | {ind_agg.get(key,{}).get('count',0):>17}", end='')
print()

# Monthly detail
print(f"\n\n  24月独立月度明细 (每月起始${DEPOSIT})")
print(f"  {'Month':<9}", end='')
for _,label in STRATS_720_ORDER: print(f" | {label:>10}", end='')
print(f"\n  {'-'*45}")
for m_label,_,_ in INDIVIDUAL_MONTHS:
    print(f"  {m_label:<9}", end='')
    for key,_ in STRATS_720_ORDER:
        r=results_ind.get(f'{m_label}_{key}',{})
        p=r.get('pnl',0)
        print(f" | ${DEPOSIT+p:>8.2f}", end='')
    print()

print(f"\n[DONE]")
