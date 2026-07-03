from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts.portfolio_guard_audit_prepare import prepare_guard_audit


def test_prepare_guard_audit_deploys_no_entry_profile_without_starting(tmp_path):
    schedule_cfg = tmp_path / "portfolio.yaml"
    strategy_cfg = tmp_path / "strategies.yaml"
    generated_root = tmp_path / "generated"
    mt5_data = tmp_path / "mt5data"
    output_dir = tmp_path / "results"

    strategy_cfg.write_text(
        """
v_a:
  version: VA
  bar_period_min: 5
  magic_number: 101
v_b:
  version: VB
  bar_period_min: 5
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
        shared_monthly_guard_key: demo
        shared_monthly_guard_debug: true
""",
        encoding="utf-8",
    )

    args = SimpleNamespace(
        schedule="demo",
        schedule_config=schedule_cfg,
        strategy_config=strategy_cfg,
        generated_root=generated_root,
        profile_name="AuditProfile",
        guard_key_suffix="audit",
        no_entry_month=12,
        mt5_home=tmp_path / "mt5home",
        mt5_data=mt5_data,
        compile=False,
        start=False,
        start_mode="startup",
        setup_delay_sec=1,
        post_start_wait=0,
        require_log_audit=False,
        log=[],
        latest_logs=2,
        output_dir=output_dir,
        output_prefix="guard_audit_demo",
        output=output_dir / "summary.md",
    )

    result = prepare_guard_audit(args)

    assert result.passed
    assert result.generated_profile.exists()
    assert result.installed_profile.exists()
    assert result.profile_audit.exists()
    assert result.log_audit.exists()
    assert "started=false" in result.report
    assert "start_mode=startup" in result.report
    assert "startup_templates=2" in result.report
    assert "pass=true" in result.report
    chart = (result.installed_profile / "chart01.chr").read_text(encoding="utf-16-le")
    assert "InpEntryMonths=12" in chart
    assert "InpSharedMonthlyGuardKey=demo_audit" in chart


def test_prepare_guard_audit_fails_when_started_without_events(tmp_path):
    schedule_cfg = tmp_path / "portfolio.yaml"
    strategy_cfg = tmp_path / "strategies.yaml"
    generated_root = tmp_path / "generated"
    mt5_data = tmp_path / "mt5data"
    logs = mt5_data / "logs"
    logs.mkdir(parents=True)
    log = logs / "20260525.log"
    log.write_text("no guard events", encoding="utf-8")

    strategy_cfg.write_text(
        """
v_a:
  version: VA
  bar_period_min: 5
  magic_number: 101
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
    live_profile:
      symbol: BTCUSDm
      guard_overrides:
        shared_monthly_guard: true
        shared_monthly_guard_key: demo
""",
        encoding="utf-8",
    )

    args = SimpleNamespace(
        schedule="demo",
        schedule_config=schedule_cfg,
        strategy_config=strategy_cfg,
        generated_root=generated_root,
        profile_name="AuditProfile",
        guard_key_suffix="audit",
        no_entry_month=12,
        mt5_home=tmp_path / "mt5home",
        mt5_data=mt5_data,
        compile=False,
        start=False,
        start_mode="startup",
        setup_delay_sec=1,
        post_start_wait=0,
        require_log_audit=True,
        log=[log],
        latest_logs=2,
        output_dir=tmp_path / "results",
        output_prefix="guard_audit_demo",
        output=None,
    )

    result = prepare_guard_audit(args)

    assert not result.passed
    assert "no SHARED_GUARD events found" in result.report
