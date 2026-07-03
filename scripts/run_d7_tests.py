#!/usr/bin/env python3
"""D7: 放松OB质量过滤 + 保留最深回调止损 — 目标回收被过度过滤的盈利交易"""
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

# D5B baseline (best so far): H2A + touch=2 + DP-SL0.5
D5B_PARAMS = {
    'InpBouncePct': '0.30',
    'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4',
    'InpMaxCounterRiskATR': '0.5',
    'InpMaxEntriesPerOB': '2',
    'InpEnableDeepestPullbackSL': 'true',
    'InpDeepestPullbackBuffer': '0.5',
}

# D7 测试：逐步放松D5B的约束
D7_TESTS = [
    # D7A: 放松MaxCounterRiskATR 0.5→1.0（允许更多逆势入场）
    ('V11XAU-QS3-D7A', 204864, 'D7A:CounterRisk1.0', {
        **D5B_PARAMS,
        'InpMaxCounterRiskATR': '1.0',
    }),
    # D7B: 放松MaxEntriesPerOB 2→3（每个OB多一次入场机会）
    ('V11XAU-QS3-D7B', 204863, 'D7B:MaxEntry3', {
        **D5B_PARAMS,
        'InpMaxEntriesPerOB': '3',
    }),
    # D7C: 同时放松两个约束
    ('V11XAU-QS3-D7C', 204862, 'D7C:Counter1.0+Entry3', {
        **D5B_PARAMS,
        'InpMaxCounterRiskATR': '1.0',
        'InpMaxEntriesPerOB': '3',
    }),
    # D7D: DP-SL buffer微调 0.5→0.7（更宽的结构止损）
    ('V11XAU-QS3-D7D', 204861, 'D7D:H2A+DP0.7', {
        **D5B_PARAMS,
        'InpDeepestPullbackBuffer': '0.7',
    }),
    # D7E: DP-SL buffer微调 0.5→0.3（更紧的结构止损）
    ('V11XAU-QS3-D7E', 204860, 'D7E:H2A+DP0.3', {
        **D5B_PARAMS,
        'InpDeepestPullbackBuffer': '0.3',
    }),
]

def replace_param(content, key, val):
    pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
    if pattern.search(content):
        return pattern.sub(f'{key}={val}', content)
    else:
        return content + f'\n{key}={val}\n'

def make_set(name, magic, version, overrides):
    dst = MT5_PROFILES_DIR / f'{name}.set'
    content = BASE_SET.read_text(encoding='utf-8')
    content = replace_param(content, 'InpVersion', version)
    content = replace_param(content, 'InpMagicNumber', str(magic))
    content = replace_param(content, 'InpEnableEntryDebug', 'true')
    for key, val in overrides.items():
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

def run_bt(name, symbol, date_from, date_to, timeout=600):
    ini_file = MT5_TESTER_DIR / 'backtest.ini'
    today_str = datetime.now().strftime('%Y%m%d')
    report_name = f'{name}_{symbol}_{today_str}'

    ini_content = f"""[Common]
Login=
Server=

[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters={name}.set
Symbol={symbol}
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
    subprocess.Popen([MT5_TERMINAL, f'/config:{ini_file}'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for i in range(timeout // 5):
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

    # Parse HTML - look for final balance in summary
    html_files = sorted(MT5_DATA.glob(f'{name}*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not html_files:
        return None

    raw = html_files[0].read_bytes()
    try:
        text = raw.decode('utf-16-le')
    except:
        text = raw.decode('utf-8', errors='ignore')

    # Date
    date_m = re.search(r'M1\s*\((\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})\)', text)
    dt_from = date_m.group(1) if date_m else '?'
    dt_to = date_m.group(2) if date_m else '?'

    # Count trades
    trades = 0
    wins = 0
    losses = 0
    lines = text.split('\n')
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

    # Balance from summary (last 50 lines)
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

    return (trades, wins, losses, wr, balance, dt_from, dt_to)

# ── Main ──────────────────────────────────────────────────────
WINDOWS = [
    ("2026.06.02", "2026.06.03", "0602", 1),
    ("2025.05.28", "2025.05.30", "0529", 2),
]
WINDOW_720 = ("2024.06.08", "2026.06.01", "720d", 723)

all_results = {}

for ver, magic, desc, params in D7_TESTS:
    name = f'v11xau-qs3-{ver.split("-")[-1].lower()}'
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"{'='*60}")

    make_set(name, magic, ver, params)
    all_results[name] = {'desc': desc, 'windows': {}}

    for date_from, date_to, wlabel, days in WINDOWS:
        print(f"  [{wlabel}] ", end='', flush=True)
        r = run_bt(name, 'XAUUSDm', date_from, date_to, timeout=300)
        if r and r[4] is not None:
            t, w, l, wr, bal, _, _ = r
            all_results[name]['windows'][wlabel] = (t, w, l, wr, bal, days)
            print(f"{t:>4}t {w}W/{l}L {wr:.1f}% ${bal:,.2f}")
        else:
            print(f"FAILED")

# ── 720d for best candidates ──────────────────────────────────
print(f"\n{'='*60}")
print(f"  720d 测试（短窗口综合最佳）")
print(f"{'='*60}")

# Score: higher balance on both windows = better
scored = []
for name, data in all_results.items():
    score = 0
    for wlabel in ['0602', '0529']:
        if wlabel in data['windows']:
            score += data['windows'][wlabel][4]  # balance
    scored.append((score, name, data))

scored.sort(reverse=True)

for i, (score, name, data) in enumerate(scored[:4]):  # top 4
    ver = data['desc'].split(':')[0]
    full_ver = f'V11XAU-QS3-{ver}'
    magic = 204860 + (4 - i)
    params = dict(D7_TESTS[i][4])

    print(f"\n  [{ver}] 720d {WINDOW_720[0]}~{WINDOW_720[1]} ", end='', flush=True)
    r = run_bt(name, 'XAUUSDm', WINDOW_720[0], WINDOW_720[1], timeout=3600)
    if r and r[4] is not None:
        t, w, l, wr, bal, _, _ = r
        all_results[name]['windows']['720d'] = (t, w, l, wr, bal, WINDOW_720[3])
        print(f"\n  {t:>5}t {w}W/{l}L {wr:.1f}% ${bal:,.2f}")

# ── Summary ──────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  D7 汇总对比")
print(f"{'='*70}")
print(f"{'策略':<30} {'0602':>18} {'0529':>18} {'720d':>18}")
print(f"{'-'*30} {'-'*18} {'-'*18} {'-'*18}")

def fmt_row(t, w, l, wr, bal, days):
    return f"{t:>3}t {w}W/{l}L {wr:>4.1f}% ${bal:>9,.0f}" if t > 0 else "FAILED"

# D5B reference
print(f"{'D5B H2A+touch2+DP0.5 [ref]':<30} {'12t 8W/4L 66.7% $      206':>18} {'22t 20W/2L 90.9% $      280':>18} {'5065t 3068W/1997L 60.6% $  265,045':>18}")

for name, data in all_results.items():
    r0602 = data['windows'].get('0602')
    r0529 = data['windows'].get('0529')
    r720d = data['windows'].get('720d')
    s0602 = fmt_row(*r0602) if r0602 else '-'
    s0529 = fmt_row(*r0529) if r0529 else '-'
    s720d = fmt_row(*r720d) if r720d else '-'
    print(f"{data['desc']:<30} {s0602:>18} {s0529:>18} {s720d:>18}")

# Cleanup
for ver, magic, desc, params in D7_TESTS:
    name = f'v11xau-qs3-{ver.split("-")[-1].lower()}'
    sf = MT5_PROFILES_DIR / f'{name}.set'
    if sf.exists():
        sf.unlink()

print(f"\nD7 完成")
