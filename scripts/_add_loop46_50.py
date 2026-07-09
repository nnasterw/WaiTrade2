import sys
from pathlib import Path
yaml_path = Path('D:/Code/codexProject/WaiTrade2/config/strategies.yaml')
content = yaml_path.read_text(encoding='utf-8')
if 'v11-btc1-loop46:' in content:
    print('Already added')
    sys.exit(0)
new_entries = chr(10) + """
v11-btc1-loop46:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP46
  description: "BV1 + bounce_pct 0.30 + min_risk_spread_ratio 3.0 - more signals via lower filter"
  magic_number: 207100
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  bounce_pct: 0.30
  min_risk_spread_ratio: 3.0

v11-btc1-loop47:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP47
  description: "BV1 + entry_depth 0.5 + bounce_close_confirm 1 - looser OB + K-line confirmation"
  magic_number: 207101
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  entry_depth_pct: 0.5
  bounce_close_confirm_bars: 1

v11-btc1-loop48:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP48
  description: "BV1 + min_ob_strength 0.3 + min_impulse 50 - lower OB bar requirements"
  magic_number: 207102
  bad_bounce_min_pct: 0.22
  bad_bounce_max_pct: 0.28
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  min_ob_strength: 0.3
  min_impulse_body_pct: 50

v11-btc1-loop49:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP49
  description: "BV1 + enable FVG + MicroBOS - multi signal family for more entries"
  magic_number: 207103
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
  enable_micro_bos_retest: true
  bounce_close_confirm_bars: 1

v11-btc1-loop50:
  <<: *v11_btc1_qual232
  version: V11-BTC1-LOOP50
  description: "BV1 + FVG+MicroBOS+low OB+low bounce+low risk_spread - max frequency combo"
  magic_number: 207104
  bad_bounce_min_pct: 0.20
  bad_bounce_max_pct: 0.26
  bad_bounce_mult: 0.4
  max_lot_size: 1.0
  enable_btc_profile: false
  smart_lock_enable: true
  smart_lock_trigger_r: 1.8
  smart_lock_pct: 0.5
  entry_depth_pct: 0.5
  min_ob_strength: 0.3
  min_impulse_body_pct: 50
  enable_fvg: true
  fvg_min_gap_atr: 0.05
  enable_micro_bos_retest: true
  bounce_pct: 0.28
  min_risk_spread_ratio: 3.0
"""
with yaml_path.open('a', encoding='utf-8') as f:
    f.write(new_entries)
print('Added loop46-50')