"""loop23-27: fine-tune min_ob_strength to find sweet spot"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-loop23:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP23
  description: "trend531 + min_ob_strength 0.55 (between 0.5 and 0.6)"
  magic_number: 206840
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  min_ob_strength: 0.55

v11-btc1-loop24:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP24
  description: "trend531 + min_ob_strength 0.6 + bad_bounce 0.20-0.26 (tighter)"
  magic_number: 206841
  bad_bounce_min_pct: 0.20
  bad_bounce_max_pct: 0.26
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  min_ob_strength: 0.6

v11-btc1-loop25:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP25
  description: "trend531 + min_ob_strength 0.5 + bounce_confirm 1 (safer entries)"
  magic_number: 206842
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  min_ob_strength: 0.5
  bounce_close_confirm_bars: 1

v11-btc1-loop26:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP26
  description: "trend531 + min_ob_strength 0.5 + htf_net_push true (combined)"
  magic_number: 206843
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  min_ob_strength: 0.5
  enable_htf_net_push_filter: true

v11-btc1-loop27:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP27
  description: "trend531 + sl_buffer 0.2 + bad_bounce 0.20-0.26 (modest improvements)"
  magic_number: 206844
  bad_bounce_min_pct: 0.20
  bad_bounce_max_pct: 0.26
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  sl_buffer_atr: 0.2
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Added 5 loop variants (loop23-27)")

