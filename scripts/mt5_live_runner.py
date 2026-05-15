#!/usr/bin/env python3
"""MT5 EA Live 部署管理器 — 在 macOS Wine MT5 中部署 EA 并管理终端进程"""

import argparse
import os
import random
import shutil
import signal
import subprocess
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from yaml_to_set import FLAT_MAP, TRAIL_MAP, format_value

# ── Wine / MT5 路径 ────────────────────────────────────────────────────────
WINE = '/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine'
WINEPREFIX = os.path.expanduser('~/Library/Application Support/net.metaquotes.wine.metatrader5')
MT5_MAIN = os.path.join(WINEPREFIX, 'drive_c/Program Files/MetaTrader 5')
TERMINAL_EXE = os.path.join(MT5_MAIN, 'terminal64.exe')

PROFILES_DIR = Path(MT5_MAIN) / 'MQL5' / 'Profiles' / 'Charts'
LIVE_PROFILE_NAME = 'WaiTrade_Live'

CONFIG_FILE = PROJECT_ROOT / 'config' / 'strategies.yaml'
PID_FILE = PROJECT_ROOT / 'results' / 'live' / 'live.pid'
LOG_DIR = PROJECT_ROOT / 'results' / 'live'

EA_NAME = 'WaiTrade\\WaiTrade_OB'
EA_PATH = 'WaiTrade/WaiTrade_OB'


# ── 配置加载 ───────────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_strategy(config: dict, name: str) -> dict:
    non_strategy_keys = {'defaults', 'symbols', 'backtest_defaults', 'mt5_account'}
    if name not in config or name in non_strategy_keys:
        available = [k for k in config if k not in non_strategy_keys and isinstance(config[k], dict)]
        print(f'错误: 策略 "{name}" 不存在。可用: {", ".join(available)}')
        sys.exit(1)
    return config[name]


def resolve_symbols(config: dict, symbol_arg: str) -> list:
    if symbol_arg.lower() == 'all':
        symbols = []
        for category in config.get('symbols', {}).values():
            if isinstance(category, list):
                symbols.extend(category)
        return symbols
    return [s.strip() for s in symbol_arg.split(',')]


# ── EA 参数生成（chr inputs 格式）────────────────────────────────────────

def generate_inputs_block(cfg: dict) -> str:
    """生成 <inputs> 块内容，格式: 参数名=值||0||0||0||N"""
    lines = []
    for yaml_key, inp_name in FLAT_MAP.items():
        if yaml_key in cfg:
            val = format_value(cfg[yaml_key])
            lines.append(f'{inp_name}={val}||0||0||0||N')

    trail_levels = cfg.get('trail_levels', [])
    for idx, level in enumerate(trail_levels):
        if not isinstance(level, dict):
            continue
        for sub_key, val in level.items():
            inp_name = TRAIL_MAP.get((idx, sub_key))
            if inp_name:
                lines.append(f'{inp_name}={format_value(val)}||0||0||0||N')

    return '\n'.join(lines)


# ── .chr 图表文件生成 ──────────────────────────────────────────────────────

def generate_chart_chr(symbol: str, period_size: int, inputs_block: str, chart_id: int = None) -> str:
    """生成单个品种的 .chr 图表配置（纯文本，写入时转 UTF-16LE）"""
    if chart_id is None:
        chart_id = random.randint(10**18, 10**19 - 1)

    return f"""<chart>
id={chart_id}
symbol={symbol}
period_type=0
period_size={period_size}
expertmode=1
scroll=1
shift=1
shift_size=20.000000
ohlc=1
one_click=0
bidline=1
askline=1
lastline=0
tradehistory=1
windows_total=1

<window>
height=100.000000
objects=0

<indicator>
name=Main
path=
apply=1
show_data=1
scale_inherit=0
scale_line=0
scale_line_percent=50
scale_line_value=0.000000
scale_fix_min=0
scale_fix_min_val=0.000000
scale_fix_max=0
scale_fix_max_val=0.000000
expertmode=1
fixed_height=-1
</indicator>

<expert>
name={EA_NAME}
path=
flags=339
window_num=0

<inputs>
{inputs_block}
</inputs>
</expert>

</window>
</chart>
"""


def generate_order_wnd(chart_count: int) -> str:
    """生成 order.wnd 窗口布局文件"""
    lines = [f'charts_count={chart_count}']
    for i in range(chart_count):
        lines.append(f'chart{i:02d}=chart{i + 1:02d}.chr')
    return '\n'.join(lines) + '\n'


def write_chr_file(path: Path, content: str):
    """以 UTF-16LE 编码写入 .chr 文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-16-le') as f:
        f.write(content)


# ── Profile 创建 ──────────────────────────────────────────────────────────

def create_live_profile(strategy_name: str, symbols: list, cfg: dict):
    """创建 MT5 Live Profile 目录，为每个品种生成带 EA 的图表"""
    profile_dir = PROFILES_DIR / LIVE_PROFILE_NAME

    if profile_dir.exists():
        shutil.rmtree(profile_dir)
    profile_dir.mkdir(parents=True)

    period_size = cfg.get('bar_period_min', 1)
    inputs_block = generate_inputs_block(cfg)

    print(f'创建 Live Profile: {LIVE_PROFILE_NAME}')
    print(f'  策略: {strategy_name} | 周期: M{period_size} | 品种数: {len(symbols)}')

    for i, symbol in enumerate(symbols, 1):
        chart_content = generate_chart_chr(symbol, period_size, inputs_block)
        chart_path = profile_dir / f'chart{i:02d}.chr'
        write_chr_file(chart_path, chart_content)
        print(f'  图表 {i:02d}: {symbol} M{period_size} + EA')

    order_content = generate_order_wnd(len(symbols))
    order_path = profile_dir / 'order.wnd'
    with open(order_path, 'w', encoding='utf-16-le') as f:
        f.write(order_content)

    print(f'  Profile 已写入: {profile_dir}')
    return profile_dir


# ── EA 编译 ───────────────────────────────────────────────────────────────

def compile_ea():
    """编译 EA，调用 mt5_compile.py 的逻辑"""
    from mt5_compile import sync_sources, compile_ea as do_compile

    print('同步源码并编译 EA...')
    sync_sources()
    success = do_compile(EA_PATH)
    if not success:
        print('错误: EA 编译失败，无法部署')
        sys.exit(1)
    print('EA 编译成功')


# ── 进程管理 ──────────────────────────────────────────────────────────────

def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def find_mt5_pid() -> int | None:
    """查找 MT5 Main 终端进程 PID"""
    result = subprocess.run(
        ['pgrep', '-f', 'MetaTrader 5/terminal64'],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        pids = result.stdout.strip().split('\n')
        if pids and pids[0]:
            return int(pids[0])
    return None


def read_saved_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        if is_process_running(pid):
            return pid
    except (ValueError, OSError):
        pass
    PID_FILE.unlink(missing_ok=True)
    return None


def save_pid(pid: int):
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(pid))


# ── 命令实现 ──────────────────────────────────────────────────────────────

def cmd_start(strategy: str, symbols: list):
    existing_pid = read_saved_pid() or find_mt5_pid()
    if existing_pid:
        print(f'警告: MT5 终端已在运行 (PID={existing_pid})')
        print('Profile 将被更新，但需要手动重启终端或切换 Profile')
        print('如需重启，请先执行: python mt5_live_runner.py --stop')

    config = load_config()
    cfg = get_strategy(config, strategy)

    if 'version' not in cfg:
        cfg['version'] = strategy

    symbol_list = resolve_symbols(config, symbols) if isinstance(symbols, str) else symbols

    compile_ea()

    create_live_profile(strategy, symbol_list, cfg)

    if existing_pid:
        print(f'\nProfile 已更新。终端正在运行中 (PID={existing_pid})。')
        print('请在 MT5 中手动切换到 WaiTrade_Live Profile，或 --stop 后重新 --start')
        return

    print('\n启动 MT5 终端...')
    env = os.environ.copy()
    env['WINEPREFIX'] = WINEPREFIX

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f'live_{datetime.now().strftime("%Y%m%d")}.log'

    cmd = [WINE, TERMINAL_EXE, f'/profile:{LIVE_PROFILE_NAME}']
    print(f'命令: {" ".join(cmd)}')

    log_file = open(log_path, 'a', encoding='utf-8')
    log_file.write(f'\n{"=" * 60}\n')
    log_file.write(f'启动: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
    log_file.write(f'策略: {strategy} | 品种: {", ".join(symbol_list)}\n')
    log_file.write(f'{"=" * 60}\n')

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    time.sleep(3)
    if proc.poll() is not None:
        print(f'错误: 终端进程立即退出 (code={proc.returncode})')
        sys.exit(1)

    actual_pid = find_mt5_pid() or proc.pid
    save_pid(actual_pid)

    print(f'MT5 终端已启动 (PID={actual_pid})')
    print(f'日志: {log_path}')
    print(f'\n注意: 首次运行需在 MT5 GUI 中点击 "AutoTrading" 按钮启用自动交易')
    print(f'查看状态: python {Path(__file__).name} --status')
    print(f'停止交易: python {Path(__file__).name} --stop')


def cmd_status():
    pid = read_saved_pid() or find_mt5_pid()
    if not pid:
        print('MT5 终端未运行')
        return

    running = is_process_running(pid)
    print(f'MT5 终端: {"运行中" if running else "已停止"} (PID={pid})')

    if not running:
        PID_FILE.unlink(missing_ok=True)
        return

    profile_dir = PROFILES_DIR / LIVE_PROFILE_NAME
    if profile_dir.exists():
        charts = list(profile_dir.glob('chart*.chr'))
        print(f'Live Profile: {len(charts)} 个图表')

    ea_log_dir = Path(MT5_MAIN) / 'MQL5' / 'Logs'
    if ea_log_dir.exists():
        today = datetime.now().strftime('%Y%m%d')
        log_files = sorted(ea_log_dir.glob(f'{today}*.log'), reverse=True)
        if log_files:
            latest = log_files[0]
            print(f'\n── EA 最近日志 ({latest.name}) ──')
            try:
                content = latest.read_text(encoding='utf-16-le', errors='replace')
                lines = content.strip().split('\n')
                for line in lines[-15:]:
                    print(f'  {line.rstrip()}')
            except Exception as e:
                print(f'  读取日志失败: {e}')


def cmd_stop():
    pid = read_saved_pid() or find_mt5_pid()
    if not pid:
        print('MT5 终端未运行')
        return

    print(f'停止 MT5 终端 (PID={pid})...')
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        if is_process_running(pid):
            os.kill(pid, signal.SIGKILL)
            time.sleep(1)
    except ProcessLookupError:
        pass

    PID_FILE.unlink(missing_ok=True)

    subprocess.run(['pkill', '-f', 'MetaTrader 5/terminal64'],
                   capture_output=True)

    print('MT5 终端已停止')


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='MT5 EA Live 部署管理器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
            使用示例:
              部署并启动:  python %(prog)s --strategy v96b_live --symbols XAUUSDm,BTCUSDm
              全品种启动:  python %(prog)s --strategy v96b_live --symbols all
              查看状态:    python %(prog)s --status
              停止交易:    python %(prog)s --stop
        '''),
    )
    parser.add_argument('--strategy', '-s', help='策略名称（对应 strategies.yaml 中的 key）')
    parser.add_argument('--symbols', help='交易品种（逗号分隔，或 "all"）')
    parser.add_argument('--status', action='store_true', help='查看运行状态')
    parser.add_argument('--stop', action='store_true', help='停止 MT5 终端')
    parser.add_argument('--no-compile', action='store_true', help='跳过 EA 编译')
    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.stop:
        cmd_stop()
    elif args.strategy and args.symbols:
        if args.no_compile:
            global compile_ea
            compile_ea = lambda: print('跳过编译')
        cmd_start(args.strategy, args.symbols)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
