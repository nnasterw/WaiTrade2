from __future__ import annotations

from types import SimpleNamespace

from scripts.portfolio_preflight_win import run_preflight


def write_trade_csv(path, pnl: float = 2.0) -> None:
    path.write_text(
        "time,date,hour,signal_type,dir,pnl_proxy\n"
        f"2026-03-01 20:00:00,2026-03-01,20,htf_pullback,buy,{pnl}\n"
        f"2026-03-02 20:00:00,2026-03-02,20,htf_pullback,buy,{pnl}\n",
        encoding="utf-8",
    )


def write_configs(tmp_path, pnl: float = 2.0, preflight_require_cost: float | None = None):
    trades = tmp_path / "trades.csv"
    write_trade_csv(trades, pnl=pnl)
    preflight_block = ""
    if preflight_require_cost is not None:
        preflight_block = f"""
    preflight:
      require_cost_pass: {preflight_require_cost}
"""

    strategy_cfg = tmp_path / "strategies.yaml"
    strategy_cfg.write_text(
        """
v_patch:
  version: VPATCH
  bar_period_min: 5
  magic_number: 1001
  entry_months: "3"
""",
        encoding="utf-8",
    )

    schedule_cfg = tmp_path / "portfolio.yaml"
    schedule_cfg.write_text(
        f"""
schedules:
  demo:
    description: demo
    deposit: 200.0
    days: 2
    targets:
      profit_min: 0.0
      daily_trades_min: 0.5
      require_non_negative_months: true
      monthly_profit_min: 0.01
    series:
      - name: Patch
        strategy: v_patch
        path: "{trades.as_posix()}"
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
{preflight_block.rstrip()}
""",
        encoding="utf-8",
    )
    return schedule_cfg, strategy_cfg


def make_args(tmp_path, schedule_cfg, strategy_cfg, require_cost_pass=0.5, costs="0,0.5"):
    return SimpleNamespace(
        schedule="demo",
        schedule_config=schedule_cfg,
        strategy_config=strategy_cfg,
        generated_root=tmp_path / "generated",
        profile_name="DemoProfile",
        guard_key_suffix="run01",
        mt5_home=tmp_path / "mt5home",
        mt5_data=tmp_path / "mt5data",
        costs=costs,
        require_cost_pass=require_cost_pass,
        output_dir=tmp_path / "reports",
        output_prefix="demo_preflight",
        output=tmp_path / "reports" / "summary.md",
        compile=False,
    )


def test_preflight_passes_and_writes_profile_audits(tmp_path):
    schedule_cfg, strategy_cfg = write_configs(tmp_path, pnl=2.0)

    result = run_preflight(make_args(tmp_path, schedule_cfg, strategy_cfg))

    assert result.passed is True
    assert "pass=true" in result.report
    assert (tmp_path / "reports" / "demo_preflight_proxy.md").exists()
    assert (tmp_path / "reports" / "demo_preflight_installed_profile_audit.md").exists()
    assert (tmp_path / "mt5data" / "MQL5" / "Profiles" / "Charts" / "DemoProfile" / "chart01.chr").exists()


def test_preflight_fails_when_required_cost_has_bad_month(tmp_path):
    schedule_cfg, strategy_cfg = write_configs(tmp_path, pnl=0.1)

    result = run_preflight(make_args(tmp_path, schedule_cfg, strategy_cfg))

    assert result.passed is False
    assert "stress cost 0.5" in result.report


def test_preflight_uses_schedule_required_cost_when_cli_omitted(tmp_path):
    schedule_cfg, strategy_cfg = write_configs(tmp_path, pnl=0.75, preflight_require_cost=1.0)

    result = run_preflight(
        make_args(
            tmp_path,
            schedule_cfg,
            strategy_cfg,
            require_cost_pass=None,
            costs="0,0.5,1.0",
        )
    )

    assert result.passed is False
    assert "stress cost 1" in result.report
    assert "required_cost_pass=1" in result.report
