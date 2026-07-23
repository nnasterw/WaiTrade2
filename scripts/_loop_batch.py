#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Loop 晋级验证执行器：30d smoke → 90d → 最多一个 720d → WFYS。"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

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


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_ex5_provenance(strategy, terminal_path):
    """确认运行时 .ex5 与仓库编译物一致，且不早于所有相关源码。"""
    config_path = ROOT / "config" / "strategies.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    strategy_cfg = config.get(strategy)
    if not isinstance(strategy_cfg, dict):
        return False, "策略不存在，无法核验 .ex5 来源: " + strategy
    defaults = config.get("defaults") or {}
    expert = str(strategy_cfg.get("expert", defaults.get("expert", r"WaiTrade2\WaiTrade_OB")))
    relative = Path(*expert.replace("/", chr(92)).split(chr(92))).with_suffix(".ex5")
    project_ex5 = ROOT / "mql5" / "Experts" / relative
    runtime_ex5 = Path(terminal_path) / "MQL5" / "Experts" / relative
    missing = [str(item) for item in (project_ex5, runtime_ex5) if not item.exists()]
    if missing:
        return False, ".ex5 缺失: " + ", ".join(missing)

    expert_family = relative.parts[0] if relative.parts else ""
    source_paths = [project_ex5.with_suffix(".mq5")]
    include_roots = [ROOT / "mql5" / "Include" / "WaiTrade2"]
    if expert_family == "WaiTrade3":
        include_roots.append(ROOT / "mql5" / "Include" / "WaiTrade3")
    for include_root in include_roots:
        if include_root.exists():
            source_paths.extend(include_root.rglob("*.mqh"))
    existing_sources = [item for item in source_paths if item.exists()]
    if not existing_sources:
        return False, "EA 源码缺失: " + str(project_ex5.with_suffix(".mq5"))
    newest_source = max(existing_sources, key=lambda item: item.stat().st_mtime)
    if project_ex5.stat().st_mtime < newest_source.stat().st_mtime:
        return False, ".ex5 早于源码，必须重新编译: " + str(newest_source)

    project_hash = _sha256(project_ex5)
    runtime_hash = _sha256(runtime_ex5)
    if project_hash != runtime_hash:
        return False, ".ex5 来源不一致: project=" + project_hash[:12] + " runtime=" + runtime_hash[:12]
    return True, "expert=" + expert + " sha256=" + project_hash


def prepare_strategy(strategy, terminal_path):
    """回测前强制执行一致性检查、生成 .set 和 Iron Rule strict。"""
    consistency = run_short([
        sys.executable, str(ROOT / "scripts" / "check_strategy_consistency.py"), strategy,
    ], timeout=120)
    if consistency.returncode != 0:
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
    provenance_ok, provenance_detail = verify_ex5_provenance(strategy, terminal_path)
    if not provenance_ok:
        return False, "EA 来源检查失败: " + provenance_detail
    return True, str(set_path.resolve()) + "; " + provenance_detail


def parse_backtest_stdout(stdout):
    balance = None
    trades = None
    trade_match = re.search(r"(\d+)\s*笔交易", stdout)
    if trade_match:
        trades = int(trade_match.group(1))
    for line in stdout.splitlines():
        if "余额" in line and "$" in line:
            try:
                balance = float(line.rsplit("$", 1)[1].split()[0].replace(",", ""))
            except (ValueError, IndexError):
                pass
        if trades is None and "笔交易" in line:
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


def get_strategy_model(strategy):
    """从 strategies.yaml 读取策略的 model 设置，默认 4 (Real ticks)."""
    import yaml
    yaml_path = ROOT / "config" / "strategies.yaml"
    if not yaml_path.exists():
        return 4
    with yaml_path.open('r', encoding='utf-8') as handle:
        docs = yaml.safe_load(handle) or {}
    cfg = docs.get(strategy) or {}
    return str(cfg.get('model', 4))


def run_mt5_test(strategy, terminal_path, env, stage, timeout=1200):
    """执行 MT5 回测；Period 由策略配置自动推导，禁止人工覆盖。"""
    if stage == "smoke_30d":
        range_args = ["--days", "30"]
        timeout = min(timeout, 360)
    elif stage == "validate_90d":
        range_args = ["--days", "90"]
    else:
        range_args = ["--from", "2024.06.01", "--to", "2026.05.31"]
    model = get_strategy_model(strategy)
    print(f"  [{stage}] {strategy} model={model} ...")
    started_at = time.time()
    cmd = [
        sys.executable, str(ROOT / "scripts" / "mt5_backtest_win.py"),
        "--strategy", strategy, "--symbol", "BTCUSDm",
    ] + range_args + [
        "--model", model, "--deposit", "200", "--timeout", str(timeout),
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


def _has_trade_rows(path):
    try:
        with Path(path).open("r", encoding="utf-8-sig", errors="replace") as handle:
            return sum(1 for line in handle if line.strip()) > 1
    except OSError:
        return False


def _has_24_month_rows(path):
    try:
        with Path(path).open("r", encoding="utf-8-sig", errors="replace") as handle:
            return sum(1 for line in handle if line.strip()) >= 25
    except OSError:
        return False


def _candidate_tester_logs(terminal_path):
    terminal = Path(terminal_path)
    roots = [terminal / "Tester" / "Agent-127.0.0.1-3000" / "logs", terminal / "Tester" / "logs"]
    candidates = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for item in root.glob("*.log"):
            resolved = str(item.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(item)
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates[:8]


def _try_extract_log(result_path, trades_csv, monthly_csv, log_path):
    digest = run_short([
        sys.executable, str(ROOT / "scripts" / "backtest_digest.py"),
        "--report", str(result_path), "--log", str(log_path),
        "--export-csv", "--brief",
    ], timeout=120)
    if digest.returncode != 0 or not _has_trade_rows(trades_csv):
        return False
    rebuilt = run_short([
        sys.executable, str(ROOT / "scripts" / "rebuild_24m.py"), str(trades_csv), "200",
    ], timeout=60)
    return rebuilt.returncode == 0 and _has_24_month_rows(monthly_csv)


def extract_trades(strategy, terminal_path, result_path):
    """从指定 720d 报告跨日找正确 Agent 日志，生成逐笔、24m 和 WFYS。"""
    result_path = Path(result_path)
    if not result_path.exists():
        return {"success": False, "reason": "报告缺失"}
    trades_csv = result_path.with_suffix(".trades.csv")
    monthly_csv = trades_csv.with_name(trades_csv.stem + "_closetime_24m.csv")
    logs = _candidate_tester_logs(terminal_path)
    selected_log = None
    for log_path in logs:
        if _try_extract_log(result_path, trades_csv, monthly_csv, log_path):
            selected_log = log_path
            break
    if selected_log is None and len(logs) >= 2:
        combined_log = ROOT / "temp" / (strategy + "_agent_combined_" + datetime.now().strftime("%Y%m%d") + ".log")
        with combined_log.open("wb") as handle:
            for log_path in sorted(logs, key=lambda item: item.stat().st_mtime):
                handle.write(log_path.read_bytes())
        if _try_extract_log(result_path, trades_csv, monthly_csv, combined_log):
            selected_log = combined_log
    if selected_log is None:
        return {"success": False, "reason": "未找到包含完整 24 月逐笔交易的 Agent 日志"}
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
        "log_path": str(selected_log.resolve()),
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
        prepared, detail = prepare_strategy(strategy, terminal_path)
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
