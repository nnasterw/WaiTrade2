#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wf-yhcl v3.0 铁律合规检查器.

Iron Rule: 禁止基于 hour/day/month 等后视镜类规律的过滤规则。
本工具扫描 .set 文件,检测以下违规参数:
  - InpNoEntryHours, InpNoBuyHours, InpNoSellHours (非空)
  - InpBTCNoEntryHours, InpBTCNoBuyHours, InpBTCNoSellHours (非空)
  - InpOBBadHours (非空且 ob_bad_hour_mult < 1.0)
  - InpEntryMonths (非空,屏蔽某些月份)
  - InpHighBalanceNoEntryMonths (非空)
  - InpMonthlyDefensiveLossPct (启用月度防御)
  - InpMonthlyLossStopPct (启用月度停损)

如果发现上述参数,输出违规警告。WFYS 评分不关心,但合规研究要求通过。

Usage:
    python iron_rule_check.py <set_file>
    python iron_rule_check.py mql5/Presets/v11-btc1-trend218.set
    python iron_rule_check.py *.set   # 批量
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# 单次检测的违规参数清单 (key_pattern, violation_type, description)
# 注意: InpMonthlyDefensiveLossPct 等月度防御参数由下面 MONTHLY_DEFENSIVE_KEYS 单独检测
# 避免重复
SINGLE_PARAMS: List[Tuple[str, str, str]] = [
    (r"^InpNoEntryHours\s*=\s*\"?([^\"\n]+)\"?", "no_entry_hours", "全局禁止入场时段"),
    (r"^InpNoBuyHours\s*=\s*\"?([^\"\n]+)\"?", "no_buy_hours", "全局禁止做多时段"),
    (r"^InpNoSellHours\s*=\s*\"?([^\"\n]+)\"?", "no_sell_hours", "全局禁止做空时段"),
    (r"^InpBTCNoEntryHours\s*=\s*\"?([^\"\n]+)\"?", "btc_no_entry_hours", "BTC 禁止入场时段"),
    (r"^InpBTCNoBuyHours\s*=\s*\"?([^\"\n]+)\"?", "btc_no_buy_hours", "BTC 禁止做多时段"),
    (r"^InpBTCNoSellHours\s*=\s*\"?([^\"\n]+)\"?", "btc_no_sell_hours", "BTC 禁止做空时段"),
    (r"^InpOBBadHours\s*=\s*\"?([^\"\n]+)\"?", "ob_bad_hours", "OB 时段降权"),
    (r"^InpEntryMonths\s*=\s*\"?([^\"\n]+)\"?", "entry_months", "月份屏蔽"),
    (r"^InpHighBalanceNoEntryMonths\s*=\s*\"?([^\"\n]+)\"?", "high_balance_no_entry_months", "高余额月份屏蔽"),
    (r"^InpMonthlyLossStopPct\s*=\s*([\d.]+)", "monthly_loss_stop_pct", "月度停损比例"),
    (r"^InpNoOBStartHour\s*=\s*(-?\d+)", "no_ob_start_hour", "OB 起始时段限制"),
    (r"^InpNoOBEndHour\s*=\s*(-?\d+)", "no_ob_end_hour", "OB 终止时段限制"),
    (r"^InpLowBalanceOBBadHours\s*=\s*\"?([^\"\n]+)\"?", "low_balance_ob_bad_hours", "低余额 OB 时段降权"),
    (r"^InpBTCBadClusterHours\s*=\s*\"?([^\"\n]+)\"?", "btc_bad_cluster_hours", "坏簇时段"),
    (r"^InpNoEntryHoursBTCNoEntry\s*=\s*\"?([^\"\n]+)\"?", "no_entry_hours_btc", "BTC 复合禁用"),
]

# 月度防御检测: 任何月度防御相关参数 > 0 即违规
MONTHLY_DEFENSIVE_KEYS = [
    "InpMonthlyDefensiveLossPct",
    "InpMonthlyDefensiveUntilProfitPct",
    "InpMonthlyDefensiveMaxMonthStartBalance",
    "InpMonthlyDefensiveMinTrades",
    "InpMonthlyDefensiveNoEntryHours",
    "InpMonthlyDefensiveNoBuyHours",
    "InpMonthlyDefensiveNoSellHours",
    "InpMonthlyDefensivePosMult",
]


def parse_set_file(path: Path) -> Dict[str, str]:
    """解析 .set 文件为 dict[key] = value."""
    params: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        params[key.strip()] = value.strip()
    return params


def check_violations(params: Dict[str, str]) -> List[Dict[str, str]]:
    """扫描参数, 返回违规清单."""
    violations = []
    seen_keys = set()

    # 1. 检测单次参数
    for pattern, violation_type, description in SINGLE_PARAMS:
        for key, value in params.items():
            m = re.match(pattern, f"{key}={value}", re.IGNORECASE)
            if not m:
                continue
            actual_value = m.group(1)
            # 跳过空值或默认值
            if actual_value.strip() in ("", "0.0", "-1", "1.0", "99999.0"):
                continue
            # OB bad hour mult 必须 < 1 才算违规(0 = 禁用)
            if violation_type == "ob_bad_hours":
                mult = params.get("InpOBBadHourMult", "1.0")
                try:
                    if float(mult) >= 1.0:
                        continue
                except ValueError:
                    pass
            if violation_type == "low_balance_ob_bad_hours":
                mult = params.get("InpLowBalanceOBBadHourMult", "1.0")
                try:
                    if float(mult) >= 1.0:
                        continue
                except ValueError:
                    pass
            # no_ob_start_hour = -1 表示禁用
            if violation_type == "no_ob_start_hour":
                try:
                    if int(actual_value) < 0:
                        continue
                except ValueError:
                    pass
            if violation_type == "no_ob_end_hour":
                try:
                    if int(actual_value) < 0:
                        continue
                except ValueError:
                    pass
            # 跳过默认值的 monthly_loss_stop (80% 通常是默认值但启用)
            if violation_type == "monthly_loss_stop_pct":
                try:
                    if float(actual_value) <= 0:
                        continue
                except ValueError:
                    pass
            violations.append({
                "key": key,
                "value": actual_value,
                "type": violation_type,
                "description": description,
            })
            seen_keys.add(key)

    # 2. 检测月度防御参数
    for key in MONTHLY_DEFENSIVE_KEYS:
        if key in seen_keys:
            continue  # 已在 SINGLE_PARAMS 检测过(目前没有重叠但保险)
        if key not in params:
            continue
        value = params[key]
        try:
            if float(value) > 0:
                violations.append({
                    "key": key,
                    "value": value,
                    "type": "monthly_defensive",
                    "description": "月度防御参数",
                })
        except ValueError:
            if value.strip():  # 非空字符串
                violations.append({
                    "key": key,
                    "value": value,
                    "type": "monthly_defensive",
                    "description": "月度防御参数(非空字符串)",
                })

    return violations


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="wf-yhcl v3.0 铁律合规检查器")
    parser.add_argument("set_files", nargs="+", help="一个或多个 .set 文件")
    parser.add_argument("--strict", action="store_true",
                       help="严格模式,违规即返回非零退出码")
    parser.add_argument("--summary", action="store_true",
                       help="只输出汇总,不显示每个文件的详情")
    args = parser.parse_args(argv)

    total_violations = 0
    file_results = []

    for fpath in args.set_files:
        path = Path(fpath)
        if not path.exists():
            print(f"[跳过] {fpath} 不存在")
            continue
        params = parse_set_file(path)
        violations = check_violations(params)
        file_results.append((path, violations))
        total_violations += len(violations)
        if not args.summary:
            if violations:
                print(f"\n[!] {path.name}: 发现 {len(violations)} 处违规")
                for v in violations:
                    print(f"    {v['key']}={v['value']}  ({v['description']})")
            else:
                print(f"[OK] {path.name}: 通过铁律合规检查")

    # 汇总
    if len(args.set_files) > 1 or args.summary:
        print(f"\n{'='*60}")
        print(f"汇总: {len(args.set_files)} 个文件, 总违规 {total_violations} 处")
        passing = sum(1 for _, v in file_results if not v)
        failing = sum(1 for _, v in file_results if v)
        print(f"  通过铁律: {passing}/{len(args.set_files)}")
        print(f"  违反铁律: {failing}/{len(args.set_files)}")

    return 1 if (args.strict and total_violations > 0) else 0


if __name__ == "__main__":
    sys.exit(main())
