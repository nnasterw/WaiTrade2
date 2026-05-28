#!/usr/bin/env python3
"""
XAU 双腿选择器顺序复利模拟器

每月从前月结束余额重新启动（无EA状态延续），模拟 Exit-Restart 操作规则下的顺序复利。
"""

import argparse
import subprocess
import sys
from pathlib import Path

# 基于 probe 决策的月度腿选择（来自 xau_dual_selector_eval 分析结果）
MONTH_SELECTIONS = {
    '2024.06': 'range', '2024.07': 'range',
    '2024.08': 'trend', '2024.09': 'trend', '2024.10': 'trend',
    '2024.11': 'trend', '2024.12': 'trend',
    '2025.01': 'range',
    '2025.02': 'trend', '2025.03': 'trend', '2025.04': 'trend',
    '2025.05': 'trend', '2025.06': 'trend', '2025.07': 'trend',
    '2025.08': 'trend', '2025.09': 'trend', '2025.10': 'trend',
    '2025.11': 'trend', '2025.12': 'trend',
    '2026.01': 'range', '2026.02': 'range', '2026.03': 'range',
    '2026.04': 'range', '2026.05': 'range',
}

MONTHLY_WINDOWS = [
    ('2024.06.01', '2024.07.01'), ('2024.07.01', '2024.07.31'),
    ('2024.08.01', '2024.08.31'), ('2024.09.01', '2024.10.01'),
    ('2024.10.01', '2024.10.31'), ('2024.11.01', '2024.12.01'),
    ('2024.12.01', '2024.12.31'), ('2025.01.01', '2025.01.31'),
    ('2025.02.01', '2025.03.03'), ('2025.03.01', '2025.03.31'),
    ('2025.04.01', '2025.05.01'), ('2025.05.01', '2025.05.31'),
    ('2025.06.01', '2025.07.01'), ('2025.07.01', '2025.07.31'),
    ('2025.08.01', '2025.08.31'), ('2025.09.01', '2025.10.01'),
    ('2025.10.01', '2025.10.31'), ('2025.11.01', '2025.12.01'),
    ('2025.12.01', '2025.12.31'), ('2026.01.01', '2026.01.31'),
    ('2026.02.01', '2026.03.03'), ('2026.03.01', '2026.03.31'),
    ('2026.04.01', '2026.05.01'), ('2026.05.01', '2026.05.27'),
]


def parse_args():
    p = argparse.ArgumentParser(description='XAU双腿选择器顺序复利月度模拟')
    p.add_argument('--range-strategy', default='v11xau_r39_range_lot5')
    p.add_argument('--trend-strategy', default='v11xau_r39_trend_lot5')
    p.add_argument('--symbol', default='XAUUSDm')
    p.add_argument('--start-deposit', type=float, default=200.0)
    p.add_argument('--exit-threshold', type=float, default=0.0,
                   help='余额超过此值时重置（0=不重置）')
    p.add_argument('--restart-balance', type=float, default=200.0)
    p.add_argument('--target-pct', type=float, default=35.0)
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--model', type=int, default=4)
    p.add_argument('--dry-run', action='store_true', help='只显示计划，不运行回测')
    return p.parse_args()


def run_monthly_backtest(strategy, symbol, date_from, date_to, deposit, timeout, model):
    """运行单月回测，返回最终余额"""
    cmd = [
        'python3', 'scripts/mt5_cli_backtest.py',
        '--background', '--brief',
        '--strategies', strategy,
        '--symbol', symbol,
        '--from', date_from, '--to', date_to,
        '--deposit', str(deposit),
        '--timeout', str(timeout),
        '--model', str(model),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr

    for line in output.splitlines():
        if line.startswith('BRIEF'):
            parts = dict(p.split('=') for p in line.split() if '=' in p)
            bal = parts.get('balance', '').replace('$', '')
            try:
                return float(bal), output
            except ValueError:
                pass
    return None, output


def main():
    args = parse_args()
    balance = args.start_deposit
    total_withdrawn = 0.0
    results = []

    print(f'顺序复利模拟: {args.range_strategy}(range) + {args.trend_strategy}(trend)')
    print(f'初始余额: ${balance:.0f}  退出阈值: ${args.exit_threshold:.0f}  重启: ${args.restart_balance:.0f}')
    print(f'目标: 每月≥{args.target_pct}%')
    print()
    print(f'{"月份":12s} {"腿":6s} {"开始余额":>12s} {"收盘余额":>12s} {"收益%":>10s} {"状态":4s}')
    print('-' * 65)

    pass_count = fail_count = 0

    for date_from, date_to in MONTHLY_WINDOWS:
        month_key = date_from[:7]
        leg = MONTH_SELECTIONS.get(month_key, 'range')
        strategy = args.trend_strategy if leg == 'trend' else args.range_strategy

        if args.dry_run:
            print(f'{month_key:12s} {leg:6s} ${balance:>11.0f} [DRY RUN]')
            continue

        open_bal = balance
        final_bal, raw_output = run_monthly_backtest(
            strategy, args.symbol, date_from, date_to,
            balance, args.timeout, args.model
        )

        if final_bal is None:
            print(f'{month_key:12s} {leg:6s} ${open_bal:>11.0f} [FAILED] {raw_output[-200:]}')
            continue

        pct = (final_bal - open_bal) / open_bal * 100
        passed = pct >= args.target_pct
        flag = '✓' if passed else '✗'
        if passed:
            pass_count += 1
        else:
            fail_count += 1

        balance = final_bal

        # Exit-Restart 逻辑
        exit_note = ''
        if args.exit_threshold > 0 and balance >= args.exit_threshold:
            withdrawn = balance - args.restart_balance
            total_withdrawn += withdrawn
            exit_note = f'  [退出→${args.restart_balance:.0f}, 提现${withdrawn:.0f}]'
            balance = args.restart_balance

        print(f'{month_key:12s} {leg:6s} ${open_bal:>11.0f} ${final_bal:>11.0f} {pct:>9.1f}% {flag}{exit_note}')
        results.append({'month': month_key, 'pct': pct, 'passed': passed, 'leg': leg})

    if not args.dry_run:
        total = pass_count + fail_count
        print()
        print(f'{'=' * 65}')
        print(f'达标: {pass_count}/{total}月  未达标: {fail_count}/{total}月')
        if args.exit_threshold > 0:
            print(f'累计提现: ${total_withdrawn:.0f}  当前余额: ${balance:.0f}')


if __name__ == '__main__':
    main()
