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

DEAL_PATTERN = re.compile(
    r'deal #(\d+)\s+(buy|sell)\s+([\d.]+)\s+(\S+)\s+at\s+([\d.]+)'
    r'(?:\s+sl:\s*([\d.]+))?(?:\s+tp:\s*([\d.]+))?'
)
BALANCE_PATTERN = re.compile(r'final balance\s+(-?[\d.]+)')
TICKS_PATTERN = re.compile(r'(\d+)\s+ticks.*?(\d+)\s+bars')
STOP_OUT_PATTERN = re.compile(r'stop out occurred on\s+(\d+)% of testing interval', re.IGNORECASE)
TESTING_HEADER_PATTERN = re.compile(
    r'(?P<symbol>\S+),(?P<period>\S+):\s+testing of .*? '
    r'from\s+(?P<date_from>\d{4}\.\d{2}\.\d{2})\s+\d{2}:\d{2} '
    r'to\s+(?P<date_to>\d{4}\.\d{2}\.\d{2})\s+\d{2}:\d{2}\s+started',
    re.IGNORECASE,
)
LOG_TIME_PATTERN = re.compile(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})')
KEY_VALUE_PATTERN = re.compile(r'(\w+)=([^\s]+)')
OPEN_SUCCESS_PATTERN = re.compile(
    r'开仓成功:\s+(.*?)\s+ticket=(\d+)\s+price=([\d.]+)\s+lot=([\d.]+)'
    r'\s+bounce_sec=(-?\d+)\s+bounce_ob=([\d.]+)\s+confirm_pos=(-?[\d.]+)'
    r'\s+touch=([\d.]+)\s+confirm=([\d.]+)'
)
ADDON_OPEN_PATTERN = re.compile(
    r'source=(\d+)\s+addon=(\d+)\s+r=(-?[\d.]+)\s+lot=([\d.]+)'
)
OPEN_MARKET_PATTERN = re.compile(
    r'market\s+(buy|sell)\s+([\d.]+)\s+(\S+)'
    r'(?:\s+sl:\s*([\d.]+))?(?:\s+tp:\s*([\d.]+))?'
)
MARKET_CLOSE_PATTERN = re.compile(
    r'market\s+(buy|sell)\s+([\d.]+)\s+(\S+),\s+close\s+#(\d+)'
)
TRIGGER_PATTERN = re.compile(
    r'(take profit triggered|stop loss triggered)\s+#(\d+).*?\[#(\d+)\s+(buy|sell)\s+([\d.]+)\s+(\S+)\s+at\s+([\d.]+)\]',
    re.IGNORECASE,
)
SL_DIAG_PATTERN = re.compile(
    r'SL_DIAG\s+reason=([^\s]+)\s+ticket=(\d+).*?new_sl=([\d.]+)'
)
EXIT_DIAG_PATTERN = re.compile(
    r'EXIT_DIAG\s+reason=([^\s]+)\s+ticket=(\d+).*?current_r=(-?[\d.]+)'
    r'.*?peak_r=(-?[\d.]+).*?dtp_peak_r=(-?[\d.]+).*?giveback_r=(-?[\d.]+)'
    r'.*?bars_held=(\d+).*?last_sl=([^\s]*)'
)
POSITION_GONE_PATTERN = re.compile(
    r'POSITION_GONE_DIAG\s+ticket=(\d+)\s+dir=(-?\d+)\s+entry=([\d.]+)\s+sl_initial=([\d.]+)'
    r'.*?peak_r=(-?[\d.]+).*?raw_peak_r=(-?[\d.]+).*?dtp_peak_r=(-?[\d.]+)'
    r'.*?open_bar=(\d+).*?last_sl=([^\s]*)\s+be=(true|false)\s+trail=(\d+)'
    r'\s+partial=(true|false)\s+dtp_partial=(true|false)\s+deep=(true|false)\s+htf=(true|false)'
    r'\s+rev=(true|false)\s+addon=(true|false)'
)
REPORT_TITLE_PATTERN = re.compile(r'MT5 Strategy Tester 回测报告 —\s*(\S+)')
REPORT_META_PATTERN = re.compile(
    r'日期:\s*(\d{4}\.\d{2}\.\d{2})\s*~\s*(\d{4}\.\d{2}\.\d{2})\s*\((\d+)天\)'
    r'\s*\|\s*资金:\s*\$(\d+(?:\.\d+)?)\s*\|\s*杠杆:\s*1:(\d+)'
    r'(?:\s*\|\s*模型:\s*(\d+))?',
)
REPORT_ROW_PATTERN = re.compile(
    r'^(\S+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s*(?:%\s*([\d.]+|inf))?\s+(N/A|[+-]?[\d.]+)\s+\$(-?[\d.]+)$'
)


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
    segments = split_agent_log_segments(content)
    if not segments:
        return None

    last_segment = segments[-1]['lines']
    result = {
        'trades': 0,
        'wins': 0,
        'losses': 0,
        'final_balance': None,
        'deals': [],
        'ticks': None,
        'bars': None,
        'stopout': False,
        'stopout_pct': None,
    }

    for line in last_segment:
        m = DEAL_PATTERN.search(line)
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

        m = BALANCE_PATTERN.search(line)
        if m:
            result['final_balance'] = float(m.group(1))

        m = TICKS_PATTERN.search(line)
        if m:
            result['ticks'] = int(m.group(1))
            result['bars'] = int(m.group(2))

        m = STOP_OUT_PATTERN.search(line)
        if m:
            result['stopout'] = True
            result['stopout_pct'] = int(m.group(1))

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


def format_report(strategy_name, date_from, date_to, days, deposit, leverage, symbol_results, model=None):
    model_text = f' | 模型: {model}' if model is not None else ''
    header = f"""
=====================================================================
MT5 Strategy Tester 回测报告 — {strategy_name.upper()}
日期: {date_from} ~ {date_to} ({days}天) | 资金: ${deposit} | 杠杆: 1:{leverage}{model_text}
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

        nr_str = f'+{nr:.1f}' if nr is not None and nr >= 0 else (f'{nr:.1f}' if nr is not None else 'N/A')
        pf_str = f'{pf:.2f}' if pf != float('inf') else 'inf'

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
        total_nr_str = f'+{total_r:.1f}' if total_r >= 0 else f'{total_r:.1f}'
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
    parser.add_argument('--deposit', type=float, help='覆盖初始资金')
    parser.add_argument('--model', help='覆盖 MT5 Strategy Tester Model；4=Real ticks')
    parser.add_argument('--v3', action='store_true', help='使用 WaiTrade3 (SMC 增强版)')

    parsed = parser.parse_args(args)

    # 加载配置：--v3 时合并加载 v2 + v3 yaml
    config = load_config()

    if parsed.v3:
        v3_path = ROOT / 'config' / 'strategies_v3.yaml'
        if v3_path.exists():
            v3_config = load_config(v3_path)
            for name, cfg in v3_config.items():
                if name in NON_STRATEGY_KEYS or not isinstance(cfg, dict):
                    continue
                # v3 专属策略或覆盖 v2 同名的策略
                base = None
                if name in config and isinstance(config[name], dict):
                    base = config[name]  # 用 v2 同名策略作 base
                elif '_base' in cfg and cfg['_base'] in config:
                    base = config[cfg['_base']]  # 用 _base 指定的 v2 策略
                if base is not None:
                    merged = dict(base)
                else:
                    merged = dict(config.get('defaults', {}))
                merged.update(cfg)
                config[name] = merged
            config[name] = merged

    strategy_arg = parsed.strategy or parsed.strategies
    strategy_names = resolve_strategies(config, strategy_arg)

    if parsed.deposit is not None:
        for name in strategy_names:
            config[name]['deposit'] = parsed.deposit

    if parsed.model is not None:
        for name in strategy_names:
            config[name]['model'] = parsed.model

    if parsed.v3:
        # 加载 v3 YAML 获取 SMC 参数默认值
        v3_yaml_path = ROOT / 'config' / 'strategies_v3.yaml'
        v3_config = {}
        if v3_yaml_path.exists():
            with open(v3_yaml_path, 'r', encoding='utf-8') as f:
                v3_config = yaml.safe_load(f) or {}
        v3_defaults = v3_config.get('defaults', {}) if isinstance(v3_config, dict) else {}

        for name in strategy_names:
            if name in config and isinstance(config[name], dict):
                config[name]['expert'] = r'WaiTrade3\WaiTrade_OB_SMC'
                # 合并 v3 默认值（仅添加 v3 参数，覆盖同名参数）
                for k, v in v3_defaults.items():
                    if k not in config[name]:
                        config[name][k] = v

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


def _extract_log_time(line):
    match = LOG_TIME_PATTERN.search(line)
    if not match:
        return None
    return match.group(1).replace('.', '-')


def _to_bool(value):
    return value == 'true'


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_key_values(text):
    return {key: value for key, value in KEY_VALUE_PATTERN.findall(text)}


def _signal_type_from_comment(comment):
    """从 EA 开仓 comment 中识别信号来源。"""
    if not comment:
        return 'ob'
    tokens = set(comment.split())
    if 'LSWP' in tokens:
        return 'loose_sweep'
    if 'CAMPRLD' in tokens or 'PS1_BUY_M5BOS' in tokens or 'PS1_SELL_M5BOS' in tokens:
        return 'campaign_reload'
    if comment and '-PS1' in comment and any(t.endswith('x') or t.startswith('x') for t in tokens) and ('B' in tokens or 'S' in tokens):
        return 'campaign_reload'
    if 'SWP' in tokens:
        return 'range'
    if 'HTFPB' in tokens:
        return 'htf_pullback'
    return 'ob'


def _direction_from_comment(comment):
    if not comment:
        return None
    tokens = comment.split()
    for idx, token in enumerate(tokens):
        if token in ('B', 'S') and idx + 1 < len(tokens):
            if tokens[idx + 1].startswith('x') or any(t.startswith('x') for t in tokens[idx + 1:]):
                return token
    return None


def _parse_summary_row(line):
    stripped = line.strip()
    if not stripped or stripped.startswith(('=', '-')):
        return None
    match = REPORT_ROW_PATTERN.match(stripped)
    if not match:
        return None
    pf_raw = match.group(5)
    net_r_raw = match.group(6)
    return {
        'name': match.group(1),
        'trades': int(match.group(2)),
        'daily_trades': float(match.group(3)),
        'win_rate': float(match.group(4)),
        'profit_factor': float(pf_raw) if pf_raw and pf_raw != 'inf' else (float('inf') if pf_raw == 'inf' else None),
        'net_r': None if net_r_raw == 'N/A' else float(net_r_raw),
        'final_balance': float(match.group(7)),
    }


def parse_backtest_report_content(content):
    """解析 results/backtest/*.txt 聚合报告。"""
    strategy_name = None
    meta = None
    symbols = []
    total = None

    for line in content.splitlines():
        if strategy_name is None:
            title_match = REPORT_TITLE_PATTERN.search(line)
            if title_match:
                strategy_name = title_match.group(1)
                continue

        if meta is None:
            meta_match = REPORT_META_PATTERN.search(line)
            if meta_match:
                meta = {
                    'date_from': meta_match.group(1),
                    'date_to': meta_match.group(2),
                    'days': int(meta_match.group(3)),
                    'deposit': float(meta_match.group(4)),
                    'leverage': meta_match.group(5),
                    'model': meta_match.group(6),
                }
                continue

        row = _parse_summary_row(line)
        if not row:
            continue
        if row['name'] == '合计':
            total = row
        else:
            row['symbol'] = row.pop('name')
            symbols.append(row)

    if strategy_name is None or meta is None:
        return None

    return {
        'strategy_name': strategy_name,
        **meta,
        'symbols': symbols,
        'total': total,
    }


def _parse_segment_meta(line):
    match = TESTING_HEADER_PATTERN.search(line)
    if not match:
        return None
    return {
        'symbol': match.group('symbol'),
        'period': match.group('period'),
        'date_from': match.group('date_from'),
        'date_to': match.group('date_to'),
    }


def split_agent_log_segments(content):
    """按 testing of 分割 Agent 日志。"""
    segments = []
    current = None
    for line in content.splitlines():
        meta = _parse_segment_meta(line)
        if meta or 'testing of' in line.lower():
            if current is not None:
                segments.append(current)
            if meta is None:
                meta = {
                    'symbol': None,
                    'period': None,
                    'date_from': None,
                    'date_to': None,
                }
            current = {'meta': meta, 'header': line, 'lines': [line]}
            continue
        if current is not None:
            current['lines'].append(line)
    if current is not None:
        segments.append(current)
    return segments


def find_matching_log_segment(
    content,
    symbol,
    date_from,
    date_to,
    final_balance=None,
    expected_markers=None,
):
    """从多段 Agent 日志中选择与摘要报告最匹配的一段。"""
    segments = split_agent_log_segments(content)
    candidates = []
    markers = [m for m in (expected_markers or []) if m]

    for segment in segments:
        meta = segment['meta']
        if meta['symbol'] != symbol or meta['date_from'] != date_from or meta['date_to'] != date_to:
            continue
        segment_text = '\n'.join(segment['lines'])
        if markers and not any(marker in segment_text for marker in markers):
            continue
        stats = parse_agent_log_content(segment_text)
        balance = stats['final_balance'] if stats else None
        diff = abs(balance - final_balance) if balance is not None and final_balance is not None else float('inf')
        candidates.append((diff, len(candidates), balance, segment))

    if not candidates:
        return None

    if final_balance is not None:
        candidates.sort(key=lambda item: (item[0], -item[1], item[2] is None))
        return candidates[0][3]
    return candidates[-1][3]


def _parse_entry_diag(line, event_time):
    if 'ENTRY_DIAG' not in line:
        return None
    payload = line.split('ENTRY_DIAG', 1)[1].strip()
    values = _parse_key_values(payload)
    direction = _to_int(values.get('dir'))
    entry = _to_float(values.get('entry'))
    if direction is None or entry is None:
        return None
    return {
        'time': event_time,
        'date': event_time.split(' ')[0] if event_time else None,
        'hour': _to_int(values.get('hour')),
        'dir': direction,
        'entry': entry,
        'sl': _to_float(values.get('sl')),
        'stage': values.get('stage'),
        'ob_age': _to_int(values.get('ob_age')),
        'touch_count': _to_int(values.get('touch_count') or values.get('touch')),
        'entry_count': _to_int(values.get('entry_count')),
        'strength': _to_float(values.get('strength')),
        'ds': _to_float(values.get('ds')),
        'fresh': _to_int(values.get('fresh')),
        'cont': _to_int(values.get('cont')),
        'h1': _to_int(values.get('h1')),
        'deep': _to_int(values.get('deep')),
        'htf': _to_int(values.get('htf')),
        'bounce_sec': _to_int(values.get('bounce_sec')),
        'bounce_ob': _to_float(values.get('bounce_ob')),
        'confirm_pos': _to_float(values.get('confirm_pos')),
        'touch_price': _to_float(values.get('touch_price') or values.get('touch')),
        'confirm_price': _to_float(values.get('confirm')),
        'risk_atr': _to_float(values.get('risk_atr')),
        'spread_risk': _to_float(values.get('spread_risk')),
        'pos_mult': _to_float(values.get('pos_mult')),
        'score': _to_int(values.get('score')),
    }


def _parse_open_order(line):
    if ', close #' in line or 'market ' not in line:
        return None
    match = OPEN_MARKET_PATTERN.search(line)
    if not match:
        return None
    return {
        'dir': match.group(1),
        'lot': float(match.group(2)),
        'symbol': match.group(3),
        'sl': float(match.group(4)) if match.group(4) else None,
        'tp': float(match.group(5)) if match.group(5) else None,
    }


def _parse_open_success(line, event_time):
    match = OPEN_SUCCESS_PATTERN.search(line)
    if not match:
        return None
    return {
        'time': event_time,
        'comment': match.group(1),
        'direction_char': _direction_from_comment(match.group(1)),
        'ticket': int(match.group(2)),
        'price': float(match.group(3)),
        'lot': float(match.group(4)),
        'bounce_sec': int(match.group(5)),
        'bounce_ob': float(match.group(6)),
        'confirm_pos': float(match.group(7)),
        'touch': float(match.group(8)),
        'confirm': float(match.group(9)),
    }


def _parse_addon_open(line, event_time):
    match = ADDON_OPEN_PATTERN.search(line)
    if not match:
        return None
    return {
        'time': event_time,
        'source_ticket': int(match.group(1)),
        'ticket': int(match.group(2)),
        'trigger_r': float(match.group(3)),
        'lot': float(match.group(4)),
    }


def _parse_close_event(line, event_time):
    trigger_match = TRIGGER_PATTERN.search(line)
    if trigger_match:
        reason = 'TP' if 'take profit' in trigger_match.group(1).lower() else 'SL'
        return {
            'ticket': int(trigger_match.group(2)),
            'reason': reason,
            'exit_ticket': int(trigger_match.group(3)),
            'close_time': event_time,
        }

    close_match = MARKET_CLOSE_PATTERN.search(line)
    if close_match:
        return {
            'ticket': int(close_match.group(4)),
            'reason': 'MARKET_CLOSE',
            'exit_ticket': None,
            'close_time': event_time,
        }
    return None


def _parse_sl_diag(line):
    match = SL_DIAG_PATTERN.search(line)
    if not match:
        return None
    return {
        'reason': match.group(1),
        'ticket': int(match.group(2)),
        'new_sl': float(match.group(3)),
    }


def _parse_exit_diag(line):
    match = EXIT_DIAG_PATTERN.search(line)
    if not match:
        return None
    return {
        'reason': match.group(1),
        'ticket': int(match.group(2)),
        'current_r': float(match.group(3)),
        'peak_r': float(match.group(4)),
        'dtp_peak_r': float(match.group(5)),
        'giveback_r': float(match.group(6)),
        'bars_held': int(match.group(7)),
        'last_sl': match.group(8) or None,
    }


def _parse_position_gone(line):
    match = POSITION_GONE_PATTERN.search(line)
    if not match:
        return None
    return {
        'ticket': int(match.group(1)),
        'dir': int(match.group(2)),
        'entry': float(match.group(3)),
        'sl_initial': float(match.group(4)),
        'peak_r': float(match.group(5)),
        'raw_peak_r': float(match.group(6)),
        'dtp_peak_r': float(match.group(7)),
        'open_bar': int(match.group(8)),
        'last_sl': match.group(9) or None,
        'be': _to_bool(match.group(10)),
        'trail': int(match.group(11)),
        'partial': _to_bool(match.group(12)),
        'dtp_partial': _to_bool(match.group(13)),
        'deep': _to_bool(match.group(14)),
        'htf': _to_bool(match.group(15)),
        'rev': _to_bool(match.group(16)),
        'addon': _to_bool(match.group(17)),
    }


def _match_pending_diag(pending_diags, direction, price):
    for idx in range(len(pending_diags) - 1, -1, -1):
        diag = pending_diags[idx]
        if diag['dir'] != direction:
            continue
        if abs(diag['entry'] - price) > 1e-6:
            continue
        return pending_diags.pop(idx)
    return pending_diags.pop() if pending_diags else None


def _match_pending_order(pending_orders, direction_text, lot):
    for idx in range(len(pending_orders) - 1, -1, -1):
        order = pending_orders[idx]
        if order['dir'] != direction_text:
            continue
        if abs(order['lot'] - lot) > 1e-9:
            continue
        return pending_orders.pop(idx)
    return pending_orders.pop() if pending_orders else None


def _match_pending_entry_deal(pending_entry_deals, ticket, lot=None):
    for idx in range(len(pending_entry_deals) - 1, -1, -1):
        deal = pending_entry_deals[idx]
        if deal['ticket'] != ticket:
            continue
        if lot is not None and abs(deal['lots'] - lot) > 1e-9:
            continue
        return pending_entry_deals.pop(idx)
    return None


def _build_trade(ticket, symbol, open_event, diag, order):
    direction_char = open_event.get('direction_char')
    if diag and diag['dir'] > 0:
        direction = 'buy'
    elif diag and diag['dir'] < 0:
        direction = 'sell'
    elif direction_char == 'B':
        direction = 'buy'
    elif direction_char == 'S':
        direction = 'sell'
    elif order and order.get('dir') in ('buy', 'sell'):
        direction = order['dir']
    else:
        direction = 'buy'
    entry = diag['entry'] if diag else open_event.get('price')
    initial_sl = None
    if diag and diag.get('sl') is not None:
        initial_sl = diag['sl']
    elif order:
        initial_sl = order['sl']

    return {
        'ticket': ticket,
        'time': (diag or open_event)['time'],
        'date': (diag or open_event)['date'] if diag else open_event['time'].split(' ')[0],
        'hour': diag['hour'] if diag else _to_int(open_event['time'][11:13]),
        'symbol': symbol,
        'dir': direction,
        'comment': open_event.get('comment'),
        'signal_type': open_event.get('signal_type') or _signal_type_from_comment(open_event.get('comment')),
        'lot': open_event.get('lot'),
        'pos_mult': diag['pos_mult'] if diag else None,
        'entry': entry,
        'initial_sl': initial_sl,
        'tp': order['tp'] if order else None,
        'exit': None,
        'reason': None,
        'exit_signal': None,
        'risk': abs(entry - initial_sl) if initial_sl is not None else None,
        'r': None,
        'duration_min': None,
        'mods': 0,
        'max_lock_r': None,
        'bounce_sec': open_event.get('bounce_sec'),
        'bounce_ob': open_event.get('bounce_ob'),
        'confirm_pos': open_event.get('confirm_pos'),
        'touch': open_event.get('touch'),
        'confirm': open_event.get('confirm'),
        'close_time': None,
        'stage': diag['stage'] if diag else None,
        'ob_age': diag['ob_age'] if diag else None,
        'strength': diag['strength'] if diag else None,
        'score': diag['score'] if diag else None,
        'ds': diag['ds'] if diag else None,
        'fresh': diag['fresh'] if diag else None,
        'cont': diag['cont'] if diag else None,
        'h1': bool(diag['h1']) if diag else None,
        'deep': bool(diag['deep']) if diag else None,
        'htf': bool(diag['htf']) if diag else None,
        'risk_atr': diag['risk_atr'] if diag else None,
        'spread_risk': diag['spread_risk'] if diag else None,
        'peak_r': None,
        'raw_peak_r': None,
        'dtp_peak_r': None,
        'giveback_r': None,
        'bars_held': None,
        'last_sl': None,
        'be': None,
        'trail': None,
        'partial': None,
        'dtp_partial': None,
        'rev': None,
        'addon': None,
        '_close_meta': {},
    }


def _calc_lock_r(trade, new_sl):
    risk = trade.get('risk')
    entry = trade.get('entry')
    if not risk or not entry:
        return None
    if trade['dir'] == 'buy':
        return (new_sl - entry) / risk
    return (entry - new_sl) / risk


def _attach_close_deal(trade, close_meta, deal, event_time):
    trade['exit'] = deal['price']
    trade['close_time'] = close_meta.get('close_time') or event_time
    trade['reason'] = close_meta.get('reason')

    if trade['reason'] == 'SL':
        exit_signal = trade.get('last_sl') or 'sl'
    elif trade['reason'] == 'MARKET_CLOSE':
        exit_signal = close_meta.get('exit_signal') or 'market_close'
    else:
        exit_signal = 'tp'
    trade['exit_signal'] = exit_signal


def _finalize_trade(trade):
    from datetime import datetime

    if trade.get('exit') is None or trade.get('entry') is None:
        return trade

    if trade['dir'] == 'buy':
        move = trade['exit'] - trade['entry']
    else:
        move = trade['entry'] - trade['exit']

    risk = trade.get('risk')
    trade['r'] = (move / risk) if risk else None

    if trade.get('time') and trade.get('close_time'):
        opened = datetime.strptime(trade['time'], '%Y-%m-%d %H:%M:%S')
        closed = datetime.strptime(trade['close_time'], '%Y-%m-%d %H:%M:%S')
        trade['duration_min'] = round((closed - opened).total_seconds() / 60.0, 3)

    trade['pnl_proxy'] = move * trade['lot']
    trade.pop('_close_meta', None)
    return trade


def parse_agent_log_segment_details(segment_lines, symbol=None):
    """解析单个 testing segment，提取逐单归因数据。"""
    basic = parse_agent_log_content('\n'.join(segment_lines)) or {}
    pending_diags = []
    pending_orders = []
    pending_entry_deals = []
    close_by_exit_ticket = {}
    pending_market_closes = []
    trades = {}

    for line in segment_lines:
        event_time = _extract_log_time(line)

        diag = _parse_entry_diag(line, event_time)
        if diag:
            pending_diags.append(diag)
            continue

        order = _parse_open_order(line)
        if order:
            pending_orders.append(order)
            continue

        open_event = _parse_open_success(line, event_time)
        if open_event:
            _match_pending_entry_deal(pending_entry_deals, open_event['ticket'], open_event['lot'])
            direction = 1 if open_event['direction_char'] == 'B' else -1
            diag = _match_pending_diag(pending_diags, direction, open_event['price'])
            order = _match_pending_order(pending_orders, 'buy' if direction > 0 else 'sell', open_event['lot'])
            trades[open_event['ticket']] = _build_trade(open_event['ticket'], symbol, open_event, diag, order)
            continue

        addon_event = _parse_addon_open(line, event_time)
        if addon_event:
            source_trade = trades.get(addon_event['source_ticket'])
            entry_deal = _match_pending_entry_deal(pending_entry_deals, addon_event['ticket'], addon_event['lot'])
            direction_text = entry_deal['direction'] if entry_deal else (source_trade.get('dir') if source_trade else None)
            order = _match_pending_order(pending_orders, direction_text, addon_event['lot'])
            comment = source_trade.get('comment') if source_trade else None
            signal_type = source_trade.get('signal_type') if source_trade else 'addon'
            direction_char = None
            if source_trade:
                direction_char = 'B' if source_trade.get('dir') == 'buy' else 'S'
            elif direction_text == 'buy':
                direction_char = 'B'
            elif direction_text == 'sell':
                direction_char = 'S'
            open_like = {
                'time': addon_event['time'],
                'date': addon_event['time'].split(' ')[0] if addon_event.get('time') else None,
                'comment': comment,
                'signal_type': signal_type,
                'direction_char': direction_char,
                'ticket': addon_event['ticket'],
                'price': entry_deal['price'] if entry_deal else None,
                'lot': addon_event['lot'],
                'bounce_sec': None,
                'bounce_ob': None,
                'confirm_pos': None,
                'touch': None,
                'confirm': None,
            }
            trades[addon_event['ticket']] = _build_trade(addon_event['ticket'], symbol, open_like, None, order)
            trades[addon_event['ticket']]['addon'] = True
            continue

        close_event = _parse_close_event(line, event_time)
        if close_event:
            trade = trades.setdefault(close_event['ticket'], {'ticket': close_event['ticket'], '_close_meta': {}})
            meta = trade.get('_close_meta')
            if meta is None:
                meta = {}
                trade['_close_meta'] = meta
            meta.update(close_event)
            if close_event['exit_ticket'] is not None:
                close_by_exit_ticket[close_event['exit_ticket']] = close_event['ticket']
            else:
                pending_market_closes.append(close_event['ticket'])
            continue

        sl_diag = _parse_sl_diag(line)
        if sl_diag and sl_diag['ticket'] in trades:
            trade = trades[sl_diag['ticket']]
            trade['mods'] = trade.get('mods', 0) + 1
            trade['last_sl'] = sl_diag['reason']
            lock_r = _calc_lock_r(trade, sl_diag['new_sl'])
            if lock_r is not None:
                current = trade.get('max_lock_r')
                trade['max_lock_r'] = lock_r if current is None else max(current, lock_r)
            continue

        exit_diag = _parse_exit_diag(line)
        if exit_diag and exit_diag['ticket'] in trades:
            trade = trades[exit_diag['ticket']]
            meta = trade.get('_close_meta')
            if meta is None:
                meta = {}
                trade['_close_meta'] = meta
            meta['exit_signal'] = exit_diag['reason']
            trade['bars_held'] = exit_diag['bars_held']
            trade['giveback_r'] = exit_diag['giveback_r']
            trade['peak_r'] = exit_diag['peak_r']
            trade['dtp_peak_r'] = exit_diag['dtp_peak_r']
            trade['last_sl'] = exit_diag['last_sl'] or trade.get('last_sl')
            continue

        position_gone = _parse_position_gone(line)
        if position_gone and position_gone['ticket'] in trades:
            trade = trades[position_gone['ticket']]
            trade['peak_r'] = position_gone['peak_r']
            trade['raw_peak_r'] = position_gone['raw_peak_r']
            trade['dtp_peak_r'] = position_gone['dtp_peak_r']
            trade['last_sl'] = position_gone['last_sl'] or trade.get('last_sl')
            trade['be'] = position_gone['be']
            trade['trail'] = position_gone['trail']
            trade['partial'] = position_gone['partial']
            trade['dtp_partial'] = position_gone['dtp_partial']
            trade['deep'] = position_gone['deep']
            trade['htf'] = position_gone['htf']
            trade['rev'] = position_gone['rev']
            trade['addon'] = position_gone['addon']
            continue

        deal = _parse_deal_from_line(line)
        if not deal:
            continue

        entry_ticket = close_by_exit_ticket.pop(deal['ticket'], None)
        if entry_ticket is None and pending_market_closes:
            entry_ticket = pending_market_closes.pop(0)
        if entry_ticket is None:
            pending_entry_deals.append(deal)
            continue
        if entry_ticket not in trades:
            continue
        _attach_close_deal(trades[entry_ticket], trades[entry_ticket].get('_close_meta', {}), deal, event_time)

    rows = []
    for trade in trades.values():
        rows.append(_finalize_trade(trade))
    rows.sort(key=lambda item: (item.get('time') or '', item['ticket']))

    return {
        'symbol': symbol,
        'final_balance': basic.get('final_balance'),
        'ticks': basic.get('ticks'),
        'bars': basic.get('bars'),
        'stopout': basic.get('stopout', False),
        'stopout_pct': basic.get('stopout_pct'),
        'trades': rows,
    }


def _parse_deal_from_line(line):
    match = DEAL_PATTERN.search(line)
    if not match:
        return None
    return {
        'ticket': int(match.group(1)),
        'direction': match.group(2),
        'lots': float(match.group(3)),
        'symbol': match.group(4),
        'price': float(match.group(5)),
    }
