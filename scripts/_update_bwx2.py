import re
from pathlib import Path
pm_path = Path(r"D:\Code\codexProject\WaiTrade2\mql5\Include\WaiTrade2\PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")
# Find CheckBigWinProtection and update to print more info
needle = "    static int s_call_count = 0;\n    s_call_count++;\n    if(s_call_count % 100 == 1) Print(\"BWX call #\", s_call_count, \" trigger=\", InpBTCBigWinTriggerR, \" htf=\", track.htf_target, \" onlyHtf=\", InpBTCBigWinOnlyHTFTarget);"
new_block = "    static int s_call_count = 0;\n    s_call_count++;\n    if(s_call_count % 50 == 1) Print(\"BWX \", s_call_count, \" trig=\", InpBTCBigWinTriggerR, \" lockTo=\", InpBTCBigWinLockToR, \" htf=\", track.htf_target, \" onlyHtf=\", InpBTCBigWinOnlyHTFTarget, \" locked=\", track.bigwin_locked, \" useBTC=\", UseBTCProfile());"
if needle in content:
    content = content.replace(needle, new_block, 1)
    pm_path.write_text(content, encoding="utf-8")
    print("Updated BWX print")
else:
    print("Not found")

