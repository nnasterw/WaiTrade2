#!/usr/bin/env python3
"""MT5 Live交易执行管理器 - 通过Wine Python + MetaTrader5包在macOS上运行实盘交易"""

import argparse
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path

import yaml

# ── Wine环境常量 ──────────────────────────────────────────────────────────────
WINE = '/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine'
WINEPREFIX = os.path.expanduser('~/Library/Application Support/net.metaquotes.wine.metatrader5')
MT5_TESTER = os.path.join(WINEPREFIX, 'drive_c/Program Files/MetaTrader 5 Tester')
WINE_PYTHON = r'C:\Python311\python.exe'

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
PID_FILE = PROJECT_ROOT / 'results' / 'live' / 'live.pid'
LOG_DIR = PROJECT_ROOT / 'results' / 'live'
CONFIG_FILE = PROJECT_ROOT / 'config' / 'strategies.yaml'

# Wine内部脚本路径（无空格路径）
WINE_SCRIPT_DIR = r'C:\bt'
WINE_SCRIPT_NAME = 'live_trading.py'
WINE_SCRIPT_WIN_PATH = f'{WINE_SCRIPT_DIR}\\{WINE_SCRIPT_NAME}'
# macOS上对应的实际路径
MAC_SCRIPT_DIR = os.path.join(WINEPREFIX, 'drive_c', 'bt')
MAC_SCRIPT_PATH = os.path.join(MAC_SCRIPT_DIR, WINE_SCRIPT_NAME)


def load_strategy_config(strategy_name: str) -> dict:
    if not CONFIG_FILE.exists():
        print(f'错误: 策略配置文件不存在: {CONFIG_FILE}')
        sys.exit(1)
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        all_config = yaml.safe_load(f)
    strategies = all_config.get('strategies', all_config)
    if strategy_name not in strategies:
        available = ', '.join(strategies.keys()) if isinstance(strategies, dict) else '无'
        print(f'错误: 策略 "{strategy_name}" 不存在，可用策略: {available}')
        sys.exit(1)
    return strategies[strategy_name]


def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def check_existing_process():
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        PID_FILE.unlink(missing_ok=True)
        return False
    if is_process_running(pid):
        return True
    PID_FILE.unlink(missing_ok=True)
    return False


def ensure_tester_terminal():
    result = subprocess.run(['pgrep', '-f', 'MetaTrader 5 Tester'], capture_output=True)
    if result.returncode == 0:
        print('Tester终端已在运行')
        return
    print('启动Tester MT5终端...')
    env = os.environ.copy()
    env['WINEPREFIX'] = WINEPREFIX
    terminal_exe = r'C:\Program Files\MetaTrader 5 Tester\terminal64.exe'
    subprocess.Popen(
        [WINE, terminal_exe, '/portable'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print('等待终端初始化(10秒)...')
    time.sleep(10)
    result = subprocess.run(['pgrep', '-f', 'MetaTrader 5 Tester'], capture_output=True)
    if result.returncode != 0:
        print('警告: 终端可能未成功启动，继续尝试...')
    else:
        print('Tester终端已就绪')


def generate_trading_script(config: dict, symbols: list) -> str:
    config_json = json.dumps(config, ensure_ascii=False, indent=4)
    symbols_json = json.dumps(symbols, ensure_ascii=False)
    version = config.get('version', 'unknown')

    script = f'''# -*- coding: utf-8 -*-
"""WaiTrade Live Trading Script - 运行于Wine Python环境"""
import MetaTrader5 as mt5
import time
import json
from datetime import datetime

CONFIG = {config_json}
SYMBOLS = {symbols_json}

def main():
    if not mt5.initialize(path=r'C:\\Program Files\\MetaTrader 5 Tester\\terminal64.exe'):
        print(f'MT5初始化失败: {{mt5.last_error()}}')
        return

    account = mt5.account_info()
    if account is None:
        print('无法获取账户信息，请检查终端是否已登录')
        mt5.shutdown()
        return

    print(f'已连接: {{account.login}} | 余额: {{account.balance}} | 杠杆: 1:{{account.leverage}}')
    print(f'策略: {version} | 品种: {{", ".join(SYMBOLS)}}')
    print(f'启动时间: {{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}}')
    print('-' * 60)

    for symbol in SYMBOLS:
        info = mt5.symbol_info(symbol)
        if info is None:
            print(f'警告: 品种 {{symbol}} 不存在')
        elif not info.visible:
            if not mt5.symbol_select(symbol, True):
                print(f'警告: 无法选择品种 {{symbol}}')
            else:
                print(f'已启用品种: {{symbol}}')
        else:
            print(f'品种就绪: {{symbol}} | 点差: {{info.spread}}')

    print('-' * 60)
    tick_count = 0
    while True:
        for symbol in SYMBOLS:
            check_signals(symbol)
            manage_positions(symbol)
        tick_count += 1
        if tick_count % 60 == 0:
            print(f'[{{datetime.now().strftime("%H:%M:%S")}}] 心跳 #{{tick_count // 60}} | 已运行{{tick_count}}秒')
        time.sleep(1)


def check_signals(symbol):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, CONFIG.get('bars', 5000))
    if rates is None:
        return
    # TODO: OB检测和信号生成
    # 实际的OB检测逻辑将从MQL5移植或从独立模块加载
    pass


def manage_positions(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return
    for pos in positions:
        # TODO: 移动止损、保本、DTP逻辑
        pass


def place_order(symbol, direction, lot, sl, tp):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f'获取{{symbol}}报价失败')
        return None
    request = {{
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': symbol,
        'volume': lot,
        'type': mt5.ORDER_TYPE_BUY if direction == 'buy' else mt5.ORDER_TYPE_SELL,
        'price': tick.ask if direction == 'buy' else tick.bid,
        'sl': sl,
        'tp': tp,
        'magic': 202605,
        'comment': f'WaiTrade {version}',
        'type_time': mt5.ORDER_TIME_GTC,
        'type_filling': mt5.ORDER_FILLING_IOC,
    }}
    result = mt5.order_send(request)
    if result is None:
        print(f'下单请求失败 {{symbol}}: 返回None')
        return None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f'下单失败 {{symbol}}: {{result.comment}} (code={{result.retcode}})')
    else:
        print(f'下单成功 {{symbol}} {{direction}} {{lot}}手 @ {{request["price"]}}  SL={{sl}} TP={{tp}}')
    return result


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('收到停止信号')
    finally:
        mt5.shutdown()
        print('MT5连接已断开')
'''
    return script


def cmd_start(strategy: str, symbols: list):
    if check_existing_process():
        pid = int(PID_FILE.read_text().strip())
        print(f'错误: 已有实盘进程在运行 (PID={pid})，请先执行 --stop')
        sys.exit(1)

    print(f'加载策略: {strategy}')
    config = load_strategy_config(strategy)
    if 'version' not in config:
        config['version'] = strategy

    print(f'交易品种: {", ".join(symbols)}')

    ensure_tester_terminal()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    os.makedirs(MAC_SCRIPT_DIR, exist_ok=True)

    print('生成交易脚本...')
    script_content = generate_trading_script(config, symbols)
    with open(MAC_SCRIPT_PATH, 'w', encoding='utf-8') as f:
        f.write(script_content)
    print(f'交易脚本已写入: {MAC_SCRIPT_PATH}')

    log_filename = f'live_{datetime.now().strftime("%Y%m%d")}.log'
    log_path = LOG_DIR / log_filename

    env = os.environ.copy()
    env['WINEPREFIX'] = WINEPREFIX
    env['PYTHONIOENCODING'] = 'utf-8'

    cmd = [WINE, WINE_PYTHON, '-X', 'utf8', '-u', WINE_SCRIPT_WIN_PATH]
    print(f'启动Wine Python交易进程...')
    print(f'命令: {" ".join(cmd)}')

    log_file = open(log_path, 'a', encoding='utf-8')
    log_file.write(f'\n{"=" * 60}\n')
    log_file.write(f'启动时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
    log_file.write(f'策略: {strategy} | 品种: {", ".join(symbols)}\n')
    log_file.write(f'{"=" * 60}\n')
    log_file.flush()

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(proc.pid))

    time.sleep(2)
    if proc.poll() is not None:
        print(f'错误: 进程启动后立即退出 (返回码={proc.returncode})')
        print(f'请检查日志: {log_path}')
        PID_FILE.unlink(missing_ok=True)
        log_file.close()
        sys.exit(1)

    log_file.close()

    print(f'\n实盘交易已启动')
    print(f'  PID:    {proc.pid}')
    print(f'  策略:   {strategy}')
    print(f'  品种:   {", ".join(symbols)}')
    print(f'  日志:   {log_path}')
    print(f'  PID文件: {PID_FILE}')
    print(f'\n使用 --status 查看状态，--stop 停止交易')


def cmd_status():
    if not PID_FILE.exists():
        print('当前没有运行中的实盘进程')
        return

    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        print('PID文件损坏')
        return

    running = is_process_running(pid)
    status = '运行中' if running else '已停止'
    print(f'实盘状态: {status}')
    print(f'PID: {pid}')

    if not running:
        print('进程已不存在，清理PID文件')
        PID_FILE.unlink(missing_ok=True)

    today = datetime.now().strftime('%Y%m%d')
    log_path = LOG_DIR / f'live_{today}.log'
    if log_path.exists():
        print(f'\n── 最近日志 ({log_path.name}) ──')
        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            for line in lines[-20:]:
                print(f'  {line.rstrip()}')
        except OSError as e:
            print(f'读取日志失败: {e}')
    else:
        print(f'今日日志不存在: {log_path}')


def cmd_stop():
    if not PID_FILE.exists():
        print('当前没有运行中的实盘进程')
        return

    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        print('PID文件损坏，已清理')
        PID_FILE.unlink(missing_ok=True)
        return

    if not is_process_running(pid):
        print(f'进程 {pid} 已不存在，清理PID文件')
        PID_FILE.unlink(missing_ok=True)
        return

    print(f'发送SIGTERM到进程 {pid}...')
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as e:
        print(f'发送信号失败: {e}')
        PID_FILE.unlink(missing_ok=True)
        return

    for i in range(5):
        time.sleep(1)
        if not is_process_running(pid):
            print('进程已优雅退出')
            PID_FILE.unlink(missing_ok=True)
            print('实盘交易已停止')
            return
        print(f'等待进程退出... ({i + 1}/5)')

    print('进程未响应SIGTERM，发送SIGKILL...')
    try:
        os.kill(pid, signal.SIGKILL)
        time.sleep(1)
    except OSError:
        pass

    PID_FILE.unlink(missing_ok=True)
    print('实盘交易已强制停止')


def main():
    parser = argparse.ArgumentParser(
        description='MT5 实盘交易执行管理器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
            使用示例:
              启动交易:  python %(prog)s --strategy v96b --symbols XAUUSDm,BTCUSDm,ETHUSDm
              查看状态:  python %(prog)s --status
              停止交易:  python %(prog)s --stop
        '''),
    )
    parser.add_argument('--strategy', '-s', help='策略名称（对应strategies.yaml中的配置）')
    parser.add_argument('--symbols', help='交易品种，逗号分隔（如 XAUUSDm,BTCUSDm）')
    parser.add_argument('--status', action='store_true', help='查看实盘运行状态')
    parser.add_argument('--stop', action='store_true', help='停止实盘交易')

    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.stop:
        cmd_stop()
    elif args.strategy and args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
        if not symbols:
            print('错误: 品种列表为空')
            sys.exit(1)
        cmd_start(args.strategy, symbols)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
