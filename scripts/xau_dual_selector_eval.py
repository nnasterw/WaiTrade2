#!/usr/bin/env python3
"""评估 XAU 双腿 selector 的月初窗口表现。"""

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from backtest_ledger import DEFAULT_LEDGER, load_ledger
from monthly_start_matrix import fmt_float, iter_months, parse_month, window_for_month


@dataclass(frozen=True)
class Feedback:
    trades: int
    net_r: float
    win_rate: float
    sl_pct: float


@dataclass(frozen=True)
class SelectorRule:
    probe_days: int = 5
    trend_min_trades: int = 20
    trend_min_net_r: float = -10.0
    trend_max_sl_pct: float = 78.0
    range_max_net_r: float = 999.0


_FEEDBACK_CACHE: dict[tuple[str, int], Feedback] = {}
_CSV_COUNT_CACHE: dict[str, int | None] = {}


def _parse_day(value: str | None) -> date | None:
    if not value:
        return None
    y, m, d = value.replace('.', '-').split('-')
    return date(int(y), int(m), int(d))


def best_record(
    records: list[dict],
    strategy: str,
    symbol: str,
    start: date,
    end: date,
    preferred_model: str | None = None,
) -> dict | None:
    date_from = start.strftime('%Y.%m.%d')
    date_to = end.strftime('%Y.%m.%d')
    matches = [
        record
        for record in records
        if record['strategy'] == strategy
        and record['symbol'] == symbol
        and record['date_from'] == date_from
        and record['date_to'] == date_to
    ]
    if preferred_model is not None:
        preferred = [record for record in matches if str(record.get('model') or '') == str(preferred_model)]
        if preferred:
            matches = preferred
    return max(matches, key=lambda record: record['final_balance']) if matches else None


def trade_csv_path(record: dict) -> Path:
    return Path(record['report_path']).with_suffix('.trades.csv')


def csv_trade_count(record: dict | None) -> int | None:
    if not record:
        return None
    cache_key = record['report_path']
    if cache_key in _CSV_COUNT_CACHE:
        return _CSV_COUNT_CACHE[cache_key]
    csv_path = trade_csv_path(record)
    if not csv_path.exists():
        _CSV_COUNT_CACHE[cache_key] = None
        return None
    with csv_path.open(newline='', encoding='utf-8') as f:
        count = sum(1 for _ in csv.DictReader(f))
    _CSV_COUNT_CACHE[cache_key] = count
    return count


def first_days_feedback(record: dict | None, probe_days: int) -> Feedback:
    if not record:
        return Feedback(trades=0, net_r=0.0, win_rate=0.0, sl_pct=100.0)
    cache_key = (record['report_path'], probe_days)
    cached = _FEEDBACK_CACHE.get(cache_key)
    if cached is not None:
        return cached

    csv_path = trade_csv_path(record)
    if not csv_path.exists():
        return Feedback(trades=0, net_r=0.0, win_rate=0.0, sl_pct=100.0)

    start = datetime.strptime(record['date_from'], '%Y.%m.%d').date()
    cutoff = start + timedelta(days=probe_days)
    r_values = []
    sl_count = 0
    with csv_path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            time_text = row.get('time') or row.get('entry_time')
            if not time_text:
                continue
            trade_day = datetime.fromisoformat(time_text.replace(' ', 'T')).date()
            if trade_day >= cutoff:
                continue
            try:
                r_value = float(row.get('r') or row.get('R') or 0.0)
            except ValueError:
                r_value = 0.0
            r_values.append(r_value)
            reason = (row.get('reason') or row.get('exit_signal') or '').lower()
            if reason == 'sl':
                sl_count += 1

    if not r_values:
        feedback = Feedback(trades=0, net_r=0.0, win_rate=0.0, sl_pct=100.0)
        _FEEDBACK_CACHE[cache_key] = feedback
        return feedback
    wins = sum(1 for value in r_values if value > 0)
    feedback = Feedback(
        trades=len(r_values),
        net_r=sum(r_values),
        win_rate=wins / len(r_values) * 100.0,
        sl_pct=sl_count / len(r_values) * 100.0,
    )
    _FEEDBACK_CACHE[cache_key] = feedback
    return feedback


def should_use_trend(range_feedback: Feedback, trend_feedback: Feedback, rule: SelectorRule) -> bool:
    return (
        trend_feedback.trades >= rule.trend_min_trades
        and trend_feedback.net_r >= rule.trend_min_net_r
        and trend_feedback.sl_pct <= rule.trend_max_sl_pct
        and range_feedback.net_r < rule.range_max_net_r
    )


def evaluate_selector(
    records: list[dict],
    symbol: str,
    range_strategy: str,
    trend_strategy: str,
    start_month: date,
    end_month: date,
    target_balance: float,
    rule: SelectorRule,
    available_to: date | None = None,
    preferred_model: str | None = None,
) -> tuple[list[dict], int]:
    rows = []
    missing = 0
    for month in iter_months(start_month, end_month):
        date_from, date_to, days = window_for_month(month, available_to)
        if days <= 0:
            continue
        range_record = best_record(records, range_strategy, symbol, date_from, date_to, preferred_model)
        trend_record = best_record(records, trend_strategy, symbol, date_from, date_to, preferred_model)
        if range_record is None:
            missing += 1
        if trend_record is None:
            missing += 1

        range_feedback = first_days_feedback(range_record, rule.probe_days)
        trend_feedback = first_days_feedback(trend_record, rule.probe_days)
        use_trend = trend_record is not None and should_use_trend(range_feedback, trend_feedback, rule)
        selected_name = 'trend' if use_trend else 'range'
        selected_record = trend_record if use_trend else range_record
        if selected_record is None and trend_record is not None:
            selected_name = 'trend'
            selected_record = trend_record

        balance = selected_record['final_balance'] if selected_record else 0.0
        rows.append(
            {
                'month': month,
                'date_from': date_from,
                'date_to': date_to,
                'selected': selected_name if selected_record else 'missing',
                'record': selected_record,
                'range_record': range_record,
                'trend_record': trend_record,
                'range_csv_rows': csv_trade_count(range_record),
                'trend_csv_rows': csv_trade_count(trend_record),
                'range_feedback': range_feedback,
                'trend_feedback': trend_feedback,
                'passed': balance >= target_balance,
            }
        )
    return rows, missing


def emit_brief(rows: list[dict], missing_count: int, target_balance: float):
    pass_count = sum(1 for row in rows if row['passed'])
    fail_count = len(rows) - pass_count
    min_balance = min((row['record']['final_balance'] for row in rows if row['record']), default=0.0)
    total_balance = sum((row['record']['final_balance'] for row in rows if row['record']), 0.0)
    csv_mismatches = 0
    for row in rows:
        for record_key, count_key in [('range_record', 'range_csv_rows'), ('trend_record', 'trend_csv_rows')]:
            record = row.get(record_key)
            if record is not None and row.get(count_key) != record['trades']:
                csv_mismatches += 1
    print(
        f'SUMMARY months={len(rows)} pass={pass_count} fail={fail_count} '
        f'missing_records={missing_count} min_balance=${min_balance:.2f} '
        f'balance_sum=${total_balance:.2f} target=${target_balance:.2f} '
        f'csv_mismatches={csv_mismatches}'
    )
    for row in rows:
        if row['passed']:
            continue
        record = row['record']
        if not record:
            print(f'FAIL {row["month"]:%Y-%m} MISSING window={row["date_from"]:%Y.%m.%d}~{row["date_to"]:%Y.%m.%d}')
            continue
        print(
            f'FAIL {row["month"]:%Y-%m} selected={row["selected"]} '
            f'balance=${record["final_balance"]:.2f} trades={record["trades"]} '
            f'daily={record["daily_trades"]:.1f} wr={record["win_rate"]:.1f}% '
            f'pf={fmt_float(record["profit_factor"], 2)}'
        )


def emit_selected(rows: list[dict], missing_count: int, target_balance: float):
    emit_brief(rows, missing_count, target_balance)
    for row in rows:
        record = row['record']
        rf = row['range_feedback']
        tf = row['trend_feedback']
        status = 'PASS' if row['passed'] else 'FAIL'
        if not record:
            print(f'{status} {row["month"]:%Y-%m} selected=missing')
            continue
        print(
            f'{status} {row["month"]:%Y-%m} selected={row["selected"]} '
            f'balance=${record["final_balance"]:.2f} trades={record["trades"]} '
            f'rf5=n{rf.trades}/R{rf.net_r:.1f}/SL{rf.sl_pct:.0f}% '
            f'tf5=n{tf.trades}/R{tf.net_r:.1f}/SL{tf.sl_pct:.0f}%'
        )


def emit_grid(records: list[dict], args):
    results = []
    for probe_days in [3, 5, 7, 10]:
        for min_trades in [10, 15, 20, 25, 30, 40, 50]:
            for min_net_r in [-30, -20, -15, -10, -5, 0, 5, 10]:
                for max_sl_pct in [65, 70, 75, 78, 80, 85, 90]:
                    rule = SelectorRule(
                        probe_days=probe_days,
                        trend_min_trades=min_trades,
                        trend_min_net_r=min_net_r,
                        trend_max_sl_pct=max_sl_pct,
                        range_max_net_r=args.range_max_net_r,
                    )
                    rows, missing = evaluate_selector(
                        records=records,
                        symbol=args.symbol,
                        range_strategy=args.range_strategy,
                        trend_strategy=args.trend_strategy,
                        start_month=parse_month(args.start),
                        end_month=parse_month(args.end),
                        available_to=_parse_day(args.available_to),
                        target_balance=args.target_balance,
                        rule=rule,
                    )
                    balances = [row['record']['final_balance'] for row in rows if row['record']]
                    results.append(
                        {
                            'pass': sum(1 for row in rows if row['passed']),
                            'months': len(rows),
                            'min_balance': min(balances, default=0.0),
                            'balance_sum': sum(balances, 0.0),
                            'trend_months': sum(1 for row in rows if row['selected'] == 'trend'),
                            'missing': missing,
                            'probe_days': probe_days,
                            'trend_min_trades': min_trades,
                            'trend_min_net_r': min_net_r,
                            'trend_max_sl_pct': max_sl_pct,
                        }
                    )

    results.sort(key=lambda row: (row['pass'], row['min_balance'], row['balance_sum']), reverse=True)
    for idx, row in enumerate(results[: args.grid_top], start=1):
        print(
            f'GRID rank={idx} pass={row["pass"]}/{row["months"]} '
            f'min_balance=${row["min_balance"]:.2f} balance_sum=${row["balance_sum"]:.2f} '
            f'trend_months={row["trend_months"]} missing_records={row["missing"]} '
            f'probe_days={row["probe_days"]} trend_min_trades={row["trend_min_trades"]} '
            f'trend_min_net_r={row["trend_min_net_r"]} trend_max_sl_pct={row["trend_max_sl_pct"]}'
        )


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description='评估 XAU range/trend 双腿 selector')
    parser.add_argument('--ledger', type=Path, default=DEFAULT_LEDGER)
    parser.add_argument('--symbol', default='XAUUSDm')
    parser.add_argument('--range-strategy', default='v11_single_selector')
    parser.add_argument('--trend-strategy', default='v11b_xau_r35_m1_tp15_nomonth')
    parser.add_argument('--start', default='2024.06')
    parser.add_argument('--end', default='2026.05')
    parser.add_argument('--available-to')
    parser.add_argument('--target-balance', type=float, default=270.0)
    parser.add_argument('--probe-days', type=int, default=5)
    parser.add_argument('--trend-min-trades', type=int, default=20)
    parser.add_argument('--trend-min-net-r', type=float, default=-10.0)
    parser.add_argument('--trend-max-sl-pct', type=float, default=78.0)
    parser.add_argument('--range-max-net-r', type=float, default=999.0, help='range probe 净R上限；默认近似禁用')
    parser.add_argument('--selected', action='store_true', help='输出每月选择明细')
    parser.add_argument('--grid', action='store_true', help='输出内置阈值网格Top结果')
    parser.add_argument('--grid-top', type=int, default=10)
    args = parser.parse_args(argv)

    records = load_ledger(args.ledger)
    if args.grid:
        emit_grid(records, args)
        return

    rule = SelectorRule(
        probe_days=args.probe_days,
        trend_min_trades=args.trend_min_trades,
        trend_min_net_r=args.trend_min_net_r,
        trend_max_sl_pct=args.trend_max_sl_pct,
        range_max_net_r=args.range_max_net_r,
    )
    rows, missing = evaluate_selector(
        records=records,
        symbol=args.symbol,
        range_strategy=args.range_strategy,
        trend_strategy=args.trend_strategy,
        start_month=parse_month(args.start),
        end_month=parse_month(args.end),
        available_to=_parse_day(args.available_to),
        target_balance=args.target_balance,
        rule=rule,
    )
    if args.selected:
        emit_selected(rows, missing, args.target_balance)
    else:
        emit_brief(rows, missing, args.target_balance)


if __name__ == '__main__':
    main()
