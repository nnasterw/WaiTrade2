"""loop18-22: fix wf-yhcl root causes (no time filters)"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-loop18:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP18
  description: "trend531 + sl_buffer 0.3 (from 0.1) - reduce tick noise SL"
  magic_number: 206830
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  sl_buffer_atr: 0.3

v11-btc1-loop19:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP19
  description: "trend531 + bounce_confirm_bars 1 (force K-line confirmation)"
  magic_number: 206831
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  bounce_close_confirm_bars: 1

v11-btc1-loop20:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP20
  description: "trend531 + min_ob_strength 0.6 (higher OB quality)"
  magic_number: 206832
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  min_ob_strength: 0.6

v11-btc1-loop21:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP21
  description: "trend531 + htf_net_push_filter true (trend alignment)"
  magic_number: 206833
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_htf_net_push_filter: true

v11-btc1-loop22:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP22
  description: "trend531 + sl_buffer 0.3 + bounce_confirm 1 + htf_push true (combined wf-yhcl fixes)"
  magic_number: 206834
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  sl_buffer_atr: 0.3
  bounce_close_confirm_bars: 1
  enable_htf_net_push_filter: true
  min_ob_strength: 0.6
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Added 5 loop variants (loop18-22)")

