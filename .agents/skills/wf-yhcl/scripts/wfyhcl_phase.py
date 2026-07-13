#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wf-yhcl 兼容适配器；完整迭代转发到项目 governed runner。"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from _project import ROOT

HERE = Path(__file__).resolve().parent
RUNNER = ROOT / "scripts" / "wfyhcl_governed.py"


def run(cmd):
    return subprocess.run(cmd, cwd=str(ROOT), check=False).returncode


def manifest_trades_path(strategy):
    pointer_path = ROOT / "research" / "loops" / "current_pipeline.json"
    if not pointer_path.exists():
        return None
    pointer = json.loads(pointer_path.read_text(encoding="utf-8-sig"))
    manifest = json.loads(Path(pointer["latest_manifest"]).read_text(encoding="utf-8-sig"))
    for bundle in reversed(manifest.get("evidence_manifest") or []):
        if bundle.get("strategy") != strategy or bundle.get("stage") != "full_720d":
            continue
        for item in bundle.get("artifacts") or []:
            if item.get("type") == "trades_csv":
                return item.get("path")
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="wf-yhcl 项目技能入口")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--force", action="store_true")
    sub.add_parser("status")
    p_discovery = sub.add_parser("complete-discovery")
    p_discovery.add_argument("--candidates", required=True)
    p_iter = sub.add_parser("governed-iterate")
    p_iter.add_argument("--plan", required=True)
    p_iter.add_argument("--terminal", default="mt5_portable_btc_bv1")
    p_iter.add_argument("--dry-run", action="store_true")
    p_diag = sub.add_parser("diagnose")
    p_diag.add_argument("--strategy", required=True)
    p_diag.add_argument("--symbol", default="BTCUSDm")
    p_diag.add_argument("--from", dest="date_from", default="2024.06.01")
    p_diag.add_argument("--to", dest="date_to", default="2026.05.31")
    p_diag.add_argument("--deposit", type=float, default=200)
    p_diag.add_argument("--level", type=int, default=2, choices=[1, 2, 3])
    p_iron = sub.add_parser("iron-rule")
    p_iron.add_argument("set_files", nargs="+")
    args = parser.parse_args(argv)

    if args.cmd in ("init", "status", "complete-discovery", "governed-iterate"):
        cmd = [sys.executable, str(RUNNER), args.cmd]
        if args.cmd == "init" and args.force:
            cmd.append("--force")
        if args.cmd == "complete-discovery":
            cmd.extend(["--candidates", args.candidates])
        if args.cmd == "governed-iterate":
            cmd.extend(["--plan", args.plan, "--terminal", args.terminal])
            if args.dry_run:
                cmd.append("--dry-run")
        return run(cmd)
    if args.cmd == "diagnose":
        cmd = [
            sys.executable, str(HERE / "batch_diagnose.py"), args.strategy,
            args.symbol, args.date_from, args.date_to, str(args.deposit),
            "--level", str(args.level), "--skip-backtest",
        ]
        trades_path = manifest_trades_path(args.strategy)
        if trades_path:
            cmd.extend(["--trades-csv", trades_path])
        return run(cmd)
    if args.cmd == "iron-rule":
        return run([sys.executable, str(HERE / "iron_rule_check.py")] + args.set_files + ["--strict"])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
