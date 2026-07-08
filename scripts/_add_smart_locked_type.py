from pathlib import Path
types_path = Path(r"D:\Code\codexProject\WaiTrade2\mql5\Include\WaiTrade2\Types.mqh")
content = types_path.read_text(encoding="utf-8")
needle = "    bool     bigwin_locked;   // "
if needle in content:
    new_line = "    bool     bigwin_locked;   // bigwin protection applied\n    bool     smart_locked;    // smart lock applied (SL trails peak R)"
    content = content.replace(needle, new_line, 1)
    types_path.write_text(content, encoding="utf-8")
    print("Added smart_locked to Types.mqh")
else:
    print("Not found")

