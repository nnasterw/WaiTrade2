from __future__ import annotations

import os

from scripts.shared_guard_log_audit import (
    audit_events,
    expectations_from_manifest,
    latest_logs,
    parse_events,
    render,
)


def test_shared_guard_log_audit_accepts_two_versions(tmp_path):
    log = tmp_path / "ea.log"
    log.write_text(
        "\n".join(
            [
                "x SHARED_GUARD event=init key=demo version=R186 symbol=BTCUSDm month=202410 start=100.00 peak=100.00 count=0 entry_stopped=0 loss_stopped=0 profit_locked=0",
                "x SHARED_GUARD event=load key=demo version=R196 symbol=BTCUSDm month=202410 start=100.00 peak=100.00 count=0 entry_stopped=0 loss_stopped=0 profit_locked=0",
                "x SHARED_GUARD event=entry key=demo version=R186 symbol=BTCUSDm month=202410 start=100.00 peak=110.00 count=1 entry_stopped=0 loss_stopped=0 profit_locked=0",
            ]
        ),
        encoding="utf-8",
    )

    events = parse_events([log])
    errors = audit_events(events, "demo", {"R186", "R196"})
    report = render(events, errors)

    assert errors == []
    assert "events=3 pass=true" in report
    assert "R186,R196" in report


def test_shared_guard_log_audit_rejects_missing_version(tmp_path):
    log = tmp_path / "ea.log"
    log.write_text(
        "SHARED_GUARD event=init key=demo version=R186 symbol=BTCUSDm month=202410 start=100.00 peak=100.00 count=0 entry_stopped=0 loss_stopped=0 profit_locked=0\n",
        encoding="utf-8",
    )

    events = parse_events([log])
    errors = audit_events(events, "demo", {"R186", "R196"})

    assert any("missing versions" in error for error in errors)


def test_shared_guard_log_audit_accepts_oninit_only_events(tmp_path):
    log = tmp_path / "ea.log"
    log.write_text(
        "\n".join(
            [
                "SHARED_GUARD event=init key=demo version=R224 symbol=BTCUSDm month=202605 start=200.00 peak=200.00 count=0 entry_stopped=0 loss_stopped=0 profit_locked=0",
                "SHARED_GUARD event=load key=demo version=R225 symbol=BTCUSDm month=202605 start=200.00 peak=200.00 count=0 entry_stopped=0 loss_stopped=0 profit_locked=0",
                "SHARED_GUARD event=load key=demo version=R226 symbol=BTCUSDm month=202605 start=200.00 peak=200.00 count=0 entry_stopped=0 loss_stopped=0 profit_locked=0",
            ]
        ),
        encoding="utf-8",
    )

    events = parse_events([log])
    errors = audit_events(events, "demo", {"R224", "R225", "R226"})

    assert errors == []


def test_expectations_from_manifest_reads_key_and_versions(tmp_path):
    manifest = tmp_path / "portfolio_manifest.yaml"
    manifest.write_text(
        """
charts:
  - version: R224
    shared_monthly_guard_key: demo_run
  - version: R225
    shared_monthly_guard_key: demo_run
""",
        encoding="utf-8",
    )

    key, versions = expectations_from_manifest(manifest)

    assert key == "demo_run"
    assert versions == {"R224", "R225"}


def test_latest_logs_reads_terminal_and_tester_logs(tmp_path):
    mt5_data = tmp_path / "mt5"
    terminal_logs = mt5_data / "logs"
    tester_logs = mt5_data / "Tester" / "logs"
    terminal_logs.mkdir(parents=True)
    tester_logs.mkdir(parents=True)
    old_log = terminal_logs / "20260524.log"
    new_log = tester_logs / "20260525.log"
    old_log.write_text("old", encoding="utf-8")
    new_log.write_text("new", encoding="utf-8")
    os.utime(old_log, (1, 1))
    os.utime(new_log, (2, 2))

    assert latest_logs(mt5_data, limit=1) == [new_log]


def test_latest_logs_reads_live_mql5_logs(tmp_path):
    mt5_data = tmp_path / "mt5"
    terminal_logs = mt5_data / "logs"
    live_logs = mt5_data / "MQL5" / "Logs"
    terminal_logs.mkdir(parents=True)
    live_logs.mkdir(parents=True)
    old_log = terminal_logs / "20260524.log"
    live_log = live_logs / "20260525.log"
    old_log.write_text("old", encoding="utf-8")
    live_log.write_text("live", encoding="utf-8")
    os.utime(old_log, (1, 1))
    os.utime(live_log, (2, 2))

    assert latest_logs(mt5_data, limit=1) == [live_log]
