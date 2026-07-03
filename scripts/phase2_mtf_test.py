#!/usr/bin/env python3
"""Phase 2: MTF=ON 单规则验证 — 生成.set变体 + 生成INI + 运行回测"""
import os, sys, shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
BT = ROOT / 'temp' / 'mt5_portable_bt'
TESTER_DIR = BT / 'MQL5' / 'Profiles' / 'Tester'
INI_DIR = BT / 'Tester'
BASE_SET = TESTER_DIR / 'v11xau-qs3.set'

# MTF test configurations
TESTS = {
    'mtf-off':   {'InpEnableMTF': 'false', 'InpMTFEnableR5BlockCounterH1': 'true', 'InpMTFEnableR4BlockCounterM15AtZone': 'true', 'InpMTFEnableR1bReduceDeepRun': 'true'},
    'mtf-all':   {'InpEnableMTF': 'true',  'InpMTFEnableR5BlockCounterH1': 'true', 'InpMTFEnableR4BlockCounterM15AtZone': 'true', 'InpMTFEnableR1bReduceDeepRun': 'true'},
    'mtf-r5':    {'InpEnableMTF': 'true',  'InpMTFEnableR5BlockCounterH1': 'true', 'InpMTFEnableR4BlockCounterM15AtZone': 'false', 'InpMTFEnableR1bReduceDeepRun': 'false'},
    'mtf-r4':    {'InpEnableMTF': 'true',  'InpMTFEnableR5BlockCounterH1': 'false', 'InpMTFEnableR4BlockCounterM15AtZone': 'true', 'InpMTFEnableR1bReduceDeepRun': 'false'},
    'mtf-r1b':   {'InpEnableMTF': 'true',  'InpMTFEnableR5BlockCounterH1': 'false', 'InpMTFEnableR4BlockCounterM15AtZone': 'false', 'InpMTFEnableR1bReduceDeepRun': 'true'},
}

def generate_set_variants():
    """读取基础.set，生成MTF变体"""
    if not BASE_SET.exists():
        print(f"[ERROR] 基础 .set 不存在: {BASE_SET}")
        return {}

    base_content = BASE_SET.read_text(encoding='utf-8')
    results = {}

    for name, overrides in TESTS.items():
        content = base_content
        for key, val in overrides.items():
            # 替换 InpXxx=oldval → InpXxx=newval
            import re
            pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
            if pattern.search(content):
                content = pattern.sub(f'{key}={val}', content)
            else:
                print(f"  [WARN] {key} not found in .set, appending")
                content += f'\n{key}={val}\n'

        out_path = TESTER_DIR / f'v11xau-qs3-{name}.set'
        out_path.write_text(content, encoding='utf-8')
        results[name] = out_path
        print(f"  Generated: {out_path.name}")

    return results

def generate_ini(name, set_name, symbol='XAUUSDm', period='M1',
                 date_from='2026.05.22', date_to='2026.05.30'):
    """生成回测 INI 文件"""
    os.makedirs(INI_DIR, exist_ok=True)

    ini_content = f"""[Common]
Login=
Server=
[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters={set_name}
Symbol={symbol}
Period={period}
Model=4
Optimization=0
FromDate={date_from}
ToDate={date_to}
Deposit=200
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report={name}
"""
    ini_path = INI_DIR / f'{name}.ini'
    ini_path.write_text(ini_content, encoding='utf-8')
    print(f"  INI: {ini_path.name} ({date_from} -> {date_to})")
    return ini_path

def main():
    print("=" * 60)
    print("Phase 2: MTF 单规则验证")
    print("=" * 60)

    # Step 1: Generate .set variants
    print("\n[1] Generating .set variants...")
    sets = generate_set_variants()

    # Step 2: Generate INI files
    print("\n[2] Generating INI files...")
    ini_files = {}
    for name in TESTS:
        set_name = f'v11xau-qs3-{name}.set'
        ini_files[name] = generate_ini(name, set_name)

    # Step 3: Print backtest commands
    print("\n[3] Backtest commands (run in PowerShell as Admin):")
    terminal = BT / 'terminal64.exe'
    for name, ini_path in ini_files.items():
        ini_abs = str(ini_path).replace('/', '\\')
        print(f'\n  #{name}:')
        print(f'  & "{terminal}" /config:"{ini_abs}" /portable')

    print("\n[DONE] Ready for backtest.")

if __name__ == '__main__':
    main()
