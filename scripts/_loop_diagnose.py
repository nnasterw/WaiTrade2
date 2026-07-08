#!/usr/bin/env python3
"""_loop_diagnose.py - Loop 诊断阶段 (yhcl 3.1 升级: 真正读 notes)

输入: handoff 笔记, 76 篇 research/notes/*.md, WFYS JSON
输出: 诊断报告 + 3-5 ranked 假设候选 (含 notes 来源引用)

yhcl 3.1 改进:
  - keyword 扫描: "瓶颈" "上限" "锁死" "突破" "灾难"
  - top_drags 关联变量提取
  - 假设来源标注 notes 路径
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter

ROOT = Path("D:/Code/codexProject/WaiTrade2")
RESULTS = ROOT / "results" / "backtest"
RESEARCH = ROOT / "research" / "loops"
NOTES = ROOT / "research" / "notes"
BASELINE_SCORE = 87.34  # trend218
PRIOR_BEST = 88.84  # trend531


def load_handoff():
    if not RESEARCH.exists():
        return None
    handoffs = sorted(RESEARCH.glob("*_handoff.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not handoffs:
        return None
    return handoffs[0].read_text(encoding="utf-8"), handoffs[0]


def load_wfys_history(n=20):
    history = []
    if not RESULTS.exists():
        return history
    for path in sorted(RESULTS.glob("*_wfys_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            per = data.get("period", {})
            days = per.get("days", 0)
            if days < 700:
                continue
            name = path.stem.replace("_wfys_", "").replace("_2026", "")
            score = data.get("score", {}).get("total_score", 0)
            grade = data.get("grade", "?")
            metrics = data.get("metrics", {}).get("monthly", {})
            profitable_months = metrics.get("profitable_months", 0)
            month_count = metrics.get("month_count", 0)
            history.append({
                "name": name,
                "score": score,
                "grade": grade,
                "profitable_months": profitable_months,
                "month_count": month_count,
                "path": str(path.relative_to(ROOT)),
            })
        except Exception:
            pass
    return history


def read_research_notes(keywords=None):
    """yhcl 3.1 升级: 读 76 篇 notes 提取瓶颈"""
    if keywords is None:
        keywords = ["瓶颈", "上限", "锁死", "突破", "灾难", "踩坑", "失败",
                    "未达成", "结构限制", "根本原因", "稳态"]
    if not NOTES.exists():
        return []
    findings = []
    for note_path in sorted(NOTES.glob("*.md")):
        try:
            text = note_path.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(text.split("\n"), start=1):
            for kw in keywords:
                if kw in line:
                    findings.append({
                        "note": note_path.name,
                        "line": i,
                        "keyword": kw,
                        "content": line.strip()[:150],
                    })
                    break
    return findings


def extract_top_drags_from_wfys():
    """从最近 WFYS JSON 提取 top_drags (瓶颈信号)"""
    drags = []
    if not RESULTS.exists():
        return drags
    for path in sorted(RESULTS.glob("*_wfys_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            per = data.get("period", {})
            if per.get("days", 0) < 700:
                continue
            name = path.stem.replace("_wfys_", "").replace("_2026", "")
            top = data.get("score", {}).get("top_drags", [])
            for d in top:
                drags.append({"variant": name, "drag": d})
        except Exception:
            pass
    return drags


def analyze_trends(history):
    if not history:
        return "无历史数据"
    scores = [h["score"] for h in history if h["score"] > 0]
    if not scores:
        return "无有效分数"
    avg = sum(scores) / len(scores)
    max_score = max(scores)
    max_name = max(history, key=lambda h: h["score"])["name"]
    min_score = min(scores)
    return f"平均 {avg:.2f}, 最高 {max_score:.2f} ({max_name}), 最低 {min_score:.2f}"


def generate_hypotheses(history, note_findings, top_drags):
    """基于历史 + notes 提取生成 3-5 个 ranked 假设"""
    if not history:
        return []
    best = max(history, key=lambda h: h["score"])
    hypotheses = []

    if best["score"] >= 90:
        hypotheses.append({
            "rank": 1,
            "name": "anchor_lock_check",
            "change": "已超 90, 验证是否触及 anchor 上限, 建议 EA 源码改动",
            "prediction": "如果改 anchor 参数 score 仍不变, 说明 anchor 锁死",
            "falsify_if": "改 anchor 参数 score 提升 >= 2.0, 说明未锁死",
            "source": "auto: best_score>=90",
        })
    if top_drags:
        drag_counter = Counter(d["drag"] for d in top_drags)
        top_drag = drag_counter.most_common(1)[0][0] if drag_counter else None
        if top_drag:
            hypotheses.append({
                "rank": len(hypotheses) + 1,
                "name": "fix_top_drag",
                "change": "针对 top_drag '" + top_drag + "' 微调 (单变量)",
                "prediction": "如果 score 提升 >= 0.5, 修复该 drag 是有效的",
                "falsify_if": "score 不变, 该 drag 是结构性限制",
                "source": "auto: top_drags from WFYS JSON",
            })

    if note_findings:
        unique_notes = list({f["note"] for f in note_findings})[:3]
        for i, note_name in enumerate(unique_notes):
            note_lines = [f for f in note_findings if f["note"] == note_name][:2]
            content_preview = " | ".join(f["content"][:60] for f in note_lines)
            hypotheses.append({
                "rank": len(hypotheses) + 1,
                "name": "note_based_" + str(i + 1),
                "change": "基于 " + note_name + " 提到的方向调整参数",
                "prediction": "如果 score 提升 >= 0.3, 该 notes 中的方向有效",
                "falsify_if": "score 不变, notes 中的诊断需要重新审视",
                "source": "notes/" + note_name,
                "evidence": content_preview,
            })

    while len(hypotheses) < 3:
        hypotheses.append({
            "rank": len(hypotheses) + 1,
            "name": "manual_design_needed",
            "change": "请手动设计新假设 (Diagnose 自动化覆盖不足)",
            "prediction": "N/A",
            "falsify_if": "N/A",
            "source": "manual",
        })

    return hypotheses[:5]


def main():
    parser = argparse.ArgumentParser(description="Loop 诊断阶段 (yhcl 3.1 升级)")
    parser.add_argument("--read-notes", action="store_true", help="读 76 篇 notes 提取瓶颈")
    parser.add_argument("--keywords", default="瓶颈,上限,锁死,突破,灾难,踩坑,失败,根本原因,结构限制,稳态")
    args = parser.parse_args()

    print("=" * 60)
    print("Loop Diagnose @ " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    print("\n[1/4] Handoff 笔记 ...")
    handoff_result = load_handoff()
    if handoff_result:
        handoff_text, handoff_path = handoff_result
        print("  [OK] 找到 handoff: " + handoff_path.name + ", 长度: " + str(len(handoff_text)) + " chars")
        print("\n--- 最近 handoff 摘要 ---")
        for line in handoff_text.split("\n")[:15]:
            print("  " + line)
    else:
        print("  [INFO] 无 handoff 笔记 (首次 Loop)")

    print("\n[2/4] WFYS 历史趋势 ...")
    history = load_wfys_history(20)
    if history:
        trend = analyze_trends(history)
        print("  " + trend)
        print("\n  最近 5 个:")
        for h in history[:5]:
            print("    " + h["name"] + ": " + str(round(h["score"], 2)) + " (" + h["grade"] + ")")
    else:
        print("  [WARN] 无 WFYS JSON 历史")

    note_findings = []
    if args.read_notes:
        print("\n[3/4] yhcl 3.1 读 76 篇 notes (关键词: " + args.keywords + ") ...")
        keywords = args.keywords.split(",")
        note_findings = read_research_notes(keywords)
        if note_findings:
            note_counter = Counter(f["note"] for f in note_findings)
            keyword_counter = Counter(f["keyword"] for f in note_findings)
            print("  [OK] 找到 " + str(len(note_findings)) + " 个瓶颈信号")
            print("  Top 笔记:")
            for note, count in note_counter.most_common(5):
                print("    " + note + ": " + str(count) + " 次")
            print("  Top 关键词:")
            for kw, count in keyword_counter.most_common(5):
                print("    '" + kw + "': " + str(count) + " 次")
            print("\n  最新 3 条证据:")
            for f in note_findings[-3:]:
                print("    " + f["note"] + ":" + str(f["line"]) + " [" + f["keyword"] + "] " + f["content"][:80])
        else:
            print("  [WARN] 无 notes 瓶颈信号")
    else:
        print("\n[3/4] (跳过 notes 读取, 用 --read-notes 启用 yhcl 3.1 升级)")

    print("\n[4/4] 假设候选 (ranked) ...")
    top_drags = extract_top_drags_from_wfys()
    hypotheses = generate_hypotheses(history, note_findings, top_drags)
    if hypotheses:
        for h in hypotheses:
            print("\n  H" + str(h["rank"]) + ": " + h.get("name", "?"))
            print("      改动: " + h["change"])
            print("      预测: " + h["prediction"])
            print("      证伪: " + h["falsify_if"])
            if h.get("source"):
                print("      来源: " + h["source"])
            if h.get("evidence"):
                print("      证据: " + h["evidence"][:80])
    else:
        print("  [INFO] 无自动假设, 请手动设计")

    print("\n" + "=" * 60)
    print("Next: python scripts/_yhcl31.py phase --phase-num N --loop-num M --variants X,Y")
    return 0


if __name__ == "__main__":
    sys.exit(main())
