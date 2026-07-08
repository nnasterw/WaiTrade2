from pathlib import Path
flatmap_path = Path(r"D:\Code\codexProject\WaiTrade2\scripts\yaml_to_set.py")
content = flatmap_path.read_text(encoding="utf-8")
needle = chr(34) + "btc_enable_monthly_loss_guard" + chr(34) + ": " + chr(34) + "InpBTCEnableMonthlyLossGuard" + chr(34) + ","
addition = needle + "\n" + chr(34) + "smart_lock_enable" + chr(34) + ": " + chr(34) + "InpSmartLockEnable" + chr(34) + ",\n" + chr(34) + "smart_lock_trigger_r" + chr(34) + ": " + chr(34) + "InpSmartLockTriggerR" + chr(34) + ",\n" + chr(34) + "smart_lock_pct" + chr(34) + ": " + chr(34) + "InpSmartLockPct" + chr(34) + ","
if needle in content:
    content = content.replace(needle, addition, 1)
    flatmap_path.write_text(content, encoding="utf-8")
    print("Added 3 SmartLock FLAT_MAP entries")
else:
    print("Not found")

