#!/usr/bin/env python3
"""消化 XAU MT5 回测报告为 digest/CSV，并可刷新审计。"""

import argparse
from pathlib import Path

from backtest_ledger import infer_strategy_from_report_path
from backtest_digest import generate_backtest_digest, read_text_auto
from mt5_common import RESULTS_DIR, parse_backtest_report_content
from xau_goal_audit import main as audit_main


DEFAULT_STRATEGIES = (
    'v11_single_selector,'
    'v11xau_range,'
    'v11xau_range_h15_block,'
    'v11xau_range_h1415_half,'
    'v11b_xau_r35_m1_tp15_nomonth,'
    'v11xau_trend,'
    'v11xau_trend_h04_block,'
    'v11xau_trend_h04_half'
)


def parse_strategy_filter(value: str) -> set[str] | None:
    if value.strip().lower() == 'all':
        return None
    return {item.strip() for item in value.split(',') if item.strip()}


def is_xau_report(path: Path, symbol: str) -> bool:
    try:
        parsed = parse_backtest_report_content(read_text_auto(path))
    except OSError:
        return False
    if not parsed:
        return False
    return any(row.get('symbol') == symbol for row in parsed.get('symbols', []))


def candidate_reports(reports_dir: Path, symbol: str, strategies: set[str] | None) -> list[Path]:
    return [
        path
        for path in sorted(Path(reports_dir).glob('*.txt'))
        if is_xau_report(path, symbol)
        and (strategies is None or infer_strategy_from_report_path(path) in strategies)
    ]


def needs_ingest(path: Path) -> bool:
    return not path.with_suffix('.md').exists() or not path.with_suffix('.trades.csv').exists()


def ingest_report(path: Path) -> dict:
    result = generate_backtest_digest(report_path=path, export_csv=True, brief=True)
    csv_path = result.get('csv_path')
    if csv_path and not result.get('matched_symbols') and Path(csv_path).exists():
        Path(csv_path).unlink()
        result['csv_path'] = None
    return result


def emit_ingest(args):
    reports = [
        path
        for path in candidate_reports(args.reports_dir, args.symbol, parse_strategy_filter(args.strategies))
        if needs_ingest(path)
    ]
    if args.limit > 0:
        reports = reports[: args.limit]
    print(f'INGEST candidates={len(reports)} symbol={args.symbol} strategies={args.strategies} dry_run={args.dry_run}')
    generated = 0
    csv_matched = 0
    for path in reports:
        if args.dry_run:
            print(f'INGEST_TODO {path}')
            continue
        result = ingest_report(path)
        generated += 1
        if result.get('csv_path'):
            csv_matched += 1
        status = 'csv' if result.get('csv_path') else 'md_only'
        print(f'INGEST_DONE {status} report={path} md={result["output_path"]}')
    if not args.dry_run:
        print(f'INGEST_SUMMARY generated={generated} csv_matched={csv_matched}')
    if args.audit:
        audit_args = ['--refresh-ledger', '--available-to', args.available_to]
        if args.commands:
            audit_args.append('--commands')
        audit_main(audit_args)


def main(argv=None):
    parser = argparse.ArgumentParser(description='消化 XAU MT5 回测报告为 digest/CSV')
    parser.add_argument('--reports-dir', type=Path, default=RESULTS_DIR)
    parser.add_argument('--symbol', default='XAUUSDm')
    parser.add_argument('--strategies', default=DEFAULT_STRATEGIES, help='逗号分隔策略过滤；all 表示全部XAU报告')
    parser.add_argument('--available-to', default='2026.05.26')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--audit', action='store_true', help='ingest 后刷新运行 xau_goal_audit')
    parser.add_argument('--commands', action='store_true', help='audit 时输出下一条补跑命令')
    args = parser.parse_args(argv)
    emit_ingest(args)


if __name__ == '__main__':
    main()
