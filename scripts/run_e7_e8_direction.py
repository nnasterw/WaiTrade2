#!/usr/bin/env python3
"""E7/E8: 方向偏差修正实验 — 针对状态过滤器误判问题"""
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
    'InpBouncePct': '0.30',
    'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4',
    'InpMaxCounterRiskATR': '0.5',
    'InpMaxEntriesPerOB': '2',
    'InpEnableDeepestPullbackSL': 'true',
    'InpDeepestPullbackBuffer': '0.5',
}

DIR_TESTS = [
    # E7: 关闭状态过滤器 — 允许双向交易，让OB质量决定方向
    ('V11XAU-E7', 204843, 'E7:关闭状态过滤', {
        **D5B_BASE,
        'InpEnableStateFilter': 'false',
        'InpMaxCounterRiskATR': '0.5',  # 保留逆势风险限制
    }),

    # E8: 放宽状态检测 — 更长回看+更弱摆动=更稳定的方向判断
    ('V11XAU-E8', 204842, 'E8:放宽状态检测', {
        **D5B_BASE,
        'InpTrendLookback': '120',   # 从80→120，更长趋势判断
        'InpSwingStrength': '2',     # 从3→2，更容易判定为趋势
    }),

    # E9: 关闭状态过滤+低杠杆 — 最保守的双向策略
    ('V11XAU-E9', 204841, 'E9:无状态+低杠杆', {
        **D5B_BASE,
        'InpEnableStateFilter': 'false',
        'InpRiskPercent': '1.0',
        'InpMaxPosMult': '1.2',
    }),

    # E10: 只允许与HTF同向的交易 (H1 push filter更严格)
    ('V11XAU-E10', 204840, 'E10:强HTF对齐', {
        **D5B_BASE,
        'InpEnableHTFNetPushFilter': 'true',
        'InpHTFNetPushTF': '60',
        'InpHTFNetPushBars': '5',       # 从3→5，更长HTF确认
        'InpHTFNetPushMinATR': '0.25',  # 从0.35→0.25，更容易检测到push
        'InpHTFNetPushCounterMult': '0.3', # 从0.6→0.3，更严厉惩罚逆势
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
    report_name = f'{name}_{today_str}'

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
            if result.stdout.strip() == '0':
                break
        except: pass
    time.sleep(2)

    html_files = sorted(MT5_DATA.glob(f'{name}*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not html_files:
        return None

    raw = html_files[0].read_bytes()
    try:
        text = raw.decode('utf-16-le')
    except:
        text = raw.decode('utf-8', errors='ignore')

    lines = text.split('\n')
    trades = 0; wins = 0; losses = 0
    buys = 0; buy_wins = 0
    sells = 0; sell_wins = 0
    for line in lines:
        if 'XAUUSDm' not in line or 'out' not in line:
            continue
        if not re.search(r'<\s*td[^>]*>\s*out\s*<\s*/td\s*>', line, re.IGNORECASE):
            continue
        trades += 1
        clean = re.sub(r'<[^>]+>', ' | ', line).strip()
        parts = [p.strip() for p in clean.split('|')]
        non_empty = [p for p in parts if p]
        try: sym_idx = non_empty.index('XAUUSDm')
        except ValueError: continue

        direction = non_empty[sym_idx + 1] if sym_idx + 1 < len(non_empty) else ''
        inout = non_empty[sym_idx + 2] if sym_idx + 2 < len(non_empty) else ''
        if inout != 'out': continue

        if direction == 'buy': buys += 1
        elif direction == 'sell': sells += 1

        if len(non_empty) >= 3:
            try:
                profit_val = float(non_empty[-3].replace(' ', ''))
                if profit_val > 0.01:
                    wins += 1
                    if direction == 'buy': buy_wins += 1
                    elif direction == 'sell': sell_wins += 1
                elif profit_val < -0.01:
                    losses += 1
            except: pass

    wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
    buy_wr = (buy_wins / buys * 100) if buys > 0 else 0.0
    sell_wr = (sell_wins / sells * 100) if sells > 0 else 0.0

    balance = None
    for i in range(max(0, len(lines)-50), len(lines)):
        clean = re.sub(r'<[^>]+>', ' | ', lines[i]).strip()
        m = re.match(r'^\|\s*\|\s*(-?[\d\s]+[\d.]*\d)\s*\|\s*\|$', clean)
        if m:
            val_str = m.group(1).replace(' ', '').replace('\xa0', '')
            try: balance = float(val_str)
            except: pass

    return (trades, wr, balance, buys, buy_wr, sells, sell_wr) if balance is not None else None

# ── Main ──────────────────────────────────────────────────────
BAD_MONTHS = [
    ("2026.01.01", "2026.01.31", "2026-01"),
    ("2026.02.01", "2026.02.28", "2026-02"),
    ("2026.03.01", "2026.03.31", "2026-03"),
    ("2026.04.01", "2026.04.30", "2026-04"),
    ("2026.05.01", "2026.05.31", "2026-05"),
]

all_results = {}

for ver, magic, desc, params in DIR_TESTS:
    name = f'v11xau-{ver.split("-")[-1].lower()}'
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"{'='*60}")
    make_set(name, ver, magic, params)
    all_results[name] = {'desc': desc, 'months': {}}

    for date_from, date_to, label in BAD_MONTHS:
        print(f"  {label} ", end='', flush=True)
        r = run_bt(name, date_from, date_to)
        if r:
            t, wr, bal, buys, buy_wr, sells, sell_wr = r
            ret = (bal - 200) / 200 * 100
            all_results[name]['months'][label] = (t, wr, bal, ret, buys, buy_wr, sells, sell_wr)
            bal_ratio = f"{buys}/{sells}"
            print(f"{t:>4}t {wr:>5.1f}% ${bal:>9.2f} B:{buy_wr:.0f}%({buys}t) S:{sell_wr:.0f}%({sells}t)")
        else:
            print(f"FAILED")

# ── Summary ──────────────────────────────────────────────────
print(f"\n{'='*100}")
print(f"  方向偏差修正实验 — 2026年坏月汇总")
print(f"{'='*100}")

# D5B baseline ref
print(f"\n{'策略':<22} {'2026-01':>24} {'2026-02':>24} {'2026-03':>24} {'2026-04':>24} {'2026-05':>24}")

# E0 reference
D5B_REF = {
    '2026-01': (611, 48.3, 372.23, 0, 48.2, 0, 48.3),
    '2026-02': (340, 51.2, 172.47, 0, 58.8, 0, 47.1),
    '2026-03': (388, 45.4, 13.07, 0, 45.3, 0, 45.5),
    '2026-04': (262, 47.3, 1.41, 0, 45.2, 0, 50.0),
    '2026-05': (317, 43.5, 0.72, 0, 41.8, 0, 45.0),
}

def fmt_cell(r):
    if not r: return f"{'FAILED':>24}"
    t, wr, bal, ret, buys, buy_wr, sells, sell_wr = r
    return f"{t:>3}t {wr:>4.1f}% ${bal:>8.2f}"

def fmt_dir(r):
    if not r: return f"{'--':>24}"
    t, wr, bal, ret, buys, buy_wr, sells, sell_wr = r
    return f"B{buy_wr:.0f}%({buys})S{sell_wr:.0f}%({sells})"

print(f"{'D5B基线(E0)':<22}", end='')
for _, _, label in BAD_MONTHS:
    print(f" {fmt_cell(D5B_REF.get(label))}", end='')
print()
print(f"{'  方向偏差:':<22}", end='')
for _, _, label in BAD_MONTHS:
    print(f" {fmt_dir(D5B_REF.get(label))}", end='')
print()

for name, data in all_results.items():
    print(f"\n{data['desc']:<22}", end='')
    for _, _, label in BAD_MONTHS:
        r = data['months'].get(label)
        print(f" {fmt_cell(r)}", end='')
    print()
    print(f"{'  方向偏差:':<22}", end='')
    for _, _, label in BAD_MONTHS:
        r = data['months'].get(label)
        print(f" {fmt_dir(r)}", end='')
    print()

# Cleanup
for ver, _, _, _ in DIR_TESTS:
    name = f'v11xau-{ver.split("-")[-1].lower()}'
    sf = MT5_PROFILES_DIR / f'{name}.set'
    if sf.exists(): sf.unlink()

print(f"\nE7-E10 完成!")
