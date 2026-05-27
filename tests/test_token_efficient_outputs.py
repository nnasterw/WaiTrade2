"""低 token 输出接口测试。"""
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

import monthly_start_matrix
import backtest_digest


SAMPLE_REPORT = """=====================================================================
MT5 Strategy Tester 回测报告 — SAMPLE
日期: 2025.01.01 ~ 2025.01.31 (30天) | 资金: $200.0 | 杠杆: 1:2000
=====================================================================

品种         交易  日均  胜率   盈亏比  净R     余额
---------------------------------------------------------------------
XAUUSDm      18    0.6   61.1   %3.75    N/A     $308.19
---------------------------------------------------------------------
合计          18    0.6   61.1   %        N/A     $308.19
=====================================================================
"""


def test_monthly_start_matrix_brief_summarizes_without_large_tables(tmp_path, monkeypatch, capsys):
    report = tmp_path / 'good_20250101_20250131_20260526.txt'
    report.write_text(SAMPLE_REPORT, encoding='utf-8')
    monkeypatch.setattr(monthly_start_matrix, 'RESULTS_DIR', tmp_path)
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'monthly_start_matrix.py',
            '--start', '2025.01',
            '--end', '2025.02',
            '--target-balance', '270',
            '--brief',
            '--leg', 'good:XAUUSDm:good',
            '--leg', 'missing:XAUUSDm:missing',
        ],
    )

    monthly_start_matrix.main()

    output = capsys.readouterr().out
    assert 'SUMMARY months=2 pass=1 fail=1 missing_reports=3' in output
    assert 'FAIL 2025-02 MISSING' in output
    assert '| 月份 |' not in output
    assert '缺失回测:' not in output


def test_backtest_digest_brief_writes_short_metric_summary(tmp_path):
    report = tmp_path / 'sample_20250101_20250131_20260526.txt'
    output = tmp_path / 'sample.md'
    report.write_text(SAMPLE_REPORT, encoding='utf-8')

    result = backtest_digest.generate_backtest_digest(
        report_path=report,
        output_path=output,
        brief=True,
    )

    markdown = output.read_text(encoding='utf-8')
    assert result['output_path'] == output
    assert '# 回测 Brief' in markdown
    assert '| XAUUSDm | 18 | 0.6 | 61.1% | 3.75 | $308.19 |' in markdown
    assert '日志来源: 未匹配逐单日志' in markdown
    assert len(markdown.splitlines()) <= 16


def test_backtest_ledger_build_writes_one_json_record_per_symbol(tmp_path):
    import json
    import backtest_ledger

    reports_dir = tmp_path / 'reports'
    reports_dir.mkdir()
    report = reports_dir / 'good_20250101_20250131_20260526.txt'
    output = tmp_path / 'ledger.jsonl'
    report.write_text(SAMPLE_REPORT, encoding='utf-8')

    count = backtest_ledger.build_ledger(reports_dir, output)

    records = [json.loads(line) for line in output.read_text(encoding='utf-8').splitlines()]
    assert count == 1
    assert records == [
        {
            'strategy': 'good',
            'strategy_name': 'SAMPLE',
            'symbol': 'XAUUSDm',
            'date_from': '2025.01.01',
            'date_to': '2025.01.31',
            'days': 30,
            'deposit': 200.0,
            'trades': 18,
            'daily_trades': 0.6,
            'win_rate': 61.1,
            'profit_factor': 3.75,
            'net_r': None,
            'final_balance': 308.19,
            'report_path': str(report),
        }
    ]


def test_backtest_ledger_query_monthly_brief_reports_only_failures(tmp_path, capsys):
    import backtest_ledger

    reports_dir = tmp_path / 'reports'
    reports_dir.mkdir()
    (reports_dir / 'good_20250101_20250131_20260526.txt').write_text(SAMPLE_REPORT, encoding='utf-8')
    ledger = tmp_path / 'ledger.jsonl'
    backtest_ledger.build_ledger(reports_dir, ledger)

    records = backtest_ledger.load_ledger(ledger)
    rows, missing = backtest_ledger.query_monthly(
        records=records,
        legs=[backtest_ledger.parse_leg('good:XAUUSDm:good')],
        start_month=backtest_ledger.parse_month('2025.01'),
        end_month=backtest_ledger.parse_month('2025.02'),
        target_balance=270,
    )
    backtest_ledger.emit_monthly_brief(rows, missing)

    output = capsys.readouterr().out
    assert output.splitlines() == [
        'SUMMARY months=2 pass=1 fail=1 missing_records=1',
        'FAIL 2025-02 MISSING window=2025.02.01~2025.03.03 days=30',
    ]


def test_backtest_ledger_selected_outputs_one_line_per_month(tmp_path, capsys):
    import backtest_ledger

    reports_dir = tmp_path / 'reports'
    reports_dir.mkdir()
    (reports_dir / 'good_20250101_20250131_20260526.txt').write_text(SAMPLE_REPORT, encoding='utf-8')
    ledger = tmp_path / 'ledger.jsonl'
    backtest_ledger.build_ledger(reports_dir, ledger)

    records = backtest_ledger.load_ledger(ledger)
    rows, missing = backtest_ledger.query_monthly(
        records=records,
        legs=[backtest_ledger.parse_leg('good:XAUUSDm:good')],
        start_month=backtest_ledger.parse_month('2025.01'),
        end_month=backtest_ledger.parse_month('2025.02'),
        target_balance=270,
    )
    backtest_ledger.emit_monthly_selected(rows, missing)

    output = capsys.readouterr().out
    assert output.splitlines() == [
        'SUMMARY months=2 pass=1 fail=1 missing_records=1',
        'PASS 2025-01 best=good/XAUUSDm/good balance=$308.19 trades=18 daily=0.6 wr=61.1% pf=3.75 window=2025.01.01~2025.01.31',
        'MONTH 2025-02 MISSING window=2025.02.01~2025.03.03 days=30',
    ]


def test_trade_cluster_summary_outputs_top_buckets_without_rows(tmp_path, capsys):
    import trade_cluster_summary

    csv_path = tmp_path / 'trades.csv'
    csv_path.write_text(
        'ticket,hour,dir,exit_signal,reason,r\n'
        '1,14,buy,tp,,2.5\n'
        '2,14,sell,tp,,1.5\n'
        '3,10,buy,sl,, -1.0\n'
        '4,10,sell,sl,, -1.2\n',
        encoding='utf-8',
    )

    trade_cluster_summary.main(['--csv', str(csv_path), '--top', '1'])

    output = capsys.readouterr().out
    assert output.splitlines() == [
        'SUMMARY trades=4 total_r=1.80 win_rate=50.0%',
        'POS hour=14 count=2 total_r=4.00 win_rate=100.0%',
        'NEG hour=10 count=2 total_r=-2.20 win_rate=0.0%',
        'EXIT tp count=2 total_r=4.00 win_rate=100.0%',
        'EXIT sl count=2 total_r=-2.20 win_rate=0.0%',
    ]


def test_mt5_cli_brief_lines_are_one_per_symbol():
    import mt5_cli_backtest

    lines = mt5_cli_backtest.format_brief_report_lines(
        strategy_name='demo',
        symbol_results={
            'XAUUSDm': {
                'trades': 18,
                'daily_trades': 0.6,
                'win_rate': 61.1,
                'profit_factor': 3.75,
                'final_balance': 308.19,
            },
            'BTCUSDm': None,
        },
        report_path=Path('/tmp/demo.txt'),
    )

    assert lines == [
        'BRIEF strategy=demo symbol=XAUUSDm trades=18 daily=0.6 wr=61.1% pf=3.75 balance=$308.19 report=/tmp/demo.txt',
        'BRIEF strategy=demo symbol=BTCUSDm status=parse_failed report=/tmp/demo.txt',
    ]


def test_generated_backtest_artifacts_are_gitignored():
    root = Path(__file__).resolve().parent.parent
    candidates = [
        'results/backtest/generated_20250101_20250131_20990101.txt',
        'results/backtest/generated_20250101_20250131_20990101.md',
        'results/backtest/generated_20250101_20250131_20990101.trades.csv',
        'temp/generated_backtest.log',
    ]

    result = subprocess.run(
        ['git', 'check-ignore', *candidates],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert set(result.stdout.splitlines()) == set(candidates)
