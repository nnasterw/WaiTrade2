#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wf-yhcl 受控迭代权威状态机。分析由当前 Codex 会话完成，脚本负责可验证状态与执行。"""
import argparse
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

from pipeline_manifest import (
    ROOT,
    baseline_promotion_decision,
    build_evidence_bundle,
    is_graduated,
    load_json,
    now_iso,
    unavailable_token_attribution,
    write_checkpoint,
)
from codex_token_audit import diff_snapshots, discover_current_rollout, snapshot_rollout

DEFAULT_CONFIG = ROOT / "config" / "iteration_pipeline.json"


def resolve_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_config(path=DEFAULT_CONFIG):
    return load_json(path)


def find_latest(pattern, directory):
    candidates = sorted(Path(directory).glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def baseline_evidence(config):
    strategy = config["baseline"]["strategy"]
    backtests = resolve_path(config["paths"]["backtest_dir"])
    wfys = find_latest(strategy + "*_wfys_*.json", backtests)
    reports = sorted(backtests.glob(strategy + "_20240601_20260531_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    report = reports[0] if reports else None
    trades = report.with_suffix(".trades.csv") if report and report.with_suffix(".trades.csv").exists() else None
    monthly = None
    if trades:
        matches = sorted(trades.parent.glob(trades.stem + "*_24m.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        monthly = matches[0] if matches else None
    artifacts = {
        "original_report": report,
        "trades_csv": trades,
        "monthly_csv": monthly,
        "wfys_json": wfys,
    }
    missing = [name for name, value in artifacts.items() if value is None]
    if missing:
        raise FileNotFoundError("baseline 证据包缺失: " + ", ".join(missing))
    provenance = {
        "model": config["objective"]["model"],
        "deposit": config["objective"]["deposit"],
        "date_from": "2024.06.01",
        "date_to": "2026.05.31",
        "wfys_standard": config["baseline"]["wfys_standard"],
    }
    return build_evidence_bundle(strategy, "full_720d", artifacts, provenance)


def capture_token_snapshot():
    try:
        rollout = discover_current_rollout(ROOT)
        return snapshot_rollout(rollout) if rollout else None
    except Exception:
        return None


def finalize_token_attribution(manifest):
    start = manifest.pop("token_snapshot_start", None)
    end = capture_token_snapshot()
    if start and end and start.get("rollout") == end.get("rollout"):
        manifest["token_attribution"] = diff_snapshots(start, end)
    elif not manifest.get("token_attribution"):
        manifest["token_attribution"] = unavailable_token_attribution()
    return manifest


def initial_manifest(config):
    next_loop = deepcopy(config["initial_next_loop"])
    return {
        "schema_version": 1,
        "pipeline_id": config["pipeline_id"],
        "loop_id": int(next_loop["loop_id"]),
        "loop_type": next_loop["type"],
        "status": "running",
        "started_at": now_iso(),
        "baseline_before": deepcopy(config["baseline"]),
        "baseline_after": None,
        "objective": deepcopy(config["objective"]),
        "plan": {
            "focus": next_loop["focus"],
            "limits": deepcopy(config["loop_limits"]),
            "discovery_requirements": [
                "分析大赢单与亏损单入场前趋势结构差异",
                "分析提高周均交易数且不破坏 WFYS 的趋势延续机会",
                "生成最多 3 个结构不同的盈利结构候选",
            ],
        },
        "variants": [],
        "gate": {"decision": "待决定", "reason": "盈利结构发现进行中", "evidence_refs": []},
        "evidence_manifest": [baseline_evidence(config)],
        "token_attribution": unavailable_token_attribution(),
        "token_snapshot_start": capture_token_snapshot(),
        "git": {},
        "next_loop": {"loop_id": int(next_loop["loop_id"]), "type": next_loop["type"]},
    }


def init_pipeline(config_path, force=False):
    config = load_config(config_path)
    pointer_path = resolve_path(config["paths"]["pipeline_pointer"])
    if pointer_path.exists() and not force:
        raise FileExistsError("流水线已初始化: " + str(pointer_path))
    manifest = initial_manifest(config)
    return write_checkpoint(manifest, resolve_path(config["paths"]["loops_dir"]), pointer_path)


def read_current(config):
    pointer_path = resolve_path(config["paths"]["pipeline_pointer"])
    pointer = load_json(pointer_path)
    manifest = load_json(pointer["latest_manifest"])
    return pointer, manifest


def enforce_plan(plan, config):
    hypotheses = list(plan.get("hypotheses") or [])
    limits = config["loop_limits"]
    if len(hypotheses) > int(limits["max_hypotheses"]):
        raise ValueError("假设数量超过单 Loop 上限")
    for item in hypotheses:
        changes = list(item.get("changes") or [])
        if len(changes) != 1:
            raise ValueError("每个普通变体必须且只能修改一个变量: " + str(item.get("id")))
        if not item.get("prediction") or not item.get("falsify_if"):
            raise ValueError("假设必须包含 prediction 和 falsify_if")
    return True


def run_iteration(config, plan_path, terminal, dry_run=False):
    plan = load_json(plan_path)
    enforce_plan(plan, config)
    variants = [item["strategy"] for item in plan.get("hypotheses") or []]
    if not variants:
        raise ValueError("验证 Loop 至少需要一个假设")
    pointer, current = read_current(config)
    loop_id = int((pointer.get("next_loop") or {}).get("loop_id", current["loop_id"] + 1))
    output = resolve_path(config["paths"]["loops_dir"]) / ("loop_" + str(loop_id) + "_batch_result.json")
    cmd = [
        sys.executable, str(ROOT / "scripts" / "_loop_batch.py"),
        "--variants", ",".join(variants),
        "--terminal", terminal,
        "--time-limit", str(config["loop_limits"]["time_limit_min"]),
        "--workload-budget", str(config["loop_limits"]["workload_budget"]),
        "--json-out", str(output),
    ]
    if dry_run:
        return {"loop_id": loop_id, "command": cmd, "variants": variants}
    manifest = start_validation_manifest(config, pointer, current, plan, loop_id)
    rc = subprocess.run(cmd, cwd=str(ROOT), check=False).returncode
    if rc != 0:
        manifest["status"] = "repair"
        manifest["gate"] = {"decision": "修复态", "reason": "晋级执行器退出码 " + str(rc), "evidence_refs": []}
        write_checkpoint(manifest, resolve_path(config["paths"]["loops_dir"]), resolve_path(config["paths"]["pipeline_pointer"]))
        raise RuntimeError("晋级验证失败，退出码 " + str(rc))
    batch = load_json(output)
    complete_validation(config, manifest, batch)
    return batch

def validate_profit_structures(data):
    candidates = list(data.get("profit_structures") or [])
    if not 1 <= len(candidates) <= 3:
        raise ValueError("盈利结构发现必须输出 1-3 个候选")
    ids = set()
    for item in candidates:
        for key in ("id", "type", "mechanism", "expected_edge", "invalid_if", "evidence_refs"):
            if key not in item or item[key] in (None, "", []):
                raise ValueError("盈利结构候选缺少字段 " + key)
        if item["id"] in ids:
            raise ValueError("盈利结构候选 ID 重复")
        ids.add(item["id"])
    return candidates


def complete_discovery(config, candidates_path):
    pointer, manifest = read_current(config)
    if manifest["loop_type"] != "profit_structure_discovery":
        raise ValueError("当前 Loop 不是盈利结构发现")
    candidates = validate_profit_structures(load_json(candidates_path))
    manifest["status"] = "completed"
    manifest["completed_at"] = now_iso()
    manifest["plan"]["profit_structures"] = candidates
    manifest["gate"] = {
        "decision": "重构架构",
        "reason": "结构上限证据成立，盈利结构发现已产生候选",
        "evidence_refs": [ref for item in candidates for ref in item.get("evidence_refs", [])],
        "automatic": True,
    }
    manifest["baseline_after"] = deepcopy(manifest["baseline_before"])
    manifest["next_loop"] = {
        "loop_id": manifest["loop_id"] + 1,
        "type": "structure_verification",
        "candidate_id": candidates[0]["id"],
        "focus": candidates[0]["mechanism"],
    }
    finalize_token_attribution(manifest)
    return write_checkpoint(
        manifest,
        resolve_path(config["paths"]["loops_dir"]),
        resolve_path(config["paths"]["pipeline_pointer"]),
    )


def candidate_from_wfys(strategy, path):
    data = load_json(path)
    metrics = data.get("metrics") or {}
    continuous = metrics.get("continuous") or {}
    trade_count = float(continuous.get("trade_count", 0) or 0)
    return {
        "strategy": strategy,
        "score": float((data.get("score") or {}).get("total_score", 0) or 0),
        "hard_failures": list(data.get("hard_failures") or []),
        "weekly_trades": trade_count / 103.0,
        "grade": data.get("grade"),
    }


def evidence_from_batch(config, promoted):
    artifacts = promoted.get("artifacts") or {}
    if not artifacts.get("success"):
        return None
    evidence_paths = {
        "original_report": artifacts.get("original_report"),
        "trades_csv": artifacts.get("trades_csv"),
        "monthly_csv": artifacts.get("monthly_csv"),
        "wfys_json": artifacts.get("wfys_json"),
    }
    provenance = {
        "model": config["objective"]["model"],
        "deposit": config["objective"]["deposit"],
        "date_from": "2024.06.01",
        "date_to": "2026.05.31",
        "wfys_standard": config["baseline"]["wfys_standard"],
    }
    return build_evidence_bundle(promoted["strategy"], "full_720d", evidence_paths, provenance)


def start_validation_manifest(config, pointer, current, plan, loop_id):
    baseline = deepcopy(current.get("baseline_after") or current["baseline_before"])
    manifest = {
        "schema_version": 1,
        "pipeline_id": config["pipeline_id"],
        "loop_id": loop_id,
        "loop_type": (pointer.get("next_loop") or {}).get("type", "governed_iteration"),
        "status": "running",
        "started_at": now_iso(),
        "baseline_before": baseline,
        "baseline_after": None,
        "objective": deepcopy(config["objective"]),
        "plan": deepcopy(plan),
        "variants": [],
        "gate": {"decision": "待决定", "reason": "晋级验证进行中", "evidence_refs": []},
        "evidence_manifest": list(current.get("evidence_manifest") or []),
        "token_attribution": unavailable_token_attribution(),
        "token_snapshot_start": capture_token_snapshot(),
        "git": {},
        "next_loop": {"loop_id": loop_id, "type": "running"},
    }
    write_checkpoint(manifest, resolve_path(config["paths"]["loops_dir"]), resolve_path(config["paths"]["pipeline_pointer"]))
    return manifest


def complete_validation(config, manifest, batch):
    manifest["variants"] = list(batch.get("variants") or [])
    manifest["status"] = "completed"
    manifest["completed_at"] = now_iso()
    manifest["workload"] = {
        "budget": batch.get("workload_budget"),
        "used": batch.get("workload_used"),
        "elapsed_min": batch.get("elapsed_min"),
    }
    promoted_name = batch.get("promoted")
    promoted = next((item for item in manifest["variants"] if item.get("strategy") == promoted_name), None)
    baseline_after = deepcopy(manifest["baseline_before"])
    next_type = "governed_iteration"
    if promoted and (promoted.get("artifacts") or {}).get("success"):
        bundle = evidence_from_batch(config, promoted)
        if bundle:
            manifest["evidence_manifest"].append(bundle)
        candidate = candidate_from_wfys(promoted_name, promoted["artifacts"]["wfys_json"])
        manifest["candidate"] = candidate
        promote, reason = baseline_promotion_decision(
            manifest["baseline_before"], candidate, config["promotion"], config["objective"]
        )
        graduated = is_graduated(candidate, config["objective"])
        if promote:
            baseline_after = candidate
            manifest["gate"] = {
                "decision": "继续当前方向",
                "reason": reason,
                "evidence_refs": [promoted["artifacts"]["wfys_json"]],
                "automatic": True,
                "graduated": graduated,
            }
        else:
            manifest["gate"] = {
                "decision": "切换假设",
                "reason": reason,
                "evidence_refs": [promoted["artifacts"]["wfys_json"]],
                "automatic": True,
                "graduated": False,
            }
    else:
        manifest["gate"] = {
            "decision": "切换假设",
            "reason": "没有变体通过 90d→720d→WFYS 晋级验证",
            "evidence_refs": [],
            "automatic": True,
            "graduated": False,
        }
    manifest["baseline_after"] = baseline_after
    manifest["next_loop"] = {
        "loop_id": manifest["loop_id"] + 1,
        "type": next_type,
        "focus": manifest["gate"]["decision"],
    }
    finalize_token_attribution(manifest)
    return write_checkpoint(
        manifest,
        resolve_path(config["paths"]["loops_dir"]),
        resolve_path(config["paths"]["pipeline_pointer"]),
    )


def print_status(config):
    pointer, manifest = read_current(config)
    print("Pipeline: " + pointer["pipeline_id"])
    print("Loop: " + str(manifest["loop_id"]) + " / " + manifest["loop_type"] + " / " + manifest["status"])
    print("Baseline: " + str(manifest["baseline_before"].get("strategy")) + " / WFYS " + str(manifest["baseline_before"].get("score")))
    print("Manifest: " + pointer["latest_manifest"])
    print("Handoff: " + pointer["latest_handoff"])
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="wf-yhcl 同会话持续受控迭代")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init", help="初始化持续流水线")
    p_init.add_argument("--force", action="store_true")
    sub.add_parser("status", help="显示当前流水线状态")
    p_discovery = sub.add_parser("complete-discovery", help="完成盈利结构发现 Loop")
    p_discovery.add_argument("--candidates", required=True)
    p_iter = sub.add_parser("governed-iterate", help="按机器可读计划执行晋级验证")
    p_iter.add_argument("--plan", required=True)
    p_iter.add_argument("--terminal", default="mt5_portable_btc_bv1")
    p_iter.add_argument("--dry-run", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    if args.cmd == "init":
        paths = init_pipeline(args.config, force=args.force)
        print("Manifest: " + str(paths[0]))
        print("Handoff: " + str(paths[1]))
        print("Pointer: " + str(paths[2]))
        return 0
    if args.cmd == "status":
        return print_status(config)
    if args.cmd == "complete-discovery":
        paths = complete_discovery(config, args.candidates)
        print("Manifest: " + str(paths[0]))
        print("Handoff: " + str(paths[1]))
        return 0
    if args.cmd == "governed-iterate":
        result = run_iteration(config, args.plan, args.terminal, dry_run=args.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
