#!/usr/bin/env python3
"""G7: G2精调 — 隔离BE变化 vs TimeExit变化的影响"""
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

D5B_BASE = {
    'InpBouncePct': '0.30', 'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4', 'InpMaxCounterRiskATR': '0.5',
    'InpMaxEntriesPerOB': '2', 'InpEnableDeepestPullbackSL': 'true',
    'InpDeepestPullbackBuffer': '0.5',
}

G7_TESTS = [
    # G7: G2 minus TimeExit change — isolate BE effect
    ('V11XAU-G7', 204814, 'G7:早BE(TimeExit=20)', {
        **D5B_BASE,
        'InpBreakevenR': '0.25',
        'InpBreakevenLockR': '0.08',
        # TimeExitBars stays at 20 (D5B default from QS3 baseline)
    }),

    # G8: Slightly less aggressive BE (midway between D5B and ZD2)
    ('V11XAU-G8', 204813, 'G8:中BE(0.35/0.15)', {
        **D5B_BASE,
        'InpBreakevenR': '0.35',
        'InpBreakevenLockR': '0.15',
        'InpTimeExitBars': '999',
    }),

    # G9: G2 + 保留原本TimeExit
    ('V11XAU-G9', 204812, 'G9:早BE+TimeExit20(同G7)', {
        **D5B_BASE,
        'InpBreakevenR': '0.25',
        'InpBreakevenLockR': '0.08',
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
    return dst

def kill_mt5_tester():
    try:
        subprocess.run(['powershell', '-Command',
            "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"
        ], capture_output=True, timeout=10)
    except: pass
    time.sleep(3)

def run_bt(name, date_from, date_to, timeout=180):
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
Report={name}_{today_str}
"""
    ini_file.write_text(ini_content)
    kill_mt5_tester()
    for old in MT5_DATA.glob(f'{name}*.htm'):
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
    html_files = sorted(MT5_DATA.glob(f'{name}*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
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

# ── Main ──────────────────────────────────────────────────────
# Only test the critical months: 2025-10 (good) + 2026-03 (worst improvement)
KEY_MONTHS = [
    ("2025.10.01", "2025.10.31", "2025-10"),
    ("2026.03.01", "2026.03.31", "2026-03"),
]

REF = {
    'D5B': {'2025-10': (395, 72.2, 51297.69), '2026-03': (388, 45.4, 13.07)},
    'G2':  {'2025-10': (395, 74.9, 47985.08), '2026-03': (386, 49.5, 114.49)},
}

print(f"{'策略':<25} {'2025-10(好月)':>24} {'2026-03(坏月)':>24}")
print("-" * 75)
for ref_name in ['D5B', 'G2']:
    r10 = REF[ref_name]['2025-10']
    r03 = REF[ref_name]['2026-03']
    print(f"{ref_name:<25} {r10[0]:>4}t {r10[1]:>5.1f}% ${r10[2]:>9,.0f}  {r03[0]:>4}t {r03[1]:>5.1f}% ${r03[2]:>9,.2f}")

for ver, magic, desc, params in G7_TESTS:
    name = f'v11xau-{ver.split("-")[-1].lower()}'
    print(f"\n{desc}")
    make_set(name, ver, magic, params)
    results = {}
    for date_from, date_to, label in KEY_MONTHS:
        print(f"  {label} ", end='', flush=True)
        r = run_bt(name, date_from, date_to)
        if r:
            t, wr, bal = r
            results[label] = (t, wr, bal)
            print(f"{t:>4}t {wr:>5.1f}% ${bal:>9,.2f}")
        else:
            print(f"FAILED")

    r10 = results.get('2025-10')
    r03 = results.get('2026-03')
    s10 = f"{r10[0]:>4}t {r10[1]:>5.1f}% ${r10[2]:>9,.0f}" if r10 else "FAILED"
    s03 = f"{r03[0]:>4}t {r03[1]:>5.1f}% ${r03[2]:>9,.2f}" if r03 else "FAILED"
    vs10 = f"{(r10[2]-51297.69)/51297.69*100:+.1f}%" if r10 else ""
    vs03 = f"{(r03[2]-13.07)/13.07*100:+.0f}%" if r03 else ""
    print(f"  vs D5B:       {vs10:>8}          {vs03:>8}")

for ver, _, _, _ in G7_TESTS:
    sf = MT5_PROFILES_DIR / f'v11xau-{ver.split("-")[-1].lower()}.set'
    if sf.exists(): sf.unlink()
print(f"\nG7精调完成!")
