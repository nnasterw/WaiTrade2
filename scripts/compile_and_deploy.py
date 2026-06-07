#!/usr/bin/env python3
"""One-click compile + deploy .ex5. Solves 2026-06-07 blood lesson.
Usage:
  python scripts/compile_and_deploy.py                          # portable (D:)
  python scripts/compile_and_deploy.py --installed              # installed (C:)
  python scripts/compile_and_deploy.py --all                    # both"""
import argparse, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPILE_SCRIPT = ROOT / 'scripts' / 'mt5_compile_win.py'
PROJECT_EX5 = ROOT / 'mql5' / 'Experts' / 'WaiTrade2' / 'WaiTrade_OB.ex5'
PORTABLE_DATA = ROOT / 'temp' / 'mt5_portable_bt'
INSTALLED_DATA = Path(os.path.expandvars(
    r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))

def compile_with_env(env_overrides, label):
    env = os.environ.copy()
    env.update(env_overrides)
    r = subprocess.run([sys.executable, str(COMPILE_SCRIPT)],
                       capture_output=True, text=True, env=env)
    print(f'[{label}] {r.stdout.strip()}')
    ok = r.returncode == 0 and 'success=true' in r.stdout
    if not ok:
        print(f'[{label}] COMPILE FAILED')
        for line in r.stdout.split('\n'):
            if 'error' in line.lower() or 'fail' in line.lower():
                print(f'  {line.strip()}')
        return None
    return env_overrides.get('MT5_DATA')

def deploy_from(compile_data_dir):
    compiled = Path(compile_data_dir) / 'MQL5' / 'Experts' / 'WaiTrade2' / 'WaiTrade_OB.ex5'
    if not compiled.exists():
        print(f'[ERR] no compiled output: {compiled}')
        return False
    PROJECT_EX5.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_EX5.write_bytes(compiled.read_bytes())
    size = PROJECT_EX5.stat().st_size
    print(f'[OK] deployed: {PROJECT_EX5} ({size/1024:.0f}KB)')
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['portable', 'installed', 'all'], default='portable')
    args = parser.parse_args()

    modes = [('portable', {'MT5_HOME': str(PORTABLE_DATA), 'MT5_DATA': str(PORTABLE_DATA)}),
             ('installed', {})] if args.mode == 'all' else [
        ('portable', {'MT5_HOME': str(PORTABLE_DATA), 'MT5_DATA': str(PORTABLE_DATA)}) if args.mode == 'portable' else
        ('installed', {})
    ]

    all_ok = True
    for label, env_ov in modes:
        print(f'\n{"="*40}\n  [{label}] compile\n{"="*40}')
        compile_data = compile_with_env(env_ov, label)
        if compile_data:
            deploy_from(compile_data)
        else:
            all_ok = False

    if all_ok and PROJECT_EX5.exists():
        print(f'\n[OK] done: {PROJECT_EX5} ({PROJECT_EX5.stat().st_size/1024:.0f}KB)')

    raise SystemExit(0 if all_ok else 1)

if __name__ == '__main__':
    main()
