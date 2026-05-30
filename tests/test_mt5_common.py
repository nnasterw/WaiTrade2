"""mt5_common 纯函数测试"""
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

from mt5_common import (
    parse_agent_log_content, calc_stats, format_report,
    resolve_symbols, resolve_strategies,
    parse_backtest_report_content, split_agent_log_segments,
    find_matching_log_segment, parse_agent_log_segment_details,
    _signal_type_from_comment,
)
from yaml_to_set import (
    strategy_to_set, format_value, NON_STRATEGY_KEYS, FLAT_MAP, TRAIL_MAP,
    load_strategies,
)
from backtest_digest import (
    build_digest_data, build_monthly_stats, render_digest_markdown, write_trade_csv,
    read_text_auto_tail,
)
import backtest_digest
import mt5_cli_backtest as cli
import mt5_backtest_win as win_cli


# ── resolve_symbols ───────────────────────────────────────────────────

def test_repo_strategies_yaml_loads():
    strategies = load_strategies(
        Path(__file__).resolve().parent.parent / 'config' / 'strategies.yaml'
    )

    assert 'v11_r221_j2_r61_context_march_probe' in strategies


def test_xau_range_hour_experiments_preserve_base_no_entry_hours():
    strategies = load_strategies(
        Path(__file__).resolve().parent.parent / 'config' / 'strategies.yaml'
    )

    base_hours = set(strategies['v11xau_range']['no_entry_hours'].split(','))
    block_hours = set(strategies['v11xau_range_h15_block']['no_entry_hours'].split(','))

    assert block_hours == base_hours | {'15'}
    assert strategies['v11xau_range_h1415_half']['no_entry_hours'] == strategies['v11xau_range']['no_entry_hours']
    assert strategies['v11xau_range_h1415_half']['low_risk_hours'] == '14,15'


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


def test_parse_log_negative_balance():
    log = """testing of EA started
deal #1 buy 0.01 EURUSD at 1.10000
final balance -0.16 USD
"""
    result = parse_agent_log_content(log)
    assert result['final_balance'] == -0.16


def test_parse_log_ticks_bars():
    result = parse_agent_log_content(SAMPLE_LOG)
    assert result['ticks'] == 50000
    assert result['bars'] == 1500


def test_parse_log_stopout():
    log = """testing of EA started
final balance -0.86 USD
stop out occurred on 28% of testing interval
"""
    result = parse_agent_log_content(log)
    assert result['stopout'] is True
    assert result['stopout_pct'] == 28


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


def test_format_report_can_include_model():
    symbol_results = {'XAUUSDm': {
        'trades': 1, 'wins': 1, 'losses': 0,
        'win_rate': 100.0, 'profit_factor': float('inf'), 'daily_trades': 0.03,
        'final_balance': 230.0, 'profit': 30.0, 'net_r': 2.0,
    }}
    report = format_report('v96b', '2026.04.15', '2026.05.15', 30, 200, '2000', symbol_results, model=4)
    parsed = parse_backtest_report_content(report)

    assert '模型: 4' in report
    assert parsed['model'] == '4'


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


def test_spread_floor_in_flat_map():
    assert 'spread_floor' in FLAT_MAP
    assert FLAT_MAP['spread_floor'] == 'InpSpreadFloor'


def test_strategy_to_set_spread_floor():
    cfg = {'version': 'test', 'spread_floor': 0.30}
    content = strategy_to_set('test', cfg)
    assert 'InpSpreadFloor=0.3' in content


# ── v9.8 四维参数映射 ─────────────────────────────────────────────────

def test_v98_trend_params_in_flat_map():
    assert FLAT_MAP['trend_lookback'] == 'InpTrendLookback'
    assert FLAT_MAP['swing_strength'] == 'InpSwingStrength'


def test_v98_state_params_in_flat_map():
    assert FLAT_MAP['enable_state_filter'] == 'InpEnableStateFilter'
    assert FLAT_MAP['range_be_r'] == 'InpRangeBE_R'
    assert FLAT_MAP['range_time_exit'] == 'InpRangeTimeExit'
    assert FLAT_MAP['trend_be_r'] == 'InpTrendBE_R'
    assert FLAT_MAP['trend_be_lock'] == 'InpTrendBE_Lock'
    assert FLAT_MAP['trend_dtp_retrace'] == 'InpTrendDTPRetrace'


def test_v98_scoring_params_in_flat_map():
    assert FLAT_MAP['enable_scoring'] == 'InpEnableScoring'
    assert FLAT_MAP['proximity_filter'] == 'InpProximityFilter'
    assert FLAT_MAP['proximity_atr'] == 'InpProximityATR'
    assert FLAT_MAP['min_score'] == 'InpMinScore'


def test_v98_decay_params_in_flat_map():
    assert FLAT_MAP['enable_decay_exit'] == 'InpEnableDecayExit'
    assert FLAT_MAP['decay_min_r'] == 'InpDecayMinR'
    assert FLAT_MAP['decay_bars'] == 'InpDecayBars'
    assert FLAT_MAP['engulf_body_pct'] == 'InpEngulfBodyPct'


def test_v11_btc_profile_extended_params_in_flat_map():
    assert FLAT_MAP['btc_enable_state_filter'] == 'InpBTCEnableStateFilter'
    assert FLAT_MAP['btc_enable_scoring'] == 'InpBTCEnableScoring'
    assert FLAT_MAP['btc_enable_decay_exit'] == 'InpBTCEnableDecayExit'
    assert FLAT_MAP['btc_mfe_fail_min_r'] == 'InpBTCMFEFailMinR'
    assert FLAT_MAP['btc_no_mfe_exit_bars'] == 'InpBTCNoMFEExitBars'
    assert FLAT_MAP['btc_enable_htf_net_push_filter'] == 'InpBTCEnableHTFNetPushFilter'
    assert FLAT_MAP['btc_htf_net_push_tf'] == 'InpBTCHTFNetPushTF'
    assert FLAT_MAP['btc_free_run_min_r'] == 'InpBTCFreeRunMinR'
    assert FLAT_MAP['btc_shallow_confirm_pos_mult'] == 'InpBTCShallowConfirmPosMult'
    assert FLAT_MAP['btc_dtp_reset_peak_after_partial'] == 'InpBTCDTPResetPeakAfterPartial'


def test_strategy_to_set_v11_btc_profile_extended_params():
    cfg = {
        'version': 'V11',
        'btc_enable_state_filter': True,
        'btc_mfe_fail_exit_r': -0.1,
        'btc_no_mfe_exit_bars': 3,
        'btc_htf_net_push_tf': 60,
        'btc_dtp_reset_peak_after_partial': False,
    }
    content = strategy_to_set('v11', cfg)
    assert 'InpBTCEnableStateFilter=true' in content
    assert 'InpBTCMFEFailExitR=-0.1' in content
    assert 'InpBTCNoMFEExitBars=3' in content
    assert 'InpBTCHTFNetPushTF=60' in content
    assert 'InpBTCDTPResetPeakAfterPartial=false' in content


def test_v11_xau_fage_alt_profile_params_in_flat_map():
    assert FLAT_MAP['enable_xau_fage_alt_profile'] == 'InpEnableXAUFageAltProfile'
    assert FLAT_MAP['xau_fage_alt_profile_months'] == 'InpXAUFageAltProfileMonths'
    assert FLAT_MAP['xau_fage_alt_use_month_filter'] == 'InpXAUFageAltUseMonthFilter'
    assert FLAT_MAP['xau_fage_alt_adaptive_start_day'] == 'InpXAUFageAltAdaptiveStartDay'
    assert FLAT_MAP['xau_fage_alt_adaptive_max_balance'] == 'InpXAUFageAltAdaptiveMaxBalance'
    assert FLAT_MAP['xau_fage_alt_adaptive_min_price'] == 'InpXAUFageAltAdaptiveMinPrice'
    assert FLAT_MAP['xau_fage_alt_adaptive_max_price'] == 'InpXAUFageAltAdaptiveMaxPrice'
    assert FLAT_MAP['xau_alt_context_filter1_months'] == 'InpXAUAltContextFilter1Months'
    assert FLAT_MAP['xau_alt_context_filter5_no_hours'] == 'InpXAUAltContextFilter5NoHours'
    assert FLAT_MAP['xau_alt_monthly_profit_target_stop_months'] == 'InpXAUAltMonthlyProfitTargetStopMonths'


def test_v11_xau_trend_profile_params_in_flat_map():
    assert FLAT_MAP['enable_xau_trend_profile'] == 'InpEnableXAUTrendProfile'
    assert FLAT_MAP['xau_trend_min_abs_net_atr'] == 'InpXAUTrendMinAbsNetATR'
    assert FLAT_MAP['xau_trend_min_range_atr'] == 'InpXAUTrendMinRangeATR'
    assert FLAT_MAP['xau_trend_fixed_tp_r'] == 'InpXAUTrendFixedTPR'
    assert FLAT_MAP['xau_trend_max_entries_per_ob'] == 'InpXAUTrendMaxEntriesPerOB'
    assert FLAT_MAP['xau_trend_htf_net_push_counter_mult'] == 'InpXAUTrendHTFNetPushCounterMult'


def test_strategy_to_set_v11_xau_trend_profile_params():
    cfg = {
        'version': 'V11',
        'enable_xau_trend_profile': True,
        'xau_trend_min_abs_net_atr': 0.55,
        'xau_trend_min_range_atr': 5.0,
        'xau_trend_fixed_tp_r': 1.5,
        'xau_trend_max_entries_per_ob': 20,
        'xau_trend_htf_net_push_counter_mult': 0.0,
    }
    content = strategy_to_set('v11', cfg)
    assert 'InpEnableXAUTrendProfile=true' in content
    assert 'InpXAUTrendMinAbsNetATR=0.55' in content
    assert 'InpXAUTrendMinRangeATR=5.0' in content
    assert 'InpXAUTrendFixedTPR=1.5' in content
    assert 'InpXAUTrendMaxEntriesPerOB=20' in content
    assert 'InpXAUTrendHTFNetPushCounterMult=0.0' in content


def test_strategy_to_set_v11_xau_fage_alt_profile_params():
    cfg = {
        'version': 'V11',
        'enable_xau_fage_alt_profile': True,
        'xau_fage_alt_profile_months': '10',
        'xau_fage_alt_use_month_filter': False,
        'xau_fage_alt_adaptive_start_day': 5,
        'xau_fage_alt_adaptive_max_balance': 230.0,
        'xau_fage_alt_adaptive_min_price': 2500.0,
        'xau_fage_alt_adaptive_max_price': 4350.0,
        'xau_alt_context_filter1_no_hours': '10,11',
        'xau_alt_monthly_profit_target_stop_months': '10',
    }
    content = strategy_to_set('v11', cfg)
    assert 'InpEnableXAUFageAltProfile=true' in content
    assert 'InpXAUFageAltProfileMonths=10' in content
    assert 'InpXAUFageAltUseMonthFilter=false' in content
    assert 'InpXAUFageAltAdaptiveStartDay=5' in content
    assert 'InpXAUFageAltAdaptiveMaxBalance=230.0' in content
    assert 'InpXAUFageAltAdaptiveMinPrice=2500.0' in content
    assert 'InpXAUFageAltAdaptiveMaxPrice=4350.0' in content
    assert 'InpXAUAltContextFilter1NoHours=10,11' in content
    assert 'InpXAUAltMonthlyProfitTargetStopMonths=10' in content


def test_v98_strategy_full_set():
    cfg = {
        'version': 'V98',
        'enable_state_filter': True,
        'enable_scoring': True,
        'enable_decay_exit': True,
        'trend_lookback': 80,
        'swing_strength': 3,
        'range_be_r': 1.0,
        'range_time_exit': 30,
        'min_score': 2,
        'decay_min_r': 1.0,
        'decay_bars': 3,
        'engulf_body_pct': 50,
    }
    content = strategy_to_set('v98', cfg)
    assert 'InpEnableStateFilter=true' in content
    assert 'InpEnableScoring=true' in content
    assert 'InpEnableDecayExit=true' in content
    assert 'InpTrendLookback=80' in content
    assert 'InpRangeBE_R=1.0' in content
    assert 'InpMinScore=2' in content


# ── v9.8a EntryEngine 参数映射 ────────────────────────────────────────

def test_v98a_entry_engine_params():
    assert FLAT_MAP['enable_entry_engine'] == 'InpEnableEntryEngine'
    assert FLAT_MAP['entry_depth_pct'] == 'InpEntryDepthPct'
    assert FLAT_MAP['entry_depth_filter'] == 'InpEntryDepthFilter'
    assert FLAT_MAP['deep_entry_boost'] == 'InpDeepEntryBoost'
    assert FLAT_MAP['entry_confirm_bars'] == 'InpEntryConfirmBars'
    assert FLAT_MAP['bounce_close_confirm_bars'] == 'InpBounceCloseConfirmBars'
    assert FLAT_MAP['bounce_close_tf'] == 'InpBounceCloseTF'
    assert FLAT_MAP['bounce_close_buffer_pct'] == 'InpBounceCloseBufferPct'
    assert FLAT_MAP['bounce_close_require_body'] == 'InpBounceCloseRequireBody'
    assert FLAT_MAP['enable_entry_momentum_filter'] == 'InpEnableEntryMomentumFilter'
    assert FLAT_MAP['entry_momentum_tf'] == 'InpEntryMomentumTF'
    assert FLAT_MAP['entry_block_counter_strong'] == 'InpEntryBlockCounterStrong'
    assert FLAT_MAP['entry_require_counter_weak'] == 'InpEntryRequireCounterWeak'


def test_bounce_close_confirm_params_in_set():
    content = strategy_to_set('test', {
        'version': 'test',
        'bounce_close_confirm_bars': 2,
        'bounce_close_tf': 1,
        'bounce_close_buffer_pct': 0.10,
        'bounce_close_require_body': True,
    })
    assert 'InpBounceCloseConfirmBars=2' in content
    assert 'InpBounceCloseTF=1' in content
    assert 'InpBounceCloseBufferPct=0.1' in content
    assert 'InpBounceCloseRequireBody=true' in content


def test_entry_momentum_filter_params_in_set():
    content = strategy_to_set('test', {
        'version': 'test',
        'enable_entry_momentum_filter': True,
        'entry_momentum_tf': 1,
        'entry_block_counter_strong': True,
        'entry_require_counter_weak': False,
    })
    assert 'InpEnableEntryMomentumFilter=true' in content
    assert 'InpEntryMomentumTF=1' in content
    assert 'InpEntryBlockCounterStrong=true' in content
    assert 'InpEntryRequireCounterWeak=false' in content


def test_partial_close_params():
    assert FLAT_MAP['partial_close_r'] == 'InpPartialCloseR'
    assert FLAT_MAP['partial_close_pct'] == 'InpPartialClosePct'
    assert FLAT_MAP['partial_post_lock_r'] == 'InpPartialPostLockR'
    assert FLAT_MAP['partial_only_deep'] == 'InpPartialOnlyDeep'


def test_partial_close_in_set():
    cfg = {'version': 'test', 'partial_close_r': 1.0, 'partial_close_pct': 50, 'partial_post_lock_r': 0.2, 'partial_only_deep': True}
    content = strategy_to_set('test', cfg)
    assert 'InpPartialCloseR=1.0' in content
    assert 'InpPartialClosePct=50' in content
    assert 'InpPartialPostLockR=0.2' in content
    assert 'InpPartialOnlyDeep=true' in content


def test_dtp_stage_params_in_set():
    assert FLAT_MAP['dtp_post_partial_lock_r'] == 'InpDTPPostPartialLockR'
    assert FLAT_MAP['dtp_reset_peak_after_partial'] == 'InpDTPResetPeakAfterPartial'
    cfg = {
        'version': 'test',
        'dtp_stage2_trigger_r': 3.0,
        'dtp_stage2_retrace': 0.25,
        'dtp_stage3_trigger_r': 4.0,
        'dtp_stage3_retrace': 0.30,
        'dtp_exit_mode': 1,
        'dtp_partial_pct': 50,
        'dtp_post_partial_retrace': 0.35,
        'dtp_post_partial_lock_r': 1.0,
        'dtp_reset_peak_after_partial': True,
        'enable_exit_debug': True,
        'enable_entry_debug': True,
    }
    content = strategy_to_set('test', cfg)
    assert 'InpDTPStage2TriggerR=3.0' in content
    assert 'InpDTPStage2Retrace=0.25' in content
    assert 'InpDTPStage3TriggerR=4.0' in content
    assert 'InpDTPStage3Retrace=0.3' in content
    assert 'InpDTPExitMode=1' in content
    assert 'InpDTPPartialPct=50' in content
    assert 'InpDTPPostPartialRetrace=0.35' in content
    assert 'InpDTPPostPartialLockR=1.0' in content
    assert 'InpDTPResetPeakAfterPartial=true' in content
    assert 'InpEnableExitDebug=true' in content
    assert 'InpEnableEntryDebug=true' in content


def test_early_loss_cut_param_in_set():
    assert FLAT_MAP['early_loss_cut_r'] == 'InpEarlyLossCutR'
    assert FLAT_MAP['mfe_fail_min_r'] == 'InpMFEFailMinR'
    assert FLAT_MAP['mfe_fail_exit_r'] == 'InpMFEFailExitR'
    assert FLAT_MAP['no_mfe_exit_bars'] == 'InpNoMFEExitBars'
    assert FLAT_MAP['no_mfe_min_peak_r'] == 'InpNoMFEMinPeakR'
    assert FLAT_MAP['no_mfe_exit_r'] == 'InpNoMFEExitR'
    assert FLAT_MAP['enable_failure_reverse'] == 'InpEnableFailureReverse'
    assert FLAT_MAP['reverse_on_early_loss'] == 'InpReverseOnEarlyLoss'
    assert FLAT_MAP['reverse_on_mfe_fail'] == 'InpReverseOnMFEFail'
    assert FLAT_MAP['reverse_on_no_mfe'] == 'InpReverseOnNoMFE'
    assert FLAT_MAP['failure_reverse_risk_mult'] == 'InpFailureReverseRiskMult'
    assert FLAT_MAP['failure_reverse_lot_mult'] == 'InpFailureReverseLotMult'
    assert FLAT_MAP['failure_reverse_tp_r'] == 'InpFailureReverseTPR'
    assert FLAT_MAP['failure_reverse_allow_chain'] == 'InpFailureReverseAllowChain'
    content = strategy_to_set('test', {
        'version': 'test',
        'early_loss_cut_r': 0.35,
        'mfe_fail_min_r': 0.5,
        'mfe_fail_exit_r': -0.1,
        'no_mfe_exit_bars': 3,
        'no_mfe_min_peak_r': 0.15,
        'no_mfe_exit_r': -0.2,
    })
    assert 'InpEarlyLossCutR=0.35' in content
    assert 'InpMFEFailMinR=0.5' in content
    assert 'InpMFEFailExitR=-0.1' in content
    assert 'InpNoMFEExitBars=3' in content
    assert 'InpNoMFEMinPeakR=0.15' in content
    assert 'InpNoMFEExitR=-0.2' in content


def test_failure_reverse_params_in_set():
    content = strategy_to_set('test', {
        'version': 'test',
        'enable_failure_reverse': True,
        'reverse_on_early_loss': True,
        'reverse_on_mfe_fail': False,
        'reverse_on_no_mfe': True,
        'failure_reverse_risk_mult': 1.2,
        'failure_reverse_lot_mult': 0.8,
        'failure_reverse_tp_r': 2.0,
        'failure_reverse_allow_chain': False,
    })
    assert 'InpEnableFailureReverse=true' in content
    assert 'InpReverseOnEarlyLoss=true' in content
    assert 'InpReverseOnMFEFail=false' in content
    assert 'InpReverseOnNoMFE=true' in content
    assert 'InpFailureReverseRiskMult=1.2' in content
    assert 'InpFailureReverseLotMult=0.8' in content
    assert 'InpFailureReverseTPR=2.0' in content
    assert 'InpFailureReverseAllowChain=false' in content


def test_direction_override_params_in_set():
    content = strategy_to_set('test', {
        'version': 'test',
        'buy_min_strength': 5.0,
        'sell_min_strength': 3.0,
        'buy_pos_mult': 0.5,
        'sell_pos_mult': 1.2,
        'buy_be_r': 0.6,
        'buy_be_lock': 0.2,
        'sell_be_r': 1.2,
        'sell_be_lock': 0.6,
        'buy_dtp_trigger_r': 1.5,
        'buy_dtp_retrace': 0.15,
        'sell_dtp_trigger_r': 3.0,
        'sell_dtp_retrace': 0.35,
        'enable_confirm_pullback': True,
        'confirm_pullback_pct': 0.4,
        'confirm_pullback_wait_sec': 20,
        'confirm_pullback_max_adverse_pct': 0.1,
        'enable_strong_addon': True,
        'strong_addon_trigger_r': 1.2,
        'strong_addon_step_r': 0.8,
        'strong_addon_max_count': 2,
        'strong_addon_lot_mult': 0.4,
        'strong_addon_risk_mult': 0.6,
        'strong_addon_min_spread_ratio': 6.0,
    })
    assert 'InpBuyMinStrength=5.0' in content
    assert 'InpSellMinStrength=3.0' in content
    assert 'InpBuyPosMult=0.5' in content
    assert 'InpSellPosMult=1.2' in content
    assert 'InpBuyBE_R=0.6' in content
    assert 'InpBuyBE_Lock=0.2' in content
    assert 'InpSellBE_R=1.2' in content
    assert 'InpSellBE_Lock=0.6' in content
    assert 'InpBuyDTPTriggerR=1.5' in content
    assert 'InpBuyDTPRetrace=0.15' in content
    assert 'InpSellDTPTriggerR=3.0' in content
    assert 'InpSellDTPRetrace=0.35' in content
    assert 'InpEnableConfirmPullback=true' in content
    assert 'InpConfirmPullbackPct=0.4' in content
    assert 'InpConfirmPullbackWaitSec=20' in content
    assert 'InpConfirmPullbackMaxAdversePct=0.1' in content
    assert 'InpEnableStrongAddOn=true' in content
    assert 'InpStrongAddOnTriggerR=1.2' in content
    assert 'InpStrongAddOnStepR=0.8' in content
    assert 'InpStrongAddOnMaxCount=2' in content
    assert 'InpStrongAddOnLotMult=0.4' in content
    assert 'InpStrongAddOnRiskMult=0.6' in content
    assert 'InpStrongAddOnMinSpreadRatio=6.0' in content


def test_gap_quality_params_in_set():
    assert FLAT_MAP['min_ob_body_pct'] == 'InpMinOBBodyPct'
    assert FLAT_MAP['min_impulse_body_pct'] == 'InpMinImpulseBodyPct'
    assert FLAT_MAP['min_impulse_vol_ratio'] == 'InpMinImpulseVolRatio'
    assert FLAT_MAP['structure_break_bars'] == 'InpStructureBreakBars'
    assert FLAT_MAP['structure_break_atr'] == 'InpStructureBreakATR'
    assert FLAT_MAP['require_impulse_candle_dir'] == 'InpRequireImpulseCandleDir'
    assert FLAT_MAP['no_ob_start_hour'] == 'InpNoOBStartHour'
    assert FLAT_MAP['no_ob_end_hour'] == 'InpNoOBEndHour'
    assert FLAT_MAP['min_ob_strength'] == 'InpMinOBStrength'
    assert FLAT_MAP['max_risk_atr'] == 'InpMaxRiskATR'
    assert FLAT_MAP['max_counter_risk_atr'] == 'InpMaxCounterRiskATR'
    cfg = {
        'version': 'test',
        'min_ob_body_pct': 55,
        'min_impulse_body_pct': 60,
        'min_impulse_vol_ratio': 1.3,
        'structure_break_bars': 3,
        'structure_break_atr': 0.1,
        'require_impulse_candle_dir': True,
        'no_ob_start_hour': 22,
        'no_ob_end_hour': 7,
        'min_ob_strength': 0.8,
        'max_risk_atr': 2.5,
        'max_counter_risk_atr': 1.2,
    }
    content = strategy_to_set('test', cfg)
    assert 'InpMinOBBodyPct=55' in content
    assert 'InpMinImpulseBodyPct=60' in content
    assert 'InpMinImpulseVolRatio=1.3' in content
    assert 'InpStructureBreakBars=3' in content
    assert 'InpStructureBreakATR=0.1' in content
    assert 'InpRequireImpulseCandleDir=true' in content
    assert 'InpNoOBStartHour=22' in content
    assert 'InpNoOBEndHour=7' in content
    assert 'InpMinOBStrength=0.8' in content
    assert 'InpMaxRiskATR=2.5' in content
    assert 'InpMaxCounterRiskATR=1.2' in content


def test_liquidity_sweep_params_in_set():
    assert FLAT_MAP['enable_liquidity_sweep'] == 'InpEnableLiquiditySweep'
    assert FLAT_MAP['liquidity_sweep_only'] == 'InpLiquiditySweepOnly'
    assert FLAT_MAP['sweep_lookback_bars'] == 'InpSweepLookbackBars'
    assert FLAT_MAP['sweep_max_range_atr'] == 'InpSweepMaxRangeATR'
    assert FLAT_MAP['sweep_min_range_spread_mult'] == 'InpSweepMinRangeSpreadMult'
    assert FLAT_MAP['sweep_min_penetration_atr'] == 'InpSweepMinPenetrationATR'
    assert FLAT_MAP['sweep_min_wick_pct'] == 'InpSweepMinWickPct'
    assert FLAT_MAP['sweep_tp_mult'] == 'InpSweepTPMult'
    assert FLAT_MAP['enable_loose_sweep'] == 'InpEnableLooseSweep'
    assert FLAT_MAP['loose_sweep_lookback_bars'] == 'InpLooseSweepLookbackBars'
    assert FLAT_MAP['loose_sweep_max_range_atr'] == 'InpLooseSweepMaxRangeATR'
    assert FLAT_MAP['loose_sweep_min_range_spread_mult'] == 'InpLooseSweepMinRangeSpreadMult'
    assert FLAT_MAP['loose_sweep_min_penetration_atr'] == 'InpLooseSweepMinPenetrationATR'
    assert FLAT_MAP['loose_sweep_min_wick_pct'] == 'InpLooseSweepMinWickPct'
    assert FLAT_MAP['loose_sweep_max_active_zones'] == 'InpLooseSweepMaxActiveZones'
    assert FLAT_MAP['enable_htf_pullback'] == 'InpEnableHTFPullback'
    assert FLAT_MAP['htf_pullback_only'] == 'InpHTFPullbackOnly'
    assert FLAT_MAP['htf_pullback_tf'] == 'InpHTFPullbackTF'
    assert FLAT_MAP['htf_pullback_bars'] == 'InpHTFPullbackBars'
    assert FLAT_MAP['htf_pullback_min_atr'] == 'InpHTFPullbackMinATR'
    assert FLAT_MAP['htf_pullback_zone_atr'] == 'InpHTFPullbackZoneATR'
    assert FLAT_MAP['htf_pullback_offset_atr'] == 'InpHTFPullbackOffsetATR'
    assert FLAT_MAP['htf_pullback_tp_mult'] == 'InpHTFPullbackTPMult'

    content = strategy_to_set('test', {
        'version': 'test',
        'enable_liquidity_sweep': True,
        'liquidity_sweep_only': True,
        'sweep_lookback_bars': 12,
        'sweep_max_range_atr': 2.5,
        'sweep_min_range_spread_mult': 4.0,
        'sweep_min_penetration_atr': 0.05,
        'sweep_min_wick_pct': 45.0,
        'sweep_tp_mult': 1.5,
        'enable_loose_sweep': True,
        'loose_sweep_lookback_bars': 6,
        'loose_sweep_max_range_atr': 4.0,
        'loose_sweep_min_range_spread_mult': 2.5,
        'loose_sweep_min_penetration_atr': 0.01,
        'loose_sweep_min_wick_pct': 30.0,
        'loose_sweep_max_active_zones': 12,
        'enable_htf_pullback': True,
        'htf_pullback_only': True,
        'htf_pullback_tf': 30,
        'htf_pullback_bars': 4,
        'htf_pullback_min_atr': 0.9,
        'htf_pullback_zone_atr': 0.4,
        'htf_pullback_offset_atr': 0.15,
        'htf_pullback_tp_mult': 1.3,
        'htf_pullback_allow_hours': '12,20,23',
        'htf_pullback_no_hours': '13',
        'htf_pullback_risk_min': 200.0,
        'htf_pullback_risk_max': 300.0,
        'htf_pullback_confirm_min': -1.5,
        'htf_pullback_confirm_max': 999.0,
        'htf_pullback_context_mult': 2.0,
    })
    assert 'InpEnableLiquiditySweep=true' in content
    assert 'InpLiquiditySweepOnly=true' in content
    assert 'InpSweepLookbackBars=12' in content
    assert 'InpSweepMaxRangeATR=2.5' in content
    assert 'InpSweepMinRangeSpreadMult=4.0' in content
    assert 'InpSweepMinPenetrationATR=0.05' in content
    assert 'InpSweepMinWickPct=45.0' in content
    assert 'InpSweepTPMult=1.5' in content
    assert 'InpEnableLooseSweep=true' in content
    assert 'InpLooseSweepLookbackBars=6' in content
    assert 'InpLooseSweepMaxRangeATR=4.0' in content
    assert 'InpLooseSweepMinRangeSpreadMult=2.5' in content
    assert 'InpLooseSweepMinPenetrationATR=0.01' in content
    assert 'InpLooseSweepMinWickPct=30.0' in content
    assert 'InpLooseSweepMaxActiveZones=12' in content
    assert 'InpEnableHTFPullback=true' in content
    assert 'InpHTFPullbackOnly=true' in content
    assert 'InpHTFPullbackTF=30' in content
    assert 'InpHTFPullbackBars=4' in content
    assert 'InpHTFPullbackMinATR=0.9' in content
    assert 'InpHTFPullbackZoneATR=0.4' in content
    assert 'InpHTFPullbackOffsetATR=0.15' in content
    assert 'InpHTFPullbackTPMult=1.3' in content
    assert 'InpHTFPullbackAllowHours=12,20,23' in content
    assert 'InpHTFPullbackNoHours=13' in content
    assert 'InpHTFPullbackRiskMin=200.0' in content
    assert 'InpHTFPullbackRiskMax=300.0' in content
    assert 'InpHTFPullbackConfirmMin=-1.5' in content
    assert 'InpHTFPullbackConfirmMax=999.0' in content
    assert 'InpHTFPullbackContextMult=2.0' in content


def test_execution_and_scan_params_in_set():
    assert FLAT_MAP['impulse_atr_mult'] == 'InpImpulseATRMult'
    assert FLAT_MAP['impulse_lookback'] == 'InpImpulseLookback'
    assert FLAT_MAP['entry_depth_relax_min_balance'] == 'InpEntryDepthRelaxMinBalance'
    assert FLAT_MAP['atr_period'] == 'InpATRPeriod'
    assert FLAT_MAP['fixed_lot_size'] == 'InpFixedLotSize'
    assert FLAT_MAP['enable_pos_mult'] == 'InpEnablePosMult'
    assert FLAT_MAP['max_pos_mult'] == 'InpMaxPosMult'
    assert FLAT_MAP['max_lot_size'] == 'InpMaxLotSize'
    assert FLAT_MAP['sweep_pos_mult'] == 'InpSweepPosMult'
    assert FLAT_MAP['range_breakout_pos_mult'] == 'InpRangeBreakoutPosMult'
    assert FLAT_MAP['htf_pullback_pos_mult'] == 'InpHTFPullbackPosMult'
    assert FLAT_MAP['sweep_max_lot_size'] == 'InpSweepMaxLotSize'
    assert FLAT_MAP['loose_sweep_pos_mult'] == 'InpLooseSweepPosMult'
    assert FLAT_MAP['loose_sweep_max_lot_size'] == 'InpLooseSweepMaxLotSize'
    assert FLAT_MAP['loose_sweep_max_active_zones'] == 'InpLooseSweepMaxActiveZones'
    assert FLAT_MAP['range_breakout_max_lot_size'] == 'InpRangeBreakoutMaxLotSize'
    assert FLAT_MAP['htf_pullback_max_lot_size'] == 'InpHTFPullbackMaxLotSize'
    assert FLAT_MAP['htf_pullback_allow_hours'] == 'InpHTFPullbackAllowHours'
    assert FLAT_MAP['htf_pullback_no_hours'] == 'InpHTFPullbackNoHours'
    assert FLAT_MAP['htf_pullback_risk_min'] == 'InpHTFPullbackRiskMin'
    assert FLAT_MAP['htf_pullback_risk_max'] == 'InpHTFPullbackRiskMax'
    assert FLAT_MAP['htf_pullback_confirm_min'] == 'InpHTFPullbackConfirmMin'
    assert FLAT_MAP['htf_pullback_confirm_max'] == 'InpHTFPullbackConfirmMax'
    assert FLAT_MAP['htf_pullback_context_mult'] == 'InpHTFPullbackContextMult'
    assert FLAT_MAP['sweep_allow_hours'] == 'InpSweepAllowHours'
    assert FLAT_MAP['sweep_no_hours'] == 'InpSweepNoHours'
    assert FLAT_MAP['sweep_context_months'] == 'InpSweepContextMonths'
    assert FLAT_MAP['sweep_context_max_day'] == 'InpSweepContextMaxDay'
    assert FLAT_MAP['sweep_context_min_month_start_balance'] == 'InpSweepContextMinMonthStartBalance'
    assert FLAT_MAP['sweep_context_no_hours'] == 'InpSweepContextNoHours'
    assert FLAT_MAP['sweep_bad_risk_min'] == 'InpSweepBadRiskMin'
    assert FLAT_MAP['sweep_bad_risk_max'] == 'InpSweepBadRiskMax'
    assert FLAT_MAP['sweep_bad_risk_mult'] == 'InpSweepBadRiskMult'
    assert FLAT_MAP['sweep_min_balance'] == 'InpSweepMinBalance'
    assert FLAT_MAP['sweep_low_balance_threshold'] == 'InpSweepLowBalanceThreshold'
    assert FLAT_MAP['sweep_low_balance_mult'] == 'InpSweepLowBalanceMult'
    assert FLAT_MAP['sweep_monthly_negative_mult'] == 'InpSweepMonthlyNegativeMult'
    assert FLAT_MAP['sweep_monthly_profit_start_pct'] == 'InpSweepMonthlyProfitStartPct'
    assert FLAT_MAP['sweep_early_bounce_sec_min'] == 'InpSweepEarlyBounceSecMin'
    assert FLAT_MAP['sweep_early_bounce_sec_max'] == 'InpSweepEarlyBounceSecMax'
    assert FLAT_MAP['sweep_early_bounce_mult'] == 'InpSweepEarlyBounceMult'
    assert FLAT_MAP['sweep_early_bounce_hours'] == 'InpSweepEarlyBounceHours'
    assert FLAT_MAP['sweep_bad_age_min_bars'] == 'InpSweepBadAgeMinBars'
    assert FLAT_MAP['sweep_bad_age_max_bars'] == 'InpSweepBadAgeMaxBars'
    assert FLAT_MAP['sweep_bad_age_mult'] == 'InpSweepBadAgeMult'
    assert FLAT_MAP['ob_pos_mult'] == 'InpOBPosMult'
    assert FLAT_MAP['ob_pos_mult_min_balance'] == 'InpOBPosMultMinBalance'
    assert FLAT_MAP['ob_bad_hours'] == 'InpOBBadHours'
    assert FLAT_MAP['ob_bad_hour_mult'] == 'InpOBBadHourMult'
    assert FLAT_MAP['low_balance_ob_bad_hours'] == 'InpLowBalanceOBBadHours'
    assert FLAT_MAP['low_balance_ob_bad_months'] == 'InpLowBalanceOBBadMonths'
    assert FLAT_MAP['low_balance_ob_bad_max_month_start_balance'] == 'InpLowBalanceOBBadMaxMonthStartBalance'
    assert FLAT_MAP['low_balance_ob_bad_hour_mult'] == 'InpLowBalanceOBBadHourMult'
    assert FLAT_MAP['low_balance_threshold'] == 'InpLowBalanceThreshold'
    assert FLAT_MAP['low_balance_pos_mult'] == 'InpLowBalancePosMult'
    assert FLAT_MAP['low_balance_max_lot_size'] == 'InpLowBalanceMaxLotSize'
    assert FLAT_MAP['monthly_guard_min_balance'] == 'InpMonthlyGuardMinBalance'
    assert FLAT_MAP['monthly_loss_stop_pct'] == 'InpMonthlyLossStopPct'
    assert FLAT_MAP['monthly_loss_stop_min_trades'] == 'InpMonthlyLossStopMinTrades'
    assert FLAT_MAP['monthly_early_loss_stop_trades'] == 'InpMonthlyEarlyLossStopTrades'
    assert FLAT_MAP['monthly_early_loss_stop_pct'] == 'InpMonthlyEarlyLossStopPct'
    assert FLAT_MAP['monthly_early_loss_stop_min_balance'] == 'InpMonthlyEarlyLossStopMinBalance'
    assert FLAT_MAP['monthly_early_loss_stop_continuous'] == 'InpMonthlyEarlyLossStopContinuous'
    assert FLAT_MAP['monthly_negative_pos_mult'] == 'InpMonthlyNegativePosMult'
    assert FLAT_MAP['monthly_warmup_profit_pct'] == 'InpMonthlyWarmupProfitPct'
    assert FLAT_MAP['monthly_warmup_pos_mult'] == 'InpMonthlyWarmupPosMult'
    assert FLAT_MAP['monthly_profit_lock_min_balance'] == 'InpMonthlyProfitLockMinBalance'
    assert FLAT_MAP['monthly_profit_lock_start_pct'] == 'InpMonthlyProfitLockStartPct'
    assert FLAT_MAP['monthly_profit_lock_keep_pct'] == 'InpMonthlyProfitLockKeepPct'
    assert FLAT_MAP['monthly_profit_target_stop_pct'] == 'InpMonthlyProfitTargetStopPct'
    assert FLAT_MAP['monthly_profit_target_stop_min_balance'] == 'InpMonthlyProfitTargetStopMinBalance'
    assert FLAT_MAP['monthly_profit_target_stop_max_balance'] == 'InpMonthlyProfitTargetStopMaxBalance'
    assert FLAT_MAP['monthly_profit_target_stop_months'] == 'InpMonthlyProfitTargetStopMonths'
    assert FLAT_MAP['monthly_profit_target_stop2_pct'] == 'InpMonthlyProfitTargetStop2Pct'
    assert FLAT_MAP['monthly_profit_target_stop2_min_balance'] == 'InpMonthlyProfitTargetStop2MinBalance'
    assert FLAT_MAP['monthly_profit_target_stop2_max_balance'] == 'InpMonthlyProfitTargetStop2MaxBalance'
    assert FLAT_MAP['monthly_profit_target_stop2_months'] == 'InpMonthlyProfitTargetStop2Months'
    assert FLAT_MAP['shared_monthly_guard'] == 'InpSharedMonthlyGuard'
    assert FLAT_MAP['shared_monthly_guard_key'] == 'InpSharedMonthlyGuardKey'
    assert FLAT_MAP['shared_monthly_guard_debug'] == 'InpSharedMonthlyGuardDebug'
    assert FLAT_MAP['free_run_min_r'] == 'InpFreeRunMinR'
    assert FLAT_MAP['entry_months'] == 'InpEntryMonths'
    assert FLAT_MAP['high_balance_no_entry_months'] == 'InpHighBalanceNoEntryMonths'
    assert FLAT_MAP['high_balance_no_entry_min_month_start_balance'] == 'InpHighBalanceNoEntryMinMonthStartBalance'
    assert FLAT_MAP['no_entry_hours'] == 'InpNoEntryHours'
    assert FLAT_MAP['no_buy_hours'] == 'InpNoBuyHours'
    assert FLAT_MAP['no_sell_hours'] == 'InpNoSellHours'
    assert FLAT_MAP['low_risk_hours'] == 'InpLowRiskHours'
    assert FLAT_MAP['low_risk_hour_mult'] == 'InpLowRiskHourMult'
    assert FLAT_MAP['high_risk_hours'] == 'InpHighRiskHours'
    assert FLAT_MAP['high_risk_hour_mult'] == 'InpHighRiskHourMult'
    assert FLAT_MAP['context_filter1_months'] == 'InpContextFilter1Months'
    assert FLAT_MAP['context_filter1_no_hours'] == 'InpContextFilter1NoHours'
    assert FLAT_MAP['context_filter1_no_buy_hours'] == 'InpContextFilter1NoBuyHours'
    assert FLAT_MAP['context_filter1_no_sell_hours'] == 'InpContextFilter1NoSellHours'
    assert FLAT_MAP['context_filter1_min_month_start_balance'] == 'InpContextFilter1MinMonthStartBalance'
    assert FLAT_MAP['context_filter1_max_month_start_balance'] == 'InpContextFilter1MaxMonthStartBalance'
    assert FLAT_MAP['context_filter1_min_price'] == 'InpContextFilter1MinPrice'
    assert FLAT_MAP['context_filter1_max_price'] == 'InpContextFilter1MaxPrice'
    assert FLAT_MAP['context_filter1_mult'] == 'InpContextFilter1Mult'
    assert FLAT_MAP['context_filter4_months'] == 'InpContextFilter4Months'
    assert FLAT_MAP['context_filter4_no_buy_hours'] == 'InpContextFilter4NoBuyHours'
    assert FLAT_MAP['context_filter4_no_sell_hours'] == 'InpContextFilter4NoSellHours'
    assert FLAT_MAP['context_filter4_min_month_start_balance'] == 'InpContextFilter4MinMonthStartBalance'
    assert FLAT_MAP['context_filter4_min_price'] == 'InpContextFilter4MinPrice'
    assert FLAT_MAP['context_filter4_mult'] == 'InpContextFilter4Mult'
    assert FLAT_MAP['context_filter5_months'] == 'InpContextFilter5Months'
    assert FLAT_MAP['context_filter5_no_hours'] == 'InpContextFilter5NoHours'
    assert FLAT_MAP['context_reverse_hours'] == 'InpContextReverseHours'
    assert FLAT_MAP['context_reverse_directions'] == 'InpContextReverseDirections'
    assert FLAT_MAP['context_reverse_sell_early_day_max'] == 'InpContextReverseSellEarlyDayMax'
    assert FLAT_MAP['context_reverse_min_price'] == 'InpContextReverseMinPrice'
    assert FLAT_MAP['context_reverse_max_month_start_balance'] == 'InpContextReverseMaxMonthStartBalance'
    assert FLAT_MAP['context_reverse_max_risk'] == 'InpContextReverseMaxRisk'
    assert FLAT_MAP['context_be_min_price'] == 'InpContextBEMinPrice'
    assert FLAT_MAP['context_be_r'] == 'InpContextBER'
    assert FLAT_MAP['late_bounce_sec'] == 'InpLateBounceSec'
    assert FLAT_MAP['late_bounce_mult'] == 'InpLateBounceMult'
    assert FLAT_MAP['bounce_sweet_min_pct'] == 'InpBounceSweetMinPct'
    assert FLAT_MAP['bounce_sweet_max_pct'] == 'InpBounceSweetMaxPct'
    assert FLAT_MAP['outside_bounce_sweet_mult'] == 'InpOutsideBounceSweetMult'
    assert FLAT_MAP['bad_risk_min'] == 'InpBadRiskMin'
    assert FLAT_MAP['bad_risk_max'] == 'InpBadRiskMax'
    assert FLAT_MAP['bad_risk_mult'] == 'InpBadRiskMult'
    assert FLAT_MAP['large_risk_min'] == 'InpLargeRiskMin'
    assert FLAT_MAP['large_risk_mult'] == 'InpLargeRiskMult'
    assert FLAT_MAP['shallow_confirm_pos_min'] == 'InpShallowConfirmPosMin'
    assert FLAT_MAP['shallow_confirm_pos_mult'] == 'InpShallowConfirmPosMult'
    assert FLAT_MAP['bad_cluster_min_balance'] == 'InpBadClusterMinBalance'
    assert FLAT_MAP['bad_cluster_only_monthly_negative'] == 'InpBadClusterOnlyMonthlyNegative'
    assert FLAT_MAP['bad_cluster1_hours'] == 'InpBadCluster1Hours'
    assert FLAT_MAP['bad_cluster1_risk_min'] == 'InpBadCluster1RiskMin'
    assert FLAT_MAP['bad_cluster1_risk_max'] == 'InpBadCluster1RiskMax'
    assert FLAT_MAP['bad_cluster1_confirm_min'] == 'InpBadCluster1ConfirmMin'
    assert FLAT_MAP['bad_cluster1_confirm_max'] == 'InpBadCluster1ConfirmMax'
    assert FLAT_MAP['bad_cluster1_mult'] == 'InpBadCluster1Mult'
    assert FLAT_MAP['bad_cluster1_signal'] == 'InpBadCluster1Signal'
    assert FLAT_MAP['bad_cluster2_signal'] == 'InpBadCluster2Signal'
    assert FLAT_MAP['bad_cluster3_signal'] == 'InpBadCluster3Signal'
    assert FLAT_MAP['bad_cluster4_signal'] == 'InpBadCluster4Signal'
    assert FLAT_MAP['bad_cluster5_hours'] == 'InpBadCluster5Hours'
    assert FLAT_MAP['bad_cluster5_risk_min'] == 'InpBadCluster5RiskMin'
    assert FLAT_MAP['bad_cluster5_risk_max'] == 'InpBadCluster5RiskMax'
    assert FLAT_MAP['bad_cluster5_confirm_min'] == 'InpBadCluster5ConfirmMin'
    assert FLAT_MAP['bad_cluster5_confirm_max'] == 'InpBadCluster5ConfirmMax'
    assert FLAT_MAP['bad_cluster5_mult'] == 'InpBadCluster5Mult'
    assert FLAT_MAP['bad_cluster5_signal'] == 'InpBadCluster5Signal'
    assert FLAT_MAP['bad_cluster6_hours'] == 'InpBadCluster6Hours'
    assert FLAT_MAP['bad_cluster6_risk_min'] == 'InpBadCluster6RiskMin'
    assert FLAT_MAP['bad_cluster6_risk_max'] == 'InpBadCluster6RiskMax'
    assert FLAT_MAP['bad_cluster6_confirm_min'] == 'InpBadCluster6ConfirmMin'
    assert FLAT_MAP['bad_cluster6_confirm_max'] == 'InpBadCluster6ConfirmMax'
    assert FLAT_MAP['bad_cluster6_mult'] == 'InpBadCluster6Mult'
    assert FLAT_MAP['bad_cluster6_signal'] == 'InpBadCluster6Signal'
    assert FLAT_MAP['bad_cluster_filtered_monthly_stop'] == 'InpBadClusterFilteredMonthlyStop'
    assert FLAT_MAP['bad_cluster_filtered_stop_min_balance'] == 'InpBadClusterFilteredStopMinBalance'
    assert FLAT_MAP['startup_bad_cluster_max_month_start_balance'] == 'InpStartupBadClusterMaxMonthStartBalance'
    assert FLAT_MAP['startup_bad_cluster1_hours'] == 'InpStartupBadCluster1Hours'
    assert FLAT_MAP['startup_bad_cluster1_risk_min'] == 'InpStartupBadCluster1RiskMin'
    assert FLAT_MAP['startup_bad_cluster1_risk_max'] == 'InpStartupBadCluster1RiskMax'
    assert FLAT_MAP['startup_bad_cluster1_confirm_min'] == 'InpStartupBadCluster1ConfirmMin'
    assert FLAT_MAP['startup_bad_cluster1_confirm_max'] == 'InpStartupBadCluster1ConfirmMax'
    assert FLAT_MAP['startup_bad_cluster1_mult'] == 'InpStartupBadCluster1Mult'
    assert FLAT_MAP['startup_bad_cluster1_signal'] == 'InpStartupBadCluster1Signal'
    assert FLAT_MAP['startup_bad_cluster4_hours'] == 'InpStartupBadCluster4Hours'
    assert FLAT_MAP['startup_bad_cluster4_risk_min'] == 'InpStartupBadCluster4RiskMin'
    assert FLAT_MAP['startup_bad_cluster4_risk_max'] == 'InpStartupBadCluster4RiskMax'
    assert FLAT_MAP['startup_bad_cluster4_confirm_min'] == 'InpStartupBadCluster4ConfirmMin'
    assert FLAT_MAP['startup_bad_cluster4_confirm_max'] == 'InpStartupBadCluster4ConfirmMax'
    assert FLAT_MAP['startup_bad_cluster4_mult'] == 'InpStartupBadCluster4Mult'
    assert FLAT_MAP['startup_bad_cluster4_signal'] == 'InpStartupBadCluster4Signal'
    assert FLAT_MAP['enable_htf_net_push_filter'] == 'InpEnableHTFNetPushFilter'
    assert FLAT_MAP['htf_net_push_tf'] == 'InpHTFNetPushTF'
    assert FLAT_MAP['htf_net_push_bars'] == 'InpHTFNetPushBars'
    assert FLAT_MAP['htf_net_push_min_atr'] == 'InpHTFNetPushMinATR'
    assert FLAT_MAP['htf_net_push_aligned_mult'] == 'InpHTFNetPushAlignedMult'
    assert FLAT_MAP['htf_net_push_neutral_mult'] == 'InpHTFNetPushNeutralMult'
    assert FLAT_MAP['htf_net_push_counter_mult'] == 'InpHTFNetPushCounterMult'
    assert FLAT_MAP['buy_min_strength'] == 'InpBuyMinStrength'
    assert FLAT_MAP['sell_min_strength'] == 'InpSellMinStrength'
    assert FLAT_MAP['buy_pos_mult'] == 'InpBuyPosMult'
    assert FLAT_MAP['sell_pos_mult'] == 'InpSellPosMult'
    assert FLAT_MAP['buy_be_r'] == 'InpBuyBE_R'
    assert FLAT_MAP['buy_be_lock'] == 'InpBuyBE_Lock'
    assert FLAT_MAP['sell_be_r'] == 'InpSellBE_R'
    assert FLAT_MAP['sell_be_lock'] == 'InpSellBE_Lock'
    assert FLAT_MAP['buy_dtp_trigger_r'] == 'InpBuyDTPTriggerR'
    assert FLAT_MAP['buy_dtp_retrace'] == 'InpBuyDTPRetrace'
    assert FLAT_MAP['sell_dtp_trigger_r'] == 'InpSellDTPTriggerR'
    assert FLAT_MAP['sell_dtp_retrace'] == 'InpSellDTPRetrace'
    assert FLAT_MAP['enable_confirm_pullback'] == 'InpEnableConfirmPullback'
    assert FLAT_MAP['confirm_pullback_pct'] == 'InpConfirmPullbackPct'
    assert FLAT_MAP['confirm_pullback_wait_sec'] == 'InpConfirmPullbackWaitSec'
    assert FLAT_MAP['confirm_pullback_max_adverse_pct'] == 'InpConfirmPullbackMaxAdversePct'
    assert FLAT_MAP['enable_strong_addon'] == 'InpEnableStrongAddOn'
    assert FLAT_MAP['strong_addon_trigger_r'] == 'InpStrongAddOnTriggerR'
    assert FLAT_MAP['strong_addon_step_r'] == 'InpStrongAddOnStepR'
    assert FLAT_MAP['strong_addon_max_count'] == 'InpStrongAddOnMaxCount'
    assert FLAT_MAP['strong_addon_lot_mult'] == 'InpStrongAddOnLotMult'
    assert FLAT_MAP['strong_addon_risk_mult'] == 'InpStrongAddOnRiskMult'
    assert FLAT_MAP['strong_addon_min_spread_ratio'] == 'InpStrongAddOnMinSpreadRatio'
    assert FLAT_MAP['close_retry_cooldown_sec'] == 'InpCloseRetryCooldownSec'
    assert FLAT_MAP['max_entries_per_ob'] == 'InpMaxEntriesPerOB'
    assert FLAT_MAP['ob_reentry_cooldown_min'] == 'InpOBReentryCooldownMin'
    assert FLAT_MAP['reentry_pos_mult'] == 'InpReentryPosMult'
    assert FLAT_MAP['continuation_pos_mult'] == 'InpContinuationPosMult'
    assert FLAT_MAP['filter_cont_age_min_bars'] == 'InpFilterContAgeMinBars'
    assert FLAT_MAP['filter_cont_age_max_bars'] == 'InpFilterContAgeMaxBars'
    assert FLAT_MAP['filter_cont_non_deep_only'] == 'InpFilterContNonDeepOnly'
    assert FLAT_MAP['filter_buy_no_h1_min_pos_mult'] == 'InpFilterBuyNoH1MinPosMult'
    assert FLAT_MAP['filter_buy_no_h1_max_pos_mult'] == 'InpFilterBuyNoH1MaxPosMult'
    assert FLAT_MAP['filter_buy_no_h1_pos_mult'] == 'InpFilterBuyNoH1PosMult'


def test_context_filter_params_in_set():
    content = strategy_to_set('test', {
        'version': 'test',
        'context_filter1_months': '11',
        'context_filter1_no_hours': '7,13',
        'context_filter1_no_buy_hours': '20,21',
        'context_filter1_no_sell_hours': '0,8',
        'context_filter1_min_month_start_balance': 100000.0,
        'context_filter1_max_month_start_balance': 25000.0,
        'context_filter1_min_price': 3000.0,
        'context_filter1_max_price': 4500.0,
        'context_filter1_mult': 0.0,
        'context_filter2_months': '3',
        'context_filter2_no_sell_hours': '0,1,8',
        'context_filter2_mult': 0.5,
        'context_filter4_months': '10',
        'context_filter4_no_buy_hours': '18,22',
        'context_filter4_no_sell_hours': '0,1,8',
        'context_filter4_min_month_start_balance': 50000.0,
        'context_filter4_min_price': 3300.0,
        'context_filter4_mult': 0.0,
        'context_filter5_months': '12',
        'context_filter5_no_hours': '4,5',
        'context_filter5_max_month_start_balance': 2500.0,
        'context_filter5_mult': 0.25,
        'context_reverse_hours': '14,15',
        'context_reverse_directions': 'buy',
        'context_reverse_sell_early_day_max': 2,
        'context_reverse_sell_late_day_min': 25,
        'context_reverse_min_price': 4500.0,
        'context_reverse_max_month_start_balance': 500.0,
        'context_reverse_max_risk': 10.0,
        'context_reverse_tp_r': 1.0,
        'context_be_min_price': 4500.0,
        'context_be_max_month_start_balance': 500.0,
        'context_be_r': 1.0,
        'context_be_lock_r': 0.2,
    })

    assert 'InpContextFilter1Months=11' in content
    assert 'InpContextFilter1NoHours=7,13' in content
    assert 'InpContextFilter1NoBuyHours=20,21' in content
    assert 'InpContextFilter1NoSellHours=0,8' in content
    assert 'InpContextFilter1MinMonthStartBalance=100000.0' in content
    assert 'InpContextFilter1MaxMonthStartBalance=25000.0' in content
    assert 'InpContextFilter1MinPrice=3000.0' in content
    assert 'InpContextFilter1MaxPrice=4500.0' in content
    assert 'InpContextFilter1Mult=0.0' in content
    assert 'InpContextFilter2Months=3' in content
    assert 'InpContextFilter2NoSellHours=0,1,8' in content
    assert 'InpContextFilter2Mult=0.5' in content
    assert 'InpContextFilter4Months=10' in content
    assert 'InpContextFilter4NoBuyHours=18,22' in content
    assert 'InpContextFilter4NoSellHours=0,1,8' in content
    assert 'InpContextFilter4MinMonthStartBalance=50000.0' in content
    assert 'InpContextFilter4MinPrice=3300.0' in content
    assert 'InpContextFilter4Mult=0.0' in content
    assert 'InpContextFilter5Months=12' in content
    assert 'InpContextFilter5NoHours=4,5' in content
    assert 'InpContextFilter5MaxMonthStartBalance=2500.0' in content
    assert 'InpContextFilter5Mult=0.25' in content
    assert 'InpContextReverseHours=14,15' in content
    assert 'InpContextReverseDirections=buy' in content
    assert 'InpContextReverseSellEarlyDayMax=2' in content
    assert 'InpContextReverseSellLateDayMin=25' in content
    assert 'InpContextReverseMinPrice=4500.0' in content
    assert 'InpContextReverseMaxMonthStartBalance=500.0' in content
    assert 'InpContextReverseMaxRisk=10.0' in content
    assert 'InpContextReverseTPR=1.0' in content
    assert 'InpContextBEMinPrice=4500.0' in content
    assert 'InpContextBEMaxMonthStartBalance=500.0' in content
    assert 'InpContextBER=1.0' in content
    assert 'InpContextBELockR=0.2' in content
    assert FLAT_MAP['ob_scan_depth'] == 'InpOBScanDepth'
    assert FLAT_MAP['magic_number'] == 'InpMagicNumber'
    assert FLAT_MAP['enable_entry_debug'] == 'InpEnableEntryDebug'
    cfg = {
        'version': 'legacy',
        'impulse_atr_mult': 1.5,
        'impulse_lookback': 3,
        'atr_period': 14,
        'fixed_lot_size': 0.01,
        'enable_pos_mult': False,
        'max_pos_mult': 8.0,
        'max_lot_size': 0.08,
        'free_run_min_r': 5.0,
        'entry_months': '3',
        'high_balance_no_entry_months': '5',
        'high_balance_no_entry_min_month_start_balance': 5000.0,
        'no_entry_hours': '0,9,12',
        'no_buy_hours': '8,10',
        'no_sell_hours': '16,22',
        'low_risk_hours': '1,3,5',
        'low_risk_hour_mult': 0.25,
        'high_risk_hours': '12,14,15',
        'high_risk_hour_mult': 2.0,
        'late_bounce_sec': 30,
        'late_bounce_mult': 0.4,
        'sweep_early_bounce_sec_min': 1,
        'sweep_early_bounce_sec_max': 5,
        'sweep_early_bounce_mult': 0.35,
        'sweep_early_bounce_hours': '0,9,20',
        'sweep_context_months': '3',
        'sweep_context_max_day': 2,
        'sweep_context_min_month_start_balance': 100000.0,
        'sweep_context_no_hours': '0,1,6,23',
        'sweep_bad_age_min_bars': 20,
        'sweep_bad_age_max_bars': 40,
        'sweep_bad_age_mult': 0.35,
        'low_balance_ob_bad_hours': '7,13,14',
        'low_balance_ob_bad_months': '11',
        'low_balance_ob_bad_max_month_start_balance': 2500.0,
        'low_balance_ob_bad_hour_mult': 0.0,
        'monthly_profit_target_stop_pct': 3.0,
        'monthly_profit_target_stop_max_balance': 2500.0,
        'monthly_profit_target_stop_months': '10,12',
        'monthly_profit_target_stop2_pct': 3.0,
        'monthly_profit_target_stop2_max_balance': 5000.0,
        'monthly_profit_target_stop2_months': '9',
        'shared_monthly_guard': True,
        'shared_monthly_guard_key': 'demo_guard',
        'shared_monthly_guard_debug': True,
        'bounce_sweet_min_pct': 0.26,
        'bounce_sweet_max_pct': 0.34,
        'outside_bounce_sweet_mult': 0.5,
        'bad_risk_min': 150.0,
        'bad_risk_max': 200.0,
        'bad_risk_mult': 0.4,
        'large_risk_min': 300.0,
        'large_risk_mult': 1.5,
        'shallow_confirm_pos_min': -0.6,
        'shallow_confirm_pos_mult': 0.45,
        'enable_htf_net_push_filter': True,
        'htf_net_push_tf': 15,
        'htf_net_push_bars': 4,
        'htf_net_push_min_atr': 0.6,
        'htf_net_push_aligned_mult': 1.2,
        'htf_net_push_neutral_mult': 0.8,
        'htf_net_push_counter_mult': 0.35,
        'close_retry_cooldown_sec': 60,
        'max_entries_per_ob': 2,
        'ob_reentry_cooldown_min': 30,
        'reentry_pos_mult': 0.20,
        'continuation_pos_mult': 1.20,
        'filter_cont_age_min_bars': 40,
        'filter_cont_age_max_bars': 79,
        'filter_cont_non_deep_only': True,
        'filter_buy_no_h1_min_pos_mult': 5.0,
        'filter_buy_no_h1_max_pos_mult': 6.5,
        'filter_buy_no_h1_pos_mult': 0.4,
        'ob_scan_depth': 200,
        'magic_number': 202605,
        'enable_entry_engine': False,
    }
    content = strategy_to_set('legacy', cfg)
    assert 'InpImpulseATRMult=1.5' in content
    assert 'InpImpulseLookback=3' in content
    assert 'InpATRPeriod=14' in content
    assert 'InpFixedLotSize=0.01' in content
    assert 'InpEnablePosMult=false' in content
    assert 'InpMaxPosMult=8.0' in content
    assert 'InpMaxLotSize=0.08' in content
    assert 'InpFreeRunMinR=5.0' in content
    assert 'InpEntryMonths=3' in content
    assert 'InpHighBalanceNoEntryMonths=5' in content
    assert 'InpHighBalanceNoEntryMinMonthStartBalance=5000.0' in content
    assert 'InpNoEntryHours=0,9,12' in content
    assert 'InpNoBuyHours=8,10' in content
    assert 'InpNoSellHours=16,22' in content
    assert 'InpLowRiskHours=1,3,5' in content
    assert 'InpLowRiskHourMult=0.25' in content
    assert 'InpHighRiskHours=12,14,15' in content
    assert 'InpHighRiskHourMult=2.0' in content
    assert 'InpLateBounceSec=30' in content
    assert 'InpLateBounceMult=0.4' in content
    assert 'InpSweepEarlyBounceSecMin=1' in content
    assert 'InpSweepEarlyBounceSecMax=5' in content
    assert 'InpSweepEarlyBounceMult=0.35' in content
    assert 'InpSweepEarlyBounceHours=0,9,20' in content
    assert 'InpSweepContextMonths=3' in content
    assert 'InpSweepContextMaxDay=2' in content
    assert 'InpSweepContextMinMonthStartBalance=100000.0' in content
    assert 'InpSweepContextNoHours=0,1,6,23' in content
    assert 'InpSweepBadAgeMinBars=20' in content
    assert 'InpSweepBadAgeMaxBars=40' in content
    assert 'InpSweepBadAgeMult=0.35' in content
    assert 'InpLowBalanceOBBadHours=7,13,14' in content
    assert 'InpLowBalanceOBBadMonths=11' in content
    assert 'InpLowBalanceOBBadMaxMonthStartBalance=2500.0' in content
    assert 'InpLowBalanceOBBadHourMult=0.0' in content
    assert 'InpMonthlyProfitTargetStopPct=3.0' in content
    assert 'InpMonthlyProfitTargetStopMaxBalance=2500.0' in content
    assert 'InpMonthlyProfitTargetStopMonths=10,12' in content
    assert 'InpMonthlyProfitTargetStop2Pct=3.0' in content
    assert 'InpMonthlyProfitTargetStop2MaxBalance=5000.0' in content
    assert 'InpMonthlyProfitTargetStop2Months=9' in content
    assert 'InpSharedMonthlyGuard=true' in content
    assert 'InpSharedMonthlyGuardKey=demo_guard' in content
    assert 'InpSharedMonthlyGuardDebug=true' in content
    assert 'InpBounceSweetMinPct=0.26' in content
    assert 'InpBounceSweetMaxPct=0.34' in content
    assert 'InpOutsideBounceSweetMult=0.5' in content
    assert 'InpBadRiskMin=150.0' in content
    assert 'InpBadRiskMax=200.0' in content
    assert 'InpBadRiskMult=0.4' in content
    assert 'InpLargeRiskMin=300.0' in content
    assert 'InpLargeRiskMult=1.5' in content
    assert 'InpShallowConfirmPosMin=-0.6' in content
    assert 'InpShallowConfirmPosMult=0.45' in content
    assert 'InpEnableHTFNetPushFilter=true' in content
    assert 'InpHTFNetPushTF=15' in content
    assert 'InpHTFNetPushBars=4' in content
    assert 'InpHTFNetPushMinATR=0.6' in content
    assert 'InpHTFNetPushAlignedMult=1.2' in content
    assert 'InpHTFNetPushNeutralMult=0.8' in content
    assert 'InpHTFNetPushCounterMult=0.35' in content
    assert 'InpCloseRetryCooldownSec=60' in content
    assert 'InpMaxEntriesPerOB=2' in content
    assert 'InpOBReentryCooldownMin=30' in content
    assert 'InpReentryPosMult=0.2' in content
    assert 'InpContinuationPosMult=1.2' in content
    assert 'InpFilterContAgeMinBars=40' in content
    assert 'InpFilterContAgeMaxBars=79' in content
    assert 'InpFilterContNonDeepOnly=true' in content
    assert 'InpFilterBuyNoH1MinPosMult=5.0' in content
    assert 'InpFilterBuyNoH1MaxPosMult=6.5' in content
    assert 'InpFilterBuyNoH1PosMult=0.4' in content
    assert 'InpOBScanDepth=200' in content
    assert 'InpMagicNumber=202605' in content
    assert 'InpEnableEntryEngine=false' in content


def test_v11_layered_params_in_set():
    assert FLAT_MAP['layered_entry_count'] == 'InpLayeredEntryCount'
    assert FLAT_MAP['layered_spacing_pct'] == 'InpLayeredSpacingPct'
    assert FLAT_MAP['layered_lot_mult'] == 'InpLayeredLotMult'
    assert FLAT_MAP['layered_avg_tp_r'] == 'InpLayeredAvgTP_R'
    assert FLAT_MAP['micro_entry_count'] == 'InpMicroEntryCount'
    assert FLAT_MAP['micro_entry_lot_mult'] == 'InpMicroEntryLotMult'
    assert FLAT_MAP['micro_entry_max_lot_size'] == 'InpMicroEntryMaxLotSize'

    content = strategy_to_set('test', {
        'version': 'test',
        'layered_entry_count': 2,
        'layered_spacing_pct': 0.33,
        'layered_lot_mult': 1.5,
        'layered_avg_tp_r': 0.0,
        'micro_entry_count': 1,
        'micro_entry_lot_mult': 0.03,
        'micro_entry_max_lot_size': 0.01,
    })
    assert 'InpLayeredEntryCount=2' in content
    assert 'InpLayeredSpacingPct=0.33' in content
    assert 'InpLayeredLotMult=1.5' in content
    assert 'InpLayeredAvgTP_R=0.0' in content
    assert 'InpMicroEntryCount=1' in content
    assert 'InpMicroEntryLotMult=0.03' in content
    assert 'InpMicroEntryMaxLotSize=0.01' in content


def test_xau_defensive_params_in_set():
    assert FLAT_MAP['defensive_confirm_max_balance'] == 'InpDefensiveConfirmMaxBalance'
    assert FLAT_MAP['defensive_bounce_close_min_body_pct'] == 'InpDefensiveBounceCloseMinBodyPct'
    assert FLAT_MAP['defensive_max_entries_per_ob'] == 'InpDefensiveMaxEntriesPerOB'
    assert FLAT_MAP['defensive_virtual_sl_confirm_bars'] == 'InpDefensiveVirtualSLConfirmBars'

    content = strategy_to_set('test', {
        'version': 'test',
        'defensive_confirm_max_balance': 250.0,
        'defensive_confirm_min_price': 4350.0,
        'defensive_bounce_close_confirm_bars': 1,
        'defensive_bounce_close_require_body': True,
        'defensive_bounce_close_min_body_pct': 45.0,
        'defensive_max_entries_per_ob': 3,
        'defensive_ob_reentry_cooldown_min': 5,
        'defensive_shallow_confirm_pos_min': 1.0,
        'defensive_shallow_confirm_pos_mult': 0.0,
        'defensive_virtual_sl_confirm_bars': 1,
        'defensive_virtual_sl_hard_buffer_r': 0.25,
    })
    assert 'InpDefensiveConfirmMaxBalance=250.0' in content
    assert 'InpDefensiveConfirmMinPrice=4350.0' in content
    assert 'InpDefensiveBounceCloseConfirmBars=1' in content
    assert 'InpDefensiveBounceCloseRequireBody=true' in content
    assert 'InpDefensiveBounceCloseMinBodyPct=45.0' in content
    assert 'InpDefensiveMaxEntriesPerOB=3' in content
    assert 'InpDefensiveOBReentryCooldownMin=5' in content
    assert 'InpDefensiveShallowConfirmPosMin=1.0' in content
    assert 'InpDefensiveShallowConfirmPosMult=0.0' in content
    assert 'InpDefensiveVirtualSLConfirmBars=1' in content
    assert 'InpDefensiveVirtualSLHardBufferR=0.25' in content


def test_v98a_strategy_set():
    cfg = {
        'version': 'V98a',
        'enable_entry_engine': True,
        'enable_state_filter': True,
        'enable_scoring': True,
        'enable_decay_exit': True,
        'bounce_pct': 0.60,
        'entry_depth_pct': 0.67,
        'entry_depth_filter': False,
        'deep_entry_boost': 2.0,
        'entry_confirm_bars': 3,
        'min_score': 4,
    }
    content = strategy_to_set('v98a', cfg)
    assert 'InpEnableEntryEngine=true' in content
    assert 'InpBouncePct=0.6' in content
    assert 'InpEntryDepthPct=0.67' in content
    assert 'InpEntryDepthFilter=false' in content
    assert 'InpDeepEntryBoost=2.0' in content
    assert 'InpEntryConfirmBars=3' in content
    assert 'InpMinScore=4' in content


def test_htf_target_and_momentum_params_in_set():
    assert FLAT_MAP['enable_htf_target'] == 'InpEnableHTFTarget'
    assert FLAT_MAP['htf_target_tf'] == 'InpHTFTargetTF'
    assert FLAT_MAP['htf_target_lookback'] == 'InpHTFTargetLookback'
    assert FLAT_MAP['htf_swing_strength'] == 'InpHTFSwingStrength'
    assert FLAT_MAP['htf_min_target_r'] == 'InpHTFMinTargetR'
    assert FLAT_MAP['htf_max_target_r'] == 'InpHTFMaxTargetR'
    assert FLAT_MAP['htf_measured_move_r'] == 'InpHTFMeasuredMoveR'
    assert FLAT_MAP['htf_require_aligned'] == 'InpHTFRequireAligned'
    assert FLAT_MAP['htf_partial_r'] == 'InpHTFPartialR'
    assert FLAT_MAP['htf_partial_pct'] == 'InpHTFPartialPct'
    assert FLAT_MAP['htf_skip_dtp'] == 'InpHTFSkipDTP'
    assert FLAT_MAP['htf_skip_trail'] == 'InpHTFSkipTrail'
    assert FLAT_MAP['htf_dtp_trigger_r'] == 'InpHTFDTPTriggerR'
    assert FLAT_MAP['htf_dtp_retrace'] == 'InpHTFDTPRetrace'
    assert FLAT_MAP['htf_dtp_post_partial_retrace'] == 'InpHTFDTPPostPartialRetrace'
    assert FLAT_MAP['enable_momentum_regime'] == 'InpEnableMomentumRegime'
    assert FLAT_MAP['weak_exit_min_r'] == 'InpWeakExitMinR'
    assert FLAT_MAP['strong_dtp_retrace_mult'] == 'InpStrongDTPRetraceMult'

    content = strategy_to_set('test', {
        'version': 'test',
        'enable_htf_target': True,
        'htf_target_tf': 15,
        'htf_target_lookback': 96,
        'htf_swing_strength': 2,
        'htf_min_target_r': 2.0,
        'htf_max_target_r': 6.0,
        'htf_measured_move_r': 2.5,
        'htf_require_aligned': True,
        'htf_partial_r': 1.2,
        'htf_partial_pct': 50,
        'htf_skip_dtp': True,
        'htf_skip_trail': True,
        'htf_dtp_trigger_r': 3.0,
        'htf_dtp_retrace': 0.35,
        'htf_dtp_post_partial_retrace': 0.45,
        'enable_momentum_regime': True,
        'weak_exit_min_r': 1.2,
        'weak_body_shrink_pct': 0.8,
        'weak_wick_body_ratio': 2.0,
        'strong_momentum_bars': 4,
        'strong_min_body_growth': 1.0,
        'strong_weak_reverse_body_pct': 25.0,
        'strong_max_pullback_pct': 35.0,
        'strong_dtp_retrace_mult': 1.5,
    })
    assert 'InpEnableHTFTarget=true' in content
    assert 'InpHTFTargetTF=15' in content
    assert 'InpHTFTargetLookback=96' in content
    assert 'InpHTFSwingStrength=2' in content
    assert 'InpHTFMinTargetR=2.0' in content
    assert 'InpHTFMaxTargetR=6.0' in content
    assert 'InpHTFMeasuredMoveR=2.5' in content
    assert 'InpHTFRequireAligned=true' in content
    assert 'InpHTFPartialR=1.2' in content
    assert 'InpHTFPartialPct=50' in content
    assert 'InpHTFSkipDTP=true' in content
    assert 'InpHTFSkipTrail=true' in content
    assert 'InpHTFDTPTriggerR=3.0' in content
    assert 'InpHTFDTPRetrace=0.35' in content
    assert 'InpHTFDTPPostPartialRetrace=0.45' in content
    assert 'InpEnableMomentumRegime=true' in content
    assert 'InpWeakExitMinR=1.2' in content
    assert 'InpWeakBodyShrinkPct=0.8' in content
    assert 'InpStrongDTPRetraceMult=1.5' in content


# ── write_set_file ───────────────────────────────────────────────────

from mt5_common import write_set_file, read_agent_log, backtest_main


def test_write_set_file_creates_file():
    config = {'v99g1': {'version': 'V99g1', 'bounce_pct': 0.3}}
    with tempfile.TemporaryDirectory() as tmp:
        path = write_set_file('v99g1', config, Path(tmp))
        assert path.exists()
        assert path.name == 'v99g1.set'


def test_write_set_file_content_correct():
    config = {'v99g1': {'version': 'V99g1', 'bounce_pct': 0.3, 'breakeven_r': 1.0}}
    with tempfile.TemporaryDirectory() as tmp:
        path = write_set_file('v99g1', config, Path(tmp))
        content = path.read_text(encoding='utf-8')
        assert 'InpBouncePct=0.3' in content
        assert 'InpBreakevenR=1.0' in content
        assert 'InpVersion=V99g1' in content


# ── read_agent_log ───────────────────────────────────────────────────

def test_read_agent_log_returns_parsed():
    log_content = """testing of EA started
deal #1 buy 0.01 XAUUSDm at 3200.500 sl: 3195.000
deal #2 sell 0.01 XAUUSDm at 3210.500
final balance 215.00
50000 ticks, 1500 bars generated
"""
    with tempfile.TemporaryDirectory() as tmp:
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        log_path = Path(tmp) / f'{today}.log'
        log_path.write_text(log_content, encoding='utf-16-le')
        result = read_agent_log(Path(tmp))
        assert result is not None
        assert result['trades'] == 1
        assert result['final_balance'] == 215.0


def test_read_agent_log_missing_file(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        result = read_agent_log(Path(tmp))
        assert result is None
        captured = capsys.readouterr()
        assert '警告' in captured.out


# ── backtest_main ────────────────────────────────────────────────────

def test_windows_runner_parse_agent_log_uses_offsets():
    import importlib
    from datetime import datetime

    win_runner = importlib.import_module('mt5_backtest_win')
    today = datetime.now().strftime('%Y%m%d')
    old_segment = """BTCUSDm,M5: testing of Experts\\WaiTrade2\\WaiTrade_OB.ex5 from 2025.01.01 00:00 to 2025.01.31 00:00 started
deal #1 buy 0.01 BTCUSDm at 100000.0 sl: 99900.0
deal #2 sell 0.01 BTCUSDm at 100100.0
final balance 111.00
100 ticks, 10 bars generated
"""
    new_segment = """BTCUSDm,M5: testing of Experts\\WaiTrade2\\WaiTrade_OB.ex5 from 2025.02.01 00:00 to 2025.02.28 00:00 started
deal #3 buy 0.01 BTCUSDm at 101000.0 sl: 100900.0
deal #4 sell 0.01 BTCUSDm at 101300.0
deal #5 buy 0.01 BTCUSDm at 101500.0 sl: 101400.0
deal #6 sell 0.01 BTCUSDm at 101450.0
final balance 222.00
200 ticks, 20 bars generated
"""
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp)
        log_path = log_dir / f'{today}.log'
        log_path.write_text(old_segment, encoding='utf-16-le')
        offsets = {log_path: log_path.stat().st_size}
        with log_path.open('ab') as f:
            f.write(new_segment.encode('utf-16-le'))

        original_dirs = win_runner.TESTER_LOG_DIRS
        try:
            win_runner.TESTER_LOG_DIRS = [log_dir]
            result = win_runner.parse_agent_log(
                symbol='BTCUSDm',
                date_from='2025.02.01',
                date_to='2025.02.28',
                log_offsets=offsets,
            )
        finally:
            win_runner.TESTER_LOG_DIRS = original_dirs

        assert result is not None
        assert result['trades'] == 2
        assert result['final_balance'] == 222.0


def test_read_text_auto_tail_reads_utf16_tail():
    prefix = 'old line\n' * 2000
    suffix = 'BTCUSDm,M5: testing tail marker\nfinal balance 222.00\n'
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'large.log'
        path.write_text(prefix + suffix, encoding='utf-16-le')

        content = read_text_auto_tail(path, tail_mb=1)

        assert 'testing tail marker' in content
        assert 'final balance 222.00' in content


def test_read_text_auto_tail_falls_back_after_memory_error(monkeypatch):
    prefix = 'old line\n' * 2000
    suffix = 'BTCUSDm,M5: fallback tail marker\nfinal balance 333.00\n'
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'large.log'
        path.write_text(prefix + suffix, encoding='utf-16-le')

        def raise_memory_error(_path):
            raise MemoryError()

        monkeypatch.setattr(backtest_digest, 'read_text_auto', raise_memory_error)

        content = read_text_auto_tail(path)

        assert 'fallback tail marker' in content
        assert 'final balance 333.00' in content


def test_backtest_main_parses_days(monkeypatch):
    called_with = {}
    fake_config = {
        'defaults': {},
        'symbols': {'metals': ['XAUUSDm']},
        'backtest_defaults': {},
        'mt5_account': {},
        'v99g1': {'version': 'V99g1'},
    }

    def fake_run(strategy_names, symbols, date_from, date_to, days, config, timeout):
        called_with['strategies'] = strategy_names
        called_with['symbols'] = symbols
        called_with['days'] = days
        called_with['timeout'] = timeout

    monkeypatch.setattr('mt5_common.load_config', lambda: fake_config)
    backtest_main(
        'test',
        fake_run,
        args=['--strategy', 'v99g1', '--symbol', 'XAUUSDm', '--days', '30'],
    )
    assert called_with['strategies'] == ['v99g1']
    assert called_with['symbols'] == ['XAUUSDm']
    assert called_with['days'] == 30
    assert called_with['timeout'] == 300


def test_backtest_main_parses_from_to(monkeypatch):
    called_with = {}
    fake_config = {
        'defaults': {},
        'symbols': {'metals': ['XAUUSDm'], 'crypto': ['BTCUSDm']},
        'backtest_defaults': {},
        'mt5_account': {},
        'v99g1': {'version': 'V99g1'},
    }

    def fake_run(strategy_names, symbols, date_from, date_to, days, config, timeout):
        called_with['date_from'] = date_from
        called_with['date_to'] = date_to
        called_with['days'] = days

    monkeypatch.setattr('mt5_common.load_config', lambda: fake_config)
    backtest_main(
        'test',
        fake_run,
        args=['--strategy', 'v99g1', '--symbols', 'all', '--from', '2026.01.01', '--to', '2026.04.01'],
    )
    assert called_with['date_from'] == '2026.01.01'
    assert called_with['date_to'] == '2026.04.01'
    assert called_with['days'] == 90


def test_backtest_main_deposit_override(monkeypatch):
    called_with = {}
    fake_config = {
        'defaults': {},
        'symbols': {'crypto': ['BTCUSDm']},
        'backtest_defaults': {'deposit': 200},
        'mt5_account': {},
        'v99j1': {'version': 'V99j1', 'deposit': 200},
    }

    def fake_run(strategy_names, symbols, date_from, date_to, days, config, timeout):
        called_with['deposit'] = config['v99j1']['deposit']

    monkeypatch.setattr('mt5_common.load_config', lambda: fake_config)
    backtest_main(
        'test',
        fake_run,
        args=[
            '--strategy', 'v99j1',
            '--symbol', 'BTCUSDm',
            '--from', '2024.11.01',
            '--to', '2024.11.30',
            '--deposit', '507.58',
        ],
    )
    assert called_with['deposit'] == 507.58


def test_backtest_main_model_override(monkeypatch):
    called_with = {}
    fake_config = {
        'defaults': {},
        'symbols': {'metals': ['XAUUSDm']},
        'backtest_defaults': {'model': 0},
        'mt5_account': {},
        'v99j2': {'version': 'V99j2', 'model': 0},
    }

    def fake_run(strategy_names, symbols, date_from, date_to, days, config, timeout):
        called_with['model'] = config['v99j2']['model']

    monkeypatch.setattr('mt5_common.load_config', lambda: fake_config)
    backtest_main(
        'test',
        fake_run,
        args=[
            '--strategy', 'v99j2',
            '--symbol', 'XAUUSDm',
            '--from', '2024.11.01',
            '--to', '2024.11.30',
            '--model', '4',
        ],
    )
    assert called_with['model'] == '4'


def test_cli_parse_agent_log_prefers_matching_new_segment(monkeypatch, tmp_path):
    today = datetime(2026, 5, 21)
    log_path = tmp_path / '20260521.log'
    old_segment = (
        'CS\t0\t00:00:01\tTester\tBTCUSDm,M1: testing of Experts\\WaiTrade2\\WaiTrade_OB.ex5 '
        'from 2026.04.21 00:00 to 2026.05.21 00:00 started with inputs:\n'
        'CS\t0\t00:00:02\tTrades\tdeal #1 buy 0.01 BTCUSDm at 70000.00 done\n'
        'CS\t0\t00:00:03\tTrades\tdeal #2 sell 0.01 BTCUSDm at 70100.00 done\n'
        'CS\t0\t00:00:04\tTester\tfinal balance 210.00\n'
    )
    new_segment = (
        'CS\t0\t00:10:01\tTester\tBTCUSDm,M1: testing of Experts\\WaiTrade2\\WaiTrade_OB.ex5 '
        'from 2025.05.21 00:00 to 2026.05.21 00:00 started with inputs:\n'
        'CS\t0\t00:10:02\tTrades\tdeal #10 buy 0.01 BTCUSDm at 71000.00 done\n'
        'CS\t0\t00:10:03\tTrades\tdeal #11 sell 0.01 BTCUSDm at 70500.00 done\n'
        'CS\t0\t00:10:04\tTester\tfinal balance 150.00\n'
    )
    log_path.write_text(old_segment + new_segment, encoding='utf-16-le')
    offset = len(old_segment.encode('utf-16-le'))

    monkeypatch.setattr(cli, 'get_tester_log_paths', lambda now=None: [log_path])
    result = cli.parse_agent_log(
        symbol='BTCUSDm',
        date_from='2025.05.21',
        date_to='2026.05.21',
        log_offsets={log_path: offset},
    )

    assert result is not None
    assert result['trades'] == 1
    assert result['final_balance'] == 150.0


def test_cli_parse_agent_log_filters_expected_marker(monkeypatch, tmp_path):
    log_path = tmp_path / '20260521.log'
    old_segment = (
        'CS\t0\t00:00:01\tTester\tBTCUSDm,M1: testing of Experts\\WaiTrade2\\WaiTrade_OB.ex5 '
        'from 2026.04.21 00:00 to 2026.05.21 00:00 started with inputs:\n'
        'CS\t0\t00:00:01\tTester\t  InpVersion=V11-OLD\n'
        'CS\t0\t00:00:02\tTrades\tdeal #1 buy 0.01 BTCUSDm at 70000.00 done\n'
        'CS\t0\t00:00:03\tTrades\tdeal #2 sell 0.01 BTCUSDm at 70100.00 done\n'
        'CS\t0\t00:00:04\tTester\tfinal balance 240.00\n'
    )
    new_segment = (
        'CS\t0\t00:10:01\tTester\tBTCUSDm,M1: testing of Experts\\WaiTrade2\\WaiTrade_OB.ex5 '
        'from 2026.04.21 00:00 to 2026.05.21 00:00 started with inputs:\n'
        'CS\t0\t00:10:01\tTester\t  InpVersion=V11-NEW\n'
        'CS\t0\t00:10:02\tTrades\tdeal #10 buy 0.01 BTCUSDm at 71000.00 done\n'
        'CS\t0\t00:10:03\tTrades\tdeal #11 sell 0.01 BTCUSDm at 70500.00 done\n'
        'CS\t0\t00:10:04\tTrades\tdeal #12 buy 0.01 BTCUSDm at 70600.00 done\n'
        'CS\t0\t00:10:05\tTrades\tdeal #13 sell 0.01 BTCUSDm at 70700.00 done\n'
        'CS\t0\t00:10:06\tTester\tfinal balance 240.00\n'
    )
    log_path.write_text(old_segment + new_segment, encoding='utf-16-le')

    monkeypatch.setattr(cli, 'get_tester_log_paths', lambda now=None: [log_path])
    result = cli.parse_agent_log(
        symbol='BTCUSDm',
        date_from='2026.04.21',
        date_to='2026.05.21',
        expected_markers=['V11-OLD'],
    )

    assert result is not None
    assert result['trades'] == 1
    assert result['final_balance'] == 240.0


def test_cli_patch_terminal_ini_dates_handles_utf8(monkeypatch, tmp_path):
    mt5_root = tmp_path / 'mt5'
    config_dir = mt5_root / 'config'
    config_dir.mkdir(parents=True)
    ini_path = config_dir / 'terminal.ini'
    ini_path.write_text(
        '[Tester]\nDateRange=2\nDateFrom=1767225600\nDateTo=1779753600\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(cli, 'MT5_MAIN', str(mt5_root))

    cli.patch_terminal_ini_dates('2024.08.01', '2024.08.31')

    content = ini_path.read_text(encoding='utf-8')
    assert 'DateRange=3' in content
    assert 'DateFrom=1722470400' in content
    assert 'DateTo=1725062400' in content


def test_cli_build_report_path_includes_window_tokens():
    report_path = cli.build_report_path(
        'v11j2',
        '2025.05.21',
        '2026.05.21',
        now=datetime(2026, 5, 21),
    )
    assert report_path.name == 'v11j2_20250521_20260521_20260521.txt'


def test_win_cli_build_report_path_includes_window_tokens():
    report_path = win_cli.build_report_path(
        'v11j2',
        '2024.11.01',
        '2024.11.30',
        now=datetime(2026, 5, 24),
    )
    assert report_path.name == 'v11j2_20241101_20241130_20260524.txt'


# ── backtest digest ──────────────────────────────────────────────────

SAMPLE_REPORT = """
=====================================================================
MT5 Strategy Tester 回测报告 — V11_BTC_M5_R21
日期: 2026.03.22 ~ 2026.05.21 (60天) | 资金: $200 | 杠杆: 1:2000
=====================================================================

品种         交易  日均  胜率   盈亏比  净R     余额
---------------------------------------------------------------------
BTCUSDm      2     0.0   50.0   %1.20    N/A     $240.00
---------------------------------------------------------------------
合计          2     0.0   50.0   %        N/A     $240.00
=====================================================================
"""

SAMPLE_SEGMENT = """CS\t0\t00:14:08.437\tTester\tBTCUSDm,M1: testing of Experts\\WaiTrade2\\WaiTrade_OB.ex5 from 2026.03.22 00:00 to 2026.05.21 00:00 started with inputs:
CS\t0\t00:14:09.534\tWaiTrade_OB (BTCUSDm,M1)\t2026.03.24 11:41:01   ENTRY_DIAG stage=entry_engine ticket=0 dir=-1 hour=11 ob_age=9 touch=278 strength=5.00 ds=1.00 fresh=0 cont=0 h1=1 deep=1 htf=0 bounce_sec=27 bounce_ob=0.276 confirm_pos=-0.791 touch=71258.60 confirm=71238.77 risk_atr=1.68 spread_risk=0.065 pos_mult=0.52 score=4 entry=71224.77 sl=71441.55
CS\t0\t00:14:09.536\tTrade\t2026.03.24 11:41:01   market sell 0.01 BTCUSDm sl: 71441.55 tp: 71116.95 (71224.77 / 71238.77)
CS\t0\t00:14:09.537\tTrades\t2026.03.24 11:41:01   deal #2 sell 0.01 BTCUSDm at 71224.77 done (based on order #2)
CS\t0\t00:14:09.538\tWaiTrade_OB (BTCUSDm,M1)\t2026.03.24 11:41:01   开仓成功: WT V11-R10-Q6K S x0.5 ticket=2 price=71224.77 lot=0.01 bounce_sec=27 bounce_ob=0.276 confirm_pos=-0.791 touch=71258.60 confirm=71238.77
CS\t0\t00:14:09.541\tTrade\t2026.03.24 11:53:06   take profit triggered #2 sell 0.01 BTCUSDm 71224.77 sl: 71441.55 tp: 71116.95 [#3 buy 0.01 BTCUSDm at 71116.95]
CS\t0\t00:14:09.541\tTrades\t2026.03.24 11:53:06   deal #3 buy 0.01 BTCUSDm at 71115.61 done (based on order #3)
CS\t0\t00:14:09.541\tWaiTrade_OB (BTCUSDm,M1)\t2026.03.24 11:53:06   POSITION_GONE_DIAG ticket=2 dir=-1 entry=71224.77 sl_initial=71441.55 peak_r=0.49 raw_peak_r=0.49 dtp_peak_r=0.00 open_bar=717 last_sl= be=false trail=0 partial=false dtp_partial=false deep=true htf=false rev=false addon=false
CS\t0\t00:14:09.551\tWaiTrade_OB (BTCUSDm,M1)\t2026.03.24 13:33:09   ENTRY_DIAG stage=entry_engine ticket=0 dir=1 hour=13 ob_age=4 touch=119 strength=3.81 ds=1.00 fresh=0 cont=1 h1=1 deep=1 htf=0 bounce_sec=0 bounce_ob=0.281 confirm_pos=-0.456 touch=70778.84 confirm=70751.04 risk_atr=1.74 spread_risk=0.051 pos_mult=13.50 score=4 entry=70737.04 sl=71013.26
CS\t0\t00:14:09.551\tTrade\t2026.03.24 13:33:09   market buy 0.27 BTCUSDm sl: 71013.26 tp: 70588.60 (70737.04 / 70751.04)
CS\t0\t00:14:09.551\tTrades\t2026.03.24 13:33:09   deal #4 buy 0.27 BTCUSDm at 70737.04 done (based on order #4)
CS\t0\t00:14:09.551\tWaiTrade_OB (BTCUSDm,M1)\t2026.03.24 13:33:09   开仓成功: WT V11-R10-Q6K B SWP x13.5 ticket=4 price=70737.04 lot=0.27 bounce_sec=0 bounce_ob=0.281 confirm_pos=-0.456 touch=70778.84 confirm=70751.04
CS\t0\t00:14:09.553\tTrade\t2026.03.24 13:38:42   stop loss triggered #4 buy 0.27 BTCUSDm 70737.04 sl: 71013.26 tp: 70588.60 [#5 sell 0.27 BTCUSDm at 70588.60]
CS\t0\t00:14:09.553\tTrades\t2026.03.24 13:38:42   deal #5 sell 0.27 BTCUSDm at 70588.04 done (based on order #5)
CS\t0\t00:14:09.553\tWaiTrade_OB (BTCUSDm,M1)\t2026.03.24 13:38:42   POSITION_GONE_DIAG ticket=4 dir=1 entry=70737.04 sl_initial=71013.26 peak_r=0.52 raw_peak_r=0.52 dtp_peak_r=0.00 open_bar=739 last_sl= be=false trail=0 partial=false dtp_partial=false deep=true htf=false rev=false addon=false
CS\t0\t00:14:09.554\tTester\tfinal balance 240.00
CS\t0\t00:14:09.554\tTester\t1000 ticks, 200 bars generated
"""

SAMPLE_STOP_OUT_SEGMENT = """CS\t0\t00:14:08.437\tTester\tBTCUSDm,M1: testing of Experts\\WaiTrade2\\WaiTrade_OB.ex5 from 2024.05.31 00:00 to 2026.05.21 00:00 started with inputs:
CS\t0\t00:14:09.554\tTester\tfinal balance -0.86 USD
CS\t3\t00:14:09.555\tTester\tstop out occurred on 28% of testing interval
"""


def test_parse_backtest_report_content_extracts_meta():
    parsed = parse_backtest_report_content(SAMPLE_REPORT)
    assert parsed['strategy_name'] == 'V11_BTC_M5_R21'
    assert parsed['date_from'] == '2026.03.22'
    assert parsed['date_to'] == '2026.05.21'
    assert parsed['model'] is None
    assert parsed['symbols'][0]['symbol'] == 'BTCUSDm'
    assert parsed['symbols'][0]['final_balance'] == 240.0


def test_split_agent_log_segments_extracts_segment_meta():
    segments = split_agent_log_segments(SAMPLE_SEGMENT)
    assert len(segments) == 1
    assert segments[0]['meta']['symbol'] == 'BTCUSDm'
    assert segments[0]['meta']['date_from'] == '2026.03.22'
    assert segments[0]['meta']['date_to'] == '2026.05.21'


def test_find_matching_log_segment_matches_balance():
    segment = find_matching_log_segment(SAMPLE_SEGMENT, 'BTCUSDm', '2026.03.22', '2026.05.21', 240.0)
    assert segment is not None
    assert segment['meta']['symbol'] == 'BTCUSDm'


def test_find_matching_log_segment_prefers_latest_equal_balance():
    old_segment = SAMPLE_SEGMENT
    new_segment = SAMPLE_SEGMENT.replace('V11-R10-Q6K', 'V11-R94-C2S2ML10')
    content = old_segment + '\n' + new_segment

    segment = find_matching_log_segment(content, 'BTCUSDm', '2026.03.22', '2026.05.21', 240.0)

    assert segment is not None
    assert any('V11-R94-C2S2ML10' in line for line in segment['lines'])


def test_find_matching_log_segment_filters_expected_marker():
    old_segment = SAMPLE_SEGMENT
    new_segment = SAMPLE_SEGMENT.replace('V11-R10-Q6K', 'V11-R94-C2S2ML10')
    content = old_segment + '\n' + new_segment

    segment = find_matching_log_segment(
        content,
        'BTCUSDm',
        '2026.03.22',
        '2026.05.21',
        240.0,
        expected_markers=['V11-R10-Q6K'],
    )

    assert segment is not None
    assert any('V11-R10-Q6K' in line for line in segment['lines'])
    assert not any('V11-R94-C2S2ML10' in line for line in segment['lines'])


def test_parse_agent_log_segment_details_extracts_trades():
    segment = split_agent_log_segments(SAMPLE_SEGMENT)[0]
    details = parse_agent_log_segment_details(segment['lines'], 'BTCUSDm')
    assert details['final_balance'] == 240.0
    assert len(details['trades']) == 2
    first = details['trades'][0]
    second = details['trades'][1]
    assert first['ticket'] == 2
    assert first['reason'] == 'TP'
    assert first['dir'] == 'sell'
    assert first['signal_type'] == 'ob'
    assert round(first['r'], 3) > 0
    assert second['ticket'] == 4
    assert second['reason'] == 'SL'
    assert second['dir'] == 'buy'
    assert second['signal_type'] == 'sweep'
    assert second['risk'] == abs(second['entry'] - second['initial_sl'])


def test_signal_type_from_comment_parses_distinct_tags():
    assert _signal_type_from_comment('WT V11 B x1.0') == 'ob'
    assert _signal_type_from_comment('WT V11 B SWP x1.0') == 'sweep'
    assert _signal_type_from_comment('WT V11 B LSWP SWP x1.0') == 'loose_sweep'
    assert _signal_type_from_comment('WT V11 B RB x1.0') == 'range'
    assert _signal_type_from_comment('WT V11 B HTFPB x1.0') == 'htf_pullback'


def test_build_digest_data_combines_summary_and_details():
    report_data, digests = build_digest_data(SAMPLE_REPORT, SAMPLE_SEGMENT)
    assert report_data['strategy_name'] == 'V11_BTC_M5_R21'
    assert len(digests) == 1
    assert digests[0]['trade_stats']['count'] == 2
    assert len(digests[0]['best_trades']) >= 1
    assert len(digests[0]['worst_trades']) >= 1


def test_render_digest_markdown_contains_sections():
    report_data, digests = build_digest_data(SAMPLE_REPORT, SAMPLE_SEGMENT)
    markdown = render_digest_markdown(report_data, digests, Path('sample.txt'), Path('20260521.log'))
    assert '# 回测提炼报告 — V11_BTC_M5_R21' in markdown
    assert '## 核心摘要' in markdown
    assert '## 逐单归因 — BTCUSDm' in markdown
    assert '### 月度表现' in markdown
    assert '### 贡献簇' in markdown
    assert '### 判别因子' in markdown
    assert 'Stopout' in markdown


def test_parse_agent_log_segment_details_extracts_stopout():
    segment = split_agent_log_segments(SAMPLE_STOP_OUT_SEGMENT)[0]
    details = parse_agent_log_segment_details(segment['lines'], 'BTCUSDm')
    assert details['stopout'] is True
    assert details['stopout_pct'] == 28


def test_build_monthly_stats_uses_deposit_baseline():
    details = {
        'trades': [
            {'time': '2026-03-01 00:00:00', 'pnl_proxy': 10.0, 'r': 1.0},
            {'time': '2026-03-15 00:00:00', 'pnl_proxy': 10.0, 'r': 1.0},
            {'time': '2026-04-01 00:00:00', 'pnl_proxy': -5.0, 'r': -0.5},
            {'time': '2026-04-15 00:00:00', 'pnl_proxy': 45.0, 'r': 4.5},
        ]
    }
    monthly = build_monthly_stats({'final_balance': 260.0}, details, deposit=200.0)
    assert [row['month'] for row in monthly] == ['2026-03', '2026-04']
    assert monthly[0]['start_balance'] == 200.0
    assert monthly[0]['end_balance'] == 220.0
    assert monthly[1]['start_balance'] == 220.0
    assert monthly[1]['end_balance'] == 260.0
    assert monthly[1]['profit'] == 40.0


def test_write_trade_csv_exports_rows():
    report_data, digests = build_digest_data(SAMPLE_REPORT, SAMPLE_SEGMENT)
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / 'trades.csv'
        write_trade_csv(csv_path, digests)
        content = csv_path.read_text(encoding='utf-8')
        assert 'ticket,time,date,hour,symbol,dir,comment,signal_type' in content
        assert 'BTCUSDm' in content
        assert 'sweep' in content
        assert '71224.77' in content
