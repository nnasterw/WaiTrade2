from __future__ import annotations

from scripts.mt5_portfolio_live_profile import create_profile
from scripts.mt5_portfolio_profile_audit import audit_profile


def write_configs(tmp_path):
    schedule_cfg = tmp_path / "portfolio.yaml"
    strategy_cfg = tmp_path / "strategies.yaml"
    out_dir = tmp_path / "profiles"

    strategy_cfg.write_text(
        """
v_a:
  version: VA
  bar_period_min: 5
  magic_number: 101
  entry_months: "3"
  context_filter1_months: "1"
  context_filter1_no_buy_hours: "14,15"
  context_filter1_min_month_start_balance: 100000.0
  context_filter1_mult: 0.0
  context_filter4_months: "10"
  context_filter4_no_sell_hours: "0,1"
  context_filter4_min_month_start_balance: 50000.0
  context_filter4_mult: 0.0
v_b:
  version: VB
  bar_period_min: 30
  magic_number: 102
""",
        encoding="utf-8",
    )
    schedule_cfg.write_text(
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
        shared_monthly_guard: true
        shared_monthly_guard_key: "demo"
        shared_monthly_guard_debug: true
        sweep_context_months: "3,5"
        sweep_context_no_hours: "0,1,6,23"
""",
        encoding="utf-8",
    )
    return schedule_cfg, strategy_cfg, out_dir


def test_profile_audit_accepts_generated_profile(tmp_path):
    schedule_cfg, strategy_cfg, out_dir = write_configs(tmp_path)
    profile = create_profile("demo", schedule_cfg, strategy_cfg, out_dir, "run01")

    errors, report = audit_profile(profile, "demo", schedule_cfg, strategy_cfg)

    assert errors == []
    assert "pass=true" in report
    assert "s1:m=1 mult=0.0 buy=14,15 min=100000.0" in report
    assert "s4:m=10 mult=0.0 sell=0,1 min=50000.0" in report
    assert "InpEntryMonths" not in report


def test_profile_audit_rejects_drifted_chart_input(tmp_path):
    schedule_cfg, strategy_cfg, out_dir = write_configs(tmp_path)
    profile = create_profile("demo", schedule_cfg, strategy_cfg, out_dir, "run01")
    chart = profile / "chart01.chr"
    text = chart.read_text(encoding="utf-16-le")
    chart.write_text(text.replace("InpEntryMonths=3", "InpEntryMonths=4"), encoding="utf-16-le")

    errors, report = audit_profile(profile, "demo", schedule_cfg, strategy_cfg)

    assert any("InpEntryMonths" in error for error in errors)
    assert "pass=false" in report


def test_profile_audit_accepts_manifest_no_entry_month(tmp_path):
    schedule_cfg, strategy_cfg, out_dir = write_configs(tmp_path)
    profile = create_profile("demo", schedule_cfg, strategy_cfg, out_dir, "run01", no_entry_month=12)

    errors, report = audit_profile(profile, "demo", schedule_cfg, strategy_cfg)

    assert errors == []
    assert "pass=true" in report
