"""低 token 输出接口测试。"""
import sys
import subprocess
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

import monthly_start_matrix
import backtest_digest
import xau_dual_selector_eval
import xau_trend_cluster_contrast
import xau_trend_variant_matrix
import xau_backtest_queue
import xau_goal_audit
import xau_ingest_reports


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
            'model': None,
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


def _write_selector_record(tmp_path, strategy, month, balance, trades, daily=1.0, win_rate=50.0, pf=1.2):
    report = tmp_path / f'{strategy}_{month}_20260601.txt'
    report.write_text('placeholder', encoding='utf-8')
    date_from, date_to, days = xau_dual_selector_eval.window_for_month(
        xau_dual_selector_eval.parse_month(f'{month[:4]}.{month[4:]}'),
        available_to=None,
    )
    return {
        'strategy': strategy,
        'strategy_name': strategy,
        'symbol': 'XAUUSDm',
        'date_from': date_from.strftime('%Y.%m.%d'),
        'date_to': date_to.strftime('%Y.%m.%d'),
        'days': days,
        'deposit': 200.0,
        'trades': trades,
        'daily_trades': daily,
        'win_rate': win_rate,
        'profit_factor': pf,
        'net_r': None,
        'final_balance': balance,
        'report_path': str(report),
    }


def _write_trades_csv(report_path, rows):
    csv_path = Path(report_path).with_suffix('.trades.csv')
    csv_path.write_text(
        'ticket,time,exit_signal,r\n'
        + ''.join(f'{ticket},{time},{exit_signal},{r}\n' for ticket, time, exit_signal, r in rows),
        encoding='utf-8',
    )


def test_xau_dual_selector_feedback_uses_probe_window(tmp_path):
    record = _write_selector_record(tmp_path, 'trend', '202501', balance=500, trades=4)
    _write_trades_csv(
        record['report_path'],
        [
            (1, '2025-01-01 01:00:00', 'sl', -1.0),
            (2, '2025-01-02 01:00:00', 'tp', 2.5),
            (3, '2025-01-05 23:00:00', 'sl', -1.0),
            (4, '2025-01-06 00:00:00', 'tp', 5.0),
        ],
    )

    feedback = xau_dual_selector_eval.first_days_feedback(record, probe_days=5)

    assert feedback.trades == 3
    assert feedback.net_r == 0.5
    assert round(feedback.win_rate, 1) == 33.3
    assert round(feedback.sl_pct, 1) == 66.7


def test_xau_dual_selector_picks_trend_only_when_probe_is_healthy(tmp_path):
    records = [
        _write_selector_record(tmp_path, 'range', '202501', balance=310, trades=10),
        _write_selector_record(tmp_path, 'trend', '202501', balance=900, trades=120),
        _write_selector_record(tmp_path, 'range', '202502', balance=330, trades=10),
        _write_selector_record(tmp_path, 'trend', '202502', balance=120, trades=120),
    ]
    _write_trades_csv(records[0]['report_path'], [(1, '2025-01-01 01:00:00', 'sl', -1.0)])
    _write_trades_csv(records[1]['report_path'], [(i, f'2025-01-01 {i % 24:02d}:00:00', 'tp', 1.0) for i in range(1, 26)])
    _write_trades_csv(records[2]['report_path'], [(1, '2025-02-01 01:00:00', 'sl', -1.0)])
    _write_trades_csv(records[3]['report_path'], [(i, f'2025-02-01 {i % 24:02d}:00:00', 'sl', -1.0) for i in range(1, 26)])

    rows, missing = xau_dual_selector_eval.evaluate_selector(
        records=records,
        symbol='XAUUSDm',
        range_strategy='range',
        trend_strategy='trend',
        start_month=xau_dual_selector_eval.parse_month('2025.01'),
        end_month=xau_dual_selector_eval.parse_month('2025.02'),
        target_balance=270,
        rule=xau_dual_selector_eval.SelectorRule(),
    )

    assert missing == 0
    assert [row['selected'] for row in rows] == ['trend', 'range']
    assert [row['record']['final_balance'] for row in rows] == [900, 330]


def test_xau_dual_selector_default_does_not_block_healthy_trend_when_range_starts_well(tmp_path):
    records = [
        _write_selector_record(tmp_path, 'range', '202501', balance=330, trades=10),
        _write_selector_record(tmp_path, 'trend', '202501', balance=900, trades=120),
    ]
    _write_trades_csv(records[0]['report_path'], [(i, f'2025-01-01 {i % 24:02d}:00:00', 'tp', 1.0) for i in range(1, 11)])
    _write_trades_csv(records[1]['report_path'], [(i, f'2025-01-01 {i % 24:02d}:00:00', 'tp', 1.0) for i in range(1, 26)])

    rows, missing = xau_dual_selector_eval.evaluate_selector(
        records=records,
        symbol='XAUUSDm',
        range_strategy='range',
        trend_strategy='trend',
        start_month=xau_dual_selector_eval.parse_month('2025.01'),
        end_month=xau_dual_selector_eval.parse_month('2025.01'),
        target_balance=270,
        rule=xau_dual_selector_eval.SelectorRule(),
    )

    assert missing == 0
    assert rows[0]['selected'] == 'trend'
    assert rows[0]['record']['final_balance'] == 900


def test_xau_dual_selector_prefers_required_model_over_higher_unknown_balance(tmp_path):
    unknown = _write_selector_record(tmp_path, 'trend', '202501', balance=900, trades=20)
    model4 = _write_selector_record(tmp_path, 'trend', '202501', balance=300, trades=20)
    model4['model'] = '4'

    selected = xau_dual_selector_eval.best_record(
        [unknown, model4],
        'trend',
        'XAUUSDm',
        xau_dual_selector_eval._parse_day('2025.01.01'),
        xau_dual_selector_eval._parse_day('2025.01.31'),
        preferred_model='4',
    )

    assert selected is model4


def test_xau_dual_selector_brief_reports_summary_and_failures(capsys):
    rows = [
        {
            'month': xau_dual_selector_eval.parse_month('2025.01'),
            'date_from': xau_dual_selector_eval._parse_day('2025.01.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.01.31'),
            'selected': 'range',
            'record': {
                'final_balance': 260.0,
                'trades': 12,
                'daily_trades': 0.4,
                'win_rate': 41.7,
                'profit_factor': 1.3,
            },
            'passed': False,
        }
    ]

    xau_dual_selector_eval.emit_brief(rows, missing_count=0, target_balance=270)

    assert capsys.readouterr().out.splitlines() == [
        'SUMMARY months=1 pass=0 fail=1 missing_records=0 min_balance=$260.00 balance_sum=$260.00 target=$270.00 csv_mismatches=0',
        'FAIL 2025-01 selected=range balance=$260.00 trades=12 daily=0.4 wr=41.7% pf=1.30',
    ]


def test_xau_dual_selector_grid_outputs_compact_top_line(tmp_path, capsys):
    records = [
        _write_selector_record(tmp_path, 'range', '202501', balance=330, trades=10),
        _write_selector_record(tmp_path, 'trend', '202501', balance=900, trades=120),
    ]
    _write_trades_csv(records[0]['report_path'], [(1, '2025-01-01 01:00:00', 'sl', -1.0)])
    _write_trades_csv(records[1]['report_path'], [(i, f'2025-01-01 {i % 24:02d}:00:00', 'tp', 1.0) for i in range(1, 26)])

    xau_dual_selector_eval.emit_grid(
        records,
        SimpleNamespace(
            symbol='XAUUSDm',
            range_strategy='range',
            trend_strategy='trend',
            start='2025.01',
            end='2025.01',
            available_to=None,
            target_balance=270,
            range_max_net_r=999,
            grid_top=1,
        ),
    )

    output = capsys.readouterr().out.strip()
    assert output.startswith('GRID rank=1 pass=1/1 min_balance=$900.00 balance_sum=$900.00')
    assert 'trend_months=1' in output


def test_xau_trend_cluster_contrast_ranks_edge_loss_buckets(monkeypatch):
    rows = [
        {
            'month': xau_dual_selector_eval.parse_month('2025.01'),
            'analysis_record': {
                'final_balance': 300,
                'trades': 2,
                'fixture_trades': [
                    {'hour': '3', 'r': '-1.0'},
                    {'hour': '4', 'r': '2.0'},
                ],
            },
        },
        {
            'month': xau_dual_selector_eval.parse_month('2025.02'),
            'analysis_record': {
                'final_balance': 900,
                'trades': 2,
                'fixture_trades': [
                    {'hour': '3', 'r': '0.5'},
                    {'hour': '4', 'r': '3.0'},
                ],
            },
        },
    ]
    monkeypatch.setattr(
        xau_trend_cluster_contrast,
        'read_trade_rows',
        lambda record: record['fixture_trades'],
    )

    buckets = xau_trend_cluster_contrast.bucket_contrast(
        rows,
        edge_months={'2025-01'},
        strong_months={'2025-02'},
        field='hour',
    )

    assert buckets[0]['key'] == '3'
    assert buckets[0]['edge_r'] == -1.0
    assert buckets[0]['strong_r'] == 0.5


def test_xau_trend_cluster_contrast_supports_numeric_bins(monkeypatch):
    rows = [
        {
            'month': xau_dual_selector_eval.parse_month('2025.01'),
            'analysis_record': {
                'final_balance': 300,
                'trades': 2,
                'fixture_trades': [
                    {'duration_min': '0.4', 'r': '-1.0'},
                    {'duration_min': '1.2', 'r': '2.0'},
                ],
            },
        },
        {
            'month': xau_dual_selector_eval.parse_month('2025.02'),
            'analysis_record': {
                'final_balance': 900,
                'trades': 2,
                'fixture_trades': [
                    {'duration_min': '0.3', 'r': '0.5'},
                    {'duration_min': '4.0', 'r': '3.0'},
                ],
            },
        },
    ]
    monkeypatch.setattr(
        xau_trend_cluster_contrast,
        'read_trade_rows',
        lambda record: record['fixture_trades'],
    )

    buckets = xau_trend_cluster_contrast.bucket_contrast(
        rows,
        edge_months={'2025-01'},
        strong_months={'2025-02'},
        field='duration_min',
        numeric_bins=[0.5, 2.0],
    )

    assert buckets[0]['key'] == '<0.5'
    assert buckets[0]['edge_r'] == -1.0
    assert buckets[0]['strong_r'] == 0.5


def test_xau_trend_variant_matrix_reports_missing_and_commands(tmp_path, monkeypatch, capsys):
    reports_dir = tmp_path / 'reports'
    reports_dir.mkdir()
    (reports_dir / 'v1_20250101_20250131_20260526.txt').write_text(SAMPLE_REPORT, encoding='utf-8')
    (reports_dir / 'v2_20250101_20250131_20260526.txt').write_text(SAMPLE_REPORT, encoding='utf-8')

    selector_rows = [
        {
            'selected': 'trend',
            'month': xau_dual_selector_eval.parse_month('2025.01'),
            'date_from': xau_dual_selector_eval._parse_day('2025.01.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.01.31'),
        },
        {
            'selected': 'trend',
            'month': xau_dual_selector_eval.parse_month('2025.02'),
            'date_from': xau_dual_selector_eval._parse_day('2025.02.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.03.03'),
        },
    ]
    monkeypatch.setattr(xau_trend_variant_matrix, 'trend_month_rows', lambda args: selector_rows)

    xau_trend_variant_matrix.main([
        '--reports-dir', str(reports_dir),
        '--variants', 'v1,v2',
        '--commands',
    ])

    output = capsys.readouterr().out
    assert 'VARIANT v1 tested=1/2 min=$308.19 balance_sum=$308.19' in output
    assert 'MISSING 2025-02' in output
    assert '--strategies v1,v2 --symbol XAUUSDm --from 2025.02.01 --to 2025.03.03' in output


def test_xau_trend_variant_matrix_can_target_range_leg(tmp_path, monkeypatch, capsys):
    reports_dir = tmp_path / 'reports'
    reports_dir.mkdir()
    (reports_dir / 'range_20250101_20250131_20260526.txt').write_text(SAMPLE_REPORT, encoding='utf-8')

    selector_rows = [
        {
            'selected': 'range',
            'month': xau_dual_selector_eval.parse_month('2025.01'),
            'date_from': xau_dual_selector_eval._parse_day('2025.01.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.01.31'),
        },
        {
            'selected': 'trend',
            'month': xau_dual_selector_eval.parse_month('2025.02'),
            'date_from': xau_dual_selector_eval._parse_day('2025.02.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.03.03'),
        },
    ]
    monkeypatch.setattr(xau_trend_variant_matrix, 'selector_rows', lambda args: (selector_rows, 0))

    xau_trend_variant_matrix.main([
        '--reports-dir', str(reports_dir),
        '--leg', 'range',
        '--variants', 'range,range_h15',
        '--commands',
    ])

    output = capsys.readouterr().out
    assert 'VARIANT range tested=1/1 min=$308.19 balance_sum=$308.19' in output
    assert '--strategies range,range_h15 --symbol XAUUSDm --from 2025.01.01 --to 2025.01.31' in output
    assert '2025.02.01' not in output


def test_xau_trend_variant_matrix_sorts_commands_by_selector_balance(tmp_path, monkeypatch, capsys):
    selector_rows = [
        {
            'selected': 'range',
            'month': xau_dual_selector_eval.parse_month('2025.01'),
            'date_from': xau_dual_selector_eval._parse_day('2025.01.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.01.31'),
            'record': {'final_balance': 400},
        },
        {
            'selected': 'range',
            'month': xau_dual_selector_eval.parse_month('2025.02'),
            'date_from': xau_dual_selector_eval._parse_day('2025.02.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.03.03'),
            'record': {'final_balance': 280},
        },
    ]
    monkeypatch.setattr(xau_trend_variant_matrix, 'selector_rows', lambda args: (selector_rows, 0))

    xau_trend_variant_matrix.main([
        '--reports-dir', str(tmp_path),
        '--leg', 'range',
        '--variants', 'range_h15,range_half',
        '--commands',
        '--commands-sort', 'balance',
    ])

    commands = [line for line in capsys.readouterr().out.splitlines() if line.startswith('python3 ')]
    assert '--from 2025.02.01 --to 2025.03.03' in commands[0]
    assert '--from 2025.01.01 --to 2025.01.31' in commands[1]


def test_xau_backtest_queue_prioritizes_range_then_trend(monkeypatch, capsys):
    def fake_variant_matrix(args):
        if args.leg == 'range':
            return [
                {
                    'month': xau_dual_selector_eval.parse_month('2025.01'),
                    'date_from': xau_dual_selector_eval._parse_day('2025.01.01'),
                    'date_to': xau_dual_selector_eval._parse_day('2025.01.31'),
                    'selector_record': {'final_balance': 400},
                    'records': {'range': {'final_balance': 400}, 'range_exp': None},
                },
                {
                    'month': xau_dual_selector_eval.parse_month('2025.02'),
                    'date_from': xau_dual_selector_eval._parse_day('2025.02.01'),
                    'date_to': xau_dual_selector_eval._parse_day('2025.03.03'),
                    'selector_record': {'final_balance': 280},
                    'records': {'range': {'final_balance': 280}, 'range_exp': None},
                },
            ], ['range', 'range_exp']
        return [
            {
                'month': xau_dual_selector_eval.parse_month('2025.03'),
                'date_from': xau_dual_selector_eval._parse_day('2025.03.01'),
                'date_to': xau_dual_selector_eval._parse_day('2025.03.31'),
                'trend_feedback': xau_dual_selector_eval.Feedback(trades=30, net_r=24.0, win_rate=60.0, sl_pct=55.0),
                'records': {'trend': {'final_balance': 900}, 'block': None, 'half': None},
            }
        ], ['trend', 'block', 'half']

    monkeypatch.setattr(xau_backtest_queue, 'variant_matrix', fake_variant_matrix)
    xau_backtest_queue.main([
        '--range-variants', 'range,range_exp',
        '--trend-variants', 'trend,block,half',
        '--commands',
    ])

    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith('QUEUE_ITEM')]
    assert 'rank=1 leg=range phase=range_front month=2025-02 reason=low_balance=$280.00' in lines[0]
    assert 'rank=2 leg=range phase=range_front month=2025-01 reason=low_balance=$400.00' in lines[1]
    assert 'rank=3 leg=trend phase=trend_h04 month=2025-03 reason=h04_delta=1.0R' in lines[2]


def test_xau_backtest_queue_commands_pin_model4(monkeypatch, capsys):
    def fake_variant_matrix(args):
        return [
            {
                'month': xau_dual_selector_eval.parse_month('2025.01'),
                'date_from': xau_dual_selector_eval._parse_day('2025.01.01'),
                'date_to': xau_dual_selector_eval._parse_day('2025.01.31'),
                'selector_record': {'final_balance': 280},
                'records': {'range': {'final_balance': 280}, 'range_exp': None},
            }
        ], ['range', 'range_exp']

    monkeypatch.setattr(xau_backtest_queue, 'variant_matrix', fake_variant_matrix)
    xau_backtest_queue.main([
        '--include', 'range',
        '--range-variants', 'range,range_exp',
        '--commands',
    ])

    output = capsys.readouterr().out
    assert '--background --brief' in output
    assert '--model 4' in output


def test_xau_backtest_queue_moves_range_rest_after_trend(monkeypatch, capsys):
    def fake_variant_matrix(args):
        if args.leg == 'range':
            rows = []
            for idx, balance in enumerate([280, 300, 360], start=1):
                rows.append({
                    'month': xau_dual_selector_eval.parse_month(f'2025.0{idx}'),
                    'date_from': xau_dual_selector_eval._parse_day(f'2025.0{idx}.01'),
                    'date_to': xau_dual_selector_eval._parse_day(f'2025.0{idx}.28'),
                    'selector_record': {'final_balance': balance},
                    'records': {'range': {'final_balance': balance}, 'range_exp': None},
                })
            return rows, ['range', 'range_exp']
        return [
            {
                'month': xau_dual_selector_eval.parse_month('2025.04'),
                'date_from': xau_dual_selector_eval._parse_day('2025.04.01'),
                'date_to': xau_dual_selector_eval._parse_day('2025.04.30'),
                'trend_feedback': xau_dual_selector_eval.Feedback(trades=30, net_r=24.0, win_rate=60.0, sl_pct=55.0),
                'records': {'trend': {'final_balance': 900}, 'block': None, 'half': None},
            }
        ], ['trend', 'block', 'half']

    monkeypatch.setattr(xau_backtest_queue, 'variant_matrix', fake_variant_matrix)
    xau_backtest_queue.main([
        '--range-variants', 'range,range_exp',
        '--trend-variants', 'trend,block,half',
        '--range-front-count', '1',
    ])

    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith('QUEUE_ITEM')]
    assert 'phase=range_front month=2025-01' in lines[0]
    assert 'phase=trend_h04 month=2025-04' in lines[1]
    assert 'phase=range_rest month=2025-02' in lines[2]
    assert 'phase=range_rest month=2025-03' in lines[3]


def test_xau_trend_variant_matrix_commands_pin_model4(tmp_path, monkeypatch, capsys):
    selector_rows = [
        {
            'selected': 'trend',
            'month': xau_dual_selector_eval.parse_month('2025.01'),
            'date_from': xau_dual_selector_eval._parse_day('2025.01.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.01.31'),
        }
    ]
    monkeypatch.setattr(xau_trend_variant_matrix, 'trend_month_rows', lambda args: selector_rows)

    xau_trend_variant_matrix.main([
        '--reports-dir', str(tmp_path),
        '--variants', 'trend,block',
        '--commands',
    ])

    output = capsys.readouterr().out
    assert '--model 4' in output


def test_xau_goal_audit_reports_missing_candidates(monkeypatch, capsys):
    combined_rows = [
        {
            'combined_record': {'final_balance': 300, 'model': '4'},
        },
        {
            'combined_record': {'final_balance': 500, 'model': '4'},
        },
    ]

    def fake_variant_matrix(args):
        if args.leg == 'trend':
            return [
                {
                    'month': xau_dual_selector_eval.parse_month('2025.01'),
                    'records': {'trend': {'final_balance': 300}, 'block': None},
                }
            ], ['trend', 'block']
        return [
            {
                'month': xau_dual_selector_eval.parse_month('2025.02'),
                'records': {'range': {'final_balance': 300}, 'range_exp': None},
            }
        ], ['range', 'range_exp']

    monkeypatch.setattr(xau_goal_audit, 'combined_h04_rows', lambda args: combined_rows)
    monkeypatch.setattr(xau_goal_audit, 'variant_matrix', fake_variant_matrix)
    monkeypatch.setattr(
        xau_goal_audit,
        'queue_items',
        lambda args: [
            {
                'leg': 'range',
                'month': xau_dual_selector_eval.parse_month('2025.02'),
                'reason': 'low_balance=$300.00',
                'command': 'python3 scripts/mt5_cli_backtest.py --background --brief --strategy range_exp',
            }
        ],
    )

    exit_code = xau_goal_audit.main([
        '--trend-variants', 'trend,block',
        '--range-variants', 'range,range_exp',
        '--details',
        '--commands',
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert 'AUDIT status=incomplete reasons=trend_h04_missing,range_candidate_missing months=2 pass=2/2' in output
    assert 'missing_trend_h04=1 missing_range_candidates=1 model_unverified=0 next=range:2025-02:low_balance=$300.00' in output
    assert 'MISSING_TREND_H04 2025-01' in output
    assert 'MISSING_RANGE_CANDIDATES 2025-02' in output
    assert 'NEXT_COMMAND python3 scripts/mt5_cli_backtest.py --background --brief --strategy range_exp' in output


def test_xau_goal_audit_can_fail_on_incomplete(monkeypatch):
    monkeypatch.setattr(
        xau_goal_audit,
        'audit',
        lambda args: {
            'status': 'incomplete',
            'reasons': ['trend_h04_missing'],
            'months': 1,
            'pass_count': 1,
            'min_balance': 300.0,
            'balance_sum': 300.0,
            'missing_trend': ['2025-01'],
            'missing_range': [],
            'model_unverified': [],
            'next_item': None,
        },
    )

    assert xau_goal_audit.main(['--fail-on-incomplete']) == 1


def test_xau_goal_audit_flags_unverified_model(monkeypatch, capsys):
    monkeypatch.setattr(
        xau_goal_audit,
        'combined_h04_rows',
        lambda args: [
            {
                'month': xau_dual_selector_eval.parse_month('2025.01'),
                'combined_record': {'final_balance': 300},
            }
        ],
    )
    monkeypatch.setattr(xau_goal_audit, 'variant_matrix', lambda args: ([], []))
    monkeypatch.setattr(xau_goal_audit, 'queue_items', lambda args: [])

    xau_goal_audit.main([])

    output = capsys.readouterr().out
    assert 'reasons=model_unverified' in output
    assert 'model_unverified=1' in output


def test_xau_goal_audit_refreshes_ledger_to_temp_path(monkeypatch):
    captured = {}

    def fake_build_ledger(reports_dir, output_path):
        captured['reports_dir'] = reports_dir
        captured['output_path'] = output_path
        output_path.write_text('', encoding='utf-8')
        return 0

    def fake_emit_audit(args):
        captured['base_ledger'] = args.base_ledger
        return {
            'status': 'complete',
            'reasons': [],
        }

    monkeypatch.setattr(xau_goal_audit, 'build_ledger', fake_build_ledger)
    monkeypatch.setattr(xau_goal_audit, 'emit_audit', fake_emit_audit)

    assert xau_goal_audit.main(['--refresh-ledger']) == 0
    assert captured['base_ledger'] == captured['output_path']
    assert captured['base_ledger'].name.startswith('xau_goal_audit_')


def test_xau_ingest_reports_dry_run_lists_xau_reports_only(tmp_path, capsys):
    xau_report = tmp_path / 'xau_20250101_20250131_20260526.txt'
    btc_report = tmp_path / 'btc_20250101_20250131_20260526.txt'
    xau_report.write_text(SAMPLE_REPORT, encoding='utf-8')
    btc_report.write_text(SAMPLE_REPORT.replace('XAUUSDm', 'BTCUSDm'), encoding='utf-8')

    xau_ingest_reports.main(['--reports-dir', str(tmp_path), '--strategies', 'xau', '--dry-run'])

    output = capsys.readouterr().out
    assert 'INGEST candidates=1 symbol=XAUUSDm strategies=xau dry_run=True' in output
    assert str(xau_report) in output
    assert str(btc_report) not in output


def test_xau_ingest_reports_removes_empty_csv_when_log_not_matched(tmp_path, monkeypatch, capsys):
    report = tmp_path / 'xau_20250101_20250131_20260526.txt'
    report.write_text(SAMPLE_REPORT, encoding='utf-8')
    csv_path = report.with_suffix('.trades.csv')

    def fake_digest(report_path, export_csv, brief):
        csv_path.write_text('ticket,time,r\n', encoding='utf-8')
        return {
            'output_path': report.with_suffix('.md'),
            'csv_path': csv_path,
            'matched_symbols': [],
        }

    monkeypatch.setattr(xau_ingest_reports, 'generate_backtest_digest', fake_digest)
    xau_ingest_reports.main(['--reports-dir', str(tmp_path), '--strategies', 'xau'])

    output = capsys.readouterr().out
    assert 'INGEST_DONE md_only' in output
    assert not csv_path.exists()


def test_xau_trend_variant_matrix_h04_rule_uses_probe_net_r(monkeypatch, capsys):
    rows = [
        {
            'month': xau_dual_selector_eval.parse_month('2025.01'),
            'trend_feedback': xau_dual_selector_eval.Feedback(trades=30, net_r=5.0, win_rate=55.0, sl_pct=60.0),
            'records': {
                'base': {'report_path': 'base-low', 'final_balance': 300},
                'block': {'final_balance': 330},
                'half': {'final_balance': 310},
            },
        },
        {
            'month': xau_dual_selector_eval.parse_month('2025.02'),
            'trend_feedback': xau_dual_selector_eval.Feedback(trades=50, net_r=30.0, win_rate=70.0, sl_pct=50.0),
            'records': {
                'base': {'report_path': 'base-high', 'final_balance': 900},
                'block': {'final_balance': 850},
                'half': {'final_balance': 930},
            },
        },
    ]

    monkeypatch.setattr(
        xau_trend_variant_matrix,
        'first_days_feedback',
        lambda record, probe_days: (_ for _ in ()).throw(AssertionError('should use selector feedback')),
    )
    xau_trend_variant_matrix.emit_h04_rule(
        rows,
        SimpleNamespace(
            base_trend_strategy='base',
            h04_block_strategy='block',
            h04_half_strategy='half',
            h04_half_min_net_r=25.0,
            probe_days=5,
        ),
    )

    output = capsys.readouterr().out
    assert 'H04_RULE half_if_tf5_net_r>=25 tested=2/2 min=$330.00 balance_sum=$1260.00 missing=-' in output
    assert 'H04_PICK 2025-01 choose=block balance=$330.00' in output
    assert 'H04_PICK 2025-02 choose=half balance=$930.00' in output


def test_xau_trend_variant_matrix_h04_rule_prints_missing_prediction(capsys):
    rows = [
        {
            'month': xau_dual_selector_eval.parse_month('2025.01'),
            'date_from': xau_dual_selector_eval._parse_day('2025.01.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.01.31'),
            'trend_feedback': xau_dual_selector_eval.Feedback(trades=40, net_r=30.0, win_rate=65.0, sl_pct=45.0),
            'records': {
                'base': {'report_path': 'base-high', 'final_balance': 900},
                'block': {'final_balance': 850},
            },
        }
    ]

    xau_trend_variant_matrix.emit_h04_rule(
        rows,
        SimpleNamespace(
            base_trend_strategy='base',
            h04_block_strategy='block',
            h04_half_strategy='half',
            h04_half_min_net_r=25.0,
            probe_days=5,
        ),
    )

    output = capsys.readouterr().out
    assert 'H04_RULE half_if_tf5_net_r>=25 tested=0/1 min=$0.00 balance_sum=$0.00 missing=2025-01' in output
    assert 'H04_TODO 2025-01 expect=half tf5=n40/R30.0/SL45% delta=5.0 window=2025.01.01~2025.01.31' in output


def test_xau_trend_variant_matrix_h04_grid_ranks_thresholds(capsys):
    rows = [
        {
            'month': xau_dual_selector_eval.parse_month('2025.01'),
            'trend_feedback': xau_dual_selector_eval.Feedback(trades=30, net_r=5.0, win_rate=55.0, sl_pct=60.0),
            'records': {
                'block': {'final_balance': 330},
                'half': {'final_balance': 310},
            },
        },
        {
            'month': xau_dual_selector_eval.parse_month('2025.02'),
            'trend_feedback': xau_dual_selector_eval.Feedback(trades=50, net_r=30.0, win_rate=70.0, sl_pct=50.0),
            'records': {
                'block': {'final_balance': 850},
                'half': {'final_balance': 930},
            },
        },
    ]

    xau_trend_variant_matrix.emit_h04_grid(
        rows,
        SimpleNamespace(
            base_trend_strategy='base',
            h04_block_strategy='block',
            h04_half_strategy='half',
            probe_days=5,
            h04_grid_thresholds='0,25,35',
            h04_grid_top=3,
        ),
    )

    output = capsys.readouterr().out.splitlines()
    assert output[0].startswith('H04_GRID rank=1 half_if_tf5_net_r>=25 tested=2/2 min=$330.00 balance_sum=$1260.00')
    assert 'half_months=1' in output[0]


def test_xau_trend_variant_matrix_sorts_missing_by_sensitivity(capsys):
    rows = [
        {
            'month': xau_dual_selector_eval.parse_month('2025.01'),
            'date_from': xau_dual_selector_eval._parse_day('2025.01.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.01.31'),
            'trend_feedback': xau_dual_selector_eval.Feedback(trades=20, net_r=1.0, win_rate=50.0, sl_pct=60.0),
            'records': {'base': {'report_path': 'base-low'}},
        },
        {
            'month': xau_dual_selector_eval.parse_month('2025.02'),
            'date_from': xau_dual_selector_eval._parse_day('2025.02.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.03.03'),
            'trend_feedback': xau_dual_selector_eval.Feedback(trades=50, net_r=24.0, win_rate=65.0, sl_pct=50.0),
            'records': {'base': {'report_path': 'base-near'}},
        },
    ]

    xau_trend_variant_matrix.emit_h04_rule(
        rows,
        SimpleNamespace(
            base_trend_strategy='base',
            h04_block_strategy='block',
            h04_half_strategy='half',
            h04_half_min_net_r=25.0,
            h04_todo_sort='sensitivity',
            probe_days=5,
        ),
    )

    todo_lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith('H04_TODO')]
    assert todo_lines[0].startswith('H04_TODO 2025-02')


def test_xau_trend_variant_matrix_combines_selector_with_verified_h04(monkeypatch):
    rows = [
        {
            'month': xau_dual_selector_eval.parse_month('2025.01'),
            'date_from': xau_dual_selector_eval._parse_day('2025.01.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.01.31'),
            'selected': 'range',
            'record': {'final_balance': 310},
        },
        {
            'month': xau_dual_selector_eval.parse_month('2025.02'),
            'date_from': xau_dual_selector_eval._parse_day('2025.02.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.03.03'),
            'selected': 'trend',
            'record': {'final_balance': 500},
            'trend_feedback': xau_dual_selector_eval.Feedback(trades=60, net_r=30.0, win_rate=70.0, sl_pct=45.0),
        },
        {
            'month': xau_dual_selector_eval.parse_month('2025.03'),
            'date_from': xau_dual_selector_eval._parse_day('2025.03.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.03.31'),
            'selected': 'trend',
            'record': {'final_balance': 420},
            'trend_feedback': xau_dual_selector_eval.Feedback(trades=30, net_r=5.0, win_rate=55.0, sl_pct=60.0),
        },
    ]
    monkeypatch.setattr(xau_trend_variant_matrix, 'selector_rows', lambda args: (rows, 0))
    monkeypatch.setattr(
        xau_trend_variant_matrix,
        'load_report_records',
        lambda reports_dir: [
            {
                'strategy': 'half',
                'symbol': 'XAUUSDm',
                'date_from': '2025.02.01',
                'date_to': '2025.03.03',
                'final_balance': 900,
            }
        ],
    )

    combined = xau_trend_variant_matrix.combined_h04_rows(
        SimpleNamespace(
            reports_dir=Path('unused'),
            symbol='XAUUSDm',
            h04_half_strategy='half',
            h04_block_strategy='block',
            h04_half_min_net_r=25.0,
        )
    )

    assert [row['combined_label'] for row in combined] == ['range', 'half', 'trend']
    assert [row['combined_record']['final_balance'] for row in combined] == [310, 900, 420]
    assert [row['h04_status'] for row in combined] == ['-', 'applied', 'fallback:block']


def test_xau_trend_variant_matrix_combined_h04_prefers_model4_candidate(monkeypatch):
    rows = [
        {
            'month': xau_dual_selector_eval.parse_month('2025.02'),
            'date_from': xau_dual_selector_eval._parse_day('2025.02.01'),
            'date_to': xau_dual_selector_eval._parse_day('2025.03.03'),
            'selected': 'trend',
            'record': {'final_balance': 500, 'model': None},
            'trend_feedback': xau_dual_selector_eval.Feedback(trades=60, net_r=30.0, win_rate=70.0, sl_pct=45.0),
        },
    ]
    monkeypatch.setattr(xau_trend_variant_matrix, 'selector_rows', lambda args: (rows, 0))
    monkeypatch.setattr(
        xau_trend_variant_matrix,
        'load_report_records',
        lambda reports_dir: [
            {
                'strategy': 'half',
                'symbol': 'XAUUSDm',
                'date_from': '2025.02.01',
                'date_to': '2025.03.03',
                'final_balance': 900,
                'model': None,
            },
            {
                'strategy': 'half',
                'symbol': 'XAUUSDm',
                'date_from': '2025.02.01',
                'date_to': '2025.03.03',
                'final_balance': 300,
                'model': '4',
            },
        ],
    )

    combined = xau_trend_variant_matrix.combined_h04_rows(
        SimpleNamespace(
            reports_dir=Path('unused'),
            symbol='XAUUSDm',
            h04_half_strategy='half',
            h04_block_strategy='block',
            h04_half_min_net_r=25.0,
            preferred_model='4',
        )
    )

    assert combined[0]['combined_record']['final_balance'] == 300
    assert combined[0]['combined_record']['model'] == '4'


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
