#!/usr/bin/env python3
"""Attribute a portfolio schedule proxy by month and source.

This is a diagnosis helper for the CSV path-level portfolio proxy. It uses the
same guard/filter order as portfolio_path_sim, then splits executed and skipped
trades by source so weak months can be traced to the leg that caused them.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
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
    build_args,
    load_config,
)


@dataclass
class SourceMonth:
    trades: int = 0
    skipped: int = 0
    profit: float = 0.0


@dataclass
class TradeDetail:
    time: str
    source: str
    signal: str
    direction: str
    hour: str
    pnl: float
    action: str
    reason: str
    month_profit_after: float


@dataclass
class AttributedMonth:
    month: str
    start_balance: float
    profit: float = 0.0
    trades: int = 0
    skipped: int = 0
    stop_reason: str = ""
    source: dict[str, SourceMonth] = field(default_factory=dict)
    details: list[TradeDetail] = field(default_factory=list)

    @property
    def end_balance(self) -> float:
        return self.start_balance + self.profit


@dataclass(frozen=True)
class SourceRisk:
    source: str
    trades: int
    profit: float
    negative_months: int
    worst_month: str
    worst_profit: float


def source_state(month: AttributedMonth, trade: Trade) -> SourceMonth:
    if trade.source not in month.source:
        month.source[trade.source] = SourceMonth()
    return month.source[trade.source]


def append_detail(
    month: AttributedMonth,
    trade: Trade,
    pnl: float,
    action: str,
    reason: str,
) -> None:
    month.details.append(
        TradeDetail(
            time=trade.time,
            source=trade.source,
            signal=trade.signal_type,
            direction=trade.direction,
            hour=trade.hour,
            pnl=pnl,
            action=action,
            reason=reason,
            month_profit_after=month.profit,
        )
    )


def run_attribution(
    trades: list[Trade],
    args: argparse.Namespace,
    cost_per_trade: float = 0.0,
) -> list[AttributedMonth]:
    months = sorted({trade.month for trade in trades})
    running_balance = args.deposit
    results: list[AttributedMonth] = []

    for month in months:
        state = MonthState(month=month, start_balance=running_balance)
        state.blocked_signals = set()
        attributed = AttributedMonth(month=month, start_balance=running_balance)

        for trade in [item for item in trades if item.month == month]:
            src = source_state(attributed, trade)
            if trade_matches_any_context_filter(trade, state, args.drop_filters, args):
                state.skipped += 1
                attributed.skipped += 1
                src.skipped += 1
                append_detail(attributed, trade, trade.pnl, "skip", "drop_filter")
                continue
            if state.blocked_signals and trade.signal_type in state.blocked_signals:
                state.skipped += 1
                attributed.skipped += 1
                src.skipped += 1
                append_detail(attributed, trade, trade.pnl, "skip", f"blocked_signal:{trade.signal_type}")
                continue
            if state.stopped:
                state.skipped += 1
                attributed.skipped += 1
                src.skipped += 1
                append_detail(attributed, trade, trade.pnl, "skip", f"stopped:{state.stop_reason}")
                continue

            pnl = trade.pnl - cost_per_trade
            state.trades += 1
            state.profit += pnl
            attributed.trades += 1
            attributed.profit += pnl
            src.trades += 1
            src.profit += pnl

            block_reason = should_block_signal_after_trade(state, trade, args)
            if block_reason:
                state.blocked_signals.add(trade.signal_type)
                state.stop_reason = f"{state.stop_reason},{block_reason}" if state.stop_reason else block_reason
            reason = should_stop_after_trade(state, args)
            if reason:
                state.stopped = True
                state.stop_reason = reason
            append_detail(attributed, trade, pnl, "execute", reason or block_reason)

        attributed.stop_reason = state.stop_reason
        results.append(attributed)
        running_balance = attributed.end_balance

    return results


def attribute_schedule(
    config_path: Path,
    schedule_name: str,
    cost_per_trade: float = 0.0,
) -> list[AttributedMonth]:
    schedules = load_config(config_path)
    if schedule_name not in schedules:
        names = ", ".join(sorted(schedules))
        raise SystemExit(f"unknown schedule: {schedule_name}; available: {names}")
    schedule = schedules[schedule_name]
    args = build_args(schedule)
    series = [as_series_arg(item) for item in schedule.get("series", [])]
    trades = load_trades(series)
    return run_attribution(trades, args, cost_per_trade=cost_per_trade)


def source_risk(rows: list[AttributedMonth]) -> list[SourceRisk]:
    sources = sorted({source for row in rows for source in row.source})
    result: list[SourceRisk] = []
    for source in sources:
        total_trades = 0
        total_profit = 0.0
        negative_months = 0
        worst_month = ""
        worst_profit = 0.0
        for row in rows:
            state = row.source.get(source, SourceMonth())
            total_trades += state.trades
            total_profit += state.profit
            if state.profit < 0:
                negative_months += 1
            if not worst_month or state.profit < worst_profit:
                worst_month = row.month
                worst_profit = state.profit
        result.append(
            SourceRisk(
                source=source,
                trades=total_trades,
                profit=total_profit,
                negative_months=negative_months,
                worst_month=worst_month,
                worst_profit=worst_profit,
            )
        )
    result.sort(key=lambda item: (item.negative_months, -item.profit), reverse=True)
    return result


def render_risk(rows: list[AttributedMonth]) -> str:
    sources = sorted({source for row in rows for source in row.source})
    lines = [
        "# Portfolio source risk audit",
        "",
        "warning: CSV path-level attribution only; not a valid MT5 portfolio backtest.",
        "",
        "## Source Summary",
        "",
        "| source | trades | profit | negative_months | worst_month | worst_profit |",
        "|---|---:|---:|---:|---|---:|",
    ]
    for item in source_risk(rows):
        lines.append(
            f"| {item.source} | {item.trades} | {item.profit:.2f} | "
            f"{item.negative_months} | {item.worst_month} | {item.worst_profit:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Monthly Overlap",
            "",
            "| month | trades | skipped | month_profit | negative_sources | worst_source | worst_profit | stop |",
            "|---|---:|---:|---:|---:|---|---:|---|",
        ]
    )
    for row in rows:
        negative_sources = [
            source for source, state in row.source.items()
            if state.profit < 0
        ]
        worst_source = ""
        worst_profit = 0.0
        if row.source:
            worst_source, worst_state = min(row.source.items(), key=lambda item: item[1].profit)
            worst_profit = worst_state.profit
        lines.append(
            f"| {row.month} | {row.trades} | {row.skipped} | {row.profit:.2f} | "
            f"{len(negative_sources)} | {worst_source} | {worst_profit:.2f} | {row.stop_reason} |"
        )

    lines.extend(
        [
            "",
            "## Monthly Matrix",
            "",
            "| month | month_profit | " + " | ".join(sources) + " |",
            "|---|---:|" + "|".join("---:" for _ in sources) + "|",
        ]
    )
    for row in rows:
        cells = [
            f"{row.source.get(source, SourceMonth()).profit:.2f}"
            for source in sources
        ]
        lines.append(f"| {row.month} | {row.profit:.2f} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def render(rows: list[AttributedMonth], only_months: set[str] | None = None, detail: bool = False) -> str:
    selected = [row for row in rows if not only_months or row.month in only_months]
    lines = [
        "# Portfolio schedule attribution",
        "",
        "warning: CSV path-level attribution only; not a valid MT5 portfolio backtest.",
        "",
        "| month | source | trades | skipped | profit | month_profit | stop |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in selected:
        for source, state in sorted(row.source.items()):
            lines.append(
                f"| {row.month} | {source} | {state.trades} | {state.skipped} | "
                f"{state.profit:.2f} | {row.profit:.2f} | {row.stop_reason} |"
            )
    if detail:
        lines.extend(
            [
                "",
                "## Trade details",
                "",
                "| month | time | source | signal | dir | hour | pnl | action | reason | month_profit_after |",
                "|---|---|---|---|---|---:|---:|---|---|---:|",
            ]
        )
        for row in selected:
            for item in row.details:
                lines.append(
                    f"| {row.month} | {item.time} | {item.source} | {item.signal} | "
                    f"{item.direction} | {item.hour} | {item.pnl:.2f} | {item.action} | "
                    f"{item.reason} | {item.month_profit_after:.2f} |"
                )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Attribute a portfolio schedule proxy by source.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--schedule", default="r186_r196_r117_r209_march_guard")
    parser.add_argument("--cost-per-trade", type=float, default=0.0)
    parser.add_argument("--months", default="", help="Comma-separated months to print")
    parser.add_argument("--detail", action="store_true", help="Print per-trade execute/skip reasons")
    parser.add_argument("--risk", action="store_true", help="Print source-level negative-month overlap report")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    months = {part.strip() for part in args.months.split(",") if part.strip()} or None
    rows = attribute_schedule(args.config, args.schedule, args.cost_per_trade)
    report = render_risk(rows) if args.risk else render(rows, only_months=months, detail=args.detail)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
