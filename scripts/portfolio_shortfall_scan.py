#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from portfolio_path_sim import load_trades, simulate  # noqa: E402
from portfolio_schedule_runner import (  # noqa: E402
    DEFAULT_CONFIG,
    as_series_arg,
    audit_targets,
    build_args,
    load_config,
)


@dataclass(frozen=True)
class ReturnAudit:
    below_count: int
    total_shortfall: float
    min_month: str
    min_return_pct: float


@dataclass(frozen=True)
class ShortfallRow:
    name: str
    path: Path
    pass_targets: bool
    bad_months: int
    total_profit: float
    profit_delta: float
    daily_trades: float
    below_count: int
    below_delta: int
    total_shortfall: float
    shortfall_delta: float
    min_month: str
    min_return_pct: float
    candidate_trades: int
    covered_months: int


def candidate_name(path: Path) -> str:
    return path.name.replace(".trades.csv", "")[:48]


def existing_paths(schedule: dict) -> set[Path]:
    result: set[Path] = set()
    for item in schedule.get("series") or []:
        path = Path(str(item.get("path", "")))
        if not path.is_absolute():
            path = ROOT / path
        result.add(path.resolve())
    return result


def return_audit(rows, target_pct: float) -> ReturnAudit:
    below = 0
    total_shortfall = 0.0
    min_month = ""
    min_return = float("inf")
    for row in rows:
        return_pct = row.profit / row.start_balance * 100.0 if row.start_balance > 0 else 0.0
        if return_pct < target_pct:
            below += 1
            total_shortfall += max(0.0, row.start_balance * target_pct / 100.0 - row.profit)
        if return_pct < min_return:
            min_return = return_pct
            min_month = row.month
    if min_return == float("inf"):
        min_return = 0.0
    return ReturnAudit(below, total_shortfall, min_month, min_return)


def scan_shortfall(
    config_path: Path,
    schedule_name: str,
    candidate_patterns: list[str],
    target_pct: float,
    top: int,
    min_covered_months: int,
    require_pass: bool,
) -> tuple[list[ShortfallRow], ShortfallRow]:
    schedules = load_config(config_path)
    if schedule_name not in schedules:
        names = ", ".join(sorted(schedules))
        raise SystemExit(f"unknown schedule: {schedule_name}; available: {names}")
    schedule = schedules[schedule_name]
    args = build_args(schedule)
    targets = schedule.get("targets") or {}
    base_series = [as_series_arg(item) for item in schedule.get("series") or []]
    base_trades = load_trades(base_series)
    base_rows = simulate(base_trades, args)
    base_target_audit = audit_targets(base_rows, args, targets)
    base_return = return_audit(base_rows, target_pct)
    base = ShortfallRow(
        name="BASE",
        path=Path(),
        pass_targets=base_target_audit.passed,
        bad_months=len(base_target_audit.bad_months),
        total_profit=base_target_audit.total_profit,
        profit_delta=0.0,
        daily_trades=base_target_audit.daily_trades,
        below_count=base_return.below_count,
        below_delta=0,
        total_shortfall=base_return.total_shortfall,
        shortfall_delta=0.0,
        min_month=base_return.min_month,
        min_return_pct=base_return.min_return_pct,
        candidate_trades=len(base_trades),
        covered_months=len({trade.month for trade in base_trades}),
    )

    rows: list[ShortfallRow] = []
    seen = existing_paths(schedule)
    matched: set[Path] = set()
    for pattern in candidate_patterns:
        for raw_match in glob.glob(pattern):
            raw_path = Path(raw_match)
            path = raw_path.resolve()
            if path in seen or path in matched or not raw_path.is_file():
                continue
            matched.add(path)
            candidate_trades = load_trades([f"{candidate_name(raw_path)}={raw_path}"])
            covered_months = len({trade.month for trade in candidate_trades})
            if covered_months < min_covered_months:
                continue
            combo_rows = simulate(base_trades + candidate_trades, args)
            combo_target_audit = audit_targets(combo_rows, args, targets)
            if require_pass and not combo_target_audit.passed:
                continue
            combo_return = return_audit(combo_rows, target_pct)
            rows.append(
                ShortfallRow(
                    name=raw_path.name,
                    path=raw_path,
                    pass_targets=combo_target_audit.passed,
                    bad_months=len(combo_target_audit.bad_months),
                    total_profit=combo_target_audit.total_profit,
                    profit_delta=combo_target_audit.total_profit - base_target_audit.total_profit,
                    daily_trades=combo_target_audit.daily_trades,
                    below_count=combo_return.below_count,
                    below_delta=base_return.below_count - combo_return.below_count,
                    total_shortfall=combo_return.total_shortfall,
                    shortfall_delta=base_return.total_shortfall - combo_return.total_shortfall,
                    min_month=combo_return.min_month,
                    min_return_pct=combo_return.min_return_pct,
                    candidate_trades=len(candidate_trades),
                    covered_months=covered_months,
                )
            )

    rows.sort(
        key=lambda row: (
            not row.pass_targets,
            row.bad_months,
            -row.shortfall_delta,
            -row.below_delta,
            -row.profit_delta,
            row.name,
        )
    )
    return rows[:top], base


def render(schedule_name: str, rows: list[ShortfallRow], base: ShortfallRow, target_pct: float) -> str:
    lines = [
        f"# Portfolio shortfall candidate scan: {schedule_name}",
        "",
        "warning: CSV path-level add-on scan only; not a valid MT5 portfolio backtest.",
        "",
        (
            f"base: target_pct={target_pct:.2f} total={base.total_profit:.2f} "
            f"daily={base.daily_trades:.2f} below={base.below_count} "
            f"shortfall={base.total_shortfall:.2f} min={base.min_month}:{base.min_return_pct:.2f}% "
            f"pass={str(base.pass_targets).lower()}"
        ),
        "",
        "| candidate | pass | bad | total | profit_delta | daily | below | below_delta | shortfall | shortfall_delta | min_return | months | trades |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row.name} | {str(row.pass_targets).lower()} | {row.bad_months} | "
            f"{row.total_profit:.2f} | {row.profit_delta:.2f} | {row.daily_trades:.2f} | "
            f"{row.below_count} | {row.below_delta} | {row.total_shortfall:.2f} | "
            f"{row.shortfall_delta:.2f} | {row.min_month}:{row.min_return_pct:.2f}% | "
            f"{row.covered_months} | {row.candidate_trades} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank add-on candidates by monthly return shortfall reduction.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--schedule", required=True)
    parser.add_argument("--candidate-glob", action="append", required=True)
    parser.add_argument("--target-pct", type=float, default=35.0)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--min-covered-months", type=int, default=20)
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows, base = scan_shortfall(
        args.config,
        args.schedule,
        args.candidate_glob,
        args.target_pct,
        args.top,
        args.min_covered_months,
        args.require_pass,
    )
    report = render(args.schedule, rows, base, args.target_pct)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
