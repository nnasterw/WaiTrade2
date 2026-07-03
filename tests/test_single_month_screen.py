from __future__ import annotations

import argparse
from pathlib import Path

from scripts.single_month_screen import (
    MonthRow,
    format_command,
    infer_strategy,
    load_month_rows,
    parse_report,
)


def test_parse_report_reads_clean_chinese_report(tmp_path):
    report = tmp_path / "report.txt"
    report.write_text(
        """
日期: 2024.06.01 ~ 2026.05.25 (720天) | 资金: $200 | 杠杆: 1:2000
BTCUSDm      10    0.3   60.0%  1.20    +3.0    $231.50
合计          10    0.3   60.0%          +3.0    $231.50
""",
        encoding="utf-8",
    )

    assert parse_report(report) == (200.0, 231.50)


def test_parse_report_reads_existing_mojibake_report(tmp_path):
    report = tmp_path / "report.txt"
    report.write_text(
        """
鏃ユ湡: 2024.06.01 ~ 2026.05.25 (720澶? | 璧勯噾: $200 | 鏉犳潌: 1:2000
鍚堣      10    0.3   60.0%          +3.0    $231.50
""",
        encoding="utf-8",
    )

    assert parse_report(report) == (200.0, 231.50)


def test_load_month_rows_uses_full_window_month_start_balance(tmp_path):
    trades = tmp_path / "demo_20240601_20240801_20260525.trades.csv"
    trades.write_text(
        "\ufeffdate,pnl_proxy\n"
        "2024-06-03,10\n"
        "2024-06-04,-5\n"
        "2024-07-01,-15\n",
        encoding="utf-8",
    )

    rows = load_month_rows(trades, deposit=200.0, final_balance=180.0)

    assert [(row.month, row.trades) for row in rows] == [("2024-06", 2), ("2024-07", 1)]
    assert rows[0].start_balance == 200.0
    assert rows[0].end_balance == 210.0
    assert rows[1].start_balance == 210.0
    assert rows[1].end_balance == 180.0


def test_format_command_includes_month_window_and_start_balance():
    args = argparse.Namespace(
        runner=r"scripts\mt5_backtest_win.py",
        symbol="BTCUSDm",
        timeout=1200,
    )
    row = MonthRow(
        month="2024-11",
        trades=4,
        pnl_proxy=-2.0,
        profit=-12.0,
        start_balance=507.58,
        end_balance=495.58,
    )

    assert format_command(args, row, "v_candidate") == (
        r"python scripts\mt5_backtest_win.py --strategy v_candidate --symbol BTCUSDm "
        "--from 2024.11.01 --to 2024.12.01 --deposit 507.58 --timeout 1200"
    )


def test_infer_strategy_strips_full_window_suffix():
    assert (
        infer_strategy(Path("results/backtest/v11_r209_demo_20240604_20260525_20260525.trades.csv"))
        == "v11_r209_demo"
    )
