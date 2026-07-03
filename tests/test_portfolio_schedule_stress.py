from __future__ import annotations

from pathlib import Path

from scripts.portfolio_schedule_stress import render, stress_schedule


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["time", "pnl_proxy", "signal_type", "dir", "hour"]
    path.write_text(
        ",".join(fields)
        + "\n"
        + "\n".join(",".join(row.get(field, "") for field in fields) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def test_schedule_stress_applies_cost_only_to_executed_trades(tmp_path):
    trades = tmp_path / "r1.trades.csv"
    write_csv(
        trades,
        [
            {"time": "2024-10-01 00:00:00", "pnl_proxy": "2", "signal_type": "ob", "dir": "buy", "hour": "0"},
            {"time": "2024-10-01 01:00:00", "pnl_proxy": "2", "signal_type": "ob", "dir": "buy", "hour": "1"},
            {"time": "2024-11-01 07:00:00", "pnl_proxy": "-100", "signal_type": "ob", "dir": "buy", "hour": "7"},
            {"time": "2024-11-01 08:00:00", "pnl_proxy": "3", "signal_type": "sweep", "dir": "sell", "hour": "8"},
        ],
    )
    cfg = tmp_path / "schedules.yaml"
    cfg.write_text(
        f"""
schedules:
  demo:
    deposit: 200
    days: 2
    series:
      - name: R1
        path: {trades}
    drop_filters:
      - "monthnum=11;signal=ob;hour=7;max_start=2500"
    guards: {{}}
""",
        encoding="utf-8",
    )

    rows = stress_schedule(cfg, "demo", [0.0, 1.0])

    assert rows[0].total_profit == 7
    assert rows[0].bad_months == []
    assert rows[1].total_profit == 4
    assert rows[1].bad_months == []
    assert rows[1].min_month is not None
    assert rows[1].min_month.profit == 2


def test_render_shows_weakest_month():
    report = render([])

    assert "weakest_month" in report
