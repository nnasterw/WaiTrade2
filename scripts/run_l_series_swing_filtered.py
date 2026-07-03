#!/usr/bin/env python3
"""L系列: 基于单子分析 — 大赢小时过滤 + swing = 去scalp留波段"""
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

# K6 swing base
SWING_BASE = {
    'InpBouncePct': '0.30', 'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4', 'InpMaxCounterRiskATR': '0.5',
    'InpMaxEntriesPerOB': '2',
    'InpEnableDeepestPullbackSL': 'true', 'InpDeepestPullbackBuffer': '0.5',
    'InpBreakevenR': '0.25', 'InpBreakevenLockR': '0.08',
    'InpDTPTriggerR': '8.0', 'InpAdaptiveDTP': 'false',
    'InpDTPRetrace': '0.2', 'InpTimeExitBars': '999',
}

L_TESTS = [
    # L1: K6 + 仅大赢时段 (0,1,3,6,8,13) — 基于单子分析:16个大赢全部在这些小时
    ('V11XAU-L1', 204770, 'L1:K6+大赢时(0,1,3,6,8,13)', {
        **SWING_BASE,
        'InpNoEntryHours': '2,4,5,7,9,10,11,12,14,15,16,17,18,19,20,21,22,23',
    }),

    # L2: K6 + 过滤大亏时段 (12,14,15,17,18,19,22,23) — 去掉毒时
    ('V11XAU-L2', 204769, 'L2:K6-毒时(12,14-23)', {
        **SWING_BASE,
        'InpNoEntryHours': '12,14,15,17,18,19,20,22,23',
    }),

    # L3: K6 + 仅最优时段 (0,1,3,6,8,11,13) — 稍放宽
    ('V11XAU-L3', 204768, 'L3:K6+优时(0,1,3,6,8,11,13)', {
        **SWING_BASE,
        'InpNoEntryHours': '2,4,5,7,9,10,12,14,15,16,17,18,19,20,21,22,23',
    }),

    # L4: K6 + 仅伦敦+纽约重叠 (8,13,14,15,16) — 高流动性时段
    ('V11XAU-L4', 204767, 'L4:K6+伦敦纽约(8,13-16)', {
        **SWING_BASE,
        'InpNoEntryHours': '0,1,2,3,4,5,6,7,9,10,11,12,17,18,19,20,21,22,23',
    }),

    # L5: QS4 scalp + 大赢时段 — scalp在正确的时段可能就够了
    ('V11XAU-L5', 204766, 'L5:scalp+大赢时(0,1,3,6,8,13)', {
        'InpBouncePct': '0.30', 'InpBounceSweetMinPct': '0.35',
        'InpOutsideBounceSweetMult': '0.4', 'InpMaxCounterRiskATR': '0.5',
        'InpMaxEntriesPerOB': '2',
        'InpEnableDeepestPullbackSL': 'true', 'InpDeepestPullbackBuffer': '0.5',
        'InpNoEntryHours': '2,4,5,7,9,10,11,12,14,15,16,17,18,19,20,21,22,23',
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

def run_bt(name, date_from, date_to, timeout=240):
    ini = MT5_TESTER_DIR / 'backtest.ini'
    ts = datetime.now().strftime('%Y%m%d')
    ini.write_text(f"""[Common]\nLogin=\nServer=\n[Tester]\nExpert=WaiTrade2\\WaiTrade_OB
ExpertParameters={name}.set\nSymbol=XAUUSDm\nPeriod=M1\nModel=4\nOptimization=0
FromDate={date_from}\nToDate={date_to}\nDeposit=200\nCurrency=USD\nLeverage=2000
ExecutionMode=0\nShutdownTerminal=1\nReport=lseries_{name}_{ts}\n""")
    kill_mt5_tester()
    for old in MT5_DATA.glob(f'lseries_{name}*.htm'):
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
    files = sorted(MT5_DATA.glob(f'lseries_{name}*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files: return None
    raw = files[0].read_bytes()
    try: text = raw.decode('utf-16-le')
    except: text = raw.decode('utf-8', errors='ignore')
    lines = text.split('\n')
    trades = 0; wins = 0; losses = 0
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
                if pv > 0.01: wins += 1
                elif pv < -0.01: losses += 1
            except: pass
    wr = (wins/(wins+losses)*100) if (wins+losses)>0 else 0.0
    bal = None
    for i in range(max(0, len(lines)-50), len(lines)):
        clean = re.sub(r'<[^>]+>', ' | ', lines[i]).strip()
        m = re.match(r'^\|\s*\|\s*(-?[\d\s]+[\d.]*\d)\s*\|\s*\|$', clean)
        if m:
            try: bal = float(m.group(1).replace(' ','').replace('\xa0',''))
            except: pass
    return (trades, wr, bal) if bal is not None else None

MONTHS = [("2025.10.01","2025.10.31","2025-10"),("2026.05.01","2026.05.31","2026-05")]
REF = {'QS4': (395,72.2,51297.69,317,43.5,0.72), 'K6': (395,74.9,19568.93,463,45.0,80.54)}

print(f"{'策略':<38} {'交易':>5} {'WR':>6} {'余额':>12} | {'交易':>5} {'WR':>6} {'余额':>12}")
print(f"{'':<38} {'2025-10(好月)':>25} | {'2026-05(坏月)':>25}")
print("-"*95)
for ref in ['QS4','K6']:
    r = REF[ref]
    print(f"{ref:<38} {r[0]:>5} {r[1]:>5.1f}% ${r[2]:>10,.0f} | {r[3]:>5} {r[4]:>5.1f}% ${r[5]:>10,.2f}")

for ver, magic, desc, params in L_TESTS:
    name = f'v11xau-{ver.split("-")[-1].lower()}'
    print(f"\n{desc}")
    make_set(name, ver, magic, params)
    results = {}
    for df, dt, label in MONTHS:
        print(f"  {label} ", end='', flush=True)
        r = run_bt(name, df, dt)
        if r: results[label] = r
        t, wr, bal = r if r else (0,0,0)
        print(f"{t:>4}t {wr:>5.1f}% ${bal:>10,.2f}")
    r10 = results.get('2025-10'); r05 = results.get('2026-05')
    s10 = f"{r10[0]:>5} {r10[1]:>5.1f}% ${r10[2]:>10,.0f}" if r10 else "FAILED"
    s05 = f"{r05[0]:>5} {r05[1]:>5.1f}% ${r05[2]:>10,.2f}" if r05 else "FAILED"
    print(f"  {'':<38} {s10} | {s05}")

for ver, _, _, _ in L_TESTS:
    sf = MT5_PROFILES_DIR / f'v11xau-{ver.split("-")[-1].lower()}.set'
    if sf.exists(): sf.unlink()
print("\nL系列完成!")
