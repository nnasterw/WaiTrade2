from __future__ import annotations

from pathlib import Path

import yaml

from scripts.mt5_portfolio_live_profile import create_profile


def test_create_profile_generates_two_guarded_charts(tmp_path):
    schedule_cfg = tmp_path / "portfolio.yaml"
    strategy_cfg = tmp_path / "strategies.yaml"
    out_dir = tmp_path / "profiles"

    strategy_cfg.write_text(
        """
v_a:
  version: VA
  bar_period_min: 30
  magic_number: 101
  sweep_no_hours: "16,18"
v_b:
  version: VB
  bar_period_min: 30
  magic_number: 102
  sweep_no_hours: "16,18"
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
        low_balance_ob_bad_months: "11"
        low_balance_ob_bad_hours: "7,13"
        monthly_profit_target_stop_pct: 3.0
        monthly_profit_target_stop_months: "10,12"
        shared_monthly_guard: true
        shared_monthly_guard_key: "demo"
        shared_monthly_guard_debug: true
""",
        encoding="utf-8",
    )

    profile = create_profile("demo", schedule_cfg, strategy_cfg, out_dir, "run01")

    assert (profile / "chart01.chr").exists()
    assert (profile / "chart02.chr").exists()
    assert (profile / "order.wnd").read_text(encoding="utf-16").splitlines() == [
        "chart01.chr",
        "chart02.chr",
    ]
    chart1 = (profile / "chart01.chr").read_text(encoding="utf-16-le")
    chart2 = (profile / "chart02.chr").read_text(encoding="utf-16-le")
    assert "symbol=BTCUSDm" in chart1
    assert "InpMagicNumber=101" in chart1
    assert "InpMagicNumber=102" in chart2
    assert "InpLowBalanceOBBadMonths=11" in chart1
    assert "InpSharedMonthlyGuard=true" in chart1
    assert "InpSharedMonthlyGuardDebug=true" in chart1
    assert "InpSharedMonthlyGuardKey=demo_run01" in chart2
    assert "InpMonthlyProfitTargetStopMonths=10,12" in chart2

    manifest = yaml.safe_load((profile / "portfolio_manifest.yaml").read_text(encoding="utf-8"))
    assert [item["stream"] for item in manifest["charts"]] == ["A", "B"]
    assert manifest["guard_key_suffix"] == "run01"
    assert manifest["charts"][0]["shared_monthly_guard_key"] == "demo_run01"


def test_create_profile_can_force_no_entry_month(tmp_path):
    schedule_cfg = tmp_path / "portfolio.yaml"
    strategy_cfg = tmp_path / "strategies.yaml"
    out_dir = tmp_path / "profiles"

    strategy_cfg.write_text(
        """
v_a:
  version: VA
  bar_period_min: 30
  magic_number: 101
  entry_months: "3,5"
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
""",
        encoding="utf-8",
    )

    profile = create_profile("demo", schedule_cfg, strategy_cfg, out_dir, "audit", no_entry_month=12)

    chart1 = (profile / "chart01.chr").read_text(encoding="utf-16-le")
    chart2 = (profile / "chart02.chr").read_text(encoding="utf-16-le")
    manifest = yaml.safe_load((profile / "portfolio_manifest.yaml").read_text(encoding="utf-8"))

    assert "InpEntryMonths=12" in chart1
    assert "InpEntryMonths=12" in chart2
    assert "InpSharedMonthlyGuardKey=demo_audit" in chart1
    assert manifest["no_entry_month"] == 12


def test_create_profile_can_apply_only_shared_guard_overrides(tmp_path):
    schedule_cfg = tmp_path / "portfolio.yaml"
    strategy_cfg = tmp_path / "strategies.yaml"
    out_dir = tmp_path / "profiles"

    strategy_cfg.write_text(
        """
v_a:
  version: VA
  bar_period_min: 30
  magic_number: 101
  low_balance_ob_bad_months: "3,5"
  low_balance_ob_bad_hours: "2,3"
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
        guard_override_mode: shared_only
    live_profile:
      symbol: BTCUSDm
      guard_overrides:
        low_balance_ob_bad_months: "11"
        low_balance_ob_bad_hours: "7,13"
        shared_monthly_guard: true
        shared_monthly_guard_key: "demo"
        shared_monthly_guard_debug: true
""",
        encoding="utf-8",
    )

    profile = create_profile("demo", schedule_cfg, strategy_cfg, out_dir, "run01")

    chart = (profile / "chart01.chr").read_text(encoding="utf-16-le")
    assert "InpLowBalanceOBBadMonths=3,5" in chart
    assert "InpLowBalanceOBBadHours=2,3" in chart
    assert "InpSharedMonthlyGuard=true" in chart
    assert "InpSharedMonthlyGuardKey=demo_run01" in chart
