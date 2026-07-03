from __future__ import annotations

from types import SimpleNamespace

from scripts.portfolio_path_sim import Trade
from scripts.portfolio_schedule_attribution import render, render_risk, run_attribution, source_risk


def args(**overrides):
    defaults = dict(
        deposit=200.0,
        profit_target_stop_pct=0.0,
        profit_target_min_trades=1,
        loss_stop_pct=0.0,
        loss_stop_min_trades=1,
        early_loss_stop_trades=0,
        early_loss_stop_pct=0.0,
        guard_months=set(),
        guard_monthnums=set(),
        guard_min_month_start_balance=0.0,
        guard_max_month_start_balance=0.0,
        signal_block_signal="",
        signal_block_loss_pct=0.0,
        signal_block_monthnums=set(),
        signal_block_min_month_start_balance=0.0,
        signal_block_max_day=0,
        drop_filters=[],
        drop_min_month_start_balance=0.0,
        drop_max_month_start_balance=0.0,
        drop_max_day=0,
        drop_only_before_month_profit=False,
        drop_only_monthly_negative=False,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def trade(source: str, time: str, pnl: float) -> Trade:
    return Trade(
        source=source,
        time=time,
        month=time[:7],
        monthnum=int(time[5:7]),
        day=int(time[8:10]),
        pnl=pnl,
        signal_type="ob",
        direction="buy",
        hour=time[11:13],
    )


def test_run_attribution_splits_profit_and_cost_by_source():
    rows = run_attribution(
        [
            trade("A", "2026-03-01 00:00:00", 10.0),
            trade("B", "2026-03-01 00:01:00", -3.0),
            trade("A", "2026-04-01 00:00:00", 2.0),
        ],
        args(),
        cost_per_trade=0.5,
    )

    assert rows[0].month == "2026-03"
    assert rows[0].profit == 6.0
    assert rows[0].trades == 2
    assert rows[0].source["A"].profit == 9.5
    assert rows[0].source["B"].profit == -3.5
    assert rows[1].start_balance == 206.0


def test_run_attribution_counts_skips_after_profit_target_by_source():
    rows = run_attribution(
        [
            trade("A", "2026-03-01 00:00:00", 10.0),
            trade("B", "2026-03-01 00:01:00", 5.0),
        ],
        args(
            profit_target_stop_pct=3.0,
            guard_monthnums={"03"},
            profit_target_min_trades=1,
        ),
    )

    assert rows[0].profit == 10.0
    assert rows[0].trades == 1
    assert rows[0].skipped == 1
    assert rows[0].source["B"].skipped == 1
    assert rows[0].stop_reason == "profit_target_3%"
    assert rows[0].details[0].action == "execute"
    assert rows[0].details[0].reason == "profit_target_3%"
    assert rows[0].details[1].action == "skip"
    assert rows[0].details[1].reason == "stopped:profit_target_3%"


def test_render_can_filter_months():
    rows = run_attribution(
        [
            trade("A", "2026-03-01 00:00:00", 1.0),
            trade("A", "2026-04-01 00:00:00", 2.0),
        ],
        args(),
    )

    report = render(rows, only_months={"2026-04"})

    assert "2026-04" in report
    assert "2026-03" not in report


def test_render_detail_prints_trade_skip_reasons():
    rows = run_attribution(
        [
            trade("A", "2026-03-01 00:00:00", 10.0),
            trade("B", "2026-03-01 00:01:00", 5.0),
        ],
        args(
            profit_target_stop_pct=3.0,
            guard_monthnums={"03"},
            profit_target_min_trades=1,
        ),
    )

    report = render(rows, only_months={"2026-03"}, detail=True)

    assert "## Trade details" in report
    assert "| 2026-03 | 2026-03-01 00:01:00 | B | ob | buy | 00 | 5.00 | skip | stopped:profit_target_3% | 10.00 |" in report


def test_source_risk_counts_negative_months_and_worst_source():
    rows = run_attribution(
        [
            trade("A", "2026-03-01 00:00:00", 10.0),
            trade("B", "2026-03-01 00:01:00", -3.0),
            trade("A", "2026-04-01 00:00:00", -2.0),
            trade("B", "2026-04-01 00:01:00", -4.0),
        ],
        args(),
    )

    risks = {item.source: item for item in source_risk(rows)}
    report = render_risk(rows)

    assert risks["A"].negative_months == 1
    assert risks["A"].worst_month == "2026-04"
    assert risks["B"].negative_months == 2
    assert "| 2026-04 | 2 | 0 | -6.00 | 2 | B | -4.00 |  |" in report
    assert "| 2026-03 | 7.00 | 10.00 | -3.00 |" in report
