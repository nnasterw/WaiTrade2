"""mt5_common 纯函数测试"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

from mt5_common import (
    parse_agent_log_content, calc_stats, format_report,
    resolve_symbols, resolve_strategies,
)
from yaml_to_set import (
    strategy_to_set, format_value, NON_STRATEGY_KEYS, FLAT_MAP, TRAIL_MAP,
)


# ── resolve_symbols ───────────────────────────────────────────────────

def test_resolve_symbols_csv():
    config = {'symbols': {'forex': ['EURUSD', 'GBPUSD'], 'metals': ['XAUUSD']}}
    assert resolve_symbols(config, 'EURUSD,GBPUSD') == ['EURUSD', 'GBPUSD']


def test_resolve_symbols_all():
    config = {'symbols': {'forex': ['EURUSD', 'GBPUSD'], 'metals': ['XAUUSD']}}
    result = resolve_symbols(config, 'all')
    assert set(result) == {'EURUSD', 'GBPUSD', 'XAUUSD'}


def test_resolve_symbols_single():
    config = {'symbols': {}}
    assert resolve_symbols(config, 'XAUUSDm') == ['XAUUSDm']


# ── resolve_strategies ────────────────────────────────────────────────

def test_resolve_strategies_valid():
    config = {
        'defaults': {}, 'symbols': {}, 'backtest_defaults': {}, 'mt5_account': {},
        'v96b': {'version': 'V96b'}, 'v95c': {'version': 'V95c'},
    }
    assert resolve_strategies(config, 'v96b') == ['v96b']


def test_resolve_strategies_multiple():
    config = {
        'defaults': {}, 'symbols': {}, 'backtest_defaults': {}, 'mt5_account': {},
        'v96b': {'version': 'V96b'}, 'v95c': {'version': 'V95c'},
    }
    assert resolve_strategies(config, 'v96b,v95c') == ['v96b', 'v95c']


def test_resolve_strategies_invalid(capsys):
    config = {
        'defaults': {}, 'symbols': {},
        'v96b': {'version': 'V96b'},
    }
    try:
        resolve_strategies(config, 'v99z')
        assert False, 'should have exited'
    except SystemExit:
        pass


# ── NON_STRATEGY_KEYS ─────────────────────────────────────────────────

def test_non_strategy_keys_content():
    assert 'defaults' in NON_STRATEGY_KEYS
    assert 'symbols' in NON_STRATEGY_KEYS
    assert 'backtest_defaults' in NON_STRATEGY_KEYS
    assert 'mt5_account' in NON_STRATEGY_KEYS
    assert len(NON_STRATEGY_KEYS) == 4


# ── parse_agent_log_content ───────────────────────────────────────────

SAMPLE_LOG = """2026.05.15 10:00:00.000	testing of WaiTrade_OB started
2026.05.15 10:00:01.000	deal #1 buy 0.01 XAUUSDm at 3200.500 sl: 3195.000
2026.05.15 10:00:02.000	deal #2 sell 0.01 XAUUSDm at 3210.500
2026.05.15 10:00:03.000	deal #3 sell 0.01 XAUUSDm at 3210.000 sl: 3215.000
2026.05.15 10:00:04.000	deal #4 buy 0.01 XAUUSDm at 3205.000
2026.05.15 10:00:05.000	final balance 215.00
2026.05.15 10:00:06.000	50000 ticks, 1500 bars generated
"""


def test_parse_log_extracts_deals():
    result = parse_agent_log_content(SAMPLE_LOG)
    assert result is not None
    assert len(result['deals']) == 4
    assert result['trades'] == 2


def test_parse_log_deal_fields():
    result = parse_agent_log_content(SAMPLE_LOG)
    d = result['deals'][0]
    assert d['ticket'] == 1
    assert d['direction'] == 'buy'
    assert d['lots'] == 0.01
    assert d['symbol'] == 'XAUUSDm'
    assert d['price'] == 3200.5
    assert d['sl'] == 3195.0


def test_parse_log_balance():
    result = parse_agent_log_content(SAMPLE_LOG)
    assert result['final_balance'] == 215.0


def test_parse_log_ticks_bars():
    result = parse_agent_log_content(SAMPLE_LOG)
    assert result['ticks'] == 50000
    assert result['bars'] == 1500


def test_parse_log_empty():
    assert parse_agent_log_content('no testing data here') is None


def test_parse_log_deal_no_sl():
    result = parse_agent_log_content(SAMPLE_LOG)
    d = result['deals'][1]  # deal #2 has no sl
    assert d['sl'] is None


def test_parse_log_multiple_segments():
    log = """testing of EA1 started
deal #1 buy 0.01 EURUSD at 1.10000
final balance 180.00
testing of EA2 started
deal #1 buy 0.01 EURUSD at 1.11000
deal #2 sell 0.01 EURUSD at 1.12000 sl: 1.10500
final balance 220.00
"""
    result = parse_agent_log_content(log)
    assert result['final_balance'] == 220.0
    assert result['trades'] == 1


# ── calc_stats ────────────────────────────────────────────────────────

def test_calc_stats_basic():
    result = parse_agent_log_content(SAMPLE_LOG)
    stats = calc_stats(result, deposit=200, days=30)
    assert stats is not None
    assert stats['trades'] == 2
    assert stats['wins'] + stats['losses'] == 2
    assert 0 <= stats['win_rate'] <= 100
    assert stats['final_balance'] == 215.0
    assert stats['profit'] == 15.0


def test_calc_stats_none_input():
    assert calc_stats(None, 200, 30) is None


def test_calc_stats_win_rate():
    # deal #1 buy@3200.5 → deal #2 sell@3210.5 → profit (buy: exit-entry > 0)
    # deal #3 sell@3210.0 → deal #4 buy@3205.0 → profit (sell: entry-exit > 0)
    result = parse_agent_log_content(SAMPLE_LOG)
    stats = calc_stats(result, 200, 30)
    assert stats['wins'] == 2
    assert stats['losses'] == 0
    assert stats['win_rate'] == 100.0


def test_calc_stats_r_multiples():
    result = parse_agent_log_content(SAMPLE_LOG)
    stats = calc_stats(result, 200, 30)
    # deal #1: risk = |3200.5 - 3195.0| = 5.5, pnl = 3210.5-3200.5 = 10.0, R = 10/5.5 ≈ 1.818
    # deal #3: sl=3215, risk = |3210-3215| = 5.0, pnl = 3210-3205 = 5.0, R = 5/5 = 1.0
    assert stats['net_r'] is not None
    assert abs(stats['net_r'] - (10.0/5.5 + 1.0)) < 0.01


def test_calc_stats_daily_trades():
    result = parse_agent_log_content(SAMPLE_LOG)
    stats = calc_stats(result, 200, 30)
    assert abs(stats['daily_trades'] - 2/30) < 0.001


# ── format_report ─────────────────────────────────────────────────────

def test_format_report_contains_strategy():
    symbol_results = {'XAUUSDm': {
        'trades': 10, 'wins': 7, 'losses': 3,
        'win_rate': 70.0, 'profit_factor': 2.5, 'daily_trades': 0.33,
        'final_balance': 230.0, 'profit': 30.0, 'net_r': 5.2,
    }}
    report = format_report('v96b', '2026.04.15', '2026.05.15', 30, 200, '2000', symbol_results)
    assert 'V96B' in report
    assert 'XAUUSDm' in report
    assert '$230.00' in report


def test_format_report_failed_symbol():
    symbol_results = {'BTCUSDm': None}
    report = format_report('v96b', '2026.04.15', '2026.05.15', 30, 200, '2000', symbol_results)
    assert '回测失败' in report


# ── format_value ──────────────────────────────────────────────────────

def test_format_value_bool():
    assert format_value(True) == 'true'
    assert format_value(False) == 'false'


def test_format_value_number():
    assert format_value(0.3) == '0.3'
    assert format_value(60) == '60'


def test_format_value_string():
    assert format_value('V96b') == 'V96b'


# ── strategy_to_set ───────────────────────────────────────────────────

def test_strategy_to_set_basic():
    cfg = {
        'version': 'V96b',
        'description': 'test',
        'bounce_pct': 0.30,
        'breakeven_r': 0.2,
    }
    content = strategy_to_set('v96b', cfg)
    assert 'InpBouncePct=0.3' in content
    assert 'InpBreakevenR=0.2' in content
    assert 'InpVersion=V96b' in content


def test_strategy_to_set_trail_levels():
    cfg = {
        'version': 'test',
        'trail_levels': [
            {'trigger_r': 1.0, 'lock_r': 0.2},
            {'trigger_r': 2.5, 'lock_r': 0.0, 'lock_mult': 0.65},
            {'trigger_r': 0.0, 'lock_r': 0.0, 'lock_mult': 0.0},
        ],
    }
    content = strategy_to_set('test', cfg)
    assert 'InpTrail1TriggerR=1.0' in content
    assert 'InpTrail1LockR=0.2' in content
    assert 'InpTrail2LockMult=0.65' in content
    # trail1 没有 LockMult
    assert 'InpTrail1LockMult' not in content


def test_strategy_to_set_comment_line():
    cfg = {'version': 'V96b', 'description': 'M1+二推'}
    content = strategy_to_set('v96b', cfg)
    assert content.startswith('; V96b')
    assert 'M1+二推' in content
