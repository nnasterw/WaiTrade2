#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 720d trades.csv 发现趋势 campaign 的盈利结构，不运行回测。"""
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


def load_trades(path):
    rows = []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                row["_dt"] = datetime.fromisoformat(row["time"])
                row["_r"] = float(row["r"])
                row["_pnl"] = float(row["pnl_proxy"])
            except (KeyError, TypeError, ValueError):
                continue
            row["_addon"] = str(row.get("addon", "")).lower() == "true"
            rows.append(row)
    rows.sort(key=lambda row: row["_dt"])
    return rows


def campaigns(rows, max_gap_hours=12):
    result = []
    for row in rows:
        new_campaign = (
            not result
            or row.get("dir") != result[-1][-1].get("dir")
            or (row["_dt"] - result[-1][-1]["_dt"]).total_seconds() > max_gap_hours * 3600
        )
        if new_campaign:
            result.append([row])
        else:
            result[-1].append(row)
    return result


def metrics(rows):
    if not rows:
        return {"trades": 0, "pnl": 0, "win_rate": 0, "avg_r": 0, "big_wins": 0}
    return {
        "trades": len(rows),
        "pnl": round(sum(row["_pnl"] for row in rows), 4),
        "win_rate": round(sum(row["_pnl"] > 0 for row in rows) * 100.0 / len(rows), 4),
        "avg_r": round(sum(row["_r"] for row in rows) / len(rows), 6),
        "big_wins": sum(row["_r"] > 3.0 for row in rows),
        "losses": sum(row["_pnl"] < 0 for row in rows),
    }


def discover(trades_path):
    path = Path(trades_path).resolve()
    rows = load_trades(path)
    grouped = campaigns(rows)
    first = []
    later = []
    later_independent = []
    later_addon = []
    post_win_independent = []
    post_loss_independent = []
    post_win_addon = []
    post_loss_addon = []

    for campaign in grouped:
        first.append(campaign[0])
        for index, row in enumerate(campaign[1:], 1):
            later.append(row)
            previous_won = campaign[index - 1]["_pnl"] > 0
            if row["_addon"]:
                later_addon.append(row)
                (post_win_addon if previous_won else post_loss_addon).append(row)
            else:
                later_independent.append(row)
                (post_win_independent if previous_won else post_loss_independent).append(row)

    source = path.as_posix()
    result = {
        "schema_version": 1,
        "source": source,
        "analysis": {
            "all": metrics(rows),
            "campaign_count": len(grouped),
            "multi_entry_campaigns": sum(len(item) > 1 for item in grouped),
            "campaign_first": metrics(first),
            "campaign_later": metrics(later),
            "later_independent": metrics(later_independent),
            "later_addon": metrics(later_addon),
            "post_win_independent": metrics(post_win_independent),
            "post_loss_independent": metrics(post_loss_independent),
            "post_win_addon": metrics(post_win_addon),
            "post_loss_addon": metrics(post_loss_addon),
        },
        "profit_structures": [
            {
                "id": "PS1",
                "type": "baseline_seeded_trend_campaign",
                "mechanism": "由已通过 baseline 入口播种方向 campaign，仅在新的 M5 结构突破与回踩形成新结构级别后独立再入，直到相反方向 CHoCH 结束 campaign；禁止全局 MicroBOS 扫描和同价即时加仓。",
                "expected_edge": "把现有高质量后续独立信号扩展为可持续频次来源，同时避免全局 HTFPB/MicroBOS 的高频噪音。",
                "invalid_if": "90d 交易频次未提升至少 30%，或 PF/回撤相对 baseline 退化超过 10%，或新增信号不能归因到新结构级别。",
                "evidence_refs": [
                    source + "#query=later_independent",
                    source + "#query=multi_entry_campaigns",
                    "research/notes/2026-06-28_v11-btc1_wfys_iteration.md#L3486-L3543",
                ],
            },
            {
                "id": "PS2",
                "type": "profit_confirmed_structural_reload",
                "mechanism": "盈利交易确认趋势后不立即加仓，等待新的结构突破、回踩和新订单块后独立重载一次，并使用独立止损和 HTF Target。",
                "expected_edge": "利用前一笔盈利后独立再入的高胜率样本，提高趋势 campaign 的复用率而不复制低质量即时 addon。",
                "invalid_if": "90d 新增信号不足，或独立重载胜率低于 baseline，或大赢单比例明显下降。",
                "evidence_refs": [
                    source + "#query=post_win_independent",
                    source + "#query=post_win_addon",
                ],
            },
            {
                "id": "PS3",
                "type": "failure_reclaim_structure_entry",
                "mechanism": "baseline 入口主动失败后，只有价格重新夺回原方向的微结构并形成新订单块时才允许独立恢复入场；同一订单块重入和失败后的即时 addon 均禁止。",
                "expected_edge": "保留失败后最终转为大趋势的恢复机会，并过滤无新结构的连续失败。",
                "invalid_if": "90d 恢复入场不能产生正期望，或新增交易主要来自同一订单块重复触发。",
                "evidence_refs": [
                    source + "#query=post_loss_independent",
                    source + "#query=post_loss_addon",
                ],
            },
        ],
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="wf-yhcl 盈利结构发现")
    parser.add_argument("--trades-csv", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args(argv)
    result = discover(args.trades_csv)
    target = Path(args.json_out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    analysis = result["analysis"]
    print("campaigns=" + str(analysis["campaign_count"]) + ", later_independent=" + str(analysis["later_independent"]["trades"]) + ", later_addon=" + str(analysis["later_addon"]["trades"]))
    print("候选: " + ", ".join(item["id"] + "=" + item["type"] for item in result["profit_structures"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
