#!/usr/bin/env python3
"""MQL5 EA编译器 - 通过Wine调用metaeditor64.exe编译EA"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

WINE = '/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine'
WINEPREFIX = os.path.expanduser('~/Library/Application Support/net.metaquotes.wine.metatrader5')
MT5_MAIN = os.path.join(WINEPREFIX, 'drive_c/Program Files/MetaTrader 5')
MT5_TESTER = os.path.join(WINEPREFIX, 'drive_c/Program Files/MetaTrader 5 Tester')
METAEDITOR = os.path.join(MT5_MAIN, 'metaeditor64.exe')

PROJECT_DIR = Path(__file__).resolve().parent.parent
MQL5_DIR = PROJECT_DIR / 'mql5'


def copy_filter(src, names):
    """只复制 .mq5 和 .mqh 文件，保留目录结构"""
    ignored = []
    for name in names:
        full = os.path.join(src, name)
        if os.path.isfile(full) and not name.endswith(('.mq5', '.mqh')):
            ignored.append(name)
    return set(ignored)


def sync_sources():
    """同步源码到MT5 Main目录"""
    dest_mql5 = Path(MT5_MAIN) / 'MQL5'
    for folder in ['Experts', 'Include']:
        src = MQL5_DIR / folder
        if not src.exists():
            continue
        dst = dest_mql5 / folder
        print(f'同步 {folder} -> {dst}')
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=copy_filter)


def compile_ea(ea_path: str) -> bool:
    """编译单个EA，返回是否成功

    使用 /tmp 临时目录 + Z: drive 路径编译（C:\Program Files 含空格静默失败）。
    目录结构: /tmp/.../WaiTrade_OB.mq5 + WaiTrade/*.mqh
    """
    source_file = Path(MQL5_DIR) / 'Experts' / f'{ea_path}.mq5'
    include_dir = MQL5_DIR / 'Include' / 'WaiTrade'

    if not source_file.exists():
        print(f'错误: 源文件不存在 {source_file}')
        return False

    print(f'编译: {ea_path}')
    env = os.environ.copy()
    env['WINEPREFIX'] = WINEPREFIX

    tmp_dir = Path('/tmp/mt5_compile_WaiTrade_OB/WaiTrade_OB')
    tmp_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_file, tmp_dir / source_file.name)

    inc_dest = tmp_dir / 'WaiTrade'
    if inc_dest.exists():
        shutil.rmtree(inc_dest)
    inc_dest.mkdir()
    for f in include_dir.glob('*.mqh'):
        shutil.copy2(f, inc_dest / f.name)

    ex5_tmp = tmp_dir / source_file.with_suffix('.ex5').name
    log_tmp = tmp_dir / source_file.with_suffix('.log').name
    ex5_tmp.unlink(missing_ok=True)
    log_tmp.unlink(missing_ok=True)

    win_path = f'Z:\\tmp\\mt5_compile_WaiTrade_OB\\WaiTrade_OB\\{source_file.name}'
    cmd = [WINE, METAEDITOR, f'/compile:{win_path}', '/log']
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)

    ex5_file = ex5_tmp
    ea_name = Path(ea_path).name

    # 读取编译日志
    log_content = ''
    if log_tmp.exists():
        try:
            log_content = log_tmp.read_text(encoding='utf-16-le', errors='replace')
        except Exception:
            log_content = log_tmp.read_text(errors='replace')

    # 检查编译结果
    success = False
    if log_content:
        if re.search(r'0 error', log_content) and 'Result' in log_content:
            success = True
        warnings = re.findall(r'warning.*', log_content, re.IGNORECASE)
        for w in warnings:
            print(f'  警告: {w.strip()}')
        if not success:
            errors = re.findall(r'error.*', log_content, re.IGNORECASE)
            for e in errors[:10]:
                print(f'  错误: {e.strip()}')
    elif ex5_file.exists():
        success = True

    if success:
        # 复制.ex5到MT5目录
        dst = Path(MT5_MAIN) / 'MQL5' / 'Experts' / f'{ea_path}.ex5'
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ex5_file, dst)
        print(f'  编译成功: {ea_name}.ex5')
        sync_to_tester(ea_path)
    else:
        print(f'  编译失败: {ea_name}')
        if result.stderr:
            print(f'  stderr: {result.stderr[:500]}')

    return success


def sync_to_tester(ea_path: str):
    """将编译产物同步到Tester目录"""
    src = Path(MT5_MAIN) / 'MQL5' / 'Experts' / f'{ea_path}.ex5'
    dst = Path(MT5_TESTER) / 'MQL5' / 'Experts' / f'{ea_path}.ex5'
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f'  已同步到Tester: {dst.name}')


def find_all_eas() -> list[str]:
    """查找所有EA源文件，返回相对路径列表（不含扩展名）"""
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
    parser.add_argument('ea_path', nargs='?', help='EA路径，如 WaiTrade/WaiTrade_OB')
    parser.add_argument('--all', action='store_true', help='编译所有EA')
    args = parser.parse_args()

    if not args.ea_path and not args.all:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(METAEDITOR):
        print(f'错误: metaeditor64.exe 不存在: {METAEDITOR}')
        sys.exit(1)

    sync_sources()

    if args.all:
        eas = find_all_eas()
        if not eas:
            print('未找到任何EA源文件')
            sys.exit(1)
        print(f'找到 {len(eas)} 个EA')
        ok, fail = 0, 0
        for ea in eas:
            if compile_ea(ea):
                ok += 1
            else:
                fail += 1
        print(f'\n编译完成: 成功 {ok}, 失败 {fail}')
        sys.exit(0 if fail == 0 else 1)
    else:
        success = compile_ea(args.ea_path)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
