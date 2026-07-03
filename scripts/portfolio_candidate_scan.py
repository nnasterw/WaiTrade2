#!/usr/bin/env python3
"""Rank candidate trade CSVs while guarding against partial-window artifacts."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from portfolio_monthly_scan import DEFAULT_MONTHS


@dataclass(frozen=True)
class CandidateRow:
    name: str
    path: Path
    total_pnl: float
    total_trades: int
    covered_months: int
    bad_months: int
    focus_pnl: float
    focus_trades: int
    weakest_month: str
    weakest_pnl: float

    @property
    def daily_trades(self) -> float:
        return self.total_trades / 720.0


def load_candidate(path: Path, months: list[str], focus_month: str) -> CandidateRow | None:
    pnl_by_month = {month: 0.0 for month in months}
    trades_by_month = {month: 0 for month in months}
    total_pnl = 0.0
    total_trades = 0
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "pnl_proxy" not in reader.fieldnames:
            return None
        for row in reader:
            month = (row.get("time") or row.get("date") or "")[:7]
            if month not in pnl_by_month:
                continue
            pnl = float(row.get("pnl_proxy") or 0.0)
            pnl_by_month[month] += pnl
            trades_by_month[month] += 1
            total_pnl += pnl
            total_trades += 1

    if total_trades == 0:
        return None
    covered = [month for month in months if trades_by_month[month] > 0]
    bad = [month for month in covered if pnl_by_month[month] < 0]
    weakest = min(covered, key=lambda month: pnl_by_month[month])
    return CandidateRow(
        name=path.name,
        path=path,
        total_pnl=total_pnl,
        total_trades=total_trades,
        covered_months=len(covered),
        bad_months=len(bad),
        focus_pnl=pnl_by_month.get(focus_month, 0.0),
        focus_trades=trades_by_month.get(focus_month, 0),
        weakest_month=weakest,
        weakest_pnl=pnl_by_month[weakest],
    )


def scan_candidates(
    patterns: list[str],
    focus_month: str,
    min_covered_months: int,
    months: list[str],
) -> list[CandidateRow]:
    rows: list[CandidateRow] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for path in Path().glob(pattern):
            resolved = path.resolve()
            if resolved in seen or not path.is_file():
                continue
            seen.add(resolved)
            item = load_candidate(path, months, focus_month)
            if item and item.covered_months >= min_covered_months:
                rows.append(item)
    rows.sort(
        key=lambda item: (
            -item.focus_pnl,
            item.bad_months,
            -item.total_pnl,
            -item.daily_trades,
            item.name,
        )
    )
    return rows


def render(rows: list[CandidateRow], top: int) -> str:
    lines = [
        "# Portfolio candidate scan",
        "",
        "| candidate | covered | bad | total | daily | focus_pnl | focus_trades | weakest |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows[:top]:
        lines.append(
            f"| {row.name} | {row.covered_months} | {row.bad_months} | "
            f"{row.total_pnl:.2f} | {row.daily_trades:.2f} | "
            f"{row.focus_pnl:.2f} | {row.focus_trades} | "
            f"{row.weakest_month}:{row.weakest_pnl:.2f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan candidate trade CSVs with coverage filters.")
    parser.add_argument("--candidate-glob", action="append", required=True)
    parser.add_argument("--focus-month", default="2026-03")
    parser.add_argument("--months", default=",".join(DEFAULT_MONTHS))
    parser.add_argument("--min-covered-months", type=int, default=20)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    months = [part.strip() for part in args.months.split(",") if part.strip()]
    rows = scan_candidates(args.candidate_glob, args.focus_month, args.min_covered_months, months)
    report = render(rows, args.top)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
