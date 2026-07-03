from __future__ import annotations

from pathlib import Path

from scripts.portfolio_return_sim import load_return_trades, run_schedule


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["time", "pnl_proxy", "signal_type", "dir", "hour"]
    path.write_text(
        ",".join(fields)
        + "\n"
        + "\n".join(",".join(row.get(field, "") for field in fields) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def test_load_return_trades_reconstructs_source_balance(tmp_path):
    trades = tmp_path / "r1.trades.csv"
    write_csv(
        trades,
        [
            {"time": "2024-10-01 00:00:00", "pnl_proxy": "20", "signal_type": "ob", "dir": "buy", "hour": "0"},
            {"time": "2024-10-01 01:00:00", "pnl_proxy": "22", "signal_type": "ob", "dir": "buy", "hour": "1"},
        ],
    )

    rows = load_return_trades([f"R1={trades}"], source_deposit=200)

    assert rows[0].return_fraction == 0.10
    assert rows[1].source_balance_before == 220
    assert rows[1].return_fraction == 0.10


def test_return_schedule_applies_returns_to_shared_balance(tmp_path):
    r1 = tmp_path / "r1.trades.csv"
    r2 = tmp_path / "r2.trades.csv"
    write_csv(
        r1,
        [
            {"time": "2024-10-01 00:00:00", "pnl_proxy": "20", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    write_csv(
        r2,
        [
            {"time": "2024-10-01 00:01:00", "pnl_proxy": "20", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    cfg = tmp_path / "schedules.yaml"
    cfg.write_text(
        f"""
schedules:
  demo:
    deposit: 200
    days: 1
    targets:
      profit_min: 0
      daily_trades_min: 0
      require_non_negative_months: true
      monthly_profit_min: 0.01
    series:
      - name: R1
        path: {r1}
      - name: R2
        path: {r2}
    guards: {{}}
""",
        encoding="utf-8",
    )

    report, audit = run_schedule(cfg, "demo")

    assert round(audit.total_profit, 2) == 42.00
    assert "2024-10 | 2 | 0 | 42.00 | 200.00 | 242.00" in report
