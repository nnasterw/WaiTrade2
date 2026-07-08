from pathlib import Path
pm_path = Path(r"D:\Code\codexProject\WaiTrade2\mql5\Include\WaiTrade2\PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")
needle = "         CheckBigWinProtection(tracks[i], state);"
new_block = "         CheckSmartLock(tracks[i], state);\n         CheckBigWinProtection(tracks[i], state);"
if needle in content:
    content = content.replace(needle, new_block, 1)
    pm_path.write_text(content, encoding="utf-8")
    print("Added CheckSmartLock call in ManagePositions")
else:
    print("Not found")

