#!/usr/bin/env python3
"""MT5 Strategy Tester 回测管理器 — 通过 Wine 在 macOS 上运行 MT5 回测"""

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import yaml_to_set

# ── Wine / MT5 路径常量 ──────────────────────────────────────────────
WINE = '/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine'
WINEPREFIX = os.path.expanduser('~/Library/Application Support/net.metaquotes.wine.metatrader5')
MT5_MAIN = os.path.join(WINEPREFIX, 'drive_c/Program Files/MetaTrader 5')
INI_DIR = os.path.join(WINEPREFIX, 'drive_c/bt')
REPORT_DIR = os.path.join(WINEPREFIX, 'drive_c/bt/reports')

CONFIG_PATH = ROOT / 'config' / 'strategies.yaml'
RESULTS_DIR = ROOT / 'results' / 'backtest'


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def resolve_symbols(config, symbol_arg):
    """解析 --symbol/--symbols 参数，返回品种列表"""
    if symbol_arg.lower() == 'all':
        symbols = []
        for category in config.get('symbols', {}).values():
            if isinstance(category, list):
                symbols.extend(category)
        return symbols
    return [s.strip() for s in symbol_arg.split(',')]


def resolve_strategies(config, strategy_arg):
    """解析 --strategy/--strategies 参数，返回策略名列表"""
    names = [s.strip() for s in strategy_arg.split(',')]
    non_strategy_keys = {'defaults', 'symbols', 'backtest_defaults', 'mt5_account'}
    available = [k for k in config if k not in non_strategy_keys and isinstance(config[k], dict)]
    for name in names:
        if name not in available:
            print(f'[错误] 策略 {name} 在 strategies.yaml 中不存在，可用: {", ".join(available)}')
            sys.exit(1)
    return names


def generate_set_file(strategy_name, config):
    """生成 .set 文件并写入 MT5 Tester 目录"""
    strategy_cfg = config[strategy_name]
    content = yaml_to_set.strategy_to_set(strategy_name, strategy_cfg)
    set_dir = Path(MT5_MAIN) / 'MQL5' / 'Profiles' / 'Tester'
    set_dir.mkdir(parents=True, exist_ok=True)
    set_path = set_dir / f'{strategy_name}.set'
    with open(set_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  .set 文件已写入: {set_path.name}')
    return set_path


def generate_ini(strategy_name, symbol, date_from, date_to, config):
    """生成回测 INI 文件"""
    strategy_cfg = config[strategy_name]
    defaults = config.get('backtest_defaults', {})
    account = config.get('mt5_account', {})

    period = strategy_cfg.get('period', defaults.get('period', 'M5'))
    model = strategy_cfg.get('model', defaults.get('model', '1'))
    deposit = strategy_cfg.get('deposit', defaults.get('deposit', 200))
    currency = strategy_cfg.get('currency', defaults.get('currency', 'USD'))
    leverage = strategy_cfg.get('leverage', defaults.get('leverage', '1:2000'))
    expert = strategy_cfg.get('expert', defaults.get('expert', r'WaiTrade\WaiTrade_OB'))

    login = account.get('login', '')
    server = account.get('server', '')
    proxy_enable = account.get('proxy_enable', 1)
    proxy_type = account.get('proxy_type', 0)
    proxy_address = account.get('proxy_address', '127.0.0.1:7897')

    if isinstance(leverage, str) and ':' in leverage:
        leverage = leverage.split(':')[-1]

    today_str = datetime.now().strftime('%Y%m%d')
    report_name = f'{strategy_name}_{symbol}_{today_str}'

    ini_content = f"""[Common]
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
DateFrom={date_from}
DateTo={date_to}
Deposit={deposit}
Currency={currency}
Leverage={leverage}
ExecutionMode=0
ShutdownTerminal=1
Visual=0
Optimization=0
Report=C:\\bt\\reports\\{report_name}
ReplaceReport=1
"""

    os.makedirs(INI_DIR, exist_ok=True)
    ini_path = os.path.join(INI_DIR, 'backtest.ini')
    with open(ini_path, 'w', encoding='utf-8') as f:
        f.write(ini_content)
    print(f'  INI 文件已写入: {ini_path}')
    return ini_path


def run_mt5(timeout_sec=300):
    """通过 Wine 启动 MT5 并等待回测完成"""
    env = os.environ.copy()
    env['WINEPREFIX'] = WINEPREFIX

    cmd = [
        WINE,
        r'C:\Program Files\MetaTrader 5\terminal64.exe',
        r'/config:C:\\bt\\backtest.ini',
    ]

    print(f'  启动 MT5 回测 (超时 {timeout_sec}s)...', end='', flush=True)
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    start = time.time()
    while proc.poll() is None:
        elapsed = time.time() - start
        if elapsed > timeout_sec:
            proc.kill()
            print(f'\n  [超时] MT5 运行超过 {timeout_sec}s，已终止')
            return False
        print('.', end='', flush=True)
        time.sleep(3)

    elapsed = time.time() - start
    print(f'\n  MT5 已退出 (耗时 {elapsed:.0f}s, 返回码 {proc.returncode})')
    return True


def parse_agent_log():
    """解析 Tester Agent 日志，提取回测结果"""
    today_str = datetime.now().strftime('%Y%m%d')
    log_path = Path(MT5_MAIN) / 'Tester' / 'Agent-127.0.0.1-3000' / 'logs' / f'{today_str}.log'

    if not log_path.exists():
        print(f'  [警告] Agent 日志不存在: {log_path}')
        return None

    try:
        with open(log_path, 'r', encoding='utf-16-le') as f:
            content = f.read()
    except Exception as e:
        print(f'  [错误] 读取日志失败: {e}')
        return None

    lines = content.splitlines()

    segments = []
    current = []
    for line in lines:
        if 'testing of' in line.lower():
            if current:
                segments.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        segments.append(current)

    if not segments:
        print('  [警告] 日志中未找到测试记录')
        return None

    last_segment = segments[-1]

    result = {
        'trades': 0,
        'wins': 0,
        'losses': 0,
        'final_balance': None,
        'deals': [],
        'ticks': None,
        'bars': None,
    }

    deal_pattern = re.compile(
        r'deal #(\d+)\s+(buy|sell)\s+([\d.]+)\s+(\S+)\s+at\s+([\d.]+)'
        r'(?:\s+sl:\s*([\d.]+))?(?:\s+tp:\s*([\d.]+))?'
    )
    balance_pattern = re.compile(r'final balance\s+([\d.]+)')
    ticks_pattern = re.compile(r'(\d+)\s+ticks.*?(\d+)\s+bars')

    for line in last_segment:
        m = deal_pattern.search(line)
        if m:
            deal = {
                'ticket': int(m.group(1)),
                'direction': m.group(2),
                'lots': float(m.group(3)),
                'symbol': m.group(4),
                'price': float(m.group(5)),
                'sl': float(m.group(6)) if m.group(6) else None,
                'tp': float(m.group(7)) if m.group(7) else None,
            }
            result['deals'].append(deal)

        m = balance_pattern.search(line)
        if m:
            result['final_balance'] = float(m.group(1))

        m = ticks_pattern.search(line)
        if m:
            result['ticks'] = int(m.group(1))
            result['bars'] = int(m.group(2))

    deals = result['deals']
    if len(deals) >= 2:
        result['trades'] = len(deals) // 2

    return result


def calc_stats(result, deposit, days):
    """从解析结果计算统计指标"""
    if not result:
        return None

    trades = result['trades']
    final_balance = result['final_balance'] or deposit
    profit = final_balance - deposit

    deals = result['deals']
    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0
    r_total = 0.0
    r_count = 0

    for i in range(0, len(deals) - 1, 2):
        entry = deals[i]
        exit_deal = deals[i + 1]

        if entry['direction'] == 'buy':
            pnl = exit_deal['price'] - entry['price']
        else:
            pnl = entry['price'] - exit_deal['price']

        if pnl > 0:
            wins += 1
            gross_profit += pnl * entry['lots']
        else:
            losses += 1
            gross_loss += abs(pnl) * entry['lots']

        if entry['sl'] is not None and entry['sl'] != 0:
            risk = abs(entry['price'] - entry['sl'])
            if risk > 0:
                r = pnl / risk
                r_total += r
                r_count += 1

    win_rate = (wins / trades * 100) if trades > 0 else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
    daily_trades = trades / days if days > 0 else 0
    net_r = r_total if r_count > 0 else None

    return {
        'trades': trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'daily_trades': daily_trades,
        'final_balance': final_balance,
        'profit': profit,
        'net_r': net_r,
    }


def format_report(strategy_name, date_from, date_to, days, deposit, leverage, symbol_results):
    """格式化回测报告"""
    header = f"""
=====================================================================
MT5 Strategy Tester 回测报告 — {strategy_name.upper()}
日期: {date_from} ~ {date_to} ({days}天) | 资金: ${deposit} | 杠杆: 1:{leverage}
=====================================================================

品种         交易  日均  胜率   盈亏比  净R     余额
---------------------------------------------------------------------"""

    lines = [header]
    total_trades = 0
    total_wins = 0
    total_losses = 0
    total_balance = 0
    total_r = 0.0
    r_count = 0

    for symbol, stats in symbol_results.items():
        if stats is None:
            lines.append(f'{symbol:<13}回测失败或无数据')
            continue

        t = stats['trades']
        d = stats['daily_trades']
        w = stats['win_rate']
        pf = stats['profit_factor']
        bal = stats['final_balance']
        nr = stats['net_r']

        nr_str = f"+{nr:.1f}" if nr is not None and nr >= 0 else (f"{nr:.1f}" if nr is not None else 'N/A')
        pf_str = f"{pf:.2f}" if pf != float('inf') else 'inf'

        lines.append(f'{symbol:<13}{t:<6}{d:<6.1f}{w:<7.1f}%{pf_str:<8}{nr_str:<8}${bal:.2f}')

        total_trades += t
        total_wins += stats['wins']
        total_losses += stats['losses']
        total_balance += bal
        if nr is not None:
            total_r += nr
            r_count += 1

    lines.append('---------------------------------------------------------------------')

    if total_trades > 0:
        total_wr = total_wins / total_trades * 100
        total_daily = total_trades / days if days > 0 else 0
        total_gp = sum(s['wins'] for s in symbol_results.values() if s)
        total_gl = sum(s['losses'] for s in symbol_results.values() if s)
        total_pf_str = 'N/A'
        total_nr_str = f"+{total_r:.1f}" if total_r >= 0 else f"{total_r:.1f}"
        if r_count == 0:
            total_nr_str = 'N/A'

        lines.append(
            f'{"合计":<12}{total_trades:<6}{total_daily:<6.1f}{total_wr:<7.1f}%{"":<8}{total_nr_str:<8}'
            f'${total_balance:.2f}'
        )

    lines.append('=====================================================================')
    return '\n'.join(lines)


def run_backtest(strategy_name, symbols, date_from, date_to, days, config, timeout):
    """对一个策略执行完整回测流程"""
    strategy_cfg = config[strategy_name]
    defaults = config.get('backtest_defaults', {})
    deposit = strategy_cfg.get('deposit', defaults.get('deposit', 200))
    leverage = strategy_cfg.get('leverage', defaults.get('leverage', '2000'))
    if isinstance(leverage, str) and ':' in leverage:
        leverage = leverage.split(':')[-1]

    print(f'\n策略: {strategy_name} | 品种数: {len(symbols)} | 周期: {date_from} ~ {date_to}')
    print('=' * 60)

    generate_set_file(strategy_name, config)

    symbol_results = {}
    for i, symbol in enumerate(symbols, 1):
        print(f'\n[{i}/{len(symbols)}] 回测 {symbol}')
        generate_ini(strategy_name, symbol, date_from, date_to, config)
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


def main():
    parser = argparse.ArgumentParser(description='MT5 Strategy Tester 回测管理器（Wine/macOS）')

    group_s = parser.add_mutually_exclusive_group(required=True)
    group_s.add_argument('--strategy', help='单个策略名称，如 v96b')
    group_s.add_argument('--strategies', help='多个策略名称，逗号分隔，如 v95c,v96b')

    group_sym = parser.add_mutually_exclusive_group(required=True)
    group_sym.add_argument('--symbol', help='单个品种，如 XAUUSDm')
    group_sym.add_argument('--symbols', help='多个品种（逗号分隔）或 all（全部品种）')

    parser.add_argument('--days', type=int, help='回测天数（从今天往前推算）')
    parser.add_argument('--from', dest='date_from', help='回测起始日期 YYYY.MM.DD')
    parser.add_argument('--to', dest='date_to', help='回测结束日期 YYYY.MM.DD')
    parser.add_argument('--timeout', type=int, default=300, help='每个品种的超时秒数（默认300）')

    args = parser.parse_args()

    config = load_config()

    strategy_arg = args.strategy or args.strategies
    strategy_names = resolve_strategies(config, strategy_arg)

    symbol_arg = args.symbol or args.symbols
    symbols = resolve_symbols(config, symbol_arg)
    if not symbols:
        print('[错误] 未找到任何品种')
        sys.exit(1)

    if args.date_from and args.date_to:
        date_from = args.date_from
        date_to = args.date_to
        d1 = datetime.strptime(date_from, '%Y.%m.%d')
        d2 = datetime.strptime(date_to, '%Y.%m.%d')
        days = (d2 - d1).days
    elif args.days:
        days = args.days
        date_to_dt = datetime.now()
        date_from_dt = date_to_dt - timedelta(days=days)
        date_from = date_from_dt.strftime('%Y.%m.%d')
        date_to = date_to_dt.strftime('%Y.%m.%d')
    else:
        print('[错误] 必须指定 --days 或 --from/--to')
        sys.exit(1)

    print(f'MT5 回测管理器')
    print(f'策略: {", ".join(strategy_names)}')
    print(f'品种: {", ".join(symbols)}')
    print(f'周期: {date_from} ~ {date_to} ({days}天)')

    os.makedirs(REPORT_DIR, exist_ok=True)

    for name in strategy_names:
        run_backtest(name, symbols, date_from, date_to, days, config, args.timeout)

    print('\n全部回测完成。')


if __name__ == '__main__':
    main()
