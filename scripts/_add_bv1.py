import subprocess, os, re, time
from pathlib import Path
env = os.environ.copy()
env["MT5_HOME"] = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_btc_bv1"
env["MT5_PORTABLE"] = "1"

# bv4: 锚点修改 - 一次放宽所有过滤看笔数能否到 210
new_entries = """

v11-btc1-bv4:
  <<: *v11_btc1_qual232
  version: V11-BTC1-BV4
  description: "bv4 = baseline 永久放宽所有 OB 准入过滤 (state_filter/structure_confirm/htf_shape 关闭 + min_risk=2.0 + smart_lock 推迟 2.5/0.3)"
  magic_number: 207300
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 2.5
  smart_lock_pct: 0.3
  min_risk_spread_ratio: 2.0
  enable_state_filter: false
  enable_entry_structure_confirm: false
  enable_entry_htf_shape_filter: false
"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")
content = yaml_path.read_text(encoding="utf-8")
if "v11-btc1-bv4:" in content:
    print("Already added")
else:
    with yaml_path.open("a", encoding="utf-8") as f:
        f.write(new_entries)
    print("Added v11-btc1-bv4")
