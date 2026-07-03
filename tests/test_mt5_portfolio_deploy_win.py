from __future__ import annotations

from unittest.mock import patch

from pathlib import Path
from types import SimpleNamespace

from scripts.mt5_portfolio_deploy_win import deploy, install_startup_assets, start_terminal, start_with_config


def test_deploy_installs_profile_and_syncs_sources(tmp_path):
    schedule_cfg = tmp_path / "portfolio.yaml"
    strategy_cfg = tmp_path / "strategies.yaml"
    generated_root = tmp_path / "generated"
    mt5_data = tmp_path / "mt5data"

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
""",
        encoding="utf-8",
    )

    args = SimpleNamespace(
        schedule="demo",
        schedule_config=schedule_cfg,
        strategy_config=strategy_cfg,
        generated_root=generated_root,
        profile_name="DemoProfile",
        guard_key_suffix="run01",
        mt5_home=tmp_path / "mt5home",
        mt5_data=mt5_data,
        compile=False,
        start=False,
    )

    generated, installed = deploy(args)

    assert generated.exists()
    assert installed == mt5_data / "MQL5" / "Profiles" / "Charts" / "DemoProfile"
    assert (installed / "chart01.chr").exists()
    assert (installed / "chart02.chr").exists()
    chart = (installed / "chart01.chr").read_text(encoding="utf-16-le")
    assert "InpSharedMonthlyGuardKey=demo_run01" in chart
    assert (mt5_data / "MQL5" / "Experts" / "WaiTrade2" / "WaiTrade_OB.mq5").exists()
    assert (mt5_data / "MQL5" / "Scripts" / "WaiTrade2" / "ClearSharedMonthlyGuard.mq5").exists()


def test_deploy_can_install_no_entry_guard_audit_profile(tmp_path):
    schedule_cfg = tmp_path / "portfolio.yaml"
    strategy_cfg = tmp_path / "strategies.yaml"
    generated_root = tmp_path / "generated"
    mt5_data = tmp_path / "mt5data"

    strategy_cfg.write_text(
        """
v_a:
  version: VA
  bar_period_min: 5
  magic_number: 101
  entry_months: "3"
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
    )

    _, installed = deploy(args)

    chart = (installed / "chart01.chr").read_text(encoding="utf-16-le")
    assert "InpEntryMonths=12" in chart
    assert "InpSharedMonthlyGuardDebug=true" in chart
    assert "InpSharedMonthlyGuardKey=demo_audit" in chart


def test_start_terminal_uses_profile_argument(tmp_path):
    mt5_home = tmp_path / "mt5home"
    terminal = mt5_home / "terminal64.exe"
    mt5_home.mkdir()
    terminal.write_text("", encoding="utf-8")

    with patch("scripts.mt5_portfolio_deploy_win.subprocess.Popen") as popen:
        start_terminal(mt5_home, "DemoProfile")

    popen.assert_called_once_with([str(terminal), "/profile:DemoProfile"], cwd=str(mt5_home))


def test_start_with_config_uses_config_argument(tmp_path):
    mt5_home = tmp_path / "mt5home"
    terminal = mt5_home / "terminal64.exe"
    mt5_home.mkdir()
    terminal.write_text("", encoding="utf-8")
    config = tmp_path / "startup.ini"
    config.write_text("[StartUp]\n", encoding="utf-8")

    with patch("scripts.mt5_portfolio_deploy_win.subprocess.Popen") as popen:
        start_with_config(mt5_home, config)

    popen.assert_called_once_with([str(terminal), f"/config:{config}"], cwd=str(mt5_home))


def test_install_startup_assets_generates_templates_set_and_ini(tmp_path):
    schedule_cfg = tmp_path / "portfolio.yaml"
    strategy_cfg = tmp_path / "strategies.yaml"
    generated_root = tmp_path / "generated"
    mt5_data = tmp_path / "mt5data"

    strategy_cfg.write_text(
        """
mt5_account:
  login: 123
  server: DemoServer
  proxy_enable: 1
  proxy_type: 0
  proxy_address: "127.0.0.1:7897"
v_a:
  version: VA
  bar_period_min: 5
  magic_number: 101
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
        shared_monthly_guard_key: demo
""",
        encoding="utf-8",
    )

    args = SimpleNamespace(
        schedule="demo",
        schedule_config=schedule_cfg,
        strategy_config=strategy_cfg,
        generated_root=generated_root,
        profile_name="DemoProfile",
        guard_key_suffix="run01",
        mt5_home=tmp_path / "mt5home",
        mt5_data=mt5_data,
        compile=False,
        start=False,
    )
    generated, _ = deploy(args)

    assets = install_startup_assets(generated, mt5_data, "DemoProfile", strategy_cfg, setup_delay_sec=2)

    assert len(assets.templates) == 2
    assert assets.templates[0] == mt5_data / "MQL5" / "Profiles" / "Templates" / "DemoProfile_chart01.tpl"
    assert "InpMagicNumber=101" in assets.templates[0].read_text(encoding="utf-16-le")
    setup_text = assets.setup_set.read_text(encoding="utf-8")
    assert "InpSymbol=BTCUSDm" in setup_text
    assert "InpPeriodsCsv=5,30" in setup_text
    assert "InpTemplatesCsv=DemoProfile_chart01.tpl,DemoProfile_chart02.tpl" in setup_text
    assert "InpSetupDelaySec=2" in setup_text
    ini_text = assets.config_ini.read_text(encoding="utf-8")
    assert "Login=123" in ini_text
    assert "Expert=WaiTrade2\\PortfolioSetup" in ini_text
    assert "ExpertParameters=DemoProfile_setup.set" in ini_text
