#!/usr/bin/env python3
"""F系列：基于ZD2互补发现的设计改进 — 体制切换+暖机保护"""
import os, sys, re, time, subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict

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

F_TESTS = [
    # F1: D5B移植ZD2暖机保护 — 月初0.1x仓位,盈利1%后恢复正常
    ('V11XAU-F1', 204830, 'F1:D5B+ZD2暖机', {
        **D5B_BASE,
        'InpMonthlyWarmupProfitPct': '1.0',    # 月盈利1%后恢复全仓
        'InpMonthlyWarmupPosMult': '0.1',       # 暖机期间0.1x
        'InpMonthlyNegativePosMult': '0.1',     # 亏损时0.1x
        'InpConsecutiveLossCooldown': '5',      # 5连亏后冷却
        'InpConsecutiveLossCooldownMin': '10',  # 冷却10分钟
    }),

    # F2: D5B移植ZD2日亏限 — 日亏1%停当日
    ('V11XAU-F2', 204829, 'F2:D5B+日亏限', {
        **D5B_BASE,
        'InpDailyLossStopPct': '1.0',           # 日亏1%停当日
        'InpMonthlyLossStopPct': '10.0',        # 月亏10%停当月
        'InpMaxConcurrent': '2',                 # 最多2并发
    }),

    # F3: D5B+暖机+日亏限+低并发 综合
    ('V11XAU-F3', 204828, 'F3:D5B+暖机+日亏+低并发', {
        **D5B_BASE,
        'InpMonthlyWarmupProfitPct': '1.0',
        'InpMonthlyWarmupPosMult': '0.1',
        'InpMonthlyNegativePosMult': '0.1',
        'InpDailyLossStopPct': '1.0',
        'InpMonthlyLossStopPct': '10.0',
        'InpMaxConcurrent': '2',
        'InpMaxPosMult': '1.5',
    }),

    # F4: ZD2参数 — risk从3%提高到5% (高WR可以承受)
    # Use ZD2 base .set
    ('V11XAU-F4', 204827, 'F4:ZD2高risk5%', {
        # This will use ZD2 .set as base
    }),
]

def replace_param(content, key, val):
    pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
    if pattern.search(content):
        return pattern.sub(f'{key}={val}', content)
    return content + f'\n{key}={val}\n'

def make_set(name, version, magic, params, base='QS3'):
    if base == 'ZD2':
        src = ROOT / 'mql5' / 'Presets' / 'V11XAU-ZD2.set'
    else:
        src = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'

    dst = MT5_PROFILES_DIR / f'{name}.set'
    content = src.read_text(encoding='utf-8')
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
    report_name = f'fseries_{name}_{today_str}'

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
    for old in MT5_DATA.glob(f'fseries_{name}*.htm'):
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

    html_files = sorted(MT5_DATA.glob(f'fseries_{name}*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not html_files:
        return None

    raw = html_files[0].read_bytes()
    try: text = raw.decode('utf-16-le')
    except: text = raw.decode('utf-8', errors='ignore')

    lines = text.split('\n')
    trades = 0; wins = 0; losses = 0
    buys = 0; buy_wins = 0; sells = 0; sell_wins = 0
    for line in lines:
        if 'XAUUSDm' not in line or 'out' not in line: continue
        if not re.search(r'<\s*td[^>]*>\s*out\s*<\s*/td\s*>', line, re.IGNORECASE): continue
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
                elif profit_val < -0.01: losses += 1
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

for ver, magic, desc, params in F_TESTS:
    name = f'v11xau-{ver.split("-")[-1].lower()}'
    base = 'ZD2' if ver == 'V11XAU-F4' else 'QS3'
    print(f"\n{'='*55}")
    print(f"  {desc}")
    print(f"{'='*55}")
    make_set(name, ver, magic, params, base)
    all_results[name] = {'desc': desc, 'months': {}}

    for date_from, date_to, label in BAD_MONTHS:
        print(f"  {label} ", end='', flush=True)
        r = run_bt(name, date_from, date_to)
        if r:
            t, wr, bal, buys, buy_wr, sells, sell_wr = r
            ret = (bal - 200) / 200 * 100
            all_results[name]['months'][label] = (t, wr, bal, ret, buys, buy_wr, sells, sell_wr)
            print(f"{t:>4}t {wr:>5.1f}% ${bal:>9.2f} ({ret:>+6.1f}%) B:{buy_wr:.0f}%({buys})S:{sell_wr:.0f}%({sells})")
        else:
            print(f"FAILED")

# ── Comparison Table ──────────────────────────────────────────
print(f"\n{'='*110}")
print(f"  F系列 vs 基准: D5B vs ZD2 vs F1-F4")
print(f"{'='*110}")

# Reference data
D5B_REF = {
    '2026-01': (611, 48.3, 372.23, +86.1, 342, 48.2, 269, 48.3),
    '2026-02': (340, 51.2, 172.47, -13.8, 119, 58.8, 221, 47.1),
    '2026-03': (388, 45.4, 13.07, -93.5, 223, 45.3, 165, 45.5),
    '2026-04': (262, 47.3, 1.41, -99.3, 146, 45.2, 116, 50.0),
    '2026-05': (317, 43.5, 0.72, -99.6, 146, 41.8, 171, 45.0),
}
ZD2_REF = {
    '2026-01': (9, 77.8, 190.07, -5.0, 1, 0.0, 8, 87.5),
    '2026-02': (3, 100.0, 1123.49, +461.7, 3, 100.0, 0, 0.0),
    '2026-03': (5, 80.0, 186.21, -6.9, 1, 100.0, 4, 75.0),
    '2026-04': (8, 100.0, 310.35, +55.2, 5, 100.0, 3, 100.0),
    '2026-05': (3, 33.3, 191.99, -4.0, 3, 33.3, 0, 0.0),
}

print(f"{'策略':<25}", end='')
for _,_,label in BAD_MONTHS:
    print(f" {label:>20}", end='')
print(f" {'月均余额':>10}")
print("-" * 130)

for ref_name, ref_data in [('D5B基线', D5B_REF), ('ZD2基线', ZD2_REF)]:
    print(f"{ref_name:<25}", end='')
    total = 0
    for _,_,label in BAD_MONTHS:
        r = ref_data.get(label)
        if r:
            t, wr, bal = r[0], r[1], r[2]
            total += bal
            print(f" {t:>4}t {wr:>4.1f}% ${bal:>8.2f}", end='')
        else:
            print(f" {'--':>20}", end='')
    print(f" ${total/5:>9.2f}")

for name, data in all_results.items():
    print(f"{data['desc']:<25}", end='')
    total = 0
    count = 0
    for _,_,label in BAD_MONTHS:
        r = data['months'].get(label)
        if r:
            t, wr, bal = r[0], r[1], r[2]
            total += bal
            count += 1
            print(f" {t:>4}t {wr:>4.1f}% ${bal:>8.2f}", end='')
        else:
            print(f" {'FAILED':>20}", end='')
    avg = total/count if count > 0 else 0
    print(f" ${avg:>9.2f}")

# ── Simulated switching strategy ──────────────────────────────
print(f"\n{'='*110}")
print(f"  月度切换模拟: 上月D5B亏>10%→本月用ZD2")
print(f"{'='*110}")

# Simple rule: if last month D5B balance < $180 (loss > 10%), use ZD2
switch_balance = 200.0
using = 'D5B'
results = []
for _,_,label in BAD_MONTHS:
    if using == 'D5B':
        r = D5B_REF.get(label)
    else:
        r = ZD2_REF.get(label)

    if r:
        t, wr, bal = r[0], r[1], r[2]
        monthly_return = (bal - 200) / 200
        switch_balance *= (1 + monthly_return)
        results.append((label, using, bal))

        # Switch rule: if using D5B and lost >10%, switch to ZD2 next month
        if using == 'D5B' and bal < 180:
            using = 'ZD2'
            print(f"  {label}: {using}={bal:.2f} → ⚠️ 切换! 下月用ZD2 (累计${switch_balance:.2f})")
        elif using == 'ZD2' and bal > 200:
            # Stay with ZD2 while it's winning
            print(f"  {label}: {using}={bal:.2f} → ZD2盈利,继续保持 (累计${switch_balance:.2f})")
        else:
            print(f"  {label}: {using}={bal:.2f} (累计${switch_balance:.2f})")

print(f"\n  切换策略5个月累计: ${switch_balance:.2f}")
print(f"  纯D5B 5个月累计: ${200 * (372.23/200) * (172.47/200) * (13.07/200) * (1.41/200) * (0.72/200):.2f}")

# Cleanup
for ver, _, _, _ in F_TESTS:
    name = f'v11xau-{ver.split("-")[-1].lower()}'
    sf = MT5_PROFILES_DIR / f'{name}.set'
    if sf.exists(): sf.unlink()

print(f"\nF系列完成!")
