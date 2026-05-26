# Strategy Iteration Handoff

Date: 2026-05-26

## Start here

Current promoted BTC strategy:

- Strategy key: `v11b`
- Parent strategy: `v11_r248_j2_r243_oct_ctx4`
- Version string: `V11B`
- Magic number: `204408`
- Main config: `config/strategies.yaml`
- Summary: `research/notes/2026-05-26_v11b_release_summary.md`
- Full diagnosis log: `research/notes/2026-05-26_btc_single_strategy_r234_diagnosis.md`

`v11b` is a BTCUSDm-focused strategy. Do not treat it as a universal multi-symbol strategy.

## Known baseline

MT5 Strategy Tester CLI, Real Ticks, $200 initial deposit:

| Window | Symbol | Trades | Daily | Win rate | PF | Final balance |
|---|---|---:|---:|---:|---:|---:|
| 720d, 2024.06.06-2026.05.26 | BTCUSDm | 3727 | 5.2 | 42.2% | 1.62 | $137351.62 |
| 60d, 2026.03.27-2026.05.26 | BTCUSDm | 291 | 4.8 | 37.5% | 1.31 | $871.08 |
| 30d, 2026.04.26-2026.05.26, new $200 start | BTCUSDm | 46 | 1.5 | 32.6% | 0.51 | $186.82 |
| 30d, 2026.04.26-2026.05.26, high-balance continuation | BTCUSDm | 150 | 5.0 | 45.3% | 0.57 | $125896.70 |

Important caveat: v11b is path and balance dependent. The 720d result is strong, but the 30d new-account start is weak.

## Key files

Strategy and parameter mapping:

- `config/strategies.yaml`
- `scripts/yaml_to_set.py`
- `mql5/Include/WaiTrade2/Config.mqh`
- `mql5/Include/WaiTrade2/SignalEngine.mqh`

EA logic touched by the current strategy line:

- `mql5/Experts/WaiTrade2/WaiTrade_OB.mq5`
- `mql5/Include/WaiTrade2/EntryEngine.mqh`
- `mql5/Include/WaiTrade2/OBDetector.mqh`
- `mql5/Include/WaiTrade2/PositionManager.mqh`
- `mql5/Include/WaiTrade2/Types.mqh`

Safe Windows isolated backtest runner:

- `scripts/mt5_backtest_isolated_win.py`
- `tests/test_mt5_backtest_isolated_win.py`

## Safe backtest workflow

Use the isolated tester wrapper whenever live is running:

```powershell
python scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated -- --strategy v11b --symbol BTCUSDm --days 60 --timeout 2400
```

For 720d BTC validation:

```powershell
python scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated -- --strategy v11b --symbol BTCUSDm --from 2024.06.06 --to 2026.05.26 --timeout 5400
```

For cross-symbol probing:

```powershell
python scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated -- --strategy v11b --symbols BTCUSDm,XAUUSDm,XAGUSDm,ETHUSDm,USOILm,USDJPYm --days 60 --timeout 2400
```

The wrapper runs live status checks before and after the backtest. It refuses to use the v11a live portable directory as tester home.

## Digest workflow

After each MT5 Strategy Tester run, create digest output instead of reading raw Agent logs:

```powershell
python scripts\backtest_digest.py --report results\backtest\<report>.txt --log temp\mt5_tester_isolated\Tester\Agent-127.0.0.1-3000\logs\20260526.log --export-csv
```

Use the `.md` digest for normal review. Open the `.trades.csv` only when diagnosing a specific month, hour, signal type, or bad cluster.

## Next useful iteration targets

1. Low-balance startup repair

   The 30d new-account start is weak. Improve startup behavior without damaging the 720d result. Test both:

   - 30d from $200
   - 720d from $200

2. Robustness around thin positive months

   R248/v11b solved all monthly losses in the 720d sample, but the margin is thin:

   - 2025-03: about +$0.66
   - 2025-05: about +$20.12

   Do not count a variant as safer unless these months remain positive after perturbation.

3. Cross-symbol strategy split

   Same-parameter v11b is not suitable for XAU/XAG/ETH/USOIL/JPY. If expanding symbols, create separate strategy families and parameter matrices.

## Validation checklist before promoting a new variant

Run:

```powershell
python -m pytest tests\test_mt5_common.py tests\test_mt5_backtest_isolated_win.py tests\test_mt5_backtest_win.py -q
python scripts\yaml_to_set.py <strategy> | Select-String -Pattern "InpVersion|InpMagicNumber|InpContextFilter"
```

Then run:

```powershell
python scripts\portfolio_live_status.py --since-hours 24 --max-heartbeat-age-min 75 --output results\live\<status_file>.md
```

Required checks:

- `streams=7 pass=true` if v11a live is running.
- `total_errors=0`.
- `stale_heartbeats=0`.
- No `terminal64.exe` or `metatester64.exe` remains from the isolated tester after the backtest.

## Recording discipline

Every completed investigation should update or add a note under `research/notes/`.

Minimum contents:

- Strategy key and parent.
- Exact MT5 command.
- Date window and initial deposit.
- Trades, daily trades, win rate, PF, final balance.
- Monthly negative count.
- Main conclusion and next action.

Do not commit `temp/`, raw MT5 logs, generated tester homes, or large bulk result files.

