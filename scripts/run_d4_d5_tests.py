#!/usr/bin/env python3
"""D4/D5 回测：最深回调止损(DeepestPullbackSL) + OB质量组合
直接操作 .set 文件和 backtest.ini，完全绕过 YAML 和 yaml_to_set.py
"""
import os, sys, re, time, shutil, subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

# ── MT5 路径 ──────────────────────────────────────────────────
MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.environ.get(
    'MT5_DATA',
    os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
))
MT5_TESTER_DIR = MT5_DATA / 'Tester'
MT5_PROFILES_DIR = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
BASE_SET = ROOT / 'mql5' / 'Presets' / 'V11XAU-QS3.set'

# ── 测试参数 ──────────────────────────────────────────────────
# QS3 基线参数（从 V11XAU-QS3.set 提取的关键值）
QS3_BASELINE = {
    'InpBouncePct': '0.22',
    'InpBounceSweetMinPct': '0.30',
    'InpBounceSweetMaxPct': '0.34',
    'InpOutsideBounceSweetMult': '0.4',
    'InpMaxCounterRiskATR': '1.5',
    'InpMaxEntriesPerOB': '5',
    'InpMaxOBAgeBarsTF': '0',
    'InpOBReentryCooldownMin': '3',
    'InpSLBufferATR': '0.3',
    'InpEnableDeepestPullbackSL': 'false',
    'InpDeepestPullbackBuffer': '0.3',
}

def make_set(name, magic, version, desc, overrides):
    """从 QS3 基线创建 .set 文件，覆盖指定参数"""
    dst = MT5_PROFILES_DIR / f'{name}.set'
    content = BASE_SET.read_text(encoding='utf-8')

    # 强制覆盖版本和魔术号
    content = replace_param(content, 'InpVersion', version)
    content = replace_param(content, 'InpMagicNumber', str(magic))
    content = replace_param(content, 'InpEnableEntryDebug', 'true')

    # 覆盖测试参数
    for key, val in overrides.items():
        content = replace_param(content, key, val)

    dst.write_text(content)
    return dst

def replace_param(content, key, val):
    """替换 .set 文件中的参数值"""
    pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
    if pattern.search(content):
        return pattern.sub(f'{key}={val}', content)
    else:
        return content + f'\n{key}={val}\n'

def kill_mt5_tester():
    """仅杀掉 Program Files 下的 terminal64（不影响 portable live 终端）"""
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
    """运行单次 MT5 回测，返回 (trades, wr_pct, balance) 或 None"""
    ini_file = MT5_TESTER_DIR / 'backtest.ini'
    today_str = datetime.now().strftime('%Y%m%d')
    report_name = f'{name}_{symbol}_{today_str}'

    # 写 INI
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

    # 杀掉旧 MT5 回测进程
    kill_mt5_tester()

    # 清理旧 HTML 报告
    for old in MT5_TESTER_DIR.glob('*.htm'):
        try:
            old.unlink()
        except:
            pass

    # 启动回测
    subprocess.Popen([MT5_TERMINAL, f'/config:{ini_file}'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 等待完成
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

    # 解析 HTML 报告
    html_files = sorted(MT5_TESTER_DIR.glob('*.htm'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not html_files:
        return None

    html = html_files[0].read_text(encoding='utf-8', errors='ignore')
    m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', html)
    if m:
        return (int(m.group(1)), float(m.group(2)), float(m.group(3)))
    return None

# ═══════════════════════════════════════════════════════════════
#  D4: 最深回调止损梯度 (QS3 基线 + DP-SL)
# ═══════════════════════════════════════════════════════════════
D4_TESTS = [
    ('V11XAU-QS3-D4A', 204870, 'D4A:DP-SL0.3', {
        'InpEnableDeepestPullbackSL': 'true',
        'InpDeepestPullbackBuffer': '0.3',
    }),
    ('V11XAU-QS3-D4B', 204869, 'D4B:DP-SL0.5', {
        'InpEnableDeepestPullbackSL': 'true',
        'InpDeepestPullbackBuffer': '0.5',
    }),
    ('V11XAU-QS3-D4C', 204868, 'D4C:DP-SL0.7', {
        'InpEnableDeepestPullbackSL': 'true',
        'InpDeepestPullbackBuffer': '0.7',
    }),
]

# ═══════════════════════════════════════════════════════════════
#  D5: OB质量 + 最深回调止损 组合
# ═══════════════════════════════════════════════════════════════
D5_TESTS = [
    ('V11XAU-QS3-D5A', 204867, 'D5A:bounce0.30+DP0.5', {
        'InpBouncePct': '0.30',
        'InpBounceSweetMinPct': '0.35',
        'InpOutsideBounceSweetMult': '0.4',
        'InpEnableDeepestPullbackSL': 'true',
        'InpDeepestPullbackBuffer': '0.5',
    }),
    ('V11XAU-QS3-D5B', 204866, 'D5B:H2A+touch2+DP0.5', {
        'InpBouncePct': '0.30',
        'InpBounceSweetMinPct': '0.35',
        'InpOutsideBounceSweetMult': '0.4',
        'InpMaxCounterRiskATR': '0.5',
        'InpMaxEntriesPerOB': '2',
        'InpEnableDeepestPullbackSL': 'true',
        'InpDeepestPullbackBuffer': '0.5',
    }),
    ('V11XAU-QS3-D5C', 204865, 'D5C:bounce0.40+DP0.5', {
        'InpBouncePct': '0.40',
        'InpBounceSweetMinPct': '0.40',
        'InpOutsideBounceSweetMult': '0.3',
        'InpEnableDeepestPullbackSL': 'true',
        'InpDeepestPullbackBuffer': '0.5',
    }),
]

# ── 测试窗口 ──────────────────────────────────────────────────
WINDOWS = [
    ("2026.06.02", "2026.06.03", "0602", 1),   # 坏日子
    ("2025.05.28", "2025.05.30", "0529", 2),   # 震荡日
]
WINDOW_720 = ("2024.06.08", "2026.06.01", "720d", 723)

# ═══════════════════════════════════════════════════════════════
def main():
    all_tests = [('D4', D4_TESTS), ('D5', D5_TESTS)]
    results = {}  # name -> {window_label: (trades, wr, balance)}

    for group_name, tests in all_tests:
        print(f"\n{'='*65}")
        print(f"  {group_name}: 最深回调止损 + OB质量组合测试")
        print(f"{'='*65}")

        for ver, magic, desc, params in tests:
            name = f'v11xau-qs3-{ver.split("-")[-1].lower()}'
            print(f"\n  [{desc}]")

            # 创建 .set
            set_path = make_set(name, magic, ver, desc, params)
            print(f"    .set -> {set_path.name}")

            results[name] = {}

            for date_from, date_to, wlabel, days in WINDOWS:
                print(f"    [{wlabel}] 回测中...", end=' ', flush=True)
                r = run_bt(name, 'XAUUSDm', date_from, date_to, timeout=300)
                if r:
                    t, wr, bal = r
                    td = t // days
                    results[name][wlabel] = (t, td, wr, bal)
                    print(f"{t:>4}t ({td:>2}t/d) {wr:>5.1f}% ${bal:>10.2f}")
                else:
                    results[name][wlabel] = None
                    print(f"FAILED")

    # ── 汇总 ──────────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"  汇总对比（含基线）")
    print(f"{'='*65}")
    print(f"{'策略':<22} {'0602':>20} {'0529':>20}")
    print(f"{'-'*22} {'-'*20} {'-'*20}")

    # 基线数据（从已有结果读取）
    baseline = {
        '0602': (26, 26, 30.8, 178.28),
        '0529': (25, 12, 48.0, 211.31),
    }
    print(f"{'QS3 baseline':<22} {fmt_row(*baseline['0602'])} {fmt_row(*baseline['0529'])}")

    # D1 数据
    d1_data = {
        'D1A bounce0.22': {'0602': (13, 13, 15.4, 187.69), '0529': (18, 9, 61.1, 211.93)},
        'D1B bounce0.30': {'0602': (16, 16, 43.8, 195.67), '0529': (16, 8, 75.0, 220.37)},
        'D1C bounce0.40': {'0602': (15, 15, 20.0, 190.89), '0529': (16, 8, 93.8, 251.64)},
        'D3 H2A+touch2': {'0602': (8, 8, 50.0, 215.24), '0529': (15, 7, 53.3, 227.29)},
    }
    for label, data in d1_data.items():
        print(f"{label:<22} {fmt_row(*data['0602'])} {fmt_row(*data['0529'])}")

    # D4/D5 结果
    for group_name, tests in all_tests:
        for ver, magic, desc, params in tests:
            name = f'v11xau-qs3-{ver.split("-")[-1].lower()}'
            r = results.get(name, {})
            r0602 = r.get('0602')
            r0529 = r.get('0529')
            s0602 = fmt_row(*r0602) if r0602 else 'FAILED'
            s0529 = fmt_row(*r0529) if r0529 else 'FAILED'
            print(f"{desc:<22} {s0602} {s0529}")

    # ── 720d 建议 ────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"  720d 候选（选择短窗口表现最好的 2-3 个）")
    print(f"{'='*65}")

    # 自动选前3
    scored = []
    for group_name, tests in all_tests:
        for ver, magic, desc, params in tests:
            name = f'v11xau-qs3-{ver.split("-")[-1].lower()}'
            r = results.get(name, {})
            score = 0
            if r.get('0602'):
                score += r['0602'][3]  # balance weight
            if r.get('0529'):
                score += r['0529'][3]
            scored.append((score, name, ver, magic, desc, params))

    scored.sort(reverse=True)
    for score, name, ver, magic, desc, params in scored[:3]:
        print(f"\n  >>> 运行 720d: {desc} (score={score:.1f})")
        print(f"      日期: {WINDOW_720[0]} ~ {WINDOW_720[1]}", end=' ', flush=True)
        r = run_bt(name, 'XAUUSDm', WINDOW_720[0], WINDOW_720[1], timeout=3600)
        if r:
            t, wr, bal = r
            td = t // WINDOW_720[3]
            print(f"\n      720d: {t}t ({td}t/d) {wr}% ${bal:,.2f}")
        else:
            print(f"\n      720d: FAILED")

    # ── 清理 .set 文件 ──────────────────────────────────
    for group_name, tests in all_tests:
        for ver, magic, desc, params in tests:
            name = f'v11xau-qs3-{ver.split("-")[-1].lower()}'
            sf = MT5_PROFILES_DIR / f'{name}.set'
            if sf.exists():
                sf.unlink()

    print(f"\n{'='*65}")
    print(f"  全部测试完成")
    print(f"{'='*65}")

def fmt_row(trades, td, wr, bal):
    return f"{trades:>3}t {td:>2}t/d {wr:>5.1f}% ${bal:>9.2f}"

if __name__ == '__main__':
    main()
