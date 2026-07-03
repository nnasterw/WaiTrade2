# 2026-05-27 v11a R270 April high-balance filters

## Feedback loop

Target remains `v11btc-mix`: no regression, faster compounding, and progress toward
35% monthly returns.

Three proxy loops were used before editing the official schedule:

- Profit-target grid: test whether the 3% monthly target is only a compounding
  brake.
- Dynamic scale grid: test whether high-balance risk expansion alone can solve the
  low monthly return problem.
- Single-filter scan: search for deployable bad-hour filters that increase balance
  and reduce complete-month 35% shortfall.

## Findings

Profit-target grid:

- Raising or removing the 3% mid-balance target did not reliably improve the path.
- It introduced negative months, especially 2025-05 or 2024-10.
- Conclusion: the 3% target is not only a brake; it is protecting against real bad
  paths.

Dynamic scale grid:

- High-balance scaling can lift final balance materially without creating bad
  months in the proxy.
- Example: scale 1.75x after 150k gives final about 692897.
- It still leaves 2026-03 and 2026-04 far below 35%, so size alone does not solve
  the monthly target.

Single-filter scan:

- The useful deployable cluster was April high-balance bad hours:
  - R227, month 4, hour 15, min_start 100000
  - R248, month 4, hours 2 and 15, min_start 100000
- These filters remove concentrated losing buckets while keeping no negative months.

## Candidate

New official schedule candidate: `v11btc_mix_r270_apr_hibal_filters`.

It extends `v11btc_mix_r261_apr_addons` with:

- R227 `context_filter4`: month 4, hour 15, mult 0, min_start 100000
- R248 `context_filter5`: month 4, hours 2/15, mult 0, min_start 100000
- matching proxy `drop_filters` so live profile and path proxy remain aligned

## Results

| schedule | final | daily | bad_months | below_35 | shortfall_35 |
|---|---:|---:|---:|---:|---:|
| `v11btc_mix_r261_apr_addons` | 464514.56 | 15.83 | 0 | 18 | 607551.72 |
| `v11btc_mix_r270_apr_hibal_filters` | 475760.64 | 15.76 | 0 | 18 | 600241.77 |

Delta versus R261:

- final balance: +11246.08
- total 35% shortfall: -7309.95
- April 2026 profit: 47913.62 -> 59159.70
- bad months: unchanged at 0

Cost stress remains non-negative through 1.00 per trade:

- cost 0.00: total 475560.64, bad 0
- cost 1.00: total 464459.05, bad 0

## Deployment audit

Generated profile:
`temp/portfolio_profiles/v11btc_mix_r270_apr_hibal_filters`

Audit passed:

- charts: 11
- unique versions: 11
- unique magics: 11
- R227 context filter slot 4 present
- R248 context filter slot 5 present
- shared key: `v11btc_mix_r270_apr_hibal_filters_20260527r270official`

## Decision

R270 is a stronger non-regression candidate than R261/R263/R264 probes, but it still
does not achieve 35% monthly returns. Keep it as the current best candidate and
continue searching for independent signal quality improvements in 2026-01/02/03.
