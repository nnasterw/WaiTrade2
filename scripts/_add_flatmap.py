from pathlib import Path
flatmap_path = Path("D:/Code/codexProject/WaiTrade2/scripts/yaml_to_set.py")
content = flatmap_path.read_text(encoding="utf-8")
needle = chr(34) + "btc_cap_loss_days" + chr(34) + ": " + chr(34) + "InpBTCCapLossDays" + chr(34) + ","
addition = needle + "\n" + chr(34) + "btc_big_win_trigger_r" + chr(34) + ": " + chr(34) + "InpBTCBigWinTriggerR" + chr(34) + ",\n" + chr(34) + "btc_big_win_lock_to_r" + chr(34) + ": " + chr(34) + "InpBTCBigWinLockToR" + chr(34) + ",\n" + chr(34) + "btc_big_win_only_htf_target" + chr(34) + ": " + chr(34) + "InpBTCBigWinOnlyHTFTarget" + chr(34) + ",\n" + chr(34) + "btc_enable_monthly_loss_guard" + chr(34) + ": " + chr(34) + "InpBTCEnableMonthlyLossGuard" + chr(34) + ",\n" + chr(34) + "btc_monthly_loss_guard_r" + chr(34) + ": " + chr(34) + "InpBTCMonthlyLossGuardR" + chr(34) + ",\n" + chr(34) + "btc_monthly_loss_guard_only_htf_target" + chr(34) + ": " + chr(34) + "InpBTCMonthlyLossGuardOnlyHTFTarget" + chr(34) + ","
if needle in content:
    content_new = content.replace(needle, addition, 1)
    flatmap_path.write_text(content_new, encoding="utf-8")
    print("Added 6 new FLAT_MAP entries")
else:
    print("Anchor not found")

