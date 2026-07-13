"""持续迭代 Manifest、证据包和 baseline Gate 回归测试。"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_manifest import (
    artifact_record,
    baseline_promotion_decision,
    build_evidence_bundle,
    is_graduated,
    load_json,
    validate_manifest,
    write_checkpoint,
)
from wfyhcl_governed import enforce_plan


def _manifest():
    return {
        "schema_version": 1,
        "pipeline_id": "test",
        "loop_id": 1,
        "loop_type": "profit_structure_discovery",
        "status": "completed",
        "baseline_before": {"strategy": "base", "score": 89.57, "hard_failures": ["频次"]},
        "baseline_after": None,
        "objective": {"wfys_min": 93, "weekly_trades_min": 2},
        "plan": {},
        "variants": [],
        "gate": {"decision": "重构架构", "reason": "结构上限证据成立"},
        "evidence_manifest": [],
        "token_attribution": {"source": "unavailable"},
        "next_loop": {"loop_id": 2, "type": "structure_verification"},
    }


def test_artifact_record_uses_absolute_path_and_sha256(tmp_path):
    path = tmp_path / "report.txt"
    path.write_bytes(b"real-ticks")
    record = artifact_record(path, "original_report")
    assert Path(record["path"]).is_absolute()
    assert record["sha256"] == hashlib.sha256(b"real-ticks").hexdigest()
    assert record["size"] == len(b"real-ticks")


def test_evidence_bundle_keeps_original_artifacts(tmp_path):
    report = tmp_path / "report.txt"
    trades = tmp_path / "trades.csv"
    report.write_text("report", encoding="utf-8")
    trades.write_text("id,pnl\n1,10\n", encoding="utf-8")
    bundle = build_evidence_bundle(
        "variant", "full_720d",
        {"original_report": report, "trades_csv": trades},
        {"model": 4, "deposit": 200},
    )
    assert bundle["strategy"] == "variant"
    assert {item["type"] for item in bundle["artifacts"]} == {"original_report", "trades_csv"}
    assert bundle["provenance"]["model"] == 4


def test_checkpoint_writes_manifest_handoff_and_pointer(tmp_path):
    manifest = _manifest()
    paths = write_checkpoint(manifest, tmp_path / "loops", tmp_path / "current_pipeline.json")
    assert all(path.exists() for path in paths)
    pointer = load_json(paths[2])
    assert pointer["same_codex_session"] is True
    assert Path(pointer["latest_manifest"]).resolve() == paths[0].resolve()
    assert "证据清单" in paths[1].read_text(encoding="utf-8")


def test_manifest_validation_requires_authoritative_fields():
    assert validate_manifest(_manifest()) is True
    broken = _manifest()
    broken.pop("gate")
    try:
        validate_manifest(broken)
    except ValueError as exc:
        assert "gate" in str(exc)
    else:
        raise AssertionError("缺少 gate 必须失败")


def test_baseline_prefers_fewer_hard_failures_with_small_score_drop():
    baseline = {"score": 89.57, "hard_failures": ["频次"]}
    candidate = {"score": 89.2, "hard_failures": [], "weekly_trades": 2.1}
    ok, reason = baseline_promotion_decision(
        baseline, candidate,
        {"fewer_hard_failures_max_score_drop": 1.0, "same_hard_failures_min_score_delta": 0.3},
        {"weekly_trades_min": 2.0},
    )
    assert ok is True
    assert "减少硬失败" in reason


def test_baseline_same_failures_needs_point_three_gain():
    baseline = {"score": 89.57, "hard_failures": ["频次"]}
    promotion = {"fewer_hard_failures_max_score_drop": 1.0, "same_hard_failures_min_score_delta": 0.3}
    objective = {"weekly_trades_min": 2.0}
    assert baseline_promotion_decision(baseline, {"score": 89.86, "hard_failures": ["频次"]}, promotion, objective)[0] is False
    assert baseline_promotion_decision(baseline, {"score": 89.87, "hard_failures": ["频次"]}, promotion, objective)[0] is True


def test_graduation_never_implies_live_deploy():
    objective = {"wfys_min": 93, "weekly_trades_min": 2, "live_auto_deploy": False}
    candidate = {"score": 93.2, "weekly_trades": 2.4, "hard_failures": []}
    assert is_graduated(candidate, objective) is True
    assert objective["live_auto_deploy"] is False


def test_plan_enforces_three_single_variable_hypotheses():
    config = {"loop_limits": {"max_hypotheses": 3}}
    valid = {"hypotheses": [
        {"id": "H1", "strategy": "a", "changes": [{"key": "x", "value": 1}], "prediction": "p", "falsify_if": "f"},
        {"id": "H2", "strategy": "b", "changes": [{"key": "y", "value": 1}], "prediction": "p", "falsify_if": "f"},
    ]}
    assert enforce_plan(valid, config) is True
    invalid = {"hypotheses": [{"id": "H1", "strategy": "a", "changes": [{"key": "x"}, {"key": "y"}], "prediction": "p", "falsify_if": "f"}]}
    try:
        enforce_plan(invalid, config)
    except ValueError as exc:
        assert "一个变量" in str(exc)
    else:
        raise AssertionError("多变量假设必须失败")
