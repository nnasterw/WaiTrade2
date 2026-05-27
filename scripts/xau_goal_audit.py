#!/usr/bin/env python3
"""审计 XAU 双腿目标当前完成度。"""

import argparse
import tempfile
from pathlib import Path
from types import SimpleNamespace

from backtest_ledger import DEFAULT_LEDGER, build_ledger
from mt5_common import RESULTS_DIR
from xau_backtest_queue import queue_items
from xau_trend_variant_matrix import combined_h04_rows, variant_matrix


def make_args(args, leg: str, variants: str):
    return SimpleNamespace(**vars(args), leg=leg, variants=variants, preferred_model=str(args.required_model))


def missing_months(rows: list[dict], variants: list[str]) -> list[str]:
    return [
        f'{row["month"]:%Y-%m}'
        for row in rows
        if not all(row['records'].get(variant) for variant in variants)
    ]


def unverified_model_months(rows: list[dict], required_model: str) -> list[str]:
    result = []
    for row in rows:
        record = row.get('combined_record')
        if not record or str(record.get('model') or '') != required_model:
            result.append(f'{row["month"]:%Y-%m}')
    return result


def audit(args) -> dict:
    combined = combined_h04_rows(make_args(args, 'trend', args.trend_variants))
    balances = [row['combined_record']['final_balance'] for row in combined if row['combined_record']]
    pass_count = sum(
        1
        for row in combined
        if row['combined_record'] and row['combined_record']['final_balance'] >= args.target_balance
    )

    trend_rows, trend_variants = variant_matrix(make_args(args, 'trend', args.trend_variants))
    range_rows, range_variants = variant_matrix(make_args(args, 'range', args.range_variants))
    missing_trend = missing_months(trend_rows, trend_variants)
    missing_range = missing_months(range_rows, range_variants)
    model_unverified = unverified_model_months(combined, str(args.required_model))
    queue = queue_items(args)

    incomplete_reasons = []
    if pass_count != len(combined):
        incomplete_reasons.append('monthly_target')
    if missing_trend:
        incomplete_reasons.append('trend_h04_missing')
    if missing_range:
        incomplete_reasons.append('range_candidate_missing')
    if model_unverified:
        incomplete_reasons.append('model_unverified')

    return {
        'status': 'complete' if not incomplete_reasons else 'incomplete',
        'reasons': incomplete_reasons,
        'months': len(combined),
        'pass_count': pass_count,
        'min_balance': min(balances, default=0.0),
        'balance_sum': sum(balances),
        'missing_trend': missing_trend,
        'missing_range': missing_range,
        'model_unverified': model_unverified,
        'next_item': queue[0] if queue else None,
    }


def emit_audit(args):
    result = audit(args)
    next_item = result['next_item']
    next_text = '-'
    if next_item:
        next_text = f'{next_item["leg"]}:{next_item["month"]:%Y-%m}:{next_item["reason"]}'
    print(
        f'AUDIT status={result["status"]} reasons={",".join(result["reasons"]) if result["reasons"] else "-"} '
        f'months={result["months"]} pass={result["pass_count"]}/{result["months"]} '
        f'min=${result["min_balance"]:.2f} balance_sum=${result["balance_sum"]:.2f} '
        f'missing_trend_h04={len(result["missing_trend"])} '
        f'missing_range_candidates={len(result["missing_range"])} '
        f'model_unverified={len(result["model_unverified"])} next={next_text}'
    )
    if args.details:
        print('MISSING_TREND_H04 ' + (','.join(result['missing_trend']) if result['missing_trend'] else '-'))
        print('MISSING_RANGE_CANDIDATES ' + (','.join(result['missing_range']) if result['missing_range'] else '-'))
        print('MODEL_UNVERIFIED ' + (','.join(result['model_unverified']) if result['model_unverified'] else '-'))
    if args.commands and next_item:
        print('NEXT_COMMAND ' + next_item['command'])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='审计 XAU 双腿目标当前完成度')
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
    parser.add_argument('--include', choices=['all', 'range', 'trend'], default='all')
    parser.add_argument('--range-front-count', type=int, default=3)
    parser.add_argument('--required-model', default='4', help='完成目标所需的 MT5 Model，默认4=Real Ticks')
    parser.add_argument('--details', action='store_true')
    parser.add_argument('--commands', action='store_true', help='输出下一条建议 MT5 后台回测命令')
    parser.add_argument('--fail-on-incomplete', action='store_true', help='目标未完成时返回非0，适合作为门禁')
    parser.add_argument('--refresh-ledger', action='store_true', help='从当前 reports-dir 临时重建 ledger 后审计')
    args = parser.parse_args(argv)
    if args.refresh_ledger:
        with tempfile.NamedTemporaryFile(prefix='xau_goal_audit_', suffix='.jsonl') as tmp:
            args.base_ledger = Path(tmp.name)
            build_ledger(args.reports_dir, args.base_ledger)
            result = emit_audit(args)
    else:
        result = emit_audit(args)
    if args.fail_on_incomplete and result['status'] != 'complete':
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
