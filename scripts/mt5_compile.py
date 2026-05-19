#!/usr/bin/env python3
"""MQL5 EA 编译器 - 自动适配 Windows 原生 MT5 与 macOS Wine MT5。"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
MQL5_DIR = PROJECT_DIR / 'mql5'

WINE = '/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine'
WINEPREFIX = os.path.expanduser('~/Library/Application Support/net.metaquotes.wine.metatrader5')
WINE_MT5_MAIN = Path(WINEPREFIX) / 'drive_c' / 'Program Files' / 'MetaTrader 5'
WINE_MT5_TESTER = Path(WINEPREFIX) / 'drive_c' / 'Program Files' / 'MetaTrader 5 Tester'

WIN_DEFAULT_TERMINAL_ID = 'D0E8209F77C8CF37AD8BF550E51FF075'
WIN_MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))


@dataclass
class CompileRuntime:
    kind: str
    metaeditor: Path
    mt5_mql5: Path
    tester_mql5: Path
    wine: Path = None
    wineprefix: str = None


def copy_filter(src, names):
    """只复制 .mq5/.mqh 文件，保留目录结构。"""
    ignored = []
    for name in names:
        full = os.path.join(src, name)
        if os.path.isfile(full) and not name.endswith(('.mq5', '.mqh')):
            ignored.append(name)
    return set(ignored)


def find_windows_data_dir():
    env_data = os.environ.get('MT5_DATA')
    if env_data:
        return Path(env_data)

    appdata = os.environ.get('APPDATA')
    if not appdata:
        return Path(r'C:\Users\Gnef\AppData\Roaming') / 'MetaQuotes' / 'Terminal' / WIN_DEFAULT_TERMINAL_ID

    default = Path(appdata) / 'MetaQuotes' / 'Terminal' / WIN_DEFAULT_TERMINAL_ID
    if default.exists():
        return default

    terminal_root = Path(appdata) / 'MetaQuotes' / 'Terminal'
    candidates = sorted(
        [p for p in terminal_root.glob('*') if (p / 'MQL5').exists()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ) if terminal_root.exists() else []
    return candidates[0] if candidates else default


def get_runtime():
    if os.name == 'nt':
        mt5_data = find_windows_data_dir()
        tester_data = Path(os.environ.get('MT5_TESTER_DATA', str(mt5_data)))
        return CompileRuntime(
            kind='windows',
            metaeditor=WIN_MT5_HOME / 'metaeditor64.exe',
            mt5_mql5=mt5_data / 'MQL5',
            tester_mql5=tester_data / 'MQL5',
        )

    wineprefix = os.environ.get('WINEPREFIX', WINEPREFIX)
    mt5_main = Path(wineprefix) / 'drive_c' / 'Program Files' / 'MetaTrader 5'
    mt5_tester = Path(wineprefix) / 'drive_c' / 'Program Files' / 'MetaTrader 5 Tester'
    return CompileRuntime(
        kind='wine',
        wine=Path(os.environ.get('WINE', WINE)),
        wineprefix=wineprefix,
        metaeditor=mt5_main / 'metaeditor64.exe',
        mt5_mql5=mt5_main / 'MQL5',
        tester_mql5=mt5_tester / 'MQL5',
    )


def sync_sources(runtime=None):
    """同步源码到目标 MT5 MQL5 目录。"""
    runtime = runtime or get_runtime()
    for folder in ['Experts', 'Include']:
        src = MQL5_DIR / folder
        if not src.exists():
            continue
        dst = runtime.mt5_mql5 / folder
        print(f'同步 {folder} -> {dst}')
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=copy_filter)


def read_log(log_path):
    if not log_path.exists():
        return ''
    for encoding in ['utf-16-le', 'utf-8']:
        try:
            return log_path.read_text(encoding=encoding, errors='replace')
        except Exception:
            pass
    return log_path.read_text(errors='replace')


def log_has_success(log_content):
    return bool(re.search(r'Result:\s*0\s+errors?', log_content, re.IGNORECASE))


def print_log_diagnostics(log_content):
    warnings = [
        line for line in log_content.splitlines()
        if re.search(r'\bwarning\b', line, re.IGNORECASE) and not re.search(r'\b0\s+warnings?\b', line, re.IGNORECASE)
    ]
    for warning in warnings[:20]:
        print(f'  警告: {warning.strip()}')

    if not log_has_success(log_content):
        errors = re.findall(r'.*error.*', log_content, re.IGNORECASE)
        for error in errors[:20]:
            print(f'  错误: {error.strip()}')


def compile_with_windows(runtime, ea_path):
    source_file = runtime.mt5_mql5 / 'Experts' / f'{ea_path}.mq5'
    ex5_file = source_file.with_suffix('.ex5')
    log_file = source_file.with_suffix('.log')
    log_file.unlink(missing_ok=True)

    cmd = [str(runtime.metaeditor), f'/compile:{source_file}', '/log']
    return run_metaeditor(cmd, source_file, ex5_file, log_file)


def compile_with_wine(runtime, ea_path):
    source_file = MQL5_DIR / 'Experts' / f'{ea_path}.mq5'
    ea_parts = Path(ea_path).parts
    include_name = ea_parts[0] if len(ea_parts) > 1 else 'WaiTrade2'
    include_dir = MQL5_DIR / 'Include' / include_name

    tmp_root = Path('/tmp/mt5_compile_WaiTrade_OB')
    tmp_dir = tmp_root / 'WaiTrade_OB'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_file, tmp_dir / source_file.name)

    inc_dest = tmp_dir / include_name
    if inc_dest.exists():
        shutil.rmtree(inc_dest)
    inc_dest.mkdir()
    for f in include_dir.glob('*.mqh'):
        shutil.copy2(f, inc_dest / f.name)

    ex5_file = tmp_dir / source_file.with_suffix('.ex5').name
    log_file = tmp_dir / source_file.with_suffix('.log').name
    ex5_file.unlink(missing_ok=True)
    log_file.unlink(missing_ok=True)

    win_path = f'Z:\\tmp\\mt5_compile_WaiTrade_OB\\WaiTrade_OB\\{source_file.name}'
    env = os.environ.copy()
    env['WINEPREFIX'] = runtime.wineprefix
    cmd = [str(runtime.wine), str(runtime.metaeditor), f'/compile:{win_path}', '/log']
    success = run_metaeditor(cmd, source_file, ex5_file, log_file, env=env)
    if success:
        dst = runtime.mt5_mql5 / 'Experts' / f'{ea_path}.ex5'
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ex5_file, dst)
    return success


def run_metaeditor(cmd, source_file, ex5_file, log_file, env=None):
    print(f'命令: {" ".join(str(c) for c in cmd)}')
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=180)

    log_content = read_log(log_file)
    if log_content:
        print_log_diagnostics(log_content)

    success = log_has_success(log_content)
    if not log_content and ex5_file.exists():
        success = True

    if success and ex5_file.exists():
        print(f'  编译成功: {source_file.with_suffix(".ex5").name}')
        return True

    print(f'  编译失败: {source_file.name}')
    if result.stdout:
        print(f'  stdout: {result.stdout[:500]}')
    if result.stderr:
        print(f'  stderr: {result.stderr[:500]}')
    if log_file.exists():
        print(f'  日志: {log_file}')
    return False


def compile_ea(ea_path, runtime=None):
    """编译单个 EA，返回是否成功。"""
    runtime = runtime or get_runtime()
    source_file = MQL5_DIR / 'Experts' / f'{ea_path}.mq5'
    ea_parts = Path(ea_path).parts
    include_name = ea_parts[0] if len(ea_parts) > 1 else 'WaiTrade2'
    include_dir = MQL5_DIR / 'Include' / include_name

    if not source_file.exists():
        print(f'错误: 源文件不存在 {source_file}')
        return False
    if not include_dir.exists():
        print(f'错误: Include目录不存在 {include_dir}')
        return False

    print(f'编译: {ea_path} ({runtime.kind})')
    success = compile_with_windows(runtime, ea_path) if runtime.kind == 'windows' else compile_with_wine(runtime, ea_path)
    if success:
        sync_to_tester(ea_path, runtime)
    return success


def sync_to_tester(ea_path, runtime=None):
    """将编译产物同步到 Tester 目录。Windows 默认和主数据目录相同。"""
    runtime = runtime or get_runtime()
    src = runtime.mt5_mql5 / 'Experts' / f'{ea_path}.ex5'
    dst = runtime.tester_mql5 / 'Experts' / f'{ea_path}.ex5'
    if not src.exists():
        return
    if src.resolve() == dst.resolve():
        print(f'  编译产物已在MT5数据目录: {src}')
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f'  已同步到Tester: {dst}')


def find_all_eas():
    """查找所有 EA 源文件，返回相对路径列表（不含扩展名）。"""
    experts_dir = MQL5_DIR / 'Experts'
    if not experts_dir.exists():
        return []
    eas = []
    for f in experts_dir.rglob('*.mq5'):
        rel = f.relative_to(experts_dir).with_suffix('')
        eas.append(str(rel))
    return sorted(eas)


def main():
    parser = argparse.ArgumentParser(description='MQL5 EA编译器')
    parser.add_argument('ea_path', nargs='?', help='EA路径，如 WaiTrade2/WaiTrade_OB')
    parser.add_argument('--all', action='store_true', help='编译所有EA')
    args = parser.parse_args()

    if not args.ea_path and not args.all:
        parser.print_help()
        sys.exit(1)

    runtime = get_runtime()
    if not runtime.metaeditor.exists():
        print(f'错误: metaeditor64.exe 不存在: {runtime.metaeditor}')
        sys.exit(1)

    sync_sources(runtime)

    if args.all:
        eas = find_all_eas()
        if not eas:
            print('未找到任何EA源文件')
            sys.exit(1)
        print(f'找到 {len(eas)} 个EA')
        ok, fail = 0, 0
        for ea in eas:
            if compile_ea(ea, runtime):
                ok += 1
            else:
                fail += 1
        print(f'\n编译完成: 成功 {ok}, 失败 {fail}')
        sys.exit(0 if fail == 0 else 1)

    success = compile_ea(args.ea_path, runtime)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
