#!/usr/bin/env python3
"""E系列改进实验：针对2026年5个坏月 — 基于D5B交易诊断的6组防御方案"""
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

# ═══════════════════════════════════════════════════════════════
# E系列实验：6组方案针对2026年坏月
# ═══════════════════════════════════════════════════════════════
E_TESTS = [
    # E0: D5B baseline (reference)
    ('V11XAU-E0', 204850, 'E0:D5B基线', dict(D5B_BASE)),

    # E1: 月度熔断强化 — 亏损15%停本月，20笔后检查10%熔断
    ('V11XAU-E1', 204849, 'E1:月度熔断15%', {
        **D5B_BASE,
        'InpMonthlyLossStopPct': '15.0',
        'InpMonthlyEarlyLossStopTrades': '20',
        'InpMonthlyEarlyLossStopPct': '10.0',
    }),

    # E2: 降低杠杆 — risk减半，pos_mult降到1.2
    ('V11XAU-E2', 204848, 'E2:低杠杆', {
        **D5B_BASE,
        'InpRiskPercent': '1.0',
        'InpMaxPosMult': '1.2',
    }),

    # E3: 延长冷却+限制入场 — 打破连续亏损簇
    ('V11XAU-E3', 204847, 'E3:冷却+限入', {
        **D5B_BASE,
        'InpCooldownBars': '5',
        'InpOBReentryCooldownMin': '15',
        'InpMaxEntriesPerOB': '1',
    }),

    # E4: 收紧出场 — 更早BE锁利 + 固定TP 1.0R
    ('V11XAU-E4', 204846, 'E4:紧出场', {
        **D5B_BASE,
        'InpBreakevenR': '0.3',
        'InpBreakevenLockR': '0.2',
        'InpFixedTPR': '1.0',
    }),

    # E5: 关闭深度入场boost — 避免放大坏入场
    ('V11XAU-E5', 204845, 'E5:无深度boost', {
        **D5B_BASE,
        'InpDeepEntryBoost': '1.0',
        'InpEntryDepthPct': '0.50',
    }),

    # E6: 综合防御 — 降杠杆+冷却+紧出场
    ('V11XAU-E6', 204844, 'E6:综合防御', {
        **D5B_BASE,
        'InpRiskPercent': '1.0',
        'InpMaxPosMult': '1.2',
        'InpCooldownBars': '3',
        'InpBreakevenR': '0.3',
        'InpBreakevenLockR': '0.2',
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
        if sym_idx + 2 >= len(non_empty) or non_empty[sym_idx + 2] != 'out':
            continue
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
BAD_MONTHS = [
    ("2026.01.01", "2026.01.31", "2026-01"),
    ("2026.02.01", "2026.02.28", "2026-02"),
    ("2026.03.01", "2026.03.31", "2026-03"),
    ("2026.04.01", "2026.04.30", "2026-04"),
    ("2026.05.01", "2026.05.31", "2026-05"),
]

all_results = {}

for ver, magic, desc, params in E_TESTS:
    name = f'v11xau-{ver.split("-")[-1].lower()}'
    print(f"\n{'='*50}")
    print(f"  {desc}")
    print(f"{'='*50}")
    make_set(name, ver, magic, params)
    all_results[name] = {'desc': desc, 'months': {}}

    for date_from, date_to, label in BAD_MONTHS:
        print(f"  {label} ", end='', flush=True)
        r = run_bt(name, date_from, date_to)
        if r:
            t, wr, bal = r
            ret = (bal - 200) / 200 * 100
            all_results[name]['months'][label] = (t, wr, bal, ret)
            print(f"{t:>4}t {wr:>5.1f}% ${bal:>8.2f} ({ret:>+6.1f}%)")
        else:
            print(f"FAILED")

# ── Summary Table ─────────────────────────────────────────────
print(f"\n{'='*110}")
print(f"  2026年坏月防御实验汇总 (每月独立起始 $200)")
print(f"{'='*110}")
print(f"{'策略':<22}", end='')
for _, _, label in BAD_MONTHS:
    print(f" {'交易/WR/余额':>24}", end='')
print(f" {'总计':>12} {'月均余额':>10}")
print("-" * 130)

# D5B baseline from earlier data for comparison
D5B_REF = {
    '2026-01': (611, 48.3, 372.23),
    '2026-02': (340, 51.2, 172.47),
    '2026-03': (388, 45.4, 13.07),
    '2026-04': (262, 47.3, 1.41),
    '2026-05': (317, 43.5, 0.72),
}

# Print D5B ref
print(f"{'D5B基线(参考)':<22}", end='')
total_bal = 0
for _, _, label in BAD_MONTHS:
    r = D5B_REF.get(label)
    if r:
        t, wr, bal = r
        total_bal += bal
        print(f" {t:>4}t {wr:>4.1f}% ${bal:>8.2f}", end='')
    else:
        print(f" {'N/A':>24}", end='')
print(f" {'--':>12} ${total_bal/5:>9.2f}")

# Print E-series
for name, data in all_results.items():
    print(f"{data['desc']:<22}", end='')
    total_bal = 0
    count = 0
    for _, _, label in BAD_MONTHS:
        r = data['months'].get(label)
        if r:
            t, wr, bal, ret = r
            total_bal += bal
            count += 1
            print(f" {t:>4}t {wr:>4.1f}% ${bal:>8.2f}", end='')
        else:
            print(f" {'FAILED':>24}", end='')
    avg_bal = total_bal / count if count > 0 else 0
    print(f" {count:>5}月 ${avg_bal:>9.2f}")

# ── Best per month ────────────────────────────────────────────
print(f"\n{'='*80}")
print(f"  逐月最佳策略")
print(f"{'='*80}")
for _, _, label in BAD_MONTHS:
    best_name = 'D5B_ref'
    best_bal = D5B_REF.get(label, (0, 0, 0))[2]
    for name, data in all_results.items():
        r = data['months'].get(label)
        if r and r[2] > best_bal:
            best_bal = r[2]
            best_name = data['desc']
    print(f"  {label}: {best_name} (${best_bal:.2f})")

# Cleanup
for ver, _, _, _ in E_TESTS:
    name = f'v11xau-{ver.split("-")[-1].lower()}'
    sf = MT5_PROFILES_DIR / f'{name}.set'
    if sf.exists(): sf.unlink()

print(f"\nE系列实验完成!")
