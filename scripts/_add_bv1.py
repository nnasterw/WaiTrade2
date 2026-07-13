import subprocess, os, re, time
from pathlib import Path
env = os.environ.copy()
env["MT5_HOME"] = r"D:\Code\codexProject\WaiTrade2\temp\mt5_portable_btc_bv1"
env["MT5_PORTABLE"] = "1"

new_entries = """

v11-btc1-loop134:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP134
  description: "BV1 baseline + min_risk 4.5 (略放宽风险比增笔数)"
  magic_number: 207188
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  min_risk_spread_ratio: 4.5

v11-btc1-loop135:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP135
  description: "BV1 baseline + min_risk 4.0 (中度放宽风险比)"
  magic_number: 207189
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  min_risk_spread_ratio: 4.0

v11-btc1-loop136:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP136
  description: "BV1 baseline + min_risk 3.5 (大幅放宽风险比)"
  magic_number: 207190
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  min_risk_spread_ratio: 3.5

v11-btc1-loop137:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP137
  description: "BV1 baseline + sl_buffer_atr 1.2 (小幅紧凑 SL)"
  magic_number: 207191
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  sl_buffer_atr: 1.2

v11-btc1-loop138:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP138
  description: "BV1 baseline + bounce_pct 0.22 (小幅放宽 OB 准入)"
  magic_number: 207192
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  bounce_pct: 0.22

v11-btc1-loop139:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP139
  description: "BV1 baseline + min_risk 4.0 + sl_buffer 1.2 (双放宽)"
  magic_number: 207193
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  min_risk_spread_ratio: 4.0
  sl_buffer_atr: 1.2

v11-btc1-loop140:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP140
  description: "BV1 baseline + min_risk 4.0 + bounce_pct 0.22 (双放宽)"
  magic_number: 207194
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  min_risk_spread_ratio: 4.0
  bounce_pct: 0.22

v11-btc1-loop141:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP141
  description: "BV1 baseline + 启用 FVG (含 OB 准入多信号源)"
  magic_number: 207195
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  enable_fvg: true
  fvg_min_gap_atr: 0.05
  fvg_max_gap_atr: 0.8
  fvg_timeout_min: 60

v11-btc1-loop142:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP142
  description: "BV1 baseline + SmartLock 2.0/0.5 (推迟锁让大赢单突破 3R)"
  magic_number: 207196
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 2.0
  smart_lock_pct: 0.5

v11-btc1-loop143:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP143
  description: "BV1 baseline + DTP trigger 1.8 (略早 DTP 提频次)"
  magic_number: 207197
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  buy_dtp_trigger_r: 1.8
  sell_dtp_trigger_r: 1.8
"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")
content = yaml_path.read_text(encoding="utf-8")
if "v11-btc1-loop134:" in content:
    print("Already added")
else:
    with yaml_path.open("a", encoding="utf-8") as f:
        f.write(new_entries)
    print("Added loop134-143")
