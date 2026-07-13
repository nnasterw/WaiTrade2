#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Loop 晋级验证执行器：30d smoke → 90d → 最多一个 720d → WFYS。"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results" / "backtest"
TEMP = ROOT / "temp"
SKILL_SCRIPTS = ROOT / ".agents" / "skills" / "wf-yhcl" / "scripts"

WORKLOAD_POINTS = {
    "smoke_30d": 1.0,
    "validate_90d": 1.0,
    "full_720d": 5.0,
    "wfys_extract": 0.5,
}
WORKLOAD_BUDGET_DEFAULT = 12.0
WORKLOAD_WARN_RATIO = 0.80
WORKLOAD_STOP_RATIO = 1.00


def estimate_stage_workload(stage):
    if stage == "full_720d":
        return WORKLOAD_POINTS["full_720d"] + WORKLOAD_POINTS["wfys_extract"]
    if stage in WORKLOAD_POINTS:
        return WORKLOAD_POINTS[stage]
    raise ValueError("未知回测阶段: " + str(stage))


def estimate_batch_workload(with_smoke=True, with_wfys=True, variants=1):
    total = variants * WORKLOAD_POINTS["validate_90d"] + WORKLOAD_POINTS["full_720d"]
    if with_smoke:
        total += variants * WORKLOAD_POINTS["smoke_30d"]
    if with_wfys:
        total += WORKLOAD_POINTS["wfys_extract"]
    return total


def check_workload_budget(used, budget, pending=0.0):
    if budget <= 0:
        return "ok", 0.0
    ratio = (used + pending) / budget
    if ratio >= WORKLOAD_STOP_RATIO:
        return "stop", ratio
    if ratio >= WORKLOAD_WARN_RATIO:
        return "warn", ratio
    return "ok", ratio


def clear_mt5_cache(terminal_path):
    """清理目标 terminal 的 MT5 cache，不触碰其他实例。"""
    tst_files = list(Path(terminal_path).rglob("*.tst"))
    cache_dirs = [Path(terminal_path) / "Tester" / "cache", Path(terminal_path) / "Tester" / "Cache"]
    cleared = 0
    for item in tst_files:
        try:
            item.unlink()
            cleared += 1
        except OSError:
            pass
    for directory in cache_dirs:
        if directory.exists():
            shutil.rmtree(str(directory), ignore_errors=True)
            directory.mkdir(exist_ok=True)
    if cleared:
        print("    [cache] 清理 " + str(cleared) + " .tst")
    return cleared


def run_short(cmd, timeout=120, env=None):
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, timeout=timeout, env=env,
    )


def prepare_strategy(strategy):
    """回测前强制执行一致性检查、生成 .set 和 Iron Rule strict。"""
    consistency = run_short([
        sys.executable, str(ROOT / "scripts" / "check_strategy_consistency.py"), strategy,
    ], timeout=120)
    if consistency.returncode != 0 or "ERROR" in consistency.stdout:
        return False, "策略一致性检查失败: " + (consistency.stdout + consistency.stderr)[-500:]

    set_path = ROOT / "mql5" / "Presets" / (strategy + ".set")
    generated = run_short([
        sys.executable, str(ROOT / "scripts" / "yaml_to_set.py"), strategy,
        "-o", str(set_path),
    ], timeout=120)
    if generated.returncode != 0 or not set_path.exists():
        return False, ".set 生成失败: " + (generated.stdout + generated.stderr)[-500:]

    iron = run_short([
        sys.executable, str(SKILL_SCRIPTS / "iron_rule_check.py"), str(set_path),
        "--strict", "--summary",
    ], timeout=120)
    if iron.returncode != 0:
        return False, "Iron Rule strict 失败: " + (iron.stdout + iron.stderr)[-500:]
    return True, str(set_path.resolve())


def parse_backtest_stdout(stdout):
    balance = None
    trades = None
    for line in stdout.splitlines():
        if "余额" in line and "$" in line:
            try:
                balance = float(line.rsplit("$", 1)[1].split()[0].replace(",", ""))
            except (ValueError, IndexError):
                pass
        if "笔交易" in line:
            for part in line.split():
                if part.isdigit():
                    trades = int(part)
                    break
    return balance, trades


def find_report(strategy, started_at):
    candidates = [
        item for item in RESULTS.glob(strategy + "_*.txt")
        if item.stat().st_mtime >= started_at - 2
    ]
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def run_mt5_test(strategy, terminal_path, env, stage, timeout=1200):
    """执行 MT5 Model 4 回测；Period 由策略配置自动推导，禁止人工覆盖。"""
    if stage == "smoke_30d":
        range_args = ["--days", "30"]
        timeout = min(timeout, 360)
    elif stage == "validate_90d":
        range_args = ["--days", "90"]
        timeout = min(timeout, 600)
    elif stage == "full_720d":
        range_args = ["--from", "2024.06.01", "--to", "2026.05.31"]
    else:
        raise ValueError("未知阶段: " + stage)

    print("  [" + stage + "] " + strategy + " ...")
    started_at = time.time()
    cmd = [
        sys.executable, str(ROOT / "scripts" / "mt5_backtest_win.py"),
        "--strategy", strategy, "--symbol", "BTCUSDm",
    ] + range_args + [
        "--model", "4", "--deposit", "200", "--timeout", str(timeout),
    ]
    result = run_short(cmd, timeout=timeout + 60, env=env)
    elapsed = time.time() - started_at
    balance, trades = parse_backtest_stdout(result.stdout)
    report = find_report(strategy, started_at)
    success = result.returncode == 0 and report is not None and trades not in (None, 0)
    status = "PASS" if success else "FAIL"
    print("    [" + status + "] " + str(round(elapsed, 1)) + "s, balance=" + str(balance) + ", trades=" + str(trades))
    return {
        "stage": stage,
        "success": success,
        "returncode": result.returncode,
        "elapsed_sec": round(elapsed, 3),
        "balance": balance,
        "trades": trades,
        "report": str(report.resolve()) if report else None,
        "error_tail": (result.stderr or result.stdout)[-500:] if not success else "",
    }


def extract_trades(strategy, terminal_path, result_path):
    """从指定 720d 报告生成逐笔、24m 和 WFYS，返回精确路径。"""
    log_path = Path(terminal_path) / "Tester" / "Agent-127.0.0.1-3000" / "logs" / (datetime.now().strftime("%Y%m%d") + ".log")
    if not log_path.exists():
        logs_dir = log_path.parent
        logs = sorted(logs_dir.glob("*.log"), key=lambda item: item.stat().st_mtime, reverse=True) if logs_dir.exists() else []
        log_path = logs[0] if logs else log_path
    result_path = Path(result_path)
    if not log_path.exists() or not result_path.exists():
        return {"success": False, "reason": "报告或 MT5 日志缺失"}

    digest = run_short([
        sys.executable, str(ROOT / "scripts" / "backtest_digest.py"),
        "--report", str(result_path), "--log", str(log_path), "--export-csv", "--brief",
    ], timeout=120)
    trades_csv = result_path.with_suffix(".trades.csv")
    if digest.returncode != 0 or not trades_csv.exists() or trades_csv.stat().st_size < 100:
        return {"success": False, "reason": "trades.csv 生成失败"}

    rebuilt = run_short([
        sys.executable, str(ROOT / "scripts" / "rebuild_24m.py"), str(trades_csv), "200",
    ], timeout=60)
    monthly_csv = trades_csv.with_name(trades_csv.stem + "_closetime_24m.csv")
    if rebuilt.returncode != 0 or not monthly_csv.exists():
        return {"success": False, "reason": "24m CSV 生成失败"}

    wfys_json = RESULTS / (strategy + "_wfys_v22_" + datetime.now().strftime("%Y%m%d") + ".json")
    wfys = run_short([
        sys.executable, str(ROOT / "scripts" / "wfys_score.py"),
        "--monthly-csv", str(monthly_csv), "--continuous-report", str(result_path),
        "--trades-csv", str(trades_csv), "--spec", "btc", "--deposit", "200",
        "--json-out", str(wfys_json),
    ], timeout=60)
    return {
        "success": wfys.returncode == 0 and wfys_json.exists(),
        "original_report": str(result_path.resolve()),
        "trades_csv": str(trades_csv.resolve()),
        "monthly_csv": str(monthly_csv.resolve()),
        "wfys_json": str(wfys_json.resolve()) if wfys_json.exists() else None,
        "log_path": str(log_path.resolve()),
    }


def choose_promoted(results):
    passed = [item for item in results if (item.get("validate_90d") or {}).get("success")]
    if not passed:
        return None
    return max(passed, key=lambda item: ((item["validate_90d"].get("balance") or float("-inf")), item["strategy"]))


def build_parser():
    parser = argparse.ArgumentParser(description="Loop 30d→90d→单一720d 晋级验证")
    parser.add_argument("--variants", required=True, help="逗号分隔策略名，最多 3 个")
    parser.add_argument("--terminal", default="mt5_portable_btc_trend111")
    parser.add_argument("--time-limit", type=int, default=30)
    parser.add_argument("--smoke", action="store_true", default=True)
    parser.add_argument("--no-smoke", dest="smoke", action="store_false")
    parser.add_argument("--workload-budget", type=float, default=WORKLOAD_BUDGET_DEFAULT)
    parser.add_argument("--token-budget", dest="legacy_token_budget", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--skip-polluted", action="store_true")
    parser.add_argument("--json-out", help="结构化批次结果路径")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.legacy_token_budget is not None:
        print("[WARN] --token-budget 已废弃，仅按回测工作量点数解释")
        args.workload_budget = args.legacy_token_budget
    variants = [item.strip() for item in args.variants.split(",") if item.strip()]
    if not variants or len(variants) > 3:
        print("[FAIL] 每 Loop 必须包含 1-3 个变体")
        return 2
    terminal_path = TEMP / args.terminal
    if not terminal_path.exists():
        print("[FAIL] terminal 不存在: " + str(terminal_path))
        return 1

    env = dict(os.environ)
    env.update({"MT5_HOME": str(terminal_path), "MT5_PORTABLE": "1", "MT5_REQUIRE_ADMIN": "0"})
    started = time.time()
    used_workload = 0.0
    output = {
        "schema_version": 1,
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "terminal": str(terminal_path.resolve()),
        "variants": [],
        "promoted": None,
        "workload_budget": args.workload_budget,
        "workload_used": 0.0,
    }

    for strategy in variants:
        prepared, detail = prepare_strategy(strategy)
        item = {"strategy": strategy, "prepared": prepared, "prepare_detail": detail}
        output["variants"].append(item)
        if not prepared:
            item["status"] = "repair"
            continue
        clear_mt5_cache(terminal_path)
        if args.smoke:
            if check_workload_budget(used_workload, args.workload_budget, WORKLOAD_POINTS["smoke_30d"])[0] == "stop":
                item["status"] = "workload_limit"
                continue
            item["smoke_30d"] = run_mt5_test(strategy, terminal_path, env, "smoke_30d", timeout=360)
            used_workload += WORKLOAD_POINTS["smoke_30d"]
            if not item["smoke_30d"]["success"]:
                item["status"] = "smoke_fail"
                continue
        if (time.time() - started) / 60 > args.time_limit:
            item["status"] = "time_limit"
            continue
        if check_workload_budget(used_workload, args.workload_budget, WORKLOAD_POINTS["validate_90d"])[0] == "stop":
            item["status"] = "workload_limit"
            continue
        item["validate_90d"] = run_mt5_test(strategy, terminal_path, env, "validate_90d", timeout=600)
        used_workload += WORKLOAD_POINTS["validate_90d"]
        item["status"] = "90d_pass" if item["validate_90d"]["success"] else "90d_fail"
        clear_mt5_cache(terminal_path)

    promoted = choose_promoted(output["variants"])
    if promoted:
        pending = WORKLOAD_POINTS["full_720d"] + WORKLOAD_POINTS["wfys_extract"]
        if check_workload_budget(used_workload, args.workload_budget, pending)[0] != "stop":
            strategy = promoted["strategy"]
            clear_mt5_cache(terminal_path)
            promoted["full_720d"] = run_mt5_test(strategy, terminal_path, env, "full_720d", timeout=1200)
            used_workload += WORKLOAD_POINTS["full_720d"]
            if promoted["full_720d"]["success"]:
                promoted["artifacts"] = extract_trades(strategy, terminal_path, promoted["full_720d"]["report"])
                used_workload += WORKLOAD_POINTS["wfys_extract"]
                promoted["status"] = "completed" if promoted["artifacts"].get("success") else "wfys_fail"
            else:
                promoted["status"] = "720d_fail"
            output["promoted"] = strategy
        else:
            promoted["status"] = "workload_limit_before_720d"

    output["workload_used"] = round(used_workload, 2)
    output["elapsed_min"] = round((time.time() - started) / 60, 3)
    output["completed_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    if args.json_out:
        target = Path(args.json_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Summary: variants=" + str(len(variants)) + ", promoted=" + str(output["promoted"]) + ", workload=" + str(output["workload_used"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
