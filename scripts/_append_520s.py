from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")

new_entries = """
v11-btc1-trend520:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND520
  description: "trend218 + cap_loss h=3,4,5,10,12 + max_lot=1.0 (fix trend500 max_lot bug)"
  magic_number: 206520
  btc_cap_loss_hours: "3,4,5,10,12"
  max_lot_size: 1.0

v11-btc1-trend521:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND521
  description: "trend218 + monthly_profit_target_stop 10pct (防 2026-05 集中损失)"
  magic_number: 206521
  btc_allow_monthly_profit_target_stop: true
  monthly_profit_target_stop_pct: 10.0
  monthly_profit_target_stop_min_balance: 1000.0
  monthly_profit_target_stop2_pct: 25.0
  monthly_profit_target_stop2_min_balance: 5000.0
  max_lot_size: 1.0

v11-btc1-trend522:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND522
  description: "trend218 + cap_loss h=3,4,5,10,12,13,15,20,21,22 (全时段, 防 2026-05)"
  magic_number: 206522
  btc_cap_loss_hours: "3,4,5,10,12,13,15,20,21,22"
  btc_cap_loss_r: -0.5
  max_lot_size: 1.0

v11-btc1-trend523:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND523
  description: "trend218 + cap_loss h=3,4,5,10,12 + monthly_defensive 5pct (双重防)"
  magic_number: 206523
  btc_cap_loss_hours: "3,4,5,10,12"
  btc_cap_loss_r: -0.4
  max_lot_size: 1.0
  monthly_defensive_max_month_start_balance: 99999.0
  monthly_defensive_min_trades: 5
  monthly_defensive_loss_pct: 5.0
  monthly_defensive_until_profit_pct: 3.0
  monthly_defensive_no_entry_hours: ""
  monthly_defensive_pos_mult: 0.4

v11-btc1-trend524:
  <<: *v11_btc1_qual232
  version: V11-BTC1-TREND524
  description: "trend218 + cap_loss h=3,4,5,10,12 + DTP 1.5/0.20 + max_lot 1.0"
  magic_number: 206524
  btc_cap_loss_hours: "3,4,5,10,12"
  btc_dtp_trigger_r: 1.5
  btc_dtp_retrace: 0.2
  max_lot_size: 1.0
"""

with open(yaml_path, "a", encoding="utf-8") as f:
    f.write(new_entries)
print("Appended 5 strategies (520-524)")

