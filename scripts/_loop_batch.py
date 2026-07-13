#!/usr/bin/env python3
"""_loop_batch.py - Loop 批量执行 (smoke test + 720d + WFYS) [yhcl 3.1 升级: token 预算]

用法:
  python scripts/_loop_batch.py --variants v11-btc1-loop1,v11-btc1-loop2 \
      --terminal mt5_portable_btc_trend111 --time-limit 30

特性 (yhcl 3.1):
  - 30d smoke test fail-fast (默认强制)
  - 每个变体后自动清理 MT5 cache
  - 自动提取 trades.csv (指定 log 路径)
  - 自动 WFYS 评分
  - 30 分钟时间盒
  - [升级] Token 预算估算 + 80% 警告 + 100% 停止
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

ROOT = Path("D:/Code/codexProject/WaiTrade2")
RESULTS = ROOT / "results" / "backtest"
TEMP = ROOT / "temp"

# yhcl 3.1: token 估算 (实测样本)
TOKEN_ESTIMATES = {
    "smoke_30d": 1.0,      # 30d smoke test
    "validate_90d": 1.0,  # 90d 中间验证（Loop Engineering 主流模式，2026-07-13 添加）
    "full_720d": 5.0,       # 720d 完整
    "wfys_extract": 0.5,   # trades.csv + WFYS
    "diagnose": 0.2,        # diagnose 阶段
    "close": 0.1,           # close 笔记
}
TOKEN_BUDGET_DEFAULT = 26.0  # 默认 30min 时间盒对应 ~26M token (留 4M 余量)
TOKEN_WARN_RATIO = 0.80      # 80% 警告
TOKEN_STOP_RATIO = 1.00      # 100% 停止


def estimate_tokens(phase, with_smoke=True, with_wfys=True):
    """估算单个变体 token 用量 (M) - 旧版 720d 完整路径"""
    total = 0.0
    if with_smoke:
        total += TOKEN_ESTIMATES["smoke_30d"]
    total += TOKEN_ESTIMATES["full_720d"]
    if with_wfys:
        total += TOKEN_ESTIMATES["wfys_extract"]
    return total


def estimate_tokens_v2(stage):
    """估算单个变体 token 用量 (M) - 2026-07-13 新版支持 90d 中间验证

    Args:
        stage: 三选一
            - "smoke_30d": 仅 smoke
            - "validate_90d": 90d 中间验证不升级 (Loop Engineering 主流)
            - "full_720d": 720d 升级走完整路径
    """
    if stage == "smoke_30d":
        return TOKEN_ESTIMATES["smoke_30d"]
    elif stage == "validate_90d":
        return TOKEN_ESTIMATES["validate_90d"]
    elif stage == "full_720d":
        total = TOKEN_ESTIMATES["smoke_30d"] + TOKEN_ESTIMATES["full_720d"] + TOKEN_ESTIMATES["wfys_extract"]
        return total
    else:
        return TOKEN_ESTIMATES["smoke_30d"] + TOKEN_ESTIMATES["full_720d"]


def measure_actual_tokens(results_dir, date_str=None):
    """根据 results/backtest/ 下的实际 txt 报告反推实际 token 用量 (M)

    2026-07-13 添加：原代码估算漏了 90d 中间验证场景。本函数扫描同日生成的
    720d/90d txt 报告以及对应 trades.csv + wfys JSON，反推实际 MT5 + digest + wfys token 用量。

    Args:
        results_dir: results/backtest 路径
        date_str: 过滤日期前缀 (如 '20260713')，None 则统计全部

    Returns:
        dict 含 n_720d, n_90d, n_wfys, est_token_m, files_count
    """
    import datetime
    import re
    from pathlib import Path
    rd = Path(results_dir)
    if not rd.exists():
        return {"n_720d": 0, "n_90d": 0, "n_wfys": 0, "est_token_m": 0.0, "files_count": 0}

    n_720d = 0
    n_90d = 0
    n_wfys = 0

    for f in rd.glob("*.txt"):
        if date_str and date_str not in f.name:
            continue
        m = re.search(r"_(\d{8})_(\d{8})_", f.name)
        if not m:
            continue
        try:
            from_dt = datetime.datetime.strptime(m.group(1), "%Y%m%d")
            to_dt = datetime.datetime.strptime(m.group(2), "%Y%m%d")
            days = (to_dt - from_dt).days
            if days > 365:
                n_720d += 1
            elif days < 200:
                n_90d += 1
        except Exception:
            continue

    for f in rd.glob("*_wfys_*.json"):
        if date_str and date_str not in f.name:
            continue
        n_wfys += 1

    est_token_m = n_720d * 5.0 + n_90d * 1.0 + n_wfys * 0.35
    return {
        "n_720d": n_720d,
        "n_90d": n_90d,
        "n_wfys": n_wfys,
        "est_token_m": round(est_token_m, 1),
        "files_count": n_720d + n_90d + n_wfys,
    }


def print_token_audit(date_str=None):
    """打印 token 用量实测对账 (实际 vs 估算) - 用于诊断脱节奇"""
    actual = measure_actual_tokens(RESULTS, date_str)
    if date_str:
        print("=== Token 实测 (" + date_str + ") ===")
    else:
        print("=== Token 实测 (全部) ===")
    print("  720d 回测:        " + str(actual["n_720d"]) + " 个（估算 " + str(round(actual["n_720d"] * 5.0, 1)) + "M）")
    print("  90d 中间验证:    " + str(actual["n_90d"]) + " 个（估算 " + str(round(actual["n_90d"] * 1.0, 1)) + "M）")
    print("  wfys 评分:        " + str(actual["n_wfys"]) + " 个（估算 " + str(round(actual["n_wfys"] * 0.35, 1)) + "M）")
    print("  ---")
    print("  实际总计:        ~" + str(actual["est_token_m"]) + "M token")
    # Compare to old estimate (always assumes full smoke+720d+wfys = 6.5M per variant)
    old_est_total = actual["files_count"] * 6.5
    diff = old_est_total - actual["est_token_m"]
    print("  旧估算总计:       ~" + str(round(old_est_total, 1)) + "M token（每变体 6.5M）")
    if diff > 0:
        print("  [WARN] 旧估算高出实际 " + str(round(diff, 1)) + "M（" + str(round(diff * 100.0 / max(old_est_total, 0.1))) + "%）-原因：90d 中间验证未被 TOKEN_ESTIMATES 统计（2026-07-13）")
    print()


def check_token_budget(used, budget):
    """检查 token 预算状态

    Returns:
        (status, ratio) - status: ok/warn/stop, ratio: used/budget
    """
    if budget <= 0:
        return "ok", 0.0
    ratio = used / budget
    if ratio >= TOKEN_STOP_RATIO:
        return "stop", ratio
    elif ratio >= TOKEN_WARN_RATIO:
        return "warn", ratio
    return "ok", ratio


def clear_mt5_cache(terminal_path):
    """清理 MT5 cache (.tst + cache dirs)"""
    tst_files = list(terminal_path.rglob("*.tst"))
    cache_dirs = [terminal_path / "Tester" / "cache", terminal_path / "Tester" / "Cache"]
    cleared = 0
    for f in tst_files:
        try:
            f.unlink()
            cleared += 1
        except Exception:
            pass
    for d in cache_dirs:
        if d.exists():
            try:
                shutil.rmtree(d, ignore_errors=True)
                d.mkdir(exist_ok=True)
            except Exception:
                pass
    if cleared > 0:
        print("    [cache] 清理 " + str(cleared) + " .tst")
    return cleared


def smoke_test(strategy, terminal_path, env, days=30, timeout=300):
    """30d smoke test"""
    print("  [smoke] " + strategy + " ...")
    start = time.time()
    cmd = [
        sys.executable, str(ROOT / "scripts" / "mt5_backtest_win.py"),
        "--strategy", strategy, "--symbol", "BTCUSDm",
        "--days", str(days), "--model", "4", "--deposit", "200", "--timeout", str(timeout),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env, timeout=timeout+30)
    elapsed = time.time() - start
    success = (result.returncode == 0) and ("结果:" in result.stdout or "余额" in result.stdout)
    balance = None
    for line in result.stdout.split("\n"):
        if "余额" in line and "$" in line and ("BTCUSDm" in line or "合计" in line):
            parts = line.split("$")
            if len(parts) >= 2:
                try:
                    balance = float(parts[-1].split()[0].replace(",", ""))
                except Exception:
                    pass
            break
    status = "PASS" if success else "FAIL"
    print("    [smoke " + status + "] " + strategy + " (" + str(int(elapsed)) + "s, balance=$" + str(balance) + ")")
    return success, balance


def full_test(strategy, terminal_path, env, timeout=1200):
    """720d 完整回测"""
    print("  [720d] " + strategy + " ...")
    start = time.time()
    cmd = [
        sys.executable, str(ROOT / "scripts" / "mt5_backtest_win.py"),
        "--strategy", strategy, "--symbol", "BTCUSDm",
        "--from", "2024.06.01", "--to", "2026.05.31",
        "--model", "4", "--deposit", "200", "--timeout", str(timeout),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env, timeout=timeout+60)
    elapsed = time.time() - start
    success = (result.returncode == 0) and "余额" in result.stdout
    balance = None
    trades = None
    for line in result.stdout.split("\n"):
        if "BTCUSDm" in line and "笔交易" in line:
            parts = line.split()
            for p in parts:
                if p.isdigit():
                    trades = int(p)
                if p.startswith("$"):
                    try:
                        balance = float(p[1:].replace(",", ""))
                    except Exception:
                        pass
    status = "PASS" if success else "FAIL"
    print("    [720d " + status + "] " + strategy + " (" + str(int(elapsed)) + "s, balance=$" + str(balance) + ", trades=" + str(trades) + ")")
    return success, balance, trades


def extract_trades(strategy, terminal_path):
    """提取 trades.csv + 24m + WFYS"""
    log_path = terminal_path / "Tester" / "Agent-127.0.0.1-3000" / "logs" / (datetime.now().strftime("%Y%m%d") + ".log")
    if not log_path.exists():
        logs_dir = terminal_path / "Tester" / "Agent-127.0.0.1-3000" / "logs"
        if logs_dir.exists():
            logs = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            if logs:
                log_path = logs[0]
    if not log_path.exists():
        print("    [FAIL] 无 log: " + str(log_path))
        return False
    result_path = RESULTS / (strategy + "_20240601_20260531_" + datetime.now().strftime("%Y%m%d") + ".txt")
    if not result_path.exists():
        candidates = sorted(RESULTS.glob(strategy + "_20240601_20260531_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            result_path = candidates[0]
    if not result_path.exists():
        print("    [FAIL] 无 result: " + str(result_path))
        return False
    # backtest_digest
    cmd = [sys.executable, str(ROOT / "scripts" / "backtest_digest.py"),
           "--report", str(result_path), "--log", str(log_path), "--export-csv", "--brief"]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
    if r.returncode != 0:
        print("    [FAIL] backtest_digest: " + r.stderr[:200])
        return False
    trades_csv = result_path.with_suffix(".trades.csv")
    if not trades_csv.exists() or trades_csv.stat().st_size < 1000:
        print("    [WARN] trades.csv 太小, 跳过 WFYS")
        return False
    # 重建 24m
    cmd = [sys.executable, str(ROOT / "scripts" / "rebuild_24m.py"), str(trades_csv), "200"]
    subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
    monthly_csv = trades_csv.with_name(trades_csv.stem + "_closetime_24m.csv")
    if not monthly_csv.exists():
        print("    [WARN] 24m CSV 缺失")
        return False
    # WFYS
    wfys_json = RESULTS / (strategy + "_wfys_" + datetime.now().strftime("%Y%m%d") + ".json")
    cmd = [sys.executable, str(ROOT / "scripts" / "wfys_score.py"),
           "--monthly-csv", str(monthly_csv), "--continuous-report", str(result_path),
           "--trades-csv", str(trades_csv), "--spec", "btc", "--deposit", "200",
           "--json-out", str(wfys_json)]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
    return r.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Loop 批量执行 (yhcl 3.1 token 预算)")
    parser.add_argument("--variants", required=True, help="逗号分隔的策略名")
    parser.add_argument("--terminal", default="mt5_portable_btc_trend111")
    parser.add_argument("--time-limit", type=int, default=30, help="时间限制 (分钟)")
    parser.add_argument("--smoke", action="store_true", default=True, help="先 smoke test (默认强制)")
    parser.add_argument("--no-smoke", dest="smoke", action="store_false")
    parser.add_argument("--token-budget", type=float, default=TOKEN_BUDGET_DEFAULT, help="token 预算 (M)")
    parser.add_argument("--skip-polluted", action="store_true", help="跳过 POLLUTED.bak 标记的")
    args = parser.parse_args()

    terminal_path = TEMP / args.terminal
    if not terminal_path.exists():
        print("[FAIL] terminal 不存在: " + str(terminal_path))
        return 1

    env = {**os.environ, "MT5_HOME": str(terminal_path), "MT5_PORTABLE": "1", "MT5_REQUIRE_ADMIN": "0"}

    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    print("=" * 60)
    print("Loop Batch @ " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("Variants: " + str(len(variants)))
    print("Terminal: " + args.terminal)
    print("Time limit: " + str(args.time_limit) + " min")
    print("Smoke test: " + str(args.smoke))
    # yhcl 3.1: token 预算预估
    est_per_var = estimate_tokens("batch", with_smoke=args.smoke, with_wfys=True)
    est_total = est_per_var * len(variants)
    print("Token budget: " + str(args.token_budget) + "M, est per variant: " + str(est_per_var) + "M, est total: " + str(round(est_total, 1)) + "M")
    if est_total > args.token_budget:
        print("  [WARN] 预估超预算 (" + str(round(est_total, 1)) + "M > " + str(args.token_budget) + "M), 建议减少变体数")
    print("=" * 60)

    start_total = time.time()
    used_tokens = 0.0  # yhcl 3.1: 累计 token
    results = []

    for v in variants:
        elapsed_total = (time.time() - start_total) / 60
        if elapsed_total > args.time_limit:
            print("[TIMEOUT] 超过 " + str(args.time_limit) + " min, 停止")
            break
        # yhcl 3.1: token 预算检查
        token_status, ratio = check_token_budget(used_tokens, args.token_budget)
        if token_status == "stop":
            print("[TOKEN-STOP] token 用尽 (" + str(round(used_tokens, 1)) + "M / " + str(args.token_budget) + "M), 停止")
            break
        elif token_status == "warn":
            print("[TOKEN-WARN] token 用量达 " + str(int(ratio * 100)) + "%, 继续但请关注")
        print()
        print("--- " + v + " ---")
        clear_mt5_cache(terminal_path)
        # Smoke test
        if args.smoke:
            ok, bal = smoke_test(v, terminal_path, env)
            used_tokens += TOKEN_ESTIMATES["smoke_30d"]
            if not ok:
                results.append({"variant": v, "status": "smoke_fail", "score": 0})
                continue
        # 720d
        ok, balance, trades = full_test(v, terminal_path, env)
        used_tokens += TOKEN_ESTIMATES["full_720d"]
        if not ok:
            results.append({"variant": v, "status": "720d_fail", "score": 0, "balance": balance})
            continue
        # 提取
        extract_ok = extract_trades(v, terminal_path)
        used_tokens += TOKEN_ESTIMATES["wfys_extract"]
        if extract_ok:
            wfys_path = RESULTS / (v + "_wfys_" + datetime.now().strftime("%Y%m%d") + ".json")
            if wfys_path.exists():
                import json
                try:
                    with open(wfys_path, encoding="utf-8") as f:
                        data = json.load(f)
                    score = data.get("score", {}).get("total_score", 0)
                    results.append({"variant": v, "status": "ok", "score": score, "balance": balance, "trades": trades})
                except Exception:
                    pass
            else:
                results.append({"variant": v, "status": "wfys_missing", "balance": balance, "trades": trades})
        else:
            results.append({"variant": v, "status": "extract_fail", "balance": balance, "trades": trades})
        clear_mt5_cache(terminal_path)
        # yhcl 3.1: 实时 token 用量
        print("    [token] 累计: " + str(round(used_tokens, 1)) + "M / " + str(args.token_budget) + "M (" + str(int((used_tokens / args.token_budget) * 100)) + "%)")

    elapsed = (time.time() - start_total) / 60
    print()
    print("=" * 60)
    print("Summary (" + str(round(elapsed, 1)) + " min, ~" + str(round(used_tokens, 1)) + "M token):")
    print("=" * 60)
    for r in results:
        line = "  " + r["variant"] + ": " + r["status"]
        if r.get("score"):
            line += " | score=" + str(round(r["score"], 2))
        if r.get("balance"):
            line += " | balance=$" + str(r["balance"])
        if r.get("trades"):
            line += " | trades=" + str(r["trades"])
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
