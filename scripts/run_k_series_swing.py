#!/usr/bin/env python3
"""K系列：scalp→swing转型 — 宽止损+晚锁利+高DTP+长持仓 = 抓波段"""
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

# QS4 scalp baseline
QS4_SCALP = {
    'InpBouncePct': '0.30', 'InpBounceSweetMinPct': '0.35',
    'InpOutsideBounceSweetMult': '0.4', 'InpMaxCounterRiskATR': '0.5',
    'InpMaxEntriesPerOB': '2', 'InpEnableDeepestPullbackSL': 'true',
    'InpDeepestPullbackBuffer': '0.5',
    # scalp特征: 紧BE, 低DTP, 短时限
    'InpBreakevenR': '0.5', 'InpBreakevenLockR': '0.4',
    'InpDTPTriggerR': '0.0', 'InpAdaptiveDTP': 'true',
    'InpTimeExitBars': '20',
    'InpRiskPercent': '1.5',
}

K_TESTS = [
    # K1: 宽止损 — 关闭DP-SL, 用ATR宽止损给呼吸空间
    ('V11XAU-K1', 204780, 'K1:宽SL(ATR0.8)', {
        **QS4_SCALP,
        'InpEnableDeepestPullbackSL': 'false',
        'InpSLBufferATR': '0.8',
        'InpTimeExitBars': '120',            # 延长时限
    }),

    # K2: 晚锁利 — BE到1.5R才锁, DTP在3R启动
    ('V11XAU-K2', 204779, 'K2:晚锁(BE1.5+DTP3)', {
        **QS4_SCALP,
        'InpBreakevenR': '1.5',
        'InpBreakevenLockR': '0.5',
        'InpDTPTriggerR': '3.0',
        'InpAdaptiveDTP': 'false',
        'InpDTPRetrace': '0.3',
        'InpTimeExitBars': '999',
    }),

    # K3: 纯波段 — 宽SL+晚锁+高DTP+长时限
    ('V11XAU-K3', 204778, 'K3:纯波段(宽SL+晚锁+高DTP)', {
        **QS4_SCALP,
        'InpEnableDeepestPullbackSL': 'false',
        'InpSLBufferATR': '0.8',
        'InpBreakevenR': '1.5',
        'InpBreakevenLockR': '0.5',
        'InpDTPTriggerR': '3.0',
        'InpAdaptiveDTP': 'false',
        'InpDTPRetrace': '0.3',
        'InpTimeExitBars': '999',
    }),

    # K4: K3 + 保留DP-SL(结构止损但放宽)
    ('V11XAU-K4', 204777, 'K4:波段+宽DP-SL(1.0)', {
        **QS4_SCALP,
        'InpEnableDeepestPullbackSL': 'true',
        'InpDeepestPullbackBuffer': '1.0',   # 宽结构止损
        'InpBreakevenR': '1.5',
        'InpBreakevenLockR': '0.5',
        'InpDTPTriggerR': '3.0',
        'InpAdaptiveDTP': 'false',
        'InpDTPRetrace': '0.3',
        'InpTimeExitBars': '999',
    }),

    # K5: K4 + 减少入场(提高OB质量)
    ('V11XAU-K5', 204776, 'K5:波段+宽DP(1.0)+高OB', {
        **QS4_SCALP,
        'InpEnableDeepestPullbackSL': 'true',
        'InpDeepestPullbackBuffer': '1.0',
        'InpBreakevenR': '1.5',
        'InpBreakevenLockR': '0.5',
        'InpDTPTriggerR': '3.0',
        'InpAdaptiveDTP': 'false',
        'InpDTPRetrace': '0.3',
        'InpTimeExitBars': '999',
        'InpMinOBBodyPct': '60.0',
        'InpMinImpulseBodyPct': '60.0',
        'InpMinOBStrength': '0.6',
        'InpCooldownBars': '20',
    }),

    # K6: ZD2风格DTP — 极高DTP触发+早BE保护(ZD2混合)
    ('V11XAU-K6', 204775, 'K6:ZD2-DTP(8R)+早BE(0.25)', {
        **QS4_SCALP,
        'InpEnableDeepestPullbackSL': 'true',
        'InpDeepestPullbackBuffer': '0.5',
        'InpBreakevenR': '0.25',             # ZD2: 早保护
        'InpBreakevenLockR': '0.08',         # ZD2: 少锁
        'InpDTPTriggerR': '8.0',             # ZD2: 极高触发
        'InpAdaptiveDTP': 'false',
        'InpDTPRetrace': '0.2',
        'InpTimeExitBars': '999',            # ZD2: 不限时
    }),
]

def replace_param(content, key, val):
    pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
    if pattern.search(content): return pattern.sub(f'{key}={val}', content)
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

def kill_mt5_tester():
    try:
        subprocess.run(['powershell', '-Command',
            "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Path -like '*Program Files*' } | Stop-Process -Force"
        ], capture_output=True, timeout=10)
    except: pass
    time.sleep(3)

def run_bt(name, date_from, date_to, timeout=300):
    ini_file = MT5_TESTER_DIR / 'backtest.ini'
    today_str = datetime.now().strftime('%Y%m%d')
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
Report=kseries_{name}_{today_str}
"""
    ini_file.write_text(ini_content)
    kill_mt5_tester()
    for old in MT5_DATA.glob(f'kseries_{name}*.htm'):
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
    html_files = sorted(MT5_DATA.glob(f'kseries_{name}*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not html_files: return None
    raw = html_files[0].read_bytes()
    try: text = raw.decode('utf-16-le')
    except: text = raw.decode('utf-8', errors='ignore')
    lines = text.split('\n')
    trades = 0; wins = 0; losses = 0
    total_profit = 0; total_loss = 0
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
                if profit_val > 0.01: wins += 1; total_profit += profit_val
                elif profit_val < -0.01: losses += 1; total_loss += abs(profit_val)
            except: pass
    wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
    avg_win = total_profit/wins if wins > 0 else 0
    avg_loss = total_loss/losses if losses > 0 else 0
    pf = avg_win/avg_loss if avg_loss > 0 else 99
    balance = None
    for i in range(max(0, len(lines)-50), len(lines)):
        clean = re.sub(r'<[^>]+>', ' | ', lines[i]).strip()
        m = re.match(r'^\|\s*\|\s*(-?[\d\s]+[\d.]*\d)\s*\|\s*\|$', clean)
        if m:
            val_str = m.group(1).replace(' ', '').replace('\xa0', '')
            try: balance = float(val_str)
            except: pass
    return (trades, wr, balance, avg_win, avg_loss, pf) if balance is not None else None

MONTHS = [("2025.10.01", "2025.10.31", "2025-10"), ("2026.05.01", "2026.05.31", "2026-05")]

print(f"{'策略':<38} {'交易':>5} {'WR':>6} {'余额':>12} {'均赢':>8} {'均亏':>8} {'PF':>5} | "
      f"{'交易':>5} {'WR':>6} {'余额':>12} {'均赢':>8} {'均亏':>8} {'PF':>5}")
print(f"{'':<38} {'2025-10(好月)':>46} | {'2026-05(坏月)':>46}")
print("-" * 140)

QS4_REF_GOOD = (395, 72.2, 51297.69, 237.92, 151.91, 1.57)
QS4_REF_BAD  = (317, 43.5, 0.72, 1.89, 2.57, 0.74)

def fmt(r):
    if not r: return f"{'FAILED':>52}"
    t, wr, bal, aw, al, pf = r
    return f"{t:>5} {wr:>5.1f}% ${bal:>10,.0f} ${aw:>7.1f} ${al:>7.1f} {pf:>4.2f}"

print(f"{'QS4 scalp(基线)':<38} {fmt(QS4_REF_GOOD)} | {fmt(QS4_REF_BAD)}")

for ver, magic, desc, params in K_TESTS:
    name = f'v11xau-{ver.split("-")[-1].lower()}'
    print(f"\n{desc}")
    make_set(name, ver, magic, params)
    results = {}
    for date_from, date_to, label in MONTHS:
        print(f"  {label} ", end='', flush=True)
        r = run_bt(name, date_from, date_to)
        if r: results[label] = r
        t, wr, bal, aw, al, pf = r if r else (0,0,0,0,0,0)
        print(f"{t:>4}t {wr:>5.1f}% ${bal:>10,.2f} W${aw:>6.1f} L${al:>6.1f} PF={pf:.2f}")
    r10 = results.get('2025-10'); r05 = results.get('2026-05')
    print(f"  {'':<38} {fmt(r10)} | {fmt(r05)}")

for ver, _, _, _ in K_TESTS:
    sf = MT5_PROFILES_DIR / f'v11xau-{ver.split("-")[-1].lower()}.set'
    if sf.exists(): sf.unlink()
print(f"\nK系列完成!")
