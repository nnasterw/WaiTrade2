"""loop37-40: trend531 + SmartLock variants (no BTC profile)"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-loop37:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP37
  description: "trend531 (no enable_btc) + SmartLock default (trigger 2.0, pct 0.5)"
  magic_number: 206870
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 2.0
  smart_lock_pct: 0.5

v11-btc1-loop38:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP38
  description: "trend531 + SmartLock 1.5/0.5 (earlier lock)"
  magic_number: 206871
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.5
  smart_lock_pct: 0.5

v11-btc1-loop39:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP39
  description: "trend531 + SmartLock 2.5/0.6 (later trigger, bigger lock)"
  magic_number: 206872
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 2.5
  smart_lock_pct: 0.6

v11-btc1-loop40:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP40
  description: "trend531 + SmartLock 2.0/0.7 (high pct for safer lock)"
  magic_number: 206873
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 2.0
  smart_lock_pct: 0.7
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Added 4 loop variants (loop37-40)")

