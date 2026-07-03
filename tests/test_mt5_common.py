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
    read_text_auto_tail, expected_log_markers, _extract_date_token,
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
        'monthly_max_entries': 12,
    }
    content = strategy_to_set('v96b', cfg)
    assert 'InpBouncePct=0.3' in content
    assert 'InpBreakevenR=0.2' in content
    assert 'InpMonthlyMaxEntries=12' in content
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


def test_bd07_noise_params_in_flat_map():
    assert FLAT_MAP['enable_tick_noise_gate'] == 'InpEnableTickNoiseGate'
    assert FLAT_MAP['tick_noise_gate_lookback'] == 'InpTickNoiseGateLookback'
    assert FLAT_MAP['tick_noise_gate_min_dir_ratio'] == 'InpTickNoiseGateMinDirRatio'
    assert FLAT_MAP['tick_noise_gate_max_range_atr'] == 'InpTickNoiseGateMaxRangeATR'
    assert FLAT_MAP['enable_dynamic_spread'] == 'InpEnableDynamicSpread'
    assert FLAT_MAP['min_sl_spread_mult'] == 'InpMinSLSpreadMult'
    assert FLAT_MAP['ob_touch_confirm_ticks'] == 'InpOBTouchConfirmTicks'


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
    assert FLAT_MAP['btc_allow_monthly_profit_target_stop'] == 'InpBTCAllowMonthlyProfitTargetStop'


def test_strategy_to_set_v11_btc_profile_extended_params():
    cfg = {
        'version': 'V11',
        'btc_enable_state_filter': True,
        'btc_mfe_fail_exit_r': -0.1,
        'btc_no_mfe_exit_bars': 3,
        'btc_htf_net_push_tf': 60,
        'btc_dtp_reset_peak_after_partial': False,
        'btc_allow_monthly_profit_target_stop': True,
    }
    content = strategy_to_set('v11', cfg)
    assert 'InpBTCEnableStateFilter=true' in content
    assert 'InpBTCMFEFailExitR=-0.1' in content
    assert 'InpBTCNoMFEExitBars=3' in content
    assert 'InpBTCHTFNetPushTF=60' in content
    assert 'InpBTCDTPResetPeakAfterPartial=false' in content
    assert 'InpBTCAllowMonthlyProfitTargetStop=true' in content


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
    assert FLAT_MAP['entry_depth_signal_types'] == 'InpEntryDepthSignalTypes'
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
    assert FLAT_MAP['enable_entry_structure_confirm'] == 'InpEnableEntryStructureConfirm'
    assert FLAT_MAP['entry_structure_confirm_families'] == 'InpEntryStructureConfirmFamilies'
    assert FLAT_MAP['entry_structure_confirm_ob_directions'] == 'InpEntryStructureConfirmOBDirections'
    assert FLAT_MAP['entry_structure_confirm_tf'] == 'InpEntryStructureConfirmTF'
    assert FLAT_MAP['entry_structure_lookback_bars'] == 'InpEntryStructureLookbackBars'
    assert FLAT_MAP['entry_structure_pivot_bars'] == 'InpEntryStructurePivotBars'
    assert FLAT_MAP['entry_structure_break_buffer_atr'] == 'InpEntryStructureBreakBufferATR'
    assert FLAT_MAP['entry_structure_require_break'] == 'InpEntryStructureRequireBreak'
    assert FLAT_MAP['entry_structure_min_net_atr'] == 'InpEntryStructureMinNetATR'
    assert FLAT_MAP['entry_structure_net_bars'] == 'InpEntryStructureNetBars'
    assert FLAT_MAP['entry_structure_reverse_body_atr'] == 'InpEntryStructureReverseBodyATR'
    assert FLAT_MAP['enable_entry_htf_shape_filter'] == 'InpEnableEntryHTFShapeFilter'
    assert FLAT_MAP['entry_htf_shape_tf'] == 'InpEntryHTFShapeTF'
    assert FLAT_MAP['entry_htf_shape_bars'] == 'InpEntryHTFShapeBars'
    assert FLAT_MAP['entry_htf_max_same_body'] == 'InpEntryHTFMaxSameBody'
    assert FLAT_MAP['entry_htf_max_range_pos'] == 'InpEntryHTFMaxRangePos'
    assert FLAT_MAP['enable_entry_exhaustion_filter'] == 'InpEnableEntryExhaustionFilter'
    assert FLAT_MAP['entry_exhaustion_tf'] == 'InpEntryExhaustionTF'
    assert FLAT_MAP['entry_exhaustion_bars'] == 'InpEntryExhaustionBars'
    assert FLAT_MAP['entry_exhaustion_max_net'] == 'InpEntryExhaustionMaxNet'
    assert FLAT_MAP['enable_entry_context_filter'] == 'InpEnableEntryContextFilter'
    assert FLAT_MAP['entry_context_tf'] == 'InpEntryContextTF'
    assert FLAT_MAP['entry_context_bars'] == 'InpEntryContextBars'
    assert FLAT_MAP['entry_context_min_net'] == 'InpEntryContextMinNet'
    assert FLAT_MAP['entry_context_max_net'] == 'InpEntryContextMaxNet'
    assert FLAT_MAP['entry_context_min_efficiency'] == 'InpEntryContextMinEfficiency'
    assert FLAT_MAP['entry_context_tf2'] == 'InpEntryContextTF2'
    assert FLAT_MAP['entry_context_bars2'] == 'InpEntryContextBars2'
    assert FLAT_MAP['entry_context_min_net2'] == 'InpEntryContextMinNet2'
    assert FLAT_MAP['entry_context_max_net2'] == 'InpEntryContextMaxNet2'
    assert FLAT_MAP['entry_context_min_efficiency2'] == 'InpEntryContextMinEfficiency2'
    assert FLAT_MAP['enable_entry_dir_context_filter'] == 'InpEnableEntryDirContextFilter'
    assert FLAT_MAP['entry_dir_context_apply_buy'] == 'InpEntryDirContextApplyBuy'
    assert FLAT_MAP['entry_dir_context_apply_sell'] == 'InpEntryDirContextApplySell'
    assert FLAT_MAP['entry_dir_context_tf'] == 'InpEntryDirContextTF'
    assert FLAT_MAP['entry_dir_context_bars'] == 'InpEntryDirContextBars'
    assert FLAT_MAP['entry_dir_context_min_net'] == 'InpEntryDirContextMinNet'
    assert FLAT_MAP['entry_dir_context_max_net'] == 'InpEntryDirContextMaxNet'
    assert FLAT_MAP['entry_dir_context_tf2'] == 'InpEntryDirContextTF2'
    assert FLAT_MAP['entry_dir_context_bars2'] == 'InpEntryDirContextBars2'
    assert FLAT_MAP['entry_dir_context_min_net2'] == 'InpEntryDirContextMinNet2'
    assert FLAT_MAP['entry_dir_context_max_net2'] == 'InpEntryDirContextMaxNet2'
    assert FLAT_MAP['enable_swp_continuation_confirm'] == 'InpEnableSWPContinuationConfirm'
    assert FLAT_MAP['swp_continuation_tf'] == 'InpSWPContinuationTF'
    assert FLAT_MAP['swp_continuation_bars'] == 'InpSWPContinuationBars'
    assert FLAT_MAP['swp_continuation_min_net_atr'] == 'InpSWPContinuationMinNetATR'
    assert FLAT_MAP['swp_continuation_reverse_body_atr'] == 'InpSWPContinuationReverseBodyATR'
    assert FLAT_MAP['swp_continuation_break_buffer_atr'] == 'InpSWPContinuationBreakBufferATR'
    assert FLAT_MAP['swp_continuation_fail_mult'] == 'InpSWPContinuationFailMult'
    assert 'range_apply_aligned_signal' not in FLAT_MAP
    assert 'enable_range_reaction' not in FLAT_MAP
    assert 'range_reaction_confirm_tf' not in FLAT_MAP
    assert 'range_reaction_cooldown_bars' not in FLAT_MAP


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


def test_entry_structure_confirm_params_in_set():
    content = strategy_to_set('test', {
        'version': 'test',
        'enable_entry_structure_confirm': True,
        'entry_structure_confirm_families': 'SWP,OB',
        'entry_structure_confirm_ob_directions': 'SELL',
        'entry_structure_confirm_tf': 5,
        'entry_structure_lookback_bars': 30,
        'entry_structure_pivot_bars': 2,
        'entry_structure_break_buffer_atr': 0.05,
        'entry_structure_require_break': False,
        'entry_structure_min_net_atr': 0.18,
        'entry_structure_net_bars': 3,
        'entry_structure_reverse_body_atr': 0.5,
        'enable_entry_htf_shape_filter': True,
        'entry_htf_shape_tf': 240,
        'entry_htf_shape_bars': 4,
        'entry_htf_max_same_body': 667.0,
        'entry_htf_max_range_pos': 0.7257,
        'enable_entry_exhaustion_filter': True,
        'entry_exhaustion_tf': 5,
        'entry_exhaustion_bars': 6,
        'entry_exhaustion_max_net': 52.04,
        'enable_entry_context_filter': True,
        'entry_context_tf': 60,
        'entry_context_bars': 6,
        'entry_context_min_net': -999.0,
        'entry_context_max_net': 999.0,
        'entry_context_min_efficiency': 0.08,
        'entry_context_tf2': 5,
        'entry_context_bars2': 12,
        'entry_context_min_net2': -280.9,
        'entry_context_max_net2': 999999.0,
        'entry_context_min_efficiency2': 0.0,
        'enable_entry_dir_context_filter': True,
        'entry_dir_context_apply_buy': True,
        'entry_dir_context_apply_sell': False,
        'entry_dir_context_tf': 15,
        'entry_dir_context_bars': 8,
        'entry_dir_context_min_net': -251.9,
        'entry_dir_context_max_net': 999999.0,
        'entry_dir_context_tf2': 5,
        'entry_dir_context_bars2': 12,
        'entry_dir_context_min_net2': -699.3,
        'entry_dir_context_max_net2': 999999.0,
        'enable_swp_continuation_confirm': True,
        'swp_continuation_tf': 5,
        'swp_continuation_bars': 2,
        'swp_continuation_min_net_atr': 0.2,
        'swp_continuation_reverse_body_atr': 0.45,
        'swp_continuation_break_buffer_atr': 0.05,
        'swp_continuation_fail_mult': 0.3,
    })
    assert 'InpEnableEntryStructureConfirm=true' in content
    assert 'InpEntryStructureConfirmFamilies=SWP,OB' in content
    assert 'InpEntryStructureConfirmOBDirections=SELL' in content
    assert 'InpEntryStructureConfirmTF=5' in content
    assert 'InpEntryStructureLookbackBars=30' in content
    assert 'InpEntryStructurePivotBars=2' in content
    assert 'InpEntryStructureBreakBufferATR=0.05' in content
    assert 'InpEntryStructureRequireBreak=false' in content
    assert 'InpEntryStructureMinNetATR=0.18' in content
    assert 'InpEntryStructureNetBars=3' in content
    assert 'InpEntryStructureReverseBodyATR=0.5' in content
    assert 'InpEnableEntryHTFShapeFilter=true' in content
    assert 'InpEntryHTFShapeTF=240' in content
    assert 'InpEntryHTFShapeBars=4' in content
    assert 'InpEntryHTFMaxSameBody=667.0' in content
    assert 'InpEntryHTFMaxRangePos=0.7257' in content
    assert 'InpEnableEntryExhaustionFilter=true' in content
    assert 'InpEntryExhaustionTF=5' in content
    assert 'InpEntryExhaustionBars=6' in content
    assert 'InpEntryExhaustionMaxNet=52.04' in content
    assert 'InpEnableEntryContextFilter=true' in content
    assert 'InpEntryContextTF=60' in content
    assert 'InpEntryContextBars=6' in content
    assert 'InpEntryContextMinNet=-999.0' in content
    assert 'InpEntryContextMaxNet=999.0' in content
    assert 'InpEntryContextMinEfficiency=0.08' in content
    assert 'InpEntryContextTF2=5' in content
    assert 'InpEntryContextBars2=12' in content
    assert 'InpEntryContextMinNet2=-280.9' in content
    assert 'InpEntryContextMaxNet2=999999.0' in content
    assert 'InpEntryContextMinEfficiency2=0.0' in content
    assert 'InpEnableEntryDirContextFilter=true' in content
    assert 'InpEntryDirContextApplyBuy=true' in content
    assert 'InpEntryDirContextApplySell=false' in content
    assert 'InpEntryDirContextTF=15' in content
    assert 'InpEntryDirContextBars=8' in content
    assert 'InpEntryDirContextMinNet=-251.9' in content
    assert 'InpEntryDirContextMaxNet=999999.0' in content
    assert 'InpEntryDirContextTF2=5' in content
    assert 'InpEntryDirContextBars2=12' in content
    assert 'InpEntryDirContextMinNet2=-699.3' in content
    assert 'InpEntryDirContextMaxNet2=999999.0' in content
    assert 'InpEnableSWPContinuationConfirm=true' in content
    assert 'InpSWPContinuationTF=5' in content
    assert 'InpSWPContinuationBars=2' in content
    assert 'InpSWPContinuationMinNetATR=0.2' in content
    assert 'InpSWPContinuationReverseBodyATR=0.45' in content
    assert 'InpSWPContinuationBreakBufferATR=0.05' in content
    assert 'InpSWPContinuationFailMult=0.3' in content


def test_failure_reentry_structure_params_in_set():
    assert FLAT_MAP['failure_reentry_require_structure_break'] == 'InpFailureReentryRequireStructureBreak'
    assert FLAT_MAP['failure_reentry_structure_lookback_bars'] == 'InpFailureReentryStructureLookbackBars'
    assert FLAT_MAP['failure_reentry_structure_pivot_bars'] == 'InpFailureReentryStructurePivotBars'
    assert FLAT_MAP['failure_reentry_break_buffer_atr'] == 'InpFailureReentryBreakBufferATR'
    assert FLAT_MAP['failure_reentry_reverse_body_atr'] == 'InpFailureReentryReverseBodyATR'
    assert FLAT_MAP['failure_reentry_block_strong_reverse'] == 'InpFailureReentryBlockStrongReverse'
    assert FLAT_MAP['failure_reentry_block_reverse_break'] == 'InpFailureReentryBlockReverseBreak'

    content = strategy_to_set('test', {
        'version': 'test',
        'failure_reentry_require_structure_break': True,
        'failure_reentry_structure_lookback_bars': 30,
        'failure_reentry_structure_pivot_bars': 2,
        'failure_reentry_break_buffer_atr': 0.05,
        'failure_reentry_reverse_body_atr': 0.5,
        'failure_reentry_block_strong_reverse': True,
        'failure_reentry_block_reverse_break': True,
    })
    assert 'InpFailureReentryRequireStructureBreak=true' in content
    assert 'InpFailureReentryStructureLookbackBars=30' in content
    assert 'InpFailureReentryStructurePivotBars=2' in content
    assert 'InpFailureReentryBreakBufferATR=0.05' in content
    assert 'InpFailureReentryReverseBodyATR=0.5' in content
    assert 'InpFailureReentryBlockStrongReverse=true' in content
    assert 'InpFailureReentryBlockReverseBreak=true' in content


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
    assert FLAT_MAP['enable_failure_reentry_confirm'] == 'InpEnableFailureReentryConfirm'
    assert FLAT_MAP['failure_reentry_confirm_losses'] == 'InpFailureReentryConfirmLosses'
    assert FLAT_MAP['failure_reentry_confirm_tf'] == 'InpFailureReentryConfirmTF'
    assert FLAT_MAP['failure_reentry_confirm_bars'] == 'InpFailureReentryConfirmBars'
    assert FLAT_MAP['failure_reentry_confirm_min_atr'] == 'InpFailureReentryConfirmMinATR'
    assert FLAT_MAP['failure_reentry_confirm_max_age_min'] == 'InpFailureReentryConfirmMaxAgeMin'
    assert FLAT_MAP['failure_reentry_block_min'] == 'InpFailureReentryBlockMin'
    assert FLAT_MAP['failure_reentry_block_ob_only'] == 'InpFailureReentryBlockOBOnly'
    assert FLAT_MAP['failure_reentry_block_min_pos_mult'] == 'InpFailureReentryBlockMinPosMult'
    assert FLAT_MAP['post_win_cooldown_min_profit'] == 'InpPostWinCooldownMinProfit'
    assert FLAT_MAP['post_win_cooldown_min'] == 'InpPostWinCooldownMin'
    assert FLAT_MAP['post_win_cooldown_families'] == 'InpPostWinCooldownFamilies'
    assert FLAT_MAP['post_win_cooldown_same_direction'] == 'InpPostWinCooldownSameDirection'
    assert FLAT_MAP['post_win_cooldown_cross_family'] == 'InpPostWinCooldownCrossFamily'
    assert FLAT_MAP['post_win_cooldown_block_entries'] == 'InpPostWinCooldownBlockEntries'
    assert FLAT_MAP['post_win_cooldown_max_lot_size'] == 'InpPostWinCooldownMaxLotSize'
    assert FLAT_MAP['post_win_cooldown_require_continuation'] == 'InpPostWinCooldownRequireContinuation'
    assert FLAT_MAP['post_win_cooldown_continuation_tf'] == 'InpPostWinCooldownContinuationTF'
    assert FLAT_MAP['post_win_cooldown_continuation_bars'] == 'InpPostWinCooldownContinuationBars'
    assert FLAT_MAP['post_win_cooldown_continuation_min_net_atr'] == 'InpPostWinCooldownContinuationMinNetATR'
    assert FLAT_MAP['post_win_cooldown_continuation_require_break'] == 'InpPostWinCooldownContinuationRequireBreak'
    assert FLAT_MAP['post_win_cooldown_continuation_break_buffer_atr'] == 'InpPostWinCooldownContinuationBreakBufferATR'
    assert FLAT_MAP['post_win_cooldown_continuation_reverse_body_atr'] == 'InpPostWinCooldownContinuationReverseBodyATR'
    assert FLAT_MAP['failure_reentry_clear_win_r'] == 'InpFailureReentryClearWinR'
    assert FLAT_MAP['failure_reentry_record_passive_loss'] == 'InpFailureReentryRecordPassiveLoss'
    assert FLAT_MAP['failure_reentry_passive_loss_max_peak_r'] == 'InpFailureReentryPassiveLossMaxPeakR'
    assert FLAT_MAP['failure_reentry_family_filter'] == 'InpFailureReentryFamilyFilter'
    assert FLAT_MAP['enable_failure_reverse'] == 'InpEnableFailureReverse'
    assert FLAT_MAP['reverse_on_early_loss'] == 'InpReverseOnEarlyLoss'
    assert FLAT_MAP['reverse_on_mfe_fail'] == 'InpReverseOnMFEFail'
    assert FLAT_MAP['reverse_on_no_mfe'] == 'InpReverseOnNoMFE'
    assert FLAT_MAP['failure_reverse_risk_mult'] == 'InpFailureReverseRiskMult'
    assert FLAT_MAP['failure_reverse_lot_mult'] == 'InpFailureReverseLotMult'
    assert FLAT_MAP['failure_reverse_tp_r'] == 'InpFailureReverseTPR'
    assert FLAT_MAP['failure_reverse_allow_chain'] == 'InpFailureReverseAllowChain'
    assert 'failure_reentry_price_tolerance' not in FLAT_MAP
    assert 'failure_reentry_price_cluster_block_min' not in FLAT_MAP
    content = strategy_to_set('test', {
        'version': 'test',
        'early_loss_cut_r': 0.35,
        'mfe_fail_min_r': 0.5,
        'mfe_fail_exit_r': -0.1,
        'no_mfe_exit_bars': 3,
        'no_mfe_min_peak_r': 0.15,
        'no_mfe_exit_r': -0.2,
        'enable_failure_reentry_confirm': True,
        'failure_reentry_confirm_losses': 2,
        'failure_reentry_confirm_tf': 5,
        'failure_reentry_confirm_bars': 3,
        'failure_reentry_confirm_min_atr': 0.18,
        'failure_reentry_confirm_max_age_min': 90.0,
        'failure_reentry_block_min': 30.0,
        'failure_reentry_block_ob_only': True,
        'failure_reentry_block_min_pos_mult': 0.5,
        'failure_reentry_clear_win_r': 1.2,
        'failure_reentry_record_passive_loss': True,
        'failure_reentry_passive_loss_max_peak_r': 0.4,
        'failure_reentry_family_filter': 'SWP,OB',
        'post_win_cooldown_min_profit': 100.0,
        'post_win_cooldown_min': 60,
        'post_win_cooldown_families': 'BOS,OB',
        'post_win_cooldown_same_direction': True,
        'post_win_cooldown_cross_family': True,
        'post_win_cooldown_block_entries': False,
        'post_win_cooldown_max_lot_size': 0.08,
        'post_win_cooldown_require_continuation': True,
        'post_win_cooldown_continuation_tf': 15,
        'post_win_cooldown_continuation_bars': 3,
        'post_win_cooldown_continuation_min_net_atr': 0.25,
        'post_win_cooldown_continuation_require_break': False,
        'post_win_cooldown_continuation_break_buffer_atr': 0.08,
        'post_win_cooldown_continuation_reverse_body_atr': 0.55,
    })
    assert 'InpEarlyLossCutR=0.35' in content
    assert 'InpMFEFailMinR=0.5' in content
    assert 'InpMFEFailExitR=-0.1' in content
    assert 'InpNoMFEExitBars=3' in content
    assert 'InpNoMFEMinPeakR=0.15' in content
    assert 'InpNoMFEExitR=-0.2' in content
    assert 'InpEnableFailureReentryConfirm=true' in content
    assert 'InpFailureReentryConfirmLosses=2' in content
    assert 'InpFailureReentryConfirmTF=5' in content
    assert 'InpFailureReentryConfirmBars=3' in content
    assert 'InpFailureReentryConfirmMinATR=0.18' in content
    assert 'InpFailureReentryConfirmMaxAgeMin=90.0' in content
    assert 'InpFailureReentryBlockMin=30.0' in content
    assert 'InpFailureReentryBlockOBOnly=true' in content
    assert 'InpFailureReentryBlockMinPosMult=0.5' in content
    assert 'InpFailureReentryClearWinR=1.2' in content
    assert 'InpFailureReentryRecordPassiveLoss=true' in content
    assert 'InpFailureReentryPassiveLossMaxPeakR=0.4' in content
    assert 'InpFailureReentryFamilyFilter=SWP,OB' in content
    assert 'InpPostWinCooldownMinProfit=100.0' in content
    assert 'InpPostWinCooldownMin=60' in content
    assert 'InpPostWinCooldownFamilies=BOS,OB' in content
    assert 'InpPostWinCooldownSameDirection=true' in content
    assert 'InpPostWinCooldownCrossFamily=true' in content
    assert 'InpPostWinCooldownBlockEntries=false' in content
    assert 'InpPostWinCooldownMaxLotSize=0.08' in content
    assert 'InpPostWinCooldownRequireContinuation=true' in content
    assert 'InpPostWinCooldownContinuationTF=15' in content
    assert 'InpPostWinCooldownContinuationBars=3' in content
    assert 'InpPostWinCooldownContinuationMinNetATR=0.25' in content
    assert 'InpPostWinCooldownContinuationRequireBreak=false' in content
    assert 'InpPostWinCooldownContinuationBreakBufferATR=0.08' in content
    assert 'InpPostWinCooldownContinuationReverseBodyATR=0.55' in content


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
        'strong_addon_use_risk_lot': True,
        'strong_addon_risk_percent': 5.0,
        'strong_addon_max_lot_size': 0.8,
        'strong_addon_families': 'BOS,HTFPB',
        'strong_addon_directions': 'buy',
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
    assert 'InpStrongAddOnUseRiskLot=true' in content
    assert 'InpStrongAddOnRiskPercent=5.0' in content
    assert 'InpStrongAddOnMaxLotSize=0.8' in content
    assert 'InpStrongAddOnFamilies=BOS,HTFPB' in content
    assert 'InpStrongAddOnDirections=buy' in content


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
    assert FLAT_MAP['htf_pullback_min_day'] == 'InpHTFPullbackMinDay'
    assert FLAT_MAP['htf_pullback_max_monthly_entries'] == 'InpHTFPullbackMaxMonthlyEntries'

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
        'htf_pullback_min_day': 10,
        'htf_pullback_max_monthly_entries': 2,
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
    assert 'InpHTFPullbackMinDay=10' in content
    assert 'InpHTFPullbackMaxMonthlyEntries=2' in content
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
    assert FLAT_MAP['bounce_close_min_body_pct'] == 'InpBounceCloseMinBodyPct'
    assert FLAT_MAP['bounce_close_weak_body_pct'] == 'InpBounceCloseWeakBodyPct'
    assert FLAT_MAP['bounce_close_weak_body_mult'] == 'InpBounceCloseWeakBodyMult'
    assert FLAT_MAP['virtual_sl_confirm_bars'] == 'InpVirtualSLConfirmBars'
    assert FLAT_MAP['virtual_sl_confirm_tf'] == 'InpVirtualSLConfirmTF'
    assert FLAT_MAP['virtual_sl_hard_buffer_r'] == 'InpVirtualSLHardBufferR'
    assert FLAT_MAP['virtual_sl_close_buffer_atr'] == 'InpVirtualSLCloseBufferATR'
    assert FLAT_MAP['defensive_confirm_min_price'] == 'InpDefensiveConfirmMinPrice'
    assert FLAT_MAP['defensive_confirm_max_price'] == 'InpDefensiveConfirmMaxPrice'
    assert FLAT_MAP['defensive_max_risk_atr'] == 'InpDefensiveMaxRiskATR'
    assert FLAT_MAP['defensive_bounce_close_min_body_pct'] == 'InpDefensiveBounceCloseMinBodyPct'
    assert FLAT_MAP['defensive_bounce_close_weak_body_pct'] == 'InpDefensiveBounceCloseWeakBodyPct'
    assert FLAT_MAP['defensive_bounce_close_weak_body_mult'] == 'InpDefensiveBounceCloseWeakBodyMult'
    assert FLAT_MAP['defensive_bounce_sweet_min_pct'] == 'InpDefensiveBounceSweetMinPct'
    assert FLAT_MAP['defensive_bounce_sweet_max_pct'] == 'InpDefensiveBounceSweetMaxPct'
    assert FLAT_MAP['defensive_outside_bounce_sweet_mult'] == 'InpDefensiveOutsideBounceSweetMult'
    assert FLAT_MAP['defensive_max_entries_per_ob'] == 'InpDefensiveMaxEntriesPerOB'
    assert FLAT_MAP['defensive_ob_reentry_cooldown_min'] == 'InpDefensiveOBReentryCooldownMin'
    assert FLAT_MAP['defensive_shallow_confirm_pos_min'] == 'InpDefensiveShallowConfirmPosMin'
    assert FLAT_MAP['defensive_shallow_confirm_pos_mult'] == 'InpDefensiveShallowConfirmPosMult'
    assert FLAT_MAP['runtime_defensive_drawdown_pct'] == 'InpRuntimeDefensiveDrawdownPct'
    assert FLAT_MAP['runtime_defensive_min_trades'] == 'InpRuntimeDefensiveMinTrades'
    assert FLAT_MAP['runtime_defensive_max_balance'] == 'InpRuntimeDefensiveMaxBalance'
    assert FLAT_MAP['runtime_defensive_pos_mult'] == 'InpRuntimeDefensivePosMult'
    assert FLAT_MAP['monthly_max_entries'] == 'InpMonthlyMaxEntries'
    assert FLAT_MAP['monthly_defensive_loss_pct'] == 'InpMonthlyDefensiveLossPct'
    assert FLAT_MAP['monthly_defensive_until_profit_pct'] == 'InpMonthlyDefensiveUntilProfitPct'
    assert FLAT_MAP['monthly_defensive_max_month_start_balance'] == 'InpMonthlyDefensiveMaxMonthStartBalance'
    assert FLAT_MAP['monthly_defensive_min_trades'] == 'InpMonthlyDefensiveMinTrades'
    assert FLAT_MAP['monthly_defensive_no_entry_hours'] == 'InpMonthlyDefensiveNoEntryHours'
    assert FLAT_MAP['monthly_defensive_no_buy_hours'] == 'InpMonthlyDefensiveNoBuyHours'
    assert FLAT_MAP['monthly_defensive_no_sell_hours'] == 'InpMonthlyDefensiveNoSellHours'
    assert FLAT_MAP['monthly_defensive_pos_mult'] == 'InpMonthlyDefensivePosMult'
    assert FLAT_MAP['fixed_lot_size'] == 'InpFixedLotSize'
    assert FLAT_MAP['enable_pos_mult'] == 'InpEnablePosMult'
    assert FLAT_MAP['max_pos_mult'] == 'InpMaxPosMult'
    assert FLAT_MAP['max_lot_size'] == 'InpMaxLotSize'
    assert FLAT_MAP['high_pos_mult_cap_threshold'] == 'InpHighPosMultCapThreshold'
    assert FLAT_MAP['high_pos_mult_max_lot_size'] == 'InpHighPosMultMaxLotSize'
    assert FLAT_MAP['high_pos_mult_cap_directions'] == 'InpHighPosMultCapDirections'
    assert FLAT_MAP['sweep_pos_mult'] == 'InpSweepPosMult'
    assert FLAT_MAP['sweep_h1_aligned_mult'] == 'InpSweepH1AlignedMult'
    assert FLAT_MAP['range_breakout_pos_mult'] == 'InpRangeBreakoutPosMult'
    assert FLAT_MAP['htf_pullback_pos_mult'] == 'InpHTFPullbackPosMult'
    assert FLAT_MAP['sweep_max_lot_size'] == 'InpSweepMaxLotSize'
    assert FLAT_MAP['loose_sweep_pos_mult'] == 'InpLooseSweepPosMult'
    assert FLAT_MAP['loose_sweep_max_lot_size'] == 'InpLooseSweepMaxLotSize'
    assert FLAT_MAP['loose_sweep_max_active_zones'] == 'InpLooseSweepMaxActiveZones'
    assert FLAT_MAP['range_breakout_max_lot_size'] == 'InpRangeBreakoutMaxLotSize'
    assert FLAT_MAP['htf_pullback_max_lot_size'] == 'InpHTFPullbackMaxLotSize'
    assert FLAT_MAP['htf_pullback_min_day'] == 'InpHTFPullbackMinDay'
    assert FLAT_MAP['htf_pullback_max_monthly_entries'] == 'InpHTFPullbackMaxMonthlyEntries'
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
    assert FLAT_MAP['sweep_only_monthly_negative'] == 'InpSweepOnlyMonthlyNegative'
    assert FLAT_MAP['sweep_monthly_profit_start_pct'] == 'InpSweepMonthlyProfitStartPct'
    assert FLAT_MAP['sweep_early_bounce_sec_min'] == 'InpSweepEarlyBounceSecMin'
    assert FLAT_MAP['sweep_early_bounce_sec_max'] == 'InpSweepEarlyBounceSecMax'
    assert FLAT_MAP['sweep_early_bounce_mult'] == 'InpSweepEarlyBounceMult'
    assert FLAT_MAP['sweep_early_bounce_hours'] == 'InpSweepEarlyBounceHours'
    assert FLAT_MAP['sweep_late_bounce_sec_min'] == 'InpSweepLateBounceSecMin'
    assert FLAT_MAP['sweep_late_bounce_mult'] == 'InpSweepLateBounceMult'
    assert FLAT_MAP['bad_bounce_min_pct'] == 'InpBadBounceMinPct'
    assert FLAT_MAP['bad_bounce_max_pct'] == 'InpBadBounceMaxPct'
    assert FLAT_MAP['bad_bounce_mult'] == 'InpBadBounceMult'
    assert FLAT_MAP['bad_bounce_signal_types'] == 'InpBadBounceSignalTypes'
    assert FLAT_MAP['bad_bounce_max_entry_pos_mult'] == 'InpBadBounceMaxEntryPosMult'
    assert FLAT_MAP['bad_bounce_pos_mult_directions'] == 'InpBadBouncePosMultDirections'
    assert FLAT_MAP['sweep_high_pos_mult_min'] == 'InpSweepHighPosMultMin'
    assert FLAT_MAP['sweep_high_pos_mult_mult'] == 'InpSweepHighPosMultMult'
    assert FLAT_MAP['aligned_no_cont_spread_risk_max'] == 'InpAlignedNoContSpreadRiskMax'
    assert FLAT_MAP['aligned_no_cont_mult'] == 'InpAlignedNoContMult'
    assert FLAT_MAP['sell_spread_risk_min'] == 'InpSellSpreadRiskMin'
    assert FLAT_MAP['sell_spread_risk_max'] == 'InpSellSpreadRiskMax'
    assert FLAT_MAP['sell_spread_risk_mult'] == 'InpSellSpreadRiskMult'
    assert FLAT_MAP['sell_spread_risk_until_profit_pct'] == 'InpSellSpreadRiskUntilProfitPct'
    assert FLAT_MAP['sell_spread_risk_ob_only'] == 'InpSellSpreadRiskOBOnly'
    assert FLAT_MAP['small_risk_atr_max'] == 'InpSmallRiskATRMax'
    assert FLAT_MAP['small_risk_atr_mult'] == 'InpSmallRiskATRMult'
    assert FLAT_MAP['small_risk_atr_entry_count_max'] == 'InpSmallRiskATREntryCountMax'
    assert FLAT_MAP['small_risk_atr_age_max_bars'] == 'InpSmallRiskATRAgeMaxBars'
    assert FLAT_MAP['risk_atr_band_bad_max'] == 'InpRiskATRBandBadMax'
    assert FLAT_MAP['risk_atr_band_bad_spread_risk_max'] == 'InpRiskATRBandBadSpreadRiskMax'
    assert FLAT_MAP['risk_atr_band_bad_age_min_bars'] == 'InpRiskATRBandBadAgeMinBars'
    assert FLAT_MAP['risk_atr_band_bad_touch_min'] == 'InpRiskATRBandBadTouchMin'
    assert FLAT_MAP['risk_atr_band_bad_mult'] == 'InpRiskATRBandBadMult'
    assert FLAT_MAP['risk_atr_band_bad_require_counter_push'] == 'InpRiskATRBandBadRequireCounterPush'
    assert FLAT_MAP['risk_atr_band_good_min'] == 'InpRiskATRBandGoodMin'
    assert FLAT_MAP['risk_atr_band_good_touch_min'] == 'InpRiskATRBandGoodTouchMin'
    assert FLAT_MAP['risk_atr_band_good_mult'] == 'InpRiskATRBandGoodMult'
    assert FLAT_MAP['old_high_score_ob_age_min_bars'] == 'InpOldHighScoreOBAgeMinBars'
    assert FLAT_MAP['old_high_score_ob_score_min'] == 'InpOldHighScoreOBScoreMin'
    assert FLAT_MAP['old_high_score_ob_mult'] == 'InpOldHighScoreOBMult'
    assert FLAT_MAP['old_pos_mult_ob_age_min_bars'] == 'InpOldPosMultOBAgeMinBars'
    assert FLAT_MAP['old_pos_mult_ob_pos_min'] == 'InpOldPosMultOBPosMin'
    assert FLAT_MAP['old_pos_mult_ob_mult'] == 'InpOldPosMultOBMult'
    assert FLAT_MAP['deep_confirm_low_spread_confirm_max'] == 'InpDeepConfirmLowSpreadConfirmMax'
    assert FLAT_MAP['deep_confirm_low_spread_risk_max'] == 'InpDeepConfirmLowSpreadRiskMax'
    assert FLAT_MAP['deep_confirm_low_spread_mult'] == 'InpDeepConfirmLowSpreadMult'
    assert FLAT_MAP['buy_cont_no_h1_age_min_bars'] == 'InpBuyContNoH1AgeMinBars'
    assert FLAT_MAP['buy_cont_no_h1_spread_risk_max'] == 'InpBuyContNoH1SpreadRiskMax'
    assert FLAT_MAP['buy_cont_no_h1_age_mult'] == 'InpBuyContNoH1AgeMult'
    assert FLAT_MAP['bos_lock_allow_counter_momentum'] == 'InpBOSLockAllowCounterMomentum'
    assert FLAT_MAP['bos_lock_counter_momentum_tf'] == 'InpBOSLockCounterMomentumTF'
    assert FLAT_MAP['bos_lock_counter_momentum_bars'] == 'InpBOSLockCounterMomentumBars'
    assert FLAT_MAP['bos_lock_counter_momentum_min_atr'] == 'InpBOSLockCounterMomentumMinATR'
    assert FLAT_MAP['bos_lock_allow_counter_break'] == 'InpBOSLockAllowCounterBreak'
    assert FLAT_MAP['bos_lock_counter_break_tf'] == 'InpBOSLockCounterBreakTF'
    assert FLAT_MAP['bos_lock_counter_break_bars'] == 'InpBOSLockCounterBreakBars'
    assert FLAT_MAP['bos_lock_counter_break_min_atr'] == 'InpBOSLockCounterBreakMinATR'
    assert FLAT_MAP['bos_lock_counter_break_buffer_atr'] == 'InpBOSLockCounterBreakBufferATR'
    assert FLAT_MAP['bos_lock_counter_break_ob_only'] == 'InpBOSLockCounterBreakOBOnly'
    assert FLAT_MAP['bos_lock_allow_counter_ob'] == 'InpBOSLockAllowCounterOB'
    assert FLAT_MAP['bos_lock_allow_counter_bounce'] == 'InpBOSLockAllowCounterBounce'
    assert FLAT_MAP['bos_lock_counter_bounce_sec_min'] == 'InpBOSLockCounterBounceSecMin'
    assert FLAT_MAP['bos_lock_counter_bounce_sec_max'] == 'InpBOSLockCounterBounceSecMax'
    assert FLAT_MAP['sweep_bad_age_min_bars'] == 'InpSweepBadAgeMinBars'
    assert FLAT_MAP['sweep_bad_age_max_bars'] == 'InpSweepBadAgeMaxBars'
    assert FLAT_MAP['sweep_bad_age_mult'] == 'InpSweepBadAgeMult'
    assert FLAT_MAP['ob_pos_mult'] == 'InpOBPosMult'
    assert FLAT_MAP['ob_pos_mult_min_balance'] == 'InpOBPosMultMinBalance'
    assert FLAT_MAP['ob_min_pos_mult'] == 'InpOBMinPosMult'
    assert FLAT_MAP['ob_min_pos_mult_directions'] == 'InpOBMinPosMultDirections'
    assert FLAT_MAP['ob_min_pos_mult_only_monthly_nonnegative'] == 'InpOBMinPosMultOnlyMonthlyNonNegative'
    assert FLAT_MAP['ob_high_pos_boost_min'] == 'InpOBHighPosBoostMin'
    assert FLAT_MAP['ob_high_pos_boost_mult'] == 'InpOBHighPosBoostMult'
    assert FLAT_MAP['ob_high_pos_boost_directions'] == 'InpOBHighPosBoostDirections'
    assert FLAT_MAP['ob_no_h1_pos_mult'] == 'InpOBNoH1PosMult'
    assert FLAT_MAP['ob_monthly_warmup_profit_pct'] == 'InpOBMonthlyWarmupProfitPct'
    assert FLAT_MAP['ob_monthly_warmup_pos_mult'] == 'InpOBMonthlyWarmupPosMult'
    assert FLAT_MAP['ob_monthly_profit_cap_pct'] == 'InpOBMonthlyProfitCapPct'
    assert FLAT_MAP['ob_monthly_profit_cap_mult'] == 'InpOBMonthlyProfitCapMult'
    assert FLAT_MAP['ob_monthly_negative_pos_mult'] == 'InpOBMonthlyNegativePosMult'
    assert FLAT_MAP['ob_monthly_mult_max_start_balance'] == 'InpOBMonthlyMultMaxStartBalance'
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
    assert FLAT_MAP['context_filter1_max_balance'] == 'InpContextFilter1MaxBalance'
    assert FLAT_MAP['context_filter1_range_tf'] == 'InpContextFilter1RangeTF'
    assert FLAT_MAP['context_filter1_min_range_atr'] == 'InpContextFilter1MinRangeATR'
    assert FLAT_MAP['context_filter1_max_net_range'] == 'InpContextFilter1MaxNetRange'
    assert FLAT_MAP['context_filter1_min_range_pos'] == 'InpContextFilter1MinRangePos'
    assert FLAT_MAP['context_filter1_max_range_pos'] == 'InpContextFilter1MaxRangePos'
    assert FLAT_MAP['context_filter1_min_month_range_atr'] == 'InpContextFilter1MinMonthRangeATR'
    assert FLAT_MAP['context_filter1_min_month_range_pos'] == 'InpContextFilter1MinMonthRangePos'
    assert FLAT_MAP['context_filter1_min_day'] == 'InpContextFilter1MinDay'
    assert FLAT_MAP['context_filter1_max_day'] == 'InpContextFilter1MaxDay'
    assert FLAT_MAP['context_filter1_ma_tf'] == 'InpContextFilter1MATF'
    assert FLAT_MAP['context_filter1_ma_bars'] == 'InpContextFilter1MABars'
    assert FLAT_MAP['context_filter1_min_ma_ext_atr'] == 'InpContextFilter1MinMAExtATR'
    assert FLAT_MAP['context_filter1_min_price'] == 'InpContextFilter1MinPrice'
    assert FLAT_MAP['context_filter1_max_price'] == 'InpContextFilter1MaxPrice'
    assert FLAT_MAP['context_filter1_mult'] == 'InpContextFilter1Mult'
    assert FLAT_MAP['context_filter4_months'] == 'InpContextFilter4Months'
    assert FLAT_MAP['context_filter4_no_buy_hours'] == 'InpContextFilter4NoBuyHours'
    assert FLAT_MAP['context_filter4_no_sell_hours'] == 'InpContextFilter4NoSellHours'
    assert FLAT_MAP['context_filter4_min_month_start_balance'] == 'InpContextFilter4MinMonthStartBalance'
    assert FLAT_MAP['context_filter4_max_balance'] == 'InpContextFilter4MaxBalance'
    assert FLAT_MAP['context_filter4_range_bars'] == 'InpContextFilter4RangeBars'
    assert FLAT_MAP['context_filter4_max_net_range'] == 'InpContextFilter4MaxNetRange'
    assert FLAT_MAP['context_filter4_min_range_pos'] == 'InpContextFilter4MinRangePos'
    assert FLAT_MAP['context_filter4_max_range_pos'] == 'InpContextFilter4MaxRangePos'
    assert FLAT_MAP['context_filter4_min_month_range_atr'] == 'InpContextFilter4MinMonthRangeATR'
    assert FLAT_MAP['context_filter4_min_month_range_pos'] == 'InpContextFilter4MinMonthRangePos'
    assert FLAT_MAP['context_filter4_min_day'] == 'InpContextFilter4MinDay'
    assert FLAT_MAP['context_filter4_max_day'] == 'InpContextFilter4MaxDay'
    assert FLAT_MAP['context_filter4_ma_tf'] == 'InpContextFilter4MATF'
    assert FLAT_MAP['context_filter4_ma_bars'] == 'InpContextFilter4MABars'
    assert FLAT_MAP['context_filter4_min_ma_ext_atr'] == 'InpContextFilter4MinMAExtATR'
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
    assert FLAT_MAP['shallow_confirm_signal_types'] == 'InpShallowConfirmSignalTypes'
    assert FLAT_MAP['shallow_confirm_directions'] == 'InpShallowConfirmDirections'
    assert FLAT_MAP['shallow_confirm_max_entry_pos_mult'] == 'InpShallowConfirmMaxEntryPosMult'
    assert FLAT_MAP['deep_fast_confirm_pos_max'] == 'InpDeepFastConfirmPosMax'
    assert FLAT_MAP['deep_fast_confirm_sec_max'] == 'InpDeepFastConfirmSecMax'
    assert FLAT_MAP['deep_fast_confirm_mult'] == 'InpDeepFastConfirmMult'
    assert FLAT_MAP['deep_fast_confirm_bounce_min_pct'] == 'InpDeepFastConfirmBounceMinPct'
    assert FLAT_MAP['deep_fast_confirm_bounce_max_pct'] == 'InpDeepFastConfirmBounceMaxPct'
    assert FLAT_MAP['deep_fast_confirm_signal_types'] == 'InpDeepFastConfirmSignalTypes'
    assert FLAT_MAP['deep_fast_confirm_directions'] == 'InpDeepFastConfirmDirections'
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
    assert FLAT_MAP['strong_addon_use_risk_lot'] == 'InpStrongAddOnUseRiskLot'
    assert FLAT_MAP['strong_addon_risk_percent'] == 'InpStrongAddOnRiskPercent'
    assert FLAT_MAP['strong_addon_max_lot_size'] == 'InpStrongAddOnMaxLotSize'
    assert FLAT_MAP['strong_addon_families'] == 'InpStrongAddOnFamilies'
    assert FLAT_MAP['strong_addon_directions'] == 'InpStrongAddOnDirections'
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
        'context_filter1_max_balance': 500.0,
        'context_filter1_range_tf': 240,
        'context_filter1_range_bars': 12,
        'context_filter1_min_range_atr': 4.0,
        'context_filter1_max_net_range': 0.45,
        'context_filter1_min_range_pos': 0.8,
        'context_filter1_max_range_pos': 1.2,
        'context_filter1_min_month_range_atr': 5.0,
        'context_filter1_min_month_range_pos': 0.7,
        'context_filter1_min_day': 20,
        'context_filter1_max_day': 31,
        'context_filter1_ma_tf': 1440,
        'context_filter1_ma_bars': 50,
        'context_filter1_min_ma_ext_atr': 2.5,
        'context_filter1_min_price': 3000.0,
        'context_filter1_max_price': 4500.0,
        'context_filter1_mult': 0.0,
        'context_filter2_months': '3',
        'context_filter2_no_sell_hours': '0,1,8',
        'context_filter2_max_balance': 750.0,
        'context_filter2_range_tf': 60,
        'context_filter2_range_bars': 6,
        'context_filter2_min_range_atr': 2.5,
        'context_filter2_max_net_range': 0.6,
        'context_filter2_min_range_pos': 0.75,
        'context_filter2_max_range_pos': 1.5,
        'context_filter2_min_month_range_atr': 4.0,
        'context_filter2_min_month_range_pos': 0.6,
        'context_filter2_min_day': 18,
        'context_filter2_max_day': 28,
        'context_filter2_ma_tf': 1440,
        'context_filter2_ma_bars': 20,
        'context_filter2_min_ma_ext_atr': 1.5,
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
    assert 'InpContextFilter1MaxBalance=500.0' in content
    assert 'InpContextFilter1RangeTF=240' in content
    assert 'InpContextFilter1RangeBars=12' in content
    assert 'InpContextFilter1MinRangeATR=4.0' in content
    assert 'InpContextFilter1MaxNetRange=0.45' in content
    assert 'InpContextFilter1MinRangePos=0.8' in content
    assert 'InpContextFilter1MaxRangePos=1.2' in content
    assert 'InpContextFilter1MinMonthRangeATR=5.0' in content
    assert 'InpContextFilter1MinMonthRangePos=0.7' in content
    assert 'InpContextFilter1MinDay=20' in content
    assert 'InpContextFilter1MaxDay=31' in content
    assert 'InpContextFilter1MATF=1440' in content
    assert 'InpContextFilter1MABars=50' in content
    assert 'InpContextFilter1MinMAExtATR=2.5' in content
    assert 'InpContextFilter1MinPrice=3000.0' in content
    assert 'InpContextFilter1MaxPrice=4500.0' in content
    assert 'InpContextFilter1Mult=0.0' in content
    assert 'InpContextFilter2Months=3' in content
    assert 'InpContextFilter2NoSellHours=0,1,8' in content
    assert 'InpContextFilter2MaxBalance=750.0' in content
    assert 'InpContextFilter2RangeTF=60' in content
    assert 'InpContextFilter2RangeBars=6' in content
    assert 'InpContextFilter2MinRangeATR=2.5' in content
    assert 'InpContextFilter2MaxNetRange=0.6' in content
    assert 'InpContextFilter2MinRangePos=0.75' in content
    assert 'InpContextFilter2MaxRangePos=1.5' in content
    assert 'InpContextFilter2MinMonthRangeATR=4.0' in content
    assert 'InpContextFilter2MinMonthRangePos=0.6' in content
    assert 'InpContextFilter2MinDay=18' in content
    assert 'InpContextFilter2MaxDay=28' in content
    assert 'InpContextFilter2MATF=1440' in content
    assert 'InpContextFilter2MABars=20' in content
    assert 'InpContextFilter2MinMAExtATR=1.5' in content
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
        'high_pos_mult_cap_threshold': 0.0,
        'high_pos_mult_max_lot_size': 0.0,
        'high_pos_mult_cap_directions': '',
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
        'bad_bounce_min_pct': 0.28,
        'bad_bounce_max_pct': 0.40,
        'bad_bounce_mult': 0.0,
        'bad_bounce_signal_types': 'OB',
        'bad_bounce_max_entry_pos_mult': 1.9,
        'bad_bounce_pos_mult_directions': 'BUY',
        'sweep_early_bounce_sec_min': 1,
        'sweep_early_bounce_sec_max': 5,
        'sweep_early_bounce_mult': 0.35,
        'sweep_early_bounce_hours': '0,9,20',
        'sweep_late_bounce_sec_min': 21,
        'sweep_late_bounce_mult': 0.4,
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
        'shallow_confirm_signal_types': 'OB',
        'shallow_confirm_directions': 'BUY',
        'shallow_confirm_max_entry_pos_mult': 1.9,
        'deep_fast_confirm_pos_max': -1.2,
        'deep_fast_confirm_sec_max': 20,
        'deep_fast_confirm_mult': 0.0,
        'deep_fast_confirm_bounce_min_pct': 0.26,
        'deep_fast_confirm_bounce_max_pct': 0.31,
        'deep_fast_confirm_signal_types': 'OB',
        'deep_fast_confirm_directions': 'BUY',
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
        'ob_no_h1_pos_mult': 0.0,
        'aligned_no_cont_spread_risk_max': 0.2,
        'aligned_no_cont_mult': 0.0,
        'sell_spread_risk_min': 0.16,
        'sell_spread_risk_max': 999.0,
        'sell_spread_risk_mult': 0.3,
        'sell_spread_risk_until_profit_pct': 2.0,
        'sell_spread_risk_ob_only': True,
        'small_risk_atr_max': 0.75,
        'small_risk_atr_mult': 0.0,
        'small_risk_atr_entry_count_max': 5,
        'small_risk_atr_age_max_bars': 160,
        'risk_atr_band_bad_max': 0.85,
        'risk_atr_band_bad_spread_risk_max': 0.2,
        'risk_atr_band_bad_age_min_bars': 20,
        'risk_atr_band_bad_touch_min': 100,
        'risk_atr_band_bad_mult': 0.0,
        'risk_atr_band_bad_require_counter_push': True,
        'risk_atr_band_good_min': 0.85,
        'risk_atr_band_good_touch_min': 500,
        'risk_atr_band_good_mult': 2.0,
        'old_high_score_ob_age_min_bars': 100,
        'old_high_score_ob_score_min': 5,
        'old_high_score_ob_mult': 0.0,
        'old_pos_mult_ob_age_min_bars': 120,
        'old_pos_mult_ob_pos_min': 0.5,
        'old_pos_mult_ob_mult': 0.0,
        'deep_confirm_low_spread_confirm_max': -0.7,
        'deep_confirm_low_spread_risk_max': 0.16,
        'deep_confirm_low_spread_mult': 0.0,
        'ob_min_pos_mult': 0.3,
        'ob_min_pos_mult_directions': 'BUY',
        'ob_min_pos_mult_only_monthly_nonnegative': True,
        'ob_high_pos_boost_min': 1.0,
        'ob_high_pos_boost_mult': 1.25,
        'ob_high_pos_boost_directions': 'BUY',
        'buy_cont_no_h1_age_min_bars': 100,
        'buy_cont_no_h1_spread_risk_max': 0.36,
        'buy_cont_no_h1_age_mult': 0.0,
        'bos_lock_allow_counter_momentum': True,
        'bos_lock_counter_momentum_tf': 5,
        'bos_lock_counter_momentum_bars': 4,
        'bos_lock_counter_momentum_min_atr': 0.55,
        'bos_lock_allow_counter_break': True,
        'bos_lock_counter_break_tf': 5,
        'bos_lock_counter_break_bars': 3,
        'bos_lock_counter_break_min_atr': 0.35,
        'bos_lock_counter_break_buffer_atr': 0.03,
        'bos_lock_counter_break_ob_only': True,
        'bos_lock_allow_counter_ob': True,
        'bos_lock_allow_counter_bounce': True,
        'bos_lock_counter_bounce_sec_min': 12,
        'bos_lock_counter_bounce_sec_max': 18,
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
    assert 'InpHighPosMultCapThreshold=0.0' in content
    assert 'InpHighPosMultMaxLotSize=0.0' in content
    assert 'InpHighPosMultCapDirections=' in content
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
    assert 'InpBadBounceMinPct=0.28' in content
    assert 'InpBadBounceMaxPct=0.4' in content
    assert 'InpBadBounceMult=0.0' in content
    assert 'InpBadBounceSignalTypes=OB' in content
    assert 'InpBadBounceMaxEntryPosMult=1.9' in content
    assert 'InpBadBouncePosMultDirections=BUY' in content
    assert 'InpShallowConfirmSignalTypes=OB' in content
    assert 'InpShallowConfirmDirections=BUY' in content
    assert 'InpShallowConfirmMaxEntryPosMult=1.9' in content
    assert 'InpDeepFastConfirmPosMax=-1.2' in content
    assert 'InpDeepFastConfirmSecMax=20' in content
    assert 'InpDeepFastConfirmMult=0.0' in content
    assert 'InpDeepFastConfirmBounceMinPct=0.26' in content
    assert 'InpDeepFastConfirmBounceMaxPct=0.31' in content
    assert 'InpDeepFastConfirmSignalTypes=OB' in content
    assert 'InpDeepFastConfirmDirections=BUY' in content
    assert 'InpSweepEarlyBounceSecMin=1' in content
    assert 'InpSweepEarlyBounceSecMax=5' in content
    assert 'InpSweepEarlyBounceMult=0.35' in content
    assert 'InpSweepEarlyBounceHours=0,9,20' in content
    assert 'InpSweepLateBounceSecMin=21' in content
    assert 'InpSweepLateBounceMult=0.4' in content
    assert 'InpSweepContextMonths=3' in content
    assert 'InpSweepContextMaxDay=2' in content
    assert 'InpSweepContextMinMonthStartBalance=100000.0' in content
    assert 'InpSweepContextNoHours=0,1,6,23' in content
    assert 'InpSweepBadAgeMinBars=20' in content
    assert 'InpSweepBadAgeMaxBars=40' in content
    assert 'InpSweepBadAgeMult=0.35' in content
    assert 'InpRiskATRBandBadRequireCounterPush=true' in content
    assert 'InpOldHighScoreOBAgeMinBars=100' in content
    assert 'InpOldHighScoreOBScoreMin=5' in content
    assert 'InpOldHighScoreOBMult=0.0' in content
    assert 'InpOldPosMultOBAgeMinBars=120' in content
    assert 'InpOldPosMultOBPosMin=0.5' in content
    assert 'InpOldPosMultOBMult=0.0' in content
    assert 'InpOBMinPosMult=0.3' in content
    assert 'InpOBMinPosMultDirections=BUY' in content
    assert 'InpOBMinPosMultOnlyMonthlyNonNegative=true' in content
    assert 'InpOBHighPosBoostMin=1.0' in content
    assert 'InpOBHighPosBoostMult=1.25' in content
    assert 'InpOBHighPosBoostDirections=BUY' in content
    assert 'InpDeepConfirmLowSpreadConfirmMax=-0.7' in content
    assert 'InpDeepConfirmLowSpreadRiskMax=0.16' in content
    assert 'InpDeepConfirmLowSpreadMult=0.0' in content
    assert 'InpBuyContNoH1AgeMinBars=100' in content
    assert 'InpBuyContNoH1SpreadRiskMax=0.36' in content
    assert 'InpBuyContNoH1AgeMult=0.0' in content
    assert 'InpBOSLockAllowCounterMomentum=true' in content
    assert 'InpBOSLockCounterMomentumTF=5' in content
    assert 'InpBOSLockCounterMomentumBars=4' in content
    assert 'InpBOSLockCounterMomentumMinATR=0.55' in content
    assert 'InpBOSLockAllowCounterBreak=true' in content
    assert 'InpBOSLockCounterBreakTF=5' in content
    assert 'InpBOSLockCounterBreakBars=3' in content
    assert 'InpBOSLockCounterBreakMinATR=0.35' in content
    assert 'InpBOSLockCounterBreakBufferATR=0.03' in content
    assert 'InpBOSLockCounterBreakOBOnly=true' in content
    assert 'InpBOSLockAllowCounterOB=true' in content
    assert 'InpBOSLockAllowCounterBounce=true' in content
    assert 'InpBOSLockCounterBounceSecMin=12' in content
    assert 'InpBOSLockCounterBounceSecMax=18' in content
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
    assert 'InpOBNoH1PosMult=0.0' in content
    assert 'InpAlignedNoContSpreadRiskMax=0.2' in content
    assert 'InpAlignedNoContMult=0.0' in content
    assert 'InpSellSpreadRiskMin=0.16' in content
    assert 'InpSellSpreadRiskMax=999.0' in content
    assert 'InpSellSpreadRiskMult=0.3' in content
    assert 'InpSellSpreadRiskUntilProfitPct=2.0' in content
    assert 'InpSellSpreadRiskOBOnly=true' in content
    assert 'InpSmallRiskATRMax=0.75' in content
    assert 'InpSmallRiskATRMult=0.0' in content
    assert 'InpSmallRiskATREntryCountMax=5' in content
    assert 'InpSmallRiskATRAgeMaxBars=160' in content
    assert 'InpRiskATRBandBadMax=0.85' in content
    assert 'InpRiskATRBandBadSpreadRiskMax=0.2' in content
    assert 'InpRiskATRBandBadAgeMinBars=20' in content
    assert 'InpRiskATRBandBadTouchMin=100' in content
    assert 'InpRiskATRBandBadMult=0.0' in content
    assert 'InpRiskATRBandGoodMin=0.85' in content
    assert 'InpRiskATRBandGoodTouchMin=500' in content
    assert 'InpRiskATRBandGoodMult=2.0' in content
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
        'entry_depth_signal_types': 'OB,BOS',
        'deep_entry_boost': 2.0,
        'entry_confirm_bars': 3,
        'min_score': 4,
    }
    content = strategy_to_set('v98a', cfg)
    assert 'InpEnableEntryEngine=true' in content
    assert 'InpBouncePct=0.6' in content
    assert 'InpEntryDepthPct=0.67' in content
    assert 'InpEntryDepthFilter=false' in content
    assert 'InpEntryDepthSignalTypes=OB,BOS' in content
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
    assert FLAT_MAP['early_bounce_sec_max'] == 'InpEarlyBounceSecMax'
    assert FLAT_MAP['early_bounce_mult'] == 'InpEarlyBounceMult'
    assert FLAT_MAP['enable_momentum_regime'] == 'InpEnableMomentumRegime'
    assert FLAT_MAP['weak_exit_min_r'] == 'InpWeakExitMinR'
    assert FLAT_MAP['weak_exit_family_filter'] == 'InpWeakExitFamilyFilter'
    assert FLAT_MAP['weak_exit_family_min_r'] == 'InpWeakExitFamilyMinR'
    assert FLAT_MAP['weak_exit_require_reverse_continuation'] == 'InpWeakExitRequireReverseContinuation'
    assert FLAT_MAP['weak_exit_hold_lock_r'] == 'InpWeakExitHoldLockR'
    assert FLAT_MAP['weak_exit_low_balance_threshold'] == 'InpWeakExitLowBalanceThreshold'
    assert FLAT_MAP['weak_exit_low_balance_force_exit_r'] == 'InpWeakExitLowBalanceForceExitR'
    assert FLAT_MAP['weak_exit_low_balance_hold_lock_r'] == 'InpWeakExitLowBalanceHoldLockR'
    assert FLAT_MAP['strong_dtp_retrace_mult'] == 'InpStrongDTPRetraceMult'
    assert FLAT_MAP['dtp_hold_on_continuation'] == 'InpDTPHoldOnContinuation'
    assert FLAT_MAP['dtp_hold_tf1'] == 'InpDTPHoldTF1'
    assert FLAT_MAP['dtp_hold_tf2'] == 'InpDTPHoldTF2'
    assert FLAT_MAP['dtp_hold_lookback_bars'] == 'InpDTPHoldLookbackBars'
    assert FLAT_MAP['dtp_hold_min_net_atr'] == 'InpDTPHoldMinNetATR'
    assert FLAT_MAP['dtp_hold_reverse_body_atr'] == 'InpDTPHoldReverseBodyATR'
    assert FLAT_MAP['dtp_hold_break_buffer_atr'] == 'InpDTPHoldBreakBufferATR'
    assert FLAT_MAP['dtp_hold_require_htf_aligned'] == 'InpDTPHoldRequireHTFAligned'
    assert FLAT_MAP['dtp_hold_min_bounce_sec'] == 'InpDTPHoldMinBounceSec'
    assert FLAT_MAP['dtp_hold_min_bounce_directions'] == 'InpDTPHoldMinBounceDirections'
    assert FLAT_MAP['dtp_hold_max_confirm_pos'] == 'InpDTPHoldMaxConfirmPos'
    assert FLAT_MAP['dtp_hold_confirm_pos_directions'] == 'InpDTPHoldConfirmPosDirections'
    assert FLAT_MAP['dtp_hold_min_entry_pos_mult'] == 'InpDTPHoldMinEntryPosMult'
    assert FLAT_MAP['dtp_hold_min_entry_pos_mult_directions'] == 'InpDTPHoldMinEntryPosMultDirections'
    assert FLAT_MAP['dtp_exit_require_reverse_continuation'] == 'InpDTPExitRequireReverseContinuation'
    assert FLAT_MAP['dtp_exit_require_momentum_weakness'] == 'InpDTPExitRequireMomentumWeakness'
    assert FLAT_MAP['dtp_strict_exit_families'] == 'InpDTPStrictExitFamilies'
    assert FLAT_MAP['dtp_strict_require_htf_aligned'] == 'InpDTPStrictRequireHTFAligned'
    assert FLAT_MAP['dtp_strict_htf_tf'] == 'InpDTPStrictHTFTF'
    assert FLAT_MAP['dtp_strict_htf_bars'] == 'InpDTPStrictHTFBars'
    assert FLAT_MAP['dtp_strict_htf_min_atr'] == 'InpDTPStrictHTFMinATR'
    assert FLAT_MAP['conditional_ob_trend_release'] == 'InpConditionalOBTrendRelease'
    assert FLAT_MAP['conditional_ob_trend_release_families'] == 'InpConditionalOBTrendReleaseFamilies'
    assert FLAT_MAP['conditional_ob_trend_release_drop_tp'] == 'InpConditionalOBTrendReleaseDropTP'
    assert FLAT_MAP['conditional_ob_trend_release_be_lock_r'] == 'InpConditionalOBTrendReleaseBELockR'
    assert FLAT_MAP['conditional_ob_trend_release_min_entry_pos_mult'] == 'InpConditionalOBTrendReleaseMinEntryPosMult'
    assert FLAT_MAP['conditional_ob_trend_release_pos_mult_directions'] == 'InpConditionalOBTrendReleasePosMultDirections'
    assert FLAT_MAP['conditional_ob_trend_release_tf1'] == 'InpConditionalOBTrendReleaseTF1'
    assert FLAT_MAP['conditional_ob_trend_release_tf2'] == 'InpConditionalOBTrendReleaseTF2'
    assert FLAT_MAP['conditional_ob_trend_release_lookback_bars'] == 'InpConditionalOBTrendReleaseLookbackBars'
    assert FLAT_MAP['conditional_ob_trend_release_min_net_atr'] == 'InpConditionalOBTrendReleaseMinNetATR'
    assert FLAT_MAP['conditional_ob_trend_release_reverse_body_atr'] == 'InpConditionalOBTrendReleaseReverseBodyATR'
    assert FLAT_MAP['conditional_ob_trend_release_break_buffer_atr'] == 'InpConditionalOBTrendReleaseBreakBufferATR'
    assert FLAT_MAP['struct_mom_require_full_reverse_exit'] == 'InpStructMomRequireFullReverseExit'
    assert FLAT_MAP['struct_mom_full_reverse_min_r'] == 'InpStructMomFullReverseMinR'
    assert FLAT_MAP['struct_profit_lock_trigger_r'] == 'InpStructProfitLockTriggerR'
    assert FLAT_MAP['struct_profit_lock_r'] == 'InpStructProfitLockR'
    assert FLAT_MAP['struct_profit_trail_trigger_r'] == 'InpStructProfitTrailTriggerR'
    assert FLAT_MAP['struct_profit_trail_lock_mult'] == 'InpStructProfitTrailLockMult'
    assert FLAT_MAP['struct_profit_lock_require_reverse_signal'] == 'InpStructProfitLockRequireReverseSignal'
    assert FLAT_MAP['structure_sl_require_htf_aligned'] == 'InpStructureSLRequireHTFAligned'
    assert FLAT_MAP['structure_sl_htf_tf'] == 'InpStructureSLHTFTF'
    assert FLAT_MAP['structure_sl_htf_bars'] == 'InpStructureSLHTFBars'
    assert FLAT_MAP['structure_sl_htf_min_atr'] == 'InpStructureSLHTFMinATR'
    assert FLAT_MAP['structure_sl_require_strong_break'] == 'InpStructureSLRequireStrongBreak'
    assert FLAT_MAP['structure_sl_strong_break_tf1'] == 'InpStructureSLStrongBreakTF1'
    assert FLAT_MAP['structure_sl_strong_break_tf2'] == 'InpStructureSLStrongBreakTF2'
    assert FLAT_MAP['structure_sl_strong_break_lookback'] == 'InpStructureSLStrongBreakLookback'
    assert FLAT_MAP['structure_sl_strong_break_max_age'] == 'InpStructureSLStrongBreakMaxAge'
    assert FLAT_MAP['structure_sl_strong_break_pivot'] == 'InpStructureSLStrongBreakPivot'
    assert FLAT_MAP['structure_sl_strong_break_buffer_atr'] == 'InpStructureSLStrongBreakBufferATR'

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
        'early_bounce_sec_max': 10,
        'early_bounce_mult': 0.0,
        'enable_momentum_regime': True,
        'weak_exit_min_r': 1.2,
        'weak_exit_family_filter': 'SWP',
        'weak_exit_family_min_r': 1.5,
        'weak_exit_require_reverse_continuation': True,
        'weak_exit_hold_lock_r': 0.8,
        'weak_exit_low_balance_threshold': 600.0,
        'weak_exit_low_balance_force_exit_r': 1.2,
        'weak_exit_low_balance_hold_lock_r': 1.0,
        'weak_body_shrink_pct': 0.8,
        'weak_wick_body_ratio': 2.0,
        'strong_momentum_bars': 4,
        'strong_min_body_growth': 1.0,
        'strong_weak_reverse_body_pct': 25.0,
        'strong_max_pullback_pct': 35.0,
        'strong_dtp_retrace_mult': 1.5,
        'dtp_hold_on_continuation': True,
        'dtp_hold_tf1': 1,
        'dtp_hold_tf2': 5,
        'dtp_hold_lookback_bars': 4,
        'dtp_hold_min_net_atr': 0.25,
        'dtp_hold_reverse_body_atr': 0.5,
        'dtp_hold_break_buffer_atr': 0.08,
        'dtp_hold_require_htf_aligned': True,
        'dtp_hold_min_bounce_sec': 12,
        'dtp_hold_min_bounce_directions': 'BUY',
        'dtp_hold_max_confirm_pos': -0.45,
        'dtp_hold_confirm_pos_directions': 'BUY',
        'dtp_hold_min_entry_pos_mult': 2.0,
        'dtp_hold_min_entry_pos_mult_directions': 'BUY',
        'dtp_exit_require_reverse_continuation': True,
        'dtp_exit_require_momentum_weakness': True,
        'dtp_strict_exit_families': 'BOS,MBOS',
        'dtp_strict_require_htf_aligned': True,
        'dtp_strict_htf_tf': 60,
        'dtp_strict_htf_bars': 4,
        'dtp_strict_htf_min_atr': 0.4,
        'conditional_ob_trend_release': True,
        'conditional_ob_trend_release_families': 'OB',
        'conditional_ob_trend_release_drop_tp': True,
        'conditional_ob_trend_release_be_lock_r': 0.0,
        'conditional_ob_trend_release_min_entry_pos_mult': 2.0,
        'conditional_ob_trend_release_pos_mult_directions': 'BUY',
        'conditional_ob_trend_release_tf1': 1,
        'conditional_ob_trend_release_tf2': 5,
        'conditional_ob_trend_release_lookback_bars': 3,
        'conditional_ob_trend_release_min_net_atr': 0.2,
        'conditional_ob_trend_release_reverse_body_atr': 0.45,
        'conditional_ob_trend_release_break_buffer_atr': 0.05,
        'struct_mom_require_full_reverse_exit': True,
        'struct_mom_full_reverse_min_r': 0.7,
        'struct_profit_lock_trigger_r': 1.0,
        'struct_profit_lock_r': 0.4,
        'struct_profit_trail_trigger_r': 2.0,
        'struct_profit_trail_lock_mult': 0.5,
        'struct_profit_lock_require_reverse_signal': True,
        'structure_sl_require_htf_aligned': True,
        'structure_sl_htf_tf': 15,
        'structure_sl_htf_bars': 5,
        'structure_sl_htf_min_atr': 0.45,
        'structure_sl_require_strong_break': True,
        'structure_sl_strong_break_tf1': 60,
        'structure_sl_strong_break_tf2': 240,
        'structure_sl_strong_break_lookback': 96,
        'structure_sl_strong_break_max_age': 144,
        'structure_sl_strong_break_pivot': 3,
        'structure_sl_strong_break_buffer_atr': 0.05,
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
    assert 'InpEarlyBounceSecMax=10' in content
    assert 'InpEarlyBounceMult=0.0' in content
    assert 'InpEnableMomentumRegime=true' in content
    assert 'InpWeakExitMinR=1.2' in content
    assert 'InpWeakExitFamilyFilter=SWP' in content
    assert 'InpWeakExitFamilyMinR=1.5' in content
    assert 'InpWeakExitRequireReverseContinuation=true' in content
    assert 'InpWeakExitHoldLockR=0.8' in content
    assert 'InpWeakExitLowBalanceThreshold=600.0' in content
    assert 'InpWeakExitLowBalanceForceExitR=1.2' in content
    assert 'InpWeakExitLowBalanceHoldLockR=1.0' in content
    assert 'InpWeakBodyShrinkPct=0.8' in content
    assert 'InpStrongDTPRetraceMult=1.5' in content
    assert 'InpDTPHoldOnContinuation=true' in content
    assert 'InpDTPHoldTF1=1' in content
    assert 'InpDTPHoldTF2=5' in content
    assert 'InpDTPHoldLookbackBars=4' in content
    assert 'InpDTPHoldMinNetATR=0.25' in content
    assert 'InpDTPHoldReverseBodyATR=0.5' in content
    assert 'InpDTPHoldBreakBufferATR=0.08' in content
    assert 'InpDTPHoldRequireHTFAligned=true' in content
    assert 'InpDTPHoldMinBounceSec=12' in content
    assert 'InpDTPHoldMinBounceDirections=BUY' in content
    assert 'InpDTPHoldMaxConfirmPos=-0.45' in content
    assert 'InpDTPHoldConfirmPosDirections=BUY' in content
    assert 'InpDTPHoldMinEntryPosMult=2.0' in content
    assert 'InpDTPHoldMinEntryPosMultDirections=BUY' in content
    assert 'InpDTPExitRequireReverseContinuation=true' in content
    assert 'InpDTPExitRequireMomentumWeakness=true' in content
    assert 'InpDTPStrictExitFamilies=BOS,MBOS' in content
    assert 'InpDTPStrictRequireHTFAligned=true' in content
    assert 'InpDTPStrictHTFTF=60' in content
    assert 'InpDTPStrictHTFBars=4' in content
    assert 'InpDTPStrictHTFMinATR=0.4' in content
    assert 'InpConditionalOBTrendRelease=true' in content
    assert 'InpConditionalOBTrendReleaseFamilies=OB' in content
    assert 'InpConditionalOBTrendReleaseDropTP=true' in content
    assert 'InpConditionalOBTrendReleaseBELockR=0.0' in content
    assert 'InpConditionalOBTrendReleaseMinEntryPosMult=2.0' in content
    assert 'InpConditionalOBTrendReleasePosMultDirections=BUY' in content
    assert 'InpConditionalOBTrendReleaseTF1=1' in content
    assert 'InpConditionalOBTrendReleaseTF2=5' in content
    assert 'InpConditionalOBTrendReleaseLookbackBars=3' in content
    assert 'InpConditionalOBTrendReleaseMinNetATR=0.2' in content
    assert 'InpConditionalOBTrendReleaseReverseBodyATR=0.45' in content
    assert 'InpConditionalOBTrendReleaseBreakBufferATR=0.05' in content
    assert 'InpStructMomRequireFullReverseExit=true' in content
    assert 'InpStructMomFullReverseMinR=0.7' in content
    assert 'InpStructProfitLockTriggerR=1.0' in content
    assert 'InpStructProfitLockR=0.4' in content
    assert 'InpStructProfitTrailTriggerR=2.0' in content
    assert 'InpStructProfitTrailLockMult=0.5' in content
    assert 'InpStructProfitLockRequireReverseSignal=true' in content
    assert 'InpStructureSLRequireHTFAligned=true' in content
    assert 'InpStructureSLHTFTF=15' in content
    assert 'InpStructureSLHTFBars=5' in content
    assert 'InpStructureSLHTFMinATR=0.45' in content
    assert 'InpStructureSLRequireStrongBreak=true' in content
    assert 'InpStructureSLStrongBreakTF1=60' in content
    assert 'InpStructureSLStrongBreakTF2=240' in content
    assert 'InpStructureSLStrongBreakLookback=96' in content
    assert 'InpStructureSLStrongBreakMaxAge=144' in content
    assert 'InpStructureSLStrongBreakPivot=3' in content
    assert 'InpStructureSLStrongBreakBufferATR=0.05' in content


# ── write_set_file ───────────────────────────────────────────────────

def test_structure_momentum_hold_params_in_set():
    assert FLAT_MAP['bos_retest_entry'] == 'InpBOSRetestEntry'
    assert FLAT_MAP['bos_lock_bounce_entries'] == 'InpBOSLockBounceEntries'
    assert FLAT_MAP['bos_retest_direct_entry'] == 'InpBOSRetestDirectEntry'
    assert FLAT_MAP['bos_retest_tf'] == 'InpBOSRetestTF'
    assert FLAT_MAP['bos_retest_tf2'] == 'InpBOSRetestTF2'
    assert FLAT_MAP['bos_retest_lookback_bars'] == 'InpBOSRetestLookbackBars'
    assert FLAT_MAP['bos_retest_pivot_bars'] == 'InpBOSRetestPivotBars'
    assert FLAT_MAP['bos_retest_break_buffer_atr'] == 'InpBOSRetestBreakBufferATR'
    assert FLAT_MAP['bos_retest_min_extension_atr'] == 'InpBOSRetestMinExtensionATR'
    assert FLAT_MAP['bos_retest_sl_buffer'] == 'InpBOSRetestSLBuffer'
    assert FLAT_MAP['bos_retest_tolerance'] == 'InpBOSRetestTolerance'
    assert FLAT_MAP['bos_retest_max_bars'] == 'InpBOSRetestMaxBars'
    assert FLAT_MAP['bos_retest_weight'] == 'InpBOSRetestWeight'
    assert FLAT_MAP['bos_retest_max_lot_size'] == 'InpBOSRetestMaxLotSize'
    assert FLAT_MAP['htf_bos_retest_entry'] == 'InpHTFBOSRetestEntry'
    assert FLAT_MAP['htf_bos_retest_direct_entry'] == 'InpHTFBOSRetestDirectEntry'
    assert FLAT_MAP['htf_bos_retest_tf'] == 'InpHTFBOSRetestTF'
    assert FLAT_MAP['htf_bos_retest_tf2'] == 'InpHTFBOSRetestTF2'
    assert FLAT_MAP['htf_bos_retest_lookback_bars'] == 'InpHTFBOSRetestLookbackBars'
    assert FLAT_MAP['htf_bos_retest_pivot_bars'] == 'InpHTFBOSRetestPivotBars'
    assert FLAT_MAP['htf_bos_retest_break_buffer_atr'] == 'InpHTFBOSRetestBreakBufferATR'
    assert FLAT_MAP['htf_bos_retest_min_extension_atr'] == 'InpHTFBOSRetestMinExtensionATR'
    assert FLAT_MAP['htf_bos_retest_sl_buffer'] == 'InpHTFBOSRetestSLBuffer'
    assert FLAT_MAP['htf_bos_retest_tolerance'] == 'InpHTFBOSRetestTolerance'
    assert FLAT_MAP['htf_bos_retest_max_bars'] == 'InpHTFBOSRetestMaxBars'
    assert FLAT_MAP['htf_bos_retest_weight'] == 'InpHTFBOSRetestWeight'
    assert FLAT_MAP['htf_bos_retest_max_lot_size'] == 'InpHTFBOSRetestMaxLotSize'
    assert FLAT_MAP['htf_bos_require_ob_confluence'] == 'InpHTFBOSRequireOBConfluence'
    assert FLAT_MAP['htf_bos_ob_lookback_bars'] == 'InpHTFBOSOBLookbackBars'
    assert FLAT_MAP['htf_bos_ob_tolerance_atr'] == 'InpHTFBOSOBToleranceATR'
    assert FLAT_MAP['htf_bos_ob_min_impulse_atr'] == 'InpHTFBOSOBMinImpulseATR'
    assert FLAT_MAP['enable_structure_momentum_hold'] == 'InpEnableStructureMomentumHold'
    assert FLAT_MAP['structure_hold_families'] == 'InpStructureHoldFamilies'
    assert FLAT_MAP['struct_skip_mfe_exits'] == 'InpStructSkipMFEExits'
    assert FLAT_MAP['struct_mom_lookback_bars'] == 'InpStructMomLookbackBars'
    assert FLAT_MAP['struct_mom_min_net_atr'] == 'InpStructMomMinNetATR'
    assert FLAT_MAP['struct_mom_strong_rev_body_atr'] == 'InpStructMomStrongRevBodyATR'
    assert FLAT_MAP['struct_mom_break_buffer_atr'] == 'InpStructMomBreakBufferATR'
    assert FLAT_MAP['structure_hold_require_quality'] == 'InpStructureHoldRequireQuality'
    assert FLAT_MAP['structure_hold_quality_tf'] == 'InpStructureHoldQualityTF'
    assert FLAT_MAP['structure_hold_quality_bars'] == 'InpStructureHoldQualityBars'
    assert FLAT_MAP['structure_hold_quality_min_atr'] == 'InpStructureHoldQualityMinATR'
    assert FLAT_MAP['structure_hold_quality_require_strong_break'] == 'InpStructureHoldQualityRequireStrongBreak'
    assert FLAT_MAP['structure_hold_dynamic_release'] == 'InpStructureHoldDynamicRelease'
    assert FLAT_MAP['structure_hold_release_min_r'] == 'InpStructureHoldReleaseMinR'
    assert FLAT_MAP['structure_hold_release_require_reverse_continuation'] == 'InpStructureHoldReleaseRequireReverseContinuation'

    content = strategy_to_set('test', {
        'version': 'test',
        'bos_retest_entry': True,
        'bos_lock_bounce_entries': False,
        'bos_retest_direct_entry': True,
        'bos_retest_tf': 60,
        'bos_retest_tf2': 240,
        'bos_retest_lookback_bars': 96,
        'bos_retest_pivot_bars': 3,
        'bos_retest_break_buffer_atr': 0.05,
        'bos_retest_min_extension_atr': 0.45,
        'bos_retest_sl_buffer': 0.7,
        'bos_retest_tolerance': 0.35,
        'bos_retest_max_bars': 1440,
        'bos_retest_weight': 2.5,
        'bos_retest_max_lot_size': 0.6,
        'htf_bos_retest_entry': True,
        'htf_bos_retest_direct_entry': False,
        'htf_bos_retest_tf': 240,
        'htf_bos_retest_tf2': 0,
        'htf_bos_retest_lookback_bars': 120,
        'htf_bos_retest_pivot_bars': 2,
        'htf_bos_retest_break_buffer_atr': 0.08,
        'htf_bos_retest_min_extension_atr': 0.8,
        'htf_bos_retest_sl_buffer': 0.7,
        'htf_bos_retest_tolerance': 0.22,
        'htf_bos_retest_max_bars': 1440,
        'htf_bos_retest_weight': 8.0,
        'htf_bos_retest_max_lot_size': 0.8,
        'htf_bos_require_ob_confluence': True,
        'htf_bos_ob_lookback_bars': 36,
        'htf_bos_ob_tolerance_atr': 0.45,
        'htf_bos_ob_min_impulse_atr': 0.75,
        'enable_structure_momentum_hold': True,
        'structure_hold_families': 'BOS,HTFPB',
        'struct_skip_mfe_exits': True,
        'struct_mom_lookback_bars': 6,
        'struct_mom_min_net_atr': 0.3,
        'struct_mom_strong_rev_body_atr': 0.55,
        'struct_mom_break_buffer_atr': 0.1,
        'structure_hold_require_quality': True,
        'structure_hold_quality_tf': 5,
        'structure_hold_quality_bars': 3,
        'structure_hold_quality_min_atr': 0.35,
        'structure_hold_quality_require_strong_break': True,
        'structure_hold_dynamic_release': True,
        'structure_hold_release_min_r': 0.4,
        'structure_hold_release_require_reverse_continuation': True,
    })
    assert 'InpBOSRetestEntry=true' in content
    assert 'InpBOSLockBounceEntries=false' in content
    assert 'InpBOSRetestDirectEntry=true' in content
    assert 'InpBOSRetestTF=60' in content
    assert 'InpBOSRetestTF2=240' in content
    assert 'InpBOSRetestLookbackBars=96' in content
    assert 'InpBOSRetestPivotBars=3' in content
    assert 'InpBOSRetestBreakBufferATR=0.05' in content
    assert 'InpBOSRetestMinExtensionATR=0.45' in content
    assert 'InpBOSRetestSLBuffer=0.7' in content
    assert 'InpBOSRetestTolerance=0.35' in content
    assert 'InpBOSRetestMaxBars=1440' in content
    assert 'InpBOSRetestWeight=2.5' in content
    assert 'InpBOSRetestMaxLotSize=0.6' in content
    assert 'InpHTFBOSRetestEntry=true' in content
    assert 'InpHTFBOSRetestDirectEntry=false' in content
    assert 'InpHTFBOSRetestTF=240' in content
    assert 'InpHTFBOSRetestTF2=0' in content
    assert 'InpHTFBOSRetestLookbackBars=120' in content
    assert 'InpHTFBOSRetestPivotBars=2' in content
    assert 'InpHTFBOSRetestBreakBufferATR=0.08' in content
    assert 'InpHTFBOSRetestMinExtensionATR=0.8' in content
    assert 'InpHTFBOSRetestSLBuffer=0.7' in content
    assert 'InpHTFBOSRetestTolerance=0.22' in content
    assert 'InpHTFBOSRetestMaxBars=1440' in content
    assert 'InpHTFBOSRetestWeight=8.0' in content
    assert 'InpHTFBOSRetestMaxLotSize=0.8' in content
    assert 'InpHTFBOSRequireOBConfluence=true' in content
    assert 'InpHTFBOSOBLookbackBars=36' in content
    assert 'InpHTFBOSOBToleranceATR=0.45' in content
    assert 'InpHTFBOSOBMinImpulseATR=0.75' in content
    assert 'InpEnableStructureMomentumHold=true' in content
    assert 'InpStructureHoldFamilies=BOS,HTFPB' in content
    assert 'InpStructSkipMFEExits=true' in content
    assert 'InpStructMomLookbackBars=6' in content
    assert 'InpStructMomMinNetATR=0.3' in content
    assert 'InpStructMomStrongRevBodyATR=0.55' in content
    assert 'InpStructMomBreakBufferATR=0.1' in content
    assert 'InpStructureHoldRequireQuality=true' in content
    assert 'InpStructureHoldQualityTF=5' in content
    assert 'InpStructureHoldQualityBars=3' in content
    assert 'InpStructureHoldQualityMinATR=0.35' in content
    assert 'InpStructureHoldQualityRequireStrongBreak=true' in content
    assert 'InpStructureHoldDynamicRelease=true' in content
    assert 'InpStructureHoldReleaseMinR=0.4' in content
    assert 'InpStructureHoldReleaseRequireReverseContinuation=true' in content


def test_micro_bos_confluence_params_in_set():
    assert FLAT_MAP['enable_micro_bos_retest'] == 'InpEnableMicroBOSRetest'
    assert FLAT_MAP['micro_bos_tf'] == 'InpMicroBOSTF'
    assert FLAT_MAP['micro_bos_lookback_bars'] == 'InpMicroBOSLookbackBars'
    assert FLAT_MAP['micro_bos_pivot_bars'] == 'InpMicroBOSPivotBars'
    assert FLAT_MAP['micro_bos_break_buffer_atr'] == 'InpMicroBOSBreakBufferATR'
    assert FLAT_MAP['micro_bos_min_net_atr'] == 'InpMicroBOSMinNetATR'
    assert FLAT_MAP['micro_bos_extension_atr'] == 'InpMicroBOSExtensionATR'
    assert FLAT_MAP['micro_bos_retest_tolerance_atr'] == 'InpMicroBOSRetestToleranceATR'
    assert FLAT_MAP['micro_bos_zone_atr'] == 'InpMicroBOSZoneATR'
    assert FLAT_MAP['micro_bos_sl_atr'] == 'InpMicroBOSSLATR'
    assert FLAT_MAP['micro_bos_pos_mult'] == 'InpMicroBOSPosMult'
    assert FLAT_MAP['micro_bos_max_bars'] == 'InpMicroBOSMaxBars'
    assert FLAT_MAP['micro_bos_cooldown_bars'] == 'InpMicroBOSCooldownBars'
    assert FLAT_MAP['micro_bos_min_bounce_sec'] == 'InpMicroBOSMinBounceSec'
    assert FLAT_MAP['micro_bos_max_bounce_sec'] == 'InpMicroBOSMaxBounceSec'
    assert FLAT_MAP['micro_bos_min_final_pos_mult'] == 'InpMicroBOSMinFinalPosMult'
    assert FLAT_MAP['micro_bos_require_h4_aligned'] == 'InpMicroBOSRequireH4Aligned'
    assert FLAT_MAP['micro_bos_require_continuation'] == 'InpMicroBOSRequireContinuation'
    assert FLAT_MAP['micro_bos_continuation_tf'] == 'InpMicroBOSContinuationTF'
    assert FLAT_MAP['micro_bos_continuation_bars'] == 'InpMicroBOSContinuationBars'
    assert FLAT_MAP['micro_bos_continuation_min_atr'] == 'InpMicroBOSContinuationMinATR'
    assert FLAT_MAP['micro_bos_use_structure_hold'] == 'InpMicroBOSUseStructureHold'
    assert FLAT_MAP['micro_bos_require_zone_confluence'] == 'InpMicroBOSRequireZoneConfluence'
    assert FLAT_MAP['micro_bos_confluence_allow_ob'] == 'InpMicroBOSConfluenceAllowOB'
    assert FLAT_MAP['micro_bos_confluence_allow_fvg'] == 'InpMicroBOSConfluenceAllowFVG'
    assert FLAT_MAP['micro_bos_confluence_tolerance_atr'] == 'InpMicroBOSConfluenceToleranceATR'

    content = strategy_to_set('test', {
        'version': 'test',
        'enable_micro_bos_retest': True,
        'micro_bos_tf': 5,
        'micro_bos_lookback_bars': 48,
        'micro_bos_pivot_bars': 2,
        'micro_bos_break_buffer_atr': 0.05,
        'micro_bos_min_net_atr': 0.25,
        'micro_bos_extension_atr': 0.35,
        'micro_bos_retest_tolerance_atr': 0.20,
        'micro_bos_zone_atr': 0.30,
        'micro_bos_sl_atr': 0.70,
        'micro_bos_pos_mult': 0.20,
        'micro_bos_max_bars': 72,
        'micro_bos_cooldown_bars': 24,
        'micro_bos_min_bounce_sec': 0,
        'micro_bos_max_bounce_sec': 90,
        'micro_bos_min_final_pos_mult': 0.0,
        'micro_bos_require_h4_aligned': True,
        'micro_bos_require_continuation': True,
        'micro_bos_continuation_tf': 5,
        'micro_bos_continuation_bars': 2,
        'micro_bos_continuation_min_atr': 0.20,
        'micro_bos_use_structure_hold': False,
        'micro_bos_require_zone_confluence': True,
        'micro_bos_confluence_allow_ob': True,
        'micro_bos_confluence_allow_fvg': False,
        'micro_bos_confluence_tolerance_atr': 0.35,
    })
    assert 'InpEnableMicroBOSRetest=true' in content
    assert 'InpMicroBOSTF=5' in content
    assert 'InpMicroBOSLookbackBars=48' in content
    assert 'InpMicroBOSPivotBars=2' in content
    assert 'InpMicroBOSBreakBufferATR=0.05' in content
    assert 'InpMicroBOSMinNetATR=0.25' in content
    assert 'InpMicroBOSExtensionATR=0.35' in content
    assert 'InpMicroBOSRetestToleranceATR=0.2' in content
    assert 'InpMicroBOSZoneATR=0.3' in content
    assert 'InpMicroBOSSLATR=0.7' in content
    assert 'InpMicroBOSPosMult=0.2' in content
    assert 'InpMicroBOSMaxBars=72' in content
    assert 'InpMicroBOSCooldownBars=24' in content
    assert 'InpMicroBOSMinBounceSec=0' in content
    assert 'InpMicroBOSMaxBounceSec=90' in content
    assert 'InpMicroBOSMinFinalPosMult=0.0' in content
    assert 'InpMicroBOSRequireH4Aligned=true' in content
    assert 'InpMicroBOSRequireContinuation=true' in content
    assert 'InpMicroBOSContinuationTF=5' in content
    assert 'InpMicroBOSContinuationBars=2' in content
    assert 'InpMicroBOSContinuationMinATR=0.2' in content
    assert 'InpMicroBOSUseStructureHold=false' in content
    assert 'InpMicroBOSRequireZoneConfluence=true' in content
    assert 'InpMicroBOSConfluenceAllowOB=true' in content
    assert 'InpMicroBOSConfluenceAllowFVG=false' in content
    assert 'InpMicroBOSConfluenceToleranceATR=0.35' in content


def test_fvg_mitigation_params_in_set():
    assert FLAT_MAP['fvg_require_h1_aligned'] == 'InpFVGRequireH1Aligned'
    assert FLAT_MAP['fvg_fade_max_entry_offset_r'] == 'InpFVGFadeMaxEntryOffsetR'

    content = strategy_to_set('test', {
        'version': 'TEST',
        'enable_fvg': True,
        'fvg_enable_fade_entry': True,
        'fvg_require_h1_aligned': True,
        'fvg_fade_max_entry_offset_r': -1.0,
        'fvg_fade_tp_mult': 1.8,
        'fvg_fade_pos_mult': 0.3,
        'fvg_fade_max_lot_size': 0.04,
        'fvg_require_confirm_candle': True,
    })
    assert 'InpEnableFVG=true' in content
    assert 'InpFVGEnableFadeEntry=true' in content
    assert 'InpFVGRequireH1Aligned=true' in content
    assert 'InpFVGFadeMaxEntryOffsetR=-1.0' in content
    assert 'InpFVGFadeTPMult=1.8' in content
    assert 'InpFVGFadePosMult=0.3' in content
    assert 'InpFVGFadeMaxLotSize=0.04' in content
    assert 'InpFVGRequireConfirmCandle=true' in content


def test_strong_sweep_reversal_params_in_set():
    assert FLAT_MAP['enable_strong_sweep_reversal'] == 'InpEnableStrongSweepReversal'
    assert FLAT_MAP['strong_sweep_require_dp'] == 'InpStrongSweepRequireDP'
    assert FLAT_MAP['strong_sweep_continuation_min_atr'] == 'InpStrongSweepContinuationMinATR'
    assert FLAT_MAP['strong_sweep_max_lot_size'] == 'InpStrongSweepMaxLotSize'

    cfg = {
        'version': 'TEST',
        'enable_strong_sweep_reversal': True,
        'strong_sweep_tf': 5,
        'strong_sweep_lookback_bars': 60,
        'strong_sweep_require_dp': True,
        'strong_sweep_discount_max': 0.45,
        'strong_sweep_premium_min': 0.55,
        'strong_sweep_require_continuation': True,
        'strong_sweep_continuation_min_atr': 0.18,
        'strong_sweep_max_lot_size': 0.03,
    }
    content = strategy_to_set('test', cfg)
    assert 'InpEnableStrongSweepReversal=true' in content
    assert 'InpStrongSweepLookbackBars=60' in content
    assert 'InpStrongSweepRequireDP=true' in content
    assert 'InpStrongSweepDiscountMax=0.45' in content
    assert 'InpStrongSweepContinuationMinATR=0.18' in content
    assert 'InpStrongSweepMaxLotSize=0.03' in content


def test_sdflip_failure_cluster_sentinel_in_set():
    content = strategy_to_set('test', {
        'version': 'TEST',
        'enable_failure_reentry_confirm': True,
        'failure_reentry_record_passive_loss': True,
        'failure_reentry_family_filter': 'SWP,OB',
    })
    assert 'InpEnableFailureReentryConfirm=true' in content
    assert 'InpFailureReentryRecordPassiveLoss=true' in content
    assert 'InpFailureReentryFamilyFilter=SWP,OB' in content


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


def _setup_cli_backtest_dirs(tmp_path):
    """为 generate_ini 测试准备隔离目录"""
    bt_dir = tmp_path / 'bt'
    bt_dir.mkdir()
    mt5_main = tmp_path / 'mt5'
    mt5_config = mt5_main / 'config'
    mt5_config.mkdir(parents=True)
    reports_dir = bt_dir / 'reports'
    reports_dir.mkdir(parents=True)
    return bt_dir, mt5_main


def test_cli_generate_ini_uses_bar_period_min(monkeypatch, tmp_path):
    """macOS 回测脚本应优先使用策略 bar_period_min / bar_tf，而非 backtest_defaults.period

    复现审计发现：Live QS 跑 M1，但回测 Period= 被写死为 M5，
    导致所有回测数据不可信。
    """
    ini_dir, mt5_main = _setup_cli_backtest_dirs(tmp_path)
    monkeypatch.setattr(cli, 'INI_DIR', ini_dir)
    monkeypatch.setattr(cli, 'MT5_MAIN', str(mt5_main))

    config = {
        'v11xau-qs': {
            'bar_period_min': 1,   # M1 — 应被优先使用
            'version': 'V11XAU-QS',
        },
        'backtest_defaults': {
            'period': 'M5',        # 旧的错误后备值
            'deposit': 200,
            'leverage': '2000',
        },
        'mt5_account': {},
    }

    path = cli.generate_ini('v11xau-qs', 'XAUUSDm', '2026.06.01', '2026.06.02', config)
    content = Path(path).read_text(encoding='utf-8')
    assert 'Period=M1' in content, f'应使用策略 bar_period_min=1 → M1，但实际内容:{content}'
    assert 'Period=M5' not in content


def test_cli_generate_ini_falls_back_to_bar_tf(monkeypatch, tmp_path):
    """无 bar_period_min 时应回退到 bar_tf"""
    ini_dir, mt5_main = _setup_cli_backtest_dirs(tmp_path)
    monkeypatch.setattr(cli, 'INI_DIR', ini_dir)
    monkeypatch.setattr(cli, 'MT5_MAIN', str(mt5_main))

    config = {
        'v11btc-test': {
            'bar_tf': 5,           # M5 — 后备
            'version': 'V11BTC',
        },
        'backtest_defaults': {
            'period': 'M1',
            'deposit': 200,
            'leverage': '2000',
        },
        'mt5_account': {},
    }

    path = cli.generate_ini('v11btc-test', 'BTCUSDm', '2026.06.01', '2026.06.02', config)
    content = Path(path).read_text(encoding='utf-8')
    assert 'Period=M5' in content, f'应使用 bar_tf=5 → M5，但实际内容:{content}'


def test_cli_generate_ini_falls_back_to_period_when_no_bar_tf(monkeypatch, tmp_path):
    """无 bar_period_min 也无 bar_tf 时，用 backtest_defaults.period 作为最终后备"""
    ini_dir, mt5_main = _setup_cli_backtest_dirs(tmp_path)
    monkeypatch.setattr(cli, 'INI_DIR', ini_dir)
    monkeypatch.setattr(cli, 'MT5_MAIN', str(mt5_main))

    config = {
        'old-strategy': {
            'period': 'M15',       # 策略级 period
            'version': 'OLD',
        },
        'backtest_defaults': {
            'period': 'M1',
            'deposit': 200,
            'leverage': '2000',
        },
        'mt5_account': {},
    }

    path = cli.generate_ini('old-strategy', 'XAUUSDm', '2026.06.01', '2026.06.02', config)
    content = Path(path).read_text(encoding='utf-8')
    assert 'Period=M15' in content, f'应使用策略级 period=M15 作为后备，但实际内容:{content}'


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

SAMPLE_ADDON_SEGMENT = """CS\t0\t00:14:08.437\tTester\tBTCUSDm,M1: testing of Experts\\WaiTrade2\\WaiTrade_OB.ex5 from 2026.03.22 00:00 to 2026.05.21 00:00 started with inputs:
CS\t0\t00:14:09.534\tWaiTrade_OB (BTCUSDm,M1)\t2026.03.24 11:41:01   ENTRY_DIAG stage=entry_engine ticket=0 dir=-1 hour=11 ob_age=9 touch=278 strength=5.00 ds=1.00 fresh=0 cont=0 h1=1 deep=1 htf=0 bounce_sec=27 bounce_ob=0.276 confirm_pos=-0.791 touch=71258.60 confirm=71238.77 risk_atr=1.68 spread_risk=0.065 pos_mult=0.52 score=4 entry=71224.77 sl=71441.55
CS\t0\t00:14:09.536\tTrade\t2026.03.24 11:41:01   market sell 0.01 BTCUSDm sl: 71441.55 tp: 71116.95 (71224.77 / 71238.77)
CS\t0\t00:14:09.537\tTrades\t2026.03.24 11:41:01   deal #2 sell 0.01 BTCUSDm at 71224.77 done (based on order #2)
CS\t0\t00:14:09.538\tWaiTrade_OB (BTCUSDm,M1)\t2026.03.24 11:41:01   寮€浠撴垚鍔? WT V11-R10-Q6K S x0.5 ticket=2 price=71224.77 lot=0.01 bounce_sec=27 bounce_ob=0.276 confirm_pos=-0.791 touch=71258.60 confirm=71238.77
CS\t0\t00:14:09.539\tTrade\t2026.03.24 11:45:01   market sell 0.02 BTCUSDm sl: 71441.55 (71190.00 / 71200.00)
CS\t0\t00:14:09.539\tTrades\t2026.03.24 11:45:01   deal #6 sell 0.02 BTCUSDm at 71200.00 done (based on order #6)
CS\t0\t00:14:09.540\tWaiTrade_OB (BTCUSDm,M1)\t2026.03.24 11:45:01   强势延续加仓: source=2 addon=6 r=1.20 lot=0.02
CS\t0\t00:14:09.541\tTrade\t2026.03.24 11:53:06   take profit triggered #2 sell 0.01 BTCUSDm 71224.77 sl: 71441.55 tp: 71116.95 [#3 buy 0.01 BTCUSDm at 71116.95]
CS\t0\t00:14:09.541\tTrades\t2026.03.24 11:53:06   deal #3 buy 0.01 BTCUSDm at 71115.61 done (based on order #3)
CS\t0\t00:14:09.541\tWaiTrade_OB (BTCUSDm,M1)\t2026.03.24 11:53:06   POSITION_GONE_DIAG ticket=2 dir=-1 entry=71224.77 sl_initial=71441.55 peak_r=0.49 raw_peak_r=0.49 dtp_peak_r=0.00 open_bar=717 last_sl= be=false trail=0 partial=false dtp_partial=false deep=true htf=false rev=false addon=false
CS\t0\t00:14:09.542\tTrade\t2026.03.24 11:54:06   market buy 0.02 BTCUSDm, close #6 (71100.00 / 71110.00 / 71100.00)
CS\t0\t00:14:09.542\tTrades\t2026.03.24 11:54:06   deal #7 buy 0.02 BTCUSDm at 71110.00 done (based on order #7)
CS\t0\t00:14:09.542\tWaiTrade_OB (BTCUSDm,M1)\t2026.03.24 11:54:06   POSITION_GONE_DIAG ticket=6 dir=-1 entry=71200.00 sl_initial=71441.55 peak_r=0.37 raw_peak_r=0.37 dtp_peak_r=0.00 open_bar=721 last_sl= be=false trail=0 partial=false dtp_partial=false deep=true htf=false rev=false addon=true
CS\t0\t00:14:09.554\tTester\tfinal balance 240.00
CS\t0\t00:14:09.554\tTester\t1000 ticks, 200 bars generated
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


def test_parse_agent_log_segment_details_extracts_addon_trade():
    segment = split_agent_log_segments(SAMPLE_ADDON_SEGMENT)[0]
    details = parse_agent_log_segment_details(segment['lines'], 'BTCUSDm')
    addon_trade = next(t for t in details['trades'] if t['ticket'] == 6)
    assert addon_trade['addon'] is True
    assert addon_trade['dir'] == 'sell'
    assert addon_trade['signal_type'] == 'addon'
    assert addon_trade['entry'] == 71200.00
    assert addon_trade['initial_sl'] == 71441.55
    assert round(addon_trade['r'], 3) > 0


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

def test_backtest_digest_extract_date_token_uses_report_suffix_date():
    token = _extract_date_token(
        Path('results/backtest/v11-btc1-qual232_20240601_20260531_20260701.txt')
    )
    assert token == '20260701'


def test_backtest_digest_expected_log_markers_falls_back_to_version_lookup(monkeypatch):
    fake_config = {
        'defaults': {},
        'v11-btc1-qual232': {
            'version': 'V11-BTC1-QUAL232',
        },
    }

    monkeypatch.setattr(backtest_digest, 'CONFIG_PATH', Path('ignored.yaml'))
    monkeypatch.setattr(backtest_digest.yaml, 'safe_load', lambda _text: fake_config)
    monkeypatch.setattr(Path, 'read_text', lambda self, encoding='utf-8': 'ignored')

    markers = expected_log_markers({'strategy_name': 'V11-BTC1-QUAL232'})

    assert markers == ['V11-BTC1-QUAL232']


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
