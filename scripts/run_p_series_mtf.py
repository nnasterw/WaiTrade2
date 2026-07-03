#!/usr/bin/env python3
"""P系列: MTF框架逐规则实现 — 每条规则一个实验, 2026-05验证"""
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

P_TESTS = [
    # R3: 逆15M降权 — CounterMult 0.6→0.3 (大幅降低逆势仓位)
    ('V11XAU-P1', 204730, 'P1:R3-逆势降权0.3', {
        **QS4,
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '15',              # 15M趋势
        'InpHTFNetPushBars': '3',
        'InpHTFNetPushMinATR': '0.35',
        'InpHTFNetPushAlignedMult': '1.3',    # 顺15M加仓
        'InpHTFNetPushNeutralMult': '1.0',
        'InpHTFNetPushCounterMult': '0.3',    # 逆15M降70%
    }),

    # R8: 大周期止盈 — 启用HTF Target
    ('V11XAU-P2', 204729, 'P2:R8-HTF目标(15M)', {
        **QS4,
        'InpEnableHTFTarget': 'true',
        'InpHTFTargetTF': '15',
        'InpHTFTargetLookback': '96',
        'InpHTFSwingStrength': '2',
        'InpHTFMinTargetR': '2.0',
        'InpHTFMaxTargetR': '6.0',
        'InpHTFMeasuredMoveR': '2.0',
        'InpHTFRequireAligned': 'true',       # 只在对齐时用大目标
        'InpHTFPartialR': '1.0',
        'InpHTFPartialPct': '50',
        'InpHTFSkipDTP': 'false',
        'InpHTFSkipTrail': 'false',
    }),

    # R6: 方向切换后冷却
    ('V11XAU-P3', 204728, 'P3:R6-切换冷却10bar', {
        **QS4,
        'InpCooldownBars': '10',
        'InpOBReentryCooldownMin': '15',
    }),

    # R2+R4: 启用HTF Pullback — 15M OB区域检测
    ('V11XAU-P4', 204727, 'P4:R2+R4-HTF回踩(15M)', {
        **QS4,
        'InpEnableHTFPullback': 'true',
        'InpHTFPullbackOnly': 'false',
        'InpHTFPullbackTF': '15',
        'InpHTFPullbackBars': '3',
        'InpHTFPullbackMinATR': '0.8',
        'InpHTFPullbackZoneATR': '0.35',
        'InpHTFPullbackOffsetATR': '0.1',
        'InpHTFPullbackTPMult': '1.0',
    }),

    # P5: 综合 — R3+R6+R8 (逆势降权+切换冷却+大目标)
    ('V11XAU-P5', 204726, 'P5:R3+R6+R8综合', {
        **QS4,
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '15', 'InpHTFNetPushBars': '3',
        'InpHTFNetPushMinATR': '0.35',
        'InpHTFNetPushAlignedMult': '1.3',
        'InpHTFNetPushNeutralMult': '1.0',
        'InpHTFNetPushCounterMult': '0.3',
        'InpCooldownBars': '10',
        'InpOBReentryCooldownMin': '15',
        'InpEnableHTFTarget': 'true',
        'InpHTFTargetTF': '15', 'InpHTFTargetLookback': '96',
        'InpHTFSwingStrength': '2', 'InpHTFMinTargetR': '2.0',
        'InpHTFMaxTargetR': '6.0', 'InpHTFRequireAligned': 'true',
    }),

    # P6: 全框架 — P5 + P4 (所有规则)
    ('V11XAU-P6', 204725, 'P6:全MTF框架', {
        **QS4,
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '15', 'InpHTFNetPushBars': '3',
        'InpHTFNetPushMinATR': '0.35',
        'InpHTFNetPushAlignedMult': '1.3',
        'InpHTFNetPushNeutralMult': '1.0',
        'InpHTFNetPushCounterMult': '0.3',
        'InpCooldownBars': '10',
        'InpOBReentryCooldownMin': '15',
        'InpEnableHTFTarget': 'true',
        'InpHTFTargetTF': '15', 'InpHTFTargetLookback': '96',
        'InpHTFSwingStrength': '2', 'InpHTFMinTargetR': '2.0',
        'InpHTFMaxTargetR': '6.0', 'InpHTFRequireAligned': 'true',
        'InpEnableHTFPullback': 'true',
        'InpHTFPullbackOnly': 'false', 'InpHTFPullbackTF': '15',
        'InpHTFPullbackBars': '3', 'InpHTFPullbackMinATR': '0.8',
        'InpHTFPullbackZoneATR': '0.35', 'InpHTFPullbackOffsetATR': '0.1',
        'InpHTFPullbackTPMult': '1.0',
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
    ini.write_text(f"[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\nExpertParameters={name}.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0\nFromDate={df}\nToDate={dt}\nDeposit=200\nCurrency=USD\nLeverage=2000\nExecutionMode=0\nShutdownTerminal=1\nReport=pseries_{name}_{ts}\n")
    kill_mt5()
    for o in MT5_DATA.glob(f'pseries_{name}*.htm'):
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
    fs=sorted(MT5_DATA.glob(f'pseries_{name}*.htm'),key=lambda p:p.stat().st_mtime,reverse=True)
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

print(f"{'P系列: MTF框架逐规则验证':^100}")
print(f"{'策略':<30} {'2025-10 交易':>6} {'WR':>6} {'余额':>12} {'PF':>5} | "
      f"{'2026-05 交易':>6} {'WR':>6} {'余额':>12} {'PF':>5} | {'好月Δ':>8} {'坏月Δ':>8}")
print("-"*120)
def fmt(r):return f"{r[0]:>6} {r[1]:>5.1f}% ${r[2]:>10,.0f} {r[5]:>4.2f}" if r else f"{'FAILED':>30}"
print(f"{'QS4 baseline':<30} {fmt(QS4_G)} | {fmt(QS4_B)} | {'baseline':>8} {'baseline':>8}")

for ver,magic,desc,params in P_TESTS:
    name=f'v11xau-{ver.split("-")[-1].lower()}'
    print(f"\n{desc}")
    make_set(name,ver,magic,params)
    results={}
    for df,dt,label in MONTHS:
        print(f"  {label} ",end='',flush=True)
        r=run_bt(name,df,dt)
        if r:results[label]=r
        t,wr,bal,aw,al,pf=r if r else (0,0,0,0,0,0)
        print(f"{t:>4}t {wr:>5.1f}% ${bal:>10,.2f} PF={pf:.2f}")
    r10=results.get('2025-10');r05=results.get('2026-05')
    d10=f"{(r10[2]-51297.69)/51297.69*100:+.1f}%" if r10 else "-"
    d05=f"{(r05[2]-0.72)/max(0.01,0.72)*100:+.0f}%" if r05 and r05[2]>0 else "-"
    print(f"  {'':<30} {fmt(r10)} | {fmt(r05)} | {d10:>8} {d05:>8}")

for ver,_,_,_ in P_TESTS:
    sf=MT5_PROFILES_DIR/f'v11xau-{ver.split("-")[-1].lower()}.set'
    if sf.exists():sf.unlink()
print("\nP系列完成!")
