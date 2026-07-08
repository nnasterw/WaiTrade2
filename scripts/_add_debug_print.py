import re
from pathlib import Path
pm_path = Path(r"D:\Code\codexProject\WaiTrade2\mql5\Include\WaiTrade2\PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")
# Add a debug print at the start of CheckBigWinProtection
needle = "void CheckBigWinProtection(PosTrack &track, const EAState &state)\n{\n    if(!UseBTCProfile()) return;\n    double trigger_r = InpBTCBigWinTriggerR;\n    double lock_to_r = InpBTCBigWinLockToR;\n    if(trigger_r <= 0.0 || lock_to_r <= 0.0) return;\n    if(InpBTCBigWinOnlyHTFTarget && !track.htf_target) return;\n    if(track.bigwin_locked) return;\n    if(!PositionSelectByTicket(track.ticket)) return;"
new_needle = "void CheckBigWinProtection(PosTrack &track, const EAState &state)\n{\n    static int s_call_count = 0;\n    s_call_count++;\n    if(s_call_count <= 3) Print(\"BWX CheckBigWinProtection call #\", s_call_count, \" trigger=\", InpBTCBigWinTriggerR, \" lockTo=\", InpBTCBigWinLockToR);\n    if(!UseBTCProfile()) return;\n    double trigger_r = InpBTCBigWinTriggerR;\n    double lock_to_r = InpBTCBigWinLockToR;\n    if(trigger_r <= 0.0 || lock_to_r <= 0.0) return;\n    if(InpBTCBigWinOnlyHTFTarget && !track.htf_target) return;\n    if(track.bigwin_locked) return;\n    if(!PositionSelectByTicket(track.ticket)) return;"
if needle in content:
    content_new = content.replace(needle, new_needle, 1)
    pm_path.write_text(content_new, encoding="utf-8")
    print("Added debug print to CheckBigWinProtection")
else:
    print("Needle not found")

