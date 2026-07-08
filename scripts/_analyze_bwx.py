import re
log = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt\Tester\Agent-127.0.0.1-3000\logs\20260707.log"
with open(log, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8", errors="ignore")
bwx_lines = [l for l in text.splitlines() if "BWX " in l]
print("BWX total lines:", len(bwx_lines))
r_values = []
for l in bwx_lines:
    m = re.search(r" r=(-?[\d\.]+)", l)
    if m:
        try:
            r_values.append(float(m.group(1)))
        except:
            pass
print("R values parsed:", len(r_values))
if r_values:
    print("Min:", min(r_values), "Max:", max(r_values))
    print("R >= 2.0:", sum(1 for r in r_values if r >= 2.0))
    print("R >= 1.5:", sum(1 for r in r_values if r >= 1.5))
    print("R >= 1.0:", sum(1 for r in r_values if r >= 1.0))
    high = [r for r in r_values if r >= 1.0]
    print("Sample R >= 1.0:", high[:20])

