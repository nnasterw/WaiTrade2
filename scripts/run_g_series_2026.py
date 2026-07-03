#!/usr/bin/env python3
"""G系列：ZD2盈利智慧注入D5B — 紧入场+早锁利+让赢家跑+夜间过滤"""
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

G_TESTS = [
    # G1: 紧入场 — ZD2的核心: MaxEntryOffsetR 1.2→0.5, EntryDepthFilter OFF
    ('V11XAU-G1', 204820, 'G1:紧入场(0.5R+浅弹)', {
        **D5B_BASE,
        'InpMaxEntryOffsetR': '0.5',       # ZD2: 必须更靠近OB才入场
        'InpEntryDepthPct': '0.50',         # ZD2: 允许更浅的入场深度
        'InpEntryDepthFilter': 'false',     # ZD2: 不强制深度入场
    }),

    # G2: 早锁利 — ZD2的核心: BE提前到0.25R, 锁定仅0.08R, 时间出场999
    ('V11XAU-G2', 204819, 'G2:早锁利(BE0.25+无时限)', {
        **D5B_BASE,
        'InpBreakevenR': '0.25',            # ZD2: 0.25R就锁
        'InpBreakevenLockR': '0.08',        # ZD2: 只锁0.08R
        'InpTimeExitBars': '999',           # ZD2: 几乎不限时
    }),

    # G3: 夜间OB过滤 — ZD2的核心: 屏蔽23-6点亚洲时段
    ('V11XAU-G3', 204818, 'G3:夜间过滤(23-6)', {
        **D5B_BASE,
        'InpNoOBStartHour': '23',
        'InpNoOBEndHour': '6',
    }),

    # G4: 紧入场+早锁利 组合
    ('V11XAU-G4', 204817, 'G4:紧入场+早锁利', {
        **D5B_BASE,
        'InpMaxEntryOffsetR': '0.5',
        'InpEntryDepthPct': '0.50',
        'InpEntryDepthFilter': 'false',
        'InpBreakevenR': '0.25',
        'InpBreakevenLockR': '0.08',
        'InpTimeExitBars': '999',
    }),

    # G5: 紧入场+早锁利+夜间过滤 全组合
    ('V11XAU-G5', 204816, 'G5:紧入+早锁+夜滤(全)', {
        **D5B_BASE,
        'InpMaxEntryOffsetR': '0.5',
        'InpEntryDepthPct': '0.50',
        'InpEntryDepthFilter': 'false',
        'InpBreakevenR': '0.25',
        'InpBreakevenLockR': '0.08',
        'InpTimeExitBars': '999',
        'InpNoOBStartHour': '23',
        'InpNoOBEndHour': '6',
    }),

    # G6: G5 + DP-SL收紧到0.3 (综合ZD2智慧)
    ('V11XAU-G6', 204815, 'G6:G5+紧DP-SL0.3', {
        **D5B_BASE,
        'InpMaxEntryOffsetR': '0.5',
        'InpEntryDepthPct': '0.50',
        'InpEntryDepthFilter': 'false',
        'InpBreakevenR': '0.25',
        'InpBreakevenLockR': '0.08',
        'InpTimeExitBars': '999',
        'InpNoOBStartHour': '23',
        'InpNoOBEndHour': '6',
        'InpDeepestPullbackBuffer': '0.3',  # 更紧的DP-SL
    }),
]

def replace_param(content, key, val):
    pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
    if pattern.search(content):
        return pattern.sub(f'{key}={val}', content)
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
    report_name = f'gseries_{name}_{today_str}'

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
Report={report_name}
"""
    ini_file.write_text(ini_content)
    kill_mt5_tester()
    for old in MT5_DATA.glob(f'gseries_{name}*.htm'):
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

    html_files = sorted(MT5_DATA.glob(f'gseries_{name}*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
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
MONTHS = [
    ("2025.10.01", "2025.10.31", "2025-10"),
    ("2026.01.01", "2026.01.31", "2026-01"),
    ("2026.02.01", "2026.02.28", "2026-02"),
    ("2026.03.01", "2026.03.31", "2026-03"),
    ("2026.04.01", "2026.04.30", "2026-04"),
    ("2026.05.01", "2026.05.31", "2026-05"),
]

REF = {
    'D5B': {'2025-10': (395, 72.2, 51297.69), '2026-01': (611, 48.3, 372.23),
            '2026-02': (340, 51.2, 172.47), '2026-03': (388, 45.4, 13.07),
            '2026-04': (262, 47.3, 1.41), '2026-05': (317, 43.5, 0.72)},
    'ZD2': {'2025-10': (10, 90.0, 198.33), '2026-01': (9, 77.8, 190.07),
            '2026-02': (3, 100.0, 1123.49), '2026-03': (5, 80.0, 186.21),
            '2026-04': (8, 100.0, 310.35), '2026-05': (3, 33.3, 191.99)},
}

all_results = {}
for ver, magic, desc, params in G_TESTS:
    name = f'v11xau-{ver.split("-")[-1].lower()}'
    print(f"\n{'='*55}")
    print(f"  {desc}")
    print(f"{'='*55}")
    make_set(name, ver, magic, params)
    all_results[name] = {'desc': desc, 'months': {}}
    for date_from, date_to, label in MONTHS:
        print(f"  {label} ", end='', flush=True)
        r = run_bt(name, date_from, date_to)
        if r:
            t, wr, bal = r
            ret = (bal - 200) / 200 * 100
            all_results[name]['months'][label] = (t, wr, bal, ret)
            print(f"{t:>4}t {wr:>5.1f}% ${bal:>9.2f} ({ret:>+6.1f}%)")
        else:
            print(f"FAILED")

# ── Summary ──────────────────────────────────────────────────
print(f"\n{'='*120}")
print(f"  G系列: ZD2智慧注入D5B — 2025-10(好月)+2026(坏月)对比")
print(f"{'='*120}")

def fmt(r): return f"{r[0]:>4}t {r[1]:>5.1f}% ${r[2]:>9.2f}" if r else f"{'FAILED':>22}"

for ref_name in ['D5B', 'ZD2']:
    print(f"\n{ref_name}基线", end='')
    for _,_,label in MONTHS:
        r = REF[ref_name].get(label)
        print(f"  {fmt(r)}", end='')
print()

for name, data in all_results.items():
    print(f"\n{data['desc']}", end='')
    for _,_,label in MONTHS:
        r = data['months'].get(label)
        print(f"  {fmt(r)}", end='')

# ── Best performer ───────────────────────────────────────────
print(f"\n\n{'='*80}")
print(f"  各月最佳G策略 vs D5B/ZD2")
print(f"{'='*80}")
for _,_,label in MONTHS:
    best_name, best_bal = 'D5B', REF['D5B'][label][2]
    for ref_name in ['ZD2']:
        if REF[ref_name][label][2] > best_bal:
            best_bal = REF[ref_name][label][2]; best_name = ref_name
    for name, data in all_results.items():
        r = data['months'].get(label)
        if r and r[2] > best_bal:
            best_bal = r[2]; best_name = data['desc']
    d5b_bal = REF['D5B'][label][2]
    imp = (best_bal - d5b_bal) / d5b_bal * 100 if d5b_bal > 0 else 999
    print(f"  {label}: {best_name} ${best_bal:.2f} (vs D5B ${d5b_bal:.2f}, {imp:+.0f}%)")

for ver, _, _, _ in G_TESTS:
    sf = MT5_PROFILES_DIR / f'v11xau-{ver.split("-")[-1].lower()}.set'
    if sf.exists(): sf.unlink()
print(f"\nG系列完成!")
