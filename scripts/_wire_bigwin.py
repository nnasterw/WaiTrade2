"""在 ManagePositions 中添加 CheckBigWinProtection 和 CheckMonthlyLossGuard 调用"""
from pathlib import Path

pm_path = Path("D:/Code/codexProject/WaiTrade2/mql5/Include/WaiTrade2/PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")

# 找到 CheckMaxLossCap 调用行
needle = "         CheckMaxLossCap(tracks[i], state, tracks, track_count);"
if needle not in content:
    print("Anchor not found")
    exit(1)

new_block = needle + "\n         CheckBigWinProtection(tracks[i], state);\n         CheckMonthlyLossGuard(tracks[i], state, tracks, track_count);"
content_new = content.replace(needle, new_block, 1)
pm_path.write_text(content_new, encoding="utf-8")
print("Wired CheckBigWinProtection and CheckMonthlyLossGuard into ManagePositions")
print("File size:", pm_path.stat().st_size)

