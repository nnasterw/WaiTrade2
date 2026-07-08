from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-trend530:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND530
  description: "trend218 + htf_min_target 2.5 + htf_measured 3.5 (从 2.2/3.2 提高, 提升 big_w)"
  magic_number: 206530
  htf_min_target_r: 2.5
  htf_measured_move_r: 3.5
  max_lot_size: 1.0

v11-btc1-trend531:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND531
  description: "trend218 + bad_bounce 0.22-0.28 mult 0.4 (更严过滤, 提升质量)"
  magic_number: 206531
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0

v11-btc1-trend532:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND532
  description: "trend218 + monthly_profit_target_stop 15pct + 30pct 阶梯"
  magic_number: 206532
  btc_allow_monthly_profit_target_stop: true
  monthly_profit_target_stop_pct: 15.0
  monthly_profit_target_stop_min_balance: 1000.0
  monthly_profit_target_stop2_pct: 30.0
  monthly_profit_target_stop2_min_balance: 5000.0
  max_lot_size: 1.0

v11-btc1-trend533:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND533
  description: "trend218 + breakeven 1.5/0.5 (从 1.3/0.3 提高, 锁利早)"
  magic_number: 206533
  breakeven_r: 1.5
  breakeven_lock_r: 0.5
  max_lot_size: 1.0

v11-btc1-trend534:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND534
  description: "trend218 + breakeven_stage2 2.0/0.8 (双层BE, 强锁利)"
  magic_number: 206534
  breakeven_r: 1.0
  breakeven_lock_r: 0.4
  breakeven_stage2_r: 2.0
  breakeven_stage2_lock_r: 0.8
  max_lot_size: 1.0

v11-btc1-trend535:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND535
  description: "trend218 + max_lot 0.6 (降一档, 防月度失控)"
  magic_number: 206535
  max_lot_size: 0.6
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Appended 6 strategies (530-535)")

