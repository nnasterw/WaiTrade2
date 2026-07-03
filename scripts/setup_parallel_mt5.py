#!/usr/bin/env python3
"""创建多个隔离MT5终端用于并行回测。共享只读数据(Bases/MQL5)，独立Tester缓存。"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
MASTER = TEMP / "mt5_tester_isolated"

# 必须独立复制的目录（回测会写入）
ISOLATE_DIRS = ["Tester"]
# junction共享的只读目录
SHARE_DIRS = ["Bases", "Config", "MQL5", "Data"]
# 必须复制的根目录文件（终端二进制+DLL）
COPY_FILES = [
    "terminal64.exe", "metaeditor64.exe", "metatester64.exe",
    "mt5clw.dat", "mtcommon.dll", "mtmanagersrv.dll",
]


def run_cmd(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kwargs)


def mklink_dir(link: Path, target: Path) -> bool:
    """创建Windows目录junction,失败返回False"""
    if link.exists():
        return True  # 已存在
    # 使用绝对路径
    link_abs = link.resolve() if link.exists() else link.absolute()
    target_abs = target.resolve()
    link_abs.parent.mkdir(parents=True, exist_ok=True)
    result = run_cmd(["cmd", "/c", f"mklink /J \"{link_abs}\" \"{target_abs}\""])
    return result.returncode == 0


def setup_terminal(name: str, master: Path = MASTER) -> Path:
    """创建一个新的隔离MT5终端"""
    target = TEMP / name
    if target.exists():
        print(f"  [skip] {name} 已存在")
        return target

    target.mkdir(parents=True, exist_ok=True)
    print(f"  创建 {name}...")

    # 1. 复制终端二进制文件
    for fname in COPY_FILES:
        src = master / fname
        if src.exists():
            shutil.copy2(src, target / fname)

    # 2. Junction共享只读目录
    for dname in SHARE_DIRS:
        src = master / dname
        if src.exists():
            mklink_dir(target / dname, src)
            print(f"    junction {dname} -> {src}")

    # 3. 创建独立的Tester目录
    tester_dir = target / "Tester"
    tester_dir.mkdir(exist_ok=True)
    (tester_dir / "cache").mkdir(exist_ok=True)
    (tester_dir / "logs").mkdir(exist_ok=True)
    (tester_dir / "Agent-127.0.0.1-3000").mkdir(exist_ok=True)

    print(f"  [done] {name} 创建完成")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="设置并行MT5回测终端")
    parser.add_argument("-n", "--count", type=int, default=2, help="额外终端数量(不包括主终端)")
    parser.add_argument("--master", type=Path, default=MASTER, help="主隔离终端路径")
    args = parser.parse_args()

    master = args.master
    if not (master / "terminal64.exe").exists():
        print(f"错误: 找不到主终端 {master}")
        print("请先创建主隔离MT5终端或使用 --master 指定路径")
        return 1

    print(f"主终端: {master}")

    terminals = ["mt5_tester_isolated"]  # 主终端已存在
    for i in range(1, args.count + 1):
        name = f"mt5_tester_isolated_{i}"
        setup_terminal(name, master)
        terminals.append(name)

    print(f"\n可用终端 ({len(terminals)}):")
    for t in terminals:
        print(f"  {TEMP / t}")

    # 验证每个终端都可用
    print("\n验证终端...")
    for t in terminals:
        exe = TEMP / t / "terminal64.exe"
        if exe.exists():
            print(f"  [OK] {t}")
        else:
            print(f"  [FAIL] {t}: 缺少 terminal64.exe")

    return 0


if __name__ == "__main__":
    sys.exit(main())
