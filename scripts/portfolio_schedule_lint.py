#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from portfolio_path_sim import parse_filter


DEFAULT_CONFIG = ROOT / "config" / "portfolio_schedules.yaml"
DEFAULT_STRATEGIES_CONFIG = ROOT / "config" / "strategies.yaml"


def load_schedules(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing schedule config: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    schedules = data.get("schedules")
    if not isinstance(schedules, dict):
        raise SystemExit(f"missing schedules block: {path}")
    return schedules


def load_strategy_config(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def only(values: set[str], key: str) -> str:
    if len(values) != 1:
        raise ValueError(f"{key} must contain exactly one value: {values}")
    return next(iter(values))


def csv_values(value: object) -> set[str]:
    return {part.strip() for part in str(value or "").split(",") if part.strip()}


def normalized_months(values: object) -> set[str]:
    return {str(int(item)) for item in values}


def find_filter(filters: list[dict[str, set[str]]], **wanted: str) -> dict[str, set[str]]:
    for item in filters:
        ok = True
        for key, value in wanted.items():
            if item.get(key) != {value}:
                ok = False
                break
        if ok:
            return item
    return {}


def find_filters(filters: list[dict[str, set[str]]], **wanted: str) -> list[dict[str, set[str]]]:
    matches = []
    for item in filters:
        ok = True
        for key, value in wanted.items():
            if item.get(key) != {value}:
                ok = False
                break
        if ok:
            matches.append(item)
    return matches


def filtered_sources(schedule: dict) -> set[str]:
    return {
        str(item.get("name") or "")
        for item in schedule.get("series") or []
        if item.get("guard_override_mode", "all") == "all" and item.get("name")
    }


def require_equal(errors: list[str], label: str, actual: object, expected: object) -> None:
    if actual != expected:
        errors.append(f"{label}: actual={actual!r} expected={expected!r}")


def series_csv_months(path: Path) -> set[str]:
    if not path.exists():
        return set()
    months: set[str] = set()
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            date = row.get("date") or row.get("time", "")[:10]
            if len(date) >= 7:
                months.add(date[:7])
    return months


def lint_series_windows(schedule: dict, strategies: dict, errors: list[str]) -> None:
    days = int(schedule.get("days", 0) or 0)
    if days < 365:
        return

    for item in schedule.get("series") or []:
        path_value = item.get("path")
        strategy_name = item.get("strategy")
        if not path_value or not strategy_name:
            continue

        strategy = strategies.get(strategy_name) or {}
        entry_months = csv_values(strategy.get("entry_months"))
        if not entry_months:
            continue

        path = Path(path_value)
        if not path.is_absolute():
            path = ROOT / path
        months = series_csv_months(path)
        if not months:
            errors.append(f"{item.get('name', strategy_name)}: series CSV missing or empty: {path_value}")
            continue

        monthnums = {str(int(month[-2:])) for month in months}
        if not monthnums.issubset(entry_months):
            errors.append(
                f"{item.get('name', strategy_name)}: CSV months {sorted(monthnums)} exceed entry_months {sorted(entry_months)}"
            )
        if len(months) < 2:
            errors.append(
                f"{item.get('name', strategy_name)}: entry_months strategy uses only {len(months)} month in CSV; use full-window MT5 CSV, not a single-month screen"
            )


def float_value(raw: object, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def lint_series_context_filters(
    schedule: dict,
    strategies: dict,
    filters: list[dict[str, set[str]]],
    errors: list[str],
) -> None:
    for item in schedule.get("series") or []:
        source = str(item.get("name") or "")
        strategy_name = item.get("strategy")
        if not source or not strategy_name:
            continue
        strategy = strategies.get(strategy_name) or {}
        for slot in (1, 2, 3, 4, 5):
            months = csv_values(strategy.get(f"context_filter{slot}_months"))
            mult = float_value(strategy.get(f"context_filter{slot}_mult", 1.0), 1.0)
            if not months or mult != 0.0:
                continue
            min_start = float_value(strategy.get(f"context_filter{slot}_min_month_start_balance"), 0.0)
            max_start = float_value(strategy.get(f"context_filter{slot}_max_month_start_balance"), 0.0)
            hour_specs = [
                ("", csv_values(strategy.get(f"context_filter{slot}_no_hours"))),
                ("buy", csv_values(strategy.get(f"context_filter{slot}_no_buy_hours"))),
                ("sell", csv_values(strategy.get(f"context_filter{slot}_no_sell_hours"))),
            ]
            for direction, hours in hour_specs:
                if not hours:
                    continue
                match = find_context_drop_filter(
                    filters,
                    source=source,
                    months=months,
                    direction=direction,
                    hours=hours,
                    min_start=min_start,
                    max_start=max_start,
                )
                if not match:
                    label = f"{source} context_filter{slot}"
                    dir_text = direction or "all"
                    errors.append(
                        f"{label}: missing proxy drop_filter for months={sorted(months)} "
                        f"dir={dir_text} hours={sorted(hours)} min_start={min_start:g} max_start={max_start:g}"
                    )


def find_context_drop_filter(
    filters: list[dict[str, set[str]]],
    source: str,
    months: set[str],
    direction: str,
    hours: set[str],
    min_start: float,
    max_start: float,
) -> dict[str, set[str]]:
    for item in filters:
        if item.get("src") != {source}:
            continue
        if item.get("monthnum") != months:
            continue
        if item.get("hour") != hours:
            continue
        if direction:
            if item.get("dir") != {direction}:
                continue
        elif item.get("dir"):
            continue
        if item.get("signal"):
            continue
        item_min = float(only(item.get("min_start", {"0"}), "min_start"))
        item_max = float(only(item.get("max_start", {"0"}), "max_start"))
        if item_min != min_start or item_max != max_start:
            continue
        return item
    return {}


def lint_shared_only_filters(schedule: dict, filters: list[dict[str, set[str]]], errors: list[str]) -> None:
    shared_only_sources = {
        str(item.get("name") or "")
        for item in schedule.get("series") or []
        if item.get("guard_override_mode") == "shared_only"
    }
    if not shared_only_sources:
        return
    for item in filters:
        if "src" not in item:
            errors.append(
                "shared_only streams require every drop_filter to include src; "
                f"global filter would affect {sorted(shared_only_sources)}"
            )
            return


def has_shared_only_stream(schedule: dict) -> bool:
    return any(
        item.get("guard_override_mode") == "shared_only"
        for item in schedule.get("series") or []
    )


def lint_schedule(schedule_name: str, schedule: dict, strategies: dict | None = None) -> list[str]:
    errors: list[str] = []
    strategies = strategies or {}
    live_profile = schedule.get("live_profile") or {}
    overrides = live_profile.get("guard_overrides") or {}
    guards = schedule.get("guards") or {}
    filters = [parse_filter(raw) for raw in schedule.get("drop_filters") or []]
    live_filtered_sources = filtered_sources(schedule)
    require_source_scoped_filters = has_shared_only_stream(schedule)

    ob_filter = find_filter(filters, monthnum="11", signal="ob")
    ob_filters = find_filters(filters, monthnum="11", signal="ob")
    if not ob_filters:
        errors.append("missing drop_filter for November low-balance OB")
    else:
        if require_source_scoped_filters and not ob_filter and live_filtered_sources:
            ob_by_src = {only(item.get("src", {""}), "src"): item for item in ob_filters if item.get("src")}
            missing = live_filtered_sources - set(ob_by_src)
            if missing:
                errors.append(f"missing source-scoped November low-balance OB drop_filter for {sorted(missing)}")
            ob_filter = next(iter(ob_by_src.values()), {})
        if not ob_filter:
            errors.append("missing unambiguous drop_filter for November low-balance OB")
        else:
            require_equal(errors, "low_balance_ob_bad_months", csv_values(overrides.get("low_balance_ob_bad_months")), ob_filter["monthnum"])
            require_equal(errors, "low_balance_ob_bad_hours", csv_values(overrides.get("low_balance_ob_bad_hours")), ob_filter.get("hour", set()))
            require_equal(
                errors,
                "low_balance_ob_bad_max_month_start_balance",
                float(overrides.get("low_balance_ob_bad_max_month_start_balance", 0.0)),
                float(only(ob_filter.get("max_start", {"0"}), "max_start")),
            )
            require_equal(errors, "low_balance_ob_bad_hour_mult", float(overrides.get("low_balance_ob_bad_hour_mult", 1.0)), 0.0)

    sweep_filters = find_filters(filters, signal="sweep")
    if not sweep_filters:
        errors.append("missing drop_filter for March high-balance sweep")
    else:
        if require_source_scoped_filters and live_filtered_sources:
            sweep_by_src = {
                only(item.get("src", {""}), "src")
                for item in sweep_filters
                if item.get("src") and "3" in item.get("monthnum", set())
            }
            missing = live_filtered_sources - sweep_by_src
            if missing:
                errors.append(f"missing source-scoped March high-balance sweep drop_filter for {sorted(missing)}")
        months = set().union(*(item.get("monthnum", set()) for item in sweep_filters))
        hours_by_filter = {tuple(sorted(item.get("hour", set()))) for item in sweep_filters}
        max_day_by_filter = {only(item.get("max_day", {"0"}), "max_day") for item in sweep_filters}
        min_start_by_filter = {only(item.get("min_start", {"0"}), "min_start") for item in sweep_filters}
        if "3" not in months:
            errors.append("missing drop_filter for March high-balance sweep")
        require_equal(errors, "sweep_context_months", csv_values(overrides.get("sweep_context_months")), months)
        if len(hours_by_filter) == 1:
            require_equal(errors, "sweep_context_no_hours", csv_values(overrides.get("sweep_context_no_hours")), set(next(iter(hours_by_filter))))
        else:
            errors.append(f"sweep_context_no_hours: inconsistent sweep drop_filter hours={hours_by_filter!r}")
        require_equal(
            errors,
            "sweep_context_max_day",
            int(overrides.get("sweep_context_max_day", 0)),
            int(only(max_day_by_filter, "max_day")),
        )
        require_equal(
            errors,
            "sweep_context_min_month_start_balance",
            float(overrides.get("sweep_context_min_month_start_balance", 0.0)),
            float(only(min_start_by_filter, "min_start")),
        )

    guard_monthnums = {str(int(item)) for item in guards.get("guard_monthnums", [])}
    require_equal(
        errors,
        "monthly_profit_target_stop_months",
        csv_values(overrides.get("monthly_profit_target_stop_months")),
        guard_monthnums,
    )
    require_equal(
        errors,
        "monthly_profit_target_stop_max_balance",
        float(overrides.get("monthly_profit_target_stop_max_balance", 0.0)),
        float(guards.get("guard_max_month_start_balance", 0.0)),
    )
    require_equal(
        errors,
        "monthly_profit_target_stop_pct",
        float(overrides.get("monthly_profit_target_stop_pct", 0.0)),
        float(guards.get("profit_target_stop_pct", 0.0)),
    )
    guard2_monthnums = {str(int(item)) for item in guards.get("guard2_monthnums", [])}
    if guard2_monthnums or float(guards.get("profit_target_stop2_pct", 0.0)) > 0:
        require_equal(
            errors,
            "monthly_profit_target_stop2_months",
            csv_values(overrides.get("monthly_profit_target_stop2_months")),
            guard2_monthnums,
        )
        require_equal(
            errors,
            "monthly_profit_target_stop2_min_balance",
            float(overrides.get("monthly_profit_target_stop2_min_balance", 0.0)),
            float(guards.get("guard2_min_month_start_balance", 0.0)),
        )
        require_equal(
            errors,
            "monthly_profit_target_stop2_max_balance",
            float(overrides.get("monthly_profit_target_stop2_max_balance", 0.0)),
            float(guards.get("guard2_max_month_start_balance", 0.0)),
        )
        require_equal(
            errors,
            "monthly_profit_target_stop2_pct",
            float(overrides.get("monthly_profit_target_stop2_pct", 0.0)),
            float(guards.get("profit_target_stop2_pct", 0.0)),
        )

    if len(schedule.get("series") or []) > 1:
        require_equal(errors, "shared_monthly_guard", bool(overrides.get("shared_monthly_guard", False)), True)
        if not overrides.get("shared_monthly_guard_key"):
            errors.append("shared_monthly_guard_key is required for multi-stream schedules")

    lint_series_windows(schedule, strategies, errors)
    lint_series_context_filters(schedule, strategies, filters, errors)
    lint_shared_only_filters(schedule, filters, errors)

    return [f"{schedule_name}: {error}" for error in errors]


def lint_config(path: Path, schedule_name: str = "", strategies_path: Path = DEFAULT_STRATEGIES_CONFIG) -> list[str]:
    schedules = load_schedules(path)
    strategies = load_strategy_config(strategies_path)
    selected = {schedule_name: schedules[schedule_name]} if schedule_name else schedules
    errors: list[str] = []
    for name, schedule in selected.items():
        errors.extend(lint_schedule(name, schedule, strategies))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint portfolio schedule proxy/live guard consistency.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--strategies-config", type=Path, default=DEFAULT_STRATEGIES_CONFIG)
    parser.add_argument("--schedule", default="")
    args = parser.parse_args()

    errors = lint_config(args.config, args.schedule, args.strategies_config)
    if errors:
        print("portfolio schedule lint failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("portfolio schedule lint passed")


if __name__ == "__main__":
    main()
