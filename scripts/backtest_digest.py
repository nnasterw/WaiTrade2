#!/usr/bin/env python3
"""回测报告提炼脚本：聚合摘要 + Agent 日志逐单归因。"""

import argparse
import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Iterable

from mt5_common import (
    parse_backtest_report_content,
    find_matching_log_segment,
    parse_agent_log_segment_details,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WINE_TESTER = Path.home() / (
    'Library/Application Support/net.metaquotes.wine.metatrader5/'
    'drive_c/Program Files/MetaTrader 5/Tester'
)
DEFAULT_WINDOWS_TESTER = Path.home() / 'AppData/Roaming/MetaQuotes/Terminal'
CSV_COLUMNS = [
    'ticket', 'time', 'date', 'hour', 'symbol', 'dir', 'comment', 'signal_type', 'lot', 'pos_mult',
    'entry', 'initial_sl', 'tp', 'exit', 'reason', 'exit_signal', 'risk', 'r',
    'duration_min', 'mods', 'max_lock_r', 'bounce_sec', 'bounce_ob', 'confirm_pos',
    'touch', 'confirm', 'close_time', 'stage', 'ob_age', 'strength', 'score', 'ds',
    'fresh', 'cont', 'h1', 'deep', 'htf', 'risk_atr', 'spread_risk', 'peak_r',
    'raw_peak_r', 'dtp_peak_r', 'giveback_r', 'bars_held', 'last_sl', 'be', 'trail',
    'partial', 'dtp_partial', 'rev', 'addon', 'pnl_proxy',
]


def _looks_misdecoded(text: str) -> bool:
    return bool(text) and text.count('\x00') / max(len(text), 1) > 0.05


def _decode_auto(data: bytes) -> str:
    for encoding in ('utf-8', 'utf-8-sig', 'utf-16-le', 'utf-16'):
        try:
            text = data.decode(encoding)
        except UnicodeError:
            continue
        if not _looks_misdecoded(text):
            return text
    return data.decode('utf-8', errors='replace')


def read_text_auto(path: Path) -> str:
    return _decode_auto(path.read_bytes())


def read_text_auto_tail(path: Path, tail_mb: int = 32) -> str:
    try:
        return read_text_auto(path)
    except MemoryError:
        tail_bytes = max(tail_mb, 1) * 1024 * 1024
        with path.open('rb') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - tail_bytes))
            data = f.read()
        return _decode_auto(data)


def _fmt_num(value, digits=2, na='N/A'):
    if value is None:
        return na
    return f'{value:.{digits}f}'


def _fmt_pct(value, digits=1, na='N/A'):
    if value is None:
        return na
    return f'{value:.{digits}f}%'


def _md_cell(value) -> str:
    return str(value).replace('|', '\\|')


def _stats(trades: list[dict]) -> dict:
    closed = [t for t in trades if t.get('r') is not None]
    wins = [t for t in closed if t['r'] > 0]
    losses = [t for t in closed if t['r'] <= 0]
    total_r = sum(t['r'] for t in closed)
    avg_r = total_r / len(closed) if closed else None
    win_rate = len(wins) / len(closed) * 100 if closed else None
    total_pnl = sum((t.get('pnl_proxy') or 0.0) for t in closed)
    avg_duration = sum((t.get('duration_min') or 0.0) for t in closed) / len(closed) if closed else None
    return {
        'count': len(closed),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': win_rate,
        'total_r': total_r,
        'avg_r': avg_r,
        'total_pnl': total_pnl,
        'avg_duration': avg_duration,
    }


def _risk_bucket(value):
    if value is None:
        return 'risk:N/A'
    if value < 100:
        return 'risk:<100'
    if value < 150:
        return 'risk:100-150'
    if value < 200:
        return 'risk:150-200'
    if value < 300:
        return 'risk:200-300'
    if value < 400:
        return 'risk:300-400'
    return 'risk:400+'


def _pos_bucket(value):
    if value is None:
        return 'x:N/A'
    if value < 1:
        return 'x:<1'
    if value < 2:
        return 'x:1-2'
    if value < 5:
        return 'x:2-5'
    if value < 10:
        return 'x:5-10'
    return 'x:10+'


def _bounce_bucket(value):
    if value is None:
        return 'sec:N/A'
    if value == 0:
        return 'sec:0'
    if value <= 10:
        return 'sec:1-10'
    if value <= 30:
        return 'sec:11-30'
    if value <= 60:
        return 'sec:31-60'
    return 'sec:60+'


def _confirm_bucket(value):
    if value is None:
        return 'cp:N/A'
    if value > -0.6:
        return 'cp:>-0.6'
    if value > -1.0:
        return 'cp:-1.0~-0.6'
    if value > -1.5:
        return 'cp:-1.5~-1.0'
    return 'cp:<=-1.5'


def _hour_bucket(value):
    if value is None:
        return 'hour:N/A'
    return f'hour:{int(value):02d}'


def _reason_bucket(trade):
    reason = trade.get('exit_signal') or trade.get('reason') or 'unknown'
    return f'exit:{reason}'


def _h1_bucket(trade):
    return 'h1:aligned' if trade.get('h1') else 'h1:not_aligned'


def _compound_label(trade, keys: tuple[str, ...]) -> str:
    labels = []
    for key in keys:
        if key == 'hour':
            labels.append(_hour_bucket(trade.get('hour')))
        elif key == 'risk':
            labels.append(_risk_bucket(trade.get('risk')))
        elif key == 'bounce_sec':
            labels.append(_bounce_bucket(trade.get('bounce_sec')))
        elif key == 'confirm_pos':
            labels.append(_confirm_bucket(trade.get('confirm_pos')))
        elif key == 'pos_mult':
            labels.append(_pos_bucket(trade.get('pos_mult')))
        elif key == 'exit':
            labels.append(_reason_bucket(trade))
        elif key == 'h1':
            labels.append(_h1_bucket(trade))
    return ' | '.join(labels)


def build_contribution_clusters(trades: list[dict], top_n=5) -> tuple[list[dict], list[dict]]:
    feature_sets = [
        ('hour', 'risk', 'confirm_pos', 'exit'),
        ('hour', 'risk', 'exit'),
        ('risk', 'confirm_pos', 'exit'),
    ]
    groups = []
    for feature_set in feature_sets:
        grouped = defaultdict(list)
        for trade in trades:
            if trade.get('r') is None:
                continue
            grouped[_compound_label(trade, feature_set)].append(trade)
        groups = []
        for label, items in grouped.items():
            stat = _stats(items)
            if stat['count'] >= 2:
                groups.append({'label': label, **stat})
        if len(groups) >= top_n:
            break

    if not groups:
        grouped = defaultdict(list)
        for trade in trades:
            if trade.get('r') is None:
                continue
            grouped[_compound_label(trade, ('risk', 'exit'))].append(trade)
        groups = [{'label': label, **_stats(items)} for label, items in grouped.items()]

    positive = sorted([g for g in groups if g['total_r'] > 0], key=lambda x: (-x['total_r'], -x['count']))[:top_n]
    negative = sorted([g for g in groups if g['total_r'] < 0], key=lambda x: (x['total_r'], -x['count']))[:top_n]
    return positive, negative


FACTOR_BUILDERS = {
    '小时': lambda t: _hour_bucket(t.get('hour')),
    '出场': lambda t: _reason_bucket(t),
    '风险档': lambda t: _risk_bucket(t.get('risk')),
    '确认耗时': lambda t: _bounce_bucket(t.get('bounce_sec')),
    '确认位置': lambda t: _confirm_bucket(t.get('confirm_pos')),
    '仓位倍数': lambda t: _pos_bucket(t.get('pos_mult')),
    'H1对齐': lambda t: _h1_bucket(t),
}


def build_factor_edges(trades: list[dict]) -> list[dict]:
    edges = []
    for factor_name, builder in FACTOR_BUILDERS.items():
        grouped = defaultdict(list)
        for trade in trades:
            if trade.get('r') is None:
                continue
            grouped[builder(trade)].append(trade)
        bucket_stats = []
        for bucket, items in grouped.items():
            stat = _stats(items)
            if stat['count'] >= 3:
                bucket_stats.append({'bucket': bucket, **stat})
        if len(bucket_stats) < 2:
            continue
        best = max(bucket_stats, key=lambda item: (item['total_r'], item['avg_r'] or -999, item['count']))
        worst = min(bucket_stats, key=lambda item: (item['total_r'], item['avg_r'] or 999, -item['count']))
        edges.append({'factor': factor_name, 'side': '优势桶', **best})
        edges.append({'factor': factor_name, 'side': '风险桶', **worst})
    return edges


def build_trade_extremes(trades: list[dict], top_n=3) -> tuple[list[dict], list[dict]]:
    closed = [t for t in trades if t.get('r') is not None]
    best = sorted(closed, key=lambda t: t['r'], reverse=True)[:top_n]
    worst = sorted(closed, key=lambda t: t['r'])[:top_n]
    return best, worst


def build_negative_month_clusters(monthly_stats: list[dict], details: dict, top_n=3) -> list[dict]:
    trades = [
        trade for trade in details.get('trades', [])
        if trade.get('time') and trade.get('r') is not None
    ]
    if not trades:
        return []

    by_month: dict[str, list[dict]] = defaultdict(list)
    for trade in trades:
        by_month[trade['time'][:7]].append(trade)

    rows = []
    for month_row in monthly_stats:
        if month_row['profit'] >= 0:
            continue
        month = month_row['month']
        items = by_month.get(month, [])
        _, negative_clusters = build_contribution_clusters(items, top_n=top_n)
        factor_edges = [
            edge for edge in build_factor_edges(items)
            if edge['side'] == '风险桶'
        ][:top_n]
        rows.append({
            'month': month,
            'profit': month_row['profit'],
            'trades': month_row['trades'],
            'sample_count': len(items),
            'negative_clusters': negative_clusters[:top_n],
            'risk_edges': factor_edges,
        })
    return rows


def build_symbol_digest(summary_row: dict, details: dict | None, deposit: float | None = None) -> dict:
    result = {
        'summary': summary_row,
        'details': details,
        'trade_stats': None,
        'positive_clusters': [],
        'negative_clusters': [],
        'factor_edges': [],
        'best_trades': [],
        'worst_trades': [],
        'monthly_stats': [],
        'negative_month_clusters': [],
        'negative_months': None,
        'stopout': False,
        'stopout_pct': None,
    }
    if not details or not details.get('trades'):
        if details:
            result['stopout'] = details.get('stopout', False)
            result['stopout_pct'] = details.get('stopout_pct')
        return result
    trades = details['trades']
    result['trade_stats'] = _stats(trades)
    pos, neg = build_contribution_clusters(trades)
    result['positive_clusters'] = pos
    result['negative_clusters'] = neg
    result['factor_edges'] = build_factor_edges(trades)
    best, worst = build_trade_extremes(trades)
    result['best_trades'] = best
    result['worst_trades'] = worst
    result['monthly_stats'] = build_monthly_stats(summary_row, details, deposit)
    result['negative_month_clusters'] = build_negative_month_clusters(result['monthly_stats'], details)
    result['negative_months'] = sum(1 for row in result['monthly_stats'] if row['profit'] < 0)
    result['stopout'] = details.get('stopout', False)
    result['stopout_pct'] = details.get('stopout_pct')
    return result


def build_monthly_stats(summary_row: dict, details: dict, deposit: float | None = None) -> list[dict]:
    trades = [trade for trade in details.get('trades', []) if trade.get('time') and trade.get('pnl_proxy') is not None]
    if not trades:
        return []

    ordered = sorted(trades, key=lambda trade: trade['time'])
    proxy_total = sum(trade.get('pnl_proxy') or 0.0 for trade in ordered)
    actual_start_balance = deposit if deposit is not None else summary_row['final_balance'] - proxy_total
    actual_total_profit = summary_row['final_balance'] - actual_start_balance
    scale = (actual_total_profit / proxy_total) if proxy_total else 0.0
    monthly_rows = []
    running_balance = actual_start_balance
    buckets: dict[str, list[dict]] = defaultdict(list)
    for trade in ordered:
        buckets[trade['time'][:7]].append(trade)

    for month in sorted(buckets):
        items = buckets[month]
        profit_proxy = sum(trade.get('pnl_proxy') or 0.0 for trade in items)
        profit = profit_proxy * scale
        month_start = running_balance
        month_end = month_start + profit
        running_balance = month_end
        rs = [trade['r'] for trade in items if trade.get('r') is not None]
        monthly_rows.append({
            'month': month,
            'trades': len(items),
            'wins': sum(1 for trade in items if (trade.get('r') or 0) > 0),
            'losses': sum(1 for trade in items if trade.get('r') is not None and trade.get('r') <= 0),
            'win_rate': (sum(1 for trade in items if (trade.get('r') or 0) > 0) / len(rs) * 100) if rs else None,
            'avg_r': mean(rs) if rs else None,
            'profit': profit,
            'start_balance': month_start,
            'end_balance': month_end,
        })
    if monthly_rows:
        drift = summary_row['final_balance'] - monthly_rows[-1]['end_balance']
        if abs(drift) > 1e-9:
            monthly_rows[-1]['profit'] += drift
            monthly_rows[-1]['end_balance'] += drift
    return monthly_rows


def _render_summary_table(report_data: dict) -> list[str]:
    lines = [
        '| 品种 | 交易 | 日均 | 胜率 | PF | 净R | 余额 |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for row in report_data['symbols']:
        pf = 'N/A' if row['profit_factor'] is None else ('inf' if row['profit_factor'] == float('inf') else f"{row['profit_factor']:.2f}")
        net_r = 'N/A' if row['net_r'] is None else f"{row['net_r']:.1f}"
        lines.append(
            f"| {row['symbol']} | {row['trades']} | {row['daily_trades']:.1f} | {row['win_rate']:.1f}% | {pf} | {net_r} | ${row['final_balance']:.2f} |"
        )
    if report_data.get('total'):
        total = report_data['total']
        pf = 'N/A' if total['profit_factor'] is None else ('inf' if total['profit_factor'] == float('inf') else f"{total['profit_factor']:.2f}")
        net_r = 'N/A' if total['net_r'] is None else f"{total['net_r']:.1f}"
        lines.append(
            f"| 合计 | {total['trades']} | {total['daily_trades']:.1f} | {total['win_rate']:.1f}% | {pf} | {net_r} | ${total['final_balance']:.2f} |"
        )
    return lines


def _render_cluster_table(clusters: list[dict]) -> list[str]:
    if not clusters:
        return ['- 无足够样本。']
    lines = [
        '| 特征簇 | 样本 | 胜率 | 平均R | 净R |',
        '|---|---:|---:|---:|---:|',
    ]
    for item in clusters:
        lines.append(
            f"| {item['label']} | {item['count']} | {_fmt_pct(item['win_rate'])} | {_fmt_num(item['avg_r'])} | {_fmt_num(item['total_r'])} |"
        )
    return lines


def _render_factor_table(edges: list[dict]) -> list[str]:
    if not edges:
        return ['- 无足够样本。']
    lines = [
        '| 因子 | 桶 | 样本 | 胜率 | 平均R | 净R |',
        '|---|---|---:|---:|---:|---:|',
    ]
    for item in edges:
        lines.append(
            f"| {item['factor']} {item['side']} | {item['bucket']} | {item['count']} | {_fmt_pct(item['win_rate'])} | {_fmt_num(item['avg_r'])} | {_fmt_num(item['total_r'])} |"
        )
    return lines


def _render_monthly_table(monthly_stats: list[dict]) -> list[str]:
    if not monthly_stats:
        return ['- 无逐月数据。']
    lines = [
        '| 月份 | 交易 | 胜率 | 平均R | 月利润 | 月初余额 | 月末余额 |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for row in monthly_stats:
        lines.append(
            f"| {row['month']} | {row['trades']} | {_fmt_pct(row['win_rate'])} | {_fmt_num(row['avg_r'])} | {_fmt_num(row['profit'])} | {_fmt_num(row['start_balance'])} | {_fmt_num(row['end_balance'])} |"
        )
    return lines


def _render_negative_month_clusters(rows: list[dict]) -> list[str]:
    if not rows:
        return ['- 无亏损月，或亏损月无足够归因样本。']
    lines = [
        '| 月份 | 月利润 | 月交易 | 归因样本 | Top坏簇 | 风险因子 |',
        '|---|---:|---:|---:|---|---|',
    ]
    for row in rows:
        top_cluster = row['negative_clusters'][0] if row['negative_clusters'] else None
        top_edge = row['risk_edges'][0] if row['risk_edges'] else None
        cluster_text = '无'
        if top_cluster:
            cluster_text = (
                f"{top_cluster['label']} "
                f"({top_cluster['count']}笔/{_fmt_num(top_cluster['total_r'])}R)"
            )
        edge_text = '无'
        if top_edge:
            edge_text = (
                f"{top_edge['factor']}={top_edge['bucket']} "
                f"({_fmt_num(top_edge['total_r'])}R)"
            )
        lines.append(
            f"| {row['month']} | {_fmt_num(row['profit'])} | {row['trades']} | {row['sample_count']} | {_md_cell(cluster_text)} | {_md_cell(edge_text)} |"
        )
    return lines


def _render_extremes(title: str, trades: list[dict]) -> list[str]:
    lines = [f'#### {title}']
    if not trades:
        lines.append('- 无数据。')
        return lines
    lines.extend([
        '| ticket | 时间 | dir | R | hour | exit | xmult | risk | sec | confirm_pos |',
        '|---|---|---|---:|---:|---|---:|---:|---:|---:|',
    ])
    for trade in trades:
        lines.append(
            f"| {trade['ticket']} | {trade.get('time','')} | {trade.get('dir','')} | {_fmt_num(trade.get('r'))} | {trade.get('hour','')} | {trade.get('exit_signal') or trade.get('reason') or ''} | {_fmt_num(trade.get('pos_mult'))} | {_fmt_num(trade.get('risk'))} | {trade.get('bounce_sec','')} | {_fmt_num(trade.get('confirm_pos'), 3)} |"
        )
    return lines


def render_digest_markdown(report_data: dict, symbol_digests: list[dict], report_path: Path, log_path: Path | None) -> str:
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        f"# 回测提炼报告 — {report_data['strategy_name']}",
        '',
        f"- 生成时间: `{generated_at}`",
        f"- 摘要来源: `{report_path}`",
        f"- 日志来源: `{log_path}`" if log_path else '- 日志来源: `未提供/未匹配`',
        '',
        '## 核心摘要',
        '',
        *_render_summary_table(report_data),
        '',
        '## 低 Token 结论',
        '',
    ]

    for digest in symbol_digests:
        symbol = digest['summary']['symbol']
        stats = digest.get('trade_stats')
        if not stats:
            lines.append(f'- `{symbol}`: 只解析到聚合摘要，未匹配到逐单日志。')
            continue
        top_pos = digest['positive_clusters'][0]['label'] if digest['positive_clusters'] else '无'
        top_neg = digest['negative_clusters'][0]['label'] if digest['negative_clusters'] else '无'
        best_factor = digest['factor_edges'][0]['bucket'] if digest['factor_edges'] else '无'
        lines.append(
            f"- `{symbol}`: 盈利主簇=`{top_pos}`；亏损主簇=`{top_neg}`；首个判别桶=`{best_factor}`。"
        )

    for digest in symbol_digests:
        symbol = digest['summary']['symbol']
        lines.extend([
            '',
            f'## 逐单归因 — {symbol}',
            '',
        ])
        stats = digest.get('trade_stats')
        if not stats:
            lines.append('- 未匹配到逐单日志，仅保留聚合摘要。')
            continue
        stopout_text = '是' if digest.get('stopout') else '否'
        stopout_pct = digest.get('stopout_pct')
        stopout_suffix = f" ({stopout_pct}% 区间)" if stopout_pct is not None else ''
        lines.extend([
            f"- 总样本: `{stats['count']}`",
            f"- 归因覆盖: `{stats['count']}/{digest['summary']['trades']}`",
            f"- 胜率: `{_fmt_pct(stats['win_rate'])}`",
            f"- 平均R: `{_fmt_num(stats['avg_r'])}`",
            f"- 净R: `{_fmt_num(stats['total_r'])}`",
            f"- 平均持仓分钟: `{_fmt_num(stats['avg_duration'])}`",
            f"- 亏损月数: `{digest.get('negative_months', 'N/A')}`",
            f"- Stopout: `{stopout_text}{stopout_suffix}`",
            '',
            '### 月度表现',
            '',
            *_render_monthly_table(digest.get('monthly_stats', [])),
            '',
            '### 亏损月坏簇',
            '',
            *_render_negative_month_clusters(digest.get('negative_month_clusters', [])),
            '',
            '### 贡献簇',
            '',
            '#### 正贡献',
            '',
            *_render_cluster_table(digest['positive_clusters']),
            '',
            '#### 负贡献',
            '',
            *_render_cluster_table(digest['negative_clusters']),
            '',
            '### 判别因子',
            '',
            *_render_factor_table(digest['factor_edges']),
            '',
        ])
        lines.extend(_render_extremes('最佳样本', digest['best_trades']))
        lines.append('')
        lines.extend(_render_extremes('最差样本', digest['worst_trades']))

    return '\n'.join(lines).strip() + '\n'


def write_trade_csv(path: Path, symbol_digests: list[dict]):
    rows = []
    for digest in symbol_digests:
        details = digest.get('details') or {}
        for trade in details.get('trades', []):
            rows.append({key: trade.get(key) for key in CSV_COLUMNS})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _extract_date_token(path: Path) -> str | None:
    match = re.search(r'(\d{8})', path.stem)
    return match.group(1) if match else None


def candidate_log_paths(report_path: Path) -> list[Path]:
    candidates = []
    date_token = _extract_date_token(report_path)
    search_roots = [
        DEFAULT_WINE_TESTER / 'Agent-127.0.0.1-3000' / 'logs',
        DEFAULT_WINE_TESTER / 'logs',
    ]
    if DEFAULT_WINDOWS_TESTER.exists():
        search_roots.extend(DEFAULT_WINDOWS_TESTER.glob('*/Tester/Agent-127.0.0.1-3000/logs'))
        search_roots.extend(DEFAULT_WINDOWS_TESTER.glob('*/Tester/logs'))

    for root in search_roots:
        if not root.exists():
            continue
        if date_token:
            exact = root / f'{date_token}.log'
            if exact.exists():
                candidates.append(exact)
        candidates.extend(sorted(root.glob('*.log'), key=lambda p: p.stat().st_mtime, reverse=True)[:5])

    deduped = []
    seen = set()
    for path in candidates:
        path = path.resolve()
        if path in seen:
            continue
        deduped.append(path)
        seen.add(path)
    return deduped


def build_digest_data(report_content: str, log_content: str | None = None) -> tuple[dict, list[dict]]:
    report_data = parse_backtest_report_content(report_content)
    if report_data is None:
        raise ValueError('无法解析回测摘要报告')

    symbol_digests = []
    for row in report_data['symbols']:
        details = None
        if log_content:
            segment = find_matching_log_segment(
                log_content,
                row['symbol'],
                report_data['date_from'],
                report_data['date_to'],
                row['final_balance'],
            )
            if segment:
                details = parse_agent_log_segment_details(segment['lines'], row['symbol'])
        symbol_digests.append(build_symbol_digest(row, details, report_data.get('deposit')))
    return report_data, symbol_digests


def generate_backtest_digest(
    report_path: Path,
    log_path: Path | None = None,
    output_path: Path | None = None,
    export_csv: bool = False,
    csv_output_path: Path | None = None,
) -> dict:
    report_path = Path(report_path)
    report_content = read_text_auto(report_path)

    resolved_log_path = Path(log_path) if log_path else None
    log_content = None
    if resolved_log_path:
        log_content = read_text_auto(resolved_log_path)
    else:
        for candidate in candidate_log_paths(report_path):
            try:
                content = read_text_auto(candidate)
            except OSError:
                continue
            report_data = parse_backtest_report_content(report_content)
            if report_data is None:
                raise ValueError('无法解析回测摘要报告')
            if any(
                find_matching_log_segment(content, row['symbol'], report_data['date_from'], report_data['date_to'], row['final_balance'])
                for row in report_data['symbols']
            ):
                resolved_log_path = candidate
                log_content = content
                break

    report_data, symbol_digests = build_digest_data(report_content, log_content)
    output_path = Path(output_path) if output_path else report_path.with_suffix('.md')
    markdown = render_digest_markdown(report_data, symbol_digests, report_path, resolved_log_path)
    output_path.write_text(markdown, encoding='utf-8')

    result = {
        'report_path': report_path,
        'log_path': resolved_log_path,
        'output_path': output_path,
        'csv_path': None,
        'matched_symbols': [d['summary']['symbol'] for d in symbol_digests if d.get('details')],
    }

    if export_csv:
        csv_output_path = Path(csv_output_path) if csv_output_path else output_path.with_suffix('.trades.csv')
        write_trade_csv(csv_output_path, symbol_digests)
        result['csv_path'] = csv_output_path

    return result


def main():
    parser = argparse.ArgumentParser(description='提炼 MT5 回测报告，输出低 token Markdown 摘要。')
    parser.add_argument('--report', required=True, help='聚合摘要报告路径，如 results/backtest/v11_btc_m5_r21_20260521.txt')
    parser.add_argument('--log', help='可选：指定 Agent/Tester 日志路径')
    parser.add_argument('--output', help='Markdown 输出路径，默认与 report 同名 .md')
    parser.add_argument('--export-csv', action='store_true', help='额外导出逐单归因 CSV')
    parser.add_argument('--csv-output', help='CSV 输出路径，默认与 md 同名 .trades.csv')
    args = parser.parse_args()

    result = generate_backtest_digest(
        report_path=Path(args.report),
        log_path=Path(args.log) if args.log else None,
        output_path=Path(args.output) if args.output else None,
        export_csv=args.export_csv,
        csv_output_path=Path(args.csv_output) if args.csv_output else None,
    )

    print(f'Markdown 已生成: {result["output_path"]}')
    if result['log_path']:
        print(f'日志来源: {result["log_path"]}')
    else:
        print('日志来源: 未匹配到逐单日志，仅输出聚合摘要')
    if result['matched_symbols']:
        print(f'已匹配逐单归因: {", ".join(result["matched_symbols"])}')
    if result['csv_path']:
        print(f'CSV 已生成: {result["csv_path"]}')


if __name__ == '__main__':
    main()
