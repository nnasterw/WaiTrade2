#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""低输出审计 Codex rollout 的真实 token_count，不读取或打印消息正文。"""
import argparse
import datetime
import json
import os
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

TOKEN_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)


def _parse_timestamp(value, tz_offset_hours):
    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    target_tz = datetime.timezone(datetime.timedelta(hours=tz_offset_hours))
    return parsed.astimezone(target_tz)


def _parse_date(value):
    if value is None:
        return None
    return datetime.datetime.strptime(value, "%Y-%m-%d").date()


def _token_dict(value):
    value = value or {}
    return {name: int(value.get(name, 0) or 0) for name in TOKEN_FIELDS}


def _subtract_tokens(current, previous):
    return {name: current.get(name, 0) - previous.get(name, 0) for name in TOKEN_FIELDS}


def _effective_tokens(tokens):
    """Codex goal 使用的非缓存等效口径。"""
    return (
        tokens.get("input_tokens", 0)
        - tokens.get("cached_input_tokens", 0)
        + tokens.get("output_tokens", 0)
    )


def _classify_function(payload):
    name = payload.get("name", "unknown")
    if name != "exec_command":
        return name
    try:
        arguments = json.loads(payload.get("arguments", "{}"))
    except (TypeError, ValueError):
        arguments = {}
    command = str(arguments.get("cmd") or arguments.get("command") or "")
    lower = command.lower().replace("\\", "/")
    if "start-sleep" in lower or (
        "get-process" in lower and ("terminal64" in lower or "metatester" in lower)
    ):
        return "回测轮询"
    if "mt5_backtest_win.py" in lower or "mt5_cli_backtest.py" in lower:
        return "启动MT5回测"
    if "check_strategy_consistency.py" in lower:
        return "策略检查"
    if "yaml_to_set.py" in lower:
        return "生成SET"
    if "wfys" in lower:
        return "WFYS"
    if "get-content" in lower or "select-string" in lower or "rg " in lower or "grep " in lower:
        return "读取/搜索"
    if "git " in lower or lower.strip().startswith("git"):
        return "Git"
    return "其他Shell"


def audit_rollout(rollout_path, date_text=None, tz_offset_hours=8):
    """返回 token 与工具元数据摘要；消息、命令和工具输出正文不会进入结果。"""
    path = Path(rollout_path)
    target_date = _parse_date(date_text)
    previous_total = {name: 0 for name in TOKEN_FIELDS}
    baseline_total = None
    final_total = None
    first_input = None
    last_input = None
    max_input = 0
    usage_events = 0
    function_calls = 0
    exec_calls = 0
    write_stdin_calls = 0
    poll_calls = 0
    tool_output_bytes = 0
    cold_cache_events = 0
    latest_action = "无"
    action_tokens = defaultdict(Counter)

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            timestamp_text = event.get("timestamp")
            if not timestamp_text:
                continue
            timestamp = _parse_timestamp(timestamp_text, tz_offset_hours)
            selected = target_date is None or timestamp.date() == target_date
            payload = event.get("payload") or {}
            top_type = event.get("type")
            payload_type = payload.get("type")

            if top_type == "response_item" and payload_type == "function_call":
                latest_action = _classify_function(payload)
                if selected:
                    function_calls += 1
                    name = payload.get("name")
                    if name == "exec_command":
                        exec_calls += 1
                    elif name == "write_stdin":
                        write_stdin_calls += 1
                    if latest_action == "回测轮询":
                        poll_calls += 1
                continue

            if top_type == "response_item" and payload_type == "function_call_output":
                if selected:
                    # 只计字节数；不解析、不返回工具输出正文。
                    tool_output_bytes += len(str(payload.get("output", "")).encode("utf-8"))
                continue

            if top_type != "event_msg" or payload_type != "token_count":
                continue
            info = payload.get("info")
            if not info:
                continue
            current_total = _token_dict(info.get("total_token_usage"))
            last_usage = _token_dict(info.get("last_token_usage"))

            if target_date is not None and timestamp.date() < target_date:
                baseline_total = current_total
            if selected:
                if baseline_total is None:
                    baseline_total = previous_total
                final_total = current_total
                usage_events += 1
                current_input = last_usage["input_tokens"]
                if first_input is None:
                    first_input = current_input
                last_input = current_input
                max_input = max(max_input, current_input)
                non_cached = current_input - last_usage["cached_input_tokens"]
                if non_cached >= 100000:
                    cold_cache_events += 1
                step_delta = _subtract_tokens(current_total, previous_total)
                for name, value in step_delta.items():
                    action_tokens[latest_action][name] += value
            previous_total = current_total

    if final_total is None:
        delta = {name: 0 for name in TOKEN_FIELDS}
    else:
        delta = _subtract_tokens(final_total, baseline_total or {})

    actions = []
    for action, values in action_tokens.items():
        item = {name: int(values.get(name, 0)) for name in TOKEN_FIELDS}
        item["action"] = action
        item["effective_tokens"] = _effective_tokens(item)
        actions.append(item)
    actions.sort(key=lambda item: item["total_tokens"], reverse=True)

    return {
        "rollout": str(path),
        "date": date_text or "全部",
        "timezone_offset_hours": tz_offset_hours,
        "raw_tokens": delta,
        "effective_tokens": _effective_tokens(delta),
        "usage_events": usage_events,
        "function_calls": function_calls,
        "exec_calls": exec_calls,
        "write_stdin_calls": write_stdin_calls,
        "poll_calls": poll_calls,
        "tool_output_bytes": tool_output_bytes,
        "first_input_tokens": first_input or 0,
        "last_input_tokens": last_input or 0,
        "max_input_tokens": max_input,
        "cold_cache_events": cold_cache_events,
        "actions": actions,
    }


def discover_current_rollout(project_root, codex_home=None):
    """从 Codex 状态库定位当前项目最近更新的未归档 rollout。"""
    override = os.environ.get("CODEX_ROLLOUT_PATH")
    if override and Path(override).exists():
        return str(Path(override).resolve())
    home = Path(codex_home) if codex_home else Path.home() / ".codex"
    database = home / "state_5.sqlite"
    if not database.exists():
        return None
    connection = sqlite3.connect("file:" + str(database) + "?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "select rollout_path,cwd from threads where archived=0 order by updated_at_ms desc"
        ).fetchall()
    finally:
        connection.close()
    prefix = chr(92) * 2 + "?" + chr(92)

    def normalize(value):
        cleaned = str(value or "")
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
        return os.path.normcase(os.path.abspath(cleaned))

    expected = normalize(project_root)
    for rollout_path, cwd in rows:
        if normalize(cwd) == expected and rollout_path:
            cleaned = str(rollout_path)
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
            if Path(cleaned).exists():
                return str(Path(cleaned).resolve())
    return None


def snapshot_rollout(rollout_path):
    audit = audit_rollout(rollout_path)
    return {
        "rollout": audit["rollout"],
        "raw_tokens": audit["raw_tokens"],
        "effective_tokens": audit["effective_tokens"],
        "usage_events": audit["usage_events"],
        "function_calls": audit["function_calls"],
        "exec_calls": audit["exec_calls"],
        "write_stdin_calls": audit["write_stdin_calls"],
        "poll_calls": audit["poll_calls"],
        "tool_output_bytes": audit["tool_output_bytes"],
        "last_input_tokens": audit["last_input_tokens"],
        "max_input_tokens": audit["max_input_tokens"],
        "cold_cache_events": audit["cold_cache_events"],
        "actions": audit["actions"],
    }


def _action_map(snapshot):
    return {item.get("action"): item for item in snapshot.get("actions") or []}


def diff_snapshots(start, end):
    raw_start = start.get("raw_tokens") or {}
    raw_end = end.get("raw_tokens") or {}
    fields = set(raw_start) | set(raw_end)
    raw_delta = {key: int(raw_end.get(key, 0)) - int(raw_start.get(key, 0)) for key in fields}
    effective = int(end.get("effective_tokens", 0)) - int(start.get("effective_tokens", 0))
    start_actions = _action_map(start)
    end_actions = _action_map(end)
    actions = []
    for action in sorted(set(start_actions) | set(end_actions)):
        before = start_actions.get(action) or {}
        after = end_actions.get(action) or {}
        item = {"action": action}
        for key in TOKEN_FIELDS + ("effective_tokens",):
            item[key] = int(after.get(key, 0)) - int(before.get(key, 0))
        if item["total_tokens"] or item["effective_tokens"]:
            actions.append(item)
    actions.sort(key=lambda item: item["total_tokens"], reverse=True)

    causes = []
    if raw_delta.get("cached_input_tokens", 0) > 0:
        causes.append({"type": "context_replay", "raw_tokens": raw_delta["cached_input_tokens"]})
    polling = next((item for item in actions if item["action"] == "回测轮询"), None)
    if polling:
        causes.append({"type": "backtest_polling", "raw_tokens": polling["total_tokens"]})
    cold_events = int(end.get("cold_cache_events", 0)) - int(start.get("cold_cache_events", 0))
    if cold_events > 0:
        causes.append({"type": "cold_cache", "events": cold_events})
    exec_delta = int(end.get("exec_calls", 0)) - int(start.get("exec_calls", 0))
    if exec_delta > 20:
        causes.append({"type": "fragmented_calls", "exec_calls": exec_delta})

    return {
        "source": "codex_token_count",
        "rollout": end.get("rollout"),
        "delta": {
            "raw_total": raw_delta.get("total_tokens", 0),
            "input": raw_delta.get("input_tokens", 0),
            "cached_input": raw_delta.get("cached_input_tokens", 0),
            "output": raw_delta.get("output_tokens", 0),
            "reasoning_output": raw_delta.get("reasoning_output_tokens", 0),
            "non_cached_effective": effective,
        },
        "context": {
            "start_last_input": start.get("last_input_tokens", 0),
            "end_last_input": end.get("last_input_tokens", 0),
            "max_call_input": end.get("max_input_tokens", 0),
            "cold_cache_events": max(cold_events, 0),
        },
        "tools": {
            "function_calls": int(end.get("function_calls", 0)) - int(start.get("function_calls", 0)),
            "exec_calls": exec_delta,
            "write_stdin_calls": int(end.get("write_stdin_calls", 0)) - int(start.get("write_stdin_calls", 0)),
            "poll_calls": int(end.get("poll_calls", 0)) - int(start.get("poll_calls", 0)),
            "tool_output_bytes": int(end.get("tool_output_bytes", 0)) - int(start.get("tool_output_bytes", 0)),
        },
        "by_stage": {},
        "causes": causes,
        "actions": actions,
    }


def format_audit(audit):
    raw = audit["raw_tokens"]
    input_tokens = raw["input_tokens"]
    cached_ratio = 0.0
    if input_tokens > 0:
        cached_ratio = raw["cached_input_tokens"] * 100.0 / input_tokens
    lines = [
        "=== Codex token 审计 ===",
        "日期: " + str(audit["date"]) + " (UTC" + ("+" if audit["timezone_offset_hours"] >= 0 else "") + str(audit["timezone_offset_hours"]) + ")",
        "Raw total: " + str(raw["total_tokens"]),
        "  input/cached/output: " + str(raw["input_tokens"]) + " / " + str(raw["cached_input_tokens"]) + " / " + str(raw["output_tokens"]),
        "非缓存等效: " + str(audit["effective_tokens"]),
        "缓存命中占输入: " + ("%.2f%%" % cached_ratio),
        "调用: usage=" + str(audit["usage_events"]) + ", function=" + str(audit["function_calls"]) + ", exec=" + str(audit["exec_calls"]) + ", write_stdin=" + str(audit["write_stdin_calls"]),
        "回测轮询: " + str(audit["poll_calls"]) + ", 冷缓存事件: " + str(audit["cold_cache_events"]),
        "单次输入 first/last/max: " + str(audit["first_input_tokens"]) + " / " + str(audit["last_input_tokens"]) + " / " + str(audit["max_input_tokens"]),
        "工具输出字节: " + str(audit["tool_output_bytes"]),
    ]
    if audit["poll_calls"] > 0 and audit["write_stdin_calls"] == 0:
        lines.append("[WARN] 存在回测轮询但未复用 write_stdin session")
    if audit["max_input_tokens"] >= 200000:
        lines.append("[WARN] 上下文已超过 200K；阶段提交后应 handoff 到新任务")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="低输出审计 Codex rollout token_count")
    parser.add_argument("rollout", help="Codex rollout JSONL 路径")
    parser.add_argument("--date", help="按本地日期筛选，格式 YYYY-MM-DD")
    parser.add_argument("--tz-offset", type=int, default=8, help="时区 UTC 偏移，默认 +8")
    parser.add_argument("--json", action="store_true", help="输出结构化摘要")
    args = parser.parse_args(argv)
    audit = audit_rollout(args.rollout, args.date, args.tz_offset)
    if args.json:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    else:
        print(format_audit(audit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
