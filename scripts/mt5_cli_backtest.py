#!/usr/bin/env python3
"""MT5 Strategy Tester 回测管理器 — 通过 Wine 在 macOS 上运行 MT5 回测"""

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from mt5_common import (
    load_config, resolve_symbols, resolve_strategies,
    parse_agent_log_content, calc_stats, format_report, RESULTS_DIR,
    write_set_file, backtest_main,
)

# ── Wine / MT5 路径常量 ──────────────────────────────────────────────
WINE = '/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine'
WINEPREFIX = os.path.expanduser('~/Library/Application Support/net.metaquotes.wine.metatrader5')
MT5_MAIN = os.path.join(WINEPREFIX, 'drive_c/Program Files/MetaTrader 5')
INI_DIR = os.path.join(WINEPREFIX, 'drive_c/bt')
REPORT_DIR = os.path.join(WINEPREFIX, 'drive_c/bt/reports')


def generate_set_file(strategy_name, config):
    set_dir = Path(MT5_MAIN) / 'MQL5' / 'Profiles' / 'Tester'
    return write_set_file(strategy_name, config, set_dir)


def expert_ex5_path(mt5_root, expert):
    """将 MT5 Expert 名称转换为本机 .ex5 路径。"""
    return Path(mt5_root) / 'MQL5' / 'Experts' / Path(*expert.split('\\')).with_suffix('.ex5')


def generate_ini(strategy_name, symbol, date_from, date_to, config):
    strategy_cfg = config[strategy_name]
    defaults = config.get('backtest_defaults', {})
    account = config.get('mt5_account', {})

    period = strategy_cfg.get('period', defaults.get('period', 'M5'))
    model = strategy_cfg.get('model', defaults.get('model', '1'))
    deposit = strategy_cfg.get('deposit', defaults.get('deposit', 200))
    currency = strategy_cfg.get('currency', defaults.get('currency', 'USD'))
    leverage = strategy_cfg.get('leverage', defaults.get('leverage', '1:2000'))
    expert = strategy_cfg.get('expert', defaults.get('expert', r'WaiTrade2\WaiTrade_OB'))

    login = account.get('login', '')
    server = account.get('server', '')
    proxy_enable = account.get('proxy_enable', 1)
    proxy_type = account.get('proxy_type', 0)
    proxy_address = account.get('proxy_address', '127.0.0.1:7897')

    if isinstance(leverage, str) and ':' in leverage:
        leverage = leverage.split(':')[-1]

    today_str = datetime.now().strftime('%Y%m%d')
    report_name = f'{strategy_name}_{symbol}_{today_str}'

    ini_content = f"""; WaiTrade2 {strategy_name} / {symbol} 回测
[Common]
Login={login}
Server={server}
ProxyEnable={proxy_enable}
ProxyType={proxy_type}
ProxyAddress={proxy_address}

[Tester]
Expert={expert}
ExpertParameters={strategy_name}.set
Symbol={symbol}
Period={period}
Model={model}
Optimization=0
DateFrom={date_from}
DateTo={date_to}
Deposit={deposit}
Leverage={leverage}
ExecutionMode=0
ShutdownTerminal=1
Report=C:\\bt\\reports\\{report_name}
"""

    os.makedirs(INI_DIR, exist_ok=True)
    ini_path = os.path.join(INI_DIR, 'backtest.ini')
    with open(ini_path, 'w', encoding='utf-8') as f:
        f.write(ini_content)

    mt5_config_ini = os.path.join(MT5_MAIN, 'config', 'backtest.ini')
    with open(mt5_config_ini, 'w', encoding='utf-8') as f:
        f.write(ini_content)

    print(f'  INI 文件已写入: {ini_path}')
    return ini_path


def kill_mt5():
    env = os.environ.copy()
    env['WINEPREFIX'] = WINEPREFIX
    subprocess.run(['pkill', '-f', 'terminal64'], capture_output=True)
    subprocess.run(['pkill', '-f', 'metatester64'], capture_output=True)
    subprocess.run(['pkill', '-f', 'MetaTrader 5.app'], capture_output=True)
    wineserver = WINE.replace('/wine', '/wineserver')
    subprocess.run([wineserver, '-k'], env=env, capture_output=True)
    time.sleep(3)


def clear_tester_cache():
    """清空Tester缓存并更新terminal.ini中的日期"""
    import shutil
    cache_dir = Path(MT5_MAIN) / 'Tester' / 'cache'
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        cache_dir.mkdir()


def patch_terminal_ini_dates(date_from_str, date_to_str):
    """覆盖terminal.ini中[Tester]段的DateFrom/DateTo(Unix时间戳)
    MT5忽略backtest.ini的日期，只读terminal.ini的缓存值。
    """
    from calendar import timegm
    import re as re_mod

    d_from = datetime.strptime(date_from_str, '%Y.%m.%d')
    d_to = datetime.strptime(date_to_str, '%Y.%m.%d')
    ts_from = int(timegm(d_from.timetuple()))
    ts_to = int(timegm(d_to.timetuple()))

    ini_path = Path(MT5_MAIN) / 'config' / 'terminal.ini'
    if not ini_path.exists():
        return

    content = ini_path.read_bytes().decode('utf-16-le', errors='replace')

    content = re_mod.sub(r'(DateFrom=)\d+', f'\\g<1>{ts_from}', content)
    content = re_mod.sub(r'(DateTo=)\d+', f'\\g<1>{ts_to}', content)
    content = re_mod.sub(r'(DateRange=)\d+', '\\g<1>3', content)

    ini_path.write_bytes(content.encode('utf-16-le'))
    print(f'  已更新terminal.ini日期: {date_from_str}~{date_to_str}')


def run_mt5(timeout_sec=300):
    env = os.environ.copy()
    env['WINEPREFIX'] = WINEPREFIX

    kill_mt5()
    clear_tester_cache()

    cmd = [
        WINE,
        r'C:\Program Files\MetaTrader 5\terminal64.exe',
        r'/config:C:\\bt\\backtest.ini',
    ]

    print(f'  启动回测 (超时 {timeout_sec}s)...', end='', flush=True)
    start = time.time()
    try:
        subprocess.run(
            cmd, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=timeout_sec
        )
        elapsed = time.time() - start
        wait_for_mt5_shutdown(timeout_sec, start)
        elapsed = time.time() - start
        print(f' 完成 ({elapsed:.0f}s)')
        return True
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f'\n  [超时] {elapsed:.0f}s')
        kill_mt5()
        return False


def is_mt5_testing_running():
    """Wine 下 terminal64 有时会先返回，需等实际 tester 进程退出。"""
    patterns = [r'[t]erminal64.exe /config:', r'[m]etatester64.exe']
    for pattern in patterns:
        result = subprocess.run(['pgrep', '-f', pattern], capture_output=True)
        if result.returncode == 0:
            return True
    return False


def wait_for_mt5_shutdown(timeout_sec, start_time):
    while is_mt5_testing_running():
        if time.time() - start_time > timeout_sec:
            raise subprocess.TimeoutExpired('terminal64.exe', timeout_sec)
        time.sleep(2)


def parse_agent_log():
    today_str = datetime.now().strftime('%Y%m%d')
    log_paths = [
        Path(MT5_MAIN) / 'Tester' / 'Agent-127.0.0.1-3000' / 'logs' / f'{today_str}.log',
        Path(MT5_MAIN) / 'Tester' / 'logs' / f'{today_str}.log',
    ]
    existing = [p for p in log_paths if p.exists()]

    if not existing:
        print(f'  [警告] Tester 日志不存在: {log_paths[0]} / {log_paths[1]}')
        return None

    log_path = max(existing, key=lambda p: p.stat().st_mtime)
    try:
        with open(log_path, 'r', encoding='utf-16-le') as f:
            content = f.read()
    except Exception as e:
        print(f'  [错误] 读取日志失败: {e}')
        return None

    return parse_agent_log_content(content)


def run_backtest(strategy_name, symbols, date_from, date_to, days, config, timeout):
    strategy_cfg = config[strategy_name]
    defaults = config.get('backtest_defaults', {})
    deposit = strategy_cfg.get('deposit', defaults.get('deposit', 200))
    leverage = strategy_cfg.get('leverage', defaults.get('leverage', '2000'))
    if isinstance(leverage, str) and ':' in leverage:
        leverage = leverage.split(':')[-1]

    print(f'\n策略: {strategy_name} | 品种数: {len(symbols)} | 周期: {date_from} ~ {date_to}')
    print('=' * 60)

    expert = strategy_cfg.get('expert', defaults.get('expert', r'WaiTrade2\WaiTrade_OB'))
    expert_path = expert_ex5_path(MT5_MAIN, expert)
    if not expert_path.exists():
        print(f'[警告] EA 文件不存在: {expert_path}')

    generate_set_file(strategy_name, config)

    symbol_results = {}
    for i, symbol in enumerate(symbols, 1):
        print(f'\n[{i}/{len(symbols)}] 回测 {symbol}')
        generate_ini(strategy_name, symbol, date_from, date_to, config)
        patch_terminal_ini_dates(date_from, date_to)
        success = run_mt5(timeout_sec=timeout)

        if success:
            result = parse_agent_log()
            stats = calc_stats(result, deposit, days)
            symbol_results[symbol] = stats
            if stats:
                print(f'  结果: {stats["trades"]}笔交易, 胜率{stats["win_rate"]:.1f}%, 余额${stats["final_balance"]:.2f}')
            else:
                print('  [警告] 未能解析回测结果')
        else:
            symbol_results[symbol] = None

    report = format_report(strategy_name, date_from, date_to, days, deposit, leverage, symbol_results)
    print(report)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime('%Y%m%d')
    report_path = RESULTS_DIR / f'{strategy_name}_{today_str}.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'\n报告已保存: {report_path}')

    return symbol_results


def _run(strategy_names, symbols, date_from, date_to, days, config, timeout):
    print(f'MT5 回测管理器')
    os.makedirs(REPORT_DIR, exist_ok=True)
    for name in strategy_names:
        run_backtest(name, symbols, date_from, date_to, days, config, timeout)
    kill_mt5()
    print('\n全部回测完成。')


def main():
    backtest_main('MT5 Strategy Tester 回测管理器（Wine/macOS）', _run)


if __name__ == '__main__':
    main()
