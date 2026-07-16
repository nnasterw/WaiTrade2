import csv
import collections
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

from mt5_common import format_report
from wfys_score import (
    build_result,
    infer_monthly_deposit,
    load_monthly_rows,
    load_report_meta,
    load_trades,
)


def _write_monthly_csv(path):
    # Hand-rolled monthly profits mapped to v2.0 WFYS semantics:
    # - 24/24 profitable months
    # - 6 strong months (> 0.25 return), 2 trend months (> 0.55 return)
    # Return-on-month is implicit: profit / running_balance => Sharpe.
    monthly_profits = [
        # (year, month, profit)
        (2024, 6, 130.0),  # ~ +65% return (trend)
        (2024, 7, 80.0),   # ~ +24%
        (2024, 8, 90.0),
        (2024, 9, 130.0),  # ~ +23%
        (2024, 10, 95.0),
        (2024, 11, 78.0),  # (monthly return ~ +12%)
        (2024, 12, 110.0),
        (2025, 1, 86.0),
        (2025, 2, 280.0),  # ~ +33% return (strong & near-trend)
        (2025, 3, 150.0),  # ~ +13%
        (2025, 4, 120.0),
        (2025, 5, 90.0),
        (2025, 6, 520.0),  # ~ +44% return (strong)
        (2025, 7, 180.0),  # ~ +11%
        (2025, 8, 220.0),
        (2025, 9, 800.0),  # ~ +46% return (strong)
        (2025, 10, 280.0),  # ~ +12%
        (2025, 11, 380.0),
        (2025, 12, 1500.0),  # ~ +56% return (trend)
        (2026, 1, 650.0),   # ~ +18%
        (2026, 2, 720.0),
        (2026, 3, 560.0),
        (2026, 4, 1200.0),  # ~ +27% return (strong)
        (2026, 5, 1180.0),
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "from", "to", "net", "balance", "trades", "wins", "losses", "wr", "pf", "report"])
        running = 200.0
        for (year, month, profit) in monthly_profits:
            month_key = "%04d-%02d" % (year, month)
            writer.writerow([
                month_key, "%04d.%02d.01" % (year, month), "%04d.%02d.28" % (year, month),
                profit, running + profit, 9, 7, 2, 78.0, 3.0, "dummy.htm",
            ])
            running += profit


def _write_report(path):
    symbol_results = {
        'XAUUSDm': {
            'trades': 220,
            'daily_trades': 220.0 / 730.0,
            'win_rate': 83.3,
            'profit_factor': 5.0,
            'final_balance': 431.0,
            'net_r': None,
            'wins': 10,
            'losses': 2,
        }
    }
    content = format_report(
        'wfys-test',
        '2024.06.01',
        '2026.05.31',
        730,
        200,
        '2000',
        symbol_results,
        model='4',
    )
    path.write_text(content, encoding='utf-8')


def _write_detailed_trades(path, with_r=True):
    """Generate 220 trades; per-month distribution fixed so monthly returns are stable."""
    rows = []
    base = datetime(2024, 6, 10, 1, 0, 0)
    # 24 months x 9 = 216 baseline trades; pad to 220 with mid winners.
    monthly_buckets = [
        (4.0, 0.35),
        (1.5, 0.45),
        (-0.6, 0.20),
    ]
    trades_per_month = 9
    months_total = 24
    trades_total = trades_per_month * months_total  # 216

    def _month_trades(month_offset, balance):
        # Build 9 trades that sum approximately to 14% monthly return on `balance`.
        # Use 3 big winners, 4 mid winners, 2 small losers.
        rows_local = [
            (4.0, 0.5),  # big
            (4.0, 0.4),
            (4.0, 0.3),
            (1.5, 0.5),
            (1.5, 0.5),
            (1.5, 0.6),
            (1.5, 0.7),
            (-0.5, 0.5),
            (-0.5, 0.5),
        ]
        return rows_local

    idx = 0
    target_balance = 200.0
    for month in range(months_total):
        ts = base + timedelta(days=month * 30)
        local = _month_trades(month, target_balance)
        # Normalize so net is positive; scale based on average r * balance contribution.
        for (r_value, weight) in local:
            t = ts + timedelta(hours=idx % 24, minutes=(idx * 13) % 60)
            jitter = ((idx * 19 + 3) % 11) / 10.0 - 0.5
            actual_r = r_value * (1.0 + jitter * 0.10)
            pnl = actual_r * 4.0
            rows.append((t.strftime("%Y-%m-%d %H:%M:%S"), pnl, actual_r))
            target_balance += pnl
            idx += 1
    # Pad to 220 with neutrals
    while idx < 220:
        t = base + timedelta(days=idx)
        rows.append((t.strftime("%Y-%m-%d %H:%M:%S"), 30.0, 7.5))
        idx += 1
    with path.open("w", encoding="utf-8", newline="") as f:
        if with_r:
            writer = csv.DictWriter(f, fieldnames=["close_time", "r", "pnl_proxy"])
        else:
            writer = csv.DictWriter(f, fieldnames=["exit_time", "pnl"])
        writer.writeheader()
        for close_time, pnl, r_value in rows:
            if with_r:
                writer.writerow({"close_time": close_time, "r": r_value, "pnl_proxy": pnl})
            else:
                writer.writerow({"exit_time": close_time, "pnl": pnl})


def test_wfys_full_result_passes_hard_gates(tmp_path):
    monthly_csv = tmp_path / '24m.csv'
    report_txt = tmp_path / '720d.txt'
    trades_csv = tmp_path / '720d.trades.csv'

    _write_monthly_csv(monthly_csv)
    _write_report(report_txt)
    _write_detailed_trades(trades_csv, with_r=True)

    rows = load_monthly_rows(monthly_csv, None)
    deposit = infer_monthly_deposit(rows)
    report = load_report_meta(report_txt)
    trades = load_trades(trades_csv)
    result = build_result(rows, report, trades, deposit, 'default')

    assert deposit == 200
    assert result['hard_failures'] == []
    assert result['hard_gates']['24月盈利月数'] is True
    assert result['hard_gates']['>3R大赢单占比'] is True
    assert result['grade'] in ('继续研究', '观察级候选', '研究版Live候选', '优先部署级候选')


def test_wfys_missing_r_metrics_fails_structural_gate(tmp_path):
    monthly_csv = tmp_path / '24m.csv'
    report_txt = tmp_path / '720d.txt'
    trades_csv = tmp_path / '720d_simple.csv'

    _write_monthly_csv(monthly_csv)
    _write_report(report_txt)
    _write_detailed_trades(trades_csv, with_r=False)

    rows = load_monthly_rows(monthly_csv, None)
    deposit = infer_monthly_deposit(rows)
    report = load_report_meta(report_txt)
    trades = load_trades(trades_csv)
    result = build_result(rows, report, trades, deposit, 'default')

    assert any('缺少R倍数列' in reason for reason in result['hard_failures'])
    assert result['hard_gates']['>3R大赢单占比'] is False
    assert result['grade'] == '淘汰'
