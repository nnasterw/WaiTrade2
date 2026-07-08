"""loop33-36: trend531 + enable_btc + BigWinLock variations"""
from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-loop33:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP33
  description: "trend531 + enable_btc + BigWinLock 2.0/1.0 (aggressive lock)"
  magic_number: 206860
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: true
  btc_big_win_trigger_r: 2.0
  btc_big_win_lock_to_r: 1.0

v11-btc1-loop34:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP34
  description: "trend531 + enable_btc + BigWinLock 2.5/1.5 no_htf_filter"
  magic_number: 206861
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: true
  btc_big_win_trigger_r: 2.5
  btc_big_win_lock_to_r: 1.5
  btc_big_win_only_htf_target: false

v11-btc1-loop35:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP35
  description: "trend531 + enable_btc + BigWinLock 1.8/1.0 + MonthlyGuard -1.5"
  magic_number: 206862
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: true
  btc_big_win_trigger_r: 1.8
  btc_big_win_lock_to_r: 1.0
  btc_big_win_only_htf_target: false
  btc_enable_monthly_loss_guard: true
  btc_monthly_loss_guard_r: -1.5
  btc_monthly_loss_guard_only_htf_target: false

v11-btc1-loop36:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP36
  description: "trend531 + enable_btc + BigWinLock 2.0/1.0 + bad_bounce 0.20-0.26 (combined)"
  magic_number: 206863
  bad_bounce_min_pct: 0.20
  bad_bounce_max_pct: 0.26
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: true
  btc_big_win_trigger_r: 2.0
  btc_big_win_lock_to_r: 1.0
  btc_big_win_only_htf_target: false
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Added 4 loop variants (loop33-36)")

