"""codex_token_audit 只抽取 usage 与工具元数据，不泄露 rollout 正文。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from codex_token_audit import audit_rollout, diff_snapshots, discover_current_rollout, format_audit


def _event(timestamp, top_type, payload):
    return json.dumps({"timestamp": timestamp, "type": top_type, "payload": payload}, ensure_ascii=False)


def _usage(timestamp, total, last):
    return _event(timestamp, "event_msg", {
        "type": "token_count",
        "info": {"total_token_usage": total, "last_token_usage": last},
    })


def _write_fixture(path):
    lines = [
        _usage("2026-07-12T15:59:59Z", {
            "input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 10,
            "reasoning_output_tokens": 0, "total_tokens": 110,
        }, {
            "input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 10,
            "reasoning_output_tokens": 0, "total_tokens": 110,
        }),
        _event("2026-07-13T04:00:00Z", "response_item", {
            "type": "function_call", "name": "exec_command", "call_id": "1",
            "arguments": json.dumps({"cmd": "Start-Sleep -Seconds 1500; Write-Output TOPSECRET"}),
        }),
        _event("2026-07-13T04:00:01Z", "response_item", {
            "type": "function_call_output", "call_id": "1", "output": "TOPSECRET-OUTPUT",
        }),
        _usage("2026-07-13T04:00:02Z", {
            "input_tokens": 200100, "cached_input_tokens": 100, "output_tokens": 30,
            "reasoning_output_tokens": 0, "total_tokens": 200130,
        }, {
            "input_tokens": 200000, "cached_input_tokens": 20, "output_tokens": 20,
            "reasoning_output_tokens": 0, "total_tokens": 200020,
        }),
        _event("2026-07-13T04:00:03Z", "response_item", {
            "type": "function_call", "name": "write_stdin", "call_id": "2",
            "arguments": json.dumps({"session_id": 123, "chars": ""}),
        }),
        _usage("2026-07-13T04:00:04Z", {
            "input_tokens": 400100, "cached_input_tokens": 200000, "output_tokens": 50,
            "reasoning_output_tokens": 0, "total_tokens": 400150,
        }, {
            "input_tokens": 200000, "cached_input_tokens": 199900, "output_tokens": 20,
            "reasoning_output_tokens": 0, "total_tokens": 200020,
        }),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_audit_uses_authoritative_cumulative_delta(tmp_path):
    rollout = tmp_path / "rollout.jsonl"
    _write_fixture(rollout)
    audit = audit_rollout(rollout, "2026-07-13", 8)
    assert audit["raw_tokens"]["total_tokens"] == 400040
    assert audit["raw_tokens"]["input_tokens"] == 400000
    assert audit["raw_tokens"]["cached_input_tokens"] == 199920
    assert audit["effective_tokens"] == 200120


def test_audit_counts_polling_and_session_reuse(tmp_path):
    rollout = tmp_path / "rollout.jsonl"
    _write_fixture(rollout)
    audit = audit_rollout(rollout, "2026-07-13", 8)
    assert audit["function_calls"] == 2
    assert audit["exec_calls"] == 1
    assert audit["write_stdin_calls"] == 1
    assert audit["poll_calls"] == 1
    assert audit["cold_cache_events"] == 1


def test_audit_never_returns_raw_command_or_output(tmp_path):
    rollout = tmp_path / "rollout.jsonl"
    _write_fixture(rollout)
    audit = audit_rollout(rollout, "2026-07-13", 8)
    serialized = json.dumps(audit, ensure_ascii=False)
    rendered = format_audit(audit)
    assert "TOPSECRET" not in serialized
    assert "TOPSECRET" not in rendered
    assert audit["tool_output_bytes"] == len("TOPSECRET-OUTPUT".encode("utf-8"))


def test_warning_when_polling_does_not_reuse_session(tmp_path):
    rollout = tmp_path / "rollout.jsonl"
    _write_fixture(rollout)
    audit = audit_rollout(rollout, "2026-07-13", 8)
    audit["write_stdin_calls"] = 0
    rendered = format_audit(audit)
    assert "未复用 write_stdin" in rendered
    assert "上下文已超过 200K" in rendered


def test_diff_snapshots_records_causes_without_control_action():
    start = {
        "rollout": "x", "raw_tokens": {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 10, "reasoning_output_tokens": 0, "total_tokens": 110},
        "effective_tokens": 30, "function_calls": 1, "exec_calls": 1, "write_stdin_calls": 0,
        "poll_calls": 0, "tool_output_bytes": 10, "last_input_tokens": 100,
        "max_input_tokens": 100, "cold_cache_events": 0, "actions": [],
    }
    end = {
        "rollout": "x", "raw_tokens": {"input_tokens": 1100, "cached_input_tokens": 880, "output_tokens": 30, "reasoning_output_tokens": 0, "total_tokens": 1130},
        "effective_tokens": 250, "function_calls": 3, "exec_calls": 3, "write_stdin_calls": 0,
        "poll_calls": 1, "tool_output_bytes": 30, "last_input_tokens": 500,
        "max_input_tokens": 500, "cold_cache_events": 1,
        "actions": [{"action": "回测轮询", "input_tokens": 500, "cached_input_tokens": 400, "output_tokens": 10, "reasoning_output_tokens": 0, "total_tokens": 510, "effective_tokens": 110}],
    }
    result = diff_snapshots(start, end)
    assert result["delta"]["raw_total"] == 1020
    assert result["delta"]["non_cached_effective"] == 220
    assert {item["type"] for item in result["causes"]} >= {"context_replay", "backtest_polling", "cold_cache"}
    assert "action" not in result


def test_discover_rollout_supports_explicit_override(monkeypatch, tmp_path):
    rollout = tmp_path / "rollout.jsonl"
    rollout.write_text("", encoding="utf-8")
    monkeypatch.setenv("CODEX_ROLLOUT_PATH", str(rollout))
    assert discover_current_rollout(tmp_path) == str(rollout.resolve())
