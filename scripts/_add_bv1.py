"""Add bv1 to yaml by appending (preserves anchors)"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")
content = yaml_path.read_text(encoding="utf-8")
if "v11-btc1-bv1" in content:
    print("bv1 already exists")
    exit(0)
new_entry = chr(10) + """
v11-btc1-bv1:
  <<: *v11_btc1_qual232
  version: V11-BTC1-BV1
  description: "bv1 = loop43 92.23 winner (SmartLock 1.8/0.5 + bad_bounce 0.22-0.28 + max_lot 1.0). Production candidate."
  magic_number: 207001
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
"""
with yaml_path.open("a", encoding="utf-8") as f:
    f.write(new_entry)
print("Appended bv1 to yaml")

