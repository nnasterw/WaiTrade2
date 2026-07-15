#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MQL5_SRC = ROOT / "mql5"
MT5_HOME = Path(os.environ.get("MT5_HOME", r"C:\Program Files\MetaTrader 5"))
MT5_DATA = Path(
    os.environ.get(
        "MT5_DATA",
        os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075"),
    )
)

SUCCESS_RE = re.compile(r"Result:\s*0 errors?,\s*(\d+) warnings?", re.IGNORECASE)
ERROR_RE = re.compile(r"Result:\s*(\d+) errors?", re.IGNORECASE)


@dataclass
class CompileResult:
    source: Path
    log: Path
    success: bool
    warnings: int = 0
    returncode: int | None = None
    message: str = ""


def copy_tree_files(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    shutil.copytree(src, dst, dirs_exist_ok=True)


def sync_mql5_files(mt5_data: Path = MT5_DATA) -> None:
    copy_tree_files(MQL5_SRC / "Experts", mt5_data / "MQL5" / "Experts")
    copy_tree_files(MQL5_SRC / "Include", mt5_data / "MQL5" / "Include")
    copy_tree_files(MQL5_SRC / "Scripts", mt5_data / "MQL5" / "Scripts")


def read_text_guess(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16-le", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_compile_log(source: Path, log: Path, returncode: int | None = None) -> CompileResult:
    if not log.exists():
        return CompileResult(source=source, log=log, success=False, returncode=returncode, message="compile log missing")

    content = read_text_guess(log)
    success_match = SUCCESS_RE.search(content)
    if success_match:
        return CompileResult(
            source=source,
            log=log,
            success=True,
            warnings=int(success_match.group(1)),
            returncode=returncode,
            message="0 errors",
        )

    error_match = ERROR_RE.search(content)
    if error_match:
        return CompileResult(
            source=source,
            log=log,
            success=False,
            returncode=returncode,
            message=f"{error_match.group(1)} errors",
        )

    return CompileResult(
        source=source,
        log=log,
        success=False,
        returncode=returncode,
        message="could not find compile Result line",
    )


def compile_command(metaeditor: Path, source: Path, log: Path) -> list[str]:
    return [str(metaeditor), "/portable", f"/compile:{source}", f"/log:{log}"]


def compile_file(metaeditor: Path, source: Path, log_dir: Path) -> CompileResult:
    if not metaeditor.exists():
        raise SystemExit(f"missing MetaEditor: {metaeditor}")
    if not source.exists():
        raise SystemExit(f"missing MQL source: {source}")

    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f"{source.stem}.compile.log"
    log.unlink(missing_ok=True)

    result = subprocess.run(
        compile_command(metaeditor, source, log),
        check=False,
        capture_output=True,
        text=True,
    )
    return parse_compile_log(source, log, result.returncode)


def compile_portfolio_sources(
    mt5_home: Path = MT5_HOME,
    mt5_data: Path = MT5_DATA,
    log_dir: Path | None = None,
) -> list[CompileResult]:
    sync_mql5_files(mt5_data)
    metaeditor = mt5_home / "MetaEditor64.exe"
    logs = log_dir or (ROOT / "temp" / "compile_win")
    sources = [
        mt5_data / "MQL5" / "Experts" / "WaiTrade2" / "WaiTrade_OB.mq5",
        mt5_data / "MQL5" / "Experts" / "WaiTrade2" / "PortfolioSetup.mq5",
        mt5_data / "MQL5" / "Experts" / "WaiTrade3" / "WaiTrade_OB_SMC.mq5",
        mt5_data / "MQL5" / "Experts" / "WaiTrade3" / "WaiTrade_OB_BV1_Slim.mq5",
        mt5_data / "MQL5" / "Scripts" / "WaiTrade2" / "ClearSharedMonthlyGuard.mq5",
    ]
    results = [compile_file(metaeditor, source, logs) for source in sources]
    for result in results:
        if not result.success:
            continue
        try:
            rel = result.source.relative_to(mt5_data / "MQL5")
        except ValueError:
            continue
        compiled = result.source.with_suffix(".ex5")
        target = MQL5_SRC / rel.with_suffix(".ex5")
        if compiled.exists() and (target.exists() or result.source.name == "WaiTrade_OB_BV1_Slim.mq5"):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(compiled, target)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Windows native MetaEditor compile with log validation.")
    parser.add_argument("--mt5-home", type=Path, default=MT5_HOME)
    parser.add_argument("--mt5-data", type=Path, default=MT5_DATA)
    parser.add_argument("--log-dir", type=Path, default=ROOT / "temp" / "compile_win")
    args = parser.parse_args()

    results = compile_portfolio_sources(args.mt5_home, args.mt5_data, args.log_dir)
    ok = True
    for result in results:
        ok = ok and result.success
        print(
            f"{result.source.name}: success={str(result.success).lower()} "
            f"warnings={result.warnings} returncode={result.returncode} log={result.log} {result.message}"
        )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
