#!/usr/bin/env python3
"""YAML策略定义 → MT5 .set 文件转换器"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("错误: 需要 PyYAML，请执行 pip install pyyaml", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_YAML = SCRIPT_DIR.parent / "config" / "strategies.yaml"

NON_STRATEGY_KEYS = {'defaults', 'symbols', 'backtest_defaults', 'mt5_account'}

# YAML key → .set INP 名称映射
FLAT_MAP = {
    "bounce_pct": "InpBouncePct",
    "timeout_min": "InpTimeoutMin",
    "max_entry_offset_r": "InpMaxEntryOffsetR",
    "entry_depth_pct": "InpEntryDepthPct",
    "entry_depth_filter": "InpEntryDepthFilter",
    "deep_entry_boost": "InpDeepEntryBoost",
    "entry_confirm_bars": "InpEntryConfirmBars",
    "bounce_close_confirm_bars": "InpBounceCloseConfirmBars",
    "bounce_close_tf": "InpBounceCloseTF",
    "bounce_close_buffer_pct": "InpBounceCloseBufferPct",
    "bounce_close_require_body": "InpBounceCloseRequireBody",
    "enable_confirm_pullback": "InpEnableConfirmPullback",
    "confirm_pullback_pct": "InpConfirmPullbackPct",
    "confirm_pullback_wait_sec": "InpConfirmPullbackWaitSec",
    "confirm_pullback_max_adverse_pct": "InpConfirmPullbackMaxAdversePct",
    "enable_entry_momentum_filter": "InpEnableEntryMomentumFilter",
    "entry_momentum_tf": "InpEntryMomentumTF",
    "entry_block_counter_strong": "InpEntryBlockCounterStrong",
    "entry_require_counter_weak": "InpEntryRequireCounterWeak",
    "require_double_touch": "InpRequireDoubleTch",
    "double_touch_window_min": "InpDoubleTchWindowMin",
    "min_ob_spread_mult": "InpMinOBSpreadMult",
    "min_risk_spread_ratio": "InpMinRiskSpreadRatio",
    "min_abs_risk_usd": "InpMinAbsRiskUSD",
    "min_ob_body_pct": "InpMinOBBodyPct",
    "min_impulse_body_pct": "InpMinImpulseBodyPct",
    "min_impulse_vol_ratio": "InpMinImpulseVolRatio",
    "structure_break_bars": "InpStructureBreakBars",
    "structure_break_atr": "InpStructureBreakATR",
    "require_impulse_candle_dir": "InpRequireImpulseCandleDir",
    "enable_range_breakout": "InpEnableRangeBreakout",
    "range_breakout_only": "InpRangeBreakoutOnly",
    "range_breakout_bars": "InpRangeBreakoutBars",
    "range_breakout_max_atr": "InpRangeBreakoutMaxATR",
    "range_breakout_min_spread_mult": "InpRangeBreakoutMinSpreadMult",
    "range_breakout_atr": "InpRangeBreakoutATR",
    "range_breakout_tp_mult": "InpRangeBreakoutTPMult",
    "range_breakout_body_dir": "InpRangeBreakoutBodyDir",
    "enable_liquidity_sweep": "InpEnableLiquiditySweep",
    "liquidity_sweep_only": "InpLiquiditySweepOnly",
    "sweep_lookback_bars": "InpSweepLookbackBars",
    "sweep_max_range_atr": "InpSweepMaxRangeATR",
    "sweep_min_range_spread_mult": "InpSweepMinRangeSpreadMult",
    "sweep_min_penetration_atr": "InpSweepMinPenetrationATR",
    "sweep_min_wick_pct": "InpSweepMinWickPct",
    "sweep_tp_mult": "InpSweepTPMult",
    "no_ob_start_hour": "InpNoOBStartHour",
    "no_ob_end_hour": "InpNoOBEndHour",
    "min_ob_strength": "InpMinOBStrength",
    "max_risk_atr": "InpMaxRiskATR",
    "max_counter_risk_atr": "InpMaxCounterRiskATR",
    "consolidate_ob": "InpConsolidateOB",
    "sl_buffer_atr": "InpSLBufferATR",
    "impulse_atr_mult": "InpImpulseATRMult",
    "impulse_lookback": "InpImpulseLookback",
    "atr_period": "InpATRPeriod",
    "breakeven_r": "InpBreakevenR",
    "breakeven_lock_r": "InpBreakevenLockR",
    "early_loss_cut_r": "InpEarlyLossCutR",
    "mfe_fail_min_r": "InpMFEFailMinR",
    "mfe_fail_exit_r": "InpMFEFailExitR",
    "no_mfe_exit_bars": "InpNoMFEExitBars",
    "no_mfe_min_peak_r": "InpNoMFEMinPeakR",
    "no_mfe_exit_r": "InpNoMFEExitR",
    "enable_failure_reverse": "InpEnableFailureReverse",
    "reverse_on_early_loss": "InpReverseOnEarlyLoss",
    "reverse_on_mfe_fail": "InpReverseOnMFEFail",
    "reverse_on_no_mfe": "InpReverseOnNoMFE",
    "failure_reverse_risk_mult": "InpFailureReverseRiskMult",
    "failure_reverse_lot_mult": "InpFailureReverseLotMult",
    "failure_reverse_tp_r": "InpFailureReverseTPR",
    "failure_reverse_allow_chain": "InpFailureReverseAllowChain",
    "dtp_trigger_r": "InpDTPTriggerR",
    "dtp_retrace": "InpDTPRetrace",
    "adaptive_dtp": "InpAdaptiveDTP",
    "dtp_stage2_trigger_r": "InpDTPStage2TriggerR",
    "dtp_stage2_retrace": "InpDTPStage2Retrace",
    "dtp_stage3_trigger_r": "InpDTPStage3TriggerR",
    "dtp_stage3_retrace": "InpDTPStage3Retrace",
    "dtp_exit_mode": "InpDTPExitMode",
    "dtp_partial_pct": "InpDTPPartialPct",
    "dtp_post_partial_retrace": "InpDTPPostPartialRetrace",
    "dtp_post_partial_lock_r": "InpDTPPostPartialLockR",
    "dtp_reset_peak_after_partial": "InpDTPResetPeakAfterPartial",
    "time_exit_bars": "InpTimeExitBars",
    "time_decay_tp": "InpTimeDecayTP",
    "risk_percent": "InpRiskPercent",
    "fixed_lot_size": "InpFixedLotSize",
    "enable_pos_mult": "InpEnablePosMult",
    "max_pos_mult": "InpMaxPosMult",
    "max_lot_size": "InpMaxLotSize",
    "max_concurrent": "InpMaxConcurrent",
    "free_run_min_r": "InpFreeRunMinR",
    "cooldown_bars": "InpCooldownBars",
    "no_entry_hours": "InpNoEntryHours",
    "no_buy_hours": "InpNoBuyHours",
    "no_sell_hours": "InpNoSellHours",
    "low_risk_hours": "InpLowRiskHours",
    "low_risk_hour_mult": "InpLowRiskHourMult",
    "high_risk_hours": "InpHighRiskHours",
    "high_risk_hour_mult": "InpHighRiskHourMult",
    "late_bounce_sec": "InpLateBounceSec",
    "late_bounce_mult": "InpLateBounceMult",
    "bounce_sweet_min_pct": "InpBounceSweetMinPct",
    "bounce_sweet_max_pct": "InpBounceSweetMaxPct",
    "outside_bounce_sweet_mult": "InpOutsideBounceSweetMult",
    "bad_risk_min": "InpBadRiskMin",
    "bad_risk_max": "InpBadRiskMax",
    "bad_risk_mult": "InpBadRiskMult",
    "large_risk_min": "InpLargeRiskMin",
    "large_risk_mult": "InpLargeRiskMult",
    "buy_min_strength": "InpBuyMinStrength",
    "sell_min_strength": "InpSellMinStrength",
    "buy_pos_mult": "InpBuyPosMult",
    "sell_pos_mult": "InpSellPosMult",
    "buy_be_r": "InpBuyBE_R",
    "buy_be_lock": "InpBuyBE_Lock",
    "sell_be_r": "InpSellBE_R",
    "sell_be_lock": "InpSellBE_Lock",
    "buy_dtp_trigger_r": "InpBuyDTPTriggerR",
    "buy_dtp_retrace": "InpBuyDTPRetrace",
    "sell_dtp_trigger_r": "InpSellDTPTriggerR",
    "sell_dtp_retrace": "InpSellDTPRetrace",
    "enable_strong_addon": "InpEnableStrongAddOn",
    "strong_addon_trigger_r": "InpStrongAddOnTriggerR",
    "strong_addon_step_r": "InpStrongAddOnStepR",
    "strong_addon_max_count": "InpStrongAddOnMaxCount",
    "strong_addon_lot_mult": "InpStrongAddOnLotMult",
    "strong_addon_risk_mult": "InpStrongAddOnRiskMult",
    "strong_addon_min_spread_ratio": "InpStrongAddOnMinSpreadRatio",
    "close_retry_cooldown_sec": "InpCloseRetryCooldownSec",
    "max_entries_per_ob": "InpMaxEntriesPerOB",
    "ob_reentry_cooldown_min": "InpOBReentryCooldownMin",
    "filter_cont_age_min_bars": "InpFilterContAgeMinBars",
    "filter_cont_age_max_bars": "InpFilterContAgeMaxBars",
    "filter_cont_non_deep_only": "InpFilterContNonDeepOnly",
    "filter_buy_no_h1_min_pos_mult": "InpFilterBuyNoH1MinPosMult",
    "filter_buy_no_h1_max_pos_mult": "InpFilterBuyNoH1MaxPosMult",
    "filter_buy_no_h1_pos_mult": "InpFilterBuyNoH1PosMult",
    "boost_in_1h_ob": "InpBoostIn1HOB",
    "ds_weight": "InpDSWeight",
    "dt_addon_boost": "InpDTAddonBoost",
    "bar_period_min": "InpBarTF",
    "bars": "InpBars",
    "ob_scan_depth": "InpOBScanDepth",
    "version": "InpVersion",
    "magic_number": "InpMagicNumber",
    "spread_floor": "InpSpreadFloor",
    # v9.8 势位态动
    "trend_lookback": "InpTrendLookback",
    "swing_strength": "InpSwingStrength",
    "enable_state_filter": "InpEnableStateFilter",
    "range_be_r": "InpRangeBE_R",
    "range_time_exit": "InpRangeTimeExit",
    "trend_be_r": "InpTrendBE_R",
    "trend_be_lock": "InpTrendBE_Lock",
    "trend_dtp_retrace": "InpTrendDTPRetrace",
    "enable_scoring": "InpEnableScoring",
    "proximity_filter": "InpProximityFilter",
    "proximity_atr": "InpProximityATR",
    "min_score": "InpMinScore",
    "enable_decay_exit": "InpEnableDecayExit",
    "decay_min_r": "InpDecayMinR",
    "decay_bars": "InpDecayBars",
    "engulf_body_pct": "InpEngulfBodyPct",
    "enable_momentum_regime": "InpEnableMomentumRegime",
    "weak_exit_min_r": "InpWeakExitMinR",
    "weak_body_shrink_pct": "InpWeakBodyShrinkPct",
    "weak_wick_body_ratio": "InpWeakWickBodyRatio",
    "strong_momentum_bars": "InpStrongMomentumBars",
    "strong_min_body_growth": "InpStrongMinBodyGrowth",
    "strong_weak_reverse_body_pct": "InpStrongWeakReverseBodyPct",
    "strong_max_pullback_pct": "InpStrongMaxPullbackPct",
    "strong_dtp_retrace_mult": "InpStrongDTPRetraceMult",
    "fixed_tp_r": "InpFixedTPR",
    "ob_height_tp_mult": "InpOBHeightTPMult",
    "layered_entry_count": "InpLayeredEntryCount",
    "layered_spacing_pct": "InpLayeredSpacingPct",
    "layered_lot_mult": "InpLayeredLotMult",
    "layered_avg_tp_r": "InpLayeredAvgTP_R",
    # 部分平仓
    "partial_close_r": "InpPartialCloseR",
    "partial_close_pct": "InpPartialClosePct",
    "partial_post_lock_r": "InpPartialPostLockR",
    "partial_only_deep": "InpPartialOnlyDeep",
    # v9.8a EntryEngine状态机
    "enable_entry_engine": "InpEnableEntryEngine",
    "enable_htf_target": "InpEnableHTFTarget",
    "htf_target_tf": "InpHTFTargetTF",
    "htf_target_lookback": "InpHTFTargetLookback",
    "htf_swing_strength": "InpHTFSwingStrength",
    "htf_min_target_r": "InpHTFMinTargetR",
    "htf_max_target_r": "InpHTFMaxTargetR",
    "htf_measured_move_r": "InpHTFMeasuredMoveR",
    "htf_require_aligned": "InpHTFRequireAligned",
    "htf_partial_r": "InpHTFPartialR",
    "htf_partial_pct": "InpHTFPartialPct",
    "htf_skip_dtp": "InpHTFSkipDTP",
    "htf_skip_trail": "InpHTFSkipTrail",
    "htf_dtp_trigger_r": "InpHTFDTPTriggerR",
    "htf_dtp_retrace": "InpHTFDTPRetrace",
    "htf_dtp_post_partial_retrace": "InpHTFDTPPostPartialRetrace",
    "enable_exit_debug": "InpEnableExitDebug",
    "enable_entry_debug": "InpEnableEntryDebug",
}

# trail_levels 映射: (层级索引, 子key) → INP名称
# 注意: trail1 没有 LockMult
TRAIL_MAP = {
    (0, "trigger_r"): "InpTrail1TriggerR",
    (0, "lock_r"): "InpTrail1LockR",
    (1, "trigger_r"): "InpTrail2TriggerR",
    (1, "lock_r"): "InpTrail2LockR",
    (1, "lock_mult"): "InpTrail2LockMult",
    (2, "trigger_r"): "InpTrail3TriggerR",
    (2, "lock_r"): "InpTrail3LockR",
    (2, "lock_mult"): "InpTrail3LockMult",
}


def format_value(v):
    """将Python值转为.set文件格式"""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def strategy_to_set(name: str, cfg: dict) -> str:
    """将单个策略配置转为.set文件内容"""
    lines = []

    # 首行注释: 版本 + 描述
    desc = cfg.get("description", "")
    version = cfg.get("version", name)
    lines.append(f"; {version} — {desc}" if desc else f"; {version}")

    # 平铺字段
    for yaml_key, inp_name in FLAT_MAP.items():
        if yaml_key in cfg:
            lines.append(f"{inp_name}={format_value(cfg[yaml_key])}")

    # trail_levels 数组
    trail_levels = cfg.get("trail_levels", [])
    for idx, level in enumerate(trail_levels):
        if not isinstance(level, dict):
            continue
        for sub_key, val in level.items():
            inp_name = TRAIL_MAP.get((idx, sub_key))
            if inp_name:
                lines.append(f"{inp_name}={format_value(val)}")

    return "\n".join(lines) + "\n"


def load_strategies(yaml_path: Path) -> dict:
    """加载YAML策略文件"""
    if not yaml_path.exists():
        print(f"错误: 找不到配置文件 {yaml_path}", file=sys.stderr)
        sys.exit(1)
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        print(f"错误: YAML根节点必须是字典", file=sys.stderr)
        sys.exit(1)
    return data


def write_set(content: str, output_path: Path):
    """写入.set文件"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"已生成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="YAML策略定义 → MT5 .set 文件转换器")
    parser.add_argument("strategy", nargs="?", help="策略名称（YAML中的顶层key）")
    parser.add_argument("--all", action="store_true", help="转换所有策略")
    parser.add_argument("--output", "-o", type=Path, help="输出文件路径（单策略模式）")
    parser.add_argument("--output-dir", type=Path, help="输出目录（--all模式）")
    parser.add_argument("--config", type=Path, default=DEFAULT_YAML, help="YAML配置路径")
    args = parser.parse_args()

    if not args.strategy and not args.all:
        parser.error("请指定策略名称或使用 --all")
    if args.strategy and args.all:
        parser.error("--all 不能与策略名称同时使用")

    strategies = load_strategies(args.config)

    if args.all:
        # 批量模式 — 跳过非策略key
        non_strategy_keys = NON_STRATEGY_KEYS
        output_dir = args.output_dir or (SCRIPT_DIR.parent / "mql5" / "Presets")
        count = 0
        for name, cfg in strategies.items():
            if name in non_strategy_keys:
                continue
            if not isinstance(cfg, dict):
                continue
            content = strategy_to_set(name, cfg)
            filename = cfg.get("version", name)
            write_set(content, output_dir / f"{filename}.set")
            count += 1
        print(f"完成，共转换 {count} 个策略")
    else:
        # 单策略模式
        name = args.strategy
        if name not in strategies:
            print(f"错误: 策略 '{name}' 不存在。可用: {', '.join(strategies.keys())}", file=sys.stderr)
            sys.exit(1)
        cfg = strategies[name]
        content = strategy_to_set(name, cfg)
        if args.output:
            write_set(content, args.output)
        else:
            sys.stdout.write(content)


if __name__ == "__main__":
    main()
