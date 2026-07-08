import re
log = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt\Tester\Agent-127.0.0.1-3000\logs\20260707.log"
with open(log, "rb") as f:
    raw = f.read()
text = raw.decode("utf-16-le", errors="ignore")
bwx_lines = [l for l in text.splitlines() if "BWX " in l and "trig=2.5" in l]
print("trig=2.5 BWX:", len(bwx_lines))
r_values = []
for l in bwx_lines:
    m = re.search(r" r=(-?[\d.]+)", l)
    if m:
        try:
            r_values.append(float(m.group(1)))
        except:
            pass
print("Total r values:", len(r_values))
above_2 = [r for r in r_values if r >= 2.0]
print("R >= 2.0 count:", len(above_2))
print("Sample R >= 2.0:", above_2[:20])
print("Max r:", max(r_values))
print("Min r:", min(r_values))
# Count by bucket
buckets = {-2:0, -1:0, 0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0}
for r in r_values:
    for k in buckets:
        if r >= k:
            buckets[k] += 1
            break
print("Cumulative buckets:", buckets)

