"""Add loop3-loop7 variants (BTC profile tuning)"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-loop3:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP3
  description: "trend218 + bad_bounce 0.22-0.28 (test bad_bounce effect with BTC profile active)"
  magic_number: 206800
  enable_btc_profile: true
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0

v11-btc1-loop4:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP4
  description: "trend218 + cap_loss h=3,4,5,10,12 r=-0.4 (test cap_loss with BTC active)"
  magic_number: 206801
  enable_btc_profile: true
  btc_cap_loss_r: -0.4
  btc_cap_loss_hours: "3,4,5,10,12"
  max_lot_size: 1.0

v11-btc1-loop5:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP5
  description: "trend218 + btc_low_balance 0.3 0.5 0.5 (tighter low_balance protection)"
  magic_number: 206802
  enable_btc_profile: true
  btc_low_balance_threshold: 1500.0
  btc_low_balance_pos_mult: 0.3
  btc_low_balance_max_lot_size: 0.5
  max_lot_size: 1.0

v11-btc1-loop6:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP6
  description: "trend218 + btc_max_lot 0.5 (max_lot_size reduced to 0.5)"
  magic_number: 206803
  enable_btc_profile: true
  btc_max_lot_size: 0.5
  max_lot_size: 0.5

v11-btc1-loop7:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP7
  description: "trend218 + bad_bounce 0.22-0.28 + cap_loss 3,4,5,10 r=-0.4 (combined)"
  magic_number: 206804
  enable_btc_profile: true
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  btc_cap_loss_r: -0.4
  btc_cap_loss_hours: "3,4,5,10"
  max_lot_size: 1.0
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Added 5 loop variants")

