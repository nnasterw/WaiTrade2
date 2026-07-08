#!/usr/bin/env python3
"""_loop.py - Loop Engineering 总入口

用法:
  python scripts/_loop.py preflight              # 环境检查
  python scripts/_loop.py diagnose               # 诊断
  python scripts/_loop.py batch --variants X,Y   # 批量回测
  python scripts/_loop.py close --variants X,Y   # 写反思+gate+handoff
  python scripts/_loop.py run --variants X,Y     # 完整流程 (preflight+batch+close)
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path("D:/Code/codexProject/WaiTrade2")
SCRIPTS = ROOT / "scripts"


def run_script(name, args=None):
    """运行同名 script"""
    cmd = [sys.executable, str(SCRIPTS / name)]
    if args:
        cmd.extend(args)
    print("[RUN] " + name + " " + (str(args) if args else ""))
    return subprocess.run(cmd, check=False).returncode


def main():
    parser = argparse.ArgumentParser(description="Loop Engineering 总入口")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight", help="环境检查")
    sub.add_parser("diagnose", help="诊断")
    p_batch = sub.add_parser("batch", help="批量回测")
    p_batch.add_argument("--variants", required=True)
    p_batch.add_argument("--terminal", default="mt5_portable_btc_trend111")
    p_batch.add_argument("--time-limit", type=int, default=30)
    p_batch.add_argument("--no-smoke", action="store_true")
    p_close = sub.add_parser("close", help="写反思+gate+handoff")
    p_close.add_argument("--variants", required=True)
    p_close.add_argument("--loop-id", type=int, required=True)
    p_close.add_argument("--gate", default="继续深挖")
    p_close.add_argument("--reason", default="")
    p_run = sub.add_parser("run", help="完整流程")
    p_run.add_argument("--variants", required=True)
    p_run.add_argument("--loop-id", type=int, required=True)
    p_run.add_argument("--terminal", default="mt5_portable_btc_trend111")
    p_run.add_argument("--time-limit", type=int, default=30)
    p_run.add_argument("--gate", default="继续深挖")
    p_run.add_argument("--reason", default="")

    args = parser.parse_args()

    if args.cmd == "preflight":
        return run_script("_loop_preflight.py", ["--cleanup-cache"])
    elif args.cmd == "diagnose":
        return run_script("_loop_diagnose.py")
    elif args.cmd == "batch":
        batch_args = ["--variants", args.variants, "--terminal", args.terminal, "--time-limit", str(args.time_limit)]
        if args.no_smoke: batch_args.append("--no-smoke")
        return run_script("_loop_batch.py", batch_args)
    elif args.cmd == "close":
        close_args = ["--variants", args.variants, "--loop-id", str(args.loop_id), "--gate", args.gate, "--reason", args.reason]
        return run_script("_loop_close.py", close_args)
    elif args.cmd == "run":
        # 完整流程
        print("=" * 60)
        print("Loop 完整流程")
        print("=" * 60)
        # 1. preflight
        rc = run_script("_loop_preflight.py", ["--cleanup-cache"])
        if rc != 0:
            print("[STOP] preflight 失败")
            return rc
        # 2. batch
        batch_args = ["--variants", args.variants, "--terminal", args.terminal, "--time-limit", str(args.time_limit)]
        rc = run_script("_loop_batch.py", batch_args)
        # 3. close (无论 batch 成功失败都写)
        close_args = ["--variants", args.variants, "--loop-id", str(args.loop_id), "--gate", args.gate, "--reason", args.reason]
        run_script("_loop_close.py", close_args)
        return rc
    return 1


if __name__ == "__main__":
    sys.exit(main())
