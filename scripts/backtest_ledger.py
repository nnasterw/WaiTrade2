#!/usr/bin/env python3
"""构建和查询 MT5 回测结果 JSONL 仓库。"""

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path

from mt5_common import RESULTS_DIR, parse_backtest_report_content
from monthly_start_matrix import Leg, fmt_float, iter_months, parse_leg, parse_month, window_for_month


DEFAULT_LEDGER = RESULTS_DIR / 'backtest_ledger.jsonl'


def infer_strategy_from_report_path(path: Path) -> str:
    match = re.match(r'(.+?)_(\d{8})_(\d{8})(?:_.+)?$', path.stem)
    if not match:
        return path.stem
    return match.group(1)


def records_from_report(path: Path) -> list[dict]:
    parsed = parse_backtest_report_content(path.read_text(encoding='utf-8'))
    if not parsed:
        return []
    strategy = infer_strategy_from_report_path(path)
    rows = []
    for row in parsed['symbols']:
        rows.append(
            {
                'strategy': strategy,
                'strategy_name': parsed['strategy_name'],
                'symbol': row['symbol'],
                'date_from': parsed['date_from'],
                'date_to': parsed['date_to'],
                'days': parsed['days'],
                'deposit': parsed.get('deposit'),
                'trades': row['trades'],
                'daily_trades': row['daily_trades'],
                'win_rate': row['win_rate'],
                'profit_factor': row['profit_factor'],
                'net_r': row['net_r'],
                'final_balance': row['final_balance'],
                'report_path': str(path),
            }
        )
    return rows


def build_ledger(reports_dir: Path = RESULTS_DIR, output_path: Path = DEFAULT_LEDGER) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted(Path(reports_dir).glob('*.txt')):
        records.extend(records_from_report(path))
    with output_path.open('w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
    return len(records)


def load_ledger(path: Path = DEFAULT_LEDGER) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _record_matches_window(record: dict, leg: Leg, start: date, end: date) -> bool:
    return (
        record['strategy'] == leg.strategy
        and record['symbol'] == leg.symbol
        and record['date_from'] == start.strftime('%Y.%m.%d')
        and record['date_to'] == end.strftime('%Y.%m.%d')
    )


def query_monthly(
    records: list[dict],
    legs: list[Leg],
    start_month: date,
    end_month: date,
    target_balance: float,
    available_to: date | None = None,
) -> tuple[list[tuple], int]:
    missing = 0
    rows = []
    for month in iter_months(start_month, end_month):
        date_from, date_to, days = window_for_month(month, available_to)
        if days <= 0:
            continue
        found = []
        for leg in legs:
            matches = [record for record in records if _record_matches_window(record, leg, date_from, date_to)]
            if not matches:
                missing += 1
                continue
            best_record = max(matches, key=lambda record: record['final_balance'])
            found.append((leg, best_record))
        best = max(found, key=lambda item: item[1]['final_balance']) if found else None
        passed = bool(best and best[1]['final_balance'] >= target_balance)
        rows.append((month, date_from, date_to, days, best, passed))
    return rows, missing


def emit_monthly_brief(rows: list[tuple], missing_count: int):
    passed_count = sum(1 for row in rows if row[5])
    failed_count = len(rows) - passed_count
    print(f'SUMMARY months={len(rows)} pass={passed_count} fail={failed_count} missing_records={missing_count}')
    for month, date_from, date_to, days, best, passed in rows:
        if passed:
            continue
        if best is None:
            print(f'FAIL {month:%Y-%m} MISSING window={date_from:%Y.%m.%d}~{date_to:%Y.%m.%d} days={days}')
            continue
        leg, record = best
        print(
            f'FAIL {month:%Y-%m} best={leg.name}/{leg.symbol}/{leg.strategy} '
            f'balance=${record["final_balance"]:.2f} trades={record["trades"]} '
            f'daily={record["daily_trades"]:.1f} wr={record["win_rate"]:.1f}% '
            f'pf={fmt_float(record["profit_factor"], 2)}'
        )


def emit_monthly_selected(rows: list[tuple], missing_count: int):
    passed_count = sum(1 for row in rows if row[5])
    failed_count = len(rows) - passed_count
    print(f'SUMMARY months={len(rows)} pass={passed_count} fail={failed_count} missing_records={missing_count}')
    for month, date_from, date_to, days, best, passed in rows:
        if best is None:
            print(f'MONTH {month:%Y-%m} MISSING window={date_from:%Y.%m.%d}~{date_to:%Y.%m.%d} days={days}')
            continue
        leg, record = best
        status = 'PASS' if passed else 'FAIL'
        print(
            f'{status} {month:%Y-%m} best={leg.name}/{leg.symbol}/{leg.strategy} '
            f'balance=${record["final_balance"]:.2f} trades={record["trades"]} '
            f'daily={record["daily_trades"]:.1f} wr={record["win_rate"]:.1f}% '
            f'pf={fmt_float(record["profit_factor"], 2)} '
            f'window={date_from:%Y.%m.%d}~{date_to:%Y.%m.%d}'
        )


def _parse_day(value: str | None) -> date | None:
    if not value:
        return None
    y, m, d = value.replace('.', '-').split('-')
    return date(int(y), int(m), int(d))


def main():
    parser = argparse.ArgumentParser(description='构建和查询 MT5 回测结果 JSONL 仓库')
    subparsers = parser.add_subparsers(dest='command', required=True)

    build_parser = subparsers.add_parser('build', help='扫描 txt 报告并生成 JSONL ledger')
    build_parser.add_argument('--reports-dir', type=Path, default=RESULTS_DIR)
    build_parser.add_argument('--output', type=Path, default=DEFAULT_LEDGER)

    query_parser = subparsers.add_parser('query-monthly', help='从 ledger 查询月初窗口缺口')
    query_parser.add_argument('--ledger', type=Path, default=DEFAULT_LEDGER)
    query_parser.add_argument('--start', required=True)
    query_parser.add_argument('--end', required=True)
    query_parser.add_argument('--available-to')
    query_parser.add_argument('--target-balance', type=float, default=270.0)
    query_parser.add_argument('--leg', action='append', required=True)
    query_parser.add_argument('--selected', action='store_true', help='输出每月实际选中的最佳腿')

    args = parser.parse_args()
    if args.command == 'build':
        count = build_ledger(args.reports_dir, args.output)
        print(f'LEDGER records={count} path={args.output}')
        return

    records = load_ledger(args.ledger)
    rows, missing = query_monthly(
        records=records,
        legs=[parse_leg(item) for item in args.leg],
        start_month=parse_month(args.start),
        end_month=parse_month(args.end),
        target_balance=args.target_balance,
        available_to=_parse_day(args.available_to),
    )
    if args.selected:
        emit_monthly_selected(rows, missing)
    else:
        emit_monthly_brief(rows, missing)


if __name__ == '__main__':
    main()
