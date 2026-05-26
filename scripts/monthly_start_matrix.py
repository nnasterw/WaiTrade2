#!/usr/bin/env python3
"""汇总“每个月当首月”的 MT5 回测矩阵。"""

import argparse
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from mt5_common import RESULTS_DIR, parse_backtest_report_content


@dataclass(frozen=True)
class Leg:
    name: str
    symbol: str
    strategy: str


def parse_month(value: str) -> date:
    year, month = value.replace('.', '-').split('-')
    return date(int(year), int(month), 1)


def iter_months(start: date, end: date):
    current = start
    while current <= end:
        yield current
        year = current.year + (current.month // 12)
        month = current.month % 12 + 1
        current = date(year, month, 1)


def window_for_month(month_start: date, available_to: date | None) -> tuple[date, date, int]:
    end = month_start + timedelta(days=30)
    if available_to and end > available_to:
        end = available_to
    return month_start, end, max((end - month_start).days, 0)


def parse_leg(value: str) -> Leg:
    name, symbol, strategy = value.split(':', 2)
    return Leg(name=name, symbol=symbol, strategy=strategy)


def report_glob(strategy: str, start: date, end: date) -> str:
    date_from = start.strftime('%Y%m%d')
    date_to = end.strftime('%Y%m%d')
    return f'{strategy}_{date_from}_{date_to}_*.txt'


def find_report(leg: Leg, start: date, end: date) -> dict | None:
    matches = sorted(RESULTS_DIR.glob(report_glob(leg.strategy, start, end)))
    for path in reversed(matches):
        parsed = parse_backtest_report_content(path.read_text(encoding='utf-8'))
        if not parsed:
            continue
        for row in parsed['symbols']:
            if row['symbol'] == leg.symbol:
                return {
                    'path': path,
                    'trades': row['trades'],
                    'daily': row['daily_trades'],
                    'win_rate': row['win_rate'],
                    'pf': row['profit_factor'],
                    'balance': row['final_balance'],
                }
    return None


def fmt_float(value, digits=1):
    if value == float('inf'):
        return 'inf'
    return f'{value:.{digits}f}'


def emit_commands(legs: list[Leg], start: date, end: date, deposit: float, timeout: int):
    for leg in legs:
        print(
            'python3 scripts/mt5_cli_backtest.py --background '
            f'--strategy {leg.strategy} --symbol {leg.symbol} '
            f'--from {start.strftime("%Y.%m.%d")} --to {end.strftime("%Y.%m.%d")} '
            f'--deposit {deposit:g} --timeout {timeout}'
        )


def emit_brief(rows, missing_count: int, target_balance: float):
    passed_rows = []
    failed_rows = []
    for month, date_from, date_to, days, _, best in rows:
        if best is None:
            failed_rows.append((month, date_from, date_to, days, None, None))
            continue
        leg, result = best
        item = (month, date_from, date_to, days, leg, result)
        if result['balance'] >= target_balance:
            passed_rows.append(item)
        else:
            failed_rows.append(item)

    print(
        f'SUMMARY months={len(rows)} pass={len(passed_rows)} '
        f'fail={len(failed_rows)} missing_reports={missing_count}'
    )
    for month, date_from, date_to, days, leg, result in failed_rows:
        if result is None:
            print(f'FAIL {month:%Y-%m} MISSING window={date_from:%Y.%m.%d}~{date_to:%Y.%m.%d} days={days}')
            continue
        print(
            f'FAIL {month:%Y-%m} best={leg.name}/{leg.symbol}/{leg.strategy} '
            f'balance=${result["balance"]:.2f} trades={result["trades"]} '
            f'daily={result["daily"]:.1f} wr={result["win_rate"]:.1f}% '
            f'pf={fmt_float(result["pf"], 2)}'
        )


def main():
    parser = argparse.ArgumentParser(description='汇总月初启动回测矩阵')
    parser.add_argument('--start', required=True, help='起始月份, 如 2024.06')
    parser.add_argument('--end', required=True, help='结束月份, 如 2026.05')
    parser.add_argument('--available-to', help='可用历史截止日期 YYYY.MM.DD')
    parser.add_argument(
        '--leg',
        action='append',
        required=True,
        help='候选腿: 名称:品种:策略, 如 xau:XAUUSDm:v11xau',
    )
    parser.add_argument('--target-balance', type=float, default=300.0)
    parser.add_argument('--deposit', type=float, default=200.0)
    parser.add_argument('--timeout', type=int, default=360)
    parser.add_argument('--emit-missing-commands', action='store_true')
    parser.add_argument('--hide-missing', action='store_true', help='只输出缺失数量，不展开缺失清单')
    parser.add_argument('--only-failures', action='store_true', help='只输出未达标或缺失的月份')
    parser.add_argument('--brief', action='store_true', help='输出低 token 单行摘要和失败月份')
    args = parser.parse_args()

    start_month = parse_month(args.start)
    end_month = parse_month(args.end)
    available_to = None
    if args.available_to:
        y, m, d = args.available_to.replace('.', '-').split('-')
        available_to = date(int(y), int(m), int(d))
    legs = [parse_leg(item) for item in args.leg]

    missing = []
    rows = []
    for month in iter_months(start_month, end_month):
        date_from, date_to, days = window_for_month(month, available_to)
        if days <= 0:
            continue
        leg_results = []
        for leg in legs:
            result = find_report(leg, date_from, date_to)
            if result is None:
                missing.append((leg, date_from, date_to))
            else:
                leg_results.append((leg, result))

        best = None
        if leg_results:
            best = max(leg_results, key=lambda item: item[1]['balance'])
        rows.append((month, date_from, date_to, days, leg_results, best))

    if args.brief:
        emit_brief(rows, len(missing), args.target_balance)
        if args.emit_missing_commands and missing:
            print('COMMANDS')
            for leg, date_from, date_to in missing:
                emit_commands([leg], date_from, date_to, args.deposit, args.timeout)
        return

    print('| 月份 | 窗口 | 最佳腿 | 余额 | 交易 | 日均 | 胜率 | PF | 达标 |')
    print('|---|---|---|---:|---:|---:|---:|---:|---|')
    for month, date_from, date_to, days, _, best in rows:
        label = month.strftime('%Y-%m')
        window = f'{date_from:%Y.%m.%d}~{date_to:%Y.%m.%d} ({days}d)'
        if best is None:
            print(f'| {label} | {window} | MISSING |  |  |  |  |  | 否 |')
            continue
        leg, result = best
        passed = '是' if result['balance'] >= args.target_balance else '否'
        if args.only_failures and passed == '是':
            continue
        print(
            f'| {label} | {window} | {leg.name}/{leg.symbol}/{leg.strategy} | '
            f'${result["balance"]:.2f} | {result["trades"]} | '
            f'{result["daily"]:.1f} | {result["win_rate"]:.1f}% | '
            f'{fmt_float(result["pf"], 2)} | {passed} |'
        )

    if missing:
        print(f'\n缺失回测: {len(missing)}')
        if not args.hide_missing:
            for leg, date_from, date_to in missing:
                print(f'- {date_from:%Y.%m.%d}~{date_to:%Y.%m.%d}: {leg.name}/{leg.symbol}/{leg.strategy}')
        if args.emit_missing_commands:
            print('\n待跑命令:')
            for leg, date_from, date_to in missing:
                emit_commands([leg], date_from, date_to, args.deposit, args.timeout)


if __name__ == '__main__':
    main()
