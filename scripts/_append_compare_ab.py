from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-yhcl1:
  <<: *v11_btc1_qual232
  version: V11-BTC1-YHCL1
  description: "yhcl multi-var: cap_loss h=3,4,5,10 + bad_bounce 0.22-0.28"
  magic_number: 207001
  btc_cap_loss_hours: "3,4,5,10"
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0

v11-btc1-yhcl2:
  <<: *v11_btc1_qual232
  version: V11-BTC1-YHCL2
  description: "yhcl multi-var: yhcl1 + DTP 1.5/0.2 + monthly_defensive 5pct"
  magic_number: 207002
  btc_cap_loss_hours: "3,4,5,10"
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  btc_dtp_trigger_r: 1.5
  btc_dtp_retrace: 0.2
  monthly_defensive_loss_pct: 5.0
  monthly_defensive_pos_mult: 0.4
  max_lot_size: 1.0

v11-btc1-loop1:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP1
  description: "loop single-var: bad_bounce 0.22-0.26 (from 0.28 tighter)"
  magic_number: 207101
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.26
  bad_bounce_mult: 0.4
  max_lot_size: 1.0

v11-btc1-loop2:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP2
  description: "loop single-var: bad_bounce mult 0.5 (from 0.4)"
  magic_number: 207102
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.5
  max_lot_size: 1.0
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Appended 4 AB-test strategies (yhcl1-2, loop1-2)")

