from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-trend540:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND540
  description: "trend531 + htf 2.5/3.5 (从 2.2/3.2 提升 HTF 目标)"
  magic_number: 206540
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  htf_min_target_r: 2.5
  htf_measured_move_r: 3.5

v11-btc1-trend541:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND541
  description: "trend531 + bad_bounce 0.20-0.26 (更严过滤)"
  magic_number: 206541
  bad_bounce_min_pct: 0.20
  bad_bounce_max_pct: 0.26
  bad_bounce_mult: 0.4
  max_lot_size: 1.0

v11-btc1-trend542:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND542
  description: "trend531 + DTP 1.8/0.25 (从 2.0/0.3 折中, 期望 big_w 提升)"
  magic_number: 206542
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  btc_dtp_trigger_r: 1.8
  btc_dtp_retrace: 0.25

v11-btc1-trend543:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND543
  description: "trend531 + btc_low_balance 0.4 (从 0.5 收紧, 防低余额时失控)"
  magic_number: 206543
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  btc_low_balance_threshold: 1500.0
  btc_low_balance_pos_mult: 0.4
  btc_low_balance_max_lot_size: 0.6

v11-btc1-trend544:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND544
  description: "trend531 + bad_bounce 0.20-0.28 mult 0.5 (更严 + 减少过滤)"
  magic_number: 206544
  bad_bounce_min_pct: 0.20
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.5
  max_lot_size: 1.0

v11-btc1-trend545:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND545
  description: "trend531 + btc_bounce_pct 0.22 (从 0.25 收紧)"
  magic_number: 206545
  btc_bounce_pct: 0.22
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Appended 6 strategies (540-545)")

