#!/usr/bin/env python3
"""_loop_close.py - Loop 结束阶段

输入: 本 Loop 的 results (WFYS JSON)
输出: 3 个 markdown 笔记
  - research/loops/<date>_loop_<N>_reflect.md
  - research/loops/<date>_loop_<N>_gate.md
  - research/loops/<date>_loop_<N>_handoff.md
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("D:/Code/codexProject/WaiTrade2")
RESULTS = ROOT / "results" / "backtest"
RESEARCH_LOOPS = ROOT / "research" / "loops"
RESEARCH_LOOPS.mkdir(parents=True, exist_ok=True)


def find_latest_wfys(variant):
    """找最新 WFYS JSON"""
    candidates = sorted(RESULTS.glob(variant + "_wfys_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def load_wfys(path):
    """读 WFYS JSON"""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except: return None


def write_reflect(variants, today, loop_id):
    """写 _reflect.md"""
    path = RESEARCH_LOOPS / (today + "_loop_" + str(loop_id) + "_reflect.md")
    lines = ["# Loop " + str(loop_id) + " 反思笔记", "", "**日期**: " + today, "**变体数**: " + str(len(variants)), ""]
    lines.append("## 假设验证表")
    lines.append("")
    lines.append("| ID | 变体 | 预期 | 实际 | 状态 |")
    lines.append("|----|------|------|------|------|")
    for v in variants:
        wfys_path = find_latest_wfys(v["name"])
        if not wfys_path:
            lines.append("| ? | " + v["name"] + " | - | 无结果 | N/A |")
            continue
        data = load_wfys(wfys_path)
        if not data:
            continue
        score = data.get("score", {}).get("total_score", 0)
        status = data.get("grade", "?")
        expected = v.get("expected", "?")
        lines.append("| " + v.get("id", "?") + " | " + v["name"] + " | " + str(expected) + " | " + str(round(score, 2)) + " (" + status + ") | " + status + " |")
    lines.append("")
    lines.append("## 实战坑记录")
    lines.append("")
    lines.append("- (自动从本 Loop 提取)")
    lines.append("")
    lines.append("## 新发现")
    lines.append("")
    lines.append("- (从变体结果推断)")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print("  [WROTE] " + str(path))
    return path


def write_gate(today, loop_id, decision, reason):
    """写 _gate.md"""
    path = RESEARCH_LOOPS / (today + "_loop_" + str(loop_id) + "_gate.md")
    lines = ["# Loop " + str(loop_id) + " Gate 决策", "", "**日期**: " + today, "**决策**: " + decision, "**理由**: " + reason, ""]
    lines.append("## 4 选 1")
    lines.append("- [x] **" + decision + "** (推荐)")
    lines.append("- [ ] 继续深挖")
    lines.append("- [ ] 切换假设")
    lines.append("- [ ] 重构架构")
    lines.append("- [ ] 停止")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print("  [WROTE] " + str(path))
    return path


def write_handoff(today, loop_id, best_variant, best_score, next_focus):
    """写 _handoff.md"""
    path = RESEARCH_LOOPS / (today + "_loop_" + str(loop_id) + "_handoff.md")
    lines = ["# Loop " + str(loop_id) + " 跨 Session 接力", "", "**日期**: " + today, ""]
    lines.append("## 当前最佳")
    lines.append("- " + best_variant + " (WFYS " + str(round(best_score, 2)) + ")")
    lines.append("")
    lines.append("## 未解决")
    lines.append("- (从本 Loop 推断)")
    lines.append("")
    lines.append("## 下 Loop 接力")
    for f in next_focus:
        lines.append("- [ ] " + f)
    lines.append("")
    lines.append("## 已排除方向")
    lines.append("- (从本 Loop 失败变体记录)")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print("  [WROTE] " + str(path))
    return path


def main():
    parser = argparse.ArgumentParser(description="Loop 结束阶段")
    parser.add_argument("--variants", required=True, help="逗号分隔策略名")
    parser.add_argument("--loop-id", type=int, required=True)
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--gate", default="继续深挖", help="Gate 决策")
    parser.add_argument("--reason", default="自动决策")
    args = parser.parse_args()

    variants = []
    for i, v in enumerate(args.variants.split(",")):
        v = v.strip()
        if not v: continue
        variants.append({"id": "H" + str(i+1), "name": v, "expected": "?"})

    print("=" * 60)
    print("Loop Close @ " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("Loop ID: " + str(args.loop_id))
    print("Variants: " + str(len(variants)))
    print("Gate: " + args.gate)
    print("=" * 60)

    # 找最佳变体
    best_name = "N/A"
    best_score = 0
    for v in variants:
        wfys = find_latest_wfys(v["name"])
        if not wfys: continue
        data = load_wfys(wfys)
        if not data: continue
        s = data.get("score", {}).get("total_score", 0)
        if s > best_score:
            best_score = s
            best_name = v["name"]

    # 写 3 个笔记
    print()
    print("--- 写笔记 ---")
    write_reflect(variants, args.date, args.loop_id)
    write_gate(args.date, args.loop_id, args.gate, args.reason)
    write_handoff(args.date, args.loop_id, best_name, best_score, [
        "复现 " + best_name + " 720d 验证稳定性",
        "基于 " + best_name + " 微调 1-2 个新方向",
    ])
    print()
    print("=" * 60)
    print("Done. 3 个笔记已写入: research/loops/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
