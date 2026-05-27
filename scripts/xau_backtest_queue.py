#!/usr/bin/env python3
"""输出 XAU 双腿下一批 MT5 补跑队列。"""

import argparse
from pathlib import Path
from types import SimpleNamespace

from backtest_ledger import DEFAULT_LEDGER
from mt5_common import RESULTS_DIR
from xau_trend_variant_matrix import (
    h04_sensitivity,
    row_selector_balance,
    variant_matrix,
)


def make_matrix_args(args, leg: str, variants: str):
    return SimpleNamespace(
        base_ledger=args.base_ledger,
        reports_dir=args.reports_dir,
        symbol=args.symbol,
        range_strategy=args.range_strategy,
        base_trend_strategy=args.base_trend_strategy,
        variants=variants,
        leg=leg,
        start=args.start,
        end=args.end,
        available_to=args.available_to,
        target_balance=args.target_balance,
        probe_days=args.probe_days,
        trend_min_trades=args.trend_min_trades,
        trend_min_net_r=args.trend_min_net_r,
        trend_max_sl_pct=args.trend_max_sl_pct,
        range_max_net_r=args.range_max_net_r,
        h04_half_min_net_r=args.h04_half_min_net_r,
        h04_block_strategy=args.h04_block_strategy,
        h04_half_strategy=args.h04_half_strategy,
    )


def missing_items(rows: list[dict], variants: list[str]) -> list[dict]:
    return [row for row in rows if not all(row['records'].get(variant) for variant in variants)]


def command(row: dict, variants: list[str], args) -> str:
    model = getattr(args, 'model', getattr(args, 'required_model', '4'))
    return (
        'python3 scripts/mt5_cli_backtest.py --background --brief '
        f'--strategies {",".join(variants)} --symbol {args.symbol} '
        f'--from {row["date_from"]:%Y.%m.%d} --to {row["date_to"]:%Y.%m.%d} '
        f'--deposit {args.deposit:g} --timeout {args.timeout} --model {model}'
    )


def queue_items(args) -> list[dict]:
    items = []
    if args.include in ('all', 'range'):
        range_args = make_matrix_args(args, 'range', args.range_variants)
        rows, variants = variant_matrix(range_args)
        for idx, row in enumerate(sorted(missing_items(rows, variants), key=row_selector_balance)):
            phase = 'range_front' if idx < args.range_front_count else 'range_rest'
            phase_rank = 0 if phase == 'range_front' else 2
            items.append({
                'leg': 'range',
                'phase': phase,
                'month': row['month'],
                'reason': f'low_balance=${row_selector_balance(row):.2f}',
                'sort_key': (phase_rank, row_selector_balance(row)),
                'command': command(row, variants, args),
            })

    if args.include in ('all', 'trend'):
        trend_args = make_matrix_args(args, 'trend', args.trend_variants)
        rows, variants = variant_matrix(trend_args)
        for row in sorted(missing_items(rows, variants), key=lambda item: h04_sensitivity(item, trend_args)):
            items.append({
                'leg': 'trend',
                'phase': 'trend_h04',
                'month': row['month'],
                'reason': f'h04_delta={h04_sensitivity(row, trend_args):.1f}R',
                'sort_key': (1, h04_sensitivity(row, trend_args)),
                'command': command(row, variants, args),
            })

    items.sort(key=lambda item: item['sort_key'])
    return items


def emit_queue(args):
    all_items = queue_items(args)
    items = all_items[: args.top] if args.top > 0 else all_items
    print(
        f'QUEUE shown={len(items)} available={len(all_items)} include={args.include} '
        f'range_variants={args.range_variants} trend_variants={args.trend_variants}'
    )
    for idx, item in enumerate(items, start=1):
        print(
            f'QUEUE_ITEM rank={idx} leg={item["leg"]} phase={item["phase"]} month={item["month"]:%Y-%m} '
            f'reason={item["reason"]}'
        )
        if args.commands:
            print(item['command'])


def main(argv=None):
    parser = argparse.ArgumentParser(description='输出 XAU 双腿下一批 MT5 补跑队列')
    parser.add_argument('--base-ledger', type=Path, default=DEFAULT_LEDGER)
    parser.add_argument('--reports-dir', type=Path, default=RESULTS_DIR)
    parser.add_argument('--symbol', default='XAUUSDm')
    parser.add_argument('--range-strategy', default='v11_single_selector')
    parser.add_argument('--base-trend-strategy', default='v11b_xau_r35_m1_tp15_nomonth')
    parser.add_argument('--range-variants', default='v11_single_selector,v11xau_range_h15_block,v11xau_range_h1415_half')
    parser.add_argument('--trend-variants', default='v11xau_trend,v11xau_trend_h04_block,v11xau_trend_h04_half')
    parser.add_argument('--start', default='2024.06')
    parser.add_argument('--end', default='2026.05')
    parser.add_argument('--available-to')
    parser.add_argument('--target-balance', type=float, default=270.0)
    parser.add_argument('--probe-days', type=int, default=5)
    parser.add_argument('--trend-min-trades', type=int, default=20)
    parser.add_argument('--trend-min-net-r', type=float, default=-10.0)
    parser.add_argument('--trend-max-sl-pct', type=float, default=78.0)
    parser.add_argument('--range-max-net-r', type=float, default=999.0)
    parser.add_argument('--h04-half-min-net-r', type=float, default=25.0)
    parser.add_argument('--h04-block-strategy', default='v11xau_trend_h04_block')
    parser.add_argument('--h04-half-strategy', default='v11xau_trend_h04_half')
    parser.add_argument('--deposit', type=float, default=200.0)
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--model', default='4', help='MT5 Strategy Tester Model；默认4=Real ticks')
    parser.add_argument('--include', choices=['all', 'range', 'trend'], default='all')
    parser.add_argument('--range-front-count', type=int, default=3, help='all模式下优先放在trend前的range薄弱月数量')
    parser.add_argument('--top', type=int, default=0, help='只输出前N个；0表示全部')
    parser.add_argument('--commands', action='store_true')
    args = parser.parse_args(argv)
    emit_queue(args)


if __name__ == '__main__':
    main()
