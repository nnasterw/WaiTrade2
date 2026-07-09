import subprocess, os, re, time
from pathlib import Path
env = os.environ.copy()
env["MT5_HOME"] = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_btc_bv1"
env["MT5_PORTABLE"] = "1"
results = []
for v in [123, 124, 125, 126, 127, 128]:
    for f in Path("temp/mt5_portable_btc_bv1/Tester").rglob("*.tst"):
        try: f.unlink()
        except: pass
    bt_ini = Path("temp/mt5_portable_btc_bv1/bt.ini")
    if bt_ini.exists():
        bt_ini.unlink()
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe", "/IM", "metatester64.exe"], capture_output=True)
    time.sleep(3)
    cmd = ["python", "scripts/mt5_backtest_win.py", "--strategy", f"v11-btc1-loop{v}", "--symbol", "BTCUSDm", "--days", "90", "--model", "4", "--deposit", "200", "--timeout", "600"]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=900)
    txt_files = sorted(Path("results/backtest").glob(f"v11-btc1-loop{v}_*2026*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if txt_files:
        content = txt_files[0].read_text(encoding="utf-8")
        m = re.search(r"BTCUSDm\s+(\d+)\s+[\d.]+\s+(\d+)\s+(\d+)\s+\S+\s+\S+\s+\$([\d.]+)", content)
        if m:
            trades, wr, balance_str = m.groups()
            balance = float(balance_str)
            results.append((v, int(trades), float(wr), balance))
            print(f"loop{v}: n={trades} wr={wr} bal=${balance}", flush=True)
        else:
            results.append((v, 0, 0, 200))
            print(f"loop{v}: no match (FAIL)", flush=True)
    else:
        results.append((v, 0, 0, 200))
        print(f"loop{v}: no report (FAIL)", flush=True)

print("\n=== Summary ===", flush=True)
for v, n, w, b in sorted(results, key=lambda x: -x[3]):
    print(f"loop{v:<5} n={n:<5} wr={w:<5} bal=${b:.2f}", flush=True)
