#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import itertools
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MONTHS = [
    "2024-06", "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07",
    "2025-08", "2025-09", "2025-10", "2025-11", "2025-12", "2026-01", "2026-02",
    "2026-03", "2026-04", "2026-05",
]


@dataclass
class MonthlySeries:
    name: str
    path: Path
    pnl_by_month: dict[str, float]
    trades_by_month: dict[str, int]

    @property
    def total_pnl(self) -> float:
        return sum(self.pnl_by_month.values())

    @property
    def total_trades(self) -> int:
        return sum(self.trades_by_month.values())


def merge_series(name: str, series: list[MonthlySeries]) -> MonthlySeries:
    pnl_by_month: dict[str, float] = defaultdict(float)
    trades_by_month: dict[str, int] = defaultdict(int)
    paths = []
    for item in series:
        paths.append(str(item.path))
        for month, pnl in item.pnl_by_month.items():
            pnl_by_month[month] += pnl
        for month, trades in item.trades_by_month.items():
            trades_by_month[month] += trades
    return MonthlySeries(name, Path(" + ".join(paths)), dict(pnl_by_month), dict(trades_by_month))


def parse_scales(raw: str) -> list[float]:
    return [float(part.strip()) for part in raw.split(",") if part.strip()]


def load_series(path: Path, name: str | None = None) -> MonthlySeries:
    pnl_by_month: dict[str, float] = defaultdict(float)
    trades_by_month: dict[str, int] = defaultdict(int)
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            month = (row.get("date") or "")[:7]
            if not month:
                continue
            pnl_by_month[month] += float(row.get("pnl_proxy") or 0.0)
            trades_by_month[month] += 1

    label = name or path.name.replace(".trades.csv", "")
    return MonthlySeries(label, path, dict(pnl_by_month), dict(trades_by_month))


def eval_combo(
    base: MonthlySeries,
    addons: list[tuple[MonthlySeries, float]],
    months: list[str],
    days: int,
) -> dict:
    monthly_pnl = {
        month: base.pnl_by_month.get(month, 0.0) + sum(
            scale * addon.pnl_by_month.get(month, 0.0)
            for addon, scale in addons
        )
        for month in months
    }
    monthly_trades = {
        month: base.trades_by_month.get(month, 0) + sum(
            addon.trades_by_month.get(month, 0)
            for addon, scale in addons
            if scale > 0
        )
        for month in months
    }
    bad = [(month, pnl) for month, pnl in monthly_pnl.items() if pnl < 0]
    return {
        "addons": addons,
        "bad": bad,
        "total_pnl": sum(monthly_pnl.values()),
        "daily_trades": sum(monthly_trades.values()) / days,
        "monthly_pnl": monthly_pnl,
        "monthly_trades": monthly_trades,
    }


def eval_monthly_addons(
    base: MonthlySeries,
    selected: dict[str, list[tuple[MonthlySeries, float]]],
    months: list[str],
    days: int,
) -> dict:
    monthly_pnl = {}
    monthly_trades = {}
    for month in months:
        addons = selected.get(month, [])
        monthly_pnl[month] = base.pnl_by_month.get(month, 0.0) + sum(
            scale * addon.pnl_by_month.get(month, 0.0)
            for addon, scale in addons
        )
        monthly_trades[month] = base.trades_by_month.get(month, 0) + sum(
            addon.trades_by_month.get(month, 0)
            for addon, scale in addons
            if scale > 0
        )
    bad = [(month, pnl) for month, pnl in monthly_pnl.items() if pnl < 0]
    return {
        "bad": bad,
        "total_pnl": sum(monthly_pnl.values()),
        "daily_trades": sum(monthly_trades.values()) / days,
        "monthly_pnl": monthly_pnl,
        "monthly_trades": monthly_trades,
        "selected": selected,
    }


def eval_oracle(series: list[MonthlySeries], months: list[str], days: int) -> dict:
    monthly_choice = {}
    monthly_pnl = {}
    monthly_trades = {}
    for month in months:
        best = max(series, key=lambda item: item.pnl_by_month.get(month, 0.0))
        monthly_choice[month] = best.name
        monthly_pnl[month] = best.pnl_by_month.get(month, 0.0)
        monthly_trades[month] = best.trades_by_month.get(month, 0)
    bad = [(month, pnl) for month, pnl in monthly_pnl.items() if pnl < 0]
    return {
        "bad": bad,
        "total_pnl": sum(monthly_pnl.values()),
        "daily_trades": sum(monthly_trades.values()) / days,
        "monthly_choice": monthly_choice,
        "monthly_pnl": monthly_pnl,
    }


def print_combo(result: dict, max_bad_detail: int) -> None:
    bad = result["bad"]
    bad_text = ", ".join(f"{month}:{pnl:.2f}" for month, pnl in bad[:max_bad_detail])
    if len(bad) > max_bad_detail:
        bad_text += ", ..."
    addon_text = " + ".join(
        f"{addon.name} x{scale:g}" for addon, scale in result["addons"]
    )
    print(
        f"{addon_text} | "
        f"bad={len(bad)} | total={result['total_pnl']:.2f} | "
        f"daily~{result['daily_trades']:.2f} | {bad_text}"
    )


def print_monthly_addons(result: dict, max_bad_detail: int) -> None:
    bad = result["bad"]
    bad_text = ", ".join(f"{month}:{pnl:.2f}" for month, pnl in bad[:max_bad_detail])
    if len(bad) > max_bad_detail:
        bad_text += ", ..."
    selected = result["selected"]
    parts = []
    for month in sorted(selected):
        addon_text = "+".join(
            f"{addon.name}x{scale:g}" for addon, scale in selected[month]
        )
        parts.append(f"{month}:{addon_text}")
    print(
        f"{'; '.join(parts)} | "
        f"bad={len(bad)} | total={result['total_pnl']:.2f} | "
        f"daily~{result['daily_trades']:.2f} | {bad_text}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Scan monthly proxy complementarity across MT5 trade CSVs. "
            "This is not a valid portfolio backtest; use it only to rank ideas."
        )
    )
    parser.add_argument("--base", required=True, action="append", type=Path, help="Base .trades.csv path; repeat for aggregate base")
    parser.add_argument("--candidate", action="append", type=Path, default=[], help="Candidate .trades.csv path")
    parser.add_argument("--candidate-glob", action="append", default=[], help="Glob for candidate CSVs")
    parser.add_argument("--scales", default="0.25,0.5,1,2,4,8,10", help="Comma-separated pnl scales")
    parser.add_argument("--months", default=",".join(DEFAULT_MONTHS), help="Comma-separated months")
    parser.add_argument("--days", type=int, default=720)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--combo-size", type=int, default=1, choices=(1, 2, 3))
    parser.add_argument(
        "--monthly-addon-scan",
        action="store_true",
        help="For each negative base month, choose one candidate+scale addon for that month only",
    )
    parser.add_argument(
        "--monthly-addon-options",
        type=int,
        default=8,
        help="Keep only the top N positive addon options per negative month",
    )
    parser.add_argument("--max-bad-detail", type=int, default=8)
    parser.add_argument("--oracle", action="store_true", help="Print hindsight best-month upper bound")
    args = parser.parse_args()

    months = [part.strip() for part in args.months.split(",") if part.strip()]
    scales = parse_scales(args.scales)
    base_parts = [load_series(path, path.name.replace(".trades.csv", "")) for path in args.base]
    base = base_parts[0] if len(base_parts) == 1 else merge_series("BASE", base_parts)

    paths = list(args.candidate)
    for pattern in args.candidate_glob:
        paths.extend(Path().glob(pattern))

    seen = {path.resolve() for path in args.base}
    candidates: list[MonthlySeries] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen or not path.exists():
            continue
        seen.add(resolved)
        candidates.append(load_series(path))

    results = []
    for size in range(1, args.combo_size + 1):
        for combo in itertools.combinations(candidates, size):
            for scale_tuple in itertools.product(scales, repeat=size):
                addons = list(zip(combo, scale_tuple))
                results.append(eval_combo(base, addons, months, args.days))

    results.sort(key=lambda item: (len(item["bad"]), -item["total_pnl"], -item["daily_trades"]))

    print("# 月度组合 proxy 扫描")
    print("警告: 这是 CSV 月度 proxy，不模拟同账户保证金、并发、月度风控、成交路径或 EA 状态。")
    print(f"base={'; '.join(str(path) for path in args.base)}")
    print(f"candidates={len(candidates)} scales={','.join(str(s) for s in scales)}")
    print()

    for result in results[: args.top]:
        print_combo(result, args.max_bad_detail)

    if args.monthly_addon_scan and candidates:
        bad_months = [
            month for month in months
            if base.pnl_by_month.get(month, 0.0) < 0
        ]
        addon_options_by_month = {}
        for month in bad_months:
            options = []
            for candidate in candidates:
                for scale in scales:
                    if scale <= 0:
                        continue
                    pnl = (
                        base.pnl_by_month.get(month, 0.0)
                        + scale * candidate.pnl_by_month.get(month, 0.0)
                    )
                    if pnl > 0:
                        options.append((candidate, scale, pnl))
            addon_options_by_month[month] = options
            options.sort(key=lambda item: (-item[2], item[1], item[0].name))
            addon_options_by_month[month] = options[: args.monthly_addon_options]

        monthly_results = []
        if all(addon_options_by_month.get(month) for month in bad_months):
            for option_tuple in itertools.product(
                *(addon_options_by_month[month] for month in bad_months)
            ):
                selected = {
                    month: [(candidate, scale)]
                    for month, (candidate, scale, _pnl) in zip(bad_months, option_tuple)
                }
                monthly_results.append(eval_monthly_addons(base, selected, months, args.days))
            monthly_results.sort(
                key=lambda item: (
                    len(item["bad"]),
                    -item["total_pnl"],
                    -item["daily_trades"],
                )
            )

        print()
        print("# 月度补腿 hindsight proxy")
        print("警告: 只在 base 亏损月事后启用补腿；这不是可部署规则，只用于观察互补上界。")
        if not monthly_results:
            missing = [month for month in bad_months if not addon_options_by_month.get(month)]
            print(f"没有找到能补正所有 base 亏损月的候选；缺口={','.join(missing)}")
        for result in monthly_results[: args.top]:
            print_monthly_addons(result, args.max_bad_detail)

    if args.oracle and candidates:
        oracle = eval_oracle([base] + candidates, months, args.days)
        print()
        print("# 月度 hindsight oracle 上界")
        print("警告: oracle 每月事后选择最好策略，只能作为互补性上界。")
        bad_text = ", ".join(f"{month}:{pnl:.2f}" for month, pnl in oracle["bad"])
        print(
            f"bad={len(oracle['bad'])} | total={oracle['total_pnl']:.2f} | "
            f"daily~{oracle['daily_trades']:.2f} | {bad_text}"
        )
        for month in months:
            print(f"{month}: {oracle['monthly_choice'][month]} {oracle['monthly_pnl'][month]:.2f}")


if __name__ == "__main__":
    main()
