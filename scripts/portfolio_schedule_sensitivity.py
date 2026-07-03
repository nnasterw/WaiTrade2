#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from portfolio_path_sim import load_trades, simulate  # noqa: E402
from portfolio_schedule_runner import (  # noqa: E402
    DEFAULT_CONFIG,
    TargetAudit,
    as_series_arg,
    audit_targets,
    build_args,
    load_config,
)


@dataclass(frozen=True)
class SensitivityRow:
    scenario: str
    total_profit: float
    profit_delta: float
    daily_trades: float
    daily_delta: float
    bad_months: int
    weakest_month: str
    weakest_profit: float
    passed: bool


def evaluate(schedule: dict) -> tuple[TargetAudit, str, float]:
    args = build_args(schedule)
    series = [as_series_arg(item) for item in schedule.get("series", [])]
    trades = load_trades(series)
    months = simulate(trades, args)
    audit = audit_targets(months, args, schedule.get("targets") or {})
    weakest = min(months, key=lambda row: row.profit) if months else None
    return audit, weakest.month if weakest else "", weakest.profit if weakest else 0.0


def with_series(schedule: dict, series: list[dict]) -> dict:
    cloned = copy.deepcopy(schedule)
    cloned["series"] = series
    return cloned


def scaled_series_item(item: dict, scale: float) -> dict:
    cloned = copy.deepcopy(item)
    original = float(cloned.get("scale", 1.0))
    cloned["scale"] = original * scale
    return cloned


def scan_sensitivity(
    config_path: Path,
    schedule_name: str,
    scales: list[float],
) -> list[SensitivityRow]:
    schedules = load_config(config_path)
    if schedule_name not in schedules:
        names = ", ".join(sorted(schedules))
        raise SystemExit(f"unknown schedule: {schedule_name}; available: {names}")
    schedule = schedules[schedule_name]
    base_audit, base_weakest_month, base_weakest_profit = evaluate(schedule)
    rows = [
        SensitivityRow(
            scenario="BASE",
            total_profit=base_audit.total_profit,
            profit_delta=0.0,
            daily_trades=base_audit.daily_trades,
            daily_delta=0.0,
            bad_months=len(base_audit.bad_months),
            weakest_month=base_weakest_month,
            weakest_profit=base_weakest_profit,
            passed=base_audit.passed,
        )
    ]

    series = schedule.get("series") or []
    for index, item in enumerate(series):
        name = str(item.get("name", f"leg{index + 1}"))
        removed = [copy.deepcopy(other) for pos, other in enumerate(series) if pos != index]
        audit, weakest_month, weakest_profit = evaluate(with_series(schedule, removed))
        rows.append(
            SensitivityRow(
                scenario=f"drop {name}",
                total_profit=audit.total_profit,
                profit_delta=audit.total_profit - base_audit.total_profit,
                daily_trades=audit.daily_trades,
                daily_delta=audit.daily_trades - base_audit.daily_trades,
                bad_months=len(audit.bad_months),
                weakest_month=weakest_month,
                weakest_profit=weakest_profit,
                passed=audit.passed,
            )
        )

        for scale in scales:
            adjusted = [
                scaled_series_item(other, scale) if pos == index else copy.deepcopy(other)
                for pos, other in enumerate(series)
            ]
            audit, weakest_month, weakest_profit = evaluate(with_series(schedule, adjusted))
            rows.append(
                SensitivityRow(
                    scenario=f"scale {name} x{scale:g}",
                    total_profit=audit.total_profit,
                    profit_delta=audit.total_profit - base_audit.total_profit,
                    daily_trades=audit.daily_trades,
                    daily_delta=audit.daily_trades - base_audit.daily_trades,
                    bad_months=len(audit.bad_months),
                    weakest_month=weakest_month,
                    weakest_profit=weakest_profit,
                    passed=audit.passed,
                )
            )
    return rows


def parse_scales(raw: str) -> list[float]:
    scales = [float(part.strip()) for part in raw.split(",") if part.strip()]
    if any(scale < 0 for scale in scales):
        raise SystemExit("scales must be non-negative")
    return scales


def render(schedule_name: str, rows: list[SensitivityRow]) -> str:
    lines = [
        f"# Portfolio schedule sensitivity: {schedule_name}",
        "",
        "warning: CSV path-level sensitivity only; not a valid MT5 portfolio backtest.",
        "",
        "| scenario | pass | bad | total | delta | daily | daily_delta | weakest |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.scenario} | {str(row.passed).lower()} | {row.bad_months} | "
            f"{row.total_profit:.2f} | {row.profit_delta:.2f} | "
            f"{row.daily_trades:.2f} | {row.daily_delta:.2f} | "
            f"{row.weakest_month}:{row.weakest_profit:.2f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run leave-one-out and leg-scale sensitivity for a portfolio schedule.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--schedule", default="v11a")
    parser.add_argument("--scales", default="0.25,0.5,0.75")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = scan_sensitivity(args.config, args.schedule, parse_scales(args.scales))
    report = render(args.schedule, rows)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
