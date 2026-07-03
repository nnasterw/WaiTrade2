from __future__ import annotations

from pathlib import Path

from scripts.portfolio_shortfall_scan import scan_shortfall


def write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    lines = ["time,pnl_proxy,signal_type,dir,hour"]
    for time, pnl in rows:
        lines.append(f"{time},{pnl},ob,buy,0")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_shortfall_scan_ranks_by_shortfall_reduction(tmp_path: Path) -> None:
    base_csv = tmp_path / "base.trades.csv"
    weak_csv = tmp_path / "weak.trades.csv"
    strong_csv = tmp_path / "strong.trades.csv"
    write_csv(base_csv, [("2024-06-01 00:00:00", 70), ("2024-07-01 00:00:00", 10)])
    write_csv(weak_csv, [("2024-06-01 00:00:00", 1), ("2024-07-01 00:00:00", 5)])
    write_csv(strong_csv, [("2024-06-01 00:00:00", 1), ("2024-07-01 00:00:00", 100)])
    cfg = tmp_path / "portfolio.yaml"
    cfg.write_text(
        f"""
schedules:
  demo:
    deposit: 200
    targets:
      require_non_negative_months: true
      monthly_profit_min: 0.01
    series:
      - name: BASE
        path: {base_csv}
    guards: {{}}
""",
        encoding="utf-8",
    )

    rows, base = scan_shortfall(
        cfg,
        "demo",
        [str(tmp_path / "*.trades.csv")],
        target_pct=35.0,
        top=10,
        min_covered_months=2,
        require_pass=True,
    )

    assert round(base.total_shortfall, 2) == 84.50
    assert rows[0].name == "strong.trades.csv"
    assert rows[0].shortfall_delta == 84.5
    assert rows[0].below_delta == 1
