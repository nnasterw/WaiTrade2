#!/usr/bin/env python3
"""对比 XAU 趋势腿/震荡腿边缘月与强月的逐单坏簇。"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

from xau_dual_selector_eval import (
    DEFAULT_LEDGER,
    SelectorRule,
    _parse_day,
    evaluate_selector,
    load_ledger,
    parse_month,
    trade_csv_path,
)


def _to_float(value) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def parse_float_bins(value: str | None) -> list[float]:
    if not value:
        return []
    return sorted(float(item.strip()) for item in value.split(',') if item.strip())


def bucket_key(raw_value: str | None, numeric_bins: list[float] | None = None) -> str:
    value = (raw_value or '').strip()
    if not value:
        return 'NA'
    if not numeric_bins:
        return value

    try:
        number = float(value)
    except ValueError:
        return 'NA'
    for limit in numeric_bins:
        if number < limit:
            return f'<{limit:g}'
    return f'>={numeric_bins[-1]:g}'


def selected_leg_rows(args) -> list[dict]:
    rows, _ = evaluate_selector(
        records=load_ledger(args.ledger),
        symbol=args.symbol,
        range_strategy=args.range_strategy,
        trend_strategy=args.trend_strategy,
        start_month=parse_month(args.start),
        end_month=parse_month(args.end),
        available_to=_parse_day(args.available_to),
        target_balance=args.target_balance,
        rule=SelectorRule(
            probe_days=args.probe_days,
            trend_min_trades=args.trend_min_trades,
            trend_min_net_r=args.trend_min_net_r,
            trend_max_sl_pct=args.trend_max_sl_pct,
            range_max_net_r=args.range_max_net_r,
        ),
    )
    record_key = f'{args.leg}_record'
    result = []
    for row in rows:
        if row['selected'] != args.leg or not row.get(record_key):
            continue
        result.append({**row, 'analysis_record': row[record_key]})
    return result


def read_trade_rows(record: dict) -> list[dict]:
    path = trade_csv_path(record)
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def bucket_contrast(
    rows: list[dict],
    edge_months: set[str],
    strong_months: set[str],
    field: str,
    numeric_bins: list[float] | None = None,
) -> list[dict]:
    buckets = defaultdict(lambda: {
        'all_r': 0.0,
        'all_n': 0,
        'edge_r': 0.0,
        'edge_n': 0,
        'strong_r': 0.0,
        'strong_n': 0,
        'months': set(),
    })
    for row in rows:
        month = row['month'].strftime('%Y-%m')
        for trade in read_trade_rows(row['analysis_record']):
            key = bucket_key(trade.get(field), numeric_bins)
            r_value = _to_float(trade.get('r'))
            bucket = buckets[key]
            bucket['all_r'] += r_value
            bucket['all_n'] += 1
            bucket['months'].add(month)
            if month in edge_months:
                bucket['edge_r'] += r_value
                bucket['edge_n'] += 1
            if month in strong_months:
                bucket['strong_r'] += r_value
                bucket['strong_n'] += 1

    result = []
    for key, bucket in buckets.items():
        result.append({
            'key': key,
            'all_r': bucket['all_r'],
            'all_n': bucket['all_n'],
            'edge_r': bucket['edge_r'],
            'edge_n': bucket['edge_n'],
            'strong_r': bucket['strong_r'],
            'strong_n': bucket['strong_n'],
            'month_count': len(bucket['months']),
        })
    return sorted(result, key=lambda item: (-max(-item['edge_r'], 0.0), item['strong_r']))


def emit_contrast(
    rows: list[dict],
    field: str,
    edge_count: int,
    strong_count: int,
    top: int,
    numeric_bins: list[float] | None = None,
):
    sorted_by_balance = sorted(rows, key=lambda row: row['analysis_record']['final_balance'])
    edge_rows = sorted_by_balance[:edge_count]
    strong_rows = sorted_by_balance[-strong_count:]
    edge_months = {row['month'].strftime('%Y-%m') for row in edge_rows}
    strong_months = {row['month'].strftime('%Y-%m') for row in strong_rows}

    print(
        f'SUMMARY {rows[0].get("selected", "unknown") if rows else "unknown"}_months={len(rows)} field={field} '
        f'leg={rows[0].get("selected", "unknown") if rows else "unknown"} '
        f'bins={",".join(f"{item:g}" for item in numeric_bins) if numeric_bins else "-"} '
        f'edge={",".join(sorted(edge_months))} strong={",".join(sorted(strong_months))}'
    )
    for row in edge_rows:
        rec = row['analysis_record']
        print(f'EDGE month={row["month"]:%Y-%m} balance=${rec["final_balance"]:.2f} trades={rec["trades"]}')
    for row in strong_rows:
        rec = row['analysis_record']
        print(f'STRONG month={row["month"]:%Y-%m} balance=${rec["final_balance"]:.2f} trades={rec["trades"]}')

    for item in bucket_contrast(rows, edge_months, strong_months, field, numeric_bins)[:top]:
        edge_gain = max(-item['edge_r'], 0.0)
        print(
            f'BUCKET {field}={item["key"]} edge_gain={edge_gain:.2f} '
            f'edge_r={item["edge_r"]:.2f} edge_n={item["edge_n"]} '
            f'strong_r={item["strong_r"]:.2f} strong_n={item["strong_n"]} '
            f'all_r={item["all_r"]:.2f} all_n={item["all_n"]} months={item["month_count"]}'
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description='对比 XAU 趋势腿/震荡腿边缘月/强月坏簇')
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
    parser.add_argument('--range-max-net-r', type=float, default=999.0)
    parser.add_argument('--leg', choices=['trend', 'range'], default='trend')
    parser.add_argument('--field', default='hour')
    parser.add_argument('--numeric-bins', help='逗号分隔数值分桶边界，例如 0.5,1,2,5')
    parser.add_argument('--edge-count', type=int, default=3)
    parser.add_argument('--strong-count', type=int, default=4)
    parser.add_argument('--top', type=int, default=8)
    args = parser.parse_args(argv)

    rows = selected_leg_rows(args)
    if not rows:
        print(f'SUMMARY {args.leg}_months=0')
        return 1
    emit_contrast(rows, args.field, args.edge_count, args.strong_count, args.top, parse_float_bins(args.numeric_bins))
    return 0


if __name__ == '__main__':
    sys.exit(main())
