# 2026-05-27 v11a R264-R269 March add-on probe

## Feedback loop

Objective: improve `v11btc_mix_r261_apr_addons` without regression while reducing
35% monthly return shortfall.

Fast proxy loop:

- Use month-gated CSV replay against `v11btc_mix_r261_apr_addons`.
- Accept only rows with both `profit_delta > 0` and `shortfall_delta > 0`.
- Reject rows where shortfall improves only because the candidate loses money and
  lowers later month-start balances.

Real loop:

- Convert selected candidates into deployable `entry_months: "3"` MT5 strategies.
- Run MT5 Strategy Tester Real Ticks over 2024-06-06 to 2026-05-26.
- Export `trades.csv` with `backtest_digest.py`.
- Re-run portfolio path simulation with the real exported CSV.

## Proxy candidates

The best positive March-only proxy rows were small:

| source | proxy profit_delta | proxy shortfall_delta |
|---|---:|---:|
| R39 March-only | 1076.22 | 322.86 |
| R167 March-only | 285.07 | 85.52 |
| R35 March-only | 196.64 | 58.99 |
| R174 March-only | 171.80 | 51.54 |
| R104 March-only | 116.97 | 35.09 |
| R195 March-only | 63.95 | 19.18 |

January-only and February-only rows with larger shortfall improvement were mostly
false positives: they reduced future target lines by losing money, so they were
not aligned with the compounding objective.

## Real Ticks result

Two representative March-only legs were validated sequentially. Do not trust the
earlier parallel tester outputs for R265/R266 because Windows Strategy Tester uses
a shared `backtest.ini`, and those runs returned suspicious 2-second cached-looking
results.

| strategy | trades | win_rate | pf | balance |
|---|---:|---:|---:|---:|
| `v11_r264_j2_r39_march_only_shared` | 52 | 44.2% | 1.78 | 238.56 |
| `v11_r267_j2_r174_march_only_shared` | 96 | 45.8% | 1.26 | 290.42 |

Portfolio replay with real CSVs:

| add-on | total | final | bad_months | below_35 | shortfall_delta | profit_delta |
|---|---:|---:|---:|---:|---:|---:|
| R264M | 464359.90 | 464559.90 | 0 | 18 | 13.60 | 45.34 |
| R267M | 464420.94 | 464620.94 | 0 | 18 | 31.91 | 106.38 |
| R264M+R267M | 464466.28 | 464666.28 | 0 | 18 | 45.52 | 151.72 |

## Decision

March-only add-ons are valid but too small. They do not materially move the 35%
monthly objective and are not worth adding to the official candidate schedule yet.

Next search should target a genuinely independent May/March signal source or a
guard design that raises low-return months without merely increasing target-line
drag in later months.
