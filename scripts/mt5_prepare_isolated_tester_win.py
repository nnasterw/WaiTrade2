#!/usr/bin/env python3
"""Prepare a dedicated portable MT5 directory for isolated Strategy Tester runs."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from mt5_backtest_isolated_win import DEFAULT_TESTER_HOME, LIVE_PORTABLE_ROOTS, validate_tester_home


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_HOME = ROOT / "temp" / "mt5_portable"


def _path_inside(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    resolved_root = root.resolve()
    return resolved == resolved_root or resolved_root in resolved.parents


def reject_live_path(path: Path) -> Path:
    resolved = path.resolve()
    for root in LIVE_PORTABLE_ROOTS:
        live_root = root.resolve()
        if resolved == live_root or live_root in resolved.parents or resolved in live_root.parents:
            raise SystemExit(f"refusing to use live portable path: {resolved}")
    return resolved


def terminal_processes_under(root: Path) -> list[str]:
    resolved = str(root.resolve())
    command = r"""
$root = [System.IO.Path]::GetFullPath($env:WAITRADE_MT5_PROCESS_ROOT)
$root = $root.TrimEnd('\', '/')
$rootWithSep = $root + [System.IO.Path]::DirectorySeparatorChar
Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue |
  Where-Object {
    $_.Path -and
    (
      ([System.IO.Path]::GetFullPath($_.Path)).Equals(
        $root,
        [System.StringComparison]::OrdinalIgnoreCase
      ) -or
      ([System.IO.Path]::GetFullPath($_.Path)).StartsWith(
        $rootWithSep,
        [System.StringComparison]::OrdinalIgnoreCase
      )
    )
  } |
  ForEach-Object { "$($_.Id)|$($_.ProcessName)|$($_.Path)" }
"""
    env = {"WAITRADE_MT5_PROCESS_ROOT": resolved}
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def validate_source_home(path: Path) -> Path:
    source = reject_live_path(path)
    terminal = source / "terminal64.exe"
    metaeditor = source / "metaeditor64.exe"
    if not terminal.exists():
        raise SystemExit(f"missing source terminal: {terminal}")
    if not metaeditor.exists():
        raise SystemExit(f"missing source MetaEditor: {metaeditor}")
    running = terminal_processes_under(source)
    if running:
        raise SystemExit(f"source portable is running; refusing to copy: {running}")
    return source


def validate_destination(path: Path, source: Path) -> Path:
    dest = reject_live_path(path)
    if _path_inside(dest, source) or _path_inside(source, dest):
        raise SystemExit(f"source and tester home must be separate directories: {source} -> {dest}")
    if dest.exists():
        validate_tester_home(dest)
        running = terminal_processes_under(dest)
        if running:
            raise SystemExit(f"tester portable is running; refusing to replace: {running}")
    return dest


def copy_portable(source: Path, dest: Path, force: bool) -> None:
    if dest.exists():
        if not force:
            raise SystemExit(f"tester home already exists; pass --force to replace: {dest}")
        shutil.rmtree(dest)
    shutil.copytree(source, dest)
    validate_tester_home(dest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare an isolated portable MT5 tester directory.")
    parser.add_argument("--source-home", type=Path, default=DEFAULT_SOURCE_HOME)
    parser.add_argument("--tester-home", type=Path, default=DEFAULT_TESTER_HOME)
    parser.add_argument("--force", action="store_true", help="Replace existing tester home after safety checks.")
    args = parser.parse_args(argv)

    source = validate_source_home(args.source_home)
    dest = validate_destination(args.tester_home, source)
    copy_portable(source, dest, force=args.force)
    print(f"prepared isolated tester: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
