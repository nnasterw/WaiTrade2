import re
log = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt\Tester\Agent-127.0.0.1-3000\logs\20260707.log"
with open(log, "rb") as f:
    raw = f.read()
text = raw.decode("utf-16-le", errors="ignore")
# Find BWX near the trend610 backtest
# Trend610 was run ~21:00 (after my latest)
bwx_lines = [l for l in text.splitlines() if "BWX " in l]
print("BWX total:", len(bwx_lines))
# Find recent ones with r= format
recent = bwx_lines[-100:]
sample = [l for l in recent if "r=" in l][:10]
for s in sample:
    print(s[:200])
print("---")
# Find lines with trigger=2.5
trig_25 = [l for l in bwx_lines if "trig=2.5" in l]
print("trigger=2.5 BWX count:", len(trig_25))
# Get r values
r_values = []
for l in trig_25:
    m = re.search(r" r=(-?[\d.]+)", l)
    if m:
        try:
            r_values.append(float(m.group(1)))
        except:
            pass
if r_values:
    print("Min r in trig=2.5 BWX:", min(r_values))
    print("Max r in trig=2.5 BWX:", max(r_values))
    print("R >= 2.0 count:", sum(1 for r in r_values if r >= 2.0))
    print("R >= 1.5 count:", sum(1 for r in r_values if r >= 1.5))
    print("R >= 1.0 count:", sum(1 for r in r_values if r >= 1.0))

