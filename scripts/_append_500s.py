from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-trend500:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND500
  description: "trend218 + cap_loss_hours 3,4,5,10,12 - covers 2025-11 h12 + 2026-01 h10"
  magic_number: 206500
  btc_cap_loss_hours: "3,4,5,10,12"

v11-btc1-trend501:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND501
  description: "trend218 + btc_cap_loss_r=-0.5"
  magic_number: 206501
  btc_cap_loss_r: -0.5

v11-btc1-trend502:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND502
  description: "trend218 + cap_loss h=3,4,5,10,12,15 r=-0.4"
  magic_number: 206502
  btc_cap_loss_r: -0.4
  btc_cap_loss_hours: "3,4,5,10,12,15"

v11-btc1-trend503:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND503
  description: "trend218 + DTP 1.8/0.25"
  magic_number: 206503
  btc_dtp_trigger_r: 1.8
  btc_dtp_retrace: 0.25

v11-btc1-trend504:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND504
  description: "trend218 + DTP 1.5/0.20"
  magic_number: 206504
  btc_dtp_trigger_r: 1.5
  btc_dtp_retrace: 0.2

v11-btc1-trend505:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND505
  description: "trend218 + entry_depth 0.7 + DTP 1.5/0.20"
  magic_number: 206505
  entry_depth_pct: 0.7
  btc_dtp_trigger_r: 1.5
  btc_dtp_retrace: 0.2

v11-btc1-trend506:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND506
  description: "trend218 + cap_loss r=-0.4 + monthly_defensive 5pct"
  magic_number: 206506
  btc_cap_loss_r: -0.4
  monthly_defensive_max_month_start_balance: 99999.0
  monthly_defensive_min_trades: 5
  monthly_defensive_loss_pct: 5.0
  monthly_defensive_until_profit_pct: 3.0
  monthly_defensive_no_entry_hours: ""
  monthly_defensive_pos_mult: 0.4

v11-btc1-trend507:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND507
  description: "trend218 + cap_loss h=3,4,5,10,12 + DTP 1.5/0.20"
  magic_number: 206507
  btc_cap_loss_hours: "3,4,5,10,12"
  btc_dtp_trigger_r: 1.5
  btc_dtp_retrace: 0.2

v11-btc1-trend508:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND508
  description: "trend218 + cap_loss h=3,4,5,11,12,13"
  magic_number: 206508
  btc_cap_loss_hours: "3,4,5,11,12,13"

v11-btc1-trend509:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND509
  description: "trend218 + cap_loss h=3,4,5,10,12 + cap_loss_days=5"
  magic_number: 206509
  btc_cap_loss_hours: "3,4,5,10,12"
  btc_cap_loss_days: "5"
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Appended 10 strategies")

