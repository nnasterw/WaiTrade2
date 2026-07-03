#!/usr/bin/env python3
"""MT5 Strategy Tester 回测管理器 — Windows 原生版本"""

import ctypes
import html
import os
import re
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
DEFAULT_PORTABLE_HOME = ROOT / 'temp' / 'mt5_portable_bt'
DEFAULT_MT5_HOME = DEFAULT_PORTABLE_HOME if (DEFAULT_PORTABLE_HOME / 'terminal64.exe').exists() else Path(r'C:\Program Files\MetaTrader 5')
MT5_HOME = Path(os.environ.get('MT5_HOME', str(DEFAULT_MT5_HOME)))
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_PORTABLE = os.environ.get(
    'MT5_PORTABLE',
    '1' if MT5_HOME.resolve() == DEFAULT_PORTABLE_HOME.resolve() else '',
).lower() in ('1', 'true', 'yes', 'on')
MT5_REQUIRE_ADMIN = os.environ.get(
    'MT5_REQUIRE_ADMIN',
    '0' if MT5_PORTABLE else '1',
).lower() in ('1', 'true', 'yes', 'on')
if MT5_PORTABLE:
    MT5_DATA = Path(os.environ.get('MT5_DATA', str(MT5_HOME)))
else:
    MT5_DATA = Path(os.environ.get(
        'MT5_DATA',
        os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
    ))
MT5_TESTER_PROFILES = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
MT5_EXPERTS = MT5_DATA / 'MQL5' / 'Experts'
MT5_TESTER_DIR = MT5_DATA / 'Tester'

INI_DIR = MT5_HOME if MT5_PORTABLE else MT5_TESTER_DIR
REPORT_DIR = MT5_DATA if MT5_PORTABLE else MT5_TESTER_DIR
LAST_REPORT_NAME = None


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
    global LAST_REPORT_NAME
    strategy_cfg = config[strategy_name]
    defaults = config.get('backtest_defaults', {})
    account = config.get('mt5_account', {})

    period = strategy_cfg.get('period', defaults.get('period', 'M5'))
    model = strategy_cfg.get('model', defaults.get('model', '1'))
    deposit = strategy_cfg.get('deposit', defaults.get('deposit', 200))
    currency = strategy_cfg.get('currency', defaults.get('currency', 'USD'))
    leverage = strategy_cfg.get('leverage', defaults.get('leverage', '1:2000'))
    expert = strategy_cfg.get('expert', defaults.get('expert', r'WaiTrade2\WaiTrade_OB'))

    proxy_enable = account.get('proxy_enable', 1)
    proxy_type = account.get('proxy_type', 0)
    proxy_address = account.get('proxy_address', '127.0.0.1:7897')

    if isinstance(leverage, str) and ':' in leverage:
        leverage = leverage.split(':')[-1]

    today_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_name = f'{strategy_name}_{symbol}_{today_str}'
    LAST_REPORT_NAME = report_name

    os.makedirs(INI_DIR, exist_ok=True)

    ini_content = f"""; WaiTrade2 {strategy_name} / {symbol} 回测
[Common]
; 回测不登录Live账号, 避免踢掉线上终端
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

    ini_path = INI_DIR / ('bt.ini' if MT5_PORTABLE else 'backtest.ini')
    with open(ini_path, 'w', encoding='utf-8') as f:
        f.write(ini_content)
    print(f'  INI 文件已写入: {ini_path}')
    return ini_path


def is_admin():
    """检查当前进程是否以管理员权限运行（Win11 26200 + MT5 5836 必须Admin才能启动IPC dispatcher）"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def clear_tester_cache():
    import shutil
    cache_dir = MT5_TESTER_DIR / 'cache'
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        cache_dir.mkdir()


def _ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def kill_mt5():
    """只停止当前 tester home 下的 MT5 进程，避免误杀 Live portable。"""
    cmd = (
        f"$root = [System.IO.Path]::GetFullPath({_ps_quote(MT5_HOME)}).TrimEnd('\\') + '\\'; "
        "Get-CimInstance Win32_Process -Filter \"name='terminal64.exe' or name='metatester64.exe'\" | "
        "Where-Object { $_.ExecutablePath -and "
        "$_.ExecutablePath.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase) } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)
    time.sleep(2)


def _mt5_config_arg(ini_path):
    ini_path = Path(ini_path)
    if MT5_PORTABLE and ini_path.parent.resolve() == MT5_HOME.resolve():
        return f'/config:{ini_path.name}'
    return f'/config:{ini_path}'


def _mt5_argument_list(ini_path):
    args = []
    if MT5_PORTABLE:
        args.append('/portable')
    args.append(_mt5_config_arg(ini_path))
    return args


def _ps_array(values):
    return '@(' + ','.join(_ps_quote(v) for v in values) + ')'


def run_mt5(timeout_sec=300):
    kill_mt5()
    clear_tester_cache()

    ini_path = INI_DIR / ('bt.ini' if MT5_PORTABLE else 'backtest.ini')
    mt5_args = _mt5_argument_list(ini_path)
    start_time = time.time()

    if MT5_REQUIRE_ADMIN and not is_admin():
        # Win11 26200 + MT5 5836: 非Admin下IPC dispatcher无法启动
        # 通过PowerShell Start-Process -Verb RunAs 提权运行
        print(f'  启动 MT5 回测 (Admin提权, 超时 {timeout_sec}s, 可能需要点UAC确认)...')
        print(f'  [提示] 也可用管理员终端运行本脚本以跳过UAC弹窗', flush=True)

        ps_cmd = (
            f'$p = Start-Process -FilePath "{MT5_TERMINAL}" '
            f'-ArgumentList {_ps_array(mt5_args)} '
            f'-WorkingDirectory "{MT5_HOME}" '
            f'-Wait -PassThru -WindowStyle Minimized -Verb RunAs; '
            f'exit $p.ExitCode'
        )

        proc = subprocess.Popen(
            ['powershell', '-NoProfile', '-Command', ps_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        try:
            stdout, stderr = proc.communicate(timeout=timeout_sec + 30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            print(f'\n  [超时] MT5 运行超过 {timeout_sec}s，已终止')
            return False

        elapsed = time.time() - start_time
        print(f'  MT5 已退出 (Admin提权, 耗时 {elapsed:.0f}s, 返回码 {proc.returncode})')
        return proc.returncode == 0

    # 已是Admin：直接运行
    print(f'  启动 MT5 回测 (超时 {timeout_sec}s)...', end='', flush=True)

    proc = subprocess.Popen(
        [MT5_TERMINAL, *mt5_args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(MT5_HOME),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
    )
    while proc.poll() is None:
        elapsed = time.time() - start_time
        if elapsed > timeout_sec:
            proc.kill()
            print(f'\n  [超时] MT5 运行超过 {timeout_sec}s，已终止')
            return False
        if int(elapsed) % 10 == 0:
            print('.', end='', flush=True)
        time.sleep(2)

    elapsed = time.time() - start_time
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


def _expected_log_markers(strategy_cfg):
    version = strategy_cfg.get('version') if isinstance(strategy_cfg, dict) else None
    return [str(version)] if version else []


def _parse_matching_result(content, symbol=None, date_from=None, date_to=None, expected_markers=None):
    if not content or not (symbol and date_from and date_to):
        return None

    segment = find_matching_log_segment(
        content,
        symbol,
        date_from,
        date_to,
        expected_markers=expected_markers,
    )
    if segment is None:
        return None
    return parse_agent_log_content('\n'.join(segment['lines']))


def find_report_file(report_name):
    if not report_name:
        return None
    candidates = [
        REPORT_DIR / f'{report_name}.htm',
        MT5_DATA / f'{report_name}.htm',
        MT5_TESTER_DIR / f'{report_name}.htm',
        MT5_HOME / f'{report_name}.htm',
    ]
    for path in candidates:
        if path.exists() and path.stat().st_size > 1000:
            return path
    return None


def parse_html_report_stats(path, deposit, days):
    """从 MT5 HTML 报告兜底解析成交汇总，防止日志路径变化导致误报失败。"""
    if not path or not Path(path).exists():
        return None
    raw = Path(path).read_bytes()
    try:
        content = raw.decode('utf-16-le')
    except UnicodeDecodeError:
        content = raw.decode('utf-16-le', errors='replace')

    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', content, re.DOTALL | re.IGNORECASE)
    trades = []
    pending = 0
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
        cells = [html.unescape(re.sub(r'<[^>]+>', '', cell)).strip() for cell in cells]
        if len(cells) != 13:
            continue
        if cells[3].lower() == 'balance':
            continue
        io = cells[4].lower()
        try:
            pnl = float(cells[10].replace(' ', '').replace(',', ''))
        except ValueError:
            pnl = 0.0
        if io == 'in':
            pending += 1
        elif io == 'out' and pending > 0:
            pending -= 1
            trades.append(pnl)

    if not trades:
        return None

    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    final_balance = deposit + sum(trades)
    return {
        'trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': len(wins) / len(trades) * 100 if trades else 0,
        'profit_factor': gross_profit / gross_loss if gross_loss > 0 else float('inf'),
        'daily_trades': len(trades) / days if days > 0 else 0,
        'final_balance': final_balance,
        'profit': final_balance - deposit,
        'net_r': None,
    }


def parse_agent_log(symbol=None, date_from=None, date_to=None, log_offsets=None, expected_markers=None):
    log_paths = get_tester_log_paths()
    existing = [p for p in log_paths if p.exists()]

    if not existing:
        return None if expected_markers else read_agent_log(AGENT_LOG_DIR)

    ordered_paths = sorted(existing, key=lambda p: p.stat().st_mtime, reverse=True)

    for use_offsets in (True, False):
        for log_path in ordered_paths:
            offset = log_offsets.get(log_path, 0) if use_offsets and log_offsets else 0
            try:
                content = _read_utf16_log(log_path, offset=offset)
            except MemoryError:
                print(f'  [警告] Agent 日志过大，跳过日志解析: {log_path}')
                continue
            result = _parse_matching_result(
                content,
                symbol=symbol,
                date_from=date_from,
                date_to=date_to,
                expected_markers=expected_markers,
            )
            if result is not None:
                return result

    if not expected_markers:
        for use_offsets in (True, False):
            for log_path in ordered_paths:
                offset = log_offsets.get(log_path, 0) if use_offsets and log_offsets else 0
                try:
                    content = _read_utf16_log(log_path, offset=offset)
                except MemoryError:
                    print(f'  [警告] Agent 日志过大，跳过日志解析: {log_path}')
                    continue
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
    expected_markers = _expected_log_markers(strategy_cfg)
    defaults = config.get('backtest_defaults', {})
    deposit = strategy_cfg.get('deposit', defaults.get('deposit', 200))
    leverage = strategy_cfg.get('leverage', defaults.get('leverage', '2000'))
    model = strategy_cfg.get('model', defaults.get('model', '1'))
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
            try:
                result = parse_agent_log(
                    symbol=symbol,
                    date_from=date_from,
                    date_to=date_to,
                    expected_markers=expected_markers,
                )
            except MemoryError:
                print('  [警告] Agent 日志解析内存不足，改用 HTML 报告兜底')
                result = None
            stats = calc_stats(result, deposit, days)
            if stats is None:
                report_file = find_report_file(LAST_REPORT_NAME)
                if report_file:
                    stats = parse_html_report_stats(report_file, deposit, days)
                    if stats:
                        print(f'  [HTML兜底] 已从报告解析结果: {report_file}')
            symbol_results[symbol] = stats
            if stats:
                print(f'  结果: {stats["trades"]}笔交易, 胜率{stats["win_rate"]:.1f}%, 余额${stats["final_balance"]:.2f}')
            else:
                print('  [警告] 未能解析回测结果')
        else:
            symbol_results[symbol] = None

    report = format_report(strategy_name, date_from, date_to, days, deposit, leverage, symbol_results, model=model)
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
