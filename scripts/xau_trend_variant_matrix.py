#!/usr/bin/env python3
"""汇总 XAU 趋势腿变体的已测覆盖和缺口。"""

import argparse
from pathlib import Path

from backtest_ledger import DEFAULT_LEDGER, records_from_report
from mt5_common import RESULTS_DIR
from xau_dual_selector_eval import (
    SelectorRule,
    _parse_day,
    best_record,
    evaluate_selector,
    first_days_feedback,
    load_ledger,
    parse_month,
)


def load_report_records(reports_dir: Path) -> list[dict]:
    records = []
    for path in sorted(reports_dir.glob('*.txt')):
        records.extend(records_from_report(path))
    return records


def parse_variants(value: str) -> list[str]:
    return [item.strip() for item in value.split(',') if item.strip()]


def trend_month_rows(args) -> list[dict]:
    rows, _ = evaluate_selector(
        records=load_ledger(args.base_ledger),
        symbol=args.symbol,
        range_strategy=args.range_strategy,
        trend_strategy=args.base_trend_strategy,
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
        preferred_model=getattr(args, 'preferred_model', None),
    )
    return [row for row in rows if row['selected'] == 'trend']


def selected_leg_month_rows(args) -> list[dict]:
    if args.leg == 'trend':
        return trend_month_rows(args)
    rows, _ = selector_rows(args)
    return [row for row in rows if row['selected'] == args.leg]


def selector_rows(args) -> tuple[list[dict], int]:
    return evaluate_selector(
        records=load_ledger(args.base_ledger),
        symbol=args.symbol,
        range_strategy=args.range_strategy,
        trend_strategy=args.base_trend_strategy,
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
        preferred_model=getattr(args, 'preferred_model', None),
    )


def variant_matrix(args) -> tuple[list[dict], list[str]]:
    variants = parse_variants(args.variants)
    current_records = load_report_records(args.reports_dir)
    rows = []
    for selector_row in selected_leg_month_rows(args):
        records_by_variant = {}
        for variant in variants:
            records_by_variant[variant] = best_record(
                current_records,
                variant,
                args.symbol,
                selector_row['date_from'],
                selector_row['date_to'],
                getattr(args, 'preferred_model', None),
            )
        rows.append(
            {
                'month': selector_row['month'],
                'date_from': selector_row['date_from'],
                'date_to': selector_row['date_to'],
                'trend_feedback': selector_row.get('trend_feedback'),
                'selector_record': selector_row.get('record'),
                'records': records_by_variant,
            }
        )
    return rows, variants


def emit_matrix(rows: list[dict], variants: list[str]):
    print('| 月份 | ' + ' | '.join(variants) + ' | 状态 |')
    print('|---|' + '|'.join(['---:'] * len(variants)) + '|---|')
    for row in rows:
        values = []
        for variant in variants:
            record = row['records'].get(variant)
            values.append(f'${record["final_balance"]:.2f}' if record else '-')
        status = 'done' if all(row['records'].get(variant) for variant in variants) else 'missing'
        print(f'| {row["month"]:%Y-%m} | ' + ' | '.join(values) + f' | {status} |')

    print('SUMMARY variants=' + ','.join(variants))
    for variant in variants:
        balances = [row['records'][variant]['final_balance'] for row in rows if row['records'].get(variant)]
        if balances:
            print(
                f'VARIANT {variant} tested={len(balances)}/{len(rows)} '
                f'min=${min(balances):.2f} balance_sum=${sum(balances):.2f}'
            )
        else:
            print(f'VARIANT {variant} tested=0/{len(rows)} min=$0.00 balance_sum=$0.00')

    missing_months = [
        f'{row["month"]:%Y-%m}'
        for row in rows
        if not all(row['records'].get(variant) for variant in variants)
    ]
    print('MISSING ' + (','.join(missing_months) if missing_months else '-'))


def emit_commands(rows: list[dict], variants: list[str], args):
    missing = [row for row in rows if not all(row['records'].get(variant) for variant in variants)]
    if not missing:
        return
    if args.commands_sort == 'sensitivity':
        missing.sort(key=lambda row: h04_sensitivity(row, args))
    elif args.commands_sort == 'balance':
        missing.sort(key=row_selector_balance)
    strategy_arg = ','.join(variants)
    model = getattr(args, 'model', getattr(args, 'preferred_model', '4')) or '4'
    for row in missing:
        print(
            'python3 scripts/mt5_cli_backtest.py --background --brief '
            f'--strategies {strategy_arg} --symbol {args.symbol} '
            f'--from {row["date_from"]:%Y.%m.%d} --to {row["date_to"]:%Y.%m.%d} '
            f'--deposit {args.deposit:g} --timeout {args.timeout} --model {model}'
        )


def row_trend_feedback(row: dict, args):
    feedback = row.get('trend_feedback')
    if feedback is not None:
        return feedback
    base_record = row['records'].get(args.base_trend_strategy)
    return first_days_feedback(base_record, args.probe_days)


def row_selector_balance(row: dict) -> float:
    selector_record = row.get('selector_record')
    if selector_record:
        return selector_record['final_balance']
    balances = [record['final_balance'] for record in row.get('records', {}).values() if record]
    return min(balances) if balances else float('inf')


def h04_sensitivity(row: dict, args) -> float:
    return abs(row_trend_feedback(row, args).net_r - args.h04_half_min_net_r)


def emit_h04_rule(rows: list[dict], args):
    block_name = args.h04_block_strategy
    half_name = args.h04_half_strategy
    balances = []
    missing = []
    chosen_rows = []
    missing_rows = []
    for row in rows:
        feedback = row_trend_feedback(row, args)
        chosen = half_name if feedback.net_r >= args.h04_half_min_net_r else block_name
        record = row['records'].get(chosen)
        if not record:
            missing.append(f'{row["month"]:%Y-%m}')
            missing_rows.append((row, chosen, feedback))
            continue
        balances.append(record['final_balance'])
        chosen_rows.append((row, chosen, record, feedback))

    if balances:
        print(
            f'H04_RULE half_if_tf{args.probe_days}_net_r>={args.h04_half_min_net_r:g} '
            f'tested={len(balances)}/{len(rows)} min=${min(balances):.2f} '
            f'balance_sum=${sum(balances):.2f} missing={",".join(missing) if missing else "-"}'
        )
    else:
        print(
            f'H04_RULE half_if_tf{args.probe_days}_net_r>={args.h04_half_min_net_r:g} '
            f'tested=0/{len(rows)} min=$0.00 balance_sum=$0.00 '
            f'missing={",".join(missing) if missing else "-"}'
        )
    for row, chosen, record, feedback in chosen_rows:
        print(
            f'H04_PICK {row["month"]:%Y-%m} choose={chosen} '
            f'balance=${record["final_balance"]:.2f} '
            f'tf{args.probe_days}=n{feedback.trades}/R{feedback.net_r:.1f}/SL{feedback.sl_pct:.0f}%'
        )
    if getattr(args, 'h04_todo_sort', 'month') == 'sensitivity':
        missing_rows.sort(key=lambda item: abs(item[2].net_r - args.h04_half_min_net_r))
    for row, chosen, feedback in missing_rows:
        print(
            f'H04_TODO {row["month"]:%Y-%m} expect={chosen} '
            f'tf{args.probe_days}=n{feedback.trades}/R{feedback.net_r:.1f}/SL{feedback.sl_pct:.0f}% '
            f'delta={abs(feedback.net_r - args.h04_half_min_net_r):.1f} '
            f'window={row["date_from"]:%Y.%m.%d}~{row["date_to"]:%Y.%m.%d}'
        )


def h04_rule_stats(rows: list[dict], args, threshold: float) -> dict:
    block_name = args.h04_block_strategy
    half_name = args.h04_half_strategy
    balances = []
    missing = []
    half_count = 0
    for row in rows:
        feedback = row_trend_feedback(row, args)
        chosen = half_name if feedback.net_r >= threshold else block_name
        if chosen == half_name:
            half_count += 1
        record = row['records'].get(chosen)
        if not record:
            missing.append(f'{row["month"]:%Y-%m}')
            continue
        balances.append(record['final_balance'])
    return {
        'threshold': threshold,
        'tested': len(balances),
        'total': len(rows),
        'min_balance': min(balances, default=0.0),
        'balance_sum': sum(balances, 0.0),
        'half_count': half_count,
        'missing': missing,
    }


def parse_float_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(',') if item.strip()]


def emit_h04_grid(rows: list[dict], args):
    results = [h04_rule_stats(rows, args, threshold) for threshold in parse_float_list(args.h04_grid_thresholds)]
    results.sort(key=lambda item: (item['tested'], item['min_balance'], item['balance_sum']), reverse=True)
    for idx, item in enumerate(results[: args.h04_grid_top], start=1):
        print(
            f'H04_GRID rank={idx} half_if_tf{args.probe_days}_net_r>={item["threshold"]:g} '
            f'tested={item["tested"]}/{item["total"]} min=${item["min_balance"]:.2f} '
            f'balance_sum=${item["balance_sum"]:.2f} half_months={item["half_count"]} '
            f'missing={",".join(item["missing"]) if item["missing"] else "-"}'
        )


def combined_h04_rows(args) -> list[dict]:
    rows, _ = selector_rows(args)
    current_records = load_report_records(args.reports_dir)
    combined = []
    for row in rows:
        record = row['record']
        label = row['selected']
        h04_status = '-'
        if row['selected'] == 'trend':
            feedback = row['trend_feedback']
            chosen = (
                args.h04_half_strategy
                if feedback.net_r >= args.h04_half_min_net_r
                else args.h04_block_strategy
            )
            chosen_record = best_record(
                current_records,
                chosen,
                args.symbol,
                row['date_from'],
                row['date_to'],
                getattr(args, 'preferred_model', None),
            )
            if chosen_record:
                record = chosen_record
                label = chosen
                h04_status = 'applied'
            else:
                h04_status = f'fallback:{chosen}'
        combined.append({**row, 'combined_record': record, 'combined_label': label, 'h04_status': h04_status})
    return combined


def emit_combined_h04(args):
    rows = combined_h04_rows(args)
    balances = [row['combined_record']['final_balance'] for row in rows if row['combined_record']]
    pass_count = sum(1 for row in rows if row['combined_record'] and row['combined_record']['final_balance'] >= args.target_balance)
    applied = sum(1 for row in rows if row['h04_status'] == 'applied')
    fallback = [f'{row["month"]:%Y-%m}' for row in rows if row['h04_status'].startswith('fallback:')]
    print(
        f'COMBINED_H04 half_if_tf{args.probe_days}_net_r>={args.h04_half_min_net_r:g} '
        f'months={len(rows)} pass={pass_count}/{len(rows)} min=${min(balances, default=0.0):.2f} '
        f'balance_sum=${sum(balances):.2f} applied={applied} fallback={len(fallback)} '
        f'missing_h04={",".join(fallback) if fallback else "-"}'
    )
    for row in rows:
        record = row['combined_record']
        if not record:
            print(f'COMBINED_PICK {row["month"]:%Y-%m} selected=missing balance=$0.00 h04={row["h04_status"]}')
            continue
        print(
            f'COMBINED_PICK {row["month"]:%Y-%m} selected={row["combined_label"]} '
            f'balance=${record["final_balance"]:.2f} h04={row["h04_status"]}'
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description='汇总 XAU 趋势腿变体覆盖和缺口')
    parser.add_argument('--base-ledger', type=Path, default=DEFAULT_LEDGER)
    parser.add_argument('--reports-dir', type=Path, default=RESULTS_DIR)
    parser.add_argument('--symbol', default='XAUUSDm')
    parser.add_argument('--range-strategy', default='v11_single_selector')
    parser.add_argument('--base-trend-strategy', default='v11b_xau_r35_m1_tp15_nomonth')
    parser.add_argument('--variants', default='v11xau_trend,v11xau_trend_h04_block,v11xau_trend_h04_half')
    parser.add_argument('--leg', choices=['trend', 'range'], default='trend')
    parser.add_argument('--start', default='2024.06')
    parser.add_argument('--end', default='2026.05')
    parser.add_argument('--available-to')
    parser.add_argument('--target-balance', type=float, default=270.0)
    parser.add_argument('--probe-days', type=int, default=5)
    parser.add_argument('--trend-min-trades', type=int, default=20)
    parser.add_argument('--trend-min-net-r', type=float, default=-10.0)
    parser.add_argument('--trend-max-sl-pct', type=float, default=78.0)
    parser.add_argument('--range-max-net-r', type=float, default=999.0)
    parser.add_argument('--commands', action='store_true', help='输出缺失窗口的 MT5 后台回测命令')
    parser.add_argument('--commands-sort', choices=['month', 'sensitivity', 'balance'], default='month')
    parser.add_argument('--h04-rule', action='store_true', help='输出04禁入/半仓反馈规则的已测表现')
    parser.add_argument('--h04-grid', action='store_true', help='扫描04半仓净R阈值')
    parser.add_argument('--combined-h04', action='store_true', help='输出双腿selector叠加已验证h04规则后的整体表现')
    parser.add_argument('--h04-block-strategy', default='v11xau_trend_h04_block')
    parser.add_argument('--h04-half-strategy', default='v11xau_trend_h04_half')
    parser.add_argument('--h04-half-min-net-r', type=float, default=25.0)
    parser.add_argument('--h04-todo-sort', choices=['month', 'sensitivity'], default='month')
    parser.add_argument('--h04-grid-thresholds', default='0,5,10,15,20,23,25,28,30,35,40,45,50')
    parser.add_argument('--h04-grid-top', type=int, default=8)
    parser.add_argument('--preferred-model', help='优先选择指定 MT5 Model 的报告，例如 4=Real Ticks')
    parser.add_argument('--deposit', type=float, default=200.0)
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--model', default='4', help='MT5 Strategy Tester Model；默认4=Real ticks')
    args = parser.parse_args(argv)

    rows, variants = variant_matrix(args)
    emit_matrix(rows, variants)
    if args.h04_rule:
        emit_h04_rule(rows, args)
    if args.h04_grid:
        emit_h04_grid(rows, args)
    if args.combined_h04:
        emit_combined_h04(args)
    if args.commands:
        emit_commands(rows, variants, args)


if __name__ == '__main__':
    main()
