#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
from dataclasses import dataclass
from pathlib import Path

from portfolio_monthly_scan import DEFAULT_MONTHS, MonthlySeries, load_series


@dataclass(frozen=True)
class ScheduleResult:
    label: str
    choice_by_month: dict[str, str]
    monthly_pnl: dict[str, float]
    monthly_trades: dict[str, int]
    bad: list[tuple[str, float]]
    total_pnl: float
    daily_trades: float


def parse_series(raw: str) -> tuple[str, Path]:
    if "=" in raw:
        name, path = raw.split("=", 1)
        return name.strip(), Path(path.strip())
    path = Path(raw)
    return path.name.replace(".trades.csv", ""), path


def eval_schedule(
    label: str,
    series_by_name: dict[str, MonthlySeries],
    choice_by_month: dict[str, str],
    months: list[str],
    days: int,
) -> ScheduleResult:
    monthly_pnl = {}
    monthly_trades = {}
    for month in months:
        name = choice_by_month[month]
        series = series_by_name[name]
        monthly_pnl[month] = series.pnl_by_month.get(month, 0.0)
        monthly_trades[month] = series.trades_by_month.get(month, 0)

    bad = [(month, pnl) for month, pnl in monthly_pnl.items() if pnl < 0]
    return ScheduleResult(
        label=label,
        choice_by_month=dict(choice_by_month),
        monthly_pnl=monthly_pnl,
        monthly_trades=monthly_trades,
        bad=bad,
        total_pnl=sum(monthly_pnl.values()),
        daily_trades=sum(monthly_trades.values()) / days,
    )


def switch_scan(
    names: list[str],
    series_by_name: dict[str, MonthlySeries],
    months: list[str],
    days: int,
) -> list[ScheduleResult]:
    results = []
    for early, late in itertools.permutations(names, 2):
        for cut_index in range(1, len(months)):
            cut_month = months[cut_index]
            choice_by_month = {
                month: early if index < cut_index else late
                for index, month in enumerate(months)
            }
            results.append(
                eval_schedule(
                    f"{early} until {months[cut_index - 1]}, then {late} from {cut_month}",
                    series_by_name,
                    choice_by_month,
                    months,
                    days,
                )
            )
    return results


def override_scan(
    seed: ScheduleResult,
    names: list[str],
    series_by_name: dict[str, MonthlySeries],
    months: list[str],
    days: int,
    max_overrides: int,
    override_months: list[str],
) -> list[ScheduleResult]:
    results = []
    month_choices = [month for month in override_months if month in months]
    if max_overrides <= 0 or not month_choices:
        return results

    for size in range(1, max_overrides + 1):
        for selected_months in itertools.combinations(month_choices, size):
            choices_per_month = []
            for month in selected_months:
                current = seed.choice_by_month[month]
                choices_per_month.append([name for name in names if name != current])

            for replacement_names in itertools.product(*choices_per_month):
                choice_by_month = dict(seed.choice_by_month)
                tags = []
                for month, name in zip(selected_months, replacement_names):
                    choice_by_month[month] = name
                    tags.append(f"{month}->{name}")
                results.append(
                    eval_schedule(
                        f"{seed.label}; override " + ", ".join(tags),
                        series_by_name,
                        choice_by_month,
                        months,
                        days,
                    )
                )
    return results


def print_result(result: ScheduleResult, max_bad_detail: int, show_months: bool) -> None:
    bad_text = ", ".join(f"{month}:{pnl:.2f}" for month, pnl in result.bad[:max_bad_detail])
    if len(result.bad) > max_bad_detail:
        bad_text += ", ..."
    print(
        f"{result.label} | bad={len(result.bad)} | total={result.total_pnl:.2f} | "
        f"daily~{result.daily_trades:.2f} | {bad_text}"
    )
    if show_months:
        print("  choices: " + ", ".join(f"{month}:{result.choice_by_month[month]}" for month in result.choice_by_month))
        print("  pnl: " + ", ".join(f"{month}:{result.monthly_pnl[month]:.2f}" for month in result.monthly_pnl))


def sort_results(results: list[ScheduleResult]) -> list[ScheduleResult]:
    return sorted(results, key=lambda item: (len(item.bad), -item.total_pnl, -item.daily_trades))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Scan simple monthly schedule proxies across MT5 trade CSVs. "
            "This is not a valid account-level backtest; use it to rank ideas before MT5 validation."
        )
    )
    parser.add_argument("--series", action="append", required=True, help="NAME=path.trades.csv")
    parser.add_argument("--months", default=",".join(DEFAULT_MONTHS), help="Comma-separated months")
    parser.add_argument("--days", type=int, default=720)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--max-bad-detail", type=int, default=8)
    parser.add_argument("--switch-scan", action="store_true", help="Scan one calendar switch point")
    parser.add_argument("--override-size", type=int, default=0, help="Add up to N hindsight month overrides to each seed")
    parser.add_argument(
        "--override-months",
        default="",
        help="Comma-separated override months. Defaults to each seed's negative months.",
    )
    parser.add_argument("--show-months", action="store_true")
    args = parser.parse_args()

    months = [part.strip() for part in args.months.split(",") if part.strip()]
    series_by_name: dict[str, MonthlySeries] = {}
    for raw in args.series:
        name, path = parse_series(raw)
        if name in series_by_name:
            raise SystemExit(f"duplicate series name: {name}")
        if not path.exists():
            raise SystemExit(f"missing series file: {path}")
        series_by_name[name] = load_series(path, name)

    names = list(series_by_name)
    seeds: list[ScheduleResult] = []
    for name in names:
        seeds.append(
            eval_schedule(
                name,
                series_by_name,
                {month: name for month in months},
                months,
                args.days,
            )
        )

    if args.switch_scan:
        seeds.extend(switch_scan(names, series_by_name, months, args.days))

    results = list(seeds)
    if args.override_size > 0:
        for seed in seeds:
            if args.override_months:
                override_months = [part.strip() for part in args.override_months.split(",") if part.strip()]
            else:
                override_months = [month for month, _pnl in seed.bad]
            results.extend(
                override_scan(
                    seed,
                    names,
                    series_by_name,
                    months,
                    args.days,
                    args.override_size,
                    override_months,
                )
            )

    print("# 月度调度 proxy 扫描")
    print("警告: 这是 CSV 月度调度 proxy，不模拟同账户保证金、并发、EA 状态、月内路径或成交交互。")
    print(f"series={','.join(names)}")
    print()
    for result in sort_results(results)[: args.top]:
        print_result(result, args.max_bad_detail, args.show_months)


if __name__ == "__main__":
    main()
