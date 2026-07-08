"""在 Types.mqh PosTrack 结构中加 bigwin_locked 字段 - 字节级"""
from pathlib import Path

types_path = Path("D:/Code/codexProject/WaiTrade2/mql5/Include/WaiTrade2/Types.mqh")
content = types_path.read_text(encoding="utf-8")

# 用 byte 操作 - 找 dtp_partial_closed 行
import re
pattern = re.compile(r"(\s+bool\s+dtp_partial_closed;[^\n]*)")
m = pattern.search(content)
if not m:
    print("Anchor not found")
    exit(1)

old_line = m.group(1)
print("Found:", repr(old_line[:80]))

new_block = old_line + "\n    bool     bigwin_locked;   // bigwin protection applied"

content_new = content.replace(old_line, new_block, 1)
types_path.write_text(content_new, encoding="utf-8")
print("Added bigwin_locked field")
print("File size:", types_path.stat().st_size)

