#!/usr/bin/env python3
"""24个月对比回测：QS3基线 vs D5B vs D5C vs D7D"""
import os, sys, re, time, subprocess
from pathlib import Path
from datetime import datetime, timedelta
from calendar import monthrange
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
MT5_TESTER_DIR = MT5_DATA / 'Tester'
MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
BASE_SET = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'
RESULTS_DIR = ROOT / 'results' / 'backtest'

STRATEGIES = {
    'QS3': {
        'version': 'V11XAU-QS3',
        'magic': 204897,
        'params': {},
        'existing_results': True,  # Already have monthly data
    },
    'D5B': {
        'version': 'V11XAU-QS3-D5B',
        'magic': 204866,
        'params': {
            'InpBouncePct': '0.30',
            'InpBounceSweetMinPct': '0.35',
            'InpOutsideBounceSweetMult': '0.4',
            'InpMaxCounterRiskATR': '0.5',
            'InpMaxEntriesPerOB': '2',
            'InpEnableDeepestPullbackSL': 'true',
            'InpDeepestPullbackBuffer': '0.5',
        },
        'existing_results': False,
    },
    'D5C': {
        'version': 'V11XAU-QS3-D5C',
        'magic': 204865,
        'params': {
            'InpBouncePct': '0.40',
            'InpBounceSweetMinPct': '0.40',
            'InpOutsideBounceSweetMult': '0.3',
            'InpEnableDeepestPullbackSL': 'true',
            'InpDeepestPullbackBuffer': '0.5',
        },
        'existing_results': False,
    },
    'D7D': {
        'version': 'V11XAU-QS3-D7D',
        'magic': 204861,
        'params': {
            'InpBouncePct': '0.30',
            'InpBounceSweetMinPct': '0.35',
            'InpOutsideBounceSweetMult': '0.4',
            'InpMaxCounterRiskATR': '0.5',
            'InpMaxEntriesPerOB': '2',
            'InpEnableDeepestPullbackSL': 'true',
            'InpDeepestPullbackBuffer': '0.7',
        },
        'existing_results': False,
    },
}

def get_months():
    """Generate 24 months from 2024-06 to 2026-05"""
    months = []
    for year in [2024, 2025, 2026]:
        start_month = 6 if year == 2024 else 1
        end_month = 6 if year == 2026 else 12  # stop at May for 2026
        if year == 2026:
            end_month = 5
        for month in range(start_month, end_month + 1):
            last_day = monthrange(year, month)[1]
            months.append((
                f'{year}.{month:02d}.01',
                f'{year}.{month:02d}.{last_day:02d}',
                f'{year}-{month:02d}',
                last_day,
            ))
    return months

def parse_qs3_result(filepath):
    """Parse existing QS3 monthly result file"""
    text = filepath.read_text(encoding='utf-8')
    m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', text)
    if m:
        return (int(m.group(1)), float(m.group(2)), float(m.group(3)))
    return None

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
        subprocess.run([
            'powershell', '-Command',
            "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"
        ], capture_output=True, timeout=10)
    except:
        pass
    time.sleep(3)

def run_monthly_bt(name, date_from, date_to):
    """Run single month backtest, return (trades, wr, balance) or None"""
    ini_file = MT5_TESTER_DIR / 'backtest.ini'
    today_str = datetime.now().strftime('%Y%m%d')
    report_name = f'{name}_monthly_{today_str}'

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

    # Clean old HTML for this strategy
    for old in MT5_DATA.glob(f'{name}*.htm'):
        try:
            old.unlink()
        except:
            pass

    subprocess.Popen([MT5_TERMINAL, f'/config:{ini_file}'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait up to 120s for monthly test
    for i in range(24):
        time.sleep(5)
        try:
            result = subprocess.run([
                'powershell', '-Command',
                "(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
                "Where-Object { $_.Path -like '*Program Files*' }).Count"
            ], capture_output=True, text=True, timeout=5)
            if result.stdout.strip() == '0':
                break
        except:
            pass
    time.sleep(2)

    # Parse HTML
    html_files = sorted(MT5_DATA.glob(f'{name}*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not html_files:
        return None

    raw = html_files[0].read_bytes()
    try:
        text = raw.decode('utf-16-le')
    except:
        text = raw.decode('utf-8', errors='ignore')

    lines = text.split('\n')

    # Count trades (out deals)
    trades = 0
    wins = 0
    losses = 0
    for line in lines:
        if 'XAUUSDm' not in line or 'out' not in line:
            continue
        if not re.search(r'<\s*td[^>]*>\s*out\s*<\s*/td\s*>', line, re.IGNORECASE):
            continue
        trades += 1
        clean = re.sub(r'<[^>]+>', ' | ', line).strip()
        parts = [p.strip() for p in clean.split('|')]
        non_empty = [p for p in parts if p]
        try:
            sym_idx = non_empty.index('XAUUSDm')
        except ValueError:
            continue
        if sym_idx + 2 >= len(non_empty) or non_empty[sym_idx + 2] != 'out':
            continue
        if len(non_empty) >= 3:
            try:
                profit_val = float(non_empty[-3].replace(' ', ''))
                if profit_val > 0.01:
                    wins += 1
                elif profit_val < -0.01:
                    losses += 1
            except:
                pass

    wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0

    # Balance from summary
    balance = None
    for i in range(max(0, len(lines)-50), len(lines)):
        clean = re.sub(r'<[^>]+>', ' | ', lines[i]).strip()
        m = re.match(r'^\|\s*\|\s*(-?[\d\s]+[\d.]*\d)\s*\|\s*\|$', clean)
        if m:
            val_str = m.group(1).replace(' ', '').replace('\xa0', '')
            try:
                balance = float(val_str)
            except:
                pass

    # Clean up HTML after parsing
    for h in html_files:
        try:
            h.unlink()
        except:
            pass

    return (trades, wr, balance) if balance is not None else None


# ── Main ──────────────────────────────────────────────────────
months = get_months()
print(f"24个月对比回测：QS3 vs D5B vs D5C vs D7D")
print(f"月份数: {len(months)}")
print()

# Collect results: {strategy: {month_label: (trades, wr, balance)}}
all_results = defaultdict(dict)

# 1. Parse existing QS3 results
print("读取 QS3 现有月度数据...")
for date_from, date_to, label, days in months:
    fname = f'v11xau-qs3_{date_from.replace(".","")}_{date_to.replace(".","")}_20260603.txt'
    fpath = RESULTS_DIR / fname
    if fpath.exists():
        r = parse_qs3_result(fpath)
        if r:
            all_results['QS3'][label] = r
    else:
        print(f"  QS3 {label}: 缺失, 需要回测")

# Check if any QS3 months are missing
missing_qs3 = [m for m in months if m[2] not in all_results['QS3']]
if missing_qs3:
    print(f"  QS3 缺失 {len(missing_qs3)} 个月, 需要补充回测")

print(f"  QS3: {len(all_results['QS3'])}/{len(months)} 个月已就绪\n")

# 2. Create .set files for new strategies
for sname, sinfo in STRATEGIES.items():
    if sinfo['existing_results']:
        continue
    name = f'v11xau-qs3-{sname.lower()}'
    make_set(name, sinfo['version'], sinfo['magic'], sinfo['params'])
    print(f"  {sname}: .set 已创建 -> {name}")

# 3. Run monthly backtests for D5B, D5C, D7D
for sname, sinfo in STRATEGIES.items():
    if sinfo['existing_results']:
        continue
    name = f'v11xau-qs3-{sname.lower()}'
    print(f"\n{'='*50}")
    print(f"  {sname} ({sinfo['version']})")
    print(f"{'='*50}")

    for date_from, date_to, label, days in months:
        print(f"  {label} ", end='', flush=True)
        r = run_monthly_bt(name, date_from, date_to)
        if r:
            t, wr, bal = r
            all_results[sname][label] = (t, wr, bal)
            ret = (bal - 200) / 200 * 100
            print(f"{t:>4}t {wr:>5.1f}% ${bal:>8.2f} ({ret:>+6.1f}%)")
        else:
            print(f"FAILED")

# 4. Print summary table
print(f"\n{'='*120}")
print(f"  24个月对比汇总：QS3 vs D5B vs D5C vs D7D (每月起始资金 $200)")
print(f"{'='*120}")
print(f"{'月份':<8} {'QS3 交易':>6} {'QS3 WR':>7} {'QS3 余额':>10} {'QS3 收益':>7} | "
      f"{'D5B 交易':>6} {'D5B WR':>7} {'D5B 余额':>10} {'D5B 收益':>7} | "
      f"{'D5C 交易':>6} {'D5C WR':>7} {'D5C 余额':>10} {'D5C 收益':>7} | "
      f"{'D7D 交易':>6} {'D7D WR':>7} {'D7D 余额':>10} {'D7D 收益':>7}")
print("-" * 120)

# Also compute aggregate stats
agg = {s: {'trades': 0, 'wins': 0, 'total_ret': 0.0, 'months_profitable': 0, 'months': 0, 'balances': []}
       for s in STRATEGIES}

for date_from, date_to, label, days in months:
    row_data = {}
    for sname in ['QS3', 'D5B', 'D5C', 'D7D']:
        r = all_results[sname].get(label)
        if r:
            t, wr, bal = r
            ret = (bal - 200) / 200 * 100
            row_data[sname] = (t, wr, bal, ret)
            agg[sname]['trades'] += t
            agg[sname]['months'] += 1
            agg[sname]['total_ret'] += ret
            agg[sname]['balances'].append(bal)
            if ret > 0:
                agg[sname]['months_profitable'] += 1
        else:
            row_data[sname] = None

    # Print row
    parts = [f"{label:<8}"]
    for sname in ['QS3', 'D5B', 'D5C', 'D7D']:
        d = row_data[sname]
        if d:
            parts.append(f"{d[0]:>6} {d[1]:>6.1f}% ${d[2]:>9.2f} {d[3]:>+6.1f}%")
        else:
            parts.append(f"{'N/A':>33}")
    print(" | ".join(parts))

# 5. Aggregate summary
print(f"\n{'='*120}")
print(f"  24个月汇总统计")
print(f"{'='*120}")
print(f"{'指标':<20} {'QS3':>15} {'D5B':>15} {'D5C':>15} {'D7D':>15}")
print("-" * 85)
print(f"{'总交易数':<20} {agg['QS3']['trades']:>15} {agg['D5B']['trades']:>15} {agg['D5C']['trades']:>15} {agg['D7D']['trades']:>15}")
print(f"{'月均交易':<20} {agg['QS3']['trades']/max(1,agg['QS3']['months']):>14.1f} {agg['D5B']['trades']/max(1,agg['D5B']['months']):>14.1f} {agg['D5C']['trades']/max(1,agg['D5C']['months']):>14.1f} {agg['D7D']['trades']/max(1,agg['D7D']['months']):>14.1f}")
print(f"{'盈利月份':<20} {agg['QS3']['months_profitable']:>13}/{agg['QS3']['months']} {agg['D5B']['months_profitable']:>13}/{agg['D5B']['months']} {agg['D5C']['months_profitable']:>13}/{agg['D5C']['months']} {agg['D7D']['months_profitable']:>13}/{agg['D7D']['months']}")
print(f"{'月均收益%':<20} {agg['QS3']['total_ret']/max(1,agg['QS3']['months']):>+14.1f}% {agg['D5B']['total_ret']/max(1,agg['D5B']['months']):>+14.1f}% {agg['D5C']['total_ret']/max(1,agg['D5C']['months']):>+14.1f}% {agg['D7D']['total_ret']/max(1,agg['D7D']['months']):>+14.1f}%")

# Best/Worst month
for sname in ['QS3', 'D5B', 'D5C', 'D7D']:
    if agg[sname]['balances']:
        best = max(agg[sname]['balances'])
        worst = min(agg[sname]['balances'])
        print(f"{sname} 最佳/最差月余额: ${best:.2f} / ${worst:.2f}")

# 6. Cleanup .set files
for sname, sinfo in STRATEGIES.items():
    if sinfo['existing_results']:
        continue
    name = f'v11xau-qs3-{sname.lower()}'
    sf = MT5_PROFILES_DIR / f'{name}.set'
    if sf.exists():
        sf.unlink()

print(f"\n月度对比完成!")
