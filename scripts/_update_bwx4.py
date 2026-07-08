from pathlib import Path
pm_path = Path(r"D:\Code\codexProject\WaiTrade2\mql5\Include\WaiTrade2\PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")
old = "    if(s_call_count % 5 == 1) Print(\"BWX \", s_call_count, \" trig=\", InpBTCBigWinTriggerR, \" htf=\", track.htf_target, \" locked=\", track.bigwin_locked);"
new = "    if(s_call_count % 5 == 1) { double cr = PriceToR(PositionGetDouble(POSITION_PRICE_CURRENT), track.entry_price, track.risk_price, track.direction); Print(\"BWX \", s_call_count, \" trig=\", InpBTCBigWinTriggerR, \" htf=\", track.htf_target, \" r=\", cr, \" risk_price=\", track.risk_price, \" entry=\", track.entry_price); }"
if old in content:
    content = content.replace(old, new, 1)
    pm_path.write_text(content, encoding="utf-8")
    print("Updated BWX to show current_r")
else:
    print("Not found")

