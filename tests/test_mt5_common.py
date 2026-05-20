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
    })
    assert 'InpEnableLiquiditySweep=true' in content
    assert 'InpLiquiditySweepOnly=true' in content
    assert 'InpSweepLookbackBars=12' in content
    assert 'InpSweepMaxRangeATR=2.5' in content
    assert 'InpSweepMinRangeSpreadMult=4.0' in content
    assert 'InpSweepMinPenetrationATR=0.05' in content
    assert 'InpSweepMinWickPct=45.0' in content
    assert 'InpSweepTPMult=1.5' in content


def test_execution_and_scan_params_in_set():
    assert FLAT_MAP['impulse_atr_mult'] == 'InpImpulseATRMult'
    assert FLAT_MAP['impulse_lookback'] == 'InpImpulseLookback'
    assert FLAT_MAP['atr_period'] == 'InpATRPeriod'
    assert FLAT_MAP['fixed_lot_size'] == 'InpFixedLotSize'
    assert FLAT_MAP['enable_pos_mult'] == 'InpEnablePosMult'
    assert FLAT_MAP['max_pos_mult'] == 'InpMaxPosMult'
    assert FLAT_MAP['max_lot_size'] == 'InpMaxLotSize'
    assert FLAT_MAP['free_run_min_r'] == 'InpFreeRunMinR'
    assert FLAT_MAP['no_entry_hours'] == 'InpNoEntryHours'
    assert FLAT_MAP['no_buy_hours'] == 'InpNoBuyHours'
    assert FLAT_MAP['no_sell_hours'] == 'InpNoSellHours'
    assert FLAT_MAP['low_risk_hours'] == 'InpLowRiskHours'
    assert FLAT_MAP['low_risk_hour_mult'] == 'InpLowRiskHourMult'
    assert FLAT_MAP['high_risk_hours'] == 'InpHighRiskHours'
    assert FLAT_MAP['high_risk_hour_mult'] == 'InpHighRiskHourMult'
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
    assert FLAT_MAP['filter_cont_age_min_bars'] == 'InpFilterContAgeMinBars'
    assert FLAT_MAP['filter_cont_age_max_bars'] == 'InpFilterContAgeMaxBars'
    assert FLAT_MAP['filter_cont_non_deep_only'] == 'InpFilterContNonDeepOnly'
    assert FLAT_MAP['filter_buy_no_h1_min_pos_mult'] == 'InpFilterBuyNoH1MinPosMult'
    assert FLAT_MAP['filter_buy_no_h1_max_pos_mult'] == 'InpFilterBuyNoH1MaxPosMult'
    assert FLAT_MAP['filter_buy_no_h1_pos_mult'] == 'InpFilterBuyNoH1PosMult'
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
        'no_entry_hours': '0,9,12',
        'no_buy_hours': '8,10',
        'no_sell_hours': '16,22',
        'low_risk_hours': '1,3,5',
        'low_risk_hour_mult': 0.25,
        'high_risk_hours': '12,14,15',
        'high_risk_hour_mult': 2.0,
        'late_bounce_sec': 30,
        'late_bounce_mult': 0.4,
        'bounce_sweet_min_pct': 0.26,
        'bounce_sweet_max_pct': 0.34,
        'outside_bounce_sweet_mult': 0.5,
        'bad_risk_min': 150.0,
        'bad_risk_max': 200.0,
        'bad_risk_mult': 0.4,
        'large_risk_min': 300.0,
        'large_risk_mult': 1.5,
        'close_retry_cooldown_sec': 60,
        'max_entries_per_ob': 2,
        'ob_reentry_cooldown_min': 30,
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
    assert 'InpNoEntryHours=0,9,12' in content
    assert 'InpNoBuyHours=8,10' in content
    assert 'InpNoSellHours=16,22' in content
    assert 'InpLowRiskHours=1,3,5' in content
    assert 'InpLowRiskHourMult=0.25' in content
    assert 'InpHighRiskHours=12,14,15' in content
    assert 'InpHighRiskHourMult=2.0' in content
    assert 'InpLateBounceSec=30' in content
    assert 'InpLateBounceMult=0.4' in content
    assert 'InpBounceSweetMinPct=0.26' in content
    assert 'InpBounceSweetMaxPct=0.34' in content
    assert 'InpOutsideBounceSweetMult=0.5' in content
    assert 'InpBadRiskMin=150.0' in content
    assert 'InpBadRiskMax=200.0' in content
    assert 'InpBadRiskMult=0.4' in content
    assert 'InpLargeRiskMin=300.0' in content
    assert 'InpLargeRiskMult=1.5' in content
    assert 'InpCloseRetryCooldownSec=60' in content
    assert 'InpMaxEntriesPerOB=2' in content
    assert 'InpOBReentryCooldownMin=30' in content
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

    content = strategy_to_set('test', {
        'version': 'test',
        'layered_entry_count': 2,
        'layered_spacing_pct': 0.33,
        'layered_lot_mult': 1.5,
        'layered_avg_tp_r': 0.0,
    })
    assert 'InpLayeredEntryCount=2' in content
    assert 'InpLayeredSpacingPct=0.33' in content
    assert 'InpLayeredLotMult=1.5' in content
    assert 'InpLayeredAvgTP_R=0.0' in content


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

import tempfile
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

def test_backtest_main_parses_days():
    called_with = {}

    def fake_run(strategy_names, symbols, date_from, date_to, days, config, timeout):
        called_with['strategies'] = strategy_names
        called_with['symbols'] = symbols
        called_with['days'] = days
        called_with['timeout'] = timeout

    backtest_main(
        'test',
        fake_run,
        args=['--strategy', 'v99g1', '--symbol', 'XAUUSDm', '--days', '30'],
    )
    assert called_with['strategies'] == ['v99g1']
    assert called_with['symbols'] == ['XAUUSDm']
    assert called_with['days'] == 30
    assert called_with['timeout'] == 300


def test_backtest_main_parses_from_to():
    called_with = {}

    def fake_run(strategy_names, symbols, date_from, date_to, days, config, timeout):
        called_with['date_from'] = date_from
        called_with['date_to'] = date_to
        called_with['days'] = days

    backtest_main(
        'test',
        fake_run,
        args=['--strategy', 'v99g1', '--symbols', 'all', '--from', '2026.01.01', '--to', '2026.04.01'],
    )
    assert called_with['date_from'] == '2026.01.01'
    assert called_with['date_to'] == '2026.04.01'
    assert called_with['days'] == 90
