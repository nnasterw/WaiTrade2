#!/usr/bin/env python3
"""将逐单 CSV 压缩为低 token 因子摘要。"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def _to_float(value) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def read_trades(path: Path) -> list[dict]:
    with Path(path).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def summarize_bucket(trades: list[dict]) -> dict:
    total_r = sum(_to_float(row.get('r')) for row in trades)
    wins = sum(1 for row in trades if _to_float(row.get('r')) > 0)
    count = len(trades)
    return {
        'count': count,
        'total_r': total_r,
        'win_rate': wins / count * 100 if count else 0.0,
    }


def group_by(trades: list[dict], field: str) -> dict[str, list[dict]]:
    groups = defaultdict(list)
    for row in trades:
        key = (row.get(field) or '').strip() or 'NA'
        groups[key].append(row)
    return dict(groups)


def best_and_worst(groups: dict[str, list[dict]], top: int) -> tuple[list[tuple], list[tuple]]:
    scored = [(key, summarize_bucket(rows)) for key, rows in groups.items()]
    positives = sorted(scored, key=lambda item: item[1]['total_r'], reverse=True)[:top]
    negatives = sorted(scored, key=lambda item: item[1]['total_r'])[:top]
    return positives, negatives


def _line(prefix: str, key: str, stats: dict) -> str:
    return (
        f'{prefix} {key} count={stats["count"]} '
        f'total_r={stats["total_r"]:.2f} win_rate={stats["win_rate"]:.1f}%'
    )


def render_summary(trades: list[dict], top: int = 3) -> str:
    summary = summarize_bucket(trades)
    lines = [
        f'SUMMARY trades={summary["count"]} total_r={summary["total_r"]:.2f} win_rate={summary["win_rate"]:.1f}%'
    ]

    pos_hours, neg_hours = best_and_worst(group_by(trades, 'hour'), top)
    for key, stats in pos_hours:
        lines.append(_line('POS', f'hour={key}', stats))
    for key, stats in neg_hours:
        prefix = 'NEG' if stats['total_r'] < 0 else 'LOW'
        lines.append(_line(prefix, f'hour={key}', stats))

    exit_groups = {}
    for row in trades:
        key = (row.get('exit_signal') or row.get('reason') or '').strip() or 'NA'
        exit_groups.setdefault(key, []).append(row)
    exit_rows = sorted(
        ((key, summarize_bucket(rows)) for key, rows in exit_groups.items()),
        key=lambda item: abs(item[1]['total_r']),
        reverse=True,
    )[: max(top * 2, 1)]
    for key, stats in exit_rows:
        lines.append(_line('EXIT', key, stats))
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description='将 trades.csv 聚合为低 token 摘要')
    parser.add_argument('--csv', required=True, type=Path)
    parser.add_argument('--top', type=int, default=3)
    args = parser.parse_args(argv)
    print(render_summary(read_trades(args.csv), top=args.top), end='')


if __name__ == '__main__':
    main()
