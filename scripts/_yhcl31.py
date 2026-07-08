#!/usr/bin/env python3
"""_yhcl31.py - yhcl 3.1 总入口 (yhcl3.0 调研深度 + Loop 执行纪律)

整合 7 项 P0+P1 改进:
  1. 30 min 时间盒 (防 yhcl2 类灾难)
  2. 30d smoke test (防 720d 跑空)
  3. MT5 cache 自动清理 (防命中)
  4. Baseline regression (trend218 = $7,615 +/- 0.5)
  5. 4 选 1 Gate (继续/切换/重构/停止)
  6. 结构化沉淀 (_reflect/_gate/_handoff)
  7. 跨 session 接力 (_handoff.md)

用法:
  # 完整 Phase+Loop 流程
  python scripts/_yhcl31.py phase --phase-num 24 --loop-num 1 \
      --variants v11-btc1-loop1,v11-btc1-loop2 \
      --terminal mt5_portable_btc_trend111 --time-limit 30

  # 仅 Diagnose (读 76 篇 notes 自动提取瓶颈)
  python scripts/_yhcl31.py diagnose

  # 仅 Preflight
  python scripts/_yhcl31.py preflight --cleanup-cache

  # 4 选 1 Gate 决策
  python scripts/_yhcl31.py gate --phase-num 24 --loop-num 1 \
      --decision "继续深挖" --reason "trend218 接近"
"""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("D:/Code/codexProject/WaiTrade2")
SCRIPTS = ROOT / "scripts"
RESEARCH_LOOPS = ROOT / "research" / "loops"


def run_script(name, args=None):
    """调用 _loop_* 子脚本"""
    cmd = [sys.executable, str(SCRIPTS / name)]
    if args:
        cmd.extend(args)
    print("[RUN] " + name + " " + (str(args) if args else ""))
    return subprocess.run(cmd, check=False).returncode


def write_phase_header(phase_num, loop_num, today):
    """写 phase header 笔记 (yhcl3.1 阶段记录)"""
    path = RESEARCH_LOOPS / (today + "_yhcl31_phase_" + str(phase_num) + "_loop_" + str(loop_num) + "_header.md")
    lines = [
        "# yhcl 3.1 Phase " + str(phase_num) + " Loop " + str(loop_num),
        "",
        "**日期**: " + today,
        "**阶段**: Phase " + str(phase_num) + " (续 yhcl3.0 Phase 1-23)",
        "**Loop**: " + str(loop_num),
        "",
        "## yhcl 3.1 5 阶段执行记录",
        "",
        "- [x] Stage 0 Diagnose",
        "- [ ] Stage 1 Preflight",
        "- [ ] Stage 2 Batch",
        "- [ ] Stage 3 Reflect",
        "- [ ] Stage 4 Close-out",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print("[WROTE] " + str(path))
    return path


def main():
    parser = argparse.ArgumentParser(description="yhcl 3.1 总入口")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # diagnose: 自动读 76 篇 notes 提取瓶颈
    sub.add_parser("diagnose", help="读 notes 自动提取瓶颈 + ranked 假设")

    # preflight: 6 项环境检查
    p_pre = sub.add_parser("preflight", help="环境检查")
    p_pre.add_argument("--cleanup-cache", action="store_true")

    # phase: 完整 Phase+Loop 流程
    p_phase = sub.add_parser("phase", help="yhcl 3.1 完整 Phase 流程")
    p_phase.add_argument("--phase-num", type=int, required=True, help="Phase 编号 (续 yhcl3.0)")
    p_phase.add_argument("--loop-num", type=int, required=True, help="Loop 编号")
    p_phase.add_argument("--variants", required=True, help="逗号分隔变体名")
    p_phase.add_argument("--terminal", default="mt5_portable_btc_trend111")
    p_phase.add_argument("--time-limit", type=int, default=30)
    p_phase.add_argument("--gate", default="继续深挖")
    p_phase.add_argument("--reason", default="")
    p_phase.add_argument("--no-smoke", action="store_true", help="跳过 smoke (默认强制)")

    # gate: 4 选 1 决策
    p_gate = sub.add_parser("gate", help="4 选 1 Gate 决策")
    p_gate.add_argument("--phase-num", type=int, required=True)
    p_gate.add_argument("--loop-num", type=int, required=True)
    p_gate.add_argument("--decision", required=True, choices=["继续深挖", "切换假设", "重构架构", "停止"])
    p_gate.add_argument("--reason", default="")

    args = parser.parse_args()
    today = datetime.now().strftime("%Y-%m-%d")
    print("=" * 60)
    print("yhcl 3.1 @ " + today)
    print("=" * 60)

    if args.cmd == "diagnose":
        # Stage 0: Diagnose (升级版 _loop_diagnose 读 notes)
        print("\n[Stage 0 Diagnose] 读 76 篇 notes + WFYS 历史\n")
        return run_script("_loop_diagnose.py", ["--read-notes"])
    elif args.cmd == "preflight":
        # Stage 1: Preflight
        print("\n[Stage 1 Preflight] 6 项环境检查\n")
        pre_args = []
        if args.cleanup_cache:
            pre_args.append("--cleanup-cache")
        return run_script("_loop_preflight.py", pre_args)
    elif args.cmd == "phase":
        # 完整 5 阶段流程
        print("\n[Stage 0] 写 phase header\n")
        write_phase_header(args.phase_num, args.loop_num, today)
        # Stage 1: Preflight
        print("\n[Stage 1 Preflight]\n")
        rc = run_script("_loop_preflight.py", ["--cleanup-cache"])
        if rc != 0:
            print("[STOP] preflight 失败, 不继续")
            return rc
        # Stage 2: Batch
        print("\n[Stage 2 Batch]\n")
        batch_args = ["--variants", args.variants, "--terminal", args.terminal, "--time-limit", str(args.time_limit)]
        if args.no_smoke:
            batch_args.append("--no-smoke")
        rc = run_script("_loop_batch.py", batch_args)
        # Stage 3: Close (写 3 件套)
        print("\n[Stage 3 Reflect]\n")
        close_args = [
            "--variants", args.variants,
            "--loop-id", str(args.loop_num),
            "--date", today,
            "--gate", args.gate,
            "--reason", args.reason,
        ]
        run_script("_loop_close.py", close_args)
        # Stage 4: Close-out
        print("\n[Stage 4 Close-out]\n")
        print("  [TODO] 更新 CONTEXT.md + 备份 + git commit")
        print("  [NOTE] 当前完成 Stage 0-3, Stage 4 由用户手动执行")
        return rc
    elif args.cmd == "gate":
        # 4 选 1 决策
        path = RESEARCH_LOOPS / (today + "_yhcl31_phase_" + str(args.phase_num) + "_loop_" + str(args.loop_num) + "_gate.md")
        lines = [
            "# yhcl 3.1 Phase " + str(args.phase_num) + " Loop " + str(args.loop_num) + " Gate 决策",
            "",
            "**日期**: " + today,
            "**决策**: **" + args.decision + "**",
            "**理由**: " + args.reason,
            "",
            "## 4 选 1",
            "- " + ("[x]" if args.decision == "继续深挖" else "[ ]") + " **继续深挖** (同方向下个 Loop)",
            "- " + ("[x]" if args.decision == "切换假设" else "[ ]") + " **切换假设** (Diagnose 重新生成)",
            "- " + ("[x]" if args.decision == "重构架构" else "[ ]") + " **重构架构** (改 EA 源码 / 换 anchor)",
            "- " + ("[x]" if args.decision == "停止" else "[ ]") + " **停止** (收尾, 写 Final Report)",
            "",
            "## 后续行动",
            "- (根据决策填写)",
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        print("[WROTE] " + str(path))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
