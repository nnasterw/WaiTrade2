# 2026-05-30 XAU ZD + New QS Live Deploy

## Scope

- ZD leg: `v11xau-zd`, magic `204800`, unchanged.
- QS leg: `v11xau-qs-highprice-lowbal-obvsl-body45-reentry3-pos100-250`, magic `205005`.
- Symbol: `XAUUSDm`.
- Live portable roots:
  - `temp/mt5_portable_xau_zd_qs/ZD`
  - `temp/mt5_portable_xau_zd_qs/QS`

## QS defense logic

The new QS leg is a live-visible high-price low-balance defense patch, not a month filter:

- enable only when current price is at least `4350` and account balance is at most `250`;
- require OB body close confirmation with at least `45%` body;
- use 1-bar M1 virtual stop confirmation;
- limit same-OB entries to 3;
- add 5-minute same-OB re-entry cooldown;
- reject outside confirmations with `confirm_pos > 1.0`.

## Validation

- `python -m pytest tests\test_mt5_common.py tests\test_mt5_compile_win.py -q`: `93 passed`.
- Isolated compile: `WaiTrade_OB.mq5`, `PortfolioSetup.mq5`, and `ClearSharedMonthlyGuard.mq5` compiled with `0 errors / 0 warnings`.
- Portable QS compile: `temp/compile_xau_live_newqs_QS`, `0 errors / 0 warnings`.
- Portable ZD compile: `temp/compile_xau_live_newqs_ZD`, `0 errors / 0 warnings`.
- Generated profile audit: `results/live/v11xau_live_zd_qs_newqs_profile_audit_20260530.md`, `pass=true`.

## Deploy Evidence

`temp/mt5_portable_xau_zd_qs/QS/MQL5/Presets/v11xau_live_QS.set`:

- `InpVersion=V11XAU-QS-HIGHPRICE-LOWBAL-OBVSL-BODY45-REENTRY3-POS100-250`
- `InpMagicNumber=205005`
- `InpDefensiveConfirmMaxBalance=250.0`
- `InpDefensiveConfirmMinPrice=4350.0`
- `InpDefensiveBounceCloseConfirmBars=1`
- `InpDefensiveMaxEntriesPerOB=3`
- `InpDefensiveOBReentryCooldownMin=5`
- `InpDefensiveShallowConfirmPosMin=1.0`
- `InpDefensiveShallowConfirmPosMult=0.0`
- `InpDefensiveVirtualSLConfirmBars=1`

`temp/mt5_portable_xau_zd_qs/ZD/MQL5/Presets/v11xau_live_ZD.set`:

- `InpVersion=V11XAU-ZD`
- `InpMagicNumber=204800`

Both XAU portable terminals were restarted from their existing startup INI files after set and EA synchronization.
