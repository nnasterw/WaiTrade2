#!/usr/bin/env python3
"""Windows MT5 Strategy Tester runner scoped to a dedicated portable terminal."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TESTER_HOME = ROOT / "temp" / "mt5_tester_isolated"
LIVE_PORTABLE_ROOT = ROOT / "temp" / "mt5_portable_v11a"
LIVE_STATUS_SCRIPT = ROOT / "scripts" / "portfolio_live_status.py"
LIVE_STATUS_DIR = ROOT / "results" / "live"


def validate_tester_home(path: Path) -> Path:
    resolved = path.resolve()
    live_root = LIVE_PORTABLE_ROOT.resolve()
    if resolved == live_root or live_root in resolved.parents or resolved in live_root.parents:
        raise SystemExit(f"refusing to use live portable directory as tester home: {resolved}")
    terminal = resolved / "terminal64.exe"
    if not terminal.exists():
        raise SystemExit(
            f"missing isolated terminal: {terminal}\n"
            "Create or copy a dedicated portable MT5 terminal before running isolated backtests."
        )
    return resolved


def run_live_guard(stage: str) -> None:
    LIVE_STATUS_DIR.mkdir(parents=True, exist_ok=True)
    output = LIVE_STATUS_DIR / f"v11a_live_status_{stage}_isolated_backtest.md"
    cmd = [
        sys.executable,
        str(LIVE_STATUS_SCRIPT),
        "--since-hours",
        "24",
        "--max-heartbeat-age-min",
        "75",
        "--output",
        str(output),
    ]
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    text = f"{result.stdout}\n{result.stderr}"
    if result.returncode != 0 or "streams=7 pass=true" not in text:
        raise SystemExit(
            f"live guard failed at {stage}; refusing isolated backtest. "
            f"See {output}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run mt5_backtest_win.py with an isolated portable MT5 home."
    )
    parser.add_argument(
        "--tester-home",
        type=Path,
        default=DEFAULT_TESTER_HOME,
        help="Dedicated portable MT5 directory used only for Strategy Tester.",
    )
    parser.add_argument(
        "backtest_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed after -- to scripts/mt5_backtest_win.py.",
    )
    args = parser.parse_args(argv)

    passthrough = list(args.backtest_args)
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]
    if not passthrough:
        raise SystemExit("missing backtest arguments; pass them after --")

    tester_home = validate_tester_home(args.tester_home)
    env = os.environ.copy()
    env["MT5_HOME"] = str(tester_home)
    env["MT5_DATA"] = str(tester_home)
    env["MT5_PORTABLE"] = "1"

    cmd = [sys.executable, str(ROOT / "scripts" / "mt5_backtest_win.py"), *passthrough]
    run_live_guard("before")
    rc = 1
    try:
        rc = subprocess.run(cmd, cwd=str(ROOT), env=env, check=False).returncode
    finally:
        run_live_guard("after")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
