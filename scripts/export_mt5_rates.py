#!/usr/bin/env python3
"""Export MT5 rates through a tiny research EA.

This is data export, not a strategy backtest. It uses Strategy Tester only as
the trusted MT5 data/runtime host.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Union

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MT5_HOME = ROOT / "temp" / "mt5_portable_bt"
MT5_HOME = Path(os.environ.get("MT5_HOME", str(DEFAULT_MT5_HOME)))
MT5_DATA = Path(os.environ.get("MT5_DATA", str(MT5_HOME)))
COMMON_FILES = Path(os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal\Common\Files"))


def ps_quote(value: Union[Path, str]) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def kill_local_mt5() -> None:
    root = str(MT5_HOME.resolve()).rstrip("\\") + "\\"
    cmd = (
        f"$root={ps_quote(root)}; "
        "Get-CimInstance Win32_Process -Filter \"name='terminal64.exe' or name='metatester64.exe'\" | "
        "Where-Object { $_.ExecutablePath -and "
        "$_.ExecutablePath.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase) } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)
    time.sleep(2)


def write_set(path: Path, symbol: str, date_from: str, date_to: str, tf_list: str, prefix: str) -> None:
    text = "\n".join(
        [
            f"InpExportSymbol={symbol}",
            f"InpFrom={date_from} 00:00",
            f"InpTo={date_to} 23:59",
            f"InpTFList={tf_list}",
            f"InpPrefix={prefix}",
            "",
        ]
    )
    path.write_text(text, encoding="utf-16")


def write_ini(path: Path, set_name: str, symbol: str, date_from: str, date_to: str, report_name: str) -> None:
    text = f"""[Common]
ProxyEnable=0

[Tester]
Expert=Research\\ExportRatesCSV
ExpertParameters={set_name}
Symbol={symbol}
Period=M1
Model=4
Optimization=0
FromDate={date_from}
ToDate={date_to}
Deposit=200
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report={report_name}
"""
    path.write_text(text, encoding="utf-8")


def run_terminal(ini_path: Path, timeout_sec: int) -> bool:
    terminal = MT5_HOME / "terminal64.exe"
    if not terminal.exists():
        raise SystemExit(f"missing terminal: {terminal}")
    args = [str(terminal), "/portable", f"/config:{ini_path.name}"]
    proc = subprocess.Popen(
        args,
        cwd=str(MT5_HOME),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    start = time.time()
    while proc.poll() is None:
        if time.time() - start > timeout_sec:
            proc.kill()
            proc.wait()
            return False
        time.sleep(1)
    return proc.returncode == 0


def collect_exports(prefix: str, out_dir: Path) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    found = []  # type: List[Path]
    for root in (COMMON_FILES, MT5_DATA / "MQL5" / "Files"):
        if not root.exists():
            continue
        for src in root.glob(prefix + "_*.csv"):
            dst = out_dir / src.name
            shutil.copy2(src, dst)
            found.append(dst)
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export MT5 OHLC CSV via Research\\ExportRatesCSV EA.")
    parser.add_argument("--symbol", default="XAUUSDm")
    parser.add_argument("--from", dest="date_from", default="2024.01.01")
    parser.add_argument("--to", dest="date_to", default="2026.06.18")
    parser.add_argument("--tf-list", default="1440,240,60,15,5")
    parser.add_argument("--prefix", default="waitrade_rates")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results" / "research" / "rates")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    profiles = MT5_DATA / "MQL5" / "Profiles" / "Tester"
    profiles.mkdir(parents=True, exist_ok=True)
    (MT5_DATA / "Tester").mkdir(parents=True, exist_ok=True)

    set_name = "research_export_rates.set"
    write_set(profiles / set_name, args.symbol, args.date_from, args.date_to, args.tf_list, args.prefix)
    ini = MT5_HOME / "export_rates.ini"
    write_ini(ini, set_name, args.symbol, args.date_from, args.date_to, args.prefix + "_report")

    kill_local_mt5()
    ok = run_terminal(ini, args.timeout)
    files = collect_exports(args.prefix, args.out_dir)
    for path in files:
        print(path)
    if not ok:
        print("MT5 export run failed or timed out", file=sys.stderr)
        return 1
    if not files:
        print("no exported CSV files found", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
