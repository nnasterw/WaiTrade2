#!/usr/bin/env python3
"""G2 24个月回测：与 QS3/D5B 月度对比"""
import os, sys, re, time, subprocess
from pathlib import Path
from datetime import datetime
from calendar import monthrange

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
MT5_TESTER_DIR = MT5_DATA / 'Tester'
MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
BASE_SET = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'
RESULTS_DIR = ROOT / 'results' / 'backtest'

G2_PARAMS = {
    'InpBouncePct': '0.30', 'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4', 'InpMaxCounterRiskATR': '0.5',
    'InpMaxEntriesPerOB': '2', 'InpEnableDeepestPullbackSL': 'true',
    'InpDeepestPullbackBuffer': '0.5',
    'InpBreakevenR': '0.25', 'InpBreakevenLockR': '0.08',
}

def get_months():
    months = []
    for year in [2024, 2025, 2026]:
        sm = 6 if year == 2024 else 1
        em = 5 if year == 2026 else 12
        for month in range(sm, em + 1):
            ld = monthrange(year, month)[1]
            months.append((f'{year}.{month:02d}.01', f'{year}.{month:02d}.{ld:02d}', f'{year}-{month:02d}', ld))
    return months

def replace_param(content, key, val):
    pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
    if pattern.search(content): return pattern.sub(f'{key}={val}', content)
    return content + f'\n{key}={val}\n'

def make_set():
    dst = MT5_PROFILES_DIR / 'v11xau-g2-24m.set'
    content = BASE_SET.read_text(encoding='utf-8')
    content = replace_param(content, 'InpVersion', 'V11XAU-G2')
    content = replace_param(content, 'InpMagicNumber', '204819')
    content = replace_param(content, 'InpEnableEntryDebug', 'true')
    for key, val in G2_PARAMS.items():
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

def run_bt(date_from, date_to, timeout=180):
    ini_file = MT5_TESTER_DIR / 'backtest.ini'
    today_str = datetime.now().strftime('%Y%m%d')
    ini_content = f"""[Common]
Login=
Server=
[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters=v11xau-g2-24m.set
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
Report=g2_24m_{today_str}
"""
    ini_file.write_text(ini_content)
    kill_mt5_tester()
    for old in MT5_DATA.glob('g2_24m*.htm'):
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
    html_files = sorted(MT5_DATA.glob('g2_24m*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
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
    balance = None; net_profit = None
    summary_nums = []
    for i in range(max(0, len(lines)-50), len(lines)):
        clean = re.sub(r'<[^>]+>', ' | ', lines[i]).strip()
        m = re.match(r'^\|\s*\|\s*(-?[\d\s]+[\d.]*\d)\s*\|\s*\|$', clean)
        if m:
            val_str = m.group(1).replace(' ', '').replace('\xa0', '')
            try: summary_nums.append(float(val_str))
            except: pass
    balance = summary_nums[-1] if len(summary_nums) >= 1 else None
    net_profit = summary_nums[-2] if len(summary_nums) >= 2 else None
    return (trades, wr, balance, net_profit)

def parse_qs3_result(filepath):
    text = filepath.read_text(encoding='utf-8')
    m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', text)
    return (int(m.group(1)), float(m.group(2)), float(m.group(3))) if m else None

# ── Main ──────────────────────────────────────────────────────
months = get_months()
print(f"G2 24个月回测 ({len(months)}个月)")

# 1. Read existing QS3 and D5B data
print("读取 QS3/D5B 现有数据...")
qs3_data = {}; d5b_data = {}
for date_from, date_to, label, days in months:
    # QS3
    fname = f'v11xau-qs3_{date_from.replace(".","")}_{date_to.replace(".","")}_20260603.txt'
    fpath = RESULTS_DIR / fname
    if fpath.exists():
        r = parse_qs3_result(fpath)
        if r: qs3_data[label] = r
    # D5B from earlier run_monthly_compare
    # We'll read from our stored data

# D5B monthly data (from earlier 24-month comparison)
D5B_MONTHLY = {
    '2024-06': (18, 55.6, 205.78), '2024-07': (99, 48.5, 196.58),
    '2024-08': (127, 60.6, 629.20), '2024-09': (130, 53.1, 226.42),
    '2024-10': (203, 63.5, 666.62), '2024-11': (188, 60.6, 652.27),
    '2024-12': (108, 61.1, 263.98), '2025-01': (203, 64.0, 483.81),
    '2025-02': (206, 55.3, 359.61), '2025-03': (198, 50.0, 469.46),
    '2025-04': (459, 65.6, 21029.81), '2025-05': (454, 66.5, 13854.70),
    '2025-06': (407, 65.4, 8164.48), '2025-07': (311, 62.7, 2977.30),
    '2025-08': (306, 55.9, 431.73), '2025-09': (355, 61.1, 9437.69),
    '2025-10': (395, 72.2, 51297.69), '2025-11': (341, 67.2, 15355.49),
    '2025-12': (474, 66.0, 14615.42), '2026-01': (611, 48.3, 372.23),
    '2026-02': (340, 51.2, 172.47), '2026-03': (388, 45.4, 13.07),
    '2026-04': (262, 47.3, 1.41), '2026-05': (317, 43.5, 0.72),
}

# 2. Run G2 for all months
print("运行 G2...")
make_set()
g2_data = {}
for date_from, date_to, label, days in months:
    print(f"  {label} ", end='', flush=True)
    r = run_bt(date_from, date_to)
    if r:
        t, wr, bal, net = r
        g2_data[label] = (t, wr, bal)
        ret = (bal - 200) / 200 * 100
        print(f"{t:>4}t {wr:>5.1f}% ${bal:>10,.2f} ({ret:>+6.1f}%)")
    else:
        print(f"FAILED")

# 3. Summary table
print(f"\n{'='*130}")
print(f"  G2 vs QS3 vs D5B — 24个月对比 (每月独立起始 $200, Model 4 Real Ticks)")
print(f"{'='*130}")

print(f"\n{'月份':<8} {'QS3交易':>6} {'QS3 WR':>7} {'QS3余额':>12} {'QS3收益':>8} | "
      f"{'D5B交易':>6} {'D5B WR':>7} {'D5B余额':>12} {'D5B收益':>8} | "
      f"{'G2交易':>6} {'G2 WR':>7} {'G2余额':>12} {'G2收益':>8} | "
      f"{'G2vsD5B':>8}")
print("-" * 130)

agg = {'QS3': {'t':0,'m':0,'p':0,'b':[]}, 'D5B': {'t':0,'m':0,'p':0,'b':[]}, 'G2': {'t':0,'m':0,'p':0,'b':[]}}

for date_from, date_to, label, days in months:
    qr = qs3_data.get(label)
    dr = D5B_MONTHLY.get(label)
    gr = g2_data.get(label)

    parts = [f"{label:<8}"]
    for sname, r in [('QS3', qr), ('D5B', dr), ('G2', gr)]:
        if r:
            t, wr, bal = r
            ret = (bal - 200) / 200 * 100
            parts.append(f"{t:>6} {wr:>6.1f}% ${bal:>11,.2f} {ret:>+7.1f}%")
            agg[sname]['t'] += t; agg[sname]['m'] += 1
            agg[sname]['b'].append(bal)
            if ret > 0: agg[sname]['p'] += 1
        else:
            parts.append(f"{'N/A':>34}")

    # G2 vs D5B delta
    if gr and dr:
        gbal = gr[2]; dbal = dr[2]
        delta = (gbal - dbal) / dbal * 100 if dbal > 1 else (gbal - dbal) / 1 * 100
        parts.append(f"{delta:>+7.1f}%")
    else:
        parts.append(f"{'--':>8}")

    print(" | ".join(parts))

# Aggregate
print(f"\n{'='*130}")
print(f"  24个月汇总")
print(f"{'='*130}")
print(f"{'指标':<20} {'QS3':>18} {'D5B':>18} {'G2':>18}")
print("-" * 60)
print(f"{'总交易数':<20} {agg['QS3']['t']:>18} {agg['D5B']['t']:>18} {agg['G2']['t']:>18}")
print(f"{'月均交易':<20} {agg['QS3']['t']/max(1,agg['QS3']['m']):>17.1f} {agg['D5B']['t']/max(1,agg['D5B']['m']):>17.1f} {agg['G2']['t']/max(1,agg['G2']['m']):>17.1f}")
print(f"{'盈利月份':<20} {agg['QS3']['p']:>16}/{agg['QS3']['m']} {agg['D5B']['p']:>16}/{agg['D5B']['m']} {agg['G2']['p']:>16}/{agg['G2']['m']}")
print(f"{'月均余额':<20} ${sum(agg['QS3']['b'])/max(1,len(agg['QS3']['b'])):>16,.0f} ${sum(agg['D5B']['b'])/max(1,len(agg['D5B']['b'])):>16,.0f} ${sum(agg['G2']['b'])/max(1,len(agg['G2']['b'])):>16,.0f}")

# Best/Worst
for sname in ['QS3','D5B','G2']:
    if agg[sname]['b']:
        print(f"{sname} 最佳/最差: ${max(agg[sname]['b']):,.0f} / ${min(agg[sname]['b']):,.2f}")

# 720d projections
print(f"\n{'='*60}")
print(f"  720d 连续回测 (需单独运行)")
print(f"{'='*60}")
print(f"  QS3: $336,082 (7,065t, 57.7% WR)")
print(f"  D5B: $265,045 (5,065t, 60.6% WR)")
print(f"  G2:  待运行")

# Cleanup
sf = MT5_PROFILES_DIR / 'v11xau-g2-24m.set'
if sf.exists(): sf.unlink()

print(f"\nG2 24个月完成!")
