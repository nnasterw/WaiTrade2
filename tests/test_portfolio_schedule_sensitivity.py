from __future__ import annotations

from scripts.portfolio_schedule_sensitivity import render, scan_sensitivity


def write_csv(path, rows: list[dict[str, str]]) -> None:
    fields = ["time", "pnl_proxy", "signal_type", "dir", "hour"]
    path.write_text(
        ",".join(fields)
        + "\n"
        + "\n".join(",".join(row.get(field, "") for field in fields) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def test_sensitivity_reports_drop_and_scale_scenarios(tmp_path):
    r1 = tmp_path / "r1.trades.csv"
    r2 = tmp_path / "r2.trades.csv"
    write_csv(
        r1,
        [
            {"time": "2026-03-01 00:00:00", "pnl_proxy": "10", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    write_csv(
        r2,
        [
            {"time": "2026-03-01 00:01:00", "pnl_proxy": "-2", "signal_type": "ob", "dir": "buy", "hour": "0"},
            {"time": "2026-04-01 00:01:00", "pnl_proxy": "4", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    cfg = tmp_path / "portfolio.yaml"
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
      - name: R2
        path: {r2}
    guards: {{}}
""",
        encoding="utf-8",
    )

    rows = scan_sensitivity(cfg, "demo", [0.5])
    report = render("demo", rows)

    assert [row.scenario for row in rows] == [
        "BASE",
        "drop R1",
        "scale R1 x0.5",
        "drop R2",
        "scale R2 x0.5",
    ]
    assert rows[0].total_profit == 12
    assert rows[1].bad_months == 1
    assert "drop R2" in report
