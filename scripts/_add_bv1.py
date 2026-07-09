import subprocess, os, re, time
from pathlib import Path
env = os.environ.copy()
env["MT5_HOME"] = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_btc_bv1"
env["MT5_PORTABLE"] = "1"

new_entries = """

v11-btc1-loop129:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP129
  description: "loop122 + BTCMinRiskSpread 3.0 (放宽 BTC 风险比过滤, 让更多 OB 通过)"
  magic_number: 207183
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: true
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  btc_min_risk_spread_ratio: 3.0

v11-btc1-loop130:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP130
  description: "loop122 + BTCMinRiskSpread 4.0 (略放宽)"
  magic_number: 207184
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: true
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  btc_min_risk_spread_ratio: 4.0

v11-btc1-loop131:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP131
  description: "loop122 + BTCBouncePct 0.20 (放宽 BTC OB 准入)"
  magic_number: 207185
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: true
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  btc_bounce_pct: 0.20

v11-btc1-loop132:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP132
  description: "loop122 + BTCBouncePct 0.30 (放宽 BTC OB 准入 0.25→0.30)"
  magic_number: 207186
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: true
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  btc_bounce_pct: 0.30

v11-btc1-loop133:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP133
  description: "loop122 + BTCMinRiskSpread 3.0 + BTCBouncePct 0.20 (双放宽)"
  magic_number: 207187
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: true
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  btc_min_risk_spread_ratio: 3.0
  btc_bounce_pct: 0.20
"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")
content = yaml_path.read_text(encoding="utf-8")
if "v11-btc1-loop129:" in content:
    print("Already added")
else:
    with yaml_path.open("a", encoding="utf-8") as f:
        f.write(new_entries)
    print("Added loop129-133")
