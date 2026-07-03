from __future__ import annotations

from pathlib import Path

from scripts.portfolio_monthly_return_audit import audit_schedule, render


def write_csv(path: Path) -> None:
    path.write_text(
        "time,pnl_proxy,signal_type,dir,hour\n"
        "2024-06-01 00:00:00,70,ob,buy,0\n"
        "2024-07-01 00:00:00,10,ob,buy,0\n",
        encoding="utf-8",
    )


def test_monthly_return_audit_reports_target_shortfall(tmp_path: Path) -> None:
    trades = tmp_path / "trades.csv"
    write_csv(trades)
    cfg = tmp_path / "schedules.yaml"
    cfg.write_text(
        f"""
schedules:
  demo:
    deposit: 200
    series:
      - name: A
        path: {trades}
    guards: {{}}
""",
        encoding="utf-8",
    )

    rows = audit_schedule(cfg, "demo", 35.0)
    report = render("demo", rows, 35.0)

    assert rows[0].return_pct == 35.0
    assert rows[0].shortfall == 0.0
    assert round(rows[1].return_pct, 2) == 3.70
    assert rows[1].shortfall == 84.5
    assert "below=1" in report
    assert "2024-07*" in report
