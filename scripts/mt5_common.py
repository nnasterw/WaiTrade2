#!/usr/bin/env python3
"""MT5 回测共享模块 — 配置加载、结果解析、统计计算、报告格式化"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from yaml_to_set import NON_STRATEGY_KEYS

CONFIG_PATH = ROOT / 'config' / 'strategies.yaml'
RESULTS_DIR = ROOT / 'results' / 'backtest'


def load_config(config_path=None):
    path = config_path or CONFIG_PATH
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def resolve_symbols(config, symbol_arg):
    if symbol_arg.lower() == 'all':
        symbols = []
        for category in config.get('symbols', {}).values():
            if isinstance(category, list):
                symbols.extend(category)
        return symbols
    return [s.strip() for s in symbol_arg.split(',')]


def resolve_strategies(config, strategy_arg):
    names = [s.strip() for s in strategy_arg.split(',')]
    available = [k for k in config if k not in NON_STRATEGY_KEYS and isinstance(config[k], dict)]
    for name in names:
        if name not in available:
            print(f'[错误] 策略 {name} 在 strategies.yaml 中不存在，可用: {", ".join(available)}')
            sys.exit(1)
    return names


def parse_agent_log_content(content):
    """纯函数：从 Agent 日志文本解析回测结果"""
    lines = content.splitlines()

    segments = []
    current = None
    for line in lines:
        if 'testing of' in line.lower():
            if current is not None:
                segments.append(current)
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        segments.append(current)

    if not segments:
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
    balance_pattern = re.compile(r'final balance\s+(-?[\d.]+)')
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
        total_nr_str = f"+{total_r:.1f}" if total_r >= 0 else f"{total_r:.1f}"
        if r_count == 0:
            total_nr_str = 'N/A'

        lines.append(
            f'{"合计":<12}{total_trades:<6}{total_daily:<6.1f}{total_wr:<7.1f}%{"":<8}{total_nr_str:<8}'
            f'${total_balance:.2f}'
        )

    lines.append('=====================================================================')
    return '\n'.join(lines)


def write_set_file(strategy_name, config, set_dir):
    """生成.set文件并写入指定目录，返回文件路径"""
    import yaml_to_set
    content = yaml_to_set.strategy_to_set(strategy_name, config[strategy_name])
    set_dir.mkdir(parents=True, exist_ok=True)
    set_path = set_dir / f'{strategy_name}.set'
    set_path.write_text(content, encoding='utf-8')
    print(f'  .set 文件已写入: {set_path.name}')
    return set_path


def read_agent_log(log_dir):
    """从指定目录读取今日Agent日志并解析"""
    from datetime import datetime
    today_str = datetime.now().strftime('%Y%m%d')
    log_path = Path(log_dir) / f'{today_str}.log'
    if not log_path.exists():
        print(f'  [警告] Agent 日志不存在: {log_path}')
        return None
    try:
        content = log_path.read_text(encoding='utf-16-le')
    except Exception as e:
        print(f'  [错误] 读取日志失败: {e}')
        return None
    return parse_agent_log_content(content)


def backtest_main(description, run_fn, args=None):
    """共享CLI参数解析和调度。

    Args:
        description: argparse description 字符串
        run_fn: callable(strategy_names, symbols, date_from, date_to, days, config, timeout)
        args: 命令行参数列表（None时从sys.argv读取）
    """
    import argparse
    from datetime import datetime, timedelta

    parser = argparse.ArgumentParser(description=description)

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

    parsed = parser.parse_args(args)

    config = load_config()

    strategy_arg = parsed.strategy or parsed.strategies
    strategy_names = resolve_strategies(config, strategy_arg)

    symbol_arg = parsed.symbol or parsed.symbols
    symbols = resolve_symbols(config, symbol_arg)
    if not symbols:
        print('[错误] 未找到任何品种')
        sys.exit(1)

    if parsed.date_from and parsed.date_to:
        date_from = parsed.date_from
        date_to = parsed.date_to
        d1 = datetime.strptime(date_from, '%Y.%m.%d')
        d2 = datetime.strptime(date_to, '%Y.%m.%d')
        days = (d2 - d1).days
    elif parsed.days:
        days = parsed.days
        date_to_dt = datetime.now()
        date_from_dt = date_to_dt - timedelta(days=days)
        date_from = date_from_dt.strftime('%Y.%m.%d')
        date_to = date_to_dt.strftime('%Y.%m.%d')
    else:
        print('[错误] 必须指定 --days 或 --from/--to')
        sys.exit(1)

    print(f'策略: {", ".join(strategy_names)}')
    print(f'品种: {", ".join(symbols)}')
    print(f'周期: {date_from} ~ {date_to} ({days}天)')

    run_fn(strategy_names, symbols, date_from, date_to, days, config, parsed.timeout)
