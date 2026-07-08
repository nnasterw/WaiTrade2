import re
log = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt\Tester\Agent-127.0.0.1-3000\logs\20260707.log"
with open(log, "rb") as f:
    raw = f.read()
text = raw.decode("utf-16-le", errors="ignore")
# Get the most recent backtest results (trend620)
recent_lines = [l for l in text.splitlines() if "trig=0.1" in l and "BWX" in l]
print("BWX with trig=0.1:", len(recent_lines))
triggered = [l for l in text.splitlines() if "BWX TRIGGER" in l]
print("BWX TRIGGER (all):", len(triggered))
biglock = [l for l in text.splitlines() if "bigwin_lock" in l]
print("bigwin_lock (all):", len(biglock))
# Check r values for trig=0.1
rs = []
for l in recent_lines:
    m = re.search(r" r=(-?[\d.]+)", l)
    if m:
        try:
            rs.append(float(m.group(1)))
        except:
            pass
if rs:
    print("R values (trig=0.1):", len(rs), "max:", max(rs), "min:", min(rs))
    print("R >= 0.1 count:", sum(1 for r in rs if r >= 0.1))

