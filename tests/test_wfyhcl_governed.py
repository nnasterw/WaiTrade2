"""governed runner 的盈利结构发现与自动 Gate 测试。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_manifest import load_json, unavailable_token_attribution, write_checkpoint
from wfyhcl_governed import complete_discovery, complete_validation


def _config(tmp_path):
    return {
        "pipeline_id": "test-pipeline",
        "baseline": {"strategy": "base", "wfys_standard": "BTC-v2.2", "score": 89.57, "hard_failures": ["频次"], "weekly_trades": 1.07},
        "objective": {"wfys_min": 93, "weekly_trades_min": 2, "model": 4, "deposit": 200, "live_auto_deploy": False},
        "promotion": {"same_hard_failures_min_score_delta": 0.3, "fewer_hard_failures_max_score_drop": 1.0},
        "paths": {
            "loops_dir": str(tmp_path / "loops"),
            "pipeline_pointer": str(tmp_path / "current.json"),
            "backtest_dir": str(tmp_path / "backtest"),
        },
    }


def _discovery_manifest(config):
    return {
        "schema_version": 1,
        "pipeline_id": config["pipeline_id"],
        "loop_id": 158,
        "loop_type": "profit_structure_discovery",
        "status": "running",
        "baseline_before": config["baseline"],
        "baseline_after": None,
        "objective": config["objective"],
        "plan": {},
        "variants": [],
        "gate": {"decision": "待决定"},
        "evidence_manifest": [],
        "token_attribution": unavailable_token_attribution(),
        "next_loop": {"loop_id": 158, "type": "profit_structure_discovery"},
    }


def test_complete_discovery_selects_structure_verification(tmp_path):
    config = _config(tmp_path)
    write_checkpoint(_discovery_manifest(config), config["paths"]["loops_dir"], config["paths"]["pipeline_pointer"])
    candidates = tmp_path / "candidates.json"
    candidates.write_text(json.dumps({"profit_structures": [{
        "id": "PS1",
        "type": "secondary_entry",
        "mechanism": "趋势突破后的第一次结构回踩二次入场",
        "expected_edge": "增加高质量趋势延续交易",
        "invalid_if": "新增交易 PF 低于 baseline",
        "evidence_refs": ["report.txt#trade-1"],
    }]}, ensure_ascii=False), encoding="utf-8")
    complete_discovery(config, candidates)
    pointer = load_json(config["paths"]["pipeline_pointer"])
    manifest = load_json(pointer["latest_manifest"])
    assert manifest["status"] == "completed"
    assert manifest["gate"]["decision"] == "重构架构"
    assert manifest["next_loop"]["type"] == "structure_verification"
    assert manifest["next_loop"]["candidate_id"] == "PS1"


def test_discovery_rejects_more_than_three_candidates(tmp_path):
    config = _config(tmp_path)
    write_checkpoint(_discovery_manifest(config), config["paths"]["loops_dir"], config["paths"]["pipeline_pointer"])
    item = {"type": "x", "mechanism": "m", "expected_edge": "e", "invalid_if": "i", "evidence_refs": ["r"]}
    values = []
    for index in range(4):
        value = dict(item)
        value["id"] = "PS" + str(index)
        values.append(value)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"profit_structures": values}), encoding="utf-8")
    try:
        complete_discovery(config, path)
    except ValueError as exc:
        assert "1-3" in str(exc)
    else:
        raise AssertionError("四个结构候选必须失败")


def test_complete_validation_promotes_fewer_hard_failures(tmp_path):
    config = _config(tmp_path)
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    files = {}
    for key, name in {
        "original_report": "report.txt",
        "trades_csv": "trades.csv",
        "monthly_csv": "24m.csv",
        "wfys_json": "wfys.json",
    }.items():
        path = artifacts_dir / name
        files[key] = str(path)
    Path(files["original_report"]).write_text("report", encoding="utf-8")
    Path(files["trades_csv"]).write_text("id,pnl\n1,1\n", encoding="utf-8")
    Path(files["monthly_csv"]).write_text("month,net\n2024-06,1\n", encoding="utf-8")
    Path(files["wfys_json"]).write_text(json.dumps({
        "score": {"total_score": 89.2},
        "grade": "通过",
        "hard_failures": [],
        "metrics": {"continuous": {"trade_count": 217}},
    }, ensure_ascii=False), encoding="utf-8")
    manifest = _discovery_manifest(config)
    manifest.update({"loop_id": 159, "loop_type": "structure_verification", "status": "running"})
    batch = {
        "workload_budget": 12,
        "workload_used": 7.5,
        "elapsed_min": 5,
        "promoted": "candidate",
        "variants": [{"strategy": "candidate", "artifacts": dict({"success": True}, **files)}],
    }
    complete_validation(config, manifest, batch)
    pointer = load_json(config["paths"]["pipeline_pointer"])
    completed = load_json(pointer["latest_manifest"])
    assert completed["baseline_after"]["strategy"] == "candidate"
    assert completed["gate"]["decision"] == "继续当前方向"
    assert completed["gate"]["graduated"] is False
    assert completed["evidence_manifest"][0]["artifacts"][0]["path"].startswith(tmp_path.as_posix())
