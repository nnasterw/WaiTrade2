import subprocess, os, re, time
from pathlib import Path
env = os.environ.copy()
env["MT5_HOME"] = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_btc_bv1"
env["MT5_PORTABLE"] = "1"

# bv3 = 复制 bv1 但 min_risk_spread_ratio 永久降低到 3.0
new_entries = """

v11-btc1-bv3:
  <<: *v11_btc1_qual232
  version: V11-BTC1-BV3
  description: "bv3 = bv1 baseline + min_risk_spread_ratio 3.0 (永久放宽风险比提频次)"
  magic_number: 207220
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  min_risk_spread_ratio: 3.0
"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")
content = yaml_path.read_text(encoding="utf-8")
if "v11-btc1-bv3:" in content:
    print("Already added")
else:
    with yaml_path.open("a", encoding="utf-8") as f:
        f.write(new_entries)
    print("Added v11-btc1-bv3")
