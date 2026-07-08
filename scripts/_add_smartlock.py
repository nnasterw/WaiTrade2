from pathlib import Path
config_path = Path(r"D:\Code\codexProject\WaiTrade2\mql5\Include\WaiTrade2\Config.mqh")
content = config_path.read_text(encoding="utf-8")
needle = "input bool   InpBTCDTPResetPeakAfterPartial = false;"
new_block = needle + "\ninput bool   InpSmartLockEnable = true;\ninput double InpSmartLockTriggerR = 2.0;\ninput double InpSmartLockPct = 0.5;"
if needle in content:
    content = content.replace(needle, new_block, 1)
    config_path.write_text(content, encoding="utf-8")
    print("Added SmartLock params to Config.mqh")
else:
    print("Anchor not found")

