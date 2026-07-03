from __future__ import annotations

from pathlib import Path

from scripts.portfolio_schedule_lint import lint_config


def write_schedule(path: Path, low_balance_hours: str = "7,13") -> None:
    path.write_text(
        f"""
schedules:
  demo:
    series:
      - name: A
        strategy: v_a
      - name: B
        strategy: v_b
    live_profile:
      symbol: BTCUSDm
      guard_overrides:
        low_balance_ob_bad_months: "11"
        low_balance_ob_bad_hours: "{low_balance_hours}"
        low_balance_ob_bad_max_month_start_balance: 2500.0
        low_balance_ob_bad_hour_mult: 0.0
        sweep_context_months: "3"
        sweep_context_max_day: 2
        sweep_context_min_month_start_balance: 100000.0
        sweep_context_no_hours: "0,1"
        monthly_profit_target_stop_pct: 3.0
        monthly_profit_target_stop_max_balance: 2500.0
        monthly_profit_target_stop_months: "10,12"
        shared_monthly_guard: true
        shared_monthly_guard_key: "demo"
    drop_filters:
      - "monthnum=11;signal=ob;hour=7,13;max_start=2500"
      - "monthnum=3;signal=sweep;hour=0,1;min_start=100000;max_day=2"
    guards:
      guard_monthnums: [10, 12]
      guard_max_month_start_balance: 2500.0
      profit_target_stop_pct: 3.0
""",
        encoding="utf-8",
    )


def test_lint_accepts_matching_proxy_and_live_guards(tmp_path):
    cfg = tmp_path / "portfolio.yaml"
    write_schedule(cfg)

    assert lint_config(cfg, "demo") == []


def test_lint_rejects_drift_between_proxy_and_live_guards(tmp_path):
    cfg = tmp_path / "portfolio.yaml"
    write_schedule(cfg, low_balance_hours="7")

    errors = lint_config(cfg, "demo")

    assert any("low_balance_ob_bad_hours" in error for error in errors)


def test_lint_accepts_multiple_sweep_context_months(tmp_path):
    cfg = tmp_path / "portfolio.yaml"
    cfg.write_text(
        """
schedules:
  demo:
    series:
      - name: A
        strategy: v_a
      - name: B
        strategy: v_b
    live_profile:
      symbol: BTCUSDm
      guard_overrides:
        low_balance_ob_bad_months: "11"
        low_balance_ob_bad_hours: "7,13"
        low_balance_ob_bad_max_month_start_balance: 2500.0
        low_balance_ob_bad_hour_mult: 0.0
        sweep_context_months: "3,5"
        sweep_context_max_day: 2
        sweep_context_min_month_start_balance: 100000.0
        sweep_context_no_hours: "0,1,6,23"
        monthly_profit_target_stop_pct: 3.0
        monthly_profit_target_stop_max_balance: 2500.0
        monthly_profit_target_stop_months: "10,12"
        shared_monthly_guard: true
        shared_monthly_guard_key: "demo"
    drop_filters:
      - "monthnum=11;signal=ob;hour=7,13;max_start=2500"
      - "monthnum=3;signal=sweep;hour=0,1,6,23;min_start=100000;max_day=2"
      - "monthnum=5;signal=sweep;hour=0,1,6,23;min_start=100000;max_day=2"
    guards:
      guard_monthnums: [10, 12]
      guard_max_month_start_balance: 2500.0
      profit_target_stop_pct: 3.0
""",
        encoding="utf-8",
    )

    assert lint_config(cfg, "demo") == []


def test_lint_accepts_second_profit_target_slot(tmp_path):
    cfg = tmp_path / "portfolio.yaml"
    cfg.write_text(
        """
schedules:
  demo:
    series:
      - name: A
        strategy: v_a
      - name: B
        strategy: v_b
    live_profile:
      symbol: BTCUSDm
      guard_overrides:
        low_balance_ob_bad_months: "11"
        low_balance_ob_bad_hours: "7,13"
        low_balance_ob_bad_max_month_start_balance: 2500.0
        low_balance_ob_bad_hour_mult: 0.0
        sweep_context_months: "3"
        sweep_context_max_day: 2
        sweep_context_min_month_start_balance: 100000.0
        sweep_context_no_hours: "0,1"
        monthly_profit_target_stop_pct: 3.0
        monthly_profit_target_stop_max_balance: 65000.0
        monthly_profit_target_stop_months: "3,4,5,10,11,12"
        monthly_profit_target_stop2_pct: 3.0
        monthly_profit_target_stop2_max_balance: 5000.0
        monthly_profit_target_stop2_months: "9"
        shared_monthly_guard: true
        shared_monthly_guard_key: "demo"
    drop_filters:
      - "monthnum=11;signal=ob;hour=7,13;max_start=2500"
      - "monthnum=3;signal=sweep;hour=0,1;min_start=100000;max_day=2"
    guards:
      guard_monthnums: [3, 4, 5, 10, 11, 12]
      guard_max_month_start_balance: 65000.0
      profit_target_stop_pct: 3.0
      guard2_monthnums: [9]
      guard2_max_month_start_balance: 5000.0
      profit_target_stop2_pct: 3.0
""",
        encoding="utf-8",
    )

    assert lint_config(cfg, "demo") == []


def test_lint_rejects_second_profit_target_slot_drift(tmp_path):
    cfg = tmp_path / "portfolio.yaml"
    cfg.write_text(
        """
schedules:
  demo:
    series:
      - name: A
        strategy: v_a
      - name: B
        strategy: v_b
    live_profile:
      symbol: BTCUSDm
      guard_overrides:
        low_balance_ob_bad_months: "11"
        low_balance_ob_bad_hours: "7,13"
        low_balance_ob_bad_max_month_start_balance: 2500.0
        low_balance_ob_bad_hour_mult: 0.0
        sweep_context_months: "3"
        sweep_context_max_day: 2
        sweep_context_min_month_start_balance: 100000.0
        sweep_context_no_hours: "0,1"
        monthly_profit_target_stop_pct: 3.0
        monthly_profit_target_stop_max_balance: 65000.0
        monthly_profit_target_stop_months: "3,4,5,10,11,12"
        monthly_profit_target_stop2_pct: 3.0
        monthly_profit_target_stop2_max_balance: 65000.0
        monthly_profit_target_stop2_months: "9"
        shared_monthly_guard: true
        shared_monthly_guard_key: "demo"
    drop_filters:
      - "monthnum=11;signal=ob;hour=7,13;max_start=2500"
      - "monthnum=3;signal=sweep;hour=0,1;min_start=100000;max_day=2"
    guards:
      guard_monthnums: [3, 4, 5, 10, 11, 12]
      guard_max_month_start_balance: 65000.0
      profit_target_stop_pct: 3.0
      guard2_monthnums: [9]
      guard2_max_month_start_balance: 5000.0
      profit_target_stop2_pct: 3.0
""",
        encoding="utf-8",
    )

    errors = lint_config(cfg, "demo")

    assert any("monthly_profit_target_stop2_max_balance" in error for error in errors)


def write_entry_month_schedule(path: Path, csv_path: Path) -> None:
    path.write_text(
        f"""
schedules:
  demo:
    days: 720
    series:
      - name: Patch
        strategy: v_patch
        path: {csv_path}
    live_profile:
      symbol: BTCUSDm
      guard_overrides:
        low_balance_ob_bad_months: "11"
        low_balance_ob_bad_hours: "7,13"
        low_balance_ob_bad_max_month_start_balance: 2500.0
        low_balance_ob_bad_hour_mult: 0.0
        sweep_context_months: "3"
        sweep_context_max_day: 2
        sweep_context_min_month_start_balance: 100000.0
        sweep_context_no_hours: "0,1"
        monthly_profit_target_stop_pct: 3.0
        monthly_profit_target_stop_max_balance: 2500.0
        monthly_profit_target_stop_months: "10,12"
    drop_filters:
      - "monthnum=11;signal=ob;hour=7,13;max_start=2500"
      - "monthnum=3;signal=sweep;hour=0,1;min_start=100000;max_day=2"
    guards:
      guard_monthnums: [10, 12]
      guard_max_month_start_balance: 2500.0
      profit_target_stop_pct: 3.0
""",
        encoding="utf-8",
    )


def write_strategy_config(path: Path) -> None:
    path.write_text(
        """
v_patch:
  entry_months: "3"
""",
        encoding="utf-8",
    )


def write_trade_csv(path: Path, dates: list[str]) -> None:
    path.write_text(
        "date,time,signal_type,hour,pnl_proxy\n"
        + "".join(f"{date},{date} 20:00:00,htf_pullback,20,1.0\n" for date in dates),
        encoding="utf-8",
    )


def test_lint_rejects_single_month_csv_for_entry_month_patch(tmp_path):
    schedule = tmp_path / "portfolio.yaml"
    strategies = tmp_path / "strategies.yaml"
    trades = tmp_path / "single.csv"
    write_strategy_config(strategies)
    write_trade_csv(trades, ["2026-03-03"])
    write_entry_month_schedule(schedule, trades)

    errors = lint_config(schedule, "demo", strategies)

    assert any("single-month screen" in error for error in errors)


def test_lint_accepts_full_window_entry_month_patch_csv(tmp_path):
    schedule = tmp_path / "portfolio.yaml"
    strategies = tmp_path / "strategies.yaml"
    trades = tmp_path / "full.csv"
    write_strategy_config(strategies)
    write_trade_csv(trades, ["2025-03-03", "2026-03-03"])
    write_entry_month_schedule(schedule, trades)

    assert lint_config(schedule, "demo", strategies) == []


def write_context_strategy_config(path: Path) -> None:
    path.write_text(
        """
v_context:
  context_filter1_months: "1"
  context_filter1_no_buy_hours: "14,15"
  context_filter1_min_month_start_balance: 100000.0
  context_filter1_mult: 0.0
""",
        encoding="utf-8",
    )


def write_context_schedule(path: Path, csv_path: Path, include_context_filter: bool) -> None:
    context_line = '\n      - "src=CTX;monthnum=1;dir=buy;hour=14,15;min_start=100000"'
    path.write_text(
        f"""
schedules:
  demo:
    days: 720
    series:
      - name: CTX
        strategy: v_context
        path: {csv_path}
      - name: Base
        strategy: v_base
        path: {csv_path}
    live_profile:
      symbol: BTCUSDm
      guard_overrides:
        low_balance_ob_bad_months: "11"
        low_balance_ob_bad_hours: "7,13"
        low_balance_ob_bad_max_month_start_balance: 2500.0
        low_balance_ob_bad_hour_mult: 0.0
        sweep_context_months: "3"
        sweep_context_max_day: 2
        sweep_context_min_month_start_balance: 100000.0
        sweep_context_no_hours: "0,1"
        monthly_profit_target_stop_pct: 3.0
        monthly_profit_target_stop_max_balance: 2500.0
        monthly_profit_target_stop_months: "10,12"
        shared_monthly_guard: true
        shared_monthly_guard_key: "demo"
    drop_filters:
      - "monthnum=11;signal=ob;hour=7,13;max_start=2500"
      - "monthnum=3;signal=sweep;hour=0,1;min_start=100000;max_day=2"{context_line if include_context_filter else ""}
    guards:
      guard_monthnums: [10, 12]
      guard_max_month_start_balance: 2500.0
      profit_target_stop_pct: 3.0
""",
        encoding="utf-8",
    )


def test_lint_rejects_missing_series_context_filter_proxy(tmp_path):
    schedule = tmp_path / "portfolio.yaml"
    strategies = tmp_path / "strategies.yaml"
    trades = tmp_path / "full.csv"
    write_context_strategy_config(strategies)
    write_trade_csv(trades, ["2025-01-03", "2026-01-03"])
    write_context_schedule(schedule, trades, include_context_filter=False)

    errors = lint_config(schedule, "demo", strategies)

    assert any("context_filter1" in error for error in errors)


def test_lint_accepts_series_context_filter_proxy(tmp_path):
    schedule = tmp_path / "portfolio.yaml"
    strategies = tmp_path / "strategies.yaml"
    trades = tmp_path / "full.csv"
    write_context_strategy_config(strategies)
    write_trade_csv(trades, ["2025-01-03", "2026-01-03"])
    write_context_schedule(schedule, trades, include_context_filter=True)

    assert lint_config(schedule, "demo", strategies) == []


def test_lint_rejects_missing_context_filter4_proxy(tmp_path):
    schedule = tmp_path / "portfolio.yaml"
    strategies = tmp_path / "strategies.yaml"
    trades = tmp_path / "full.csv"
    strategies.write_text(
        """
v_context:
  context_filter4_months: "10"
  context_filter4_no_sell_hours: "0,1"
  context_filter4_min_month_start_balance: 50000.0
  context_filter4_mult: 0.0
""",
        encoding="utf-8",
    )
    write_trade_csv(trades, ["2025-10-03", "2026-10-03"])
    write_context_schedule(schedule, trades, include_context_filter=False)

    errors = lint_config(schedule, "demo", strategies)

    assert any("context_filter4" in error for error in errors)


def test_lint_rejects_global_drop_filter_with_shared_only_stream(tmp_path):
    schedule = tmp_path / "portfolio.yaml"
    strategies = tmp_path / "strategies.yaml"
    trades = tmp_path / "full.csv"
    write_trade_csv(trades, ["2025-11-03", "2026-11-03"])
    strategies.write_text("v_base: {}\n", encoding="utf-8")
    schedule.write_text(
        f"""
schedules:
  demo:
    deposit: 200
    series:
      - name: A
        strategy: v_base
        path: {trades}
        guard_override_mode: shared_only
    live_profile:
      symbol: BTCUSDm
      guard_overrides:
        low_balance_ob_bad_months: "11"
        low_balance_ob_bad_hours: "7"
        low_balance_ob_bad_max_month_start_balance: 2500.0
        low_balance_ob_bad_hour_mult: 0.0
        sweep_context_months: "3"
        sweep_context_max_day: 2
        sweep_context_min_month_start_balance: 100000.0
        sweep_context_no_hours: "0,1"
        monthly_profit_target_stop_pct: 3.0
        monthly_profit_target_stop_months: "10"
        shared_monthly_guard: true
        shared_monthly_guard_key: "demo"
    drop_filters:
      - "monthnum=11;signal=ob;hour=7;max_start=2500"
      - "monthnum=3;signal=sweep;hour=0,1;min_start=100000;max_day=2"
    guards:
      guard_monthnums: [10]
      profit_target_stop_pct: 3.0
""",
        encoding="utf-8",
    )

    errors = lint_config(schedule, "demo", strategies)

    assert any("shared_only streams require every drop_filter to include src" in error for error in errors)
