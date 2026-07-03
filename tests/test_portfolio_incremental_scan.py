from __future__ import annotations

from pathlib import Path

from scripts.portfolio_incremental_scan import scan_incremental


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["time", "pnl_proxy", "signal_type", "dir", "hour"]
    path.write_text(
        ",".join(fields)
        + "\n"
        + "\n".join(",".join(row.get(field, "") for field in fields) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def write_schedule(path: Path, base_csv: Path) -> None:
    path.write_text(
        f"""
schedules:
  demo:
    deposit: 200
    days: 10
    targets:
      profit_min: 0
      daily_trades_min: 0
      require_non_negative_months: true
      monthly_profit_min: 0.01
    series:
      - name: BASE
        path: {base_csv.as_posix()}
    guards: {{}}
""",
        encoding="utf-8",
    )


def test_incremental_scan_ranks_candidate_by_combined_path(tmp_path, monkeypatch):
    base = tmp_path / "base.trades.csv"
    good = tmp_path / "good.trades.csv"
    bad_month = tmp_path / "bad_month.trades.csv"
    schedule = tmp_path / "portfolio.yaml"
    write_csv(
        base,
        [
            {"time": "2026-01-01 00:00:00", "pnl_proxy": "5", "signal_type": "ob", "dir": "buy", "hour": "0"},
            {"time": "2026-02-01 00:00:00", "pnl_proxy": "5", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    write_csv(
        good,
        [
            {"time": "2026-01-01 00:01:00", "pnl_proxy": "2", "signal_type": "sweep", "dir": "buy", "hour": "0"},
            {"time": "2026-02-01 00:01:00", "pnl_proxy": "3", "signal_type": "sweep", "dir": "buy", "hour": "0"},
        ],
    )
    write_csv(
        bad_month,
        [
            {"time": "2026-01-01 00:01:00", "pnl_proxy": "100", "signal_type": "sweep", "dir": "buy", "hour": "0"},
            {"time": "2026-02-01 00:01:00", "pnl_proxy": "-10", "signal_type": "sweep", "dir": "buy", "hour": "0"},
        ],
    )
    write_schedule(schedule, base)
    monkeypatch.chdir(tmp_path)

    rows, base_row = scan_incremental(schedule, "demo", ["*.trades.csv"], top=10)

    assert base_row.total_profit == 10
    assert [row.name for row in rows] == ["good.trades.csv", "bad_month.trades.csv"]
    assert rows[0].profit_delta == 5
    assert rows[0].pass_targets is True
    assert rows[0].covered_months == 2
    assert rows[0].candidate_trades == 2
    assert rows[0].overlap_ratio == 0
    assert rows[1].profit_delta == 90


def test_incremental_scan_excludes_existing_schedule_series(tmp_path, monkeypatch):
    base = tmp_path / "base.trades.csv"
    schedule = tmp_path / "portfolio.yaml"
    write_csv(
        base,
        [
            {"time": "2026-01-01 00:00:00", "pnl_proxy": "5", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    write_schedule(schedule, base)
    monkeypatch.chdir(tmp_path)

    rows, _ = scan_incremental(schedule, "demo", ["*.trades.csv"], top=10)

    assert rows == []


def test_incremental_scan_reports_candidate_overlap(tmp_path, monkeypatch):
    base = tmp_path / "base.trades.csv"
    overlap = tmp_path / "overlap.trades.csv"
    schedule = tmp_path / "portfolio.yaml"
    row = {"time": "2026-01-01 00:00:00", "pnl_proxy": "5", "signal_type": "ob", "dir": "buy", "hour": "0"}
    write_csv(base, [row])
    write_csv(overlap, [row, {"time": "2026-01-02 00:00:00", "pnl_proxy": "2", "signal_type": "ob", "dir": "buy", "hour": "0"}])
    write_schedule(schedule, base)
    monkeypatch.chdir(tmp_path)

    rows, _ = scan_incremental(schedule, "demo", ["*.trades.csv"], top=10)

    assert rows[0].name == "overlap.trades.csv"
    assert rows[0].overlap_ratio == 0.5


def test_incremental_scan_can_filter_coverage_and_overlap(tmp_path, monkeypatch):
    base = tmp_path / "base.trades.csv"
    partial = tmp_path / "partial.trades.csv"
    overlap = tmp_path / "overlap.trades.csv"
    schedule = tmp_path / "portfolio.yaml"
    base_row = {"time": "2026-01-01 00:00:00", "pnl_proxy": "5", "signal_type": "ob", "dir": "buy", "hour": "0"}
    write_csv(base, [base_row])
    write_csv(
        partial,
        [{"time": "2026-01-02 00:00:00", "pnl_proxy": "2", "signal_type": "ob", "dir": "buy", "hour": "0"}],
    )
    write_csv(
        overlap,
        [
            base_row,
            {"time": "2026-02-01 00:00:00", "pnl_proxy": "2", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    write_schedule(schedule, base)
    monkeypatch.chdir(tmp_path)

    rows, _ = scan_incremental(
        schedule,
        "demo",
        ["*.trades.csv"],
        top=10,
        min_covered_months=2,
        max_overlap=0.25,
    )

    assert rows == []
