#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import yaml

try:
    from .shared_guard_log_audit import read_log
except ImportError:
    from shared_guard_log_audit import read_log


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "temp" / "portfolio_profiles" / "v11a" / "portfolio_manifest.yaml"
DEFAULT_PORTABLE_ROOT = ROOT / "temp" / "mt5_portable_v11a"
DEFAULT_OUTPUT = ROOT / "results" / "live" / "v11a_live_status.md"

HEARTBEAT_RE = re.compile(r"HEARTBEAT\s+(?P<version>[^|]+)\|(?P<body>.*)")
LOG_TIME_RE = re.compile(r"\b(?P<hour>\d{1,2}):(?P<minute>\d{2}):(?P<second>\d{2})\.\d{3}\b")
GUARD_RE = re.compile(r"SHARED_GUARD\s+(?P<body>.*)")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
OPEN_RE = re.compile(r"(?:开仓成功|寮€浠撴垚鍔).*?ticket=(?P<ticket>\d+).*?lot=(?P<lot>[\d.]+)")
CLOSE_RE = re.compile(r"(?:平仓|close|ClosePosition|market_close)", re.IGNORECASE)
ERROR_RE = re.compile(r"retcode=|10016|trade_retcod|invalid stops|开仓失败|止损无效|寮€浠撳け璐", re.IGNORECASE)
DISCONNECT_RE = re.compile(r"disconnected|connection .*lost", re.IGNORECASE)
AUTH_RE = re.compile(r"authorized on .* through", re.IGNORECASE)


@dataclass
class StreamStatus:
    stream: str
    version: str
    magic: str
    path: Path
    process_id: str
    authorized: bool
    trading_enabled: bool
    loaded: bool
    guard_event: str
    heartbeat: str
    heartbeat_age_min: int | None
    heartbeat_fresh: bool
    opens: int
    closes: int
    errors: int
    heartbeats: int
    guard_events: int
    disconnects: int
    latest_bar: str = ""
    latest_ob: str = ""
    latest_pos: str = ""
    latest_atr: str = ""
    latest_spread: str = ""
    latest_state: str = ""
    process_start: str = ""
    uptime_min: int | None = None
    last_disconnect: str = ""
    reconnects: int = 0
    last_reconnect: str = ""
    last_error: str = ""


def load_manifest(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("charts") or [])


def terminal_processes() -> dict[str, dict[str, str]]:
    command = (
        "Get-Process terminal64 -ErrorAction SilentlyContinue | "
        "Select-Object Id,Path,@{Name='StartTime';Expression={$_.StartTime.ToString('yyyy-MM-dd HH:mm:ss')}} | "
        "ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {}
    import json

    data = json.loads(result.stdout)
    if isinstance(data, dict):
        data = [data]
    processes: dict[str, dict[str, str]] = {}
    for item in data:
        path = str(item.get("Path") or "").lower()
        if path:
            processes[path] = {
                "id": str(item.get("Id") or ""),
                "start_time": str(item.get("StartTime") or ""),
            }
    return processes


def uptime_minutes(start_time: str, now: datetime) -> int | None:
    if not start_time:
        return None
    try:
        start = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return max(0, int((now - start).total_seconds() // 60))


def latest_log_text(path: Path) -> str:
    if not path.exists():
        return ""
    return read_log(path)


def newest_log(root: Path) -> Path | None:
    if not root.exists():
        return None
    logs = [
        path
        for path in root.glob("*.log")
        if path.is_file() and re.fullmatch(r"\d{8}\.log", path.name)
    ]
    if not logs:
        return None
    return max(logs, key=lambda path: path.stat().st_mtime)


def recent_logs(root: Path, limit: int = 2) -> list[Path]:
    if not root.exists():
        return []
    logs = [
        path
        for path in root.glob("*.log")
        if path.is_file() and re.fullmatch(r"\d{8}\.log", path.name)
    ]
    return sorted(logs, key=lambda path: path.name, reverse=True)[:limit]


def combined_log_text(paths: list[Path]) -> str:
    parts = []
    for path in sorted(paths, key=lambda item: item.name):
        text = latest_log_text(path)
        if text:
            parts.append(text)
    return "\n".join(parts)


def last_line(text: str, pattern: re.Pattern[str]) -> str:
    result = ""
    for line in text.splitlines():
        if pattern.search(line):
            result = line.strip()
    return result


def table_cell(value: str, max_len: int = 120) -> str:
    clean = " ".join(value.replace("|", "/").split())
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 3] + "..."


def to_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def reconnect_info(text: str) -> tuple[int, str]:
    reconnects = 0
    last_reconnect = ""
    pending_disconnect = False
    for line in text.splitlines():
        if DISCONNECT_RE.search(line):
            pending_disconnect = True
            continue
        if pending_disconnect and AUTH_RE.search(line):
            reconnects += 1
            last_reconnect = line.strip()
            pending_disconnect = False
    return reconnects, last_reconnect


def filter_since(text: str, log_path: Path | None, now: datetime, since: datetime | None) -> str:
    if since is None:
        return text
    lines: list[str] = []
    for line in text.splitlines():
        timestamp = line_time(line, log_path, now)
        if timestamp is None or timestamp >= since:
            lines.append(line)
    return "\n".join(lines)


def guard_event(text: str) -> str:
    latest = ""
    for line in text.splitlines():
        match = GUARD_RE.search(line)
        if not match:
            continue
        fields = {key: value for key, value in KV_RE.findall(match.group("body"))}
        latest = fields.get("event", "")
    return latest


def line_time(line: str, log_path: Path | None, now: datetime) -> datetime | None:
    match = LOG_TIME_RE.search(line)
    if not match:
        return None
    base = datetime.fromtimestamp(log_path.stat().st_mtime) if log_path and log_path.exists() else now
    item = base.replace(
        hour=int(match.group("hour")),
        minute=int(match.group("minute")),
        second=int(match.group("second")),
        microsecond=0,
    )
    if item > now + timedelta(minutes=5):
        item -= timedelta(days=1)
    return item


def heartbeat_info(text: str, log_path: Path | None, now: datetime) -> tuple[str, int | None]:
    line = last_line(text, HEARTBEAT_RE)
    if not line:
        return "", None
    marker = "HEARTBEAT "
    text_value = line[line.find(marker) + len(marker) :] if marker in line else line
    timestamp = line_time(line, log_path, now)
    if timestamp is None:
        return text_value, None
    age = max(0, int((now - timestamp).total_seconds() // 60))
    return text_value, age


def heartbeat_text(text: str) -> str:
    return heartbeat_info(text, None, datetime.now())[0]


def heartbeat_fields(heartbeat: str) -> dict[str, str]:
    return {key: value for key, value in KV_RE.findall(heartbeat)}


def stream_status(
    chart: dict,
    portable_root: Path,
    processes: dict[str, dict[str, str]],
    now: datetime,
    max_heartbeat_age_min: int,
    since: datetime | None,
) -> StreamStatus:
    stream = str(chart.get("stream") or "")
    stream_dir = portable_root / stream
    terminal = stream_dir / "terminal64.exe"
    term_log_paths = recent_logs(stream_dir / "logs")
    mql_log_paths = recent_logs(stream_dir / "MQL5" / "Logs")
    term_log_path = term_log_paths[0] if term_log_paths else None
    mql_log_path = mql_log_paths[0] if mql_log_paths else None
    term_log = combined_log_text(term_log_paths)
    mql_log = combined_log_text(mql_log_paths)
    combined = term_log + "\n" + mql_log
    window_term_log = filter_since(term_log, term_log_path, now, since)
    window_mql_log = filter_since(mql_log, mql_log_path, now, since)
    window_combined = window_term_log + "\n" + window_mql_log
    process = processes.get(str(terminal).lower(), {})
    process_id = process.get("id", "")
    process_start = process.get("start_time", "")

    heartbeat, heartbeat_age = heartbeat_info(mql_log, mql_log_path, now)
    hb_fields = heartbeat_fields(heartbeat)
    reconnects, last_reconnect = reconnect_info(window_term_log)

    return StreamStatus(
        stream=stream,
        version=str(chart.get("version") or ""),
        magic=str(chart.get("magic_number") or ""),
        path=stream_dir,
        process_id=process_id,
        authorized="authorized on" in term_log,
        trading_enabled="trading has been enabled" in term_log,
        loaded="loaded successfully" in term_log and str(chart.get("version") or "") in mql_log,
        guard_event=guard_event(mql_log),
        heartbeat=heartbeat,
        heartbeat_age_min=heartbeat_age,
        heartbeat_fresh=heartbeat_age is not None and heartbeat_age <= max_heartbeat_age_min,
        opens=len(OPEN_RE.findall(window_combined)),
        closes=len(CLOSE_RE.findall(window_combined)),
        errors=len(ERROR_RE.findall(window_combined)),
        heartbeats=len(HEARTBEAT_RE.findall(window_mql_log)),
        guard_events=len(GUARD_RE.findall(window_mql_log)),
        disconnects=len(DISCONNECT_RE.findall(window_term_log)),
        latest_bar=hb_fields.get("bar", ""),
        latest_ob=hb_fields.get("ob", ""),
        latest_pos=hb_fields.get("pos", ""),
        latest_atr=hb_fields.get("atr", ""),
        latest_spread=hb_fields.get("spread", ""),
        latest_state=hb_fields.get("state", ""),
        process_start=process_start,
        uptime_min=uptime_minutes(process_start, now),
        last_disconnect=last_line(window_term_log, DISCONNECT_RE),
        reconnects=reconnects,
        last_reconnect=last_reconnect,
        last_error=last_line(window_combined, ERROR_RE),
    )


def render(
    statuses: list[StreamStatus],
    caveat: bool,
    generated_at: datetime | None = None,
    since: datetime | None = None,
    min_uptime_min: int = 0,
) -> str:
    pass_all = all(
        item.process_id
        and item.authorized
        and item.trading_enabled
        and item.loaded
        and item.guard_event
        and item.heartbeat
        and item.heartbeat_fresh
        and (min_uptime_min <= 0 or (item.uptime_min is not None and item.uptime_min >= min_uptime_min))
        for item in statuses
    )
    lines = ["# Portfolio live status", ""]
    lines.append(f"streams={len(statuses)} pass={str(pass_all).lower()}")
    if generated_at:
        lines.append(f"generated_at={generated_at:%Y-%m-%d %H:%M:%S}")
    if since:
        lines.append(f"window_since={since:%Y-%m-%d %H:%M:%S}")
    if min_uptime_min > 0:
        lines.append(f"min_uptime_min={min_uptime_min}")
    lines.append("")
    total_pos = sum(to_int(item.latest_pos) for item in statuses)
    ob_streams = sum(1 for item in statuses if to_int(item.latest_ob) > 0)
    min_uptime = min((item.uptime_min for item in statuses if item.uptime_min is not None), default=None)
    uptime_ok_count = sum(
        1
        for item in statuses
        if min_uptime_min <= 0 or (item.uptime_min is not None and item.uptime_min >= min_uptime_min)
    )
    stale_heartbeats = sum(1 for item in statuses if not item.heartbeat_fresh)
    lines.extend(
        [
            "## Summary",
            f"total_pos={total_pos}",
            f"ob_streams={ob_streams}",
            f"total_opens={sum(item.opens for item in statuses)}",
            f"total_closes={sum(item.closes for item in statuses)}",
            f"total_errors={sum(item.errors for item in statuses)}",
            f"total_disconnects={sum(item.disconnects for item in statuses)}",
            f"total_reconnects={sum(item.reconnects for item in statuses)}",
            f"stale_heartbeats={stale_heartbeats}",
            f"uptime_ok_streams={uptime_ok_count}/{len(statuses)}",
            f"min_uptime_min_seen={'-' if min_uptime is None else min_uptime}",
            "",
        ]
    )
    lines.append("| stream | pid | uptime_min | uptime_ok | started | authorized | trading | loaded | guard | hb_age_min | hb_fresh | pos | ob | spread | atr | state | opens | closes | errors | heartbeats | guard_events | disconnects | reconnects | last_disconnect | last_reconnect | last_error | heartbeat |")
    lines.append("|---|---:|---:|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|")
    for item in statuses:
        heartbeat = table_cell(item.heartbeat, max_len=180)
        age = "-" if item.heartbeat_age_min is None else str(item.heartbeat_age_min)
        uptime = "-" if item.uptime_min is None else str(item.uptime_min)
        uptime_ok = min_uptime_min <= 0 or (item.uptime_min is not None and item.uptime_min >= min_uptime_min)
        last_disconnect = table_cell(item.last_disconnect) or "-"
        last_reconnect = table_cell(item.last_reconnect) or "-"
        last_error = table_cell(item.last_error) or "-"
        lines.append(
            f"| {item.stream} | {item.process_id or '-'} | {uptime} | {str(uptime_ok).lower()} | "
            f"{item.process_start or '-'} | "
            f"{str(item.authorized).lower()} | "
            f"{str(item.trading_enabled).lower()} | {str(item.loaded).lower()} | {item.guard_event or '-'} | "
            f"{age} | {str(item.heartbeat_fresh).lower()} | {item.latest_pos or '-'} | {item.latest_ob or '-'} | "
            f"{item.latest_spread or '-'} | {item.latest_atr or '-'} | {item.latest_state or '-'} | "
            f"{item.opens} | {item.closes} | {item.errors} | "
            f"{item.heartbeats} | {item.guard_events} | {item.disconnects} | {item.reconnects} | "
            f"{last_disconnect} | {last_reconnect} | {last_error} | {heartbeat} |"
        )
    if caveat:
        lines.append("")
        lines.append("## Caveat")
        lines.append(
            "This portable multi-terminal deployment shares broker account state, but MT5 Global Variables are terminal-local. "
            "Treat shared monthly guard behavior as not equivalent to a single-terminal multi-chart deployment."
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize v11a portable MT5 live status.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--portable-root", type=Path, default=DEFAULT_PORTABLE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--max-heartbeat-age-min",
        type=int,
        default=75,
        help="EA prints HEARTBEAT hourly; fail when the latest heartbeat is older than this.",
    )
    parser.add_argument(
        "--since-hours",
        type=float,
        help="Count opens/closes/errors/heartbeats only within the last N hours. Health checks still use latest logs.",
    )
    parser.add_argument(
        "--min-uptime-min",
        type=int,
        default=0,
        help="Require each terminal process to have run at least N minutes. Useful for 24h live reviews.",
    )
    parser.add_argument("--no-caveat", action="store_true")
    args = parser.parse_args()

    processes = terminal_processes()
    now = datetime.now()
    since = now - timedelta(hours=args.since_hours) if args.since_hours else None
    statuses = [
        stream_status(chart, args.portable_root, processes, now, args.max_heartbeat_age_min, since)
        for chart in load_manifest(args.manifest)
    ]
    report = render(
        statuses,
        caveat=not args.no_caveat,
        generated_at=now,
        since=since,
        min_uptime_min=args.min_uptime_min,
    )
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    raise SystemExit(0 if "pass=true" in report.splitlines()[2] else 1)


if __name__ == "__main__":
    main()
