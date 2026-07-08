import re, zlib
ex5_path = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt\MQL5\Experts\WaiTrade2\WaiTrade_OB.ex5"
with open(ex5_path, "rb") as f:
    d = f.read()
# Look for any zlib data containing strings
matches = list(re.finditer(b"\x78\x9c", d)) + list(re.finditer(b"\x78\xda", d))
print("Found", len(matches), "zlib headers")
found = 0
for i, m in enumerate(matches):
    pos = m.start()
    for length in [100000, 500000, 2000000]:
        try:
            data = zlib.decompress(d[pos : pos + length])
            if len(data) > 100 and any(c < 32 and c not in (9, 10, 13) for c in data[:1000]) is False and len(data) > 50:
                # Probably text-like
                text = data[:500].decode("utf-8", errors="replace")
                if "WaiTrade" in text or "Manage" in text or "Check" in text or "BigWin" in text:
                    print(f"Offset {pos} size {len(data)}:")
                    print(f"  Text: {text[:300]}")
                    found += 1
                    if found > 5:
                        break
        except Exception:
            continue
    if found > 5:
        break

