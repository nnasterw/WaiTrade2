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
    "require_double_touch": "InpRequireDoubleTch",
    "double_touch_window_min": "InpDoubleTchWindowMin",
    "min_ob_spread_mult": "InpMinOBSpreadMult",
    "min_risk_spread_ratio": "InpMinRiskSpreadRatio",
    "min_abs_risk_usd": "InpMinAbsRiskUSD",
    "min_ob_body_pct": "InpMinOBBodyPct",
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
    "cooldown_bars": "InpCooldownBars",
    "no_entry_hours": "InpNoEntryHours",
    "close_retry_cooldown_sec": "InpCloseRetryCooldownSec",
    "max_entries_per_ob": "InpMaxEntriesPerOB",
    "ob_reentry_cooldown_min": "InpOBReentryCooldownMin",
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
    "fixed_tp_r": "InpFixedTPR",
    # 部分平仓
    "partial_close_r": "InpPartialCloseR",
    "partial_close_pct": "InpPartialClosePct",
    # v9.8a EntryEngine状态机
    "enable_entry_engine": "InpEnableEntryEngine",
    "enable_exit_debug": "InpEnableExitDebug",
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
