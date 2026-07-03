#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml


LINE_RE = re.compile(r"SHARED_GUARD\s+(.*)")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
DEFAULT_MT5_DATA = Path(
    os.environ.get(
        "MT5_DATA",
        os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075"),
    )
)


def read_log(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw[:200].count(b"\x00") > 20:
        return raw.decode("utf-16-le", errors="replace")
    for encoding in ("utf-8-sig", "utf-8", "utf-16-le"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_events(paths: list[Path]) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for path in paths:
        if not path.exists():
            raise SystemExit(f"missing log: {path}")
        for line in read_log(path).splitlines():
            match = LINE_RE.search(line)
            if not match:
                continue
            item = {key: value for key, value in KV_RE.findall(match.group(1))}
            item["file"] = str(path)
            events.append(item)
    return events


def latest_logs(mt5_data: Path, limit: int = 2) -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()
    for subdir in ("logs", "Tester/logs", "MQL5/Logs", "MQL5/logs"):
        root = mt5_data / subdir
        if root.exists():
            for path in root.glob("*.log"):
                if not path.is_file():
                    continue
                resolved = str(path.resolve()).lower()
                if resolved in seen:
                    continue
                seen.add(resolved)
                candidates.append(path)
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[:limit]


def expectations_from_manifest(path: Path) -> tuple[str, set[str]]:
    manifest = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    charts = manifest.get("charts") or []
    keys = {
        str(chart.get("shared_monthly_guard_key", ""))
        for chart in charts
        if chart.get("shared_monthly_guard_key")
    }
    if len(keys) != 1:
        raise SystemExit(f"manifest must contain exactly one shared guard key, found {sorted(keys)}")
    versions = {
        str(chart.get("version", ""))
        for chart in charts
        if chart.get("version")
    }
    if not versions:
        raise SystemExit(f"manifest has no chart versions: {path}")
    return next(iter(keys)), versions


def audit_events(
    events: list[dict[str, str]],
    expect_key: str = "",
    expect_versions: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not events:
        return ["no SHARED_GUARD events found"]

    keys = {event.get("key", "") for event in events}
    if expect_key and keys != {expect_key}:
        errors.append(f"expected key {expect_key}, found {sorted(keys)}")

    if expect_versions:
        versions = {event.get("version", "") for event in events}
        missing = expect_versions - versions
        if missing:
            errors.append(f"missing versions: {sorted(missing)}")

    event_names = {event.get("event", "") for event in events}
    if not ({"init", "load"} & event_names):
        errors.append("missing init/load event")

    return errors


def render(events: list[dict[str, str]], errors: list[str]) -> str:
    by_event = Counter(event.get("event", "") for event in events)
    by_version = Counter(event.get("version", "") for event in events)
    by_key_month: dict[tuple[str, str], set[str]] = defaultdict(set)
    for event in events:
        by_key_month[(event.get("key", ""), event.get("month", ""))].add(event.get("version", ""))

    lines = ["# Shared monthly guard audit", ""]
    lines.append(f"events={len(events)} pass={str(not errors).lower()}")
    lines.append("")
    lines.append("| event | count |")
    lines.append("|---|---:|")
    for event_name, count in sorted(by_event.items()):
        lines.append(f"| {event_name} | {count} |")
    lines.append("")
    lines.append("| version | count |")
    lines.append("|---|---:|")
    for version, count in sorted(by_version.items()):
        lines.append(f"| {version} | {count} |")
    lines.append("")
    lines.append("| key | month | versions |")
    lines.append("|---|---|---|")
    for (key, month), versions in sorted(by_key_month.items()):
        lines.append(f"| {key} | {month} | {','.join(sorted(versions))} |")
    if errors:
        lines.append("")
        lines.append("## Errors")
        for error in errors:
            lines.append(f"- {error}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit SHARED_GUARD diagnostics from MT5 logs.")
    parser.add_argument("--log", action="append", type=Path, default=[])
    parser.add_argument("--manifest", type=Path, help="Generated portfolio_manifest.yaml to infer key and versions.")
    parser.add_argument("--mt5-data", type=Path, default=DEFAULT_MT5_DATA)
    parser.add_argument("--expect-key", default="")
    parser.add_argument("--expect-version", action="append", default=[])
    parser.add_argument("--latest-logs", type=int, default=2, help="Use newest MT5 logs when --log is omitted.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    expect_key = args.expect_key
    expect_versions = set(args.expect_version)
    if args.manifest:
        manifest_key, manifest_versions = expectations_from_manifest(args.manifest)
        expect_key = expect_key or manifest_key
        expect_versions = expect_versions or manifest_versions

    logs = args.log or latest_logs(args.mt5_data, args.latest_logs)
    if not logs:
        raise SystemExit(f"no logs found under {args.mt5_data}")

    events = parse_events(logs)
    errors = audit_events(events, expect_key, expect_versions)
    report = render(events, errors)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
