#!/usr/bin/env python3
"""_loop_preflight.py - Loop 启动前环境检查"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path("D:/Code/codexProject/WaiTrade2")
TEMP = ROOT / "temp"
BACKUP = TEMP / "loop_engineering_baseline_2026-07-07"
DEFAULT_TERMINAL = "mt5_portable_btc_trend111"


def check_backup():
    print("[1/6] Backup check ...")
    if not BACKUP.exists():
        print("  [FAIL] 备份目录不存在")
        return False
    yaml_bak = BACKUP / "strategies.yaml"
    if not yaml_bak.exists():
        print("  [FAIL] 备份 yaml 不存在")
        return False
    size = yaml_bak.stat().st_size
    print("  [OK] 备份 yaml: " + str(size) + " bytes")
    return True


def check_terminal(terminal_name):
    print("[2/6] Terminal check: " + terminal_name)
    term = TEMP / terminal_name
    if not term.exists():
        print("  [FAIL] terminal 不存在")
        return False
    exe = term / "terminal64.exe"
    if not exe.exists():
        print("  [FAIL] 缺少 terminal64.exe")
        return False
    try:
        ps_cmd = "(Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*" + terminal_name + "*' }).Count"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, check=False, timeout=10
        )
        count = int(result.stdout.strip() or "0")
        if count > 0:
            print("  [FAIL] terminal 被占用: " + str(count) + " 个进程")
            return False
    except Exception as e:
        print("  [WARN] 进程检查失败: " + str(e))
    ex5 = term / "MQL5" / "Experts" / "WaiTrade2" / "WaiTrade_OB.ex5"
    if not ex5.exists():
        print("  [FAIL] 缺少 WaiTrade_OB.ex5")
        return False
    print("  [OK] terminal 空闲, ex5 存在")
    return True


def check_cache(terminal_name, cleanup=False):
    print("[3/6] MT5 cache check (cleanup=" + str(cleanup) + ")")
    term = TEMP / terminal_name
    cache_dirs = [term / "Tester" / "cache", term / "Tester" / "Cache"]
    tst_files = list(term.rglob("*.tst"))
    total_size = sum(f.stat().st_size for f in tst_files)
    if total_size > 0:
        print("  [WARN] 发现 cache: " + str(len(tst_files)) + " .tst, " + str(total_size/1024) + " KB")
        if cleanup:
            for f in tst_files:
                try: f.unlink()
                except: pass
            for d in cache_dirs:
                if d.exists():
                    shutil.rmtree(d, ignore_errors=True)
                    d.mkdir(exist_ok=True)
            print("  [OK] cache 已清理")
            return True
        print("        用 --cleanup-cache 自动清理")
        return False
    print("  [OK] cache 干净")
    return True


def check_baseline(terminal_name):
    print("[4/6] Baseline regression check ...")
    term = TEMP / terminal_name
    set_target = term / "MQL5" / "Profiles" / "Tester" / "v11-btc1-trend218.set"
    if not set_target.exists():
        print("  [WARN] trend218 .set 不在 terminal, 可手动复制")
        return True
    print("  [OK] trend218 .set 存在")
    return True


def check_user_procs():
    print("[5/6] User process check ...")
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | Select-Object Id, Path | ConvertTo-Json -Compress"],
            capture_output=True, text=True, check=False, timeout=10
        )
        import json
        procs = []
        if result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict): procs = [data]
            elif isinstance(data, list): procs = data
        user_procs = [p for p in procs if "mt5_portable_bt" in (p.get("Path") or "")]
        if user_procs:
            print("  [INFO] " + str(len(user_procs)) + " 个用户进程 (不阻塞)")
        else:
            print("  [OK] 无其他 MT5 进程")
    except Exception as e:
        print("  [WARN] 检查异常: " + str(e))
    return True


def check_port():
    print("[6/6] Port 3000 check ...")
    try:
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, check=False, timeout=10)
        listening = [l for l in result.stdout.splitlines() if "LISTENING" in l and ":3000" in l]
        if listening:
            for l in listening:
                print("  [INFO] 端口 3000: " + l.strip())
        else:
            print("  [OK] 端口 3000 空闲")
    except Exception as e:
        print("  [WARN] 端口检查失败: " + str(e))
    return True


def main():
    parser = argparse.ArgumentParser(description="Loop 启动前环境检查")
    parser.add_argument("--terminal", default=DEFAULT_TERMINAL)
    parser.add_argument("--cleanup-cache", action="store_true")
    parser.add_argument("--skip-baseline", action="store_true")
    args = parser.parse_args()
    print("=" * 60)
    print("Loop Preflight Check @ " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("Terminal: " + args.terminal)
    print("=" * 60)
    results = []
    results.append(("Backup", check_backup()))
    results.append(("Terminal", check_terminal(args.terminal)))
    results.append(("MT5 cache", check_cache(args.terminal, cleanup=args.cleanup_cache)))
    if not args.skip_baseline:
        results.append(("Baseline", check_baseline(args.terminal)))
    results.append(("User processes", check_user_procs()))
    results.append(("Port 3000", check_port()))
    print()
    print("=" * 60)
    print("Summary:")
    failed = [name for name, ok in results if not ok]
    if failed:
        print("  [FAIL] " + str(len(failed)) + " 项不通过: " + ", ".join(failed))
        return 1
    print("  [OK] 全部 " + str(len(results)) + " 项通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
