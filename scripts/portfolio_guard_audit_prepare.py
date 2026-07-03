#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from mt5_portfolio_deploy_win import (  # noqa: E402
    DEFAULT_PROFILE_ROOT,
    MT5_DATA,
    MT5_HOME,
    deploy,
    install_startup_assets,
    start_terminal,
    start_with_config,
)
from mt5_portfolio_profile_audit import audit_profile  # noqa: E402
from shared_guard_log_audit import audit_events, expectations_from_manifest, latest_logs, parse_events, render  # noqa: E402


DEFAULT_SCHEDULE_CONFIG = ROOT / "config" / "portfolio_schedules.yaml"
DEFAULT_STRATEGY_CONFIG = ROOT / "config" / "strategies.yaml"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "backtest"


@dataclass(frozen=True)
class GuardAuditPrepareResult:
    generated_profile: Path
    installed_profile: Path
    manifest: Path
    profile_audit: Path
    log_audit: Path
    report: str
    passed: bool


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def prepare_guard_audit(args: argparse.Namespace) -> GuardAuditPrepareResult:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.output_prefix or f"portfolio_guard_audit_{args.schedule}"

    deploy_args = SimpleNamespace(
        schedule=args.schedule,
        schedule_config=args.schedule_config,
        strategy_config=args.strategy_config,
        generated_root=args.generated_root,
        profile_name=args.profile_name,
        guard_key_suffix=args.guard_key_suffix,
        no_entry_month=args.no_entry_month,
        mt5_home=args.mt5_home,
        mt5_data=args.mt5_data,
        compile=args.compile,
        start=False,
    )
    generated, installed = deploy(deploy_args)
    manifest = generated / "portfolio_manifest.yaml"

    profile_errors, profile_report = audit_profile(
        generated,
        args.schedule,
        args.schedule_config,
        args.strategy_config,
    )
    installed_errors, installed_report = audit_profile(
        installed,
        args.schedule,
        args.schedule_config,
        args.strategy_config,
    )
    profile_audit_path = output_dir / f"{prefix}_profile_audit.md"
    write_report(
        profile_audit_path,
        profile_report + "\n---\n\n" + installed_report,
    )

    startup_assets = install_startup_assets(
        generated,
        args.mt5_data,
        installed.name,
        args.strategy_config,
        args.setup_delay_sec,
    )

    if args.start:
        if args.start_mode == "startup":
            start_with_config(args.mt5_home, startup_assets.config_ini)
        else:
            start_terminal(args.mt5_home, installed.name)
        if args.post_start_wait > 0:
            time.sleep(args.post_start_wait)

    expect_key, expect_versions = expectations_from_manifest(manifest)
    logs = args.log or latest_logs(args.mt5_data, args.latest_logs)
    log_errors: list[str] = []
    events = []
    if logs:
        events = parse_events(logs)
        log_errors = audit_events(events, expect_key, expect_versions)
        log_report = render(events, log_errors)
    else:
        log_errors = [f"no logs found under {args.mt5_data}"]
        log_report = render([], log_errors)
    log_audit_path = output_dir / f"{prefix}_log_audit.md"
    write_report(log_audit_path, log_report)

    if args.start_mode == "startup":
        start_command = f'"{args.mt5_home / "terminal64.exe"}" /config:{startup_assets.config_ini}'
    else:
        start_command = f'"{args.mt5_home / "terminal64.exe"}" /profile:{installed.name}'
    followup_command = (
        f"python scripts\\shared_guard_log_audit.py --manifest {manifest} "
        f"--output {output_dir / (prefix + '_runtime_log_audit.md')}"
    )

    require_log_audit = args.start or getattr(args, "require_log_audit", False)
    passed = not profile_errors and not installed_errors and (not log_errors if require_log_audit else True)

    report_lines = [
        f"# Portfolio guard audit prepare: {args.schedule}",
        "",
        f"generated_profile={generated}",
        f"installed_profile={installed}",
        f"manifest={manifest}",
        f"profile_audit={profile_audit_path}",
        f"log_audit={log_audit_path}",
        f"no_entry_month={args.no_entry_month}",
        f"guard_key_suffix={args.guard_key_suffix}",
        f"compiled={str(args.compile).lower()}",
        f"started={str(args.start).lower()}",
        f"start_mode={args.start_mode}",
        f"startup_config={startup_assets.config_ini}",
        f"startup_set={startup_assets.setup_set}",
        f"startup_templates={len(startup_assets.templates)}",
        "",
        "## Current Log Audit",
        "",
        f"events={len(events)} pass={str(not log_errors).lower()}",
        "",
        "## Commands",
        "",
        f"start_command={start_command}",
        f"followup_audit_command={followup_command}",
        "",
        "## Result",
        "",
        f"pass={str(passed).lower()}",
    ]
    if profile_errors or installed_errors:
        report_lines.append("")
        report_lines.append("### Profile errors")
        for error in profile_errors + installed_errors:
            report_lines.append(f"- {error}")
    if log_errors:
        report_lines.append("")
        report_lines.append("### Current log audit errors")
        for error in log_errors:
            report_lines.append(f"- {error}")
    report = "\n".join(report_lines) + "\n"
    if args.output:
        write_report(args.output, report)

    return GuardAuditPrepareResult(
        generated_profile=generated,
        installed_profile=installed,
        manifest=manifest,
        profile_audit=profile_audit_path,
        log_audit=log_audit_path,
        report=report,
        passed=passed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a no-entry MT5 portfolio profile for shared guard log audit.")
    parser.add_argument("--schedule", default="r224_r225_r226_r211_r213_r216_r227_deployable_context")
    parser.add_argument("--schedule-config", type=Path, default=DEFAULT_SCHEDULE_CONFIG)
    parser.add_argument("--strategy-config", type=Path, default=DEFAULT_STRATEGY_CONFIG)
    parser.add_argument("--generated-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    parser.add_argument("--profile-name", default="WaiTrade2_Portfolio_BTC_GuardAudit_NoEntry")
    parser.add_argument("--guard-key-suffix", required=True)
    parser.add_argument("--no-entry-month", type=int, default=12)
    parser.add_argument("--mt5-home", type=Path, default=MT5_HOME)
    parser.add_argument("--mt5-data", type=Path, default=MT5_DATA)
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--start", action="store_true", help="Start MT5 after preparing. Default is deploy/audit only.")
    parser.add_argument(
        "--start-mode",
        choices=("profile", "startup"),
        default="startup",
        help="startup uses /config:[StartUp] PortfolioSetup + templates; profile uses raw /profile.",
    )
    parser.add_argument("--setup-delay-sec", type=int, default=5)
    parser.add_argument("--post-start-wait", type=float, default=15.0, help="Seconds to wait before scanning logs after --start.")
    parser.add_argument(
        "--require-log-audit",
        action="store_true",
        help="Fail when current logs do not contain the expected shared guard events, without starting MT5.",
    )
    parser.add_argument("--log", action="append", type=Path, default=[])
    parser.add_argument("--latest-logs", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-prefix", default="")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = prepare_guard_audit(args)
    print(result.report, end="")
    raise SystemExit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
