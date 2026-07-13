"""_loop_batch 的预算只能表示回测工作量，不能冒充 Codex token。"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import _loop_batch
from _loop_batch import (
    WORKLOAD_POINTS,
    build_parser,
    check_workload_budget,
    estimate_batch_workload,
    estimate_stage_workload,
)


def test_workload_points_cover_three_validation_stages():
    assert WORKLOAD_POINTS["smoke_30d"] == 1.0
    assert WORKLOAD_POINTS["validate_90d"] == 1.0
    assert WORKLOAD_POINTS["full_720d"] == 5.0


def test_stage_workload_is_not_named_token():
    assert estimate_stage_workload("smoke_30d") == 1.0
    assert estimate_stage_workload("validate_90d") == 1.0
    assert estimate_stage_workload("full_720d") == 5.5
    assert not hasattr(_loop_batch, "TOKEN_ESTIMATES")
    assert not hasattr(_loop_batch, "measure_actual_tokens")


def test_unknown_stage_fails_closed():
    try:
        estimate_stage_workload("unknown")
    except ValueError as exc:
        assert "未知回测阶段" in str(exc)
    else:
        raise AssertionError("未知阶段必须抛出 ValueError")


def test_batch_workload_options():
    assert estimate_batch_workload(with_smoke=True, with_wfys=True, variants=3) == 11.5
    assert estimate_batch_workload(with_smoke=False, with_wfys=True, variants=3) == 8.5
    assert estimate_batch_workload(with_smoke=False, with_wfys=False, variants=3) == 8.0


def test_workload_budget_thresholds():
    assert check_workload_budget(20.7, 26.0)[0] == "ok"
    assert check_workload_budget(20.8, 26.0)[0] == "warn"
    assert check_workload_budget(26.0, 26.0)[0] == "stop"


def test_cli_exposes_workload_not_token_budget():
    parser = build_parser()
    help_text = parser.format_help()
    assert "--workload-budget" in help_text
    assert "--token-budget" not in help_text
    args = parser.parse_args(["--variants", "x", "--workload-budget", "12"])
    assert args.workload_budget == 12.0


def test_legacy_token_budget_is_hidden_compatibility_alias():
    parser = build_parser()
    args = parser.parse_args(["--variants", "x", "--token-budget", "12"])
    assert args.legacy_token_budget == 12.0
