#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import itertools
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from portfolio_path_sim import (  # noqa: E402
    MonthState,
    Trade,
    load_trades,
    should_block_signal_after_trade,
    should_stop_after_trade,
    trade_matches_any_context_filter,
)
from portfolio_schedule_runner import (  # noqa: E402
    DEFAULT_CONFIG,
    as_series_arg,
    audit_targets,
    build_args,
    load_config,
)


BALANCE_GUARD_KEYS = {
    "guard_min_month_start_balance",
    "guard_max_month_start_balance",
    "guard2_min_month_start_balance",
    "guard2_max_month_start_balance",
    "signal_block_min_month_start_balance",
    "drop_min_month_start_balance",
    "drop_max_month_start_balance",
}
BALANCE_FILTER_KEYS = {"min_start", "max_start"}


@dataclass(frozen=True)
class GridRow:
    scales: dict[str, float]
    total_scale: float
    active_legs: int
    total_profit: float
    daily_trades: float
    bad_months: int
    weakest_month: str
    weakest_profit: float
    passed: bool


def scale_balance_thresholds(schedule: dict, factor: float) -> dict:
    if factor == 1.0:
        return schedule
    cloned = copy.deepcopy(schedule)
    guards = cloned.get("guards") or {}
    for key in BALANCE_GUARD_KEYS:
        if key in guards:
            guards[key] = float(guards[key]) * factor
    cloned["guards"] = guards

    scaled_filters: list[str] = []
    for raw in cloned.get("drop_filters") or []:
        parts: list[str] = []
        for part in str(raw).split(";"):
            if "=" not in part:
                parts.append(part)
                continue
            key, value = part.split("=", 1)
            if key in BALANCE_FILTER_KEYS:
                value = f"{float(value) * factor:g}"
            parts.append(f"{key}={value}")
        scaled_filters.append(";".join(parts))
    cloned["drop_filters"] = scaled_filters
    return cloned


def load_source_trades(schedule: dict) -> dict[str, list[Trade]]:
    result: dict[str, list[Trade]] = {}
    for item in schedule.get("series") or []:
        name = str(item.get("name") or "")
        if not name:
            raise SystemExit("series item missing name")
        result[name] = load_trades([as_series_arg(item)])
    return result


def group_trades_by_month(source_trades: dict[str, list[Trade]]) -> dict[str, list[Trade]]:
    result: dict[str, list[Trade]] = {}
    for items in source_trades.values():
        for trade in items:
            result.setdefault(trade.month, []).append(trade)
    for trades in result.values():
        trades.sort(key=lambda item: (item.time, item.source))
    return dict(sorted(result.items()))


def simulate_scaled_months(
    trades_by_month: dict[str, list[Trade]],
    scales: dict[str, float],
    args: argparse.Namespace,
) -> list[MonthState]:
    running_balance = args.deposit
    rows: list[MonthState] = []
    for month, trades in trades_by_month.items():
        state = MonthState(month=month, start_balance=running_balance, blocked_signals=set())
        for trade in trades:
            scale = scales.get(trade.source, 1.0)
            if scale <= 0:
                continue
            if trade_matches_any_context_filter(trade, state, args.drop_filters, args):
                state.skipped += 1
                continue
            if state.blocked_signals and trade.signal_type in state.blocked_signals:
                state.skipped += 1
                continue
            if state.stopped:
                state.skipped += 1
                continue

            state.trades += 1
            state.profit += trade.pnl * scale
            block_reason = should_block_signal_after_trade(state, trade, args)
            if block_reason:
                state.blocked_signals.add(trade.signal_type)
                state.stop_reason = f"{state.stop_reason},{block_reason}" if state.stop_reason else block_reason
            reason = should_stop_after_trade(state, args)
            if reason:
                state.stopped = True
                state.stop_reason = reason
        rows.append(state)
        running_balance = state.end_balance
    return rows


def evaluate_combo(schedule: dict, trades_by_month: dict[str, list[Trade]], scales: dict[str, float]) -> GridRow:
    args = build_args(schedule)
    months = simulate_scaled_months(trades_by_month, scales, args)
    audit = audit_targets(months, args, schedule.get("targets") or {})
    weakest = min(months, key=lambda row: row.profit) if months else None
    return GridRow(
        scales=dict(scales),
        total_scale=sum(scale for scale in scales.values() if scale > 0),
        active_legs=sum(1 for scale in scales.values() if scale > 0),
        total_profit=audit.total_profit,
        daily_trades=audit.daily_trades,
        bad_months=len(audit.bad_months),
        weakest_month=weakest.month if weakest else "",
        weakest_profit=weakest.profit if weakest else 0.0,
        passed=audit.passed,
    )


def scan_grid(
    config_path: Path,
    schedule_name: str,
    scale_values: list[float],
    min_active_legs: int = 1,
    top: int = 30,
    source_scale_values: dict[str, list[float]] | None = None,
    include_failed: bool = False,
    balance_threshold_factor: float = 1.0,
) -> list[GridRow]:
    schedules = load_config(config_path)
    if schedule_name not in schedules:
        names = ", ".join(sorted(schedules))
        raise SystemExit(f"unknown schedule: {schedule_name}; available: {names}")
    schedule = scale_balance_thresholds(schedules[schedule_name], balance_threshold_factor)
    source_trades = load_source_trades(schedule)
    trades_by_month = group_trades_by_month(source_trades)
    sources = list(source_trades)
    rows: list[GridRow] = []
    values_by_source = [
        source_scale_values.get(source, scale_values) if source_scale_values else scale_values
        for source in sources
    ]
    for values in itertools.product(*values_by_source):
        scales = dict(zip(sources, values))
        if sum(1 for value in values if value > 0) < min_active_legs:
            continue
        row = evaluate_combo(schedule, trades_by_month, scales)
        if include_failed or row.passed:
            rows.append(row)
    rows.sort(
        key=lambda row: (
            not row.passed,
            row.bad_months,
            row.total_scale,
            row.active_legs,
            -row.weakest_profit,
            -row.total_profit,
            -row.daily_trades,
            scale_label(row.scales),
        )
    )
    return rows[:top]


def parse_scales(raw: str) -> list[float]:
    values = [float(part.strip()) for part in raw.split(",") if part.strip()]
    if not values:
        raise SystemExit("no scale values provided")
    if any(value < 0 for value in values):
        raise SystemExit("scale values must be non-negative")
    return values


def parse_source_scale(raw: str) -> tuple[str, list[float]]:
    if "=" not in raw:
        raise SystemExit(f"bad --source-scale value: {raw}")
    source, values = raw.split("=", 1)
    return source.strip(), parse_scales(values)


def parse_source_scales(raw_items: list[str]) -> dict[str, list[float]]:
    result: dict[str, list[float]] = {}
    for raw in raw_items:
        source, values = parse_source_scale(raw)
        if not source:
            raise SystemExit(f"bad --source-scale source: {raw}")
        result[source] = values
    return result


def scale_label(scales: dict[str, float]) -> str:
    return ",".join(f"{source}={scale:g}" for source, scale in scales.items())


def render(schedule_name: str, rows: list[GridRow]) -> str:
    lines = [
        f"# Portfolio scale grid scan: {schedule_name}",
        "",
        "warning: CSV path-level scale grid only; scale is a screening proxy, not a live-ready MT5 parameter.",
        "",
        "| rank | active | total_scale | total | daily | bad | weakest | scales |",
        "|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for index, row in enumerate(rows, 1):
        lines.append(
            f"| {index} | {row.active_legs} | {row.total_scale:.2f} | "
            f"{row.total_profit:.2f} | {row.daily_trades:.2f} | {row.bad_months} | "
            f"{row.weakest_month}:{row.weakest_profit:.2f} | {scale_label(row.scales)} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Brute-force source scale grid for a portfolio schedule proxy.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--schedule", default="v11a")
    parser.add_argument("--scales", default="0,0.25,0.5,0.75,1")
    parser.add_argument(
        "--source-scale",
        action="append",
        default=[],
        help="Override scale values for one source, e.g. R225=0.75,1. Can be repeated.",
    )
    parser.add_argument("--min-active-legs", type=int, default=1)
    parser.add_argument("--include-failed", action="store_true")
    parser.add_argument(
        "--balance-threshold-factor",
        type=float,
        default=1.0,
        help="Scale guard/drop-filter balance thresholds for reduced-exposure screening.",
    )
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = scan_grid(
        args.config,
        args.schedule,
        parse_scales(args.scales),
        min_active_legs=args.min_active_legs,
        top=args.top,
        source_scale_values=parse_source_scales(args.source_scale),
        include_failed=args.include_failed,
        balance_threshold_factor=args.balance_threshold_factor,
    )
    report = render(args.schedule, rows)
    if args.balance_threshold_factor != 1.0:
        report = report.replace(
            "\nwarning:",
            f"\nbalance_threshold_factor={args.balance_threshold_factor:g}\n\nwarning:",
            1,
        )
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
