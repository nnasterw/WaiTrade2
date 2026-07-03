#!/usr/bin/env python3
"""补跑 QS3 2025-06 和 2025-07"""
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
ExpertParameters=V11XAU-QS3.set
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
Report=qs3_missing_{today_str}
"""
    ini_file.write_text(ini_content)
    kill_mt5_tester()
    for old in MT5_DATA.glob('qs3_missing*.htm'):
        try: old.unlink()
        except: pass
    # Need QS3 .set in profiles dir
    import shutil
    shutil.copy(BASE_SET, MT5_PROFILES_DIR / 'V11XAU-QS3.set')
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
    html_files = sorted(MT5_DATA.glob('qs3_missing*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
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

months = [("2025.06.01", "2025.06.30", "2025-06"), ("2025.07.01", "2025.07.31", "2025-07")]
for date_from, date_to, label in months:
    print(f"QS3 {label} ", end='', flush=True)
    r = run_bt(date_from, date_to)
    if r:
        t, wr, bal = r
        print(f"{t:>4}t {wr:>5.1f}% ${bal:>10,.2f}")
    else:
        print(f"FAILED")
print("done")
