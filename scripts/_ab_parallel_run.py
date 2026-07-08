"""A/B 对比: 并行跑 4 个变体 (2 个 terminal)"""
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path("D:/Code/codexProject/WaiTrade2")
AB_DIR = ROOT / "results" / "ab_compare_2026-07-07"
AB_DIR.mkdir(parents=True, exist_ok=True)

# 两个 portable 路径
TERMINALS = [
    ROOT / "temp" / "mt5_portable_btc_trend111",
    # 第二个 portable: 从 mt5_portable_bt 复制
    ROOT / "temp" / "mt5_portable_btc_compare2",
]

# A/B 4 个变体分配到 2 个 terminal (顺序跑, 避免 cache)
STRATEGIES_A = ["v11-btc1-yhcl1", "v11-btc1-yhcl2"]
STRATEGIES_B = ["v11-btc1-loop1", "v11-btc1-loop2"]
TIMEOUT = 1200  # 20 分钟超时 (含 WFYS 提取)

def run_strategy_on_terminal(terminal: Path, strategy: str, port_offset: int):
    """单 terminal 顺序跑 2 个变体"""
    env_overrides = {
        "MT5_HOME": str(terminal),
        "MT5_PORTABLE": "1",
        "MT5_REQUIRE_ADMIN": "0",
    }
    log_path = AB_DIR / f"{strategy}_log.txt"
    print(f"  [{terminal.name}] Start {strategy}", flush=True)
    start = time.time()
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "mt5_backtest_win.py"),
        "--strategy", strategy,
        "--symbol", "BTCUSDm",
        "--from", "2024.06.01",
        "--to", "2026.05.31",
        "--model", "4",
        "--deposit", "200",
        "--timeout", "1200",
    ]
    with open(log_path, "w", encoding="utf-8") as f:
        result = subprocess.run(
            cmd, stdout=f, stderr=subprocess.STDOUT,
            env={**__import__("os").environ, **env_overrides},
            timeout=TIMEOUT,
        )
    elapsed = time.time() - start
    status = "OK" if result.returncode == 0 else "FAIL"
    print(f"  [{terminal.name}] {strategy} {status} ({elapsed:.0f}s)", flush=True)
    return strategy, status, elapsed

def main():
    print(f"=== A/B 并行回测 ({time.strftime(\"%H:%M:%S\")}) ===")
    print(f"  Group A (yhcl3.0 multi-var): {STRATEGIES_A}")
    print(f"  Group B (Loop Eng single-var): {STRATEGIES_B}")
    print()

    threads = []
    # Terminal 1: A 组 (yhcl1, yhcl2 顺序)
    t1 = threading.Thread(
        target=lambda: [run_strategy_on_terminal(TERMINALS[0], s, 0) for s in STRATEGIES_A],
        name="Terminal1-A",
    )
    threads.append(t1)
    # Terminal 2: B 组 (loop1, loop2 顺序)
    t2 = threading.Thread(
        target=lambda: [run_strategy_on_terminal(TERMINALS[1], s, 1) for s in STRATEGIES_B],
        name="Terminal2-B",
    )
    threads.append(t2)

    t1.start()
    t2.start()
    for t in threads:
        t.join()
    print(f"=== 完成 ({time.strftime(\"%H:%M:%S\")}) ===")

if __name__ == "__main__":
    main()

