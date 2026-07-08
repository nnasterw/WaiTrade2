from pathlib import Path
pm_path = Path(r"D:\Code\codexProject\WaiTrade2\mql5\Include\WaiTrade2\PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")
old = "    if(s_call_count % 50 == 1) Print(\"BWX \", s_call_count, \" trig=\", InpBTCBigWinTriggerR, \" lockTo=\", InpBTCBigWinLockToR, \" htf=\", track.htf_target, \" onlyHtf=\", InpBTCBigWinOnlyHTFTarget, \" locked=\", track.bigwin_locked, \" useBTC=\", UseBTCProfile());"
new = "    if(s_call_count % 5 == 1) Print(\"BWX \", s_call_count, \" trig=\", InpBTCBigWinTriggerR, \" htf=\", track.htf_target, \" locked=\", track.bigwin_locked);"
if old in content:
    content = content.replace(old, new, 1)
    pm_path.write_text(content, encoding="utf-8")
    print("Updated BWX print to every 5 calls")
else:
    print("Not found")

