import subprocess, os, re, time
from pathlib import Path
env = os.environ.copy()
env["MT5_HOME"] = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_btc_bv1"
env["MT5_PORTABLE"] = "1"

# 关键测试: 关闭 state_filter + 关闭 entry_htf_shape_filter
new_entries = """

v11-btc1-loop153:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP153
  description: "BV1 baseline + 关闭 state_filter (市场状态过滤)"
  magic_number: 207230
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  enable_state_filter: false

v11-btc1-loop154:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP154
  description: "BV1 baseline + 关闭 entry_htf_shape_filter"
  magic_number: 207231
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  enable_entry_htf_shape_filter: false

v11-btc1-loop155:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP155
  description: "BV1 baseline + 关闭 state_filter + entry_htf_shape_filter (双关闭)"
  magic_number: 207232
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  enable_state_filter: false
  enable_entry_htf_shape_filter: false

v11-btc1-loop156:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP156
  description: "BV1 baseline + 关闭 entry_structure_confirm"
  magic_number: 207233
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  enable_entry_structure_confirm: false

v11-btc1-loop157:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP157
  description: "BV1 baseline + 关闭 state_filter + entry_structure_confirm"
  magic_number: 207234
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  enable_state_filter: false
  enable_entry_structure_confirm: false
"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")
content = yaml_path.read_text(encoding="utf-8")
if "v11-btc1-loop153:" in content:
    print("Already added")
else:
    with yaml_path.open("a", encoding="utf-8") as f:
        f.write(new_entries)
    print("Added loop153-157")
