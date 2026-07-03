#!/usr/bin/env python3
"""M系列：通用波段参数 — 宽SL+晚锁利+高DTP+长时限, 不由任何单月调优"""
import os, sys, re, time, subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
MT5_TESTER_DIR = MT5_DATA / 'Tester'
MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
BASE_SET = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'

QS4_ENTRY = {  # 入场逻辑不变
    'InpBouncePct': '0.30', 'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4', 'InpMaxCounterRiskATR': '0.5',
    'InpMaxEntriesPerOB': '2',
}

M_TESTS = [
    # M1: ATR宽止损 + 1R证明确认 + 3R波段 + 4小时时限
    ('V11XAU-M1', 204760, 'M1:ATR1.0/BE1.0/DTP3/T240', {
        **QS4_ENTRY,
        'InpEnableDeepestPullbackSL': 'false',
        'InpSLBufferATR': '1.0',           # 1 ATR呼吸空间
        'InpBreakevenR': '1.0',            # 1R后才锁利(证明自己是好交易)
        'InpBreakevenLockR': '0.3',
        'InpDTPTriggerR': '3.0',           # 3R启动跟踪止盈
        'InpAdaptiveDTP': 'false',
        'InpDTPRetrace': '0.3',
        'InpTimeExitBars': '240',          # 4小时时限(足够波段发展)
    }),

    # M2: DP-SL结构止损 + 同M1出场
    ('V11XAU-M2', 204759, 'M2:DP1.0/BE1.0/DTP3/T240', {
        **QS4_ENTRY,
        'InpEnableDeepestPullbackSL': 'true',
        'InpDeepestPullbackBuffer': '1.0', # 宽结构止损
        'InpBreakevenR': '1.0',
        'InpBreakevenLockR': '0.3',
        'InpDTPTriggerR': '3.0',
        'InpAdaptiveDTP': 'false',
        'InpDTPRetrace': '0.3',
        'InpTimeExitBars': '240',
    }),

    # M3: 更宽+更高 — ATR1.5/BE1.5/DTP5/T480
    ('V11XAU-M3', 204758, 'M3:ATR1.5/BE1.5/DTP5/T480', {
        **QS4_ENTRY,
        'InpEnableDeepestPullbackSL': 'false',
        'InpSLBufferATR': '1.5',
        'InpBreakevenR': '1.5',
        'InpBreakevenLockR': '0.5',
        'InpDTPTriggerR': '5.0',
        'InpAdaptiveDTP': 'false',
        'InpDTPRetrace': '0.3',
        'InpTimeExitBars': '480',
    }),

    # M4: 中庸 — ATR0.7/BE0.7/DTP2/T120 (scalp和波段中间)
    ('V11XAU-M4', 204757, 'M4:ATR0.7/BE0.7/DTP2/T120', {
        **QS4_ENTRY,
        'InpEnableDeepestPullbackSL': 'false',
        'InpSLBufferATR': '0.7',
        'InpBreakevenR': '0.7',
        'InpBreakevenLockR': '0.2',
        'InpDTPTriggerR': '2.0',
        'InpAdaptiveDTP': 'false',
        'InpDTPRetrace': '0.25',
        'InpTimeExitBars': '120',
    }),

    # M5: M1 + 降频 — 加冷却减少交易密度
    ('V11XAU-M5', 204756, 'M5:M1+冷却20+限入1', {
        **QS4_ENTRY,
        'InpEnableDeepestPullbackSL': 'false',
        'InpSLBufferATR': '1.0',
        'InpBreakevenR': '1.0',
        'InpBreakevenLockR': '0.3',
        'InpDTPTriggerR': '3.0',
        'InpAdaptiveDTP': 'false',
        'InpDTPRetrace': '0.3',
        'InpTimeExitBars': '240',
        'InpCooldownBars': '20',
        'InpMaxEntriesPerOB': '1',
        'InpMaxConcurrent': '2',
    }),
]

def replace_param(c, k, v):
    p = re.compile(rf'^{k}=.*$', re.MULTILINE)
    return p.sub(f'{k}={v}', c) if p.search(c) else c + f'\n{k}={v}\n'

def make_set(name, version, magic, params):
    dst = MT5_PROFILES_DIR / f'{name}.set'
    content = BASE_SET.read_text(encoding='utf-8')
    content = replace_param(content, 'InpVersion', version)
    content = replace_param(content, 'InpMagicNumber', str(magic))
    content = replace_param(content, 'InpEnableEntryDebug', 'true')
    for k, v in params.items(): content = replace_param(content, k, v)
    dst.write_text(content)

def kill_mt5_tester():
    try:
        subprocess.run(['powershell', '-Command',
            "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"
        ], capture_output=True, timeout=10)
    except: pass; time.sleep(3)

def run_bt(name, date_from, date_to, timeout=300):
    ini = MT5_TESTER_DIR / 'backtest.ini'
    ts = datetime.now().strftime('%Y%m%d')
    ini.write_text(f"""[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB
ExpertParameters={name}.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0
FromDate={date_from}\nToDate={date_to}\nDeposit=200\nCurrency=USD\nLeverage=2000
ExecutionMode=0\nShutdownTerminal=1\nReport=mseries_{name}_{ts}\n""")
    kill_mt5_tester()
    for old in MT5_DATA.glob(f'mseries_{name}*.htm'):
        try: old.unlink()
        except: pass
    subprocess.Popen([MT5_TERMINAL, f'/config:{ini}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(timeout//5):
        time.sleep(5)
        try:
            r = subprocess.run(['powershell', '-Command',
                "(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
                "Where-Object { $_.Path -like '*Program Files*' }).Count"],
                capture_output=True, text=True, timeout=5)
            if r.stdout.strip() == '0': break
        except: pass
    time.sleep(2)
    files = sorted(MT5_DATA.glob(f'mseries_{name}*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files: return None
    raw = files[0].read_bytes()
    try: text = raw.decode('utf-16-le')
    except: text = raw.decode('utf-8', errors='ignore')
    lines = text.split('\n')
    trades = 0; wins = 0; losses = 0; tprofit = 0; tloss = 0
    for line in lines:
        if 'XAUUSDm' not in line or 'out' not in line: continue
        if not re.search(r'<\s*td[^>]*>\s*out\s*<\s*/td\s*>', line, re.IGNORECASE): continue
        trades += 1
        clean = re.sub(r'<[^>]+>', ' | ', line).strip()
        parts = [p.strip() for p in clean.split('|')]
        ne = [p for p in parts if p]
        try: si = ne.index('XAUUSDm')
        except ValueError: continue
        if si+2 >= len(ne) or ne[si+2] != 'out': continue
        if len(ne) >= 3:
            try:
                pv = float(ne[-3].replace(' ',''))
                if pv > 0.01: wins += 1; tprofit += pv
                elif pv < -0.01: losses += 1; tloss += abs(pv)
            except: pass
    wr = (wins/(wins+losses)*100) if (wins+losses)>0 else 0.0
    aw = tprofit/wins if wins>0 else 0; al = tloss/losses if losses>0 else 0
    pf = aw/al if al>0 else 99
    bal = None
    for i in range(max(0,len(lines)-50), len(lines)):
        clean = re.sub(r'<[^>]+>', ' | ', lines[i]).strip()
        m = re.match(r'^\|\s*\|\s*(-?[\d\s]+[\d.]*\d)\s*\|\s*\|$', clean)
        if m:
            try: bal = float(m.group(1).replace(' ','').replace('\xa0',''))
            except: pass
    return (trades, wr, bal, aw, al, pf) if bal is not None else None

MONTHS = [("2025.10.01","2025.10.31","2025-10"),("2026.05.01","2026.05.31","2026-05")]

print(f"{'策略':<35} {'交易':>5} {'WR':>6} {'余额':>12} {'均赢':>8} {'均亏':>8} {'PF':>5} | "
      f"{'交易':>5} {'WR':>6} {'余额':>12} {'均赢':>8} {'均亏':>8} {'PF':>5}")
print(f"{'':<35} {'2025-10(好月)':>46} | {'2026-05(坏月)':>46}")
print("-"*140)

QS4_G = (395,72.2,51297.69,237.9,151.9,1.57)
QS4_B = (317,43.5,0.72,1.9,2.6,0.74)

def fmt(r): return f"{r[0]:>5} {r[1]:>5.1f}% ${r[2]:>10,.0f} ${r[3]:>7.1f} ${r[4]:>7.1f} {r[5]:>4.2f}" if r else f"{'FAILED':>46}"
print(f"{'QS4 scalp(基线)':<35} {fmt(QS4_G)} | {fmt(QS4_B)}")

for ver, magic, desc, params in M_TESTS:
    name = f'v11xau-{ver.split("-")[-1].lower()}'
    print(f"\n{desc}")
    make_set(name, ver, magic, params)
    results = {}
    for df, dt, label in MONTHS:
        print(f"  {label} ", end='', flush=True)
        r = run_bt(name, df, dt)
        if r: results[label] = r
        t,wr,bal,aw,al,pf = r if r else (0,0,0,0,0,0)
        print(f"{t:>4}t {wr:>5.1f}% ${bal:>10,.2f} W${aw:>6.1f} L${al:>6.1f} PF={pf:.2f}")
    r10 = results.get('2025-10'); r05 = results.get('2026-05')
    print(f"  {'':<35} {fmt(r10)} | {fmt(r05)}")

for ver,_,_,_ in M_TESTS:
    sf = MT5_PROFILES_DIR / f'v11xau-{ver.split("-")[-1].lower()}.set'
    if sf.exists(): sf.unlink()
print("\nM系列完成!")
