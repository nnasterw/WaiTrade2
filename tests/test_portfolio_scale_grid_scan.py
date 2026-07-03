from __future__ import annotations

from scripts.portfolio_scale_grid_scan import parse_source_scales, render, scale_balance_thresholds, scan_grid


def write_csv(path, rows: list[dict[str, str]]) -> None:
    fields = ["time", "pnl_proxy", "signal_type", "dir", "hour"]
    path.write_text(
        ",".join(fields)
        + "\n"
        + "\n".join(",".join(row.get(field, "") for field in fields) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def test_scale_grid_finds_lowest_passing_exposure(tmp_path):
    r1 = tmp_path / "r1.trades.csv"
    r2 = tmp_path / "r2.trades.csv"
    write_csv(
        r1,
        [
            {"time": "2026-03-01 00:00:00", "pnl_proxy": "100", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    write_csv(
        r2,
        [
            {"time": "2026-04-01 00:00:00", "pnl_proxy": "100", "signal_type": "ob", "dir": "buy", "hour": "0"},
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
      profit_min: 90
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

    rows = scan_grid(cfg, "demo", [0, 0.5, 1.0], min_active_legs=1, top=5)
    report = render("demo", rows)

    assert rows[0].total_scale == 1.0
    assert rows[0].total_profit == 100.0
    assert "R1=0.5,R2=0.5" in report


def test_parse_source_scales_overrides_one_source():
    assert parse_source_scales(["R225=0.75,1", "R216M=0.25,0.5"]) == {
        "R225": [0.75, 1.0],
        "R216M": [0.25, 0.5],
    }


def test_scale_grid_can_include_failed_rows(tmp_path):
    r1 = tmp_path / "r1.trades.csv"
    write_csv(
        r1,
        [
            {"time": "2026-03-01 00:00:00", "pnl_proxy": "1", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    cfg = tmp_path / "portfolio.yaml"
    cfg.write_text(
        f"""
schedules:
  demo:
    deposit: 200
    days: 1
    targets:
      profit_min: 90
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

    assert scan_grid(cfg, "demo", [1.0], include_failed=True)[0].passed is False


def test_scale_balance_thresholds_updates_guards_and_filters():
    schedule = {
        "guards": {
            "guard_max_month_start_balance": 1000.0,
            "guard2_min_month_start_balance": 100.0,
        },
        "drop_filters": [
            "monthnum=3;signal=sweep;min_start=100000;max_start=200000;hour=0",
        ],
    }

    scaled = scale_balance_thresholds(schedule, 0.25)

    assert scaled["guards"]["guard_max_month_start_balance"] == 250.0
    assert scaled["guards"]["guard2_min_month_start_balance"] == 25.0
    assert scaled["drop_filters"] == [
        "monthnum=3;signal=sweep;min_start=25000;max_start=50000;hour=0",
    ]
