"""Add loop8-loop12: Reduce trade count via tighter BTC parameters"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-loop8:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP8
  description: "trend218 + btc_max_pos_mult 30 (from 300) - reduce stacking"
  magic_number: 206810
  enable_btc_profile: true
  btc_max_pos_mult: 30.0
  max_lot_size: 1.0

v11-btc1-loop9:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP9
  description: "trend218 + btc_max_pos_mult 30 + btc_bounce_pct 0.30 - tighter"
  magic_number: 206811
  enable_btc_profile: true
  btc_max_pos_mult: 30.0
  btc_bounce_pct: 0.30
  max_lot_size: 1.0

v11-btc1-loop10:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP10
  description: "trend218 + btc_min_risk_spread 8 + btc_bounce_pct 0.30 - skip bad signals"
  magic_number: 206812
  enable_btc_profile: true
  btc_min_risk_spread_ratio: 8.0
  btc_bounce_pct: 0.30
  max_lot_size: 1.0

v11-btc1-loop11:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP11
  description: "trend218 + btc_max_concurrent 3 (from 8) - max 3 positions"
  magic_number: 206813
  enable_btc_profile: true
  btc_max_concurrent: 3
  max_lot_size: 1.0

v11-btc1-loop12:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP12
  description: "trend218 + btc_dtp_trigger_r 2.0 retrigger 0.3 + btc_bounce_pct 0.30"
  magic_number: 206814
  enable_btc_profile: true
  btc_dtp_trigger_r: 2.0
  btc_dtp_retrace: 0.3
  btc_bounce_pct: 0.30
  max_lot_size: 1.0
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Added 5 loop variants (loop8-12)")

