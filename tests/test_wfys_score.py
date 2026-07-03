import csv
import sys
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
    profits = [
        40, 44, 38, 40, 39, 41, 43, 45,
        120, 38, 39, 40, 42, 36, -10, 48,
        44, 140, 39, 38, 41, -5, 180, -8,
    ]
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['month', 'from', 'to', 'net', 'balance', 'trades', 'wins', 'losses', 'wr', 'pf', 'report'])
        year = 2024
        month = 6
        for profit in profits:
            month_key = '%04d-%02d' % (year, month)
            writer.writerow([
                month_key,
                '%04d.%02d.01' % (year, month),
                '%04d.%02d.28' % (year, month),
                profit,
                200 + profit,
                20,
                12,
                8,
                60.0,
                2.0,
                'dummy.htm',
            ])
            month += 1
            if month > 12:
                month = 1
                year += 1


def _write_report(path):
    symbol_results = {
        'XAUUSDm': {
            'trades': 12,
            'daily_trades': 12.0 / 730.0,
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
    rows = [
        ('2024-06-10 01:00:00', 20.0, 2.0),
        ('2024-07-12 01:00:00', 25.0, 4.2),
        ('2024-08-15 01:00:00', -8.0, -1.0),
        ('2024-09-09 01:00:00', 18.0, 3.2),
        ('2024-11-02 01:00:00', 22.0, 2.2),
        ('2025-01-18 01:00:00', 30.0, 5.0),
        ('2025-03-06 01:00:00', -6.0, -0.8),
        ('2025-05-22 01:00:00', 24.0, 3.8),
        ('2025-08-14 01:00:00', 28.0, 4.1),
        ('2025-10-12 01:00:00', 18.0, 1.2),
        ('2026-02-11 01:00:00', 26.0, 3.5),
        ('2026-05-18 01:00:00', 34.0, 4.8),
    ]
    with path.open('w', encoding='utf-8', newline='') as f:
        if with_r:
            writer = csv.DictWriter(f, fieldnames=['close_time', 'r', 'pnl_proxy'])
        else:
            writer = csv.DictWriter(f, fieldnames=['exit_time', 'pnl'])
        writer.writeheader()
        for close_time, pnl, r_value in rows:
            if with_r:
                writer.writerow({'close_time': close_time, 'r': r_value, 'pnl_proxy': pnl})
            else:
                writer.writerow({'exit_time': close_time, 'pnl': pnl})


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
