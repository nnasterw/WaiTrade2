from pathlib import Path
pm_path = Path(r"D:\Code\codexProject\WaiTrade2\mql5\Include\WaiTrade2\PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")
import re
# Find the trigger_r check and add detailed debug
pattern = re.compile(r"(    if\(current_r < trigger_r\) return;)([\s\S]{0,400}?)(    if\(ApplyProtectiveSL\(track, new_sl, \"bigwin_lock\", current_r\)))")
matches = pattern.findall(content)
print("Found matches:", len(matches))
if matches:
    # Add debug between trigger check and apply
    for m in matches:
        print(repr(m[0])[:80], "...")
        print("---")
        break

