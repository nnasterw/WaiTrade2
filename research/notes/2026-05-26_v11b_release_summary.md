# v11b Release Summary

Date: 2026-05-26

## Current status

`v11b` is the promoted single-BTC strategy derived from `v11_r248_j2_r243_oct_ctx4`.

The core result is:

- 720d BTCUSDm, 2024.06.06-2026.05.26, $200 start: 3727 trades, 5.2/day, 42.2% win rate, PF 1.62, final balance $137351.62.
- 60d BTCUSDm, 2026.03.27-2026.05.26, $200 start: 291 trades, 4.8/day, 37.5% win rate, PF 1.31, final balance $871.08.
- 30d new-account start is weak: 46 trades, final balance $186.82.
- 30d high-balance continuation is positive: 150 trades, final balance $125896.70 from $125228.10.

Interpretation: v11b is a BTC-focused strategy with strong long-run sample performance, but it is balance/path dependent. It should not be treated as a guaranteed new-account 30d performer.

## Strategy key

- `config/strategies.yaml`: `v11b`
- Parent: `v11_r248_j2_r243_oct_ctx4`
- Version: `V11B`
- Magic number: `204408`

## Core implementation

- `mql5/Include/WaiTrade2/Config.mqh`
- `mql5/Include/WaiTrade2/SignalEngine.mqh`
- `scripts/yaml_to_set.py`

The main v11b-specific enabler is additional context filter capacity (`context_filter4/5`) so October high-balance protection can be added without replacing the existing May protection.

## Backtest and audit files

- `results/backtest/v11_r248_j2_r243_oct_ctx4_20240606_20260526_20260526.txt`
- `results/backtest/v11_r248_j2_r243_oct_ctx4_20240606_20260526_20260526.md`
- `results/backtest/v11b_20260426_20260526_20260526.txt`
- `results/backtest/v11b_20260426_20260526_20260526.md`
- `results/backtest/v11b_20260426_20260526_deposit125228_20260526.txt`
- `results/backtest/v11b_20260426_20260526_deposit125228_20260526.md`
- `results/backtest/v11b_20260327_20260526_20260526.txt`
- `results/backtest/v11b_20260327_20260526_20260526.md`
- `results/backtest/v11b_20240606_20260526_20260526.txt`
- `results/backtest/v11b_20240606_20260526_20260526.md`
- `research/notes/2026-05-26_btc_single_strategy_r234_diagnosis.md`

## Cross-symbol finding

v11b should not be deployed as a universal multi-symbol strategy.

720d same-parameter results:

- BTCUSDm: $137351.62
- XAUUSDm: $39.88
- XAGUSDm: $30.50
- ETHUSDm: $65.26
- USOILm: $147.13
- USDJPYm: $152.17

Non-BTC symbols need their own parameter search and risk model.

## Verification

Command:

```powershell
python -m pytest tests\test_mt5_common.py tests\test_mt5_backtest_isolated_win.py tests\test_mt5_backtest_win.py -q
```

Result: `104 passed`.

Live status after isolated backtests:

- `streams=7 pass=true`
- `total_pos=0`
- `total_errors=0`
- `stale_heartbeats=0`

