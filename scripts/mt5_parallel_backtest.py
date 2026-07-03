#!/usr/bin/env python3
"""并行MT5回测管理器：在多个隔离终端上同时运行回测"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
ISOLATED_TERMINALS = [
    TEMP / "mt5_tester_isolated",
    TEMP / "mt5_tester_isolated_1",
    TEMP / "mt5_tester_isolated_2",
]


@dataclass
class BacktestTask:
    strategy: str
    symbol: str
    date_from: str
    date_to: str
    timeout: int = 1800

@dataclass
class BacktestResult:
    task: BacktestTask
    terminal: Path
    output: str = ""
    exit_code: int = -1
    elapsed_sec: float = 0.0
    success: bool = False


def terminal_available(terminal: Path) -> bool:
    """检查终端是否可用（未被占用）"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"(Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
         f"Where-Object {{ $_.Path -like '*{terminal.name}*' }}).Count"],
        capture_output=True, text=True, check=False,
    )
    try:
        count = int(result.stdout.strip() or "0")
        return count == 0
    except ValueError:
        return True


def kill_terminal(terminal: Path) -> None:
    """强制终止终端进程"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
         f"Where-Object {{ $_.Path -like '*{terminal.name}*' }} | "
         "Stop-Process -Force"],
        capture_output=True, text=True, check=False,
    )


def clear_terminal_cache(terminal: Path) -> None:
    """清理终端缓存和旧日志，防止Agent日志污染"""
    import shutil
    # 清理cache
    cache_dir = terminal / "Tester" / "cache"
    if cache_dir.exists():
        for item in cache_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
            except Exception:
                pass
    # 清理旧Agent日志（防止解析到上一次回测结果）
    for logs_dir in [
        terminal / "Tester" / "Agent-127.0.0.1-3000" / "logs",
        terminal / "Tester" / "logs",
    ]:
        if logs_dir.exists():
            for item in logs_dir.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                except Exception:
                    pass
    # 清理全局变量文件（防止跨回测状态污染）
    gvar_file = terminal / "Bases" / "gvariables.dat"
    if gvar_file.exists():
        try:
            gvar_file.unlink()
        except Exception:
            pass


def run_backtest_on_terminal(task: BacktestTask, terminal: Path) -> BacktestResult:
    """在指定终端上运行回测"""
    start = time.time()

    # 确保终端环境干净
    clear_terminal_cache(terminal)

    # 删除可能残留的.set文件（让回测脚本重新生成）
    set_file = terminal / "MQL5" / "Profiles" / "Tester" / f"{task.strategy}.set"
    if set_file.exists():
        set_file.unlink()

    env = os.environ.copy()
    env["MT5_HOME"] = str(terminal)
    env["MT5_DATA"] = str(terminal)
    env["MT5_PORTABLE"] = "1"

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "mt5_backtest_win.py"),
        "--strategy", task.strategy,
        "--symbol", task.symbol,
        "--from", task.date_from,
        "--to", task.date_to,
        "--timeout", str(task.timeout),
    ]

    try:
        result = subprocess.run(
            cmd, cwd=str(ROOT), env=env,
            capture_output=True, text=True, check=False,
            timeout=task.timeout + 120,  # 额外2分钟余量
        )
        elapsed = time.time() - start
        return BacktestResult(
            task=task, terminal=terminal,
            output=result.stdout, exit_code=result.returncode,
            elapsed_sec=elapsed, success=(result.returncode == 0),
        )
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        kill_terminal(terminal)
        return BacktestResult(
            task=task, terminal=terminal,
            output="TIMEOUT", exit_code=-1,
            elapsed_sec=elapsed, success=False,
        )
    except Exception as e:
        elapsed = time.time() - start
        return BacktestResult(
            task=task, terminal=terminal,
            output=str(e), exit_code=-1,
            elapsed_sec=elapsed, success=False,
        )


def run_parallel(tasks: list[BacktestTask]) -> list[BacktestResult]:
    """并行运行多个回测任务"""
    # 找到可用的终端
    available = [t for t in ISOLATED_TERMINALS
                 if (t / "terminal64.exe").exists()]

    if not available:
        print("错误: 没有可用的隔离MT5终端")
        return []

    # 杀死所有隔离终端的残留进程
    for term in available:
        kill_terminal(term)

    print(f"可用终端: {len(available)}")
    print(f"任务数: {len(tasks)}")
    print(f"并发数: {min(len(available), len(tasks))}")

    results: list[BacktestResult] = []
    lock = threading.Lock()
    terminal_queue = list(available)
    task_idx = [0]  # 用list实现闭包可变引用

    def worker(terminal: Path):
        while True:
            with lock:
                if task_idx[0] >= len(tasks):
                    return
                idx = task_idx[0]
                task_idx[0] += 1
                task = tasks[idx]

            print(f"\n[{terminal.name}] 开始: {task.strategy} ({task.date_from}~{task.date_to})")
            result = run_backtest_on_terminal(task, terminal)
            with lock:
                results.append(result)

            # 提取关键信息
            status = "OK" if result.success else "FAIL"
            summary = extract_summary(result)
            print(f"[{terminal.name}] {status} ({result.elapsed_sec:.0f}s): {summary}")

            # 清理缓存为下一个任务
            clear_terminal_cache(terminal)

    # 启动worker线程
    threads = []
    num_workers = min(len(available), len(tasks))
    for i in range(num_workers):
        t = threading.Thread(target=worker, args=(available[i],), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return results


def extract_summary(result: BacktestResult) -> str:
    """从回测输出中提取摘要"""
    lines = result.output.split('\n')
    for line in lines:
        if '结果:' in line or ('笔交易' in line and '胜率' in line):
            return line.strip()
    # 查找汇总行
    for i, line in enumerate(lines):
        if result.task.symbol in line and ('笔' in line or 'trades' in line.lower()):
            return line.strip()
    return f"exit={result.exit_code}"


def main() -> int:
    parser = argparse.ArgumentParser(description="并行MT5回测管理器")
    parser.add_argument("--tasks", type=Path, help="JSON任务文件路径")
    parser.add_argument("--strategy", action="append", dest="strategies", help="策略名(可重复)")
    parser.add_argument("--symbol", default="XAUUSDm", help="品种")
    parser.add_argument("--from", dest="date_from", help="起始日期 YYYY.MM.DD")
    parser.add_argument("--to", dest="date_to", help="结束日期 YYYY.MM.DD")
    parser.add_argument("--timeout", type=int, default=1800, help="每个任务超时秒数")
    parser.add_argument("--list-terminals", action="store_true", help="列出可用终端")
    args = parser.parse_args()

    if args.list_terminals:
        print("可用隔离终端:")
        for t in ISOLATED_TERMINALS:
            exe = t / "terminal64.exe"
            status = "READY" if exe.exists() else "MISSING"
            in_use = not terminal_available(t)
            print(f"  {t} [{status}] {'(占用中)' if in_use else '(空闲)'}")
        return 0

    tasks: list[BacktestTask] = []

    if args.tasks:
        with open(args.tasks, encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            tasks.append(BacktestTask(**item))
    elif args.strategies and args.date_from and args.date_to:
        for s in args.strategies:
            tasks.append(BacktestTask(
                strategy=s, symbol=args.symbol,
                date_from=args.date_from, date_to=args.date_to,
                timeout=args.timeout,
            ))
    else:
        parser.print_help()
        return 1

    if not tasks:
        print("没有回测任务")
        return 1

    start = time.time()
    results = run_parallel(tasks)
    total_elapsed = time.time() - start

    # 报告
    print(f"\n{'='*70}")
    print(f"并行回测完成: {len(results)}/{len(tasks)} 个任务, 总耗时 {total_elapsed:.0f}s")
    print(f"{'='*70}")
    print(f"{'策略':<30} {'终端':<25} {'状态':<6} {'耗时':>6} {'摘要'}")
    print(f"{'-'*70}")

    for r in sorted(results, key=lambda x: x.task.strategy):
        status = "WIN" if r.success else "FAIL"
        summary = extract_summary(r)
        print(f"{r.task.strategy:<30} {r.terminal.name:<25} {status:<6} {r.elapsed_sec:>5.0f}s {summary}")

    return 0 if all(r.success for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
