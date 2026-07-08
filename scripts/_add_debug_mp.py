import re
from pathlib import Path
pm_path = Path(r"D:\Code\codexProject\WaiTrade2\mql5\Include\WaiTrade2\PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")
# Add debug print at the start of ManagePositions
needle = "void ManagePositions(PosTrack &tracks[], int &track_count, const EAState &state)\n{\n    if(CheckMonthlyLossStop(true))\n    {"
new_needle = "void ManagePositions(PosTrack &tracks[], int &track_count, const EAState &state)\n{\n    static int s_mp_count = 0;\n    s_mp_count++;\n    if(s_mp_count <= 3) Print(\"MPX ManagePositions call #\", s_mp_count, \" track_count=\", track_count);\n    if(CheckMonthlyLossStop(true))\n    {"
if needle in content:
    content_new = content.replace(needle, new_needle, 1)
    pm_path.write_text(content_new, encoding="utf-8")
    print("Added debug print to ManagePositions")
else:
    print("Needle not found")

