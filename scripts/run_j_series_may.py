#!/usr/bin/env python3
"""J系列：激进降频 — 针对scalp模式在坏月的自毁特性"""
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

QS4_BASE = {
    'InpBouncePct': '0.30', 'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4', 'InpMaxCounterRiskATR': '0.5',
    'InpMaxEntriesPerOB': '2', 'InpEnableDeepestPullbackSL': 'true',
    'InpDeepestPullbackBuffer': '0.5',
}

J_TESTS = [
    # J1: 激进全局冷却 — 从1bar→20bar(20分钟), 打破高频模式
    ('V11XAU-J1', 204790, 'J1:冷却20bar', {
        **QS4_BASE,
        'InpCooldownBars': '20',
    }),

    # J2: 限制每小时最多3笔
    ('V11XAU-J2', 204789, 'J2:时上限3笔', {
        **QS4_BASE,
        'InpCooldownBars': '10',
        'InpMaxEntriesPerOB': '1',
        'InpMaxConcurrent': '2',
    }),

    # J3: 过滤毒时段(02,12,15,17,18,19,20,23) + 冷却
    ('V11XAU-J3', 204788, 'J3:毒时过滤+冷却', {
        **QS4_BASE,
        'InpCooldownBars': '10',
        'InpNoEntryHours': '2,12,15,17,18,19,20,23',
    }),

    # J4: 极端降频 — 冷却30bar + 仅1并发 + 毒时过滤
    ('V11XAU-J4', 204787, 'J4:极端降频', {
        **QS4_BASE,
        'InpCooldownBars': '30',
        'InpMaxConcurrent': '1',
        'InpMaxEntriesPerOB': '1',
        'InpNoEntryHours': '2,12,15,17,18,19,20,23',
    }),

    # J5: 日亏限10% — 日亏损超10%停当日
    ('V11XAU-J5', 204786, 'J5:日亏限10%', {
        **QS4_BASE,
        'InpDailyLossStopPct': '10.0',
        'InpCooldownBars': '10',
    }),

    # J6: 综合激进 — J1+J3+J5
    ('V11XAU-J6', 204785, 'J6:综合(冷却+毒时+日亏限)', {
        **QS4_BASE,
        'InpCooldownBars': '20',
        'InpNoEntryHours': '2,12,15,17,18,19,20,23',
        'InpDailyLossStopPct': '10.0',
        'InpMaxConcurrent': '2',
        'InpMaxEntriesPerOB': '1',
    }),
]

def replace_param(content, key, val):
    pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
    if pattern.search(content): return pattern.sub(f'{key}={val}', content)
    return content + f'\n{key}={val}\n'

def make_set(name, version, magic, params):
    dst = MT5_PROFILES_DIR / f'{name}.set'
    content = BASE_SET.read_text(encoding='utf-8')
    content = replace_param(content, 'InpVersion', version)
    content = replace_param(content, 'InpMagicNumber', str(magic))
    content = replace_param(content, 'InpEnableEntryDebug', 'true')
    for key, val in params.items():
        content = replace_param(content, key, val)
    dst.write_text(content)

def kill_mt5_tester():
    try:
        subprocess.run(['powershell', '-Command',
            "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"
        ], capture_output=True, timeout=10)
    except: pass
    time.sleep(3)

def run_bt(name, date_from, date_to, timeout=240):
    ini_file = MT5_TESTER_DIR / 'backtest.ini'
    today_str = datetime.now().strftime('%Y%m%d')
    ini_content = f"""[Common]
Login=
Server=
[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters={name}.set
Symbol=XAUUSDm
Period=M1
Model=4
Optimization=0
FromDate={date_from}
ToDate={date_to}
Deposit=200
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report=jseries_{name}_{today_str}
"""
    ini_file.write_text(ini_content)
    kill_mt5_tester()
    for old in MT5_DATA.glob(f'jseries_{name}*.htm'):
        try: old.unlink()
        except: pass
    subprocess.Popen([MT5_TERMINAL, f'/config:{ini_file}'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(timeout // 5):
        time.sleep(5)
        try:
            result = subprocess.run(['powershell', '-Command',
                "(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
                "Where-Object { $_.Path -like '*Program Files*' }).Count"
            ], capture_output=True, text=True, timeout=5)
            if result.stdout.strip() == '0': break
        except: pass
    time.sleep(2)
    html_files = sorted(MT5_DATA.glob(f'jseries_{name}*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not html_files: return None
    raw = html_files[0].read_bytes()
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
        non_empty = [p for p in parts if p]
        try: sym_idx = non_empty.index('XAUUSDm')
        except ValueError: continue
        if sym_idx + 2 >= len(non_empty) or non_empty[sym_idx + 2] != 'out': continue
        if len(non_empty) >= 3:
            try:
                profit_val = float(non_empty[-3].replace(' ', ''))
                if profit_val > 0.01: wins += 1
                elif profit_val < -0.01: losses += 1
            except: pass
    wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
    balance = None
    for i in range(max(0, len(lines)-50), len(lines)):
        clean = re.sub(r'<[^>]+>', ' | ', lines[i]).strip()
        m = re.match(r'^\|\s*\|\s*(-?[\d\s]+[\d.]*\d)\s*\|\s*\|$', clean)
        if m:
            val_str = m.group(1).replace(' ', '').replace('\xa0', '')
            try: balance = float(val_str)
            except: pass
    return (trades, wr, balance) if balance is not None else None

MONTHS = [("2025.10.01", "2025.10.31", "2025-10"), ("2026.05.01", "2026.05.31", "2026-05")]
QS4_REF = {'2025-10': (395, 72.2, 51297.69), '2026-05': (317, 43.5, 0.72)}

print(f"{'策略':<35} {'2025-10(好月)':>28} {'2026-05(坏月)':>28}")
print("-" * 95)
print(f"{'QS4(D5B)':<35} 395t  72.2% $   51,298  317t  43.5% $      0.72")

for ver, magic, desc, params in J_TESTS:
    name = f'v11xau-{ver.split("-")[-1].lower()}'
    print(f"\n{desc}")
    make_set(name, ver, magic, params)
    results = {}
    for date_from, date_to, label in MONTHS:
        print(f"  {label} ", end='', flush=True)
        r = run_bt(name, date_from, date_to)
        if r:
            t, wr, bal = r; results[label] = (t, wr, bal)
            print(f"{t:>4}t {wr:>5.1f}% ${bal:>10,.2f}")
        else:
            print(f"FAILED")
    r10 = results.get('2025-10'); r05 = results.get('2026-05')
    if r10 and r05:
        v10 = (r10[2]-51297.69)/51297.69*100
        v05 = (r05[2]-0.72)/0.72*100 if r05[2] > 0 else 0
        print(f"  vs QS4:       {v10:>+8.1f}%          {v05:>+8.0f}%")

for ver, _, _, _ in J_TESTS:
    sf = MT5_PROFILES_DIR / f'v11xau-{ver.split("-")[-1].lower()}.set'
    if sf.exists(): sf.unlink()
print(f"\nJ系列完成!")
