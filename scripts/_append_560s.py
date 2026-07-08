from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")
new_entries = """
v11-btc1-trend560:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND560
  description: "trend531 + htf_partial_r 1.5 pct 50 (HTF 单部分止盈 1.5R/50%)"
  magic_number: 206560
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  htf_partial_r: 1.5
  htf_partial_pct: 50

v11-btc1-trend561:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND561
  description: "trend531 + bad_bounce 0.24-0.28 (更窄 sweet spot)"
  magic_number: 206561
  bad_bounce_min_pct: 0.24
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0

v11-btc1-trend562:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND562
  description: "trend531 + ob_high_pos_boost 1.7 mult (从 1.5 提高)"
  magic_number: 206562
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  ob_high_pos_boost_mult: 1.7

v11-btc1-trend563:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND563
  description: "trend531 + bad_bounce 0.22-0.28 + htf_partial_r 1.0 (双锁)"
  magic_number: 206563
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  htf_partial_r: 1.0
  htf_partial_pct: 50
"""
with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Appended 4 strategies (560-563)")

