import re
log = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt\Tester\Agent-127.0.0.1-3000\logs\20260707.log"
with open(log, "rb") as f:
    raw = f.read()
print("Size:", len(raw))
print("First 200 bytes (hex):", raw[:200].hex())
matches = re.findall(b"BWX", raw)
print("BWX in raw bytes:", len(matches))
# Decode with utf-16
try:
    text16 = raw.decode("utf-16-le", errors="ignore")
    print("UTF-16 BWX count:", text16.count("BWX"))
    if "BWX" in text16:
        idx = text16.find("BWX")
        print("First BWX:", text16[idx:idx+200])
except Exception as e:
    print("UTF-16 fail:", str(e)[:100])

