"""一键回测: V96b XAUUSDm 30天 M1"""
import os
import subprocess
import sys
import time

MT5_TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"
MT5_DATA = r"C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075"
MT5_TESTER = os.path.join(MT5_DATA, "Tester")

STRATEGY = "V96b"
SYMBOL = "XAUUSDm"
FROM_DATE = "2026.04.14"
TO_DATE = "2026.05.14"

ini_content = f"""; WaiTrade {STRATEGY} / {SYMBOL} 30天M1回测
[Tester]
Expert=WaiTrade\\WT_ALL_V96_XAU_M1b.ex5
ExpertParameters={STRATEGY}.set
Symbol={SYMBOL}
Period=M1
Model=0
Optimization=0
FromDate={FROM_DATE}
ToDate={TO_DATE}
Deposit=200
Leverage=2000
Spread=0.25
ExecutionMode=0
ShutdownTerminal=1
Report=wt_{STRATEGY}_{SYMBOL}_30d_v2
"""

config_path = os.path.join(MT5_TESTER, f"wt_{STRATEGY}_{SYMBOL}_30d.ini")
os.makedirs(MT5_TESTER, exist_ok=True)

with open(config_path, "w", encoding="utf-8") as f:
    f.write(ini_content)

print(f"INI written: {config_path}")
print(f"INI content:")
print(ini_content)

# Verify EA exists
ea_path = os.path.join(MT5_DATA, "MQL5", "Experts", "WaiTrade", "WT_ALL_V96_XAU_M1b.ex5")
if not os.path.exists(ea_path):
    print(f"ERROR: EA not found at {ea_path}")
    sys.exit(1)
print(f"EA found: {ea_path}")

# Verify terminal exists
if not os.path.exists(MT5_TERMINAL):
    print(f"ERROR: Terminal not found at {MT5_TERMINAL}")
    sys.exit(1)

# Kill existing processes
os.system("taskkill /F /IM terminal64.exe 2>nul")
os.system("taskkill /F /IM metatester64.exe 2>nul")
time.sleep(2)

# Run backtest
cmd = [MT5_TERMINAL, f"/config:{config_path}"]
print(f"\nRunning: {cmd}")
print(f"(Time: {time.strftime('%H:%M:%S')})")

t0 = time.time()
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    elapsed = time.time() - t0
    print(f"Exit code: {result.returncode}")
    print(f"Elapsed: {elapsed:.0f}s")
    if result.stdout:
        print(f"stdout: {result.stdout[:500]}")
    if result.stderr:
        print(f"stderr: {result.stderr[:500]}")
except subprocess.TimeoutExpired:
    elapsed = time.time() - t0
    print(f"TIMEOUT after {elapsed:.0f}s")
except Exception as e:
    print(f"Error: {e}")

# Cleanup
os.system("taskkill /F /IM metatester64.exe 2>nul")
os.system("taskkill /F /IM terminal64.exe 2>nul")

# Check for report
print(f"\n--- Checking for report ---")
for root, dirs, files in os.walk(MT5_DATA):
    for f in files:
        if "wt_V96b_XAUUSD" in f:
            full = os.path.join(root, f)
            print(f"  Found: {full}")
