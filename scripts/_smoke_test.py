import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

kill_mt5()
t0 = time.time()
print('Silent test (Win32 FindWindow+1ms poll)...', end='', flush=True)
r = run_bt_silent('smoke2', 'v11xau-qs3.set', '2026.05.01', '2026.05.02')
elapsed = time.time() - t0
if r:
    print(f' OK ({elapsed:.0f}s) {r["count"]}T PnL=${r["pnl"]:.2f}')
else:
    print(f' FAILED ({elapsed:.0f}s)')
