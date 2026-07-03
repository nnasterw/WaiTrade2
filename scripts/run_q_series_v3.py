#!/usr/bin/env python3
"""Q系列: MTF框架v3 — 阻止逆H1 + 15M回踩 + 波段出场"""
import os, sys, re, time, subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
MT5_TESTER_DIR = MT5_DATA / 'Tester'; MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
BASE_SET = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'

QS4_ENTRY = {'InpBouncePct':'0.30','InpBounceSweetMinPct':'0.35','InpOutsideBounceSweetMult':'0.4',
             'InpMaxCounterRiskATR':'0.5','InpMaxEntriesPerOB':'2',
             'InpEnableDeepestPullbackSL':'true','InpDeepestPullbackBuffer':'0.5'}

Q_TESTS = [
    # Q1: 阻止逆H1 — HTFNetPush on H1, Counter=0.0
    ('V11XAU-Q1', 204720, 'Q1:阻止逆H1', {
        **QS4_ENTRY,
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '60',              # H1级别
        'InpHTFNetPushBars': '5',             # 5根H1 bar确认
        'InpHTFNetPushMinATR': '0.4',
        'InpHTFNetPushAlignedMult': '1.3',
        'InpHTFNetPushNeutralMult': '1.0',
        'InpHTFNetPushCounterMult': '0.0',    # 逆H1=阻止!
    }),

    # Q2: Q1 + 15M回踩 — HTFPullback找15M OB
    ('V11XAU-Q2', 204719, 'Q2:Q1+15M回踩', {
        **QS4_ENTRY,
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '60', 'InpHTFNetPushBars': '5',
        'InpHTFNetPushMinATR': '0.4',
        'InpHTFNetPushAlignedMult': '1.3',
        'InpHTFNetPushNeutralMult': '1.0',
        'InpHTFNetPushCounterMult': '0.0',
        'InpEnableHTFPullback': 'true',
        'InpHTFPullbackOnly': 'false', 'InpHTFPullbackTF': '15',
        'InpHTFPullbackBars': '3', 'InpHTFPullbackMinATR': '0.8',
        'InpHTFPullbackZoneATR': '0.35', 'InpHTFPullbackOffsetATR': '0.1',
        'InpHTFPullbackTPMult': '1.0',
    }),

    # Q3: Q2 + H1大目标 — HTFTarget启用
    ('V11XAU-Q3', 204718, 'Q3:Q2+H1目标', {
        **QS4_ENTRY,
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '60', 'InpHTFNetPushBars': '5',
        'InpHTFNetPushMinATR': '0.4',
        'InpHTFNetPushAlignedMult': '1.3',
        'InpHTFNetPushNeutralMult': '1.0',
        'InpHTFNetPushCounterMult': '0.0',
        'InpEnableHTFPullback': 'true',
        'InpHTFPullbackOnly': 'false', 'InpHTFPullbackTF': '15',
        'InpHTFPullbackBars': '3', 'InpHTFPullbackMinATR': '0.8',
        'InpHTFPullbackZoneATR': '0.35', 'InpHTFPullbackOffsetATR': '0.1',
        'InpHTFPullbackTPMult': '1.0',
        'InpEnableHTFTarget': 'true',
        'InpHTFTargetTF': '60', 'InpHTFTargetLookback': '96',
        'InpHTFSwingStrength': '2', 'InpHTFMinTargetR': '2.0',
        'InpHTFMaxTargetR': '8.0', 'InpHTFRequireAligned': 'true',
    }),

    # Q4: Q3 + 波段出场(M4) — 逆H1阻止+回踩+大目标+波段SL
    ('V11XAU-Q4', 204717, 'Q4:全v3(逆H1+回踩+H1目标+波段)', {
        **QS4_ENTRY,
        'InpEnableDeepestPullbackSL': 'false',
        'InpSLBufferATR': '0.7',
        'InpBreakevenR': '0.7', 'InpBreakevenLockR': '0.2',
        'InpDTPTriggerR': '2.0', 'InpAdaptiveDTP': 'false', 'InpDTPRetrace': '0.25',
        'InpTimeExitBars': '120',
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '60', 'InpHTFNetPushBars': '5',
        'InpHTFNetPushMinATR': '0.4',
        'InpHTFNetPushAlignedMult': '1.3',
        'InpHTFNetPushNeutralMult': '1.0',
        'InpHTFNetPushCounterMult': '0.0',
        'InpEnableHTFPullback': 'true',
        'InpHTFPullbackOnly': 'false', 'InpHTFPullbackTF': '15',
        'InpHTFPullbackBars': '3', 'InpHTFPullbackMinATR': '0.8',
        'InpHTFPullbackZoneATR': '0.35', 'InpHTFPullbackOffsetATR': '0.1',
        'InpHTFPullbackTPMult': '1.0',
        'InpEnableHTFTarget': 'true',
        'InpHTFTargetTF': '60', 'InpHTFTargetLookback': '96',
        'InpHTFSwingStrength': '2', 'InpHTFMinTargetR': '2.0',
        'InpHTFMaxTargetR': '8.0', 'InpHTFRequireAligned': 'true',
    }),

    # Q5: Q4 + 冷却 — 全框架最严格版
    ('V11XAU-Q5', 204716, 'Q5:Q4+冷却5bar', {
        **QS4_ENTRY,
        'InpEnableDeepestPullbackSL': 'false', 'InpSLBufferATR': '0.7',
        'InpBreakevenR': '0.7', 'InpBreakevenLockR': '0.2',
        'InpDTPTriggerR': '2.0', 'InpAdaptiveDTP': 'false', 'InpDTPRetrace': '0.25',
        'InpTimeExitBars': '120',
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '60', 'InpHTFNetPushBars': '5',
        'InpHTFNetPushMinATR': '0.4',
        'InpHTFNetPushAlignedMult': '1.3', 'InpHTFNetPushNeutralMult': '1.0',
        'InpHTFNetPushCounterMult': '0.0',
        'InpEnableHTFPullback': 'true',
        'InpHTFPullbackOnly': 'false', 'InpHTFPullbackTF': '15',
        'InpHTFPullbackBars': '3', 'InpHTFPullbackMinATR': '0.8',
        'InpHTFPullbackZoneATR': '0.35', 'InpHTFPullbackOffsetATR': '0.1',
        'InpEnableHTFTarget': 'true',
        'InpHTFTargetTF': '60', 'InpHTFTargetLookback': '96',
        'InpHTFSwingStrength': '2', 'InpHTFMinTargetR': '2.0',
        'InpHTFMaxTargetR': '8.0', 'InpHTFRequireAligned': 'true',
        'InpCooldownBars': '5', 'InpMaxConcurrent': '3',
    }),
]

def rep(c,k,v):
    p=re.compile(rf'^{k}=.*$',re.MULTILINE)
    return p.sub(f'{k}={v}',c) if p.search(c) else c+f'\n{k}={v}\n'

def make_set(name,ver,magic,params):
    dst=MT5_PROFILES_DIR/f'{name}.set'
    c=BASE_SET.read_text(encoding='utf-8')
    for k,v in {'InpVersion':ver,'InpMagicNumber':str(magic),'InpEnableEntryDebug':'true'}.items():c=rep(c,k,v)
    for k,v in params.items():c=rep(c,k,v)
    dst.write_text(c)

def kill_mt5():
    try:subprocess.run(['powershell','-Command',"Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"],capture_output=True,timeout=10)
    except:pass;time.sleep(3)

def run_bt(name,df,dt,to=300):
    ini=MT5_TESTER_DIR/'backtest.ini';ts=datetime.now().strftime('%Y%m%d')
    ini.write_text(f"[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\nExpertParameters={name}.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0\nFromDate={df}\nToDate={dt}\nDeposit=200\nCurrency=USD\nLeverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport=qseries_{name}_{ts}\n")
    kill_mt5()
    for o in MT5_DATA.glob(f'qseries_{name}*.htm'):
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
    fs=sorted(MT5_DATA.glob(f'qseries_{name}*.htm'),key=lambda p:p.stat().st_mtime,reverse=True)
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
QS4_G=(395,72.2,51297.69,237.9,151.9,1.57);QS4_B=(317,43.5,0.72,1.9,2.6,0.74)
P4_G=(1421,69.5,218183.84,0,0,1.14);P4_B=(180,38.9,1.33,0,0,0.64)
P6_G=(985,68.2,98565.29,0,0,1.10);P6_B=(389,42.2,1.71,0,0,0.78)

print(f"{'策略':<30} {'交易':>6} {'WR':>6} {'余额':>14} {'PF':>5} | {'交易':>6} {'WR':>6} {'余额':>14} {'PF':>5} | {'好月':>8} {'坏月':>8}")
print(f"{'':<30} {'2025-10(好月)':>33} | {'2026-05(坏月)':>33} |")
print("-"*120)
def fm(r):return f"{r[0]:>6} {r[1]:>5.1f}% ${r[2]:>12,.0f} {r[5]:>4.2f}" if r else f"{'FAILED':>30}"
for ref_name,r10,r05 in [('QS4 baseline',QS4_G,QS4_B),('P4 HTF回踩',P4_G,P4_B),('P6 全MTF',P6_G,P6_B)]:
    print(f"{ref_name:<30} {fm(r10)} | {fm(r05)} | {'':>8} {'':>8}")

for ver,magic,desc,params in Q_TESTS:
    name=f'v11xau-{ver.split("-")[-1].lower()}'
    print(f"\n{desc}")
    make_set(name,ver,magic,params)
    results={}
    for df,dt,label in MONTHS:
        print(f"  {label} ",end='',flush=True)
        r=run_bt(name,df,dt)
        if r:results[label]=r
        t,wr,bal,aw,al,pf=r if r else (0,0,0,0,0,0)
        print(f"{t:>4}t {wr:>5.1f}% ${bal:>12,.2f} PF={pf:.2f}")
    r10=results.get('2025-10');r05=results.get('2026-05')
    d10=f"{(r10[2]-51297.69)/51297.69*100:+.1f}%" if r10 else "-"
    d05=f"{(r05[2]-0.72)/max(0.01,0.72)*100:+.0f}%" if r05 and r05[2]>0 else "-"
    print(f"  {'':<30} {fm(r10)} | {fm(r05)} | {d10:>8} {d05:>8}")

for ver,_,_,_ in Q_TESTS:
    sf=MT5_PROFILES_DIR/f'v11xau-{ver.split("-")[-1].lower()}.set'
    if sf.exists():sf.unlink()
print("\nQ系列完成!")
