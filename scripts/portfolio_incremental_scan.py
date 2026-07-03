#!/usr/bin/env python3
"""Scan candidate CSVs as incremental add-ons to an existing portfolio schedule.

This is a diagnosis helper for finding genuinely useful extra legs. It runs the
same path-level proxy as portfolio_schedule_runner, then adds one candidate CSV
at a time and reports whether the combined path improves without breaking the
monthly target.
"""

from __future__ import annotations

import argparse
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
class IncrementalRow:
    name: str
    path: Path
    total_profit: float
    profit_delta: float
    daily_trades: float
    daily_delta: float
    bad_months: int
    weakest_month: str
    weakest_profit: float
    covered_months: int
    candidate_trades: int
    overlap_ratio: float
    pass_targets: bool


def candidate_name(path: Path) -> str:
    name = path.name.replace(".trades.csv", "")
    return name[:48]


def existing_paths(schedule: dict) -> set[Path]:
    paths: set[Path] = set()
    for item in schedule.get("series", []):
        path = Path(str(item.get("path", "")))
        if not path.is_absolute():
            path = ROOT / path
        paths.add(path.resolve())
    return paths


def trade_key(trade) -> tuple[str, str, str, str, str]:
    return (trade.time, trade.signal_type, trade.direction, trade.hour, f"{trade.pnl:.6f}")


def scan_incremental(
    config_path: Path,
    schedule_name: str,
    candidate_patterns: list[str],
    top: int,
    min_covered_months: int = 0,
    min_candidate_trades: int = 1,
    max_overlap: float = 1.0,
) -> tuple[list[IncrementalRow], IncrementalRow]:
    schedules = load_config(config_path)
    if schedule_name not in schedules:
        names = ", ".join(sorted(schedules))
        raise SystemExit(f"unknown schedule: {schedule_name}; available: {names}")
    schedule = schedules[schedule_name]
    args = build_args(schedule)
    targets = schedule.get("targets") or {}
    base_series = [as_series_arg(item) for item in schedule.get("series", [])]
    if not base_series:
        raise SystemExit(f"schedule has no series: {schedule_name}")

    base_trades = load_trades(base_series)
    base_keys = {trade_key(trade) for trade in base_trades}
    base_rows = simulate(base_trades, args)
    base_audit = audit_targets(base_rows, args, targets)
    base_weakest = min(base_rows, key=lambda row: row.profit)
    base = IncrementalRow(
        name="BASE",
        path=Path(),
        total_profit=base_audit.total_profit,
        profit_delta=0.0,
        daily_trades=base_audit.daily_trades,
        daily_delta=0.0,
        bad_months=len(base_audit.bad_months),
        weakest_month=base_weakest.month,
        weakest_profit=base_weakest.profit,
        covered_months=len({row.month for row in base_rows if row.trades > 0}),
        candidate_trades=sum(row.trades for row in base_rows),
        overlap_ratio=0.0,
        pass_targets=base_audit.passed,
    )

    rows: list[IncrementalRow] = []
    seen = existing_paths(schedule)
    matched: set[Path] = set()
    for pattern in candidate_patterns:
        for raw_path in Path().glob(pattern):
            path = raw_path.resolve()
            if path in seen or path in matched or not raw_path.is_file():
                continue
            matched.add(path)
            candidate_trades = load_trades([f"{candidate_name(raw_path)}={raw_path}"])
            covered_months = len({trade.month for trade in candidate_trades})
            if len(candidate_trades) < min_candidate_trades or covered_months < min_covered_months:
                continue
            candidate_keys = [trade_key(trade) for trade in candidate_trades]
            overlap = sum(1 for key in candidate_keys if key in base_keys)
            overlap_ratio = overlap / len(candidate_keys) if candidate_keys else 0.0
            if overlap_ratio > max_overlap:
                continue
            series = base_series + [f"{candidate_name(raw_path)}={raw_path}"]
            try:
                combo_rows = simulate(base_trades + candidate_trades, args)
            except SystemExit:
                continue
            audit = audit_targets(combo_rows, args, targets)
            weakest = min(combo_rows, key=lambda row: row.profit)
            rows.append(
                IncrementalRow(
                    name=raw_path.name,
                    path=raw_path,
                    total_profit=audit.total_profit,
                    profit_delta=audit.total_profit - base_audit.total_profit,
                    daily_trades=audit.daily_trades,
                    daily_delta=audit.daily_trades - base_audit.daily_trades,
                    bad_months=len(audit.bad_months),
                    weakest_month=weakest.month,
                    weakest_profit=weakest.profit,
                    covered_months=covered_months,
                    candidate_trades=len(candidate_trades),
                    overlap_ratio=overlap_ratio,
                    pass_targets=audit.passed,
                )
            )

    rows.sort(
        key=lambda row: (
            not row.pass_targets,
            row.bad_months,
            row.overlap_ratio,
            -row.profit_delta,
            -row.daily_delta,
            row.name,
        )
    )
    return rows[:top], base


def render(schedule_name: str, rows: list[IncrementalRow], base: IncrementalRow) -> str:
    lines = [
        f"# Portfolio incremental candidate scan: {schedule_name}",
        "",
        "warning: CSV path-level add-on scan only; not a valid MT5 portfolio backtest.",
        "",
        (
            f"base: total={base.total_profit:.2f} daily={base.daily_trades:.2f} "
            f"bad={base.bad_months} weakest={base.weakest_month}:{base.weakest_profit:.2f} "
            f"pass={str(base.pass_targets).lower()}"
        ),
        "",
        "| candidate | pass | bad | total | delta | daily | daily_delta | months | trades | overlap | weakest |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.name} | {str(row.pass_targets).lower()} | {row.bad_months} | "
            f"{row.total_profit:.2f} | {row.profit_delta:.2f} | "
            f"{row.daily_trades:.2f} | {row.daily_delta:.2f} | "
            f"{row.covered_months} | {row.candidate_trades} | {row.overlap_ratio:.2f} | "
            f"{row.weakest_month}:{row.weakest_profit:.2f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan add-on candidates against a portfolio schedule proxy.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--schedule", required=True)
    parser.add_argument("--candidate-glob", action="append", required=True)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--min-covered-months", type=int, default=20)
    parser.add_argument("--min-candidate-trades", type=int, default=1)
    parser.add_argument("--max-overlap", type=float, default=1.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows, base = scan_incremental(
        args.config,
        args.schedule,
        args.candidate_glob,
        args.top,
        min_covered_months=args.min_covered_months,
        min_candidate_trades=args.min_candidate_trades,
        max_overlap=args.max_overlap,
    )
    report = render(args.schedule, rows, base)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
