#!/usr/bin/env python3
"""ZD2 24个月回测 + 四策略对比CSV"""
import os, sys, re, time, subprocess, csv
from pathlib import Path
from datetime import datetime
from calendar import monthrange

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
MT5_TESTER_DIR = MT5_DATA / 'Tester'
MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
RESULTS_DIR = ROOT / 'results' / 'backtest'

def get_months():
    months = []
    for year in [2024, 2025, 2026]:
        sm = 6 if year == 2024 else 1
        em = 5 if year == 2026 else 12
        for month in range(sm, em + 1):
            ld = monthrange(year, month)[1]
            months.append((f'{year}.{month:02d}.01', f'{year}.{month:02d}.{ld:02d}', f'{year}-{month:02d}', ld))
    return months

def kill_mt5_tester():
    try:
        subprocess.run(['powershell', '-Command',
            "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"
        ], capture_output=True, timeout=10)
    except: pass
    time.sleep(3)

def run_bt(set_filename, date_from, date_to, timeout=180):
    ini_file = MT5_TESTER_DIR / 'backtest.ini'
    today_str = datetime.now().strftime('%Y%m%d')
    report_name = f'zd2_24m_{today_str}'
    ini_content = f"""[Common]
Login=
Server=
[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters={set_filename}
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
    for old in MT5_DATA.glob('zd2_24m*.htm'):
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
    html_files = sorted(MT5_DATA.glob('zd2_24m*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
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

# ── Known data from previous runs ──────────────────────────────
QS3_DATA = {
    '2024-06': (29, 48.3, 204.70), '2024-07': (165, 52.1, 228.87),
    '2024-08': (215, 60.0, 277.87), '2024-09': (139, 54.7, 254.86),
    '2024-10': (222, 55.9, 285.43), '2024-11': (242, 57.0, 441.42),
    '2024-12': (142, 58.5, 256.83), '2025-01': (198, 54.5, 287.67),
    '2025-02': (254, 58.3, 477.17), '2025-03': (252, 52.0, 291.83),
    '2025-04': (782, 62.7, 7932.51), '2025-05': (588, 65.8, 4699.67),
    '2025-06': (493, 64.1, 886.03), '2025-07': (417, 59.7, 459.22),
    '2025-08': (357, 53.5, 342.25), '2025-09': (500, 62.0, 1463.87),
    '2025-10': (608, 63.3, 33215.53), '2025-11': (565, 61.9, 4250.57),
    '2025-12': (689, 60.4, 1501.01), '2026-01': (666, 45.6, 182.02),
    '2026-02': (501, 45.7, 30.78), '2026-03': (405, 47.7, 21.77),
    '2026-04': (398, 44.2, 55.15), '2026-05': (497, 44.3, 1.30),
}
D5B_DATA = {
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
G2_DATA = {
    '2024-06': (18, 61.1, 207.84), '2024-07': (99, 53.5, 192.61),
    '2024-08': (127, 65.4, 623.67), '2024-09': (131, 57.3, 232.82),
    '2024-10': (203, 70.0, 780.95), '2024-11': (188, 63.3, 558.13),
    '2024-12': (108, 66.7, 254.10), '2025-01': (186, 54.3, 154.82),
    '2025-02': (202, 62.9, 743.00), '2025-03': (198, 53.5, 449.14),
    '2025-04': (459, 69.3, 21263.90), '2025-05': (454, 70.7, 12905.39),
    '2025-06': (407, 69.0, 7102.69), '2025-07': (311, 66.6, 2199.40),
    '2025-08': (306, 59.2, 398.39), '2025-09': (355, 65.4, 8846.74),
    '2025-10': (395, 74.9, 47985.08), '2025-11': (341, 70.1, 13138.05),
    '2025-12': (474, 68.1, 12354.97), '2026-01': (611, 52.1, 375.88),
    '2026-02': (340, 49.7, 172.88), '2026-03': (386, 49.5, 116.96),
    '2026-04': (313, 46.8, 1.79), '2026-05': (317, 45.9, 1.39),
}

# ── Run ZD2 for all months ─────────────────────────────────────
months = get_months()
print(f"ZD2 24个月回测 ({len(months)}个月)")

# Copy ZD2 .set to profiles
import shutil
zd2_src = ROOT / 'mql5' / 'Presets' / 'V11XAU-ZD2.set'
shutil.copy(zd2_src, MT5_PROFILES_DIR / 'V11XAU-ZD2-24m.set')

zd2_data = {}
for date_from, date_to, label, days in months:
    print(f"  {label} ", end='', flush=True)
    r = run_bt('V11XAU-ZD2-24m.set', date_from, date_to)
    if r:
        t, wr, bal = r
        zd2_data[label] = (t, wr, bal)
        ret = (bal - 200) / 200 * 100
        print(f"{t:>4}t {wr:>5.1f}% ${bal:>10,.2f} ({ret:>+6.1f}%)")
    else:
        print(f"FAILED")

# ── Print summary table ────────────────────────────────────────
STRATEGIES = [
    ('QS3', QS3_DATA),
    ('D5B', D5B_DATA),
    ('G2', G2_DATA),
    ('ZD2', zd2_data),
]

print(f"\n{'='*150}")
print(f"  四策略 24 个月对比: QS3 vs D5B vs G2 vs ZD2")
print(f"{'='*150}")

header = f"{'月份':<8}"
for sname, _ in STRATEGIES:
    header += f" | {sname}交易 {sname}WR {sname}余额 {sname}收益"
print(header)
print("-" * 150)

agg = {sname: {'t':0, 'm':0, 'p':0, 'b':[]} for sname, _ in STRATEGIES}

for date_from, date_to, label, days in months:
    parts = [f"{label:<8}"]
    for sname, sdata in STRATEGIES:
        r = sdata.get(label)
        if r:
            t, wr, bal = r
            ret = (bal - 200) / 200 * 100
            parts.append(f" {t:>6} {wr:>5.1f}% ${bal:>10,.2f} {ret:>+7.1f}%")
            agg[sname]['t'] += t; agg[sname]['m'] += 1
            agg[sname]['b'].append(bal)
            if ret > 0: agg[sname]['p'] += 1
        else:
            parts.append(f" {'N/A':>32}")
    print(" |".join(parts))

# Aggregate
print(f"\n{'='*80}")
print(f"  汇总")
print(f"{'='*80}")
print(f"{'指标':<20}", end='')
for sname, _ in STRATEGIES:
    print(f" {sname:>15}", end='')
print(f"\n{'-'*80}")
print(f"{'总交易数':<20}", end='')
for sname, _ in STRATEGIES:
    print(f" {agg[sname]['t']:>15}", end='')
print(f"\n{'月均交易':<20}", end='')
for sname, _ in STRATEGIES:
    print(f" {agg[sname]['t']/max(1,agg[sname]['m']):>14.1f}", end='')
print(f"\n{'盈利月份':<20}", end='')
for sname, _ in STRATEGIES:
    print(f" {agg[sname]['p']:>13}/{agg[sname]['m']}", end='')
print(f"\n{'月均余额':<20}", end='')
for sname, _ in STRATEGIES:
    avg = sum(agg[sname]['b'])/max(1,len(agg[sname]['b']))
    print(f" ${avg:>14,.0f}", end='')
print(f"\n{'最佳月':<20}", end='')
for sname, _ in STRATEGIES:
    print(f" ${max(agg[sname]['b']):>14,.0f}", end='')
print(f"\n{'最差月':<20}", end='')
for sname, _ in STRATEGIES:
    print(f" ${min(agg[sname]['b']):>14,.2f}", end='')
print()

# ── Save CSV ───────────────────────────────────────────────────
csv_path = ROOT / 'results' / 'backtest' / 'four_strategies_24month_comparison.csv'
with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['月份',
        'QS3交易','QS3胜率%','QS3余额','QS3收益%',
        'D5B交易','D5B胜率%','D5B余额','D5B收益%',
        'G2交易','G2胜率%','G2余额','G2收益%',
        'ZD2交易','ZD2胜率%','ZD2余额','ZD2收益%',
    ])
    for date_from, date_to, label, days in months:
        row = [label]
        for sname, sdata in STRATEGIES:
            r = sdata.get(label)
            if r:
                t, wr, bal = r
                ret = (bal - 200) / 200 * 100
                row.extend([t, f"{wr:.1f}", f"{bal:.2f}", f"{ret:.1f}"])
            else:
                row.extend(['','','',''])
        writer.writerow(row)
    # Summary row
    row = ['汇总']
    for sname, _ in STRATEGIES:
        a = agg[sname]
        row.extend([a['t'], '', f"{sum(a['b'])/max(1,len(a['b'])):.2f}", ''])
    writer.writerow(row)

print(f"\nCSV saved: {csv_path}")

# Cleanup
sf = MT5_PROFILES_DIR / 'V11XAU-ZD2-24m.set'
if sf.exists(): sf.unlink()

print("ZD2 24个月完成!")
