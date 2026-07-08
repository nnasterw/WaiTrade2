import re
from pathlib import Path
pm_path = Path(r"D:\Code\codexProject\WaiTrade2\mql5\Include\WaiTrade2\PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")
# Remove the s_call_count limit
old = "    static int s_call_count = 0;\n    s_call_count++;\n    if(s_call_count <= 3) Print(\"BWX CheckBigWinProtection call #\", s_call_count, \" trigger=\", InpBTCBigWinTriggerR, \" lockTo=\", InpBTCBigWinLockToR);"
new = "    static int s_call_count = 0;\n    s_call_count++;\n    if(s_call_count % 100 == 1) Print(\"BWX call #\", s_call_count, \" trigger=\", InpBTCBigWinTriggerR, \" lockTo=\", InpBTCBigWinLockToR, \" htf=\", track.htf_target, \" onlyHtf=\", InpBTCBigWinOnlyHTFTarget, \" r=\", current_r, \" locked=\", track.bigwin_locked);"
# Try with current_r definition
old_simple = "    if(s_call_count <= 3) Print(\"BWX CheckBigWinProtection call #\", s_call_count, \" trigger=\", InpBTCBigWinTriggerR, \" lockTo=\", InpBTCBigWinLockToR);"
new_simple = "    if(s_call_count % 100 == 1) Print(\"BWX call #\", s_call_count, \" trigger=\", InpBTCBigWinTriggerR, \" htf=\", track.htf_target, \" onlyHtf=\", InpBTCBigWinOnlyHTFTarget);"
if old_simple in content:
    content = content.replace(old_simple, new_simple, 1)
    pm_path.write_text(content, encoding="utf-8")
    print("Replaced BWX print with periodic + htf info")
else:
    print("Not found, current content snippet:")
    idx = content.find("BWX")
    print(content[max(0,idx-200):idx+500] if idx >= 0 else "not found")

