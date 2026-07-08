from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")
new_entries = """
v11-btc1-trend550:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND550
  description: "trend531 + BigWinLock 2.5/1.5 (R>=2.5 锁到 1.5R) - 提升 big_w"
  magic_number: 206550
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  btc_big_win_trigger_r: 2.5
  btc_big_win_lock_to_r: 1.5

v11-btc1-trend551:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND551
  description: "trend531 + BigWinLock 3.0/2.0 (R>=3.0 锁到 2.0R)"
  magic_number: 206551
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  btc_big_win_trigger_r: 3.0
  btc_big_win_lock_to_r: 2.0

v11-btc1-trend552:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND552
  description: "trend531 + BigWinLock 2.0/1.0 + MonthlyGuard -1.5R (防月度失控)"
  magic_number: 206552
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  btc_big_win_trigger_r: 2.0
  btc_big_win_lock_to_r: 1.0
  btc_enable_monthly_loss_guard: true
  btc_monthly_loss_guard_r: -1.5
  btc_monthly_loss_guard_only_htf_target: true

v11-btc1-trend553:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND553
  description: "trend531 + BigWinLock 2.5/1.0 + MonthlyGuard -1.5R (组合优化)"
  magic_number: 206553
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  btc_big_win_trigger_r: 2.5
  btc_big_win_lock_to_r: 1.0
  btc_enable_monthly_loss_guard: true
  btc_monthly_loss_guard_r: -1.5
  btc_monthly_loss_guard_only_htf_target: true
"""
with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Appended 4 strategies (550-553)")

