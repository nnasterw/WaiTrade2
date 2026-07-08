"""loop41-45: SmartLock fine-tune to push big_w >= 20%"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-loop41:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP41
  description: "trend531 + SmartLock 2.0/0.45 (slightly tighter)"
  magic_number: 206880
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 2.0
  smart_lock_pct: 0.45

v11-btc1-loop42:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP42
  description: "trend531 + SmartLock 2.2/0.5 (later trigger)"
  magic_number: 206881
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 2.2
  smart_lock_pct: 0.5

v11-btc1-loop43:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP43
  description: "trend531 + SmartLock 1.8/0.5 (earlier trigger)"
  magic_number: 206882
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5

v11-btc1-loop44:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP44
  description: "trend531 + SmartLock 2.0/0.5 + sl_buffer 0.12 (slight SL improve)"
  magic_number: 206883
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 2.0
  smart_lock_pct: 0.5
  sl_buffer_atr: 0.12

v11-btc1-loop45:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP45
  description: "trend531 + SmartLock 2.0/0.4 (more aggressive lock to retain less but reduce max loss)"
  magic_number: 206884
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 2.0
  smart_lock_pct: 0.4
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Added 5 loop variants (loop41-45)")

