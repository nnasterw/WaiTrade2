#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from mt5_portfolio_deploy_win import deploy  # noqa: E402
from mt5_portfolio_profile_audit import audit_profile  # noqa: E402
from portfolio_return_sim import run_schedule as run_return_schedule  # noqa: E402
from portfolio_schedule_lint import lint_config  # noqa: E402
from portfolio_schedule_runner import DEFAULT_CONFIG, load_config, run_schedule  # noqa: E402
from portfolio_schedule_stress import parse_costs, render as render_stress, stress_schedule  # noqa: E402


DEFAULT_STRATEGY_CONFIG = ROOT / "config" / "strategies.yaml"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "backtest"
DEFAULT_GENERATED_ROOT = ROOT / "temp" / "portfolio_profiles"
DEFAULT_MT5_HOME = Path(os.environ.get("MT5_HOME", r"C:\Program Files\MetaTrader 5"))
DEFAULT_MT5_DATA = Path(
    os.environ.get(
        "MT5_DATA",
        os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075"),
    )
)


@dataclass(frozen=True)
class PreflightResult:
    passed: bool
    report: str
    generated_profile: Path | None = None
    installed_profile: Path | None = None


def bool_text(value: bool) -> str:
    return str(value).lower()


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_preflight(args: argparse.Namespace) -> PreflightResult:
    errors: list[str] = []
    prefix = args.output_prefix or f"portfolio_{args.schedule}_preflight"
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    schedules = load_config(args.schedule_config)
    schedule = schedules[args.schedule]
    schedule_preflight = schedule.get("preflight") or {}
    require_cost_pass = (
        args.require_cost_pass
        if args.require_cost_pass is not None
        else float(schedule_preflight.get("require_cost_pass", 0.5))
    )

    sections: list[str] = [
        f"# Portfolio preflight: {args.schedule}",
        "",
        "warning: preflight does not start MT5 and is not a true multi-stream Strategy Tester backtest.",
        "",
    ]

    lint_errors = lint_config(args.schedule_config, args.schedule, args.strategy_config)
    if lint_errors:
        errors.extend(lint_errors)
    sections.extend(["## Lint", "", f"pass={bool_text(not lint_errors)}", ""])
    for error in lint_errors:
        sections.append(f"- {error}")
    if lint_errors:
        sections.append("")

    proxy_report, proxy_audit = run_schedule(args.schedule_config, args.schedule)
    proxy_path = output_dir / f"{prefix}_proxy.md"
    write_report(proxy_path, proxy_report)
    if not proxy_audit.passed:
        errors.append("portfolio schedule proxy target failed")
    sections.extend(
        [
            "## Proxy",
            "",
            f"file={proxy_path}",
            (
                f"total={proxy_audit.total_profit:.2f} daily={proxy_audit.daily_trades:.2f} "
                f"bad={len(proxy_audit.bad_months)} pass={bool_text(proxy_audit.passed)}"
            ),
            "",
        ]
    )

    stress_rows = stress_schedule(args.schedule_config, args.schedule, parse_costs(args.costs))
    stress_report = render_stress(stress_rows)
    stress_path = output_dir / f"{prefix}_stress.md"
    write_report(stress_path, stress_report)
    required = [row for row in stress_rows if abs(row.cost_per_trade - require_cost_pass) < 1e-9]
    if not required:
        errors.append(f"required stress cost {require_cost_pass:g} not present")
    elif required[0].bad_months:
        errors.append(
            f"stress cost {require_cost_pass:g} has {len(required[0].bad_months)} bad months"
        )
    sections.extend(
        [
            "## Stress",
            "",
            f"file={stress_path}",
            f"required_cost_pass={require_cost_pass:g}",
            "",
        ]
    )
    for row in stress_rows:
        weakest = row.min_month.month if row.min_month else ""
        weakest_profit = row.min_month.profit if row.min_month else 0.0
        sections.append(
            f"- cost={row.cost_per_trade:.2f} bad={len(row.bad_months)} "
            f"weakest={weakest} {weakest_profit:.2f}"
        )
    sections.append("")

    return_report, return_audit = run_return_schedule(args.schedule_config, args.schedule)
    return_path = output_dir / f"{prefix}_return_proxy.md"
    write_report(return_path, return_report)
    if not return_audit.passed:
        errors.append("shared-return proxy target failed")
    sections.extend(
        [
            "## Shared Return Proxy",
            "",
            f"file={return_path}",
            (
                f"daily={return_audit.daily_trades:.2f} "
                f"bad={len(return_audit.bad_months)} pass={bool_text(return_audit.passed)}"
            ),
            "",
        ]
    )

    deploy_args = SimpleNamespace(
        schedule=args.schedule,
        schedule_config=args.schedule_config,
        strategy_config=args.strategy_config,
        generated_root=args.generated_root,
        profile_name=args.profile_name,
        guard_key_suffix=args.guard_key_suffix,
        mt5_home=args.mt5_home,
        mt5_data=args.mt5_data,
        compile=args.compile,
        start=False,
    )
    generated, installed = deploy(deploy_args)

    generated_errors, generated_report = audit_profile(
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
    generated_audit_path = output_dir / f"{prefix}_generated_profile_audit.md"
    installed_audit_path = output_dir / f"{prefix}_installed_profile_audit.md"
    write_report(generated_audit_path, generated_report)
    write_report(installed_audit_path, installed_report)
    errors.extend(generated_errors)
    errors.extend(installed_errors)
    sections.extend(
        [
            "## Profile",
            "",
            f"generated={generated}",
            f"installed={installed}",
            f"generated_audit={generated_audit_path}",
            f"installed_audit={installed_audit_path}",
            f"pass={bool_text(not generated_errors and not installed_errors)}",
            "",
        ]
    )

    if args.compile:
        sections.extend(["## Compile", "", "pass=true", "log_dir=temp/compile_win", ""])

    sections.extend(["## Result", "", f"pass={bool_text(not errors)}", ""])
    if errors:
        sections.append("### Errors")
        for error in errors:
            sections.append(f"- {error}")
        sections.append("")

    report = "\n".join(sections)
    if args.output:
        write_report(args.output, report)
    return PreflightResult(
        passed=not errors,
        report=report,
        generated_profile=generated,
        installed_profile=installed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run BTC portfolio Windows preflight without starting MT5.")
    parser.add_argument("--schedule", default="r186_r196_r117_r209_march_guard")
    parser.add_argument("--schedule-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--strategy-config", type=Path, default=DEFAULT_STRATEGY_CONFIG)
    parser.add_argument("--generated-root", type=Path, default=DEFAULT_GENERATED_ROOT)
    parser.add_argument("--profile-name", default="WaiTrade2_Portfolio_BTC_R209_DryRun")
    parser.add_argument("--guard-key-suffix", default="")
    parser.add_argument("--mt5-home", type=Path, default=DEFAULT_MT5_HOME)
    parser.add_argument("--mt5-data", type=Path, default=DEFAULT_MT5_DATA)
    parser.add_argument("--costs", default="0,0.05,0.1,0.25,0.5,1.0")
    parser.add_argument("--require-cost-pass", type=float)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-prefix", default="")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()

    result = run_preflight(args)
    print(result.report, end="")
    raise SystemExit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
