#!/usr/bin/env python3
"""N系列: 针对评分系统在坏月失效的结构性改进"""
import os, sys, re, time, subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
MT5_TESTER_DIR = MT5_DATA / 'Tester'; MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
BASE_SET = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'

QS4 = {'InpBouncePct':'0.30','InpBounceSweetMinPct':'0.35','InpOutsideBounceSweetMult':'0.4',
       'InpMaxCounterRiskATR':'0.5','InpMaxEntriesPerOB':'2',
       'InpEnableDeepestPullbackSL':'true','InpDeepestPullbackBuffer':'0.5'}

N_TESTS = [
    # N1: 关闭评分 — 所有交易统一仓位,消除坏月放大效应
    ('V11XAU-N1', 204750, 'N1:关闭评分(统一仓位)', {
        **QS4, 'InpEnableScoring': 'false', 'InpMaxPosMult': '1.0',
    }),
    # N2: 限制最大倍率 — 1.5x上限,保留评分但削峰
    ('V11XAU-N2', 204749, 'N2:限倍率1.5x', {
        **QS4, 'InpMaxPosMult': '1.5',
    }),
    # N3: 最低评分门槛 — 只做高评分交易
    ('V11XAU-N3', 204748, 'N3:最低评分门槛', {
        **QS4, 'InpMinScore': '2',
    }),
    # N4: N1 + M4波段出场
    ('V11XAU-N4', 204747, 'N4:关评分+波段(M4出场)', {
        **QS4, 'InpEnableScoring': 'false', 'InpMaxPosMult': '1.0',
        'InpEnableDeepestPullbackSL': 'false', 'InpSLBufferATR': '0.7',
        'InpBreakevenR': '0.7', 'InpBreakevenLockR': '0.2',
        'InpDTPTriggerR': '2.0', 'InpAdaptiveDTP': 'false', 'InpDTPRetrace': '0.25',
        'InpTimeExitBars': '120',
    }),
    # N5: N2 + M4波段
    ('V11XAU-N5', 204746, 'N5:限倍率1.5x+波段', {
        **QS4, 'InpMaxPosMult': '1.5',
        'InpEnableDeepestPullbackSL': 'false', 'InpSLBufferATR': '0.7',
        'InpBreakevenR': '0.7', 'InpBreakevenLockR': '0.2',
        'InpDTPTriggerR': '2.0', 'InpAdaptiveDTP': 'false', 'InpDTPRetrace': '0.25',
        'InpTimeExitBars': '120',
    }),
]

def replace_param(c,k,v):
    p=re.compile(rf'^{k}=.*$',re.MULTILINE)
    return p.sub(f'{k}={v}',c) if p.search(c) else c+f'\n{k}={v}\n'

def make_set(name,ver,magic,params):
    dst=MT5_PROFILES_DIR/f'{name}.set'
    c=BASE_SET.read_text(encoding='utf-8')
    for k,v in {'InpVersion':ver,'InpMagicNumber':str(magic),'InpEnableEntryDebug':'true'}.items():c=replace_param(c,k,v)
    for k,v in params.items():c=replace_param(c,k,v)
    dst.write_text(c)

def kill_mt5():
    try:subprocess.run(['powershell','-Command',"Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"],capture_output=True,timeout=10)
    except:pass;time.sleep(3)

def run_bt(name,df,dt,to=240):
    ini=MT5_TESTER_DIR/'backtest.ini';ts=datetime.now().strftime('%Y%m%d')
    ini.write_text(f"[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\nExpertParameters={name}.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0\nFromDate={df}\nToDate={dt}\nDeposit=200\nCurrency=USD\nLeverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport=nseries_{name}_{ts}\n")
    kill_mt5()
    for o in MT5_DATA.glob(f'nseries_{name}*.htm'):
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
    fs=sorted(MT5_DATA.glob(f'nseries_{name}*.htm'),key=lambda p:p.stat().st_mtime,reverse=True)
    if not fs:return None
    raw=fs[0].read_bytes()
    try:text=raw.decode('utf-16-le')
    except:text=raw.decode('utf-8',errors='ignore')
    lines=text.split('\n')
    trades=0;wins=0;losses=0;tp=0;tl=0
    for line in lines:
        if 'XAUUSDm' not in line or 'out' not in line:continue
        if not re.search(r'<\s*td[^>]*>\s*out\s*<\s*/td\s*>',line,re.IGNORECASE):continue
        trades+=1
        clean=re.sub(r'<[^>]+>',' | ',line).strip()
        parts=[p.strip() for p in clean.split('|')]
        ne=[p for p in parts if p]
        try:si=ne.index('XAUUSDm')
        except ValueError:continue
        if si+2>=len(ne) or ne[si+2]!='out':continue
        if len(ne)>=3:
            try:
                pv=float(ne[-3].replace(' ',''))
                if pv>0.01:wins+=1;tp+=pv
                elif pv<-0.01:losses+=1;tl+=abs(pv)
            except:pass
    wr=(wins/(wins+losses)*100) if (wins+losses)>0 else 0.0
    aw=tp/wins if wins>0 else 0;al=tl/losses if losses>0 else 0
    pf=aw/al if al>0 else 99
    bal=None
    for i in range(max(0,len(lines)-50),len(lines)):
        clean=re.sub(r'<[^>]+>',' | ',lines[i]).strip()
        m=re.match(r'^\|\s*\|\s*(-?[\d\s]+[\d.]*\d)\s*\|\s*\|$',clean)
        if m:
            try:bal=float(m.group(1).replace(' ','').replace('\xa0',''))
            except:pass
    return (trades,wr,bal,aw,al,pf) if bal is not None else None

MONTHS=[("2025.10.01","2025.10.31","2025-10"),("2026.05.01","2026.05.31","2026-05")]

print(f"{'策略':<35} {'交易':>5} {'WR':>6} {'余额':>12} {'均赢':>8} {'均亏':>8} {'PF':>5} | "
      f"{'交易':>5} {'WR':>6} {'余额':>12} {'均赢':>8} {'均亏':>8} {'PF':>5}")
print(f"{'':<35} {'2025-10(好月)':>46} | {'2026-05(坏月)':>46}")
print("-"*140)
QS4_G=(395,72.2,51297.69,237.9,151.9,1.57);QS4_B=(317,43.5,0.72,1.9,2.6,0.74)
M4_G=(553,63.8,52554.84,202.2,95.0,2.13);M4_B=(198,30.8,-0.31,2.5,2.6,0.96)
def fmt(r):return f"{r[0]:>5} {r[1]:>5.1f}% ${r[2]:>10,.0f} ${r[3]:>7.1f} ${r[4]:>7.1f} {r[5]:>4.2f}" if r else "FAILED"
print(f"{'QS4 scalp':<35} {fmt(QS4_G)} | {fmt(QS4_B)}")
print(f"{'M4 波段':<35} {fmt(M4_G)} | {fmt(M4_B)}")

for ver,magic,desc,params in N_TESTS:
    name=f'v11xau-{ver.split("-")[-1].lower()}'
    print(f"\n{desc}")
    make_set(name,ver,magic,params)
    results={}
    for df,dt,label in MONTHS:
        print(f"  {label} ",end='',flush=True)
        r=run_bt(name,df,dt)
        if r:results[label]=r
        t,wr,bal,aw,al,pf=r if r else (0,0,0,0,0,0)
        print(f"{t:>4}t {wr:>5.1f}% ${bal:>10,.2f} W${aw:>6.1f} L${al:>6.1f} PF={pf:.2f}")
    r10=results.get('2025-10');r05=results.get('2026-05')
    print(f"  {'':<35} {fmt(r10)} | {fmt(r05)}")

for ver,_,_,_ in N_TESTS:
    sf=MT5_PROFILES_DIR/f'v11xau-{ver.split("-")[-1].lower()}.set'
    if sf.exists():sf.unlink()
print("\nN系列完成!")
