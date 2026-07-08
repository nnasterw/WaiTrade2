"""Add loop13-17: Push trend531 88.34 to 90+ without BTC profile"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

# BTC profile FALSE - focus on default-param tuning
new_entries = """
v11-btc1-loop13:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP13
  description: "trend531 + btc_dtp_trigger 2.0 retrace 0.3 - raise DTP for less premature exits"
  magic_number: 206820
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  dtp_trigger_r: 2.0
  dtp_retrace: 0.3

v11-btc1-loop14:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP14
  description: "trend531 + cooldown 3 bars (from 1) + ob_reentry 60min (from 30)"
  magic_number: 206821
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  cooldown_bars: 3
  ob_reentry_cooldown_min: 60

v11-btc1-loop15:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP15
  description: "trend531 + bad_bounce 0.20-0.26 (tighter than 0.22-0.28)"
  magic_number: 206822
  bad_bounce_min_pct: 0.20
  bad_bounce_max_pct: 0.26
  bad_bounce_mult: 0.4
  max_lot_size: 1.0

v11-btc1-loop16:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP16
  description: "trend531 + bounce_sweet 0.30-0.40 (tighter sweet spot) + bounce_pct 0.28"
  magic_number: 206823
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  bounce_sweet_min_pct: 0.30
  bounce_sweet_max_pct: 0.40
  bounce_pct: 0.28

v11-btc1-loop17:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP17
  description: "trend531 + min_risk_spread 4.0 + bounce_pct 0.28 - skip low quality signals"
  magic_number: 206824
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  min_risk_spread_ratio: 4.0
  bounce_pct: 0.28
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Added 5 loop variants (loop13-17)")

