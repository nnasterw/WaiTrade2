# 2026-05-27 v11a R261-R263 April add-ons

## Context

Core target remains v11a/v11btc-mix non-regression while compounding faster toward a
35% monthly return target. The current accepted candidate before this round was
`v11btc_mix_r248`, with no negative months but 18/24 months still below 35%.

Live was intentionally left stopped so MT5 Strategy Tester runs can proceed without
interference.

## Search loop

- Full `portfolio_shortfall_scan.py` over the whole MT5 CSV pool timed out at 120s.
- A fast raw CSV screen was used only as a triage layer for weak 2026-03/04/05 months.
- April-only candidates from the R105/R106/R107 family looked useful in path replay,
  but older all-window CSV slicing is not deployable, so each candidate was converted
  into a real MT5 strategy with `entry_months: "4"`.

## Real Ticks validation

All three legs were run with MT5 Strategy Tester Real Ticks over 2024-06-06 to
2026-05-26, then exported with `backtest_digest.py`.

| strategy | trades | win_rate | pf | balance |
|---|---:|---:|---:|---:|
| `v11_r261_j2_r106_april_only_shared` | 176 | 38.6% | 1.48 | 980.72 |
| `v11_r262_j2_r107_april_only_shared` | 172 | 39.0% | 1.37 | 886.70 |
| `v11_r263_j2_r105_april_only_shared` | 159 | 39.0% | 1.36 | 883.05 |

## Portfolio result

New schedule candidate: `v11btc_mix_r261_apr_addons`.

It keeps the full `v11btc_mix_r248` guard/drop-filter surface and adds R261/R262/R263
as April-only shared-guard legs.

| schedule | final | daily | bad_months | below_35 | shortfall |
|---|---:|---:|---:|---:|---:|
| `v11btc_mix_r248` | 462303.52 | 15.24 | 0 | 18 | 608988.89 |
| `v11btc_mix_r261_apr_addons` | 464514.56 | 15.83 | 0 | 18 | 607551.72 |

Delta versus R248:

- final balance: +2211.04
- 35% total shortfall: -1437.18
- bad months: unchanged at 0
- weakest target month remains 2026-05 at 1.25%

Cost stress remained non-negative through 1.00 per trade:

- cost 0.00: total 464314.56, bad 0
- cost 1.00: total 453165.97, bad 0

## Deployment audit

Generated profile:
`temp/portfolio_profiles/v11btc_mix_r261_apr_addons`

Audit passed:

- charts: 11
- unique versions: 11
- unique magics: 11
- shared key: `v11btc_mix_r261_apr_addons_20260527r261apr`

## Decision

This is a valid non-regression improvement candidate, but it does not solve the
35% monthly target. Adopt only as an incremental April balance add-on candidate;
continue searching for larger independent legs in 2026-01/02/03/05 where the
shortfall dominates.
