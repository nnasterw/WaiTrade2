#!/usr/bin/env python3
"""MT5 Strategy Tester 回测管理器 — Windows 原生版本"""

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
    calc_stats, format_report, RESULTS_DIR,
    write_set_file, read_agent_log, backtest_main,
    parse_agent_log_content, find_matching_log_segment,
)

# ── Windows MT5 路径常量 ──────────────────────────────────────────────
MT5_HOME = Path(os.environ.get('MT5_HOME', r'C:\Program Files\MetaTrader 5'))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.environ.get(
    'MT5_DATA',
    os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
))
MT5_TESTER_PROFILES = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
MT5_EXPERTS = MT5_DATA / 'MQL5' / 'Experts'
MT5_TESTER_DIR = MT5_DATA / 'Tester'

INI_DIR = MT5_TESTER_DIR
REPORT_DIR = MT5_TESTER_DIR


def ensure_mt5_dirs():
    dirs = [
        MT5_DATA / 'MQL5' / 'Profiles' / 'Tester',
        MT5_DATA / 'MQL5' / 'Experts',
        MT5_DATA / 'Tester',
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def generate_set_file(strategy_name, config):
    ensure_mt5_dirs()
    return write_set_file(strategy_name, config, MT5_TESTER_PROFILES)


def expert_ex5_path(experts_root, expert):
    """将 MT5 Expert 名称转换为本机 .ex5 路径。"""
    return Path(experts_root) / Path(*expert.split('\\')).with_suffix('.ex5')


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

    os.makedirs(INI_DIR, exist_ok=True)

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
FromDate={date_from}
ToDate={date_to}
Deposit={deposit}
Currency={currency}
Leverage={leverage}
ExecutionMode=0
ShutdownTerminal=1
Report={report_name}
"""

    ini_path = INI_DIR / 'backtest.ini'
    with open(ini_path, 'w', encoding='utf-8') as f:
        f.write(ini_content)
    print(f'  INI 文件已写入: {ini_path}')
    return ini_path


def kill_mt5():
    subprocess.run(
        ['taskkill', '/F', '/IM', 'terminal64.exe'],
        capture_output=True,
    )
    subprocess.run(
        ['taskkill', '/F', '/IM', 'metatester64.exe'],
        capture_output=True,
    )
    time.sleep(3)


def clear_tester_cache():
    import shutil
    cache_dir = MT5_TESTER_DIR / 'cache'
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        cache_dir.mkdir()


def run_mt5(timeout_sec=300):
    kill_mt5()
    clear_tester_cache()

    ini_path = INI_DIR / 'backtest.ini'
    config_arg = f'/config:{ini_path}'

    cmd = [MT5_TERMINAL, config_arg]

    print(f'  启动 MT5 回测 (超时 {timeout_sec}s)...', end='', flush=True)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
    )

    start = time.time()
    while proc.poll() is None:
        elapsed = time.time() - start
        if elapsed > timeout_sec:
            proc.kill()
            print(f'\n  [超时] MT5 运行超过 {timeout_sec}s，已终止')
            return False
        if int(elapsed) % 10 == 0:
            print('.', end='', flush=True)
        time.sleep(2)

    elapsed = time.time() - start
    print(f'\n  MT5 已退出 (耗时 {elapsed:.0f}s, 返回码 {proc.returncode})')
    return proc.returncode == 0


AGENT_LOG_DIR = MT5_DATA / 'Tester' / 'Agent-127.0.0.1-3000' / 'logs'
TESTER_LOG_DIRS = [
    AGENT_LOG_DIR,
    MT5_DATA / 'Tester' / 'logs',
]


def get_tester_log_paths(now=None):
    current_time = now or datetime.now()
    today_str = current_time.strftime('%Y%m%d')
    return [Path(log_dir) / f'{today_str}.log' for log_dir in TESTER_LOG_DIRS]


def _read_utf16_log(path, offset=0):
    try:
        raw = path.read_bytes()
    except Exception as e:
        print(f'  [错误] 读取日志失败: {e}')
        return None

    if offset and 0 <= offset < len(raw):
        if offset % 2 != 0:
            offset -= 1
        raw = raw[offset:]

    try:
        return raw.decode('utf-16-le')
    except UnicodeDecodeError:
        return raw.decode('utf-16-le', errors='ignore')


def _parse_matching_result(content, symbol=None, date_from=None, date_to=None):
    if not content or not (symbol and date_from and date_to):
        return None

    segment = find_matching_log_segment(content, symbol, date_from, date_to)
    if segment is None:
        return None
    return parse_agent_log_content('\n'.join(segment['lines']))


def parse_agent_log(symbol=None, date_from=None, date_to=None, log_offsets=None):
    log_paths = get_tester_log_paths()
    existing = [p for p in log_paths if p.exists()]

    if not existing:
        return read_agent_log(AGENT_LOG_DIR)

    ordered_paths = sorted(existing, key=lambda p: p.stat().st_mtime, reverse=True)

    for use_offsets in (True, False):
        for log_path in ordered_paths:
            offset = log_offsets.get(log_path, 0) if use_offsets and log_offsets else 0
            content = _read_utf16_log(log_path, offset=offset)
            result = _parse_matching_result(content, symbol=symbol, date_from=date_from, date_to=date_to)
            if result is not None:
                return result

    for use_offsets in (True, False):
        for log_path in ordered_paths:
            offset = log_offsets.get(log_path, 0) if use_offsets and log_offsets else 0
            content = _read_utf16_log(log_path, offset=offset)
            result = parse_agent_log_content(content) if content else None
            if result is not None:
                return result

    return None


def build_report_path(strategy_name, date_from, date_to, now=None):
    current_time = now or datetime.now()
    today_str = current_time.strftime('%Y%m%d')
    return RESULTS_DIR / f'{strategy_name}_{date_from.replace(".", "")}_{date_to.replace(".", "")}_{today_str}.txt'


def run_backtest(strategy_name, symbols, date_from, date_to, days, config, timeout):
    strategy_cfg = config[strategy_name]
    defaults = config.get('backtest_defaults', {})
    deposit = strategy_cfg.get('deposit', defaults.get('deposit', 200))
    leverage = strategy_cfg.get('leverage', defaults.get('leverage', '2000'))
    if isinstance(leverage, str) and ':' in leverage:
        leverage = leverage.split(':')[-1]

    expert = strategy_cfg.get('expert', defaults.get('expert', r'WaiTrade2\WaiTrade_OB'))
    expert_path = expert_ex5_path(MT5_EXPERTS, expert)
    if not expert_path.exists():
        print(f'[警告] EA 文件不存在: {expert_path}')

    print(f'\n策略: {strategy_name} | 品种数: {len(symbols)} | 周期: {date_from} ~ {date_to}')
    print('=' * 60)

    generate_set_file(strategy_name, config)

    symbol_results = {}
    for i, symbol in enumerate(symbols, 1):
        print(f'\n[{i}/{len(symbols)}] 回测 {symbol}')
        generate_ini(strategy_name, symbol, date_from, date_to, config)
        success = run_mt5(timeout_sec=timeout)

        if success:
            result = parse_agent_log(symbol=symbol, date_from=date_from, date_to=date_to)
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
    report_path = build_report_path(strategy_name, date_from, date_to)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'\n报告已保存: {report_path}')

    return symbol_results


def _run(strategy_names, symbols, date_from, date_to, days, config, timeout):
    print(f'MT5 回测管理器 (Windows)')
    for name in strategy_names:
        run_backtest(name, symbols, date_from, date_to, days, config, timeout)
    print('\n全部回测完成。')


def main():
    backtest_main('MT5 Strategy Tester 回测管理器（Windows）', _run)


if __name__ == '__main__':
    main()
