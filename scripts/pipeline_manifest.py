#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""持续迭代流水线的 Manifest、证据包和 baseline Gate。Python 3.8 兼容。"""
import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_MANIFEST_KEYS = (
    "schema_version", "pipeline_id", "loop_id", "loop_type", "status",
    "baseline_before", "objective", "plan", "gate", "evidence_manifest",
    "token_attribution", "next_loop",
)


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def artifact_record(path, artifact_type, required=True):
    item = Path(path).resolve()
    if not item.exists():
        if required:
            raise FileNotFoundError(str(item))
        return None
    stat = item.stat()
    return {
        "type": artifact_type,
        "path": item.as_posix(),
        "sha256": sha256_file(item),
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
    }


def atomic_write_json(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, str(target))
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return target


def validate_manifest(manifest):
    missing = [key for key in REQUIRED_MANIFEST_KEYS if key not in manifest]
    if missing:
        raise ValueError("Manifest 缺少字段: " + ", ".join(missing))
    if manifest.get("schema_version") != 1:
        raise ValueError("不支持的 Manifest schema_version")
    if not isinstance(manifest.get("loop_id"), int) or manifest["loop_id"] < 1:
        raise ValueError("loop_id 必须是正整数")
    if not isinstance(manifest.get("evidence_manifest"), list):
        raise ValueError("evidence_manifest 必须是数组")
    return True


def unavailable_token_attribution(reason="rollout 未提供"):
    return {
        "source": "unavailable",
        "reason": reason,
        "delta": {},
        "context": {},
        "tools": {},
        "by_stage": {},
        "causes": [],
    }


def baseline_promotion_decision(baseline, candidate, promotion, objective):
    """先比较硬失败，再比较目标约束，最后比较 WFYS。"""
    base_failures = list(baseline.get("hard_failures") or [])
    cand_failures = list(candidate.get("hard_failures") or [])
    base_score = float(baseline.get("score", 0) or 0)
    cand_score = float(candidate.get("score", 0) or 0)
    weekly = float(candidate.get("weekly_trades", 0) or 0)
    weekly_min = float(objective.get("weekly_trades_min", 0) or 0)
    fewer_drop = float(promotion.get("fewer_hard_failures_max_score_drop", 1.0))
    same_delta = float(promotion.get("same_hard_failures_min_score_delta", 0.3))

    if len(cand_failures) > len(base_failures):
        return False, "候选增加硬失败"
    if len(cand_failures) < len(base_failures):
        if weekly < weekly_min:
            return False, "候选未达到周均交易目标"
        if cand_score < base_score - fewer_drop:
            return False, "候选消除硬失败但评分下降超过容忍值"
        return True, "候选减少硬失败且评分下降在容忍范围内"
    if cand_score >= base_score + same_delta:
        return True, "硬失败相同且 WFYS 达到可信提升阈值"
    return False, "候选未形成可信 baseline 改善"


def is_graduated(candidate, objective):
    return (
        not list(candidate.get("hard_failures") or [])
        and float(candidate.get("score", 0) or 0) >= float(objective.get("wfys_min", 0) or 0)
        and float(candidate.get("weekly_trades", 0) or 0) >= float(objective.get("weekly_trades_min", 0) or 0)
    )


def build_evidence_bundle(strategy, stage, artifacts, provenance):
    records = []
    for artifact_type, path in artifacts.items():
        if path:
            record = artifact_record(path, artifact_type, required=True)
            records.append(record)
    return {
        "strategy": strategy,
        "stage": stage,
        "artifacts": records,
        "provenance": dict(provenance),
    }


def render_handoff(manifest):
    gate = manifest.get("gate") or {}
    baseline_after = manifest.get("baseline_after") or manifest.get("baseline_before") or {}
    lines = [
        "# Loop " + str(manifest["loop_id"]) + " 检查点",
        "",
        "**流水线**: " + manifest["pipeline_id"],
        "**Loop 类型**: " + manifest["loop_type"],
        "**状态**: " + manifest["status"],
        "**Gate**: " + str(gate.get("decision", "待决定")),
        "**理由**: " + str(gate.get("reason", "")),
        "",
        "## 当前 baseline",
        "",
        "- 策略: " + str(baseline_after.get("strategy", "N/A")),
        "- WFYS: " + str(baseline_after.get("score", "N/A")),
        "- 硬失败: " + str(baseline_after.get("hard_failures", [])),
        "",
        "## 证据清单",
        "",
    ]
    bundles = manifest.get("evidence_manifest") or []
    if not bundles:
        lines.append("- 暂无证据包")
    for bundle in bundles:
        lines.append("### " + str(bundle.get("strategy")) + " / " + str(bundle.get("stage")))
        for item in bundle.get("artifacts") or []:
            lines.append("- " + str(item.get("type")) + ": `" + str(item.get("path")) + "` (sha256 `" + str(item.get("sha256")) + "`)")
        lines.append("")
    lines.extend(["", "## 下一 Loop", "", "- " + json.dumps(manifest.get("next_loop") or {}, ensure_ascii=False), ""])
    token = manifest.get("token_attribution") or {}
    lines.extend(["## Token 用量归因", "", "- 来源: " + str(token.get("source", "unavailable"))])
    delta = token.get("delta") or {}
    if delta:
        lines.append("- Raw total: " + str(delta.get("raw_total", delta.get("total_tokens", 0))))
        lines.append("- 非缓存等效: " + str(delta.get("non_cached_effective", 0)))
    lines.append("")
    return "\n".join(lines)


def write_checkpoint(manifest, loops_dir, pointer_path):
    validate_manifest(manifest)
    loops = Path(loops_dir)
    loops.mkdir(parents=True, exist_ok=True)
    date_text = datetime.now().strftime("%Y-%m-%d")
    stem = date_text + "_loop_" + str(manifest["loop_id"])
    manifest_path = loops / (stem + "_manifest.json")
    handoff_path = loops / (stem + "_handoff.md")
    atomic_write_json(manifest_path, manifest)
    with handoff_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_handoff(manifest))
    pointer = {
        "schema_version": 1,
        "pipeline_id": manifest["pipeline_id"],
        "same_codex_session": True,
        "latest_manifest": manifest_path.resolve().as_posix(),
        "latest_handoff": handoff_path.resolve().as_posix(),
        "latest_loop_id": manifest["loop_id"],
        "next_loop": manifest.get("next_loop") or {},
        "updated_at": now_iso(),
    }
    atomic_write_json(pointer_path, pointer)
    return manifest_path, handoff_path, Path(pointer_path)
