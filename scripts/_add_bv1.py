import subprocess, os, re, time
from pathlib import Path
env = os.environ.copy()
env["MT5_HOME"] = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_btc_bv1"
env["MT5_PORTABLE"] = "1"

new_entries = """

v11-btc1-loop116:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP116
  description: "BV1 + bounce_pct 0.20 (单独放宽 OB 准入)"
  magic_number: 207170
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  bounce_pct: 0.20

v11-btc1-loop117:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP117
  description: "BV1 + min_risk_spread_ratio 3.0 (单独放宽风险比)"
  magic_number: 207171
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  min_risk_spread_ratio: 3.0

v11-btc1-loop118:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP118
  description: "BV1 + sl_buffer_atr 1.0 (单独紧凑 SL)"
  magic_number: 207172
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  sl_buffer_atr: 1.0

v11-btc1-loop119:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP119
  description: "BV1 + bounce_pct 0.20 + sl_buffer_atr 1.0 (双放宽 OB+SL)"
  magic_number: 207173
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  bounce_pct: 0.20
  sl_buffer_atr: 1.0

v11-btc1-loop120:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP120
  description: "BV1 + min_risk_spread 3.0 + sl_buffer 1.0 (双放宽风险比+SL)"
  magic_number: 207174
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  min_risk_spread_ratio: 3.0
  sl_buffer_atr: 1.0

v11-btc1-loop121:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP121
  description: "BV1 + bounce_pct 0.20 + min_risk_spread 3.0 (双放宽 OB+风险比)"
  magic_number: 207175
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  bounce_pct: 0.20
  min_risk_spread_ratio: 3.0
"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")
content = yaml_path.read_text(encoding="utf-8")
if "v11-btc1-loop116:" in content:
    print("Already added")
else:
    with yaml_path.open("a", encoding="utf-8") as f:
        f.write(new_entries)
    print("Added loop116-121")
