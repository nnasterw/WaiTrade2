from pathlib import Path
pm_path = Path(r"D:\Code\codexProject\WaiTrade2\mql5\Include\WaiTrade2\PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")
old_line = "    if(current_r < trigger_r) return;\n    // 将 SL 移到 lock_to_r 位置 (锁利)\n    double new_sl = RToPrice(lock_to_r, track.entry_price, track.risk_price, track.direction);"
new_line = "    if(current_r < trigger_r) { if(current_r > trigger_r - 0.3) Print(\"BWX near r=\", current_r, \" trig=\", trigger_r); return; }\n    Print(\"BWX TRIGGER r=\", current_r, \">= trig=\", trigger_r);\n    // 将 SL 移到 lock_to_r 位置 (锁利)\n    double new_sl = RToPrice(lock_to_r, track.entry_price, track.risk_price, track.direction);"
if old_line in content:
    content = content.replace(old_line, new_line, 1)
    pm_path.write_text(content, encoding="utf-8")
    print("Added")
else:
    print("Not found")

