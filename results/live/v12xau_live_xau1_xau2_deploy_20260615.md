# 2026-06-15 V12 XAU1 + XAU2 Live Deploy

## Scope

- XAU1: `v12xau1`, BD07 live-safe alias, `InpVersion=V12XAU1`, `Magic=212001`.
- XAU2: `v12xau2`, `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock3_20_fail_pos05_2_60_noclear` live-safe alias, `InpVersion=V12XAU2`, `Magic=212002`.
- Symbol/TF: `XAUUSDm` M1.
- Account: Exness-MT5Trial5 `277656700`.
- Portable roots:
  - `temp/mt5_portable_xau_v12/XAU1`
  - `temp/mt5_portable_xau_v12/XAU2`

## Live-Safe Overrides

The research candidate used aggressive sizing (`risk=8`, `max_lot=5`). Live presets were capped for the $200 account safety boundary:

- `max_lot_size=0.1`
- `max_concurrent=5`
- `max_entries_per_ob=5`
- `ob_reentry_cooldown_min=3`
- `cooldown_bars=1`
- XAU2 `risk_percent=3.0`

Both presets have `InpEnableEntryDebug=true`.

## Validation

- `python scripts/check_strategy_consistency.py v12xau1 --brief`: ERROR 0 / WARN 0.
- `python scripts/check_strategy_consistency.py v12xau2 --brief`: ERROR 0 / WARN 0.
- `python -m pytest tests/test_mt5_common.py -q`: 94 passed.
- `python scripts/compile_and_deploy.py --mode portable`: 0 errors / 0 warnings; `WaiTrade_OB.ex5` deployed.

## Deploy Evidence

- XAU1 terminal log: 732 inputs read from `MQL5\Presets\v12xau1.set`; `WaiTrade_OB (XAUUSDm,M1) loaded successfully`.
- XAU1 Expert log: `WaiTrade2 V12XAU1 | XAUUSDm | Magic=212001`; heartbeat on `PERIOD_M1`.
- XAU2 terminal log: 742 inputs read from `MQL5\Presets\v12xau2.set`; `WaiTrade_OB (XAUUSDm,M1) loaded successfully`.
- XAU2 Expert log: `WaiTrade2 V12XAU2 | XAUUSDm | Magic=212002`; heartbeat on `PERIOD_M1`.
