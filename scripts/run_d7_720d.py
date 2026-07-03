#!/usr/bin/env python3
"""运行 D7D 和 D7A 的 720d 回测（短窗口最佳候选）"""
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

def replace_param(content, key, val):
    pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
    if pattern.search(content):
        return pattern.sub(f'{key}={val}', content)
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

def run_bt_720(name, symbol='XAUUSDm'):
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
FromDate=2024.06.08
ToDate=2026.06.01
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

    # 720d needs more time
    for i in range(720):  # up to 60 min
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
    time.sleep(3)

    html_files = sorted(MT5_DATA.glob(f'{name}*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not html_files:
        return None

    raw = html_files[0].read_bytes()
    try:
        text = raw.decode('utf-16-le')
    except:
        text = raw.decode('utf-8', errors='ignore')

    lines = text.split('\n')
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

    return (trades, wins, losses, wr, balance)

# ── D7D: H2A + DP-SL 0.7 (best short-window) ──────────────────
print("=" * 60)
print("  D7D: H2A + DP-SL 0.7 — 720d")
print("=" * 60)
make_set('v11xau-qs3-d7d', 204861, 'V11XAU-QS3-D7D', {
    'InpBouncePct': '0.30',
    'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4',
    'InpMaxCounterRiskATR': '0.5',
    'InpMaxEntriesPerOB': '2',
    'InpEnableDeepestPullbackSL': 'true',
    'InpDeepestPullbackBuffer': '0.7',
})
print("  运行中...", flush=True)
r = run_bt_720('v11xau-qs3-d7d')
if r:
    t, w, l, wr, bal = r
    print(f"  D7D 720d: {t}t {w}W/{l}L {wr:.1f}% ${bal:,.2f}")
else:
    print(f"  D7D 720d: FAILED")

# ── D7A: CounterRisk 1.0 (for comparison) ──────────────────────
print("\n" + "=" * 60)
print("  D7A: CounterRisk1.0 + DP-SL 0.5 — 720d")
print("=" * 60)
make_set('v11xau-qs3-d7a', 204864, 'V11XAU-QS3-D7A', {
    'InpBouncePct': '0.30',
    'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4',
    'InpMaxCounterRiskATR': '1.0',
    'InpMaxEntriesPerOB': '2',
    'InpEnableDeepestPullbackSL': 'true',
    'InpDeepestPullbackBuffer': '0.5',
})
print("  运行中...", flush=True)
r = run_bt_720('v11xau-qs3-d7a')
if r:
    t, w, l, wr, bal = r
    print(f"  D7A 720d: {t}t {w}W/{l}L {wr:.1f}% ${bal:,.2f}")
else:
    print(f"  D7A 720d: FAILED")

print("\nDone!")
