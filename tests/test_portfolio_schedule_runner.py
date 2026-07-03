from __future__ import annotations

from pathlib import Path

from scripts.portfolio_schedule_runner import run_schedule


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["time", "pnl_proxy", "signal_type", "dir", "hour"]
    path.write_text(
        ",".join(fields)
        + "\n"
        + "\n".join(",".join(row.get(field, "") for field in fields) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def test_schedule_runner_applies_context_filters_and_targets(tmp_path):
    r1 = tmp_path / "r1.trades.csv"
    r2 = tmp_path / "r2.trades.csv"
    write_csv(
        r1,
        [
            {"time": "2024-10-01 00:00:00", "pnl_proxy": "10", "signal_type": "ob", "dir": "buy", "hour": "0"},
            {"time": "2024-10-02 00:00:00", "pnl_proxy": "-100", "signal_type": "ob", "dir": "buy", "hour": "0"},
            {"time": "2024-11-01 07:00:00", "pnl_proxy": "-50", "signal_type": "ob", "dir": "buy", "hour": "7"},
            {"time": "2024-11-02 08:00:00", "pnl_proxy": "15", "signal_type": "sweep", "dir": "buy", "hour": "8"},
        ],
    )
    write_csv(
        r2,
        [
            {"time": "2024-10-01 01:00:00", "pnl_proxy": "5", "signal_type": "sweep", "dir": "sell", "hour": "1"},
            {"time": "2024-11-01 08:00:00", "pnl_proxy": "20", "signal_type": "sweep", "dir": "sell", "hour": "8"},
        ],
    )
    cfg = tmp_path / "schedules.yaml"
    cfg.write_text(
        f"""
schedules:
  demo:
    deposit: 200
    days: 2
    targets:
      profit_min: 40
      daily_trades_min: 1
      require_non_negative_months: true
    series:
      - name: R1
        path: {r1}
      - name: R2
        path: {r2}
    drop_filters:
      - "monthnum=11;signal=ob;hour=7;max_start=2500"
    guards:
      guard_monthnums: [10]
      guard_max_month_start_balance: 2500
      profit_target_stop_pct: 3
      profit_target_min_trades: 1
""",
        encoding="utf-8",
    )

    report, audit = run_schedule(cfg, "demo")

    assert audit.passed
    assert audit.total_profit == 45
    assert audit.daily_trades == 1.5
    assert "2024-10 | 1 | 2 | 10.00" in report
    assert "2024-11 | 2 | 1 | 35.00" in report


def test_schedule_runner_can_require_positive_monthly_profit(tmp_path):
    r1 = tmp_path / "r1.trades.csv"
    write_csv(
        r1,
        [
            {"time": "2024-10-01 00:00:00", "pnl_proxy": "0", "signal_type": "ob", "dir": "buy", "hour": "0"},
            {"time": "2024-11-01 00:00:00", "pnl_proxy": "2", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    cfg = tmp_path / "schedules.yaml"
    cfg.write_text(
        f"""
schedules:
  demo:
    deposit: 200
    days: 2
    targets:
      profit_min: 0
      daily_trades_min: 0
      require_non_negative_months: true
      monthly_profit_min: 0.01
    series:
      - name: R1
        path: {r1}
    guards: {{}}
""",
        encoding="utf-8",
    )

    report, audit = run_schedule(cfg, "demo")

    assert not audit.passed
    assert audit.bad_months[0].month == "2024-10"
    assert "monthly profit >= 0.01 | 1 bad | False" in report


def test_schedule_runner_applies_second_profit_target_slot(tmp_path):
    r1 = tmp_path / "r1.trades.csv"
    write_csv(
        r1,
        [
            {"time": "2024-09-01 00:00:00", "pnl_proxy": "10", "signal_type": "ob", "dir": "buy", "hour": "0"},
            {"time": "2024-09-02 00:00:00", "pnl_proxy": "-100", "signal_type": "ob", "dir": "buy", "hour": "0"},
            {"time": "2024-10-01 00:00:00", "pnl_proxy": "500", "signal_type": "ob", "dir": "buy", "hour": "0"},
            {"time": "2025-09-01 00:00:00", "pnl_proxy": "10", "signal_type": "ob", "dir": "buy", "hour": "0"},
            {"time": "2025-09-02 00:00:00", "pnl_proxy": "20", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    cfg = tmp_path / "schedules.yaml"
    cfg.write_text(
        f"""
schedules:
  demo:
    deposit: 200
    days: 4
    targets:
      profit_min: 0
      daily_trades_min: 0
      require_non_negative_months: true
    series:
      - name: R1
        path: {r1}
    guards:
      guard_monthnums: [10]
      profit_target_stop_pct: 3
      guard_max_month_start_balance: 1000
      profit_target_stop2_pct: 3
      guard2_monthnums: [9]
      guard2_max_month_start_balance: 500
""",
        encoding="utf-8",
    )

    report, audit = run_schedule(cfg, "demo")

    assert audit.passed
    assert "2024-09 | 1 | 1 | 10.00" in report
    assert "profit_target2_3%" in report
    assert "2024-10 | 1 | 0 | 500.00" in report
    assert "2025-09 | 2 | 0 | 30.00" in report
