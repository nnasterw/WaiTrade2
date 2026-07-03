from __future__ import annotations

from pathlib import Path

from scripts.portfolio_candidate_scan import scan_candidates


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["time", "pnl_proxy", "signal_type", "dir", "hour"]
    path.write_text(
        ",".join(fields)
        + "\n"
        + "\n".join(",".join(row.get(field, "") for field in fields) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def test_candidate_scan_filters_partial_window_artifacts(tmp_path, monkeypatch):
    partial = tmp_path / "partial.trades.csv"
    full = tmp_path / "full.trades.csv"
    write_csv(
        partial,
        [
            {"time": "2026-03-01 00:00:00", "pnl_proxy": "100", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    write_csv(
        full,
        [
            {"time": "2026-02-01 00:00:00", "pnl_proxy": "1", "signal_type": "ob", "dir": "buy", "hour": "0"},
            {"time": "2026-03-01 00:00:00", "pnl_proxy": "2", "signal_type": "ob", "dir": "buy", "hour": "0"},
        ],
    )
    monkeypatch.chdir(tmp_path)

    rows = scan_candidates(["*.trades.csv"], "2026-03", min_covered_months=2, months=["2026-02", "2026-03"])

    assert [row.name for row in rows] == ["full.trades.csv"]
    assert rows[0].focus_pnl == 2
    assert rows[0].covered_months == 2
