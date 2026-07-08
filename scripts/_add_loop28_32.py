"""loop28-32: fine-tune trend531 with modest improvements"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-loop28:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP28
  description: "trend531 + sl_buffer_atr 0.15 (modest SL buffer, from 0.1)"
  magic_number: 206850
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  sl_buffer_atr: 0.15

v11-btc1-loop29:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP29
  description: "trend531 + bounce_close_confirm_bars 1 (force K-line confirm)"
  magic_number: 206851
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  bounce_close_confirm_bars: 1

v11-btc1-loop30:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP30
  description: "trend531 + entry_depth 0.5 (deeper OB entry, from 0.67)"
  magic_number: 206852
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  entry_depth_pct: 0.5

v11-btc1-loop31:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP31
  description: "trend531 + min_impulse_body_pct 55 (stronger momentum requirement)"
  magic_number: 206853
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  min_impulse_body_pct: 55

v11-btc1-loop32:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP32
  description: "trend531 + bad_bounce 0.21-0.27 (slight tightening, between 0.22-0.28 and 0.20-0.26)"
  magic_number: 206854
  bad_bounce_min_pct: 0.21
  bad_bounce_max_pct: 0.27
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Added 5 loop variants (loop28-32)")

