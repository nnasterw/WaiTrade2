# 2026-05-23 V11 Round116-118: R32 regime and monthly feedback tests

Latest status as of 2026-05-25:
- Active objective: BTC 720d Real Ticks / proxy portfolio, daily trades `>4`, profit `>90000u`, and every month profitable.
- Current best proxy schedule: `r186_r196_r212_r211_r213_r216_guard`.
- Latest preflight: `results/backtest/portfolio_r186_r196_r212_r211_r213_r216_guard_may_h6_preflight_compile_20260525.md`, pass with compile.
- Metrics: total `231278.42`, daily `7.04`, bad months `0`; fixed-cost `1.00/entry` keeps bad months `0`.
- Profile audit now explicitly reports `sweep_months=3,5` and `sweep_no_hours=0,1,6,23` on all 6 installed charts.
- Remaining proof gap: still a CSV path-level portfolio proxy plus dry-run profile/preflight, not a true MT5 multi-stream same-account 720d Strategy Tester run.
- Latest weak-month diagnosis: 2026-05 is the weakest month. Detail attribution is saved at `results/backtest/portfolio_r186_r196_r212_r211_r213_r216_guard_2026_05_attribution_detail_20260525.md`.
- May candidate scan is saved at `results/backtest/portfolio_candidate_scan_2026_05_20260525.md`; no full-window candidate materially improves May beyond the existing R186/R196 sweep winner, so do not add another May leg without stronger MT5 evidence.
- Incremental low-overlap scan is saved at `results/backtest/portfolio_incremental_scan_low_overlap_r186_r196_r212_r211_r213_r216_guard_20260525.md`.
- Best new proxy direction: resurrect low-overlap R55-family leg with source-specific high-balance bad-hour filters. Probe result is `292633.03u`, daily `7.65`, bad months `0`, cost `1.00/entry` bad months `0`; saved at `results/backtest/portfolio_r186_r196_r212_r211_r213_r216_r55_probe_proxy_20260525.md` and `_stress_20260525.md`. This is not yet MT5-valid because it uses CSV/source-level filters and an older candidate export.

Historical note for this round: the earlier working target was daily trades `>8`, balance `>$80k`, and every month profitable.

Current best unchanged:

| Strategy | Trades | Daily | Win | PF | Balance | Losing months |
|---|---:|---:|---:|---:|---:|---:|
| `v11_r107_j2_r105_mloss8` | 3197 | 4.4 | 42.0% | 1.37 | $63815.35 | 8 |

## Round116: R32 high-frequency frame with survival guards

Hypothesis: R32 is profitable in the 2025-2026 regime and fails 720d because it lacks early survival controls. Adding R107 low-balance/monthly guards might keep the high-frequency profile while surviving 2024.

| Strategy | 720d trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r116_j2_r32_survive` | N/A | N/A | N/A | N/A | timeout/no report | invalid result |
| `v11_r116_j2_r32_survive_swp16` | 2482 | 3.4 | 43.2% | 1.24 | $36211.36 | survival + sweep 16/18 cut is too restrictive |
| `v11_r116_j2_r32_survive_badcluster` | 3086 | 4.3 | 41.8% | 1.13 | $55355.23 | bad-cluster protects, but still below R107 |

Conclusion: R32 is not a clean low-correlation add-on. Its strong 365d result is regime-dependent; when made survivable over 720d, it converges below R107.

## Existing-candidate combination scan

I scanned existing `*.trades.csv` files against R107 losing months. No candidate with full coverage had positive total PnL across all R107 losing months. The best candidates merely lost less, and most shared the same 2026-01/03/05 drawdown exposure.

Conclusion: simple portfolioing of existing variants is unlikely to satisfy monthly profitability. The candidates are highly correlated to the same BTC regime risk.

## Round117: stronger monthly-negative feedback

Hypothesis: R107 still loses too much after the month turns negative. Lowering `monthly_negative_pos_mult` might reduce high-balance monthly drawdown.

| Strategy | 720d trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r117_j2_r107_mneg040` | N/A | N/A | N/A | N/A | timeout/no report | invalid result |
| `v11_r117_j2_r107_mneg020` | 2945 | 4.1 | 42.0% | 1.16 | $57615.39 | lower drawdown but cuts recovery/right tail |
| `v11_r117_j2_r107_mneg_cut` | 2032 | 2.8 | 43.0% | 1.26 | $42320.43 | converts big losses to small losses, but locks strategy out |

Conclusion: month-negative stop/soft-stop triggers too late. It can reduce 2026 losses, but it cannot make months profitable and damages compounding.

## Round118: monthly warmup risk

Code change: added `InpMonthlyWarmupProfitPct` and `InpMonthlyWarmupPosMult`. While current month profit is below the configured percentage of month-start balance, entries use the warmup multiplier. YAML and tests were synced.

Hypothesis: month-start low-risk mode could avoid early monthly damage before full-size trading resumes.

| Strategy | 720d trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r118_j2_r107_warm1_m50` | 2978 | 4.1 | 41.9% | 1.19 | $58725.08 | protects early month but cuts right tail |
| `v11_r118_j2_r107_warm1_m30` | 2988 | 4.2 | 42.0% | 1.17 | $58633.16 | stronger warmup is not better |
| `v11_r118_j2_r107_warm2_m50` | N/A | N/A | N/A | N/A | timeout/no report | invalid result |

Conclusion: monthly warmup is not enough. It reduces exposure before monthly profit is established, but the same reduction also suppresses the 2025H2 compounding that makes R107 strong.

## Current direction

Static hour filters, loose sweep add-ons, existing-variant portfolioing, monthly-negative stops, and monthly warmup all failed to beat R107. The next promising direction should be a genuinely new, low-correlated signal source or a dynamic regime classifier that can distinguish 2025H2 expansion from 2026 drawdown regimes before losses appear.

## 2026-05 weak-month attribution

After the May high-balance sweep-hour guard, schedule `r186_r196_r212_r211_r213_r216_guard` keeps May positive but thin:

| Cost per entry | 2026-05 profit | Bad months |
|---:|---:|---:|
| 0.00 | 7.21 | 0 |
| 0.50 | 6.21 | 0 |
| 1.00 | 5.21 | 0 |

Per-trade attribution shows the guard removes only the 2026-05-01 06:48 double sweep loser and keeps the 07:31 double sweep winner:

| Time | Source | Signal | Action | PnL |
|---|---|---|---|---:|
| 2026-05-01 06:48:39 | R186/R196 | sweep buy h6 | skip by drop_filter | -0.14 each |
| 2026-05-01 07:31:51 | R186/R196 | sweep buy h7 | execute | +3.61 each |

Candidate scan for 2026-05 confirms the same point: among full-window CSVs, the best May PnL is already the R186/R196/R197/R200 family at `+3.47` before guard; HTF pullback candidates add only `+0.6` to `+2.1` proxy PnL and carry many bad months. Conclusion: May is not currently solved by adding another known leg; further work should seek genuinely low-correlation signal sources, not extra May filters.

## Incremental low-correlation candidate scan

I added `scripts/portfolio_incremental_scan.py` to test candidate CSVs as add-ons to the current best schedule, using the same path-level monthly guards as `portfolio_schedule_runner`. The scanner reports target pass/fail, profit delta, daily-trade delta, candidate coverage, trade count, and overlap against the current base trades. This avoids accepting same-family duplicates such as R197 just because adding a duplicate leg inflates proxy profit.

Low-overlap scan (`max_overlap=0.05`, `min_covered_months=20`) shows:

| Candidate class | Result | Diagnosis |
|---|---|---|
| HTF pullback micro/no13 variants | Pass, but only `+24u` to `+53u` delta | Low risk, too small to matter |
| R39/R55/R61 G-family | Large delta, but fails months | Promising only if bad clusters can be filtered |
| R197/R183-style duplicates | Large apparent delta in unfiltered scan | Too correlated / same-family; do not treat as a new edge |

Bad-cluster diagnosis on R55/R39/R61:
- R55/R61 fail 2026-03 mainly on high-balance sell hour `0/1/8`.
- R39/R55/R61 fail 2026-05 mainly on high-balance buy hour `13/20/21/22` and sell hour `0/10/11/19/23`.
- R55 also reintroduced 2024-11 low-balance hour risk once added to the path; source-specific November hour filtering was needed because the old export lacks `signal_type`.

Probe schedule `r186_r196_r212_r211_r213_r216_r55_probe` with source-specific filters:
- Add R55 candidate `v11_r55_j2_g50_m05_t12_20240601_20260522_20260522.trades.csv`.
- Drop R55P in 2024/2025 November hours `7,13,14,15,18,22` while month-start balance <= `25000`.
- Drop R55P high-balance March sell hours `0,1,8`.
- Drop R55P high-balance May buy hours `13,20,21,22` and sell hours `0,10,11,19,23`.

Proxy result:

| Screen | Total | Daily | Bad months | Weakest |
|---|---:|---:|---:|---|
| no cost | `292633.03` | `7.65` | `0` | 2024-11 `+81.46` |
| cost `1.00/entry` | `287203.20` | `7.65` | `0` | 2024-11 `+64.24` |

Conclusion: the best next experimental branch is not another May patch; it is a deployable R55-family strategy variant with those month/hour/balance filters encoded in YAML/EA parameters, followed by MT5 720d Real Ticks validation. Until then this remains a promising CSV proxy only.

## Round119-120: offline bad-cluster replay vs real MT5 path

离线逐单代理回放显示，R107 的少量 OB 尾部坏簇看似有很高杠杆：

| Offline rule | Proxy balance | Proxy losing months | Note |
|---|---:|---:|---|
| filter `ob/hour15/risk400+/cp -1.5~-1.0` | $77818 | 7 | 仅 12 单，但代理收益提升很大 |
| plus filter `ob/hour7,8,9,17/risk100-400/cp<=-0.6` | $91556 | 6 | 离线代理明显过度乐观 |

真实 720d MT5 Real Ticks 回测证伪了 hard cut：

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r119_j2_r107_obtail15_cut` | 2642 | 3.7 | 42.4% | 1.26 | $56292.72 | hard cut 破坏路径，低于 R107 |
| `v11_r119_j2_r107_obtail2_cut` | 2603 | 3.6 | 41.6% | 1.54 | $52034.83 | 过滤更重，进一步损坏复利 |
| `v11_r119_j2_r107_obtail2_soft` | 3198 | 4.4 | 42.4% | 1.42 | $65885.70 | 新阶段冠军，但仍 8 个亏损月 |

R119 soft 的 digest 显示，OB 尾部软降权能小幅提高 PF/余额，但月度问题没有解决；亏损主簇又回到 sweep：`hour15/risk400+/cp<=-1.5`、`hour01/risk200-300/cp -1.5~-1.0`、`hour12/risk150-200/cp<=-1.5`。

Round120 测试较宽 sweep 坏簇 `hour 0,1,2,10,19,20 + risk100-300 + cp<=-1.0`：

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r120_j2_r107_swpbad_soft` | 2729 | 3.8 | 42.4% | 1.20 | $55818.31 | sweep 宽软降权真实路径失败 |
| `v11_r120_j2_r107_swpbad_cut` | 2539 | 3.5 | 42.3% | 1.17 | $55664.39 | hard cut 同样失败 |

结论：

- 离线代理只能用来提假设，不能作为策略优劣依据；hard cut 会改变后续余额、lot、并发和月控路径，真实结果可能反向。
- 当前阶段最好为 `v11_r119_j2_r107_obtail2_soft`，余额 $65885.70，高于 R107 的 $63815.35，但仍不满足目标。
- 继续删/降权现有 R107 信号无法解决日均 >8 和月月盈利；下一步应优先寻找低相关补频信号，或增加真正的入场前 regime classifier，而不是继续堆 bad-cluster。

## Round121: R119 soft + monthly profit lock

R119 soft 的月内曲线显示，部分亏损月属于“先盈利后回吐”：2026-01 曾经月内 +$3.7k 后收成 -$5.1k，2024-09/2025-05 也有类似结构。但 2026-03 和 2026-05 基本从月初就弱，profit lock 无法解决。

离线扫描提示 `monthly_profit_lock_min_balance=60000, start=5%, keep=70%` 可能首次越过 $80k。真实 720d MT5 回测确认该方向有效：

| Strategy | Trades | Daily | Win | PF | Balance | Losing months | Conclusion |
|---|---:|---:|---:|---:|---:|---:|---|
| `v11_r121_j2_r119_lock60_5_70` | 2781 | 3.9 | 42.5% | 1.50 | $83368.47 | 7 | 新阶段冠军，首次超过 $80k |
| `v11_r121_j2_r119_lock30_5_40` | 2386 | 3.3 | 42.9% | 1.26 | $33061.99 | N/A | 过早锁定，破坏 2025H2 复利 |
| `v11_r121_j2_r119_lock0_20_40` | 2887 | 4.0 | 42.2% | 1.39 | $64429.63 | N/A | 防守不足且仍压收益 |

R121 digest:

- 盈利目标已达成：$83368.47 > $80000。
- 交易频率仍不足：2781 单，日均 3.9，距离 >8 很远。
- 月月盈利仍未达成：7 个亏损月。
- Profit lock 成功把 2026-01 从 R119 的 -$5111 改成 +$2556，并把 2026-02 锁成 +$19259；但 2026-03 (-$6872) 和 2026-05 (-$6278) 更突出。

下一步：

- 以 `v11_r121_j2_r119_lock60_5_70` 为新基线。
- 不再优先做全局降权；它会继续降低日均交易数。
- 需要一个低相关补频模块，最好只在 R121 锁仓/低活动窗口或 2026-03/05 这类从月初走弱的 regime 中补单，同时不污染 2025H2 复利。

## Round122: range-breakout frequency leg on R121

Hypothesis: the historical R83 range-breakout add-on slightly increased trade frequency on the R59 base, so a tiny capped range leg might coexist with the new R121 profit-lock champion.

Tested on MT5 720d:

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r122_j2_r121_rb_micro` | 243 | 0.3 | 41.2% | 0.76 | $0.80 | failed/near-stopout |
| `v11_r122_j2_r121_rb_small` | 215 | 0.3 | 45.6% | 0.74 | -$0.28 | failed/negative balance |

Conclusion: R83-style range-breakout is not a compatible add-on for R121. It changes the path enough to destroy survival and does not solve frequency. Keep `v11_r121_j2_r119_lock60_5_70` as the current best.

## Round123-126: profit-lock loosen and high-frequency sweep attempts

All tests below used the fixed comparison window `2024.06.02 ~ 2026.05.23` to avoid `--days 720` drifting to the next day.

Round123 tested whether R121's profit lock could be loosened to regain trade count:

| Strategy | Trades | Daily | Win | PF | Balance | Losing months | Conclusion |
|---|---:|---:|---:|---:|---:|---:|---|
| `v11_r123_j2_r119_lock60_20_70` | 2885 | 4.0 | 42.4% | 1.42 | $76600.12 | N/A | more trades but below $80k |
| `v11_r123_j2_r119_lock60_30_70` | 3029 | 4.2 | 42.2% | 1.39 | $79951.78 | 8 | almost $80k, but losing months worsen |
| `v11_r123_j2_r119_lock60_30_60` | 3148 | 4.4 | 42.5% | 1.40 | $77543.61 | N/A | frequency recovers, profit drops |

Conclusion: R123 confirms R121 sits near the profit/frequency frontier. Loosening the lock recovers 248-367 trades but loses the monthly protection that made R121 cross $80k.

Round124 moved the R45 high-frequency sweep recipe onto R121:

| Strategy | Trades | Daily | Win | PF | Balance | Losing months | Conclusion |
|---|---:|---:|---:|---:|---:|---:|---|
| `v11_r124_j2_r121_swp_loose` | 4732 | 6.6 | 44.0% | 0.94 | $34959.74 | 12 | frequency improves, quality collapses |
| `v11_r124_j2_r121_swp_loose_small` | 520 | 0.7 | 48.1% | 1.47 | $33815.05 | N/A | max lot 0.005 is below practical BTC sizing; leg becomes distorted |
| `v11_r124_j2_r123_swp_loose` | 4732 | 6.6 | 44.0% | 0.94 | $34959.74 | N/A | same path as R124 loose |

R124 digest showed the loose sweep damage is broad and persistent. It creates 12 losing months and the main risk moves to `sweep/hour20`, `sweep/hour13/risk200-300/cp -1.5~-1.0`, and `sweep/hour15/risk400+/cp<=-1.5`.

Round125 tried to keep loose-sweep frequency while isolating the digest bad clusters:

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r125_j2_r124_no20` | 4518 | 6.3 | 44.0% | 0.93 | $35772.94 | disabling hour20 is insufficient |
| `v11_r125_j2_r124_swpbad_soft` | 4568 | 6.3 | 43.9% | 0.89 | $33883.31 | soft cluster pressure does not fix PF |
| `v11_r125_j2_r124_swpbad_cut` | 4418 | 6.1 | 44.1% | 0.96 | $34057.28 | hard cluster cut still far below R121 |

Round126 tried earlier profit lock on the high-frequency sweep path:

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r126_j2_r124_lock30_5_70` | 4656 | 6.5 | 44.0% | 0.93 | $33893.58 | earlier lock does not rescue quality |
| `v11_r126_j2_r124_lock30_5_40` | 5590 | 7.8 | 44.0% | 0.99 | $794.37 | nearly hits trade frequency, but destroys profit |
| `v11_r126_j2_r124_lock30_20_40` | 4732 | 6.6 | 44.0% | 0.94 | $34959.74 | same as R124 loose |

Conclusion:

- Current best remains `v11_r121_j2_r119_lock60_5_70`: $83368.47, daily 3.9, 7 losing months.
- The historical high-frequency sweep recipe can approach the trade-count target, but its expected value is too weak. Once daily frequency approaches 8, balance collapses.
- The next useful direction is not more sweep loosen/filter cycling. We need either a genuinely separate high-frequency signal with positive PF, or an entry-before-loss regime classifier that suppresses 2026-03/05 without reducing 2025H2 expansion.

## Round127: high-balance early weak-month stop

Implemented a one-shot early-month stop:

- `monthly_early_loss_stop_trades`: evaluate only after exactly N entries in the month.
- `monthly_early_loss_stop_pct`: stop if balance/equity is below month-start balance by this percentage.
- `monthly_early_loss_stop_min_balance`: only enable the guard once account balance is high enough.

Offline scan on R121 showed 2026-03 and 2026-05 both became weak within the first 8 entries at high balance, while 2026-01/02/04 should not be stopped by `N=8, pct=1.0, min_balance=60000`.

Fixed-window MT5 Real Ticks (`2024.06.02 ~ 2026.05.23`):

| Strategy | Trades | Daily | Win | PF | Balance | Losing months | Conclusion |
|---|---:|---:|---:|---:|---:|---:|---|
| `v11_r127_j2_r121_early8_1` | 2499 | 3.5 | 42.9% | 1.58 | $94575.12 | 7 | new champion; protects 2026-03/05 |
| `v11_r127_j2_r121_early3_1` | 2607 | 3.6 | 42.8% | 1.58 | $88754.48 | 7 | catches May, misses March |
| `v11_r127_j2_r123_early8_1` | 2749 | 3.8 | 42.5% | 1.45 | $90264.95 | 8 | more trades, worse monthly profile |

Digest notes:

- `v11_r127_j2_r121_early8_1` cuts 2026-03 to 8 trades / -$870 and 2026-05 to 8 trades / -$966.
- Profit improves from R121's $83.4k to $94.6k, but trade frequency drops from 3.9/day to 3.5/day.
- Losing month count stays at 7 because early stop cannot make a month profitable after the first losses have already occurred.

Conclusion: R127 is the new best risk/profit path, but it does not address the frequency target or all-profitable-month target. Early stop is protective, not generative.

## Round128: narrow sweep bad-cluster filters on R127

Offline CSV replay suggested a small possible improvement from filtering late remaining sweep buckets, especially `hour 1/20 + risk 200-400 + cp -1.0~-0.6`. Real MT5 path rejected the idea:

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r128_j2_r127_swp_h120_cp_cut` | 260 | 0.4 | 43.1% | 0.84 | -$0.13 | path collapse |
| `v11_r128_j2_r127_swp_h120_wide_cut` | 2725 | 3.8 | 41.7% | 0.87 | $8256.78 | broad cut destroys PF |
| `v11_r128_j2_r127_swp_h15_tail_cut` | 249 | 0.3 | 43.0% | 0.84 | -$0.68 | path collapse |

Conclusion:

- Do not continue bad-cluster hard-cut cycling on R127.
- CSV replay is useful for hypothesis generation only; true MT5 path dependencies dominate once filters change order flow, monthly stops, balance, lots, and concurrency.
- Current best is `v11_r127_j2_r121_early8_1`: $94,575.12, daily 3.5, 7 losing months.
- Next direction should be a separate positive-EV frequency source or a pre-entry regime classifier. Single-BTC frequency above 8/day has so far appeared only when PF falls below 1.

## Cross-symbol check: R127 on BTC + ETH

To test whether frequency can be improved without loosening BTC entries, ran `v11_r127_j2_r121_early8_1` on BTCUSDm + ETHUSDm over the same fixed window.

| Symbol | Trades | Daily | Win | PF | Balance |
|---|---:|---:|---:|---:|---:|
| BTCUSDm | 2499 | 3.5 | 42.9% | 1.58 | $94575.12 |
| ETHUSDm | 318 | 0.4 | 37.4% | 0.72 | $39.95 |
| Combined | 2817 | 3.9 | 42.2% | N/A | $94615.07 |

Conclusion: simple BTC+ETH portfolioing does not solve frequency. ETH needs its own parameters or should be excluded from this R127 BTC-tuned recipe.

## Updated target and Round129-130: early stop on high-frequency sweep

Target updated to: daily trades >5, balance >$100000, every month profitable.

Hypothesis: the high-frequency R124/R126 sweep path might only need R127-style early weak-month protection.

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r129_j2_r126_540_early8_1_g30` | 5590 | 7.8 | 44.0% | 0.99 | $794.37 | unchanged from R126; guard does not rescue path |
| `v11_r129_j2_r126_540_early3_005_g30` | 5590 | 7.8 | 44.0% | 0.99 | $794.37 | unchanged |
| `v11_r129_j2_r124_early8_1_g30` | 4277 | 5.9 | 44.7% | 0.94 | $39558.27 | frequency ok, profit far too low |
| `v11_r130_j2_r126_540_early8_1_all` | 5590 | 7.8 | 44.0% | 0.99 | $794.37 | all-balance early stop still unchanged |
| `v11_r130_j2_r126_540_early3_005_all` | 5590 | 7.8 | 44.0% | 0.99 | $794.37 | unchanged |
| `v11_r130_j2_r124_early8_1_all` | 4277 | 5.9 | 44.7% | 0.94 | $39558.27 | unchanged from R129 R124 |

Conclusion: monthly early-stop logic cannot rescue the loose-sweep high-frequency source. Its EV is too weak before monthly guards can help.

## Round131-133: R127 neighborhood under new target

Round131 tested moderate sweep loosening between R127 and R124:

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r131_j2_r127_swp_mid1` | N/A | N/A | N/A | N/A | timeout | invalid/no result |
| `v11_r131_j2_r127_swp_mid2` | 1352 | 1.9 | 46.1% | 1.72 | -$424.50 | path collapse |
| `v11_r131_j2_r127_swp_mid_r58` | 360 | 0.5 | 46.7% | 0.85 | -$2.00 | path collapse |

Round132 tested keeping R127 signal quality but increasing capacity:

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r132_j2_r127_cap10_e5` | 2501 | 3.5 | 42.8% | 1.61 | $89769.13 | capacity does not add meaningful frequency, hurts balance |
| `v11_r132_j2_r123e8_cap10_e5` | 2841 | 3.9 | 42.5% | 1.25 | $52655.99 | looser lock + capacity damages PF |
| `v11_r132_j2_r123e8_cap10_e5_r58` | 212 | 0.3 | 44.3% | 0.84 | $1.28 | risk increase collapses path |

Round133 tested whether R127 can simply be scaled to the $100k target:

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r133_j2_r127_r56` | 1539 | 2.1 | 43.2% | 0.76 | -$190.66 | risk +0.2 is not stable |
| `v11_r133_j2_r127_r57` | 221 | 0.3 | 43.0% | 0.84 | $0.24 | risk +0.3 collapses |
| `v11_r133_j2_r127_lock10_70` | 2605 | 3.6 | 42.8% | 1.48 | $87045.91 | looser profit lock hurts |

Monthly first-N diagnosis on R127:

- 2026-03 and 2026-05 are caught by early8, but remain small losing months.
- 2025-05 starts strongly positive through the first 20 trades, then later turns negative. Early-month diagnosis cannot prevent this.
- 2024-10 and 2024-12 also turn weak mid-month rather than immediately.

Conclusion:

- Current best remains `v11_r127_j2_r121_early8_1`: $94575.12, daily 3.5, 7 losing months.
- Simple scaling, looser profit lock, looser sweep, higher capacity, and high-frequency sweep rescue attempts are all falsified.
- To satisfy the updated target, the next real direction must add a new positive-EV frequency source or a stronger intra-month profit preservation rule that does not destroy 2025H2 compounding.

## Round134: low-balance monthly profit lock

Diagnose pass on R127 losing months showed:

- 2024-09, 2024-10, 2025-05 had positive intra-month peaks before ending negative.
- Existing R127 profit lock only starts after balance reaches $60000, so it cannot protect early/mid-stage losing months.
- Hypothesis: enable a small monthly profit lock earlier to reduce losing months.

Fixed-window MT5 Real Ticks:

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r134_j2_r127_lock0_5_70` | 1612 | 2.2 | 40.2% | 1.09 | $6886.27 | all-balance lock destroys compounding |
| `v11_r134_j2_r127_lock0_2_50` | 1059 | 1.5 | 38.2% | 1.06 | $770.12 | too defensive |
| `v11_r134_j2_r127_lock500_2_50` | 1564 | 2.2 | 40.7% | 0.56 | $490.23 | delayed small lock still fails |

Conclusion: protecting early/mid-stage months with profit lock is not viable. It prevents some giveback but removes the compounding path needed to reach $100k.

Updated falsified directions:

- Loose/high-frequency sweep: frequency improves, EV collapses.
- Moderate sweep loosening: unstable/path collapse.
- Higher concurrency/entries per OB: no meaningful frequency gain.
- Higher risk: path collapse.
- Looser high-balance profit lock: balance drops.
- Low-balance profit lock: compounding destroyed.

The remaining path to the target needs a genuinely new positive-EV entry source or a richer regime classifier that acts before entry, not another monthly stop/lock variant.

## Round135: isolated micro frequency legs on R127

Hypothesis: existing `range_breakout` or `loose_sweep` can be added as a tiny capped frequency leg without damaging the R127 main path.

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r135_j2_r127_rb_micro` | 2494 | 3.5 | 42.9% | 1.61 | $89734.91 | no frequency gain; balance lower |
| `v11_r135_j2_r127_rb_tiny` | 2494 | 3.5 | 42.9% | 1.61 | $89734.91 | same path as micro |
| `v11_r135_j2_r127_lswp_micro` | 2448 | 3.4 | 42.3% | 1.13 | $32262.16 | loose sweep damages path |

Digest/CSV check:

- `v11_r135_j2_r127_rb_micro` exported 2494 trades: `sweep=1957`, `ob=537`, `range=0`.
- `v11_r135_j2_r127_lswp_micro` exported 2448 trades: `sweep=1935`, `ob=513`; loose sweep is not exposed as a separate signal type and still changes path quality.

Conclusion: the current built-in supplemental legs are not viable as isolated frequency add-ons. RangeBreakout did not produce a distinct frequency stream on this setup; LooseSweep changed order flow and reduced balance sharply.

Next useful implementation direction: add/debug a genuinely distinct entry source with explicit signal type and isolation controls, or add a pre-entry regime classifier. Reusing old `range_breakout`/`loose_sweep` switches is exhausted for this target.

## Round136: high-balance monthly warmup on R127

Hypothesis: keep R127 low-balance compounding intact, but once balance is high (`monthly_guard_min_balance=60000`), use monthly warmup sizing until the month proves itself.

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r136_j2_r127_warm60_1_m50` | 2601 | 3.6 | 42.8% | 1.49 | $86964.68 | high-balance warmup cuts compounding |
| `v11_r136_j2_r127_warm60_2_m50` | 2601 | 3.6 | 42.8% | 1.49 | $86964.68 | same path |
| `v11_r136_j2_r127_warm60_1_m30` | 2601 | 3.6 | 42.8% | 1.49 | $87015.58 | slightly better, still below R127 |

Conclusion: monthly warmup, even only at high balance, does not move toward the target. It lowers the large compounding months more than it protects bad months.

Current best remains `v11_r127_j2_r121_early8_1`: daily 3.5, balance $94575.12, 7 losing months.

Exhausted parameter families now include: sweep loosen/tighten, loose sweep, range breakout add-ons, capacity, risk scaling, profit-lock timing, early monthly stop, and monthly warmup. The next aligned task is implementation of a new observable entry/regime feature, with explicit signal attribution in digest so it can be diagnosed separately.

## Round137: sweep monthly-state gates on R127

Hypothesis: keep the R127 OB path intact and only gate sweep after weak monthly state, because several losing months had sweep drawdown.

Fixed-window MT5 Real Ticks (`2024.06.02` to `2026.05.23`):

| Strategy | Trades | Daily | Win | PF | Balance | Losing months | Conclusion |
|---|---:|---:|---:|---:|---:|---:|---|
| `v11_r137_j2_r127_swp_mneg0` | 1848 | 2.6 | 43.5% | 1.44 | $52295.34 | 12 | disabling sweep after monthly negative destroys compounding |
| `v11_r137_j2_r127_swp_mneg035` | 2332 | 3.2 | 42.5% | 1.19 | $45211.86 | 10 | partial sweep reduction is worse |
| `v11_r137_j2_r127_swp_profit2` | 1651 | 2.3 | 44.8% | 1.14 | $47915.24 | 12 | requiring a +2% monthly cushion before sweep misses too much of the positive path |

Digest/CSV findings:

- R127 signal-type total: `ob=538/+61.34R`, `sweep=1961/+11.52R`.
- R137 `mneg0`: `ob=529/+42.97R`, `sweep=1319/-3.23R`.
- R137 `mneg035`: `ob=549/+42.83R`, `sweep=1783/-37.36R`.
- R137 `profit2`: `ob=523/+41.74R`, `sweep=1128/+59.31R`, but trade count and balance still collapse.

Conclusion: sweep is noisy but structurally important to the R127 compounding path. Monthly-state sweep gates reduce frequency and balance, and do not reduce losing months enough. Do not continue with broad sweep month gates.

## Round138: OB-only bad-cluster filters on R127

Offline diagnosis suggested OB hour 7/8/9 was a bad bucket (`74 trades, -24.41R`) while overall OB remained strong (`538 trades, +61.34R`). Tested narrow OB-only cluster filters without touching sweep.

| Strategy | Trades | Daily | Win | PF | Balance | Losing months | Conclusion |
|---|---:|---:|---:|---:|---:|---:|---|
| `v11_r138_j2_r127_ob_h789_soft` | 234 | 0.3 | 42.3% | 0.84 | -$0.06 | path collapsed | soft sizing changes the path badly |
| `v11_r138_j2_r127_ob_h789_cut` | 2424 | 3.4 | 42.3% | 2.01 | $82234.66 | 8 | best R138, but below R127 and worse 2026-03 |
| `v11_r138_j2_r127_ob_shallow_cut` | 311 | 0.4 | 41.5% | 0.82 | -$5.93 | path collapsed | broad shallow OB filter is not viable |

Digest/CSV findings for `v11_r138_j2_r127_ob_h789_cut`:

- Signal-type totals: `ob=439/+69.20R`, `sweep=1985/-22.84R`.
- It improved OB quality, but the removed OB trades changed path context and made sweep the drag.
- Losing months still include 2024-10/11/12, 2025-05/11, 2026-03/05; 2026-03 worsened to about `-$6328`.

Conclusion: narrow OB filtering can improve isolated OB R quality but still misses the overall target. Like sweep gates, static bad-cluster filters are exhausted as a primary path. The next useful work is a genuinely new entry/regime feature with explicit signal attribution, or a regime classifier that changes before signal generation rather than after signal selection.

## Round139: new HTF pullback signal source

Implemented a new `HTFPB` signal source:

- Detection: higher-timeframe net push over recent closed HTF bars creates a pullback zone near the HTF close.
- Attribution: order comments include `HTFPB`; digest maps this to `signal_type=htf_pullback`.
- Config: `enable_htf_pullback`, `htf_pullback_only`, HTF bars/ATR/zone/offset/TP, plus position and lot caps.
- Validation: Python tests passed (`71 passed`), native MetaEditor compile passed (`0 errors, 0 warnings`).

First fixed-window MT5 Real Ticks results:

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r139_j2_r127_htfpb_micro` | 146 | 0.2 | 45.9% | 0.62 | $1.47 | not viable as a direct R127 add-on; path is heavily disrupted |
| `v11_r139_j2_htfpb_only` | 2299 | 3.2 | 59.5% | 0.89 | $59.37 | real frequency source, but negative EV |

Digest findings for `v11_r139_j2_htfpb_only`:

- All trades are `htf_pullback`; signal attribution now works.
- Total R: `-62.29R`, despite `66.6%` win rate.
- Exit structure: `tp=1528/+572.21R`, `sl=525/-529.36R`, `market_close=246/-105.14R`.
- Risk buckets: `risk 200-300 = +15.49R`; `100-150`, `150-200`, `300-400`, `400+` are negative.
- Hour buckets: hour 12 is near breakeven (`+0.82R`), hour 15 tiny positive, while hour 23/13/14/20 are negative.

Conclusion: HTFPB is a useful new diagnosable signal source but not yet a profitable leg. The shape is high-win/low-payoff with market-close leakage and full-SL losses overwhelming small TPs. Next R140 should isolate HTFPB improvements before combining with R127: e.g. risk 200-300 only, avoid hours 23/14, test larger `htf_pullback_tp_mult`, and possibly reduce market-close leakage.

## Round140: isolate HTFPB positive risk bucket

Hypothesis: R139 showed the only positive HTFPB bucket was `risk 200-300` (`+15.49R`, PF 1.12 offline), so cut all HTFPB trades outside that distance and test whether a larger TP repairs payoff.

Fixed-window MT5 Real Ticks (`2024.06.02` to `2026.05.23`):

| Strategy | Trades | Daily | Win | PF | Balance | Digest R | Losing months | Conclusion |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `v11_r140_j2_htfpb_r200_300` | 1565 | 2.2 | 63.1% | 0.98 | $230.44 | +18.09R | 8 | risk filter turns HTFPB slightly positive, but edge is tiny |
| `v11_r140_j2_htfpb_r200_300_tp15` | 1324 | 1.8 | 52.0% | 0.94 | $150.45 | -14.59R | 10 | larger TP worsens path |
| `v11_r140_j2_htfpb_r200_300_tp2` | 1315 | 1.8 | 44.3% | 0.95 | $138.63 | -20.92R | 11 | larger TP worsens path |

Digest/CSV findings for `v11_r140_j2_htfpb_r200_300`:

- Signal is now a small positive leg: `1565` trades, `+18.09R`, balance `$230.44`.
- Exit structure remains fragile: `tp=1083/+406.02R`, `sl=319/-321.42R`, `market_close=163/-66.51R`.
- Worst hours: `13=-15.44R`, `23=-6.45R`, `14=-4.97R`, `21=-3.70R`.
- Best hours: `12=+17.81R`, `20=+9.59R`.
- Confirm position `>-0.6` is negative (`-13.17R`); deeper confirmations are positive.

Conclusion: HTFPB does not want a farther TP. It is a high-win, short-payoff signal; the only useful direction is tighter regime/hour/exit control, or using it as a small capped add-on after isolation.

## Round141: HTFPB hour gates after risk isolation

Hypothesis: remove the worst R140 hours while keeping the positive `risk 200-300` bucket.

| Strategy | Trades | Daily | Win | PF | Balance | Digest R | Losing months | Conclusion |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `v11_r141_j2_htfpb_r200_300_no13` | 1180 | 1.6 | 62.4% | 1.01 | $250.10 | pending detailed use | improved but still small |
| `v11_r141_j2_htfpb_r200_300_no1323` | 955 | 1.3 | 63.0% | 1.03 | $263.42 | pending detailed use | improved but lower frequency |
| `v11_r141_j2_htfpb_r200_300_no132314` | 934 | 1.3 | 63.3% | 1.07 | $283.66 | +35.07R | 10 | best HTFPB-only variant so far, still only a small add-on |

Digest/CSV findings for `v11_r141_j2_htfpb_r200_300_no132314`:

- Remaining exit structure: `tp=650/+253.29R`, `sl=173/-174.11R`, `market_close=111/-44.11R`.
- Remaining best hours: `12=+18.41R`, `20=+8.98R`.
- Remaining worst hours: `1=-4.90R`, `21=-3.48R`, `0=-1.19R`.
- Confirm buckets: `>-0.6=-2.39R`, `-1.0~-0.6=+18.21R`, `-1.5~-1.0=+6.95R`, `<=-1.5=+12.30R`.
- Losing months still include 2025-07 (`-$22.00`), 2026-02 (`-$7.56`), 2025-10/11 (about `-$4-5`).

Conclusion: R141 creates the best isolated HTFPB leg so far, but it is not a primary path to the objective: daily count falls to `1.3`, balance is only `$283.66`, and losing months remain high. Further simple hour bans would start cutting the main positive hours (`12/20`). The next useful tests are (1) remove shallow confirm `>-0.6`, (2) reduce market-close leakage via timeout/session behavior if supported, or (3) merge R141 as a tiny capped add-on to R127 and verify whether it improves monthly smoothness without disturbing the champion path.

## Round142: HTFPB shallow-confirm filter

Hypothesis: after R141, cut shallow HTFPB confirmations (`confirm_pos > -0.6`) because this bucket was negative while deeper confirmations were positive.

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r142_j2_htfpb_r200_300_no13_cp06` | 1049 | 1.5 | 63.0% | 1.02 | $269.50 | better than R141 no13 but not enough |
| `v11_r142_j2_htfpb_r200_300_no1323_cp06` | 872 | 1.2 | 63.6% | 1.03 | $267.02 | worse than R141 no1323 |
| `v11_r142_j2_htfpb_r200_300_no132314_cp06` | 830 | 1.2 | 64.0% | 1.07 | $284.51 | only +$0.85 over R141 best, with fewer trades |

Digest/CSV findings for `v11_r142_j2_htfpb_r200_300_no132314_cp06`:

- Exit structure improved only slightly: `tp=582/+231.78R`, `sl=158/-159.04R`, `market_close=90/-37.82R`.
- Best hours remain `12=+14.16R`, `20=+11.08R`; worst remaining hours are small buckets `1=-4.90R`, `21=-3.48R`, `0=-1.19R`.
- Losing months still include 2025-07 (`-$19.60`), 2026-02 (`-$8.81`), 2024-12/2025-09/2025-10/2025-11.

Conclusion: shallow-confirm filtering is not a meaningful lever. It removes some bad trades but also removes enough small TP winners that the best variant barely improves. Do not continue with static confirm filters as the main path. The useful next test is to merge R141/R142 as a tiny capped add-on to R127, because as an isolated strategy HTFPB is only a small positive leg.

## Round143: naive R127 + HTFPB micro merge failed

Hypothesis: merge the best isolated HTFPB filters back into R127 as a tiny capped add-on.

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r143_j2_r127_htfpb_r141_micro` | 217 | 0.3 | 43.3% | 0.74 | -$0.01 | invalid merge; global hour filter damaged R127 |
| `v11_r143_j2_r127_htfpb_r142_micro` | 203 | 0.3 | 42.9% | 0.73 | -$0.52 | invalid merge; global hour filter damaged R127 |

Digest/CSV findings:

- No HTFPB trades survived in the combined run; attribution showed only `ob` and `sweep`.
- The inherited `no_entry_hours=13,23,14` was global, not HTFPB-specific, so it removed important R127 OB/sweep entries and collapsed the champion path.
- R143 is therefore an implementation/configuration mistake, not proof that a properly isolated HTFPB add-on cannot work.

Conclusion: do not use global `no_entry_hours` in combination strategies. R144 should express HTFPB hour filters through `bad_cluster*_signal: "htfpb"` so R127 OB/sweep remains untouched.

## Round144-R146: HTFPB add-on isolation bug

Hypothesis: express HTFPB filters with `bad_cluster*_signal: "htfpb"` instead of global `no_entry_hours`, then merge HTFPB as a tiny add-on to R127 without touching OB/sweep.

Initial R144/R145 result:

| Strategy | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| `v11_r144_j2_r127_htfpb_sig_r141_micro` | 172 | 0.2 | 45.9% | 0.66 | $0.44 | still invalid; HTFPB enable corrupts main path |
| `v11_r144_j2_r127_htfpb_sig_r142_micro` | 172 | 0.2 | 45.9% | 0.66 | $0.44 | same result |
| `v11_r145_j2_r127_htfpb_sig_r141_micro_fix` | 172 | 0.2 | 45.9% | 0.66 | $0.44 | new version/magic ruled out tester cache |
| `v11_r145_j2_r127_htfpb_sig_cp06_micro_fix` | 172 | 0.2 | 45.9% | 0.66 | $0.44 | same result |

Implemented isolation fixes:

- Treat HTFPB as supplemental capacity in `OBDetector.mqh`, same class as loose sweep for primary-zone pruning.
- Treat HTFPB monitors as supplemental in `EntryEngine.mqh`, so primary OB/sweep monitors can replace them when monitor slots are full.
- Exclude HTFPB from ordinary OB consolidation and ordinary OB duplicate checks.
- Native MetaEditor compile passed after the fixes: `0 errors, 0 warnings`.

R146 after isolation fixes:

| Strategy | Trades | Daily | Win | PF | Balance | Signal totals | Conclusion |
|---|---:|---:|---:|---:|---:|---|---|
| `v11_r146_j2_r127_htfpb_sig_r141_isolated` | 1886 | 2.6 | 43.1% | 0.90 | $516.62 | `ob=565/+36.74R`, `sweep=1321/-4.17R`, `htfpb=0` | partial recovery, still not viable |
| `v11_r146_j2_r127_htfpb_sig_cp06_isolated` | 1886 | 2.6 | 43.1% | 0.90 | $516.62 | same path | partial recovery, still not viable |

Diagnosis:

- The worst R144/R145 collapse was not tester cache; it was real path corruption.
- The R146 fixes restored some path health (`172` trades -> `1886`), but the champion path is still far below R127 (`2499` trades, `$94575.12`).
- No HTFPB trades appear in combined attribution, so HTFPB currently acts as a path disruptor rather than an actual add-on.
- Remaining damage is mostly sweep: R127 `sweep=1961/+11.52R`, R146 `sweep=1321/-4.17R`.

Conclusion: HTFPB is usable only as an isolated attribution strategy for now. It is not safe to merge into the shared `g_zones`/EntryEngine path without deeper architectural separation. Do not continue testing R127+HTFPB parameter variants until HTFPB has its own independent zone/monitor lane or a post-main-scan add-on path that cannot consume primary sweep/OB capacity.

## Round147: narrow sweep bad-cluster cuts on R127

Hypothesis: avoid new signal-source interference and cut only three clearly negative R127 sweep clusters found offline:

- `sweep hour=1 risk=200-300 cp=-1.5~-1.0` (`16 trades, -8.88R`)
- `sweep hour=15 risk=400+ cp<=-1.5` (`20 trades, -7.99R`)
- `sweep hour=20 risk=300-400 cp=-1.5~-1.0` (`17 trades, -5.62R`)

Fixed-window MT5 Real Ticks result:

| Strategy | Trades | Daily | Win | PF | Balance | Signal totals | Conclusion |
|---|---:|---:|---:|---:|---:|---|---|
| `v11_r147_j2_r127_swp_3bad_cut` | 2432 | 3.4 | 43.0% | 1.24 | $36168.55 | `ob=536/+38.25R`, `sweep=1896/+14.88R` | not viable; static sweep cuts still damage compounding |

Digest findings:

- R147 removes only 67 trades vs R127 but final balance drops from `$94575.12` to `$36168.55`.
- The reduced path misses part of the strong late-2025 compounding and ends with five consecutive losing months in 2026.
- This repeats the R137/R138 lesson: small offline-negative bucket removal can still change the sequential path enough to hurt balance badly.

Conclusion: do not continue with static bad-cluster deletion as the main path. The remaining viable work is either (1) a truly isolated add-on architecture that cannot alter R127 OB/sweep path, or (2) a pre-entry regime/state feature that changes signal quality without path-dependent post-hoc deletion.

## Round148-R150: independent HTFPB lane probe

Implemented a separate HTFPB lane in the EA:

- `g_htf_zones[]` and `g_htf_monitors[]` separate from the primary `g_zones[]` and `g_monitors[]`.
- Non-HTFPBOnly mode no longer appends HTFPB zones into the primary OB/sweep zone pool.
- HTFPB execution uses `ExecuteSignalFromZone(..., allow_layered=false)` so zone marking targets the HTF lane, not the primary lane.
- R127 with HTFPB disabled was rerun after the architecture change and exactly matched the known champion: `2499` trades, `$94575.12`.

Fixed-window MT5 Real Ticks results:

| Strategy | Trades | Daily | Win | PF | Balance | Signal totals | Conclusion |
|---|---:|---:|---:|---:|---:|---|---|
| `v11_r127_j2_r121_early8_1` | 2499 | 3.5 | 42.9% | 1.58 | $94575.12 | `ob=538/+61.34R`, `sweep=1961/+11.52R` | regression path intact |
| `v11_r148_j2_r127_htfpb_lane_r141_micro` | 2472 | 3.4 | 43.1% | 1.30 | $33162.87 | `ob=533/+35.38R`, `sweep=1939/-7.74R`, `htfpb=0` | independent lane still perturbs path |
| `v11_r149_j2_r127_htfpb_lane_r141_fallback` | 2472 | 3.4 | 43.1% | 1.30 | $33162.87 | same as R148 | executing HTFPB only when primary has no confirmed signal does not help |
| `v11_r150_j2_r127_htfpb_detect_only_probe` | 2472 | 3.4 | 43.1% | 1.30 | $33162.87 | same as R148 | detection-only still perturbs path |

Diagnosis:

- The R127 regression proves the new code is inert when HTFPB is disabled.
- R150 proves the perturbation happens before HTFPB monitor registration/execution. Merely enabling HTFPB detection changes the MT5 Strategy Tester path.
- Most likely mechanism: the extra HTF `CopyRates()` / multi-timeframe data access in `DetectHTFPullbacks()` changes tester data/cache/timing behavior enough to alter the primary OB/sweep path, even with separate arrays and no HTFPB trades.
- Therefore HTFPB cannot be safely added to the same EA execution path as R127 right now.

Conclusion: HTFPB remains useful as a separately backtested attribution signal, but not as an in-EA add-on. Future work should either run HTFPB as a separate EA/magic stream, or derive HTFPB features from already-loaded primary/HTF state without extra tester data calls in the main signal path. For the current target, continue from R127 rather than R148/R150.
## Round151: continuous early monthly loss stop on R127

Hypothesis: R127 early monthly loss stop only checked at exactly the Nth monthly entry. If a weak month crossed the 1% line after entry N, the early stop would not protect later entries. Change tested: add `monthly_early_loss_stop_continuous=true`, so the early weak-month stop checks every entry after the threshold.

Implementation notes:

- Added `InpMonthlyEarlyLossStopContinuous` and YAML mapping `monthly_early_loss_stop_continuous`.
- Default is `false` to preserve existing R127 behavior.
- R151 candidates explicitly set it to `true`.
- Native MetaEditor compile passed: `0 errors, 0 warnings`.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r127_j2_r121_early8_1` | 2499 | 3.5 | 42.9% | 1.58 | $94575.12 | `ob=538/+61.34R`, `sweep=1961/+11.52R` | 7 balance months | champion remains best |
| `v11_r151_j2_r127_early8_ge_fix` | 2340 | 3.2 | 43.2% | 1.36 | $60302.09 | `ob=503/+49.43R`, `sweep=1837/+2.05R` | 10 balance months | worse; cuts profitable high-balance recovery |
| `v11_r151_j2_r127_early5_ge_fix` | 2337 | 3.2 | 43.3% | 1.36 | $60304.93 | `ob=503/+49.43R`, `sweep=1834/+4.22R` | 10 balance months | worse |
| `v11_r151_j2_r127_early3_ge_fix` | 2300 | 3.2 | 43.4% | 1.35 | $60608.40 | `ob=501/+51.15R`, `sweep=1799/+18.20R` | 10 balance months | R close to R127 but balance far worse |

Diagnosis:

- Continuous early stop does reduce late bad-month exposure, especially in 2026-04/05.
- It also blocks the high-balance recovery path that makes R127 strong: R127 has profitable balance months in 2026-01, 2026-02, and 2026-04, while R151 variants turn those into small or negative balance months.
- The E3 variant keeps net R closest to R127 (`69.35R` vs `72.86R`) but loses compounding because it stops too early during large-balance months.
- Therefore the issue is not simply "stop weak months earlier". R127 needs a more selective signal/regime adjustment that preserves the late-month recovery trades.

Conclusion: do not continue continuous early monthly loss stop as the main route. Keep the code as an explicit experimental option (`monthly_early_loss_stop_continuous`) but leave champion R127 default behavior unchanged. Next candidates should focus on low-interference sweep sizing/filtering, especially preserving hour 13/14 market-close winners while reducing hour 20/1/7/2 SL drag.
## Round152: preserve R127 clusters and add a 4th sweep bad-cluster slot

Hypothesis: R127 sweep hours `1` and `20` are persistent R drag, while hour `13/14` are core profit. Test soft sizing rather than hard deletion.

Important implementation correction:

- First R152 attempt accidentally reused `bad_cluster1`, which overwrote R127's existing broad shallow-confirm protection. That produced false collapse (`257-288` trades, near-zero balance). Treat those first runs as invalid configuration-overwrite probes, not strategy results.
- Added `bad_cluster4_*` inputs, YAML mapping, and tests so new experiments can preserve R127's existing three cluster rules.
- Default `bad_cluster4` is empty, so R127 remains unchanged.
- Tests: `python -m pytest tests\test_mt5_common.py -q` -> `71 passed`.
- Native MetaEditor compile passed: `0 errors, 0 warnings`.

Valid fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---|
| `v11_r127_j2_r121_early8_1` | champion | 2499 | 3.5 | 42.9% | 1.58 | $94575.12 | `ob=538/+61.34R`, `sweep=1961/+11.52R` | baseline |
| `v11_r152_j2_r127_h20_r150_400_soft` | `bad_cluster4`: hour20 sweep risk 150-400 x0.35 | 2858 | 4.0 | 42.9% | 1.15 | $18251.01 | `ob=617/+41.64R`, `sweep=2241/-11.83R` | invalid direction; path opens too much weak sweep |
| `v11_r152_j2_r127_h20_r150_400_half` | hour20 sweep risk 150-400 x0.50 | 2787 | 3.9 | 42.6% | 0.94 | $10669.43 | `ob=616/+39.04R`, `sweep=2171/-12.91R` | invalid direction |
| `v11_r152_j2_r127_h1_h20_soft` | hour1/hour20 sweep x0.50 | 2468 | 3.4 | 42.9% | 1.58 | $94684.53 | `ob=538/+61.34R`, `sweep=1930/+14.33R` | tiny balance improvement only |

Diagnosis:

- `H1/H20 x0.5` modestly improves sweep R (`+14.33R` vs `+11.52R`) and final balance (`+$109`) but reduces trade count and does not reduce balance losing months (`7`). It is not enough to replace R127 as a meaningful new champion.
- `H20 risk 150-400` variants unexpectedly increase trade count and damage path. Likely the reduced loss sizing keeps monthly/profit-lock state open longer, allowing many later weak trades. This is another reminder that offline R-bucket fixes can invert under sequential compounding and state gates.
- The new `bad_cluster4` slot is useful infrastructure; keep it for future additive tests that must preserve R127's original three clusters.

Conclusion: R152 does not reach the target. The next useful direction is not more bad-hour soft sizing. We need a frequency add-on that is isolated from R127's main OB/sweep capacity, or a truly pre-entry quality feature that raises trade count without changing the state path too aggressively.
## Round153: modest R127 risk scaling

Hypothesis: R127 is close to the updated `$100k` profit target (`$94.6k`), so a small risk increase might cross the profit threshold without changing signal logic.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|
| `v11_r153_j2_r127_risk57` | R127 risk `5.4 -> 5.7` | 221 | 0.3 | 43.0% | 0.84 | $0.24 | near-stopout; invalid |
| `v11_r153_j2_r127_risk60` | R127 risk `5.4 -> 6.0` | 214 | 0.3 | 44.9% | 0.83 | -$0.62 | stopout/negative balance; invalid |
| `v11_r153_j2_r152_h1h20_risk57` | R152 H1/H20 soft + risk `5.7` | 222 | 0.3 | 43.2% | 0.84 | -$1.05 | invalid |

Diagnosis:

- R127's `$94.6k` result is already near the survivable risk ceiling for this path.
- Small risk scaling causes early path failure and collapses trade count to ~220, so the strategy cannot be pushed over `$100k` by simple risk increase.
- This also explains why static bucket changes often invert: monthly/profit-lock and margin path are highly sensitive to early compounding state.

Conclusion: do not continue simple risk scaling. The best confirmed path remains R127, with R152 H1/H20 as only a tiny, non-decisive improvement. Next work must be a genuine new signal/regime feature, not leverage or bad-cluster cycling.
## Round154: R127 entry momentum filter as pre-entry regime gate

Hypothesis: existing `EntryMomentumFilter` can block entries against unresolved short-term strong momentum, reducing SL clusters without adding a new signal source. R127 already has `HTFNetPushFilter` enabled, so this round only tests the previously disabled entry momentum gate.

Implementation / validation:

- Added R154 variants with `enable_entry_momentum_filter=true` on M1/M5/M15.
- Reused existing `PassEntryMomentumFilter()` in final entry validation; no new signal source added.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.
- Native MetaEditor compile passed: `0 errors, 0 warnings`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Entry momentum TF | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r127_j2_r121_early8_1` | off | 2499 | 3.5 | 42.9% | 1.58 | $94575.12 | `ob=538/+61.34R`, `sweep=1961/+11.52R` | 7 balance months | baseline |
| `v11_r154_j2_r127_entry_mom_m1` | M1 | 2490 | 3.5 | 42.9% | 1.55 | $92641.86 | `ob=534/+62.90R`, `sweep=1956/+8.83R` | worse | not useful |
| `v11_r154_j2_r127_entry_mom_m5` | M5 | 2485 | 3.5 | 42.9% | 1.57 | $93894.72 | `ob=537/+60.61R`, `sweep=1948/+23.11R` | worse balance | better R, worse compounding |
| `v11_r154_j2_r127_entry_mom_m15` | M15 | 2495 | 3.5 | 42.7% | 1.55 | $94706.88 | `ob=538/+61.34R`, `sweep=1957/+19.15R` | 7 balance months | tiny new balance high, not decisive |

Diagnosis:

- M15 entry momentum gate is a real but weak pre-entry feature. It removes 17 R127-like trades for `-7.76R` and adds 13 path-shift trades for `-0.13R`, net improving R attribution.
- The improvement mainly comes from sweep (`+19.15R` vs R127 `+11.52R`), while OB stays unchanged.
- Balance gain is tiny (`+$131.76` over R127), and it does not improve trade frequency or losing-month count.
- M5 improves R more (`83.72R`) but compounds worse, so R alone is not enough to select it.

Conclusion: keep `v11_r154_j2_r127_entry_mom_m15` as the current tiny balance high, but it is not a goal-reaching solution. Next test: combine the two weak positive effects (`R154 M15` + `R152 H1/H20 sweep x0.5`) and verify whether they stack or interfere.
## Round155: combine M15 entry momentum with H1/H20 sweep soft sizing

Hypothesis: R154 M15 entry momentum and R152 H1/H20 sweep half-size each showed small positive balance effects. Combining them might stack without disrupting R127's main path.

Fixed-window MT5 Real Ticks result (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r127_j2_r121_early8_1` | 2499 | 3.5 | 42.9% | 1.58 | $94575.12 | `ob=538/+61.34R`, `sweep=1961/+11.52R` | 7 balance months | baseline |
| `v11_r154_j2_r127_entry_mom_m15` | 2495 | 3.5 | 42.7% | 1.55 | $94706.88 | `ob=538/+61.34R`, `sweep=1957/+19.15R` | 7 balance months | tiny balance high |
| `v11_r155_j2_r154_m15_h1h20_soft` | 2461 | 3.4 | 42.9% | 1.56 | $94776.12 | `ob=538/+61.34R`, `sweep=1923/+19.11R` | 7 balance months | current tiny balance high, not goal-reaching |

Diagnosis:

- The two effects do not materially stack in R terms: R155 net is `80.45R`, essentially the same as R154 M15 `80.49R`.
- R155 improves final balance by only `$69.24` over R154 M15 and `$201.00` over R127, while reducing trades to `2461` (`3.4/day`).
- Losing balance months remain `7`; R-based losing months remain broad. The objective remains far away.
- The useful finding is that M15 entry momentum is a weak but real pre-entry feature. H1/H20 half-size is mostly a compounding-path tweak, not a quality breakthrough.

Conclusion: current best by balance is now `v11_r155_j2_r154_m15_h1h20_soft` at `$94776.12`, but it is not meaningfully better than R127 and does not solve daily frequency or monthly profitability. Next direction should use M15 entry momentum as a base feature only if testing a genuinely new signal/regime mechanism; do not spend more turns stacking static filters.

## Round156: R155 strong add-on retest

Hypothesis: since R155 is close to the `$100k` balance threshold but still low frequency, a single small add-on on already-winning positions might raise right-tail exposure without changing the base entry filter.

Implementation / validation:

- Added three R156 variants on top of R155: `0.25x @ 1.2R`, `0.40x @ 1.2R`, and `0.25x @ 1.5R`.
- Added a safety guard to `OpenFailureReverse()` so future reverse tests also respect `InpMaxConcurrent` and `InpMaxLotSize`.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.
- Native MetaEditor compile passed: `0 errors, 0 warnings`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r155_j2_r154_m15_h1h20_soft` | baseline | 2461 | 3.4 | 42.9% | 1.56 | $94776.12 | `ob=538/+61.34R`, `sweep=1923/+19.11R` | 7 | current tiny balance high |
| `v11_r156_j2_r155_addon025_t12` | add once, `0.25x @ 1.2R` | 2321 | 3.2 | 42.7% | 1.05 | $50049.37 | `ob=516/+46.41R`, `sweep=1782/+17.34R` | 11 | invalid |
| `v11_r156_j2_r155_addon040_t12` | add once, `0.40x @ 1.2R` | 2327 | 3.2 | 42.6% | 1.09 | $48704.71 | `ob=521/+43.29R`, `sweep=1782/+24.97R` | 11 | invalid |
| `v11_r156_j2_r155_addon025_t15` | add once, `0.25x @ 1.5R` | 2376 | 3.3 | 42.5% | 1.05 | $49516.53 | `ob=529/+42.71R`, `sweep=1829/+20.53R` | 11 | invalid |

Diagnosis:

- StrongAddOn triggered only `23/24/18` times for the three R156 variants, far too little to lift daily frequency from `3.4` to `>5`.
- The add-on tickets are not currently marked as `addon=true` by the digest CSV because add-on orders do not emit the same open-event format as base entries. Ticket back-reference from `强势延续加仓: source=... addon=...` confirms the small trigger count. The parser should be improved before relying on add-on attribution.
- Even with few add-ons, enabling the mechanism worsens the sequential path: fewer base trades, worse PF, more losing months, and roughly half the final balance.
- This matches older Round57 evidence: StrongAddOn damages BTC 720-day compounding and is not a suitable frequency/profit lever.

Conclusion: reject R156. Do not continue StrongAddOn on R155. Also do not return to post-exit failure reverse as a main direction; Round56 already showed it accelerates low-balance path collapse. The next viable branch is to revisit proven high-frequency but unstable R32/R45-style signal bases and stabilize them with R127/R155-style guards, not to add post-entry actions to the low-frequency champion.

## Round157: R155 with positive-hour loose sweep allowlist

Hypothesis: R124 showed loose sweep can raise frequency but destroys PF. A narrower version that only allows historically positive sweep hours might preserve the R155 path while adding safer sweep exposure.

Implementation / validation:

- Added `v11_r157_j2_r155_swp_core`: R155 base, R45-style looser sweep detection, `sweep_allow_hours=13,14,15`, `max_concurrent=8`.
- Added `v11_r157_j2_r155_swp_core20`: same, with hour 20 included.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r155_j2_r154_m15_h1h20_soft` | baseline | 2461 | 3.4 | 42.9% | 1.56 | $94776.12 | `ob=538/+61.34R`, `sweep=1923/+19.11R` | 7 | current best |
| `v11_r157_j2_r155_swp_core` | loose sweep only h13/14/15 | 1588 | 2.2 | 47.8% | 1.20 | $35844.62 | `ob=528/+24.70R`, `sweep=1060/+113.88R` | 12 | invalid |
| `v11_r157_j2_r155_swp_core20` | loose sweep only h13/14/15/20 | 1881 | 2.6 | 45.5% | 1.20 | $35867.64 | `ob=522/+25.84R`, `sweep=1359/+69.63R` | 11 | invalid |

Diagnosis:

- The allowlist does not add frequency; it removes a large portion of R155's normal sweep stream and drops daily trades to `2.2/2.6`.
- R attribution is misleadingly high for `SWPCORE` (`+138.59R`) because the sequence path changes and the 2025H2 compounding base becomes much smaller. Final balance is therefore far worse despite higher net R.
- OB contribution collapses from `+61R` to roughly `+25R`, showing that sweep gating changes the shared state path rather than acting as an isolated sweep quality filter.
- Hour allowlists repeat the same failure mode as earlier static filters: they identify positive buckets in isolation but damage the sequential engine.

Conclusion: reject R157. Do not continue sweep allowlist / loose-sweep filtering on R155. Current best remains `v11_r155_j2_r154_m15_h1h20_soft`, but it still misses all objective constraints except being close to the balance threshold. Next work should require a genuinely new pre-entry regime signal or an offline path simulator that predicts sequential effects before spending full MT5 runs; more static sweep/hour/risk bucket cycling is exhausted.

## Round158: R155 with sweep-only monthly negative size reduction

Hypothesis: R155's high-balance losing months are mostly sweep-heavy after the month turns negative. Existing `sweep_monthly_negative_mult` might protect weak months with less damage than the global monthly negative multiplier.

Implementation / validation:

- Added `v11_r158_j2_r155_swp_mneg035`: R155 base, keep sweep at `0.35x` after current month turns negative.
- Added `v11_r158_j2_r155_swp_mneg0`: R155 base, disable sweep after current month turns negative.
- `.set` mapping checked: M15 entry momentum, H1/H20 bad cluster, magic number, and sweep monthly negative multiplier all emitted correctly.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r155_j2_r154_m15_h1h20_soft` | baseline | 2461 | 3.4 | 42.9% | 1.56 | $94776.12 | `ob=538/+61.34R`, `sweep=1923/+19.11R` | 7 | current best |
| `v11_r158_j2_r155_swp_mneg035` | sweep `0.35x` after monthly negative | 2203 | 3.1 | 43.3% | 1.56 | $93256.17 | `ob=531/+53.04R`, `sweep=1672/+30.81R` | 8 | invalid |
| `v11_r158_j2_r155_swp_mneg0` | no sweep after monthly negative | 1807 | 2.5 | 44.6% | 1.35 | $65778.84 | `ob=545/+56.93R`, `sweep=1262/+25.44R` | 8 | invalid |

Diagnosis:

- R158 protects some weak sweep exposure but also removes too much sequential participation. Frequency drops from `3.4/day` to `3.1/day` and `2.5/day`, moving further away from the `>5/day` target.
- The `0.35x` variant increases net R (`83.85R` vs R155 `80.45R`) but lowers final balance, confirming again that R-bucket improvement is not enough when the compounding path is disturbed.
- Losing balance months increase from `7` to `8`; `v11_r158_j2_r155_swp_mneg0` creates a new large 2026-02 loss (`-$5332.57`) by cutting the recovery path too hard.
- Sweep-only monthly negative control is therefore another defensive overlay that trims both bad and good right-tail sequences.

Conclusion: reject R158. Do not continue monthly-negative sweep throttling on R155. The next branch should not be another month-control overlay; it should either add a genuinely independent high-frequency signal with R155 guards, or use an offline sequential path simulator to screen candidates before MT5.

## Round159: high-frequency R79 crossed with R155 defensive features

Hypothesis: R79 is the best 720-day fixed-window branch that reaches the `>5/day` frequency target (`3565` trades, `5.0/day`, `$52774.14`). Adding the two weakly useful R155 features, M15 entry momentum and H1/H20 sweep half-size, might preserve R79's frequency while reducing high-balance 2026 drawdown. A second variant adds R155-style high-balance early monthly loss stop.

Implementation / validation:

- Added `v11_r159_j2_r79_m15_h1h20_soft`: R79 equivalent base, M15 entry momentum, H1/H20 sweep `0.50x`.
- Added `v11_r159_j2_r79_m15_h1h20_early8`: same plus high-balance early monthly loss stop after 8 trades at `1%`.
- R79 did not have a YAML anchor, so the implementation inherits `v11_r78_j2_r71_depth50_bal1000` and explicitly restores R79's shallow-confirm sweep cluster.
- `.set` mapping checked: R79 shallow cluster, M15 momentum, H1/H20 cluster, and early8 inputs all emitted correctly.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r79_j2_r78_shallow_confirm_soft` | high-frequency reference | 3565 | 5.0 | 41.8% | 1.36 | $52774.14 | `ob=653/+44.12R`, `sweep=2912/-60.56R` | 9 | frequency target only |
| `v11_r159_j2_r79_m15_h1h20_soft` | R79 + M15 + H1/H20 sweep half | 3397 | 4.7 | 41.8% | 1.44 | $54362.22 | `ob=627/+40.10R`, `sweep=2770/-53.55R` | 9 | invalid |
| `v11_r159_j2_r79_m15_h1h20_early8` | R159 + high-balance early8 | 3211 | 4.5 | 41.9% | 1.61 | $59440.67 | `ob=602/+44.45R`, `sweep=2609/-45.57R` | 9 | invalid |

Diagnosis:

- The cross improves balance over R79 by `$1588` to `$6667`, and early8 successfully limits 2026-05 from around `-$6040` to `-$965`.
- It does not solve the real high-frequency failure: sweep remains negative (`-45R` to `-54R`) and 2026-01/02/03 still lose heavily.
- Frequency falls below the target (`4.7/day` and `4.5/day`), so the improvement comes from defensive trimming, not a better high-frequency signal.
- This confirms the current split: R155 is the best balance path; R79 is the best frequency path; static defensive overlays cannot bridge the two.

Conclusion: reject R159 as a goal-reaching branch. However, keep one useful insight: ordinary OB remains positive even on high-frequency branches, while sweep is the recurring leak. Next test should try increasing R155's regular OB frequency without adding loose sweep exposure, for example staged OB depth relaxation on top of R155.

## Round160: R155 with staged regular-OB depth relaxation

Hypothesis: R155's ordinary OB stream is consistently positive (`+61.34R`), while sweep is only mildly positive and fragile. Relaxing regular OB depth after the account survives startup might add frequency through OB rather than through loose sweep.

Implementation / validation:

- Added `v11_r160_j2_r155_depth50_bal1000`: R155 base with `entry_depth_pct=0.50` after balance reaches `$1000`.
- Added `v11_r160_j2_r155_depth55_bal1000`: R155 base with `entry_depth_pct=0.55` after balance reaches `$1000`.
- `.set` mapping checked: R155 M15 momentum, sweep no-hours, H1/H20 cluster, monthly guards, and depth relax all emitted correctly.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r155_j2_r154_m15_h1h20_soft` | baseline | 2461 | 3.4 | 42.9% | 1.56 | $94776.12 | `ob=538/+61.34R`, `sweep=1923/+19.11R` | 7 | current best |
| `v11_r160_j2_r155_depth50_bal1000` | depth `0.50` after `$1000` | 2478 | 3.4 | 42.0% | 1.47 | $60858.20 | `ob=524/+47.01R`, `sweep=1954/-56.43R` | 10 | invalid |
| `v11_r160_j2_r155_depth55_bal1000` | depth `0.55` after `$1000` | 2570 | 3.6 | 41.3% | 1.45 | $50092.57 | `ob=542/+40.14R`, `sweep=2028/-89.38R` | 10 | invalid |

Diagnosis:

- Depth relaxation did not actually add useful OB frequency. OB count is flat to lower (`524/542` vs `538`) and OB R worsens.
- The damaging effect comes through shared sequential state: sweep flips from `+19.11R` on R155 to `-56.43R` and `-89.38R`.
- Frequency barely moves (`3.4/day` to `3.6/day`), nowhere near `>5/day`, while losing months increase from `7` to `10`.
- This is another example where a locally plausible OB knob changes the shared OB/sweep lifecycle path and damages compounding.

Conclusion: reject R160. Do not continue entry-depth relaxation on R155. The remaining path likely needs a new independent signal/regime mechanism, not more static filters, month overlays, add-ons, or depth tweaks on the same OB/sweep lifecycle.

## Round161-162: ordinary-OB-only size increase

Hypothesis: whole-strategy risk scaling failed because it also scales fragile sweep exposure. R155 ordinary OB is the most stable positive stream (`+61R`), so scaling only ordinary OB might push balance over `$100k` without loosening sweep.

Implementation / validation:

- Added `InpOBPosMult` / `ob_pos_mult`, default `1.0`, applied only to ordinary OB and not to sweep/range/HTFPB.
- After R161 showed startup collapse, added `InpOBPosMultMinBalance` / `ob_pos_mult_min_balance`, default `0.0`, so OB-only scaling can start only after a balance threshold.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.
- Native MetaEditor compile passed: `0 errors, 0 warnings`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r155_j2_r154_m15_h1h20_soft` | baseline | 2461 | 3.4 | 42.9% | 1.56 | $94776.12 | `ob=538/+61.34R`, `sweep=1923/+19.11R` | 7 | current best |
| `v11_r161_j2_r155_ob115` | ordinary OB `1.15x` from startup | 197 | 0.3 | 45.2% | 0.84 | -$4.10 | `ob=84/+6.88R`, `sweep=113/+15.47R` | n/a | invalid |
| `v11_r161_j2_r155_ob125` | ordinary OB `1.25x` from startup | 183 | 0.3 | 48.1% | 0.82 | -$13.18 | `ob=77/+10.91R`, `sweep=106/+16.97R` | n/a | invalid |
| `v11_r162_j2_r155_ob115_bal60` | ordinary OB `1.15x` after `$60000` | 2461 | 3.4 | 42.9% | 1.55 | $94248.57 | `ob=538/+61.51R`, `sweep=1923/+19.11R` | 7 | invalid |
| `v11_r162_j2_r155_ob125_bal60` | ordinary OB `1.25x` after `$60000` | 2461 | 3.4 | 42.9% | 1.55 | $93975.01 | `ob=538/+61.59R`, `sweep=1923/+19.11R` | 7 | invalid |

Diagnosis:

- Starting OB-only scaling from `$200` breaks survival immediately. Even though R attribution remains positive, margin/path dynamics collapse before the strategy reaches its compounding regime.
- Delaying OB scaling until `$60000` avoids the startup failure and preserves trade count/month count, but final balance still drops by `$528` to `$801`.
- The R total is slightly higher on R162, yet balance is lower. This repeats the core lesson: small positive R changes can still damage the compounding sequence.
- OB-only scaling is therefore not the missing `$100k` lever.

Conclusion: reject R161/R162 as strategy candidates. Keep the new `ob_pos_mult` inputs only as default-off experimental infrastructure; do not continue simple OB leverage scans unless paired with a genuinely new classifier.

## Round163: R155 with sweep early-confirm size reduction

Hypothesis: offline attribution on R155 showed sweep entries confirmed within `0-10s` were a net negative bucket (`526` trades, about `-14.43R`), while OB entries in the same confirmation-speed bucket were positive. A sweep-only early-confirm size reduction might improve the path without touching ordinary OB.

Implementation / validation:

- Added `v11_r163_j2_r155_swp_early10_soft`: R155 base, sweep entries with `bounce_sec <= 10` reduced to `0.35x`.
- Added `v11_r163_j2_r155_swp_early10_cut`: same, but sweep entries with `bounce_sec <= 10` disabled.
- `.set` mapping checked: M15 entry momentum, H1/H20 sweep soft cluster, early-bounce window, and magic numbers all emitted correctly.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r155_j2_r154_m15_h1h20_soft` | baseline | 2461 | 3.4 | 42.9% | 1.56 | $94776.12 | `ob=538/+61.34R`, `sweep=1923/+19.11R` | 7 | current reference |
| `v11_r163_j2_r155_swp_early10_soft` | sweep `0-10s` at `0.35x` | 2295 | 3.2 | 43.5% | 1.56 | $95138.02 | `ob=536/+59.18R`, `sweep=1759/+37.57R` | 8 | partial improvement |
| `v11_r163_j2_r155_swp_early10_cut` | sweep `0-10s` disabled | 2196 | 3.0 | 43.1% | 1.44 | $48443.50 | `ob=525/+41.53R`, `sweep=1671/-0.26R` | 10 | invalid |

Diagnosis:

- The soft variant is the first recent candidate to edge above R155's final balance (`+$361.90`) and improves sweep R from `+19.11R` to `+37.57R`.
- The improvement is too narrow for the objective: frequency drops from `3.4/day` to `3.2/day`, and losing months increase from `7` to `8`.
- The hard cut is strongly invalid. Removing the early-confirm sweep bucket damages sequence participation and collapses final balance to `$48443.50`.
- Therefore `0-10s` sweep is not pure noise. It contains enough right-tail participation that it should be throttled, not removed.
- R163 also changes the month profile: it fixes R155's tiny 2024-09 loss, but adds small losing months in 2025-03 and 2025-04. That is not acceptable for the monthly objective.

Conclusion: keep `v11_r163_j2_r155_swp_early10_soft` as a useful component and a new local high-balance reference, but do not promote it to final candidate. Next work should refine the early-confirm throttle by adding a second condition, rather than cutting all fast sweep entries or applying more broad monthly overlays.

## Round164: R155 with early-confirm sweep reduction only in bad hours

Hypothesis: R163 improved balance but also reduced strong positive early-confirm sweep hours such as `h13` and `h08`. Adding `sweep_early_bounce_hours` should allow the early-confirm throttle to apply only to the offline bad hours while preserving the positive fast-sweep hours.

Implementation / validation:

- Added `InpSweepEarlyBounceHours` / `sweep_early_bounce_hours`, default `""`. Empty means the existing early-bounce multiplier still applies to all hours, preserving R163 behavior.
- Added `v11_r164_j2_r155_swp_e10_bad5`: R155/R163 early `0-10s` sweep `0.35x`, only hours `0,3,9,14,20`.
- Added `v11_r164_j2_r155_swp_e10_bad7`: same, only hours `0,3,4,9,14,17,20`.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.
- Native MetaEditor compile passed: `0 errors, 0 warnings`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r155_j2_r154_m15_h1h20_soft` | baseline | 2461 | 3.4 | 42.9% | 1.56 | $94776.12 | `ob=538/+61.34R`, `sweep=1923/+19.11R` | 7 | reference |
| `v11_r163_j2_r155_swp_early10_soft` | all-hour early `0-10s` sweep `0.35x` | 2295 | 3.2 | 43.5% | 1.56 | $95138.02 | `ob=536/+59.18R`, `sweep=1759/+37.57R` | 8 | local high balance |
| `v11_r164_j2_r155_swp_e10_bad5` | early throttle only h0/h3/h9/h14/h20 | 2575 | 3.6 | 41.8% | 1.49 | $52242.73 | `ob=529/+42.54R`, `sweep=2046/-54.85R` | 11 | invalid |
| `v11_r164_j2_r155_swp_e10_bad7` | early throttle only h0/h3/h4/h9/h14/h17/h20 | 2574 | 3.6 | 41.8% | 1.49 | $52242.15 | `ob=529/+42.54R`, `sweep=2045/-52.86R` | 11 | invalid |

Diagnosis:

- The hour-scoped throttle catastrophically breaks the R155/R163 path. Balance drops to about `$52k`, sweep flips deeply negative, and losing months increase to `11`.
- This is not a simple "bad hours removed, good hours retained" problem. Changing early entries in only a subset of hours alters the later OB/sweep lifecycle and opens a worse sequence with more sweep trades.
- The all-hour throttle in R163 is safer precisely because it changes the fast-sweep stream consistently. Selective hour throttling creates path instability.
- R164 is another warning that offline bucket selection is unreliable unless it predicts sequential state effects.

Conclusion: reject R164. Keep the new `sweep_early_bounce_hours` input only as default-off infrastructure, but do not continue static hour-scoped early-confirm throttles on R155.

## Round165: R155 all-hour early-confirm sweep multiplier sweep

Hypothesis: R163's `0.35x` early-confirm sweep throttle may not be the best all-hour multiplier. Testing nearby values should reveal whether the improvement is robust or a narrow path artifact.

Implementation / validation:

- Added `v11_r165_j2_r155_swp_e10_050`: R155/R163 all-hour `0-10s` sweep at `0.50x`.
- Added `v11_r165_j2_r155_swp_e10_025`: R155/R163 all-hour `0-10s` sweep at `0.25x`.
- `.set` mapping checked: `InpSweepEarlyBounceHours` is empty for both variants, so the multiplier applies to all hours.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.
- Re-ran `v11_r163_j2_r155_swp_early10_soft` after the new input/compile and confirmed the result is stable at `$95138.02`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r155_j2_r154_m15_h1h20_soft` | baseline | 2461 | 3.4 | 42.9% | 1.56 | $94776.12 | `ob=538/+61.34R`, `sweep=1923/+19.11R` | 7 | reference |
| `v11_r163_j2_r155_swp_early10_soft` | early `0-10s` sweep `0.35x` | 2295 | 3.2 | 43.5% | 1.56 | $95138.02 | `ob=536/+59.18R`, `sweep=1759/+37.57R` | 8 | local best |
| `v11_r165_j2_r155_swp_e10_050` | early `0-10s` sweep `0.50x` | 2519 | 3.5 | 41.9% | 1.49 | $51594.23 | `ob=529/+41.71R`, `sweep=1990/-39.41R` | 11 | invalid |
| `v11_r165_j2_r155_swp_e10_025` | early `0-10s` sweep `0.25x` | 2515 | 3.5 | 42.1% | 1.50 | $53276.59 | `ob=528/+41.21R`, `sweep=1987/-29.21R` | 9 | invalid |

Diagnosis:

- The all-hour multiplier response is highly non-linear. `0.35x` is stable and slightly better than R155, while nearby `0.25x` and `0.50x` both open a much worse path.
- R165 increases trade count but flips sweep negative and creates large high-balance losses in 2025-11 and 2026-01/02/03/05.
- This confirms that R163 is a narrow path sweet spot, not a smooth parameter family.

Conclusion: reject R165. Keep `v11_r163_j2_r155_swp_early10_soft` as the only useful early-confirm component. Do not continue scalar sweeps around this multiplier unless paired with a separate regime classifier.

## Round166: R163 early-confirm throttle on high-frequency R79/R159 branches

Updated objective note: the frequency target changed from `>5/day` to `>4/day`. This makes the high-frequency R79/R159 family relevant again, because R155/R163 are still below `4/day` even though they have the best balance path.

Hypothesis: R79 reaches the new frequency target but leaks through sweep. R163's all-hour `0-10s` sweep `0.35x` throttle might reduce that sweep leak while preserving enough frequency.

Implementation / validation:

- Added `v11_r166_j2_r79_swp_e10_035`: R79 high-frequency base plus all-hour early-confirm sweep `0-10s` at `0.35x`.
- Added `v11_r166_j2_r159_swp_e10_035`: R159 high-frequency cross plus the same early-confirm throttle.
- `.set` mapping checked for R79 shallow-confirm sweep cluster, R159 M15/H1H20 features, early-confirm throttle, and magic numbers.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r79_j2_r78_shallow_confirm_soft` | high-frequency reference | 3565 | 5.0 | 41.8% | 1.36 | $52774.14 | `ob=653/+44.12R`, `sweep=2912/-60.56R` | 9 | frequency only |
| `v11_r159_j2_r79_m15_h1h20_early8` | best prior high-frequency defensive cross | 3211 | 4.5 | 41.9% | 1.61 | $59440.67 | `ob=602/+44.45R`, `sweep=2609/-45.57R` | 9 | current high-frequency balance reference |
| `v11_r166_j2_r79_swp_e10_035` | R79 + early `0-10s` sweep `0.35x` | 3352 | 4.7 | 41.9% | 1.43 | $54050.00 | `ob=628/+40.46R`, `sweep=2724/-39.33R` | 9 | invalid |
| `v11_r166_j2_r159_swp_e10_035` | R159 + early `0-10s` sweep `0.35x` | n/a | n/a | n/a | n/a | n/a | n/a | n/a | timed out at 1200s |

Diagnosis:

- R166_R79 satisfies the revised frequency target (`4.7/day`) and improves the R79 sweep leak (`-60.56R` to `-39.33R`), but final balance only reaches `$54050.00`.
- The high-frequency family remains split: OB is positive (`+40.46R`) while sweep is still net negative despite multiple throttles.
- Losing months remain high (`9`), including large high-balance losses in 2026-01/02/03/05.
- The R159+early10 run timed out and produced no usable report. Do not treat it as evidence either way; rerun only if a later branch needs it.

Conclusion: R166 is not a goal-reaching candidate. Under the revised `>4/day` target, the best high-frequency reference remains `v11_r159_j2_r79_m15_h1h20_early8` (`4.5/day`, `$59440.67`). Next work should test whether modest risk scaling on that frequency-valid branch can reach `$100k` without startup or monthly collapse.

## Round167: modest risk scaling on the frequency-valid R159 early8 branch

Hypothesis: under the updated `>4/day` objective, R159 early8 is frequency-valid (`4.5/day`) but only reaches `$59440.67`. If the branch mainly lacks exposure, modest risk increases to `2.5%` or `3.0%` might push it toward `$100k`.

Implementation / validation:

- Added `v11_r167_j2_r159_early8_risk25`: R159 early8 with `risk_percent=2.5`.
- Added `v11_r167_j2_r159_early8_risk30`: R159 early8 with `risk_percent=3.0`.
- `.set` mapping checked: M15 entry momentum, R79 shallow-confirm cluster, H1/H20 soft cluster, early8 monthly stop, and risk percent are all emitted correctly.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r159_j2_r79_m15_h1h20_early8` | high-frequency reference | 3211 | 4.5 | 41.9% | 1.61 | $59440.67 | `ob=602/+44.45R`, `sweep=2609/-45.57R` | 9 | reference |
| `v11_r167_j2_r159_early8_risk25` | risk `2.5%` | 1716 | 2.4 | 41.5% | 0.80 | $4423.59 | `ob=498/+52.28R`, `sweep=1218/-29.60R` | 10 | invalid |
| `v11_r167_j2_r159_early8_risk30` | risk `3.0%` | 995 | 1.4 | 44.0% | 1.08 | $745.46 | `ob=445/+61.50R`, `sweep=550/+33.71R` | 11 | invalid |

Diagnosis:

- Risk scaling destroys both frequency and balance. The account path contracts early, so the strategy sees far fewer trades rather than compounding faster.
- The R totals are not enough to judge viability; the path/margin dynamics dominate once risk rises from `2%`.
- R167 rules out simple exposure scaling on the high-frequency family.

Conclusion: reject R167. Do not continue risk scaling on R79/R159. The next sensible split is: keep R163 as the near-`$100k` balance reference and find a low-damage way to add frequency, or find a genuinely new high-frequency signal with positive expectancy.

## Round168: R163 headline risk lowered to 2.05/2.10 by mistake

Hypothesis at the time: R163 was assumed to be near a `2%` headline-risk branch, so `2.05%` / `2.10%` looked like a tiny increase that might push the `$95138.02` balance over `$100k`.

Correction: R163 actually inherits `risk_percent=5.4`, with startup risk controlled by `low_balance_pos_mult=0.39` until balance reaches `$1000`. Therefore R168 did not raise risk; it lowered mature-regime headline risk from `5.4%` to roughly `2.05-2.10%`.

Implementation / validation:

- Added `v11_r168_j2_r163_risk205`: R163 with `risk_percent=2.05`.
- Added `v11_r168_j2_r163_risk210`: R163 with `risk_percent=2.10`.
- `.set` check exposed the correction: R163 baseline emits `InpRiskPercent=5.4`.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r163_j2_r155_swp_early10_soft` | baseline, headline risk `5.4` | 2295 | 3.2 | 43.5% | 1.56 | $95138.02 | `ob=536/+59.18R`, `sweep=1759/+37.57R` | 8 | reference |
| `v11_r168_j2_r163_risk205` | headline risk `2.05` | 626 | 0.9 | 45.8% | 1.28 | $796.67 | `ob=363/+45.26R`, `sweep=263/-3.82R` | n/a | invalid |
| `v11_r168_j2_r163_risk210` | headline risk `2.10` | 637 | 0.9 | 45.5% | 1.27 | $797.28 | `ob=367/+42.75R`, `sweep=270/-4.97R` | n/a | invalid |

Diagnosis:

- Lowering mature-regime risk destroys the compounding path and drops frequency below `1/day`.
- This round mainly fixed our mental model: R163's balance comes from a high headline risk after startup survival, not from a flat `2%` profile.
- Any real "slight risk increase" test should be around `5.4`, e.g. `5.45` / `5.50`, not around `2.0`.

Conclusion: reject R168. Treat it as a parameter-interpretation correction, not a failed risk-increase test.

## Round169: true slight headline risk increase on R163

Hypothesis: after correcting the R168 risk misunderstanding, R163 might cross `$100k` with a tiny headline-risk increase from `5.4%` to `5.45%` or `5.50%`, while keeping the same startup low-balance guard.

Implementation / validation:

- Added `v11_r169_j2_r163_risk545`: R163 with `risk_percent=5.45`.
- Added `v11_r169_j2_r163_risk550`: R163 with `risk_percent=5.50`.
- `.set` mapping checked: `InpRiskPercent=5.45/5.50`, `InpLowBalancePosMult=0.39`, early-confirm sweep `0.35x`, and H1/H20 soft cluster are emitted correctly.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.
- The first `5.45` batch run timed out, then a single-strategy rerun completed normally.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r163_j2_r155_swp_early10_soft` | baseline risk `5.4` | 2295 | 3.2 | 43.5% | 1.56 | $95138.02 | `ob=536/+59.18R`, `sweep=1759/+37.57R` | 8 | reference |
| `v11_r169_j2_r163_risk545` | risk `5.45` | 2531 | 3.5 | 42.2% | 1.48 | $48781.58 | `ob=529/+43.04R`, `sweep=2002/-23.50R` | 9 | invalid |
| `v11_r169_j2_r163_risk550` | risk `5.50` | 2533 | 3.5 | 42.1% | 1.48 | $49094.87 | `ob=529/+43.01R`, `sweep=2004/-22.73R` | 9 | invalid |

Diagnosis:

- R163 is extremely path-sensitive around the mature-risk value. Raising headline risk by only `0.05` flips sweep from `+37.57R` to negative and cuts final balance roughly in half.
- The extra trades are not useful frequency; they come from a worse sequence with more sweep leakage.
- This rules out simple risk nudging as a way to cross `$100k`.

Conclusion: reject R169. Keep R163 risk at `5.4`. Future work should not touch core risk unless a separate classifier changes which trades are allowed.

## Round170: ordinary OB weak-hour overlay on R163

Hypothesis: R163's ordinary OB attribution is positive overall, but OB entries in hours `7/8/9` are negative in offline attribution. A signal-specific weak-hour overlay might reduce bad-month damage without touching the positive sweep stream.

Implementation / validation:

- Added `v11_r170_j2_r163_ob_h789_soft`: R163 plus `ob_bad_hours="7,8,9"` at `0.35x`.
- Added `v11_r170_j2_r163_ob_h789_cut`: same but `ob_bad_hour_mult=0.0`.
- `.set` mapping checked: ordinary OB weak hours, early-confirm sweep, and H1/H20 sweep soft cluster are emitted correctly.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r163_j2_r155_swp_early10_soft` | baseline | 2295 | 3.2 | 43.5% | 1.56 | $95138.02 | `ob=536/+59.18R`, `sweep=1759/+37.57R` | 8 | reference |
| `v11_r170_j2_r163_ob_h789_soft` | all OB h7/8/9 at `0.35x` | 2255 | 3.1 | 42.0% | 1.94 | $89209.86 | `ob=489/+54.86R`, `sweep=1766/+3.18R` | 7 | invalid |
| `v11_r170_j2_r163_ob_h789_cut` | all OB h7/8/9 disabled | 2307 | 3.2 | 43.2% | 1.09 | $51282.06 | `ob=476/+64.62R`, `sweep=1831/+9.29R` | 11 | invalid |

Diagnosis:

- R170 soft improves headline PF and reduces losing months from `8` to `7`, but lowers final balance by about `$5928`.
- Sweep contribution collapses from `+37.57R` to `+3.18R` even though the direct filter targets only OB. This confirms again that changing OB participation alters the later sweep path.
- The hard cut is strongly invalid and creates a 2026 high-balance loss cluster similar to other over-filtered variants.

Conclusion: reject R170. A broad OB hour overlay is too coarse. If this branch continues, only modify the existing R163 `bad_cluster3` bucket more carefully; do not add separate all-OB hour filters.

## Round171: tighten existing R163 OB bad cluster3

Hypothesis: R163 already has a targeted OB bad cluster3 (`hours 7/8/9/17`, `risk 100-400`, `confirm < -0.6`, `signal=ob`) at `0.35x`. Tightening this existing bucket might reduce weak OB losses with less path disruption than the broad R170 hour overlay.

Implementation / validation:

- Added `v11_r171_j2_r163_ob_cluster3_m20`: R163 with `bad_cluster3_mult=0.20`.
- Added `v11_r171_j2_r163_ob_cluster3_cut`: R163 with `bad_cluster3_mult=0.0`.
- `.set` mapping checked: cluster3, early-confirm sweep, H1/H20 sweep cluster, and magic numbers are emitted correctly.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r163_j2_r155_swp_early10_soft` | baseline cluster3 `0.35x` | 2295 | 3.2 | 43.5% | 1.56 | $95138.02 | `ob=536/+59.18R`, `sweep=1759/+37.57R` | 8 | reference |
| `v11_r171_j2_r163_ob_cluster3_m20` | cluster3 `0.20x` | 2531 | 3.5 | 42.0% | 1.51 | $50684.61 | `ob=523/+45.05R`, `sweep=2008/-22.11R` | 9 | invalid |
| `v11_r171_j2_r163_ob_cluster3_cut` | cluster3 disabled | n/a | n/a | n/a | n/a | n/a | n/a | n/a | timed out / no report |

Diagnosis:

- Tightening cluster3 from `0.35x` to `0.20x` is enough to flip the sweep path negative and cut final balance almost in half.
- The extra trade count (`3.5/day`) is not useful; it comes from a worse sequence with high-balance 2026 losses.
- The cut variant got stuck and produced no report before the outer command timed out; the m20 result is already sufficient to reject this direction.

Conclusion: reject R171. Do not continue static OB bad-cluster tightening on R163.

## Round172: tighten R163 risk 150-200 bucket

Hypothesis: R163's `risk 150-200` bucket remains negative in offline attribution (`-26.83R`) even though it is already reduced by `bad_risk_mult=0.60`. Tightening that generic risk bucket might reduce bad-month damage without targeting hours.

Implementation / validation:

- Added `v11_r172_j2_r163_bad_risk035`: R163 with `bad_risk_mult=0.35`.
- Added `v11_r172_j2_r163_bad_risk_cut`: R163 with `bad_risk_mult=0.0`.
- `.set` mapping checked: `InpBadRiskMin=150`, `InpBadRiskMax=200`, new multiplier, early-confirm sweep, and H1/H20 cluster are emitted correctly.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r163_j2_r155_swp_early10_soft` | baseline `bad_risk_mult=0.60` | 2295 | 3.2 | 43.5% | 1.56 | $95138.02 | `ob=536/+59.18R`, `sweep=1759/+37.57R` | 8 | reference |
| `v11_r172_j2_r163_bad_risk035` | risk 150-200 at `0.35x` | 2567 | 3.6 | 41.9% | 1.48 | $53929.66 | `ob=527/+40.22R`, `sweep=2040/-18.24R` | 10 | invalid |
| `v11_r172_j2_r163_bad_risk_cut` | risk 150-200 disabled | 1898 | 2.6 | 43.5% | 1.00 | $27803.82 | `ob=442/+34.07R`, `sweep=1456/+28.19R` | 11 | invalid |

Diagnosis:

- Tightening an offline-negative risk bucket again damages the sequential path. The soft variant increases trade count but flips sweep negative and halves balance.
- The hard cut reduces frequency and leaves PF at `1.00`, far below target quality.
- This reinforces the main diagnosis from R164/R169/R171: R163's weak-looking buckets often carry path-state value that is not captured by simple R aggregation.

Conclusion: reject R172. Stop static bucket tightening on R163; future improvement needs a true pre-entry regime feature or a separate execution lane that does not perturb the primary OB/sweep path.

## Round173: loosen R163 same-OB reentry capacity

Hypothesis: R163 misses the revised frequency target (`3.2/day` vs `>4/day`). Instead of adding loose external signals, allow more same-OB follow-up entries with shorter cooldown, hoping to add frequency inside the existing signal family.

Implementation / validation:

- Added `v11_r173_j2_r163_reentry5_cd15`: R163 with `max_entries_per_ob=5`, `ob_reentry_cooldown_min=15`.
- Added `v11_r173_j2_r163_reentry6_cd15`: R163 with `max_entries_per_ob=6`, `ob_reentry_cooldown_min=15`.
- `.set` mapping checked: reentry capacity/cooldown, early-confirm sweep, H1/H20 cluster, and magic numbers are emitted correctly.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r163_j2_r155_swp_early10_soft` | baseline reentry `4`, cooldown `30m` | 2295 | 3.2 | 43.5% | 1.56 | $95138.02 | `ob=536/+59.18R`, `sweep=1759/+37.57R` | 8 | reference |
| `v11_r173_j2_r163_reentry5_cd15` | reentry `5`, cooldown `15m` | 1280 | 1.8 | 46.4% | 0.92 | -$662.69 | `ob=442/+39.02R`, `sweep=838/+37.16R` | n/a | invalid |
| `v11_r173_j2_r163_reentry6_cd15` | reentry `6`, cooldown `15m` | 1305 | 1.8 | 45.7% | 0.96 | -$332.06 | `ob=450/+37.54R`, `sweep=855/+25.25R` | n/a | invalid |

Diagnosis:

- Loosening reentry does not add usable frequency. It breaks the early survival/compounding path and drives balance negative.
- The lower final trade count indicates the account path contracts before the strategy reaches the high-frequency regime.
- R163's reentry/cooldown setting is part of its survival structure, not a safe frequency throttle.

Conclusion: reject R173. Do not continue loosening same-OB reentry on R163.

## Round174: same-OB reentry with reduced reentry size

Hypothesis: R173 failed because additional same-zone reentries were full-size. Add a default-off `reentry_pos_mult` so second and later entries from the same zone can be tested as a small frequency add-on.

Implementation / validation:

- Added `InpReentryPosMult` / `reentry_pos_mult`, default `1.0`, applied only when `zone.entry_count > 0`.
- Added `v11_r174_j2_r163_reentry5_cd15_m10`: R173 reentry settings with reentries at `0.10x`.
- Added `v11_r174_j2_r163_reentry5_cd15_m20`: same with reentries at `0.20x`.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.
- Native MetaEditor compile passed: `0 errors, 0 warnings`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r163_j2_r155_swp_early10_soft` | baseline | 2295 | 3.2 | 43.5% | 1.56 | $95138.02 | `ob=536/+59.18R`, `sweep=1759/+37.57R` | 8 | reference |
| `v11_r174_j2_r163_reentry5_cd15_m10` | reentry `5`, cooldown `15m`, reentries `0.10x` | 793 | 1.1 | 42.9% | 0.95 | $419.53 | `ob=370/+50.69R`, `sweep=423/+8.22R` | n/a | invalid |
| `v11_r174_j2_r163_reentry5_cd15_m20` | reentry `5`, cooldown `15m`, reentries `0.20x` | 123 | 0.2 | 43.1% | 0.63 | -$2.33 | `ob=73/+6.23R`, `sweep=50/-7.96R` | n/a | invalid |

Diagnosis:

- Even tiny reentry sizing does not make same-OB reentry a safe frequency add-on. The act of permitting extra reentries changes zone/monitor lifecycle and breaks the early path.
- This rules out the same-zone reuse family for R163.

Conclusion: reject R174. Keep `reentry_pos_mult` as default-off infrastructure, but do not continue reentry-based frequency scans.

## 2026-05-24 Round176-R177: R163 ENTRY_DIAG and sweep age bad-cluster probe

Baseline status:
- Best current BTC candidate remains `v11_r163_j2_r155_swp_early10_soft`: `2295` trades, daily `3.2`, win `43.5%`, PF `1.56`, balance `$95138.02`, losing months `8`.
- This is close to the `$100k` target but still below daily `>4` and far from month-by-month profitability.

R176 instrumentation:
- Added `v11_r176_j2_r163_debug_probe` with `enable_entry_debug: true`; result exactly matched R163: `2295` trades, balance `$95138.02`.
- Manual log segment extraction found `2301` `ENTRY_DIAG` lines and `2295` parsed trades, so debug logging is behavior-neutral and usable for regime diagnosis.
- Key aggregates from the R176 trade fields:
  - `h1=false`: `764` trades, `+32.51R`, pnl proxy `+$34046.45`.
  - `h1=true`: `1531` trades, `+64.23R`, pnl proxy `+$60972.37`.
  - `cont=1`: `306` trades, `+38.86R`, pnl proxy `+$60896.62`.
  - `cont=0`: `1989` trades, `+57.88R`, pnl proxy `+$34122.20`.
  - Sweep zone age `20-40` bars was strongly negative in the static diagnostic bucket, while very fresh sweep zones were positive.

R177 implementation:
- Added default-off inputs `InpSweepBadAgeMinBars`, `InpSweepBadAgeMaxBars`, `InpSweepBadAgeMult`.
- Added YAML keys `sweep_bad_age_min_bars`, `sweep_bad_age_max_bars`, `sweep_bad_age_mult`.
- Applied the multiplier only to liquidity sweep zones whose age is in `[min, max)` bars.
- Validation: `python -m pytest tests\test_mt5_common.py -q` -> `71 passed`; native MetaEditor compile -> `0 errors, 0 warnings`.

R177 fixed-window MT5 Real Ticks, BTCUSDm, `2024.06.02` to `2026.05.23`:
- `v11_r177_j2_r163_swp_age20_40_m035`: `2179` trades, daily `3.0`, win `43.2%`, PF `1.56`, balance `$95368.88`, losing months `8`; `ob=534/+56.47R`, `sweep=1645/+60.06R`.
- `v11_r177_j2_r163_swp_age20_40_cut`: `1911` trades, daily `2.7`, win `41.8%`, PF `1.68`, balance `$48112.24`, losing months `10`; `ob=520/+33.21R`, `sweep=1391/+8.24R`.

Conclusion:
- Reject R177 as a target solution. The age bad-cluster is a useful diagnostic clue, but hard filtering it breaks the sweep path and soft filtering only gives a tiny balance improvement while reducing frequency.
- Next better candidate: continuation-aware sizing. R176 shows `cont=1` concentrates a large share of pnl proxy on only `306` trades, so test a default-off continuation position multiplier before doing more static bucket filters.

## 2026-05-24 Round178: continuation sizing probe

Hypothesis: R176 showed `cont=1` as a concentrated positive cluster (`306` trades, `+38.86R`, pnl proxy around `+$60.9k`), so a default-off continuation multiplier may push R163 above the updated profit threshold without changing signal generation.

Implementation:
- Added `InpContinuationPosMult` / `continuation_pos_mult`, default `1.0`.
- Applied only when `zone.is_continuation` is true; `<=0` filters.
- Validation: `python -m pytest tests\test_mt5_common.py -q` -> `71 passed`; native MetaEditor compile -> `0 errors, 0 warnings`.

Fixed-window MT5 Real Ticks, BTCUSDm, `2024.06.02` to `2026.05.23`:
- `v11_r178_j2_r163_cont_m120`: `2611` trades, daily `3.6`, win `41.9%`, PF `1.47`, balance `$52205.27`; digest `sweep=2080/-32.06R`, `ob=531/+42.00R`; losing months `9`.
- `v11_r178_j2_r163_cont_m135`: `2593` trades, daily `3.6`, win `42.7%`, PF `1.12`, balance `$12584.21`; digest `sweep=1992/-19.37R`, `ob=601/+43.25R`; losing months `10`.

Conclusion: reject R178. The continuation multiplier changes the execution path enough to turn sweep negative; do not continue position-mult scans on static `cont` without a second path-stability guard.

## 2026-05-24 Round179: R159 high-frequency guard pack

Updated objective: daily trades `>4`, profit `>90000u`, every month profitable. R163/R177 are near the profit threshold but low frequency and still have losing months, while R159/R166 satisfy frequency but not profit.

Hypothesis: use R159 as the high-frequency base, then add R163-style protection: tighter `monthly_loss_stop_pct`, monthly profit lock, early sweep reduction, and OB bad-hour guard.

Fixed-window MT5 Real Ticks, BTCUSDm, `2024.06.02` to `2026.05.23`:
- `v11_r179_j2_r159_guard_pack`: `3005` trades, daily `4.2`, win `42.9%`, PF `1.52`, balance `$36960.07`.
- `v11_r179_j2_r159_guard_mneg035`: `3105` trades, daily `4.3`, win `42.6%`, PF `1.45`, balance `$52351.82`; digest `ob=572/+48.31R`, `sweep=2533/-17.67R`.

Conclusion: reject R179. It clears the frequency constraint but still inherits the high-frequency sweep leak and cannot approach the `>90000u` profit threshold.

## 2026-05-24 Round180: R163 layered-entry frequency probe

Hypothesis: instead of adding a new low-quality signal source, split/extend R163 entries with one small deeper layered limit order to raise trade count while keeping the main signal path.

Fixed-window MT5 Real Ticks, BTCUSDm, `2024.06.02` to `2026.05.23`:
- `v11_r180_j2_r163_layer2_micro`: `317` trades, daily `0.4`, balance `$0.26`.
- `v11_r180_j2_r163_layer2_tiny`: `320` trades, daily `0.4`, balance `$0.55`.

Conclusion: reject and seal this direction. The current layered pending-order implementation is not a low-pollution trade-count add-on; it changes execution, pending-order, and concurrency state enough to destroy the R163 path.

## 2026-05-24 Round181: same-signal micro market entry probe

Hypothesis: if layered pending orders fail because they alter pending-order and fill timing, a same-signal micro market entry after the primary fill might raise real trade count while avoiding new zones, monitors, or timeframe reads.

Implementation:
- Added default-off inputs `InpMicroEntryCount`, `InpMicroEntryLotMult`, `InpMicroEntryMaxLotSize`.
- Micro entries are sent only after the primary order succeeds, with the same SL/TP and a capped lot.
- Validation: `python -m pytest tests\test_mt5_common.py -q` -> `71 passed`; native MetaEditor compile -> `0 errors, 0 warnings`.

Fixed-window MT5 Real Ticks, BTCUSDm, `2024.06.02` to `2026.05.23`:
- `v11_r181_j2_r163_micro1_cap001`: `384` trades, daily `0.5`, win `0.3%`, PF `0.44`, balance `$-0.13`.
- `v11_r181_j2_r163_micro2_cap001`: `579` trades, daily `0.8`, win `14.7%`, PF `1.19`, balance `$-2.88`.

Conclusion: reject and seal same-signal order multiplication. Even tiny real副单 can rewrite monthly-entry counts, position concurrency, close sequencing, and account path. Trade-count goals must be solved by genuinely independent positive signal quality or account-level orchestration, not by splitting R163 orders inside the same EA path.

## Round175: relax R163 EntryEngine bounce confirmation

Hypothesis: R163 misses the revised frequency target. Since it already has `outside_bounce_sweet_mult=0.70`, relaxing `bounce_pct` could allow earlier confirmations while the existing sweet-zone sizing reduces weaker new entries.

Implementation / validation:

- Added `v11_r175_j2_r163_bounce022`: R163 with `bounce_pct=0.22`.
- Added `v11_r175_j2_r163_bounce020`: R163 with `bounce_pct=0.20`.
- `.set` mapping checked: bounce, early-confirm sweep, outside-bounce sweet multiplier, and magic numbers are emitted correctly.
- `python -m pytest tests\test_mt5_common.py -q`: `71 passed`.

Fixed-window MT5 Real Ticks results (`BTCUSDm`, `2024.06.02 ~ 2026.05.23`, initial `$200`):

| Strategy | Change | Trades | Daily | Win | PF | Balance | Signal totals | Losing months | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `v11_r163_j2_r155_swp_early10_soft` | baseline bounce `0.25` | 2295 | 3.2 | 43.5% | 1.56 | $95138.02 | `ob=536/+59.18R`, `sweep=1759/+37.57R` | 8 | reference |
| `v11_r175_j2_r163_bounce022` | bounce `0.22` | 2053 | 2.9 | 43.4% | 0.94 | $31482.13 | `ob=517/+44.42R`, `sweep=1536/+1.56R` | n/a | invalid |
| `v11_r175_j2_r163_bounce020` | bounce `0.20` | 2221 | 3.1 | 42.6% | 1.36 | $43028.21 | `ob=549/+42.70R`, `sweep=1672/+11.85R` | n/a | invalid |

Diagnosis:

- Relaxing bounce does not add frequency; it lowers both trade count and balance relative to R163.
- The R163 `0.25` bounce threshold is another path-sensitive anchor. Moving it earlier changes the subsequent OB/sweep lifecycle rather than adding a clean marginal signal.

Conclusion: reject R175. Stop simple entry-relaxation scans on R163.

## 2026-05-24 Round182-R184: high-balance tail guards and account-level scan

Updated objective remains: BTC fixed-window MT5 Real Ticks (`2024.06.02` to `2026.05.23`) should clear daily trades `>4`, balance `>90000u`, and every month positive.

Current best references before this round:
- `v11_r127_j2_r121_early8_1`: `2499` trades, daily `3.5`, balance `$94575.12`, losing months `7`.
- `v11_r155_j2_r154_m15_h1h20_soft`: `2461` trades, daily `3.4`, balance `$94776.12`, losing months `7`.
- `v11_r163_j2_r155_swp_early10_soft`: `2295` trades, daily `3.2`, balance `$95138.02`, losing months `8`.
- `v11_r177_j2_r163_swp_age20_40_m035`: `2179` trades, daily `3.0`, balance `$95368.88`, losing months `8`.

Account-level/offline scan:
- Existing full-window CSVs do not contain a naturally complementary stream that is positive in both `2026-05` and `2025-07`.
- `R163 + HTFPB` can lift daily count above `4`, but HTFPB is too small and has negative `2025-07`; even scaled to unrealistic size it leaves multiple losing months.
- Broad scan found only HTFPB positive in `2026-05`, and only by about `$1-$2` proxy. Conclusion: stacking existing signal streams does not solve the monthly constraint without new logic or a true external portfolio/scheduler.

Implementation:
- Added default-off `bad_cluster5_*` input slot and YAML mapping so R182 can express one extra narrow bad-cluster filter without overwriting existing R163 clusters.
- Validation: `python -m pytest tests\test_mt5_common.py -q` -> `71 passed`; native MetaEditor compile -> `0 errors, 0 warnings`.

Hypothesis R182:
- Offline R176 debug showed the `2026-05` damage was dominated by one `OB hour20`, `risk 100-150`, `confirm_pos < -1` trade (`-966.69` pnl proxy).
- Filtering that exact cluster appeared to improve realized R163 proxy from about `$95019` to `$95986` and move `2026-05` from `-$967` to about `-$1`.

Fixed-window MT5 Real Ticks:
- `v11_r182_j2_r163_ob20_tail_cut`: `2462` trades, daily `3.4`, win `43.1%`, PF `1.48`, balance `$89824.64`, losing months `8`.
  - `2026-05`: `175` trades, `-$6274.61`.
  - Diagnosis: filtering the large early loss prevented the existing early-month loss stop from firing, released the rest of the bad May path, and made the month much worse.

Hypothesis R183:
- Combine R182 with high-balance continuous early stop after `6` entries, `0.001%` loss, active from balance/peak `80000`, to stop `2026-03` before the two large OB losses and stop R182's released `2026-05` path.

Fixed-window MT5 Real Ticks:
- `v11_r183_j2_r182_hibal_e6`: `2181` trades, daily `3.0`, win `43.8%`, PF `1.55`, balance `$86268.31`, losing months `9`.
  - `2026-03`: `6` trades, `-$11.29`.
  - `2026-04`: `11` trades, `-$4.72` versus R163/R182 April around `+$10.7k`.
  - `2026-05`: `7` trades, `-$0.89`.
  - Diagnosis: the guard successfully caps March/May tail risk, but starts too early and cuts off the April recovery month.

Hypothesis R184:
- Delay the R183 guard to `90000` so April can recover before the high-balance stop activates.

Fixed-window MT5 Real Ticks:
- `v11_r184_j2_r182_hibal90_e6`: `2407` trades, daily `3.3`, win `43.4%`, PF `1.58`, balance `$90191.13`, losing months `8`.
  - `2026-03`: `121` trades, about `-$6909.54`.
  - `2026-04`: `122` trades, about `+$10813.50`.
  - `2026-05`: `7` trades, about `-$0.94`.
  - Diagnosis: delaying the guard preserves April and fixes May, but releases March into a much worse path than R163.

Conclusion:
- Reject R182/R183/R184 as target solutions.
- The useful lesson is structural: removing a large early losing trade can be harmful if that loss was the event that triggered monthly stop. Any future tail filter must either count filtered high-risk events into monthly risk state or use an external scheduler; plain pre-entry filtering rewrites the path.
- Best live candidate remains R163/R177 family for profit, but it still fails daily `>4` and every-month-positive. Frequency/monthly constraints likely need a genuinely independent stream or portfolio-level orchestration, not more same-EA path edits.

## 2026-05-24 Round185: filtered-signal monthly stop

Hypothesis:
- R182 failed because the filtered `2026-05` disaster trade was also the event that made the existing monthly stop useful.
- Add a default-off switch: when a `bad_cluster` hard-filters a signal, optionally lock the rest of the month. R185 enables this only for the narrow R182 `OB hour20 risk 100-150 confirm_pos<-1` filter.

Implementation:
- Added `InpBadClusterFilteredMonthlyStop` and `InpBadClusterFilteredStopMinBalance`.
- When any bad-cluster returns `pos_mult < 0`, the optional handler marks the monthly loss/entry stop as locked if the configured balance/peak threshold is met.
- Validation: `python -m pytest tests\test_mt5_common.py -q` -> `71 passed`; native MetaEditor compile -> `0 errors, 0 warnings`.

Fixed-window MT5 Real Ticks:
- `v11_r185_j2_r182_filter_stop`: `2289` trades, daily `3.2`, win `43.6%`, PF `1.58`, balance `$96108.70`, losing months `7`.
- Monthly change versus R163:
  - `2026-05`: R163 `8` trades / `-$967.23`; R185 `2` trades / `+$3.47`.
  - `2026-03`: unchanged at `8` trades / about `-$870.89`.
  - `2026-04`: preserved at `122` trades / about `+$10690.85`.

Conclusion:
- R185 is the new best balance/profit reference and validates the "filtered event must stop the month" mechanism.
- It still fails the updated target: daily trades remain `3.2` and losing months remain `7`.
- Next target should be the remaining large bad month `2026-03`, but avoid broad h7/h8/h9 OB cuts because R170 already showed those rewrite the path badly. If testing March, use a second narrow filtered-stop cluster for the two `2026-03` hour8 OB tail losses, not a broad hour filter.

## 2026-05-24 Round186: second filtered-stop cluster for March tail

Hypothesis:
- R185 fixed `2026-05` but left `2026-03` at about `-$870`.
- R176 debug showed the March high-balance damage came from two simultaneous `OB hour8` losses with `risk 291-297` and `confirm_pos -1.0~-0.6`.
- Offline scan of R163/R176 trades found this narrow bucket matched only the two March losses, not the 2025 hour8 positive OB samples.

Implementation:
- Added default-off `bad_cluster6_*` input slot and YAML mapping.
- Added `v11_r186_j2_r185_ob8_tail_cut`: R185 plus `bad_cluster6_hours=8`, `risk 291-297`, `confirm -1.0~-0.6`, `signal=ob`, hard filter, with filtered-signal monthly stop inherited.
- Validation: `python -m pytest tests\test_mt5_common.py -q` -> `71 passed`; native MetaEditor compile -> `0 errors, 0 warnings`.

Fixed-window MT5 Real Ticks:
- `v11_r186_j2_r185_ob8_tail_cut`: `2287` trades, daily `3.2`, win `43.6%`, PF `1.58`, balance `$96941.72`, losing months `7`.
- Monthly change versus R185:
  - `2026-03`: R185 `8` trades / about `-$870.89`; R186 `6` trades / about `-$13.37`.
  - `2026-05`: preserved at `2` trades / about `+$3.47`.
  - `2026-04`: preserved as a strong recovery month, about `+$10666`.

Post-R186 account-level scan:
- `R186 + HTFPB/R104` still cannot produce all-positive months. Best coarse scan using scaled `HTF142` and `R104` reached about `$101938` and daily `6.22`, but still had losing months `2024-11`, `2026-01`, and `2026-05`.
- Scaling old streams is not a solution; low-balance 2024/2025 losing months need a separate low-balance/startup-specific edge, not more high-balance tail surgery.

Conclusion:
- R186 is the new best profit reference and a validated high-balance tail-risk improvement.
- It still fails the updated target: daily `3.2 < 4` and seven losing months remain (`2024-10`, `2024-11`, `2024-12`, `2025-03`, `2025-04`, `2025-05`, `2026-03`).
- Next work should shift to low-balance/startup phase and independent frequency, because the high-balance tail clusters are now much smaller and no longer the main blocker.

## 2026-05-24 Round187: low-balance monthly profit target stop

Diagnosis from R186 low-balance losing months:
- `2024-10`, `2024-12`, `2025-03`, `2025-04`, and `2025-05` all had positive month prefixes and later gave back profits.
- Examples: `2024-10` peaked around `+$72`, `2025-03` around `+$105`, `2025-05` was about `+$173` after the first trade.
- `2024-11` and R186 `2026-03` did not have a positive prefix, so lock-profit alone cannot solve all months.

Hypothesis:
- Add a default-off low-balance monthly profit target stop. R187 stops new entries after month profit reaches `2%` of month-start balance while month-start balance is `<=1000`.
- This intentionally tests whether the low-balance giveback months can be made positive before pursuing independent frequency again.

Implementation:
- Added `InpMonthlyProfitTargetStopPct` and `InpMonthlyProfitTargetStopMaxBalance`.
- `PassMonthlyEntryGuard()` now treats this as a third monthly entry-stop mode, alongside loss stop and profit-lock.
- Added `v11_r187_j2_r186_lowbal_pt2`.
- Validation: `python -m pytest tests\test_mt5_common.py -q` -> `71 passed`; native MetaEditor compile -> `0 errors, 0 warnings`.

Fixed-window MT5 Real Ticks:
- `v11_r187_j2_r186_lowbal_pt2`: `431` trades, daily `0.6`, win `35.5%`, PF `0.98`, balance `$701.82`, losing months `2`.
- It made several low-balance giveback months positive, but account growth stalled:
  - `2024-11`: still negative, about `-$129`.
  - `2026-05`: became negative again, about `-$177`, because the account never escaped low balance and the high-balance R185/R186 tail protections never activated.

Conclusion:
- Reject R187 as a target solution and seal simple low-balance profit-target locking.
- It improves the monthly-count symptom but destroys the compounding path, trade frequency, and high-balance regime entry.
- Low-balance fixes must be selective by bad-cluster/signal quality or come from an independent startup edge; broad low-balance month-level locks are not viable.

## 2026-05-24 Round188: low-balance OB hour filter

Hypothesis:
- R186 low-balance bad months, especially `2024-11`, contained several ordinary OB losses around hours `13/14/15`.
- Test a startup-only ordinary-OB hour filter: apply only when month-start balance is `<=1000`, only to ordinary OB, and cut hours `13,14,15`.

Implementation:
- Added default-off inputs `InpLowBalanceOBBadHours`, `InpLowBalanceOBBadMaxMonthStartBalance`, and `InpLowBalanceOBBadHourMult`.
- Applied after the regular OB context multiplier, only when the signal is ordinary OB and the month-start balance is within the configured startup threshold.
- Added `v11_r188_j2_r186_lowbal_ob131415_cut`.
- Validation before the MT5 run: `python -m pytest tests\test_mt5_common.py -q` -> `71 passed`; native MetaEditor compile -> `0 errors, 0 warnings`.

Fixed-window MT5 Real Ticks:
- `v11_r188_j2_r186_lowbal_ob131415_cut`: `2603` trades, daily `3.6`, win `41.7%`, PF `1.49`, balance `$52318.85`, losing months `10`.
- It improved `2024-11` versus R186 (`-$47.41` in this altered path), but damaged the account path heavily:
  - `2024-09`: `-$122.55`
  - `2024-10`: `-$102.99`
  - `2024-12`: `-$113.45`
  - `2025-11`: `-$2701.79`
  - `2026-01`: `-$4132.21`
  - `2026-02`: `-$3769.96`
  - `2026-03`: `-$3473.89`
  - `2026-05`: `-$4543.91`

Conclusion:
- Reject R188. A broad startup OB hour filter can make the target month look less bad, but it rewrites the later compounding path and turns several high-balance months into large losses.
- Seal "wide low-balance OB hour cut" as a direction. Future startup fixes need either a calibrated single-month screening loop plus exact-path validation, or a true independent startup edge rather than broad hour filters inside the same EA path.

## 2026-05-24 Round189-R191: single-month screening calibration and startup bad-cluster test

Question:
- For similar small strategy changes, can we speed up iteration by starting the bad month from the prior full-run month-start balance and testing only that month?
- Calibration target: R186 full-window `2024-11` had `82` trades, monthly profit about `-$214.85`, month-start balance about `$507.58`.

Implementation:
- Added CLI `--deposit` override to `backtest_main`, so a one-off MT5 run can use the full-run month-start balance without editing YAML.
- Changed the Windows runner report path to include date-window tokens, preventing single-month reports from overwriting same-day full-window reports.
- Added default-off startup bad-cluster inputs `InpStartupBadClusterMaxMonthStartBalance` and `InpStartupBadCluster1..4*`, applied only when `g_monthly_start_balance <= threshold`.
- Validation: `python -m pytest tests\test_mt5_common.py -q` -> `73 passed`; native MetaEditor compile -> `0 errors, 0 warnings`.

Single-month calibration (`2024.11.01` to `2024.12.01`, deposit `$507.58`):
- `v11_r186_j2_r185_ob8_tail_cut`: `81` trades, balance `$290.60`, month profit `-$216.98`.
- This is close to the full-window R186 `2024-11` result (`82` trades, `-$214.85`), so the single-month loop is useful as a first-pass screen for this month.
- Important caveat remains: it cannot replace 720-day validation because EA state, filtered-zone lifecycle, and later compounding path can diverge.

Screening candidates:
- `v11_r189_j2_r186_screen_202411_swp20_cut`: exact `sweep hour20 risk300-400 confirm -1.5~-1.0` cut. Single-month balance `$302.07`, profit about `-$205.51`; reject, too small.
- `v11_r190_j2_r186_screen_202411_swp20_23_cut`: exact `sweep hour20` plus `sweep hour23 risk200-300 confirm<-1` cuts. Single-month balance `$303.55`, profit about `-$204.03`; reject, too small.
- Both variants still had no positive month prefix; best prefix remained after the first trade at about `-$29.73`.

R191 startup OB exact filter:
- `v11_r191_j2_r186_startup_202411_ob_top4_cut`: startup-only exact filters for the four largest low-balance `2024-11` ordinary OB losses.
- Single-month result: `100` trades, balance `$410.80`, profit `-$96.78`; first positive prefix appeared at trade 7, peak prefix about `+$7.54`.
- Full-window result (`2024.06.02` to `2026.05.23`): `2698` trades, daily `3.7`, win `41.7%`, PF `1.49`, balance `$52402.64`, losing months `10`.

Conclusion:
- The single-month calibrated loop is validated as a fast screen: R186 reproduced close enough in 22 seconds versus several minutes for the 720-day run.
- But R191 proves a local startup-month improvement is not sufficient. Like R188, it improves `2024-11` locally while rewriting the compounding path and creating large high-balance losses (`2025-11`, `2026-01`, `2026-02`, `2026-03`, `2026-05`).
- Reject R189/R190/R191 as target solutions. Keep the single-month loop for rejecting weak ideas quickly, but require full 720-day MT5 confirmation before accepting any low-balance/startup filter.
- Next direction should move away from same-EA startup filters and toward either an independent positive frequency stream or a portfolio/account-level scheduler; repeated in-EA filters are path-sensitive and keep damaging the later regime.

## 2026-05-24 Round192-R195: independent sweep probe and single-month profit-stop screens

Question:
- Can the R186 `hour13` sweep edge act as an independent complement stream?
- Can the newly validated single-month loop quickly separate low-balance lock-profit ideas from true `2024-11` startup fixes?

R192 independent sweep probe:
- Added `v11_r192_j2_r186_sweep13_only_probe`: inherit R186, `liquidity_sweep_only=true`, `sweep_allow_hours=13`, `max_concurrent=4`, `max_entries_per_ob=2`.
- Offline R186 CSV suggested `hour13` sweep had `181` samples, about `+$95.6` pnl proxy and `+50.3R`, with positive contribution in several R186 losing months.
- Fixed-window MT5 Real Ticks result: `175` trades, daily `0.2`, win `42.3%`, PF `1.24`, balance `$222.79`, losing months `13`.
- Conclusion: reject as a target solution. The stream is mildly positive, but too small and too month-unstable to solve frequency or all-positive-month targets. Keep it only as a feature hint.

R193/R194 low-balance profit-stop screens:
- Added `v11_r193_j2_r186_lowbal_pt8_screen` and `v11_r194_j2_r186_lowbal_pt12_screen`.
- Single-month `2024-10`, deposit `$693.66`: both variants stopped after `5` trades, balance `$764.18`, month profit `+$70.52`.
- Single-month `2024-11`, deposit `$507.58`: both variants matched R186 path, `81` trades, balance `$290.60`, month profit `-$216.98`.
- Diagnosis: `2024-10` had a positive prefix, so profit-stop works there. `2024-11` never had a positive prefix under R186; peak prefix was still `-$29.73`, and the first two trades already put the month near `-$104`.
- Conclusion: less-aggressive profit locks are useful as fast screens for giveback months, but they do not solve no-positive-prefix startup months.

R195 startup exact filter plus tiny profit stop:
- Added `v11_r195_j2_r191_startup_pt1_screen`: R186 plus the four R191 startup exact OB filters and `monthly_profit_target_stop_pct=1.0` while month-start balance is `<=1000`.
- Single-month `2024-11`, deposit `$507.58`: `9` trades, balance `$514.54`, month profit `+$6.96`.
- Trade path: after exact startup filters, the month stayed around `-$8` through trade 6, flipped positive on trade 7, and stopped after trade 9 at about `+$7.54` prefix.
- Additional single-month checks:
  - `2024-10`, deposit `$693.66`: `5` trades, balance `$764.18`.
  - `2024-12`, deposit `$292.73`: `26` trades, balance `$314.64`.
- Full-window MT5 Real Ticks: `350` trades, daily `0.5`, win `38.6%`, PF `0.68`, balance `$198.15`, losing months `22`.
- Conclusion: this is the first useful `2024-11` single-month screen, but it is rejected as a target solution after the 720-day run. It validates the shape needed for the bad startup months: first avoid the opening OB damage, then stop after tiny low-balance profit. As a global rule it stalls compounding, suppresses frequency, and later gives back in months such as `2026-01` and `2026-05`. A future accepted version needs a regime gate that only activates this rescue behavior on no-positive-prefix startup conditions, not broadly across all low-balance months.

## 2026-05-24 Round196-R199: balance-window gated rescue

Hypothesis:
- R195 failed because the 1% low-balance profit stop was active from the initial `$200` cold start, suppressing compounding before the account escaped startup.
- Add a lower month-start balance bound to the profit-target stop. Prediction: if this is the cause, enabling the rescue only after month-start balance reaches `$300`/`$500` should preserve more of R186's growth while keeping the low-balance bad-month protection.

Implementation:
- Added `InpMonthlyProfitTargetStopMinBalance`, mapped from `monthly_profit_target_stop_min_balance`, default `0`.
- `IsMonthlyProfitTargetStopEnabled()` now requires `month_start >= min` when configured, and still respects the existing max-balance gate.
- Added:
  - `v11_r196_j2_r195_pt1_min300`: R195 rescue, 1% profit stop only for month-start `$300..$1000`.
  - `v11_r197_j2_r195_pt1_min500`: same, but `$500..$1000`.
  - `v11_r198_j2_r195_pt3_min500`: 3% profit stop for `$500..$1000`.
  - `v11_r199_j2_r195_pt5_min500`: 5% screening variant.
- Validation: `python -m pytest tests\test_mt5_common.py -q` -> `73 passed`; native MetaEditor compile -> `0 errors, 0 warnings`.

Results:
- `R196`: `1576` trades, daily `2.2`, win `41.8%`, PF `1.99`, balance `$90264.98`, losing months `4`.
  - Better than R195 and closer to target profit, but still below R186 profit and much too low on daily frequency.
  - Losing months: `2024-11 -$125.82`, `2025-10 -$3474.68`, `2025-11 -$3209.20`, `2026-03 -$13.31`.
- `R197`: identical to R196, so the first meaningful activation already happens above `$500`.
- `R198`: single-month `2024-11` still passed (`$507.58 -> $514.54`), but full-window fell to `2174` trades, daily `3.0`, PF `1.10`, balance `$54508.17`, losing months `6`.
  - It restored `2025-10/11` as large winners but exposed later high-balance tail losses: `2026-01`, `2026-02`, `2026-03`, `2026-05`.
- `R199`: single-month `2024-11` failed (`$507.58 -> $410.80`), so it was rejected without a full-window run.

Conclusion:
- Balance-window gating is an improvement over global R195, but still not a target solution.
- R196 is the best rescue variant so far by monthly count/PF, but not by final target: daily `2.2 < 4`, balance just above `$90k`, and four losing months remain.
- R198 shows the tradeoff sharply: looser startup rescue keeps later frequency but loses high-balance protection.
- Next useful direction is not another scalar profit-stop sweep. The strategy needs separate behavior by account regime: low-balance rescue around `$500..$1000`, then R186-style growth/tail controls above that. The immediate blocker for R196 is `2025-10/11`, where the 1% rescue/profit-stop path appears too restrictive and turns R186's large positive months negative.

Path-dependence follow-up:
- R196/R198 rescue gates are correctly bounded to month-start balance `$300/500..$1000`; they are not directly active in the later high-balance months.
- The later `2025-10/11` divergence is therefore path-dependent: earlier rescue changes the account/zone/monitor state and compounding path, not simply a high-balance parameter firing by mistake.
- R196 versus R198:
  - R196: keeps low-balance rescue tight, reaches `$90264.98`, but turns `2025-10/11` into losses and daily falls to `2.2`.
  - R198: restores `2025-10/11` as large winners, but later high-balance months (`2026-01/02/03/05`) fail and balance falls to `$54508.17`.
- Coarse CSV-only portfolio scan (not a valid MT5 account-path proof) suggests that account-level combination is more promising than more same-EA mixing:
  - `R186 + R187*10` had only two negative months in monthly proxy and rough total above `$100k`, with high estimated frequency.
  - This cannot be accepted as a backtest because it ignores shared margin, concurrent path, monthly guards, and execution interaction.
- Conclusion: same-EA rescue parameters are now showing strong path sensitivity. The next serious branch should be a portfolio/account-level scheduler or a true multi-strategy runner that can validate independent streams without rewriting R186's internal path.

## 2026-05-24 Portfolio proxy scan

Purpose:
- Before building a true multi-strategy runner, test whether existing full-window MT5 trade CSVs contain enough monthly complementarity to justify that work.
- Added `scripts/portfolio_monthly_scan.py`, a deliberately labelled proxy tool. It sums monthly `pnl_proxy` and trade counts across strategies with configurable scales. It does not simulate shared margin, concurrent path, monthly guards, execution interaction, or EA state.

Validation:
- `python -m py_compile scripts\portfolio_monthly_scan.py` passed.

Findings with `R186` as base:
- Static one-leg add-ons cannot remove all bad months.
  - `R186 + R187*10`: only `2` negative months in proxy, rough total `$101918.76`, but daily only about `3.77`; remaining bad months are `2024-11` and `2026-05`.
  - `R186 + R142*4`: `3` negative months, rough daily `4.33`, remaining `2024-10/11/12`.
- Two-leg static add-ons also cannot remove all bad months.
  - Best examples still leave `3` negative months even with rough daily above `5`.
- Hindsight monthly oracle across `R186/R196/R198/R187/R142/R104` reaches `0` negative months and rough total about `$140k`, but daily is only about `3.4`.
  - The oracle shape picks `R196` for several startup/growth months, `R186` for high-balance profit months, `R198` for selected recovery months, and `R142/R104` for isolated bad months.
  - This is not deployable because it chooses after the month is known.

Simple ex-ante-ish rules:
- `R196` through `2025-09`, then `R186`: rough total `$128255.75`, only `2` negative months (`2024-11`, `2026-03`), daily `2.85`.
- This improves monthly stability but still fails the daily frequency target.

Conclusion:
- Existing streams contain real complementarity, but static weighted blending is not enough.
- A deployable next branch needs a scheduler with ex-ante regime signals, not hindsight month selection. Candidate signals to test next: month-start balance, previous month outcome, early-month prefix after N trades, and calendar/seasonal guard. The scheduler must eventually be validated by a real MT5-compatible runner because proxy sums are insufficient evidence.

## 2026-05-24 Single-month screening and schedule proxy follow-up

Question:
- If a known bad month, such as `2024-11`, is negative in the full 720-day run, can we reuse the full-window month-start balance as the deposit and test only that month to reduce iteration time?

Assessment:
- Yes, as a first-pass screen. The R186 single-month reproduction already matched the full-window `2024-11` loss closely enough (`-$216.98` single-month vs about `-$214.85` full-window).
- This can reject weak ideas much faster than a full `2024.06.02` to `2026.05.23` MT5 run.
- It cannot accept a final strategy because the isolated month does not preserve all full-window state: open/closed zone lifecycle, prior month EA state, path-dependent balance, monthly stop history, concurrent positions, and later compounding effects can diverge.
- Practical rule: use single-month tests for local bad-month hypotheses; only promote a candidate after a full fixed-window Real Ticks run and digest.

Tooling:
- Added `scripts/portfolio_schedule_scan.py` to scan simple one-strategy monthly schedules: single strategy, one calendar switch point, and small fixed-month overrides.
- Extended `scripts/portfolio_monthly_scan.py` so `--base` can be repeated to model an aggregate base, and added `--monthly-addon-scan` for hindsight bad-month add-on upper-bound checks.
- Validation: `python -m py_compile scripts\portfolio_monthly_scan.py scripts\portfolio_schedule_scan.py` passed.

Findings:
- Pure monthly switching can reach `0` negative months in proxy, but daily trade frequency remains too low (`~2.5` to `~3.1`). This fails the `>4/day` target.
- `R186` as a constant base plus bad-month-only add-ons can reach `0` negative months and above `$90k` in proxy, but daily trade frequency stays around `3.58`. It proves monthly complementarity, not the full target.
- Full-time `R186 + R196` is the strongest proxy base so far: rough total about `$187k`, daily about `5.37`, with only four negative months left (`2024-10`, `2024-11`, `2024-12`, `2026-03`).
- The remaining hardest gap is `2024-11`: with `R186+R196`, it is about `-$341`. Full-library scan shows the best positive `2024-11` complement is the HTF pullback family, especially `R140`/`R143`, but the raw monthly edge is only about `+$20`.
- A hindsight upper-bound shape exists: `R186+R196` full-time plus month-specific high-scale add-ons (`R198` for `2024-10`, `R140` for `2024-11`, `R104` for `2024-12`, `R187` for `2026-03`) reaches `0` negative months, rough total about `$192k`, and daily about `5.7`.

Conclusion:
- The fast-screen idea is valid and should be part of the workflow, but acceptance still requires the 720-day fixed-window MT5 validation.
- The best current direction is no longer another scalar tweak to R186/R196. It is to extract a deployable ex-ante trigger for the `2024-11` HTF-pullback complement, then validate it in a true runner.
- Calendar/month-specific high-scale add-ons are useful only as an upper-bound diagnostic. Treat them as evidence that the edge exists, not as a strategy.

## 2026-05-24 Round200-R203: HTFPB complement lane repair

Hypothesis:
- The portfolio proxy showed that the HTF pullback family was the strongest positive complement around the hard `2024-11` gap.
- Prediction: adding a small, filtered HTFPB lane to R196 should improve `2024-11` without materially damaging the R196 base path.

Implementation:
- Added HTFPB context filters: allowed hours, blocked hours, risk range, confirm-position range, and context multiplier.
- Fixed non-`HTFPullbackOnly` mode so HTFPB zones run in an independent lane:
  - `g_htf_zones` are detected separately from the primary OB/sweep zones.
  - HTFPB zones now receive H1 alignment and `UpdateOBStatus`, otherwise stale zones fill the lane and suppress fresh signals.
  - Confirmed HTFPB monitors execute through `ExecuteSignalFromZone` against the HTFPB zone array.
- Added `R200/R201/R202/R203` probes and kept `R203` as a standalone sell-only micro validation of the best observed HTFPB subcluster.
- Validation: `python -m pytest tests\test_mt5_common.py -q` -> `73 passed`; native MetaEditor compile -> `0 errors, 0 warnings`.

Results:
- `R200` (`R196 + hours 12/20/23 HTFPB micro`): `2194` trades, daily `3.0`, PF `1.48`, balance `$60017.25`, losing months `6`.
  - HTFPB contributed about `+$6.26` proxy across `440` trades and improved `2024-11` from `-$125.82` to `-$98.52`, but the combined path lost far too much final balance.
- `R202` (`R196 + hour12, confirm -1.5..-0.6 HTFPB micro`): `1953` trades, daily `2.7`, PF `1.56`, balance `$50851.18`, losing months `7`.
  - HTFPB itself contributed about `+$32.46` proxy across `136` trades.
  - The better subcluster was `hour12 sell`: `75` trades, about `+$40.60` proxy and `+16.09R`; `hour12 buy` was negative.
  - Despite that, the same-EA combined path degraded badly versus R196.
- `R203` (`HTFPB only, hour12 sell-only micro`): `152` trades, daily `0.2`, PF `1.32`, balance `$237.22`, losing months `11`.
  - It is a real positive edge, but too small: `2024-11` adds only about `+$3.10`, nowhere near enough to cover the remaining R196/R186+R196 gap.

Conclusion:
- The HTFPB lane is now technically working, but it is not the main solution.
- R200/R202 prove the danger of same-EA mixing: a small positive complement can still rewrite the account path and damage the primary OB/sweep stream.
- R203 proves that `hour12 sell HTFPB` is a mildly positive independent stream, but it is too low-frequency and too low-PnL to solve the target.
- Next branch should return to portfolio/account-level orchestration or a true multi-strategy runner. The best proxy remains `R186 + R196` full-time: high profit and frequency, with a small set of residual bad months to solve by ex-ante scheduling or isolated complements.

Tooling follow-up:
- Added `scripts/single_month_screen.py` to automate the fast bad-month workflow.
- It reads a full-window `.trades.csv` plus report `.txt`, reconstructs month-start balances using the same scaled `pnl_proxy` method as `backtest_digest.py`, and prints ready-to-run MT5 single-month commands with `--deposit`.
- Example on R196 correctly recovered the four full-window losing months and deposits:
  - `2024-11`, start `$856.34`, profit `-$125.82`
  - `2025-10`, start `$43490.84`, profit `-$3474.68`
  - `2025-11`, start `$40016.16`, profit `-$3209.20`
  - `2026-03`, start `$79499.82`, profit `-$13.31`
- Validation: `python -m py_compile scripts\single_month_screen.py scripts\portfolio_monthly_scan.py scripts\portfolio_schedule_scan.py` passed.

## 2026-05-24 Path-level portfolio guard proxy

Purpose:
- Move beyond monthly totals and test whether `R186 + R196` can be repaired by account-level orchestration over the actual exported trade order.
- Added `scripts/portfolio_path_sim.py`: merges multiple `.trades.csv` streams by timestamp and simulates simple account-level rules such as month profit stop, loss stop, and pre-trade drop filters.
- Warning: this is still a proxy. It does not simulate shared margin, order fills, recomputed lot sizing, EA state, or the fact that skipping trades changes later state. It is useful only for ranking orchestration ideas.

Baseline:
- `R186 + R196` merged path:
  - total about `$187274.77`, final `$187474.77`, daily `5.37`, losing months `4`.
  - Losing months: `2024-10 -$174.24`, `2024-11 -$341.39`, `2024-12 -$20.02`, `2026-03 -$26.74`.

Bad-month shapes:
- `2024-10`: positive early, max prefix about `+$84.65`, then gives back. Month-level profit stop can fix it.
- `2024-12`: positive prefix exists, but needs lower profit-stop threshold after `2024-11` filtering changes month-start balance.
- `2024-11`: no positive prefix. The first few ordinary OB losses already drive the month deeply negative. Profit stop cannot help.
- `2026-03`: tiny loss, all from early sweep trades on `2026-03-01` and `2026-03-02`; only two small sweep trades were positive.

Proxy upper-bound repair:
- Command shape:
  - merge `R186` and `R196`.
  - drop `2024-11` OB hours `7,13,14,15,18,22`.
  - drop `2026-03` sweep hours `0,1,6,23`.
  - enable a `3%` month profit stop only in `2024-10` and `2024-12`.
- Result:
  - `bad=0`
  - total about `$188043.04`
  - final about `$188243.04`
  - daily about `5.22`
- This is the first proxy shape that satisfies all three target metrics simultaneously.

Conclusion:
- The best direction is now an account-level scheduler / true multi-strategy runner, not another same-EA variant.
- The candidate rule family is:
  1. run R186 and R196 as separate streams,
  2. account-level month profit stop for early giveback months,
  3. ex-ante bad-cluster filters for low-balance November startup OB damage,
  4. sweep protection for early-March sweep clusters.
- The unresolved hard part is deployability: the current repaired proxy uses calendar-specific filters. Next work should replace those with ex-ante signals or implement a runner that can be explicitly scheduled and then validate with fixed-window MT5-compatible execution.

Follow-up: season/regime proxy, not exact year-month:
- Extended `scripts/portfolio_path_sim.py` with:
  - `monthnum` filter support,
  - per-filter balance/day/profit context (`min_start`, `max_start`, `max_day`, `before_profit`, `monthly_negative`),
  - month-number and balance gates for profit stops,
  - repeated `--drop-filter` support.
- A less hindsight-specific season/regime rule still reaches the same proxy target:
  - `R186 + R196` merged streams.
  - November low-balance OB startup guard:
    - `monthnum=11;signal=ob;hour=7,13,14,15,18,22;max_start=2500`
  - March high-balance first-two-days sweep guard:
    - `monthnum=3;signal=sweep;hour=0,1,6,23;min_start=100000;max_day=2`
  - October/December low-balance recovery profit stop:
    - `guard_monthnums=10,12`
    - `guard_max_month_start_balance=2500`
    - `profit_target_stop_pct=3`
- Proxy result:
  - `bad=0`
  - total about `$188043.04`
  - final about `$188243.04`
  - daily about `5.22`
- This is still not accepted as a valid backtest. It is, however, the first rule set that is not tied to exact year-month strings and still satisfies all target metrics in path-level proxy.
- Next implementation candidate: an account-level scheduler configuration that can run R186 and R196 as separate streams and apply these month-number/balance/signal/hour guards before dispatching orders.

## 2026-05-24 单月快筛与可部署参数验证

问题:
- 是否可以记录完整路径中问题月份的月初余额，然后只跑该月 MT5 回测，用来缩短同类型小改动的等待时间。

结论:
- 可以作为第一层快筛，尤其适合验证“这个坏月是否被修到不亏”。
- 不能作为最终通过标准。完整 720 天仍必须跑，因为月度停手、复利路径、并发/冷却、EA 状态都会让后续路径重写。

实测:
- 新增可部署参数:
  - `InpLowBalanceOBBadMonths`
  - `InpSweepContextMonths`
  - `InpSweepContextMaxDay`
  - `InpSweepContextMinMonthStartBalance`
  - `InpSweepContextNoHours`
  - `InpMonthlyProfitTargetStopMonths`
- 修正 sweep 门控拆分:
  - `InpSweepNoHours` 保持基础全局过滤。
  - `InpSweepContextNoHours` 只在月份/日序/月初余额上下文满足时额外过滤。
- 验证:
  - `python -m pytest tests\test_mt5_common.py -q` -> 73 passed.
  - Windows MetaEditor 编译 `WaiTrade_OB` -> 0 errors, 0 warnings.

单月快筛结果:
- `v11_r204_r186_season_guard`, 2024-11, deposit `$507.58`:
  - 105 trades, daily 3.5, balance `$512.06`, profit about `+$4.48`.
  - 相比原 R186 isolated 2024-11 的大亏，单月目标达成。
- `v11_r205_r196_season_guard`, 2024-11, deposit `$856.34`:
  - 155 trades, daily 5.2, balance `$876.82`, profit `+$20.48`.
- 2026-03 isolated:
  - R204 deposit `$86294.18` -> balance `$86280.64`, about `-$13.54`.
  - R205 deposit `$79499.82` -> balance `$79485.64`, about `-$14.18`.
  - 这是预期边界: March guard 的 `min_month_start_balance=100000` 来自组合账户 proxy，单策略 isolated 账户未达到门槛，因此不会触发。

完整 720 天验证:
- `v11_r204_r186_season_guard`:
  - 445 trades, daily 0.6, PF 0.71, balance `$-516.50`.
  - 反例: 2024-11 单月转正，但低余额 Oct/Dec 月度盈利停手改变复利路径，完整回测崩掉。
- `v11_r206_r186_nov_guard` / `v11_r207_r196_nov_guard`:
  - 去掉低余额月度盈利停手，只保留 Nov low-balance OB guard 和 March context guard。
  - 两者完整结果一致: 2684 trades, daily 3.7, PF 1.48, balance `$52403.81`, losing months 8.
  - 说明 monthly target stop 是 R204 崩盘主因，但单策略参数化 guard 仍明显弱于原始 R186/R196 路径。

当前最佳方案:
- 原始 `R186 + R196` 组合 proxy 仍是最佳基线:
  - final about `$187474.77`, daily about `5.37`, losing months 4.
- R206 + R196 组合 proxy:
  - final about `$142983.54`, daily about `5.92`, losing months 8.
- 因此当前最优方向不是把规则硬塞回单策略 EA，而是保留 R186/R196 作为独立流，在账户级 scheduler / true multi-strategy runner 层做:
  - 低余额 11月 OB 坏小时过滤,
  - 高余额 3月前2天 sweep 过滤,
  - 低余额 10/12月恢复期盈利停手。

## 2026-05-24 scheduler 配置化复现

目的:
- 把当前最佳 `R186 + R196` 账户级季节/余额规则从一次性命令固化成可复跑工件。
- 让后续新增候选策略或替换 CSV 时，可以一键审计三条目标:
  - total profit > `$90000`
  - daily trades > `4`
  - losing months = `0`

新增:
- `config/portfolio_schedules.yaml`
  - schedule: `r186_r196_season_guard`
  - series: R186 + R196 full-window `.trades.csv`
  - drop filters:
    - `monthnum=11;signal=ob;hour=7,13,14,15,18,22;max_start=2500`
    - `monthnum=3;signal=sweep;hour=0,1,6,23;min_start=100000;max_day=2`
  - guards:
    - `guard_monthnums=[10,12]`
    - `guard_max_month_start_balance=2500`
    - `profit_target_stop_pct=3`
- `scripts/portfolio_schedule_runner.py`
  - reads YAML schedule,
  - reuses `portfolio_path_sim.py` functions,
  - prints target audit and month table,
  - exits `0` only when configured targets pass.
- `tests/test_portfolio_schedule_runner.py`
  - locks down context drop filters and month profit stop behavior.

Validation:
- `python -m pytest tests\test_portfolio_schedule_runner.py tests\test_mt5_common.py -q`
  - `74 passed`
- `python scripts\portfolio_schedule_runner.py --schedule r186_r196_season_guard --output results\backtest\portfolio_r186_r196_season_guard_20260524.md`
  - `total=188043.04`
  - `final=188243.04`
  - `daily=5.22`
  - `bad=0`
  - `pass=true`

Important caveat:
- This remains a CSV path-level proxy, not a valid MT5 portfolio backtest.
- It does not prove shared margin, recomputed lot sizing, changed EA state after skipped trades, or live order dispatch behavior.
- Next required step is a true account-level scheduler / multi-strategy runner that can dispatch R186 and R196 as independent streams and enforce the same rules before order placement.

## 2026-05-24 portfolio live profile 生成器

Purpose:
- Move the best scheduler proxy one step closer to deployment.
- Existing `mt5_live_runner.py` creates one strategy across many symbols. The current best BTC idea needs two independent streams on the same symbol:
  - R186 on `BTCUSDm`
  - R196 on `BTCUSDm`
  - distinct magic numbers
  - same guard overlay before order placement

Added:
- `scripts/mt5_portfolio_live_profile.py`
  - reads `config/portfolio_schedules.yaml`
  - loads each stream's base strategy from `config/strategies.yaml`
  - overlays `live_profile.guard_overrides`
  - writes a multi-chart MT5 profile under `temp/portfolio_profiles/<schedule>/`
  - writes `portfolio_manifest.yaml` for audit
- `tests/test_mt5_portfolio_live_profile.py`
  - verifies two charts are generated,
  - verifies MT5-compatible `order.wnd`,
  - verifies distinct magic numbers,
  - verifies guard inputs are present in both charts.

Validation:
- `python -m pytest tests\test_mt5_portfolio_live_profile.py tests\test_portfolio_schedule_runner.py tests\test_mt5_common.py -q`
  - `75 passed`
- `python scripts\mt5_portfolio_live_profile.py --schedule r186_r196_season_guard`
  - generated `temp\portfolio_profiles\r186_r196_season_guard`
  - manifest:
    - chart01: R186 / `v11_r186_j2_r185_ob8_tail_cut` / magic `204345` / BTCUSDm
    - chart02: R196 / `v11_r196_j2_r195_pt1_min300` / magic `204355` / BTCUSDm
  - both charts include:
    - `InpLowBalanceOBBadMonths=11`
    - `InpLowBalanceOBBadHours=7,13,14,15,18,22`
    - `InpSweepContextMonths=3`
    - `InpSweepContextMaxDay=2`
    - `InpSweepContextMinMonthStartBalance=100000.0`
    - `InpSweepContextNoHours=0,1,6,23`
    - `InpMonthlyProfitTargetStopPct=3.0`
    - `InpMonthlyProfitTargetStopMaxBalance=2500.0`
    - `InpMonthlyProfitTargetStopMonths=10,12`

Caveat:
- This is deployable profile generation, not proof of the final target.
- It still needs a true validation loop:
  1. either forward/live dry-run on demo with this profile,
  2. or a dedicated multi-strategy MT5 backtest EA/runner that can execute both streams in one tester pass.

## 2026-05-24 shared monthly guard state

Problem:
- The two-chart portfolio profile is closer to deployment, but each EA chart originally owned its own static monthly guard state.
- That means `monthly_profit_target_stop` could fire on one chart while the other stream kept trading until it independently evaluated the same condition.
- The proxy rule is account-level, so live/forward execution needs shared monthly state.

Change:
- Added optional EA inputs:
  - `InpSharedMonthlyGuard`
  - `InpSharedMonthlyGuardKey`
- Default remains off in `config/strategies.yaml`, so existing single-strategy 720d backtests are not changed.
- When enabled, the EA stores monthly state in MT5 Terminal Global Variables under:
  - `WT2_MONTH_<key>_<yyyymm>_*`
- Shared fields:
  - month start balance
  - monthly peak balance
  - monthly entry count
  - entry stopped flag
  - loss stopped flag
  - profit locked flag
- Also made `g_monthly_entry_stopped` effective in `PassMonthlyEntryGuard()`, so a once-fired monthly stop remains locked for the rest of the month instead of relying only on recalculating the threshold.

Portfolio profile:
- `config/portfolio_schedules.yaml` now sets:
  - `shared_monthly_guard: true`
  - `shared_monthly_guard_key: r186_r196_season_guard`
- Regenerated `temp\portfolio_profiles\r186_r196_season_guard`.
- Both R186 and R196 charts now include:
  - `InpSharedMonthlyGuard=true`
  - `InpSharedMonthlyGuardKey=r186_r196_season_guard`

Validation:
- `python -m pytest tests\test_mt5_portfolio_live_profile.py tests\test_portfolio_schedule_runner.py tests\test_mt5_common.py -q`
  - `75 passed`
- Windows MetaEditor compile:
  - `Result: 0 errors, 0 warnings`

Remaining:
- This fixes a real deployability gap, but the final target is still not proven.
- Need a forward/demo dry-run or a real portfolio tester harness that verifies R186/R196 shared monthly guard behavior over the 720d BTC window.

## 2026-05-24 shared guard run-id and cleanup

Problem:
- MT5 Terminal Global Variables persist across runs.
- A stable shared monthly guard key is useful for a live account, but dangerous for repeated dry-runs or historical replay because stale `WT2_MONTH_<key>_<yyyymm>_*` values can contaminate the next run.

Added:
- `scripts/mt5_portfolio_live_profile.py --guard-key-suffix <suffix>`
  - appends a sanitized suffix to `shared_monthly_guard_key`.
  - example:
    - base key: `r186_r196_season_guard`
    - suffix: `dryrun_20260524`
    - effective key: `r186_r196_season_guard_dryrun_20260524`
- `mql5/Scripts/WaiTrade2/ClearSharedMonthlyGuard.mq5`
  - input: `InpSharedMonthlyGuardKey`
  - deletes terminal globals under prefix `WT2_MONTH_<key>_`
- `docs/portfolio_scheduler_runbook.md`
  - documents how to generate a fresh profile and how to clear shared guard globals.

Validation:
- `python -m pytest tests\test_mt5_portfolio_live_profile.py tests\test_portfolio_schedule_runner.py tests\test_mt5_common.py -q`
  - `75 passed`
- Generated dry-run profile:
  - `python scripts\mt5_portfolio_live_profile.py --schedule r186_r196_season_guard --guard-key-suffix dryrun_20260524`
  - both charts use `InpSharedMonthlyGuardKey=r186_r196_season_guard_dryrun_20260524`
- Windows MetaEditor compile:
  - `WaiTrade_OB.mq5`: `0 errors, 0 warnings`
  - `ClearSharedMonthlyGuard.mq5`: `0 errors, 0 warnings`

Implication:
- The portfolio deployment path is now safer for repeated demo/forward validation.
- Still not final proof of the target; the required missing piece is a real validation run that executes both R186 and R196 streams under shared account state.

## 2026-05-24 Windows portfolio deploy script

Purpose:
- Install the generated portfolio profile into the actual Windows MT5 data directory safely.
- Default behavior must not start MT5, to avoid accidental live trading.

Added:
- `scripts/mt5_portfolio_deploy_win.py`
  - generates the profile from `config/portfolio_schedules.yaml`
  - syncs `mql5/Experts`, `mql5/Include`, and `mql5/Scripts`
  - installs the profile into:
    - `%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Profiles\Charts\<profile>`
  - supports `--compile`
  - supports explicit `--start`, but does not start by default.
- `tests/test_mt5_portfolio_deploy_win.py`
  - verifies profile installation,
  - verifies source sync,
  - verifies run-id shared guard key reaches chart inputs.

Validation:
- `python -m pytest tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_portfolio_schedule_runner.py tests\test_mt5_common.py -q`
  - `76 passed`
- Dry-run deploy:
  - `python scripts\mt5_portfolio_deploy_win.py --schedule r186_r196_season_guard --profile-name WaiTrade2_Portfolio_BTC_DryRun --guard-key-suffix dryrun_20260524`
  - installed profile:
    - `C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Profiles\Charts\WaiTrade2_Portfolio_BTC_DryRun`
  - chart01:
    - BTCUSDm / magic `204345`
    - `InpSharedMonthlyGuardKey=r186_r196_season_guard_dryrun_20260524`
  - chart02:
    - BTCUSDm / magic `204355`
    - `InpSharedMonthlyGuardKey=r186_r196_season_guard_dryrun_20260524`

Remaining:
- This is now deployable for demo/forward validation.
- It still does not satisfy the final objective until a real validation run proves:
  - daily trades > 4,
  - profit > `$90000`,
  - no losing months,
  - on the actual 720d BTC evaluation path.

## 2026-05-24 schedule/live guard consistency lint

Problem:
- The best idea now exists in two forms:
  - proxy rules in `drop_filters` and `guards`,
  - deployable EA inputs in `live_profile.guard_overrides`.
- If these drift, a forward/demo run could test a different rule set than the proxy that passed the target.

Added:
- `scripts/portfolio_schedule_lint.py`
  - checks November low-balance OB filter consistency:
    - months,
    - hours,
    - max month-start balance,
    - zero multiplier.
  - checks March high-balance sweep filter consistency:
    - month,
    - hours,
    - max day,
    - min month-start balance.
  - checks 10/12 low-balance profit stop consistency:
    - guard month numbers,
    - max month-start balance,
    - profit target percent.
  - requires `shared_monthly_guard=true` and a non-empty key for multi-stream schedules.
- `tests/test_portfolio_schedule_lint.py`
  - verifies matching config passes,
  - verifies drift in live hours fails.

Validation:
- `python -m pytest tests\test_portfolio_schedule_lint.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_portfolio_schedule_runner.py tests\test_mt5_common.py -q`
  - `78 passed`
- `python scripts\portfolio_schedule_lint.py --schedule r186_r196_season_guard`
  - passed
- Re-ran proxy audit:
  - `total=188043.04`
  - `final=188243.04`
  - `daily=5.22`
  - `bad=0`
  - `pass=true`

Implication:
- The deployable profile and the passing proxy are now guarded against silent rule drift.
- Final target is still unproven until an actual MT5-compatible dual-stream validation exists.

## 2026-05-24 single-month screening and shared guard diagnostics

Screening rule:
- For similar strategy variants with small parameter changes, single-month tests are useful as a fast rejection screen.
- The month should start from the reconstructed balance before that month, not from `$200`, when the hypothesis depends on account scale, low-balance recovery, monthly profit stops, or shared guard state.
- A passing month is not evidence of full-window validity. It only earns a full 720d Real Ticks run or a portfolio proxy audit.

Reason:
- The BTC variants are path dependent:
  - month-start balance affects lot size and low/high balance gates,
  - prior trades affect monthly peak and stop/lock state,
  - multi-stream R186/R196 schedules need shared month state,
  - open positions, cooldown, and entry de-duplication can leak across a month boundary.
- Recent example: the R204/R205 November-only guard looked useful on a single month, but the 720d path degraded badly. Single-month screening caught a local repair, not a deployable strategy.

Added diagnostics:
- `InpSharedMonthlyGuardDebug` / `shared_monthly_guard_debug`
- `SHARED_GUARD` log events for init/load/entry/monthly stops/rate blocks.
- `scripts/shared_guard_log_audit.py` to audit MT5 logs for the expected guard key and both versions.
- Tests now cover the debug input mapping, generated profile, and log parser.

Validation:
- Generated dry-run profile with `--guard-key-suffix dryrun_20260524`.
- `chart01.chr`:
  - `InpVersion=V11-R186-OB8TAIL-R186`
  - `InpMagicNumber=204345`
  - `InpSharedMonthlyGuardKey=r186_r196_season_guard_dryrun_20260524`
  - `InpSharedMonthlyGuardDebug=true`
- `chart02.chr`:
  - `InpVersion=V11-R196-STOB4PT1M300-R196`
  - `InpMagicNumber=204355`
  - `InpSharedMonthlyGuardKey=r186_r196_season_guard_dryrun_20260524`
  - `InpSharedMonthlyGuardDebug=true`
- `python -m pytest tests\test_shared_guard_log_audit.py tests\test_portfolio_schedule_lint.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_portfolio_schedule_runner.py tests\test_mt5_common.py -q`
  - `80 passed`
- `python scripts\portfolio_schedule_runner.py --schedule r186_r196_season_guard --output results\backtest\portfolio_r186_r196_season_guard_20260524.md`
  - `total=188043.04`
  - `final=188243.04`
  - `daily=5.22`
  - `bad=0`
  - `pass=true`
- MetaEditor compile:
  - `WaiTrade_OB.mq5`: `0 errors, 0 warnings`
  - `ClearSharedMonthlyGuard.mq5`: `0 errors, 0 warnings`

Implication:
- Single-month optimisation is safe only as a queue-prioritisation tool.
- The best current candidate remains the account-level R186+R196 schedule proxy, now with deployable shared guard diagnostics for demo/forward validation.

## 2026-05-24 proxy robustness stress

Diagnose loop:
- Reproduced the remaining weak spot with the fast CSV schedule proxy.
- The schedule passes the headline target, but the weakest month is only barely positive.
- Hypothesis tested: if the schedule is only cosmetically passing, a small fixed execution cost per executed trade will quickly create bad months.

Change:
- Added `scripts/portfolio_schedule_stress.py`.
  - Reuses the YAML schedule.
  - Applies a fixed per-executed-trade cost to the source CSV trades.
  - Reports total profit, daily trade rate, bad month count, and weakest month.
- Added `monthly_profit_min` target support to `scripts/portfolio_schedule_runner.py`.
  - Current schedule now requires `monthly_profit_min: 0.01`, matching the stricter meaning of "every month profitable" instead of merely non-negative.

Validation:
- `python -m pytest tests\test_shared_guard_log_audit.py tests\test_portfolio_schedule_lint.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_stress.py tests\test_mt5_common.py -q`
  - `83 passed`
- `python scripts\portfolio_schedule_runner.py --schedule r186_r196_season_guard --output results\backtest\portfolio_r186_r196_season_guard_20260524.md`
  - `total=188043.04`
  - `final=188243.04`
  - `daily=5.22`
  - `monthly_profit_min=0.01`
  - `bad=0`
  - `pass=true`
- `python scripts\portfolio_schedule_stress.py --schedule r186_r196_season_guard --costs 0,0.05,0.1,0.25,0.5,1.0 --output results\backtest\portfolio_r186_r196_season_guard_stress_20260524.md`
  - cost `0.00`: bad `0`, weakest `2026-03`, profit `0.68`
  - cost `0.25`: bad `0`, weakest `2026-03`, profit `0.18`
  - cost `0.50`: bad `4`, weakest `2024-12`, profit `-60.52`
  - cost `1.00`: bad `5`, weakest `2024-11`, profit `-136.23`

Implication:
- The current candidate satisfies the strict proxy target, but robustness is weak.
- Next improvement should focus on increasing the minimum monthly margin, especially:
  - `2026-03`: only two surviving trades after the high-balance sweep guard, total `+0.68`.
  - low-balance `2024-11/2024-12`: many small trades become fragile once fixed execution cost is applied.
- Do not mark the overall goal complete until the path is validated in an MT5-compatible dual-stream or forward/demo setup.

## 2026-05-24 R63/R117 candidate scan

Diagnose loop:
- Symptom: the best R186+R196 proxy passes the target but `2026-03` has only `+0.68` profit.
- Hypothesis A: a March-specialist strategy can be added as a small third leg to increase the weakest-month margin.
- Hypothesis B: single-month specialist evidence is a partial-window artifact; full-window MT5 validation will fail.
- Hypothesis C: a different full-window leg may not fix March, but can improve total profit and frequency without breaking monthly profitability.

Added:
- `scripts/portfolio_candidate_scan.py`
  - scans `.trades.csv` candidates,
  - reports coverage month count,
  - supports `--min-covered-months` to avoid ranking single-month artifacts as deployable candidates.
- `tests/test_portfolio_candidate_scan.py`

Validation:
- `python scripts\portfolio_candidate_scan.py --candidate-glob "results/backtest/*.trades.csv" --focus-month 2026-03 --min-covered-months 20 --top 30 --output results\backtest\portfolio_candidate_scan_202603_covered20_20260524.md`
- `python -m pytest tests\test_shared_guard_log_audit.py tests\test_portfolio_candidate_scan.py tests\test_portfolio_schedule_lint.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_stress.py tests\test_mt5_common.py -q`
  - `84 passed`

R63 result:
- Single-month/partial R63 slices looked strong in March.
- Fresh MT5 720d run:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r63_j2_shallow_g30neg --symbol BTCUSDm --days 720 --timeout 900 --deposit 200`
  - result: `3485` trades, daily `4.8`, balance `$58382.09`
  - digest: `results/backtest/v11_r63_j2_shallow_g30neg_20240603_20260524_20260524.md`
  - bad months: `8`
  - `2026-03`: `-5966.99`
- Adding full-window R63 to R186+R196 fails even at `0.01x` because `2026-03` turns negative.
- Conclusion: Hypothesis A is rejected; Hypothesis B is supported.

R117 result:
- Fresh MT5 720d run:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r117_j2_r107_mneg_cut --symbol BTCUSDm --days 720 --timeout 900 --deposit 200`
  - result: `2032` trades, daily `2.8`, balance `$42320.43`
  - digest: `results/backtest/v11_r117_j2_r107_mneg_cut_20240603_20260524_20260524.md`
- Added deployable proxy schedule:
  - `r186_r196_r117_season_guard`
  - output: `results/backtest/portfolio_r186_r196_r117_season_guard_20260524.md`
  - stress: `results/backtest/portfolio_r186_r196_r117_season_guard_stress_20260524.md`
- Proxy result:
  - total `230772.62`
  - final `230972.62`
  - daily `7.89`
  - monthly profit min `0.01`
  - bad `0`
  - pass `true`
- Stress result:
  - cost `0.25`: bad `0`, weakest `2026-03`, profit `0.18`
  - cost `0.50`: bad `5`, weakest `2024-11`, profit `-61.73`
- Generated dry-run profile:
  - `temp/portfolio_profiles/r186_r196_r117_season_guard`
  - charts: R186/R196/R117
  - shared key: `r186_r196_r117_season_guard_dryrun_20260524`

Implication:
- Current best proxy has moved from R186+R196 to R186+R196+R117.
- It improves total profit and frequency substantially, but does not solve the thin `2026-03` margin.
- Next work should target a deployable way to increase minimum monthly profit, not just total profit.

## 2026-05-24 March actual-balance screen

Question:
- Can a March-specialist leg be enabled only for `2026-03` using the portfolio month-start balance to lift the weakest month above `+0.68`?

Method:
- Use MT5 Strategy Tester single-month Real Ticks runs.
- Start deposit equals the current best proxy month-start balance for `2026-03`: `$209584.85`.
- Window: `2026.03.01` to `2026.04.01`.
- Digest each report with `backtest_digest.py`.

Results:
- `v11_r63_j2_shallow_g30neg`
  - `348` trades, daily `11.2`, final `$200881.70`
  - month profit `-8703.15`
  - top bad cluster: `sig:sweep | hour:09 | risk:200-300 | cp:>-0.6 | exit:sl`
- `v11_r39_j2_start1000_m16_g5k`
  - `348` trades, daily `11.2`, final `$201034.43`
  - month profit `-8550.42`
  - top bad cluster: `sig:sweep | hour:09 | risk:200-300 | cp:>-0.6 | exit:sl`
- `v11_r167_j2_r159_early8_risk25`
  - `357` trades, daily `11.5`, final `$203929.43`
  - month profit `-5655.42`
  - top bad cluster: `sig:sweep | hour:09 | risk:200-300 | cp:>-0.6 | exit:sl`
- `v11_r187_j2_r186_lowbal_pt2`
  - `6` trades, daily `0.2`, final `$209570.64`
  - month profit `-14.21`
- `v11_r195_j2_r191_startup_pt1_screen`
  - `6` trades, daily `0.2`, final `$209570.64`
  - month profit `-14.21`

Conclusion:
- The apparent March-positive CSV candidates do not survive actual-balance single-month MT5 testing.
- The issue is path and balance dependence, not merely missing exposure.
- Current `2026-03` guard is doing the right thing by keeping only two small positive hour-22 sweep trades and blocking larger losing clusters.
- Next viable direction is not adding a March leg; it is either:
  - find a genuinely positive high-balance March rule via MT5 single-month screen first, or
  - accept the current March guard and move validation effort to a true multi-stream forward/demo audit.

## 2026-05-24 shared-balance return proxy

Problem:
- The path-level proxy adds each strategy's absolute MT5 PnL from independent balance paths.
- A true multi-stream account shares one balance, so the existing proxy can hide guard drift caused by faster shared-account growth.

Added:
- `scripts/portfolio_return_sim.py`
  - reconstructs each source strategy's balance path,
  - converts each trade into a per-trade return,
  - applies that return to one shared portfolio balance,
  - reuses the same monthly/drop guard logic.
- `tests/test_portfolio_return_sim.py`

Finding:
- Original `r186_r196_r117_season_guard` passes the absolute proxy, but fails the shared-return proxy:
  - bad months: `2024-10`, `2024-11`, `2025-05`
  - cause: shared-account growth makes the old `max_start=2500` early-season guards inactive.
- The shared-return dollar values are intentionally not trusted as MT5 profit estimates because they compound inferred returns and ignore lot caps/margin interaction.
- The pass/fail monthly path is still useful for diagnosing guard activation drift.

Robust guard:
- Added schedule `r186_r196_r117_robust_guard`.
- Changes from `r186_r196_r117_season_guard`:
  - November OB startup filter max start: `25000`
  - Monthly profit target stop months: `3,4,5,10,11,12`
  - Monthly profit target stop max start: `65000`
  - Profit target: `3%`

Validation:
- `python scripts\portfolio_schedule_runner.py --schedule r186_r196_r117_robust_guard --output results\backtest\portfolio_r186_r196_r117_robust_guard_20260524.md`
  - total `230968.30`
  - final `231168.30`
  - daily `6.97`
  - bad `0`
  - pass `true`
- `python scripts\portfolio_return_sim.py --schedule r186_r196_r117_robust_guard --output results\backtest\portfolio_r186_r196_r117_robust_return_proxy_20260524.md`
  - bad `0`
  - pass `true`
- `python scripts\portfolio_return_sim.py --schedule r186_r196_r117_robust_guard --fixed-cost-per-trade 0.25 --output results\backtest\portfolio_r186_r196_r117_robust_return_proxy_cost025_20260524.md`
  - bad `0`
  - pass `true`
- `python scripts\portfolio_schedule_stress.py --schedule r186_r196_r117_robust_guard --costs 0,0.05,0.1,0.25,0.5,1.0 --output results\backtest\portfolio_r186_r196_r117_robust_guard_stress_20260524.md`
  - cost `0.25`: bad `0`, weakest `2026-03`, profit `0.18`
  - cost `0.50`: bad `1`, weakest `2026-03`, profit `-0.32`
  - cost `1.00`: bad `2`, weakest `2024-12`, profit `-205.16`
- `python scripts\portfolio_schedule_lint.py --schedule r186_r196_r117_robust_guard`
  - passed
- `python -m pytest tests\test_portfolio_return_sim.py tests\test_shared_guard_log_audit.py tests\test_portfolio_candidate_scan.py tests\test_portfolio_schedule_lint.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_stress.py tests\test_mt5_common.py -q`
  - `86 passed`

Implication:
- Current best proxy is now `r186_r196_r117_robust_guard`.
- It is stronger than the prior three-leg schedule because both absolute PnL proxy and shared-return guard-drift proxy pass.
- Adding months `3,4,11` to the profit-target stop reduced the fixed-cost `0.50/entry` bad-month count from `4` to `1`.
- The remaining `0.50/entry` bad month is `2026-03`, caused by only two tiny positive trades; the current trade set has no deployable way to improve that without finding a new March-positive MT5 rule.
- It is still not a valid MT5 multi-strategy 720d backtest; the next proof step is forward/demo or a true multi-stream tester implementation.

## 2026-05-25 R209 March patch

Diagnose loop:
- Symptom: `r186_r196_r117_robust_guard` passes the strict proxy target, but `2026-03` is only `+0.68`; fixed cost `0.50/entry` turns it negative.
- Feedback loop: MT5 Strategy Tester single-month Real Ticks, `2026.03.01` to `2026.04.01`, start deposit `$209780.53` from the robust portfolio path.
- Hypothesis A: March-positive CSV candidates are balance/path artifacts and fail at actual balance.
- Hypothesis B: R142 HTF pullback is almost usable, but weak hours dilute the edge.
- Hypothesis C: a smaller March-only HTF pullback leg can raise the minimum monthly margin without adding too many trades.

Actual-balance screen batch 2:
- Rejected all broad candidates:
  - `v11_r35_j2_lg405_start1000`: `348` trades, final `$201230.43`, profit `-8550.10`
  - `v11_r174_j2_r163_reentry5_cd15_m10`: `192` trades, final `$192934.65`, profit `-16845.88`
  - `v11_r104_j2_r45_mneg_pl5_k70`: `28` trades, final `$196552.60`, profit `-13227.93`
  - `v11_r168_j2_r163_risk210`: `8` trades, final `$207618.95`, profit `-2161.58`
  - `v11_r168_j2_r163_risk205`: `8` trades, final `$207670.11`, profit `-2110.42`
  - `v11_r49_j2_g30m10_r58`: `348` trades, final `$201230.43`, profit `-8550.10`
  - `v11_r58_j2_g30_swp_mid_001`: `348` trades, final `$201230.43`, profit `-8550.10`
  - `v11_r142_j2_htfpb_r200_300_no132314_cp06`: `298` trades, final `$209767.64`, profit `-12.89`
- R35/R49/R58 are the same high-frequency sweep shape; top bad cluster remains March hour-09 sweep SL.
- R142 was closest, but too broad: `298` trades for a tiny loss and not cost robust.

R142 hour diagnosis:
- R142 actual-balance March weak hours:
  - hour `01`: `20` trades, `-16.02` proxy PnL
  - hour `09`: `24` trades, `-8.42`
  - hour `19`: `11` trades, `-5.05`
- R208 (`v11_r208_j2_r142_no010919`) blocked hours `1,9,19` in addition to `13,14,23`.
  - Actual-balance March: `245` trades, final `$209790.47`, profit `+9.94`
  - Cost screen rejected it: at `0.05/entry`, March turns negative (`-1.19`) because the edge is too fragmented.

R209 result:
- R209 (`v11_r209_j2_r142_h00182022`) keeps only robust HTF pullback hours `0,18,20,22` and adds deployable `entry_months: "3"`.
- Added EA input `InpEntryMonths`; `SignalEngine` now blocks new entries outside listed months. This keeps backtest/live aligned instead of requiring manual March-only chart attachment.
- Compile validation:
  - Native MetaEditor log: `Result: 0 errors, 0 warnings`
- MT5 actual-balance March:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r209_j2_r142_h00182022 --symbol BTCUSDm --from 2026.03.01 --to 2026.04.01 --timeout 900 --deposit 209780.53`
  - result: `67` trades, daily `2.2`, final `$209807.28`, profit `+26.75`
  - digest: `results/backtest/v11_r209_j2_r142_h00182022_20260301_20260401_20260525.md`
- MT5 720d standalone after `entry_months=3`:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r209_j2_r142_h00182022 --symbol BTCUSDm --days 720 --timeout 900 --deposit 200`
  - result: `30` trades, final `$216.36`, bad months `0`
  - digest: `results/backtest/v11_r209_j2_r142_h00182022_20240604_20260525_20260525.md`

New best proxy:
- Added schedule `r186_r196_r117_r209_march_guard`.
- It uses the robust R186/R196/R117 base plus R209 full-window March patch.
- Important correction: the first proxy used the R209 single-month actual-balance CSV. That was too optimistic because the single-month window produced `67` March trades, while the full 720d R209 path produced only `20` trades in `2026-03`. This is a state/warmup/path-dependence artifact, so the schedule now uses the full-window CSV only.
- Proxy result:
  - output: `results/backtest/portfolio_r186_r196_r117_r209_march_guard_20260525.md`
  - total `230982.61`
  - final `231182.61`
  - daily `6.99`
  - bad `0`
  - `2026-03`: `22` trades, profit `+15.00`
- Fixed-cost stress:
  - output: `results/backtest/portfolio_r186_r196_r117_r209_march_guard_stress_20260525.md`
  - cost `0.25`: bad `0`, weakest `2026-05`, profit `+5.54`
  - cost `0.50`: bad `0`, weakest `2026-03`, profit `+4.00`
- Compared with `r186_r196_r117_robust_guard`, this lifts the weakest-month margin and makes cost `0.50/entry` materially safer.

Validation:
- `python scripts\portfolio_schedule_lint.py --schedule r186_r196_r117_r209_march_guard`
  - passed
- Added lint protection: entry-month patch strategies must use full-window CSV evidence; a single-month CSV is rejected.
- `python scripts\mt5_portfolio_live_profile.py --schedule r186_r196_r117_r209_march_guard --guard-key-suffix dryrun_20260525`
  - generated `temp/portfolio_profiles/r186_r196_r117_r209_march_guard`
  - chart04 R209 has `InpEntryMonths=3`, magic `204368`, shared key `r186_r196_r117_r209_march_guard_dryrun_20260525`
- Added `scripts/mt5_portfolio_profile_audit.py`
  - compares generated/installed `.chr` inputs against `config/portfolio_schedules.yaml` + `config/strategies.yaml`
  - catches drift such as missing R209 `InpEntryMonths=3`, wrong magic, wrong shared key, or edited chart inputs
- Profile audits:
  - generated profile: `results/backtest/portfolio_r186_r196_r117_r209_march_guard_profile_audit_20260525.md`, pass
  - installed profile: `results/backtest/portfolio_r186_r196_r117_r209_march_guard_installed_profile_audit_20260525.md`, pass
- Deployed dry-run profile without starting MT5:
  - `WaiTrade2_Portfolio_BTC_R209_DryRun`
  - installed under MT5 `MQL5\Profiles\Charts`
- Added `scripts/mt5_compile_win.py`
  - syncs project `mql5\Experts`, `mql5\Include`, and `mql5\Scripts` into Windows MT5 data dir
  - compiles `WaiTrade_OB.mq5` and `ClearSharedMonthlyGuard.mq5`
  - treats MetaEditor success as `Result: 0 errors` from the log, not process return code
  - validated current tree: both files compiled with `0 errors`, `0 warnings`
- `python scripts\mt5_portfolio_deploy_win.py --schedule r186_r196_r117_r209_march_guard --profile-name WaiTrade2_Portfolio_BTC_R209_DryRun --guard-key-suffix dryrun_20260525 --compile`
  - generated, installed, and compiled successfully; terminal was not started
- Added `scripts/portfolio_preflight_win.py`
  - runs schedule/live lint
  - writes path-level proxy, fixed-cost stress, and shared-return proxy reports
  - requires fixed cost `0.50/entry` to keep zero bad months
  - deploys the MT5 profile without starting terminal
  - optionally compiles with the Windows MetaEditor log validator
  - audits generated and installed profiles
- Current best preflight:
  - command: `python scripts\portfolio_preflight_win.py --schedule r186_r196_r117_r209_march_guard --profile-name WaiTrade2_Portfolio_BTC_R209_DryRun --guard-key-suffix dryrun_20260525 --output-prefix portfolio_r186_r196_r117_r209_march_guard_preflight_20260525 --output results\backtest\portfolio_r186_r196_r117_r209_march_guard_preflight_20260525.md --compile`
  - result: pass
  - proxy: total `230982.61`, daily `6.99`, bad `0`
  - stress cost `0.50`: bad `0`, weakest `2026-03`, profit `+4.00`
  - shared-return proxy: daily `6.94`, bad `0`
  - generated/installed profile audit: pass
- `python -m pytest tests\test_mt5_common.py tests\test_portfolio_schedule_lint.py tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_stress.py tests\test_mt5_portfolio_live_profile.py -q`
  - `80 passed`
- Full targeted regression after profile audit:
  - `python -m pytest tests\test_portfolio_return_sim.py tests\test_shared_guard_log_audit.py tests\test_portfolio_candidate_scan.py tests\test_portfolio_schedule_lint.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_mt5_portfolio_profile_audit.py tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_stress.py tests\test_mt5_common.py -q`
- Full targeted regression after Windows compile script:
  - `python -m pytest tests\test_mt5_compile_win.py tests\test_portfolio_return_sim.py tests\test_shared_guard_log_audit.py tests\test_portfolio_candidate_scan.py tests\test_portfolio_schedule_lint.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_mt5_portfolio_profile_audit.py tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_stress.py tests\test_mt5_common.py -q`
  - `93 passed`
- Full targeted regression after preflight:
  - `python -m pytest tests\test_mt5_compile_win.py tests\test_portfolio_preflight_win.py tests\test_portfolio_return_sim.py tests\test_shared_guard_log_audit.py tests\test_portfolio_candidate_scan.py tests\test_portfolio_schedule_lint.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_mt5_portfolio_profile_audit.py tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_stress.py tests\test_mt5_common.py -q`
  - `95 passed`

Implication:
- Current best proxy moves to `r186_r196_r117_r209_march_guard`.
- R209 should be treated as a March-only patch, not a standalone main leg.
- Do not use R209 single-month CSV in portfolio schedules; it overstates deployable March exposure.
- Remaining proof gap: this is still a CSV path-level portfolio proxy assembled from individual MT5 720d legs, not a true MT5 multi-stream same-account 720d backtest.

## 2026-05-25 single-month screening workflow

Question:
- Can we speed up similar small strategy edits by taking the balance before a bad month, using it as the initial deposit, and testing only that month?

Conclusion:
- Yes, as a rejection screen. It can cut waiting time when iterating on narrow changes aimed at a known bad month such as `2024-11`.
- No, as an acceptance criterion. Single-month MT5 runs do not reconstruct earlier EA state, warmed zones, pending state, cooldowns, and path-dependent trade availability. R209 March already showed the risk: single-month March produced `67` trades, while the same strategy inside the full 720d path produced only `20` March trades.

Tooling:
- Fixed `scripts/single_month_screen.py` so it can parse both readable Chinese reports (`资金`, `合计`) and the existing mojibake report text (`璧勯噾`, `鍚堣`).
- Added `tests/test_single_month_screen.py`.
- Example command:
  - `python scripts\single_month_screen.py --trades results\backtest\v11_r186_j2_r185_ob8_tail_cut_20260524.trades.csv --deposit 200 --final-balance 96941.72 --months 2024-11 --strategy v11_r186_j2_r185_ob8_tail_cut --timeout 1200`
  - output command uses `--deposit 507.58` for `2024-11`, matching the full-window estimated month-start balance.

Regression:
- `python -m pytest tests\test_single_month_screen.py -q`
  - `5 passed`
- `python -m pytest tests\test_mt5_common.py tests\test_portfolio_schedule_lint.py tests\test_portfolio_preflight_win.py tests\test_mt5_compile_win.py tests\test_single_month_screen.py -q`
  - `87 passed`

Rule:
- Use single-month actual-balance screening to kill bad ideas quickly.
- Promote only candidates that pass the full fixed-window 720d Real Ticks path and the portfolio schedule lint/stress/preflight gates.

## 2026-05-25 R210 December patch attempt

Hypothesis:
- Stress `cost=1.00/entry` shows the current best proxy fails mainly at `2024-12`.
- Existing full-window CSV scan found `v11_r104_j2_r45_mneg_pl10_k50` has positive `2024-12` contribution, so a deployable December-only patch might improve the weak month without polluting other months.

Implementation:
- Added `v11_r210_j2_r104_dec_patch` in `config/strategies.yaml`.
- It inherits the R104/R45 monthly-negative sweep setup, keeps `monthly_profit_lock_start_pct=10.0`, `monthly_profit_lock_keep_pct=50.0`, and adds `entry_months: "12"`.

MT5 full-window validation:
- command: `python scripts\mt5_backtest_win.py --strategy v11_r210_j2_r104_dec_patch --symbol BTCUSDm --days 720 --timeout 1200 --deposit 200`
- result: `63` trades, final balance `$301.49`
- digest: `results/backtest/v11_r210_j2_r104_dec_patch_20240604_20260525_20260525.md`
- trade CSV: `results/backtest/v11_r210_j2_r104_dec_patch_20240604_20260525_20260525.trades.csv`
- monthly:
  - `2024-12`: `21` trades, `+14.61`
  - `2025-12`: `42` trades, `+86.88`
  - bad months: `0`

Portfolio test:
- Temporary schedule with R210 added:
  - proxy total `231058.46`, daily `7.07`, bad `0`
  - stress `cost=0.50`: bad `0`, weakest `2026-03`, `+4.00`
  - stress `cost=1.00`: bad `2`, weakest `2024-12`, `-211.50`
- Current best without R210:
  - proxy total `230982.61`, daily `6.99`, bad `0`
  - stress `cost=1.00`: weakest `2024-12`, `-205.16`

Conclusion:
- Reject R210 as a portfolio add-on. It is positive as a standalone December-only leg, but in the portfolio path it adds trades and changes the month-profit-target timing, slightly worsening the high-cost December stress case.
- Current best remains `r186_r196_r117_r209_march_guard`.
- The next useful December investigation should target deployable filters or guard logic, not another raw additive December leg.

## 2026-05-25 R211 March patch tightening

Diagnosis:
- Current best `r186_r196_r117_r209_march_guard` passes the objective proxy, but stress `cost=0.50/entry` leaves only `+4.00` in `2026-03`.
- Added `scripts/portfolio_schedule_attribution.py` to split each schedule month by source under the same guard/filter/cost path.
- Attribution showed the March stress margin is almost entirely R209M:
  - no cost: R209M `20` trades, `+14.31`
  - cost `0.50`: R209M `20` trades, `+4.31`, total March `+4.00`

Hypothesis:
- R209M's low-end March HTFPB risk bucket is cost-polluting. CSV inspection showed several `risk≈202-208` March trades were net negative after realistic fixed costs.
- Tightening March HTFPB from the old effective `200-300` bucket to `220-300` should reduce trades and improve March net quality.

Implementation:
- Added `v11_r211_j2_r142_h20_risk220` in `config/strategies.yaml`.
- Important buglet found during diagnosis: R142/R209 originally enforce the `200-300` HTFPB bucket via `bad_cluster` filters, not via `InpHTFPullbackRiskMin/Max`.
- First R211 attempt set only `htf_pullback_risk_min=220`, which did nothing because MQL only applies this filter when `InpHTFPullbackRiskMax > InpHTFPullbackRiskMin`.
- Fixed R211 to set both:
  - `htf_pullback_risk_min: 220.0`
  - `htf_pullback_risk_max: 300.0`

MT5 full-window validation:
- command: `python scripts\mt5_backtest_win.py --strategy v11_r211_j2_r142_h20_risk220 --symbol BTCUSDm --days 720 --timeout 1200 --deposit 200`
- result: `25` trades, win rate `80.0%`, final balance `$222.58`
- digest: `results/backtest/v11_r211_j2_r142_h20_risk220_20240604_20260525_20260525.md`
- trade CSV: `results/backtest/v11_r211_j2_r142_h20_risk220_20240604_20260525_20260525.trades.csv`

New best proxy:
- Added schedule `r186_r196_r117_r211_march_guard`.
- It replaces R209M with R211M and keeps R186/R196/R117 and the same shared guard rules.
- Proxy:
  - output: `results/backtest/portfolio_r186_r196_r117_r211_march_guard_20260525.md`
  - total `230986.67`
  - final `231186.67`
  - daily `6.99`
  - bad `0`
  - `2026-03`: `18` trades, profit `+19.05`
- Fixed-cost stress:
  - output: `results/backtest/portfolio_r186_r196_r117_r211_march_guard_stress_20260525.md`
  - cost `0.50`: bad `0`, weakest `2026-05`, profit `+4.29`
  - cost `1.00`: bad `1`, weakest `2024-12`, profit `-205.16`
- Improvement over R209 schedule:
  - `2026-03` no-cost month profit improves from `+15.00` to `+19.05`
  - `cost=0.50` weakest month moves away from March; March becomes `+10.05` in attribution
  - `cost=1.00` bad months drop from `2` to `1`

Preflight:
- command: `python scripts\portfolio_preflight_win.py --schedule r186_r196_r117_r211_march_guard --profile-name WaiTrade2_Portfolio_BTC_R211_DryRun --guard-key-suffix dryrun_20260525 --output-prefix portfolio_r186_r196_r117_r211_march_guard_preflight_20260525 --output results\backtest\portfolio_r186_r196_r117_r211_march_guard_preflight_20260525.md --compile`
- result: pass
- proxy: total `230986.67`, daily `6.99`, bad `0`
- stress cost `0.50`: bad `0`, weakest `2026-05`, profit `+4.29`
- shared-return proxy: daily `6.94`, bad `0`
- generated/installed profile audit: pass
- compile: pass

Implication:
- Current best proxy moves to `r186_r196_r117_r211_march_guard`.
- R211 is a cleaner March-only patch than R209 and should replace R209 in dry-run profiles.
- Remaining proof gap is unchanged: this is still a CSV path-level portfolio proxy plus profile/preflight validation, not a true MT5 multi-stream same-account 720d Strategy Tester run.

## 2026-05-25 R212 high-balance May guard

Diagnosis:
- After R211, the weakest fixed-cost `0.50/entry` month became `2026-05`, profit `+4.29`.
- Attribution showed:
  - `2026-05`: R117 contributed `1` trade, `-0.64` after cost `0.50`
  - `2025-05`: the low-balance May recovery path must not be globally removed
- Proxy test: skip R117 only when `monthnum=5` and month-start balance is high. Thresholds `>=5000` preserved the low-balance 2025 May path while removing the high-balance 2026 May loss.

Implementation:
- Added EA inputs:
  - `InpHighBalanceNoEntryMonths`
  - `InpHighBalanceNoEntryMinMonthStartBalance`
- Added YAML keys:
  - `high_balance_no_entry_months`
  - `high_balance_no_entry_min_month_start_balance`
- Implemented the guard in `PassMonthlyEntryGuard()` using the shared monthly start balance.
- Added `v11_r212_j2_r117_no_may_highbal`:
  - inherits the R117 monthly-negative cut shape
  - `high_balance_no_entry_months: "5"`
  - `high_balance_no_entry_min_month_start_balance: 5000.0`

MT5 full-window validation:
- command: `python scripts\mt5_backtest_win.py --strategy v11_r212_j2_r117_no_may_highbal --symbol BTCUSDm --days 720 --timeout 1200 --deposit 200`
- result: `2031` trades, final balance `$42320.57`
- compared with R117: one fewer trade and slight balance improvement (`$42320.43` -> `$42320.57`)
- digest: `results/backtest/v11_r212_j2_r117_no_may_highbal_20240604_20260525_20260525.md`
- CSV: `results/backtest/v11_r212_j2_r117_no_may_highbal_20240604_20260525_20260525.trades.csv`

New best proxy:
- Added schedule `r186_r196_r212_r211_march_guard`.
- Proxy:
  - output: `results/backtest/portfolio_r186_r196_r212_r211_march_guard_20260525.md`
  - total `231013.09`
  - final `231213.09`
  - daily `6.99`
  - bad `0`
  - `2026-05`: `4` trades, `+6.93`
- Fixed-cost stress:
  - output: `results/backtest/portfolio_r186_r196_r212_r211_march_guard_stress_20260525.md`
  - cost `0.50`: bad `0`, weakest `2026-05`, `+4.93`
  - cost `1.00`: bad `1`, weakest `2024-12`, `-205.16`

Preflight:
- command: `python scripts\portfolio_preflight_win.py --schedule r186_r196_r212_r211_march_guard --profile-name WaiTrade2_Portfolio_BTC_R212_R211_DryRun --guard-key-suffix dryrun_20260525 --output-prefix portfolio_r186_r196_r212_r211_march_guard_preflight_20260525 --output results\backtest\portfolio_r186_r196_r212_r211_march_guard_preflight_20260525.md --compile`
- result: pass
- proxy: total `231013.09`, daily `6.99`, bad `0`
- stress cost `0.50`: bad `0`, weakest `2026-05`, profit `+4.93`
- shared-return proxy: daily `6.94`, bad `0`
- generated/installed profile audit: pass
- compile: pass

Implication:
- Current best proxy moves to `r186_r196_r212_r211_march_guard`.
- R212 is a small but deployable May robustness improvement over R117 in the portfolio.
- Remaining proof gap is unchanged: true MT5 same-account multi-stream 720d validation is still missing.

## 2026-05-25 R197 replacement and May thin-month scan

Question:
- Check whether `v11_r197_j2_r195_pt1_min500` should replace R196, or be added as another leg, to improve the remaining thin month `2026-05`.
- Evaluate the user's proposed speed-up: for a bad month such as `2024-11`, record the prior month-end balance as the new initial deposit and run only that calendar month.

R197 replacement result:
- Differential proxy replaced R196 with R197 inside `r186_r196_r212_r211_march_guard`.
- Result was exactly unchanged at all checked costs:
  - cost `0.00`: total `231013.09`, weakest `2026-05 +6.93`
  - cost `0.50`: total `228481.41`, weakest `2026-05 +4.93`
  - cost `1.00`: total `225703.61`, bad `1`, weakest `2024-12 -205.16`
- Interpretation: under the current portfolio path and shared guard, R197 is an equivalent replacement for R196, not an improvement.

R197 add-on result:
- Adding R197 as a fifth leg was the only full-window candidate that raised `2026-05` under the current proxy guard:
  - cost `0.50`: `2026-05` improves from `+4.93` to `+7.40`
  - cost `1.00`: still has one bad month, `2024-12`, and the weakest result worsens to about `-215.20`
- Rejected as a candidate upgrade because it is a same-family near-duplicate of R196 and mainly doubles the same signal exposure. That is not a clean robustness improvement.

Single-month screen assessment:
- Using the previous month-end balance as the next month's initial deposit is useful as a fast rejection screen.
- It is especially useful for questions like: "does this parameter change fix `2024-11` without waiting for a full 720d run?"
- It is not acceptance evidence. Passing candidates still need the fixed-window 720d Real Ticks run because full-path behavior depends on compounding, month-start guard state, shared portfolio guard, OB/EA state, concurrent exposure, and month-internal trade ordering.
- Existing helper: `scripts/single_month_screen.py` generates month-only MT5 commands with the inferred month-start balance. Treat its output as a screening loop only.

## 2026-05-25 R213 December coverage patch

Diagnosis:
- After R212/R211, the no-cost proxy already had zero bad months, but fixed-cost `1.00/entry` still had one bad month:
  - `2024-12`: `-205.16`
- Full-window candidate scans showed no independent always-on leg could repair that month without breaking other months.
- December-only proxy tests suggested R104-derived positive hours could provide targeted coverage.

Screening variants:
- Added `v11_r213_j2_r104_dec_hours_patch`:
  - inherits `v11_r104_j2_r45_mneg_pl5_k70`
  - `entry_months: "12"`
  - allowed hours: `6,11,14,15,18`
  - `magic_number: 204372`
- Added `v11_r214_j2_r195_dec_hours_patch`:
  - inherits `v11_r195_j2_r191_startup_pt1_screen`
  - `entry_months: "12"`
  - allowed hours: `11,15`
  - `magic_number: 204373`

Single-month screen:
- R213 command: `python scripts\mt5_backtest_win.py --strategy v11_r213_j2_r104_dec_hours_patch --symbol BTCUSDm --from 2024.12.01 --to 2025.01.01 --deposit 2016.62 --timeout 1200`
  - result: `33` trades, final `$2246.66`, profit `+230.04`
- R214 command: `python scripts\mt5_backtest_win.py --strategy v11_r214_j2_r195_dec_hours_patch --symbol BTCUSDm --from 2024.12.01 --to 2025.01.01 --deposit 2016.62 --timeout 1200`
  - result: `17` trades, final `$4197.96`, profit `+2181.34`
- Important caveat: R214's single-month edge came heavily from `market_close` exits at the test window boundary, so it required full-window validation before trusting.

MT5 full-window validation:
- R214 command: `python scripts\mt5_backtest_win.py --strategy v11_r214_j2_r195_dec_hours_patch --symbol BTCUSDm --days 720 --timeout 1200 --deposit 200`
  - result: `4` trades, final `$222.67`
  - full-window portfolio effect was too small; rejected as a schedule upgrade.
- R213 command: `python scripts\mt5_backtest_win.py --strategy v11_r213_j2_r104_dec_hours_patch --symbol BTCUSDm --days 720 --timeout 1200 --deposit 200`
  - result: `19` trades, final `$351.59`
  - digest: `results/backtest/v11_r213_j2_r104_dec_hours_patch_20240604_20260525_20260525.md`
  - CSV: `results/backtest/v11_r213_j2_r104_dec_hours_patch_20240604_20260525_20260525.trades.csv`

New best proxy:
- Added schedule `r186_r196_r212_r211_r213_dec_guard`.
- Proxy:
  - output: `results/backtest/portfolio_r186_r196_r212_r211_r213_dec_guard_20260525.md`
  - total `231111.91`
  - final `231311.91`
  - daily `7.01`
  - bad `0`
  - `2024-12`: `+101.92`
  - `2026-05`: `+6.93`
- Fixed-cost stress:
  - output: `results/backtest/portfolio_r186_r196_r212_r211_r213_dec_guard_stress_20260525.md`
  - cost `0.50`: bad `0`, weakest `2026-05`, `+4.93`
  - cost `1.00`: bad `0`, weakest `2026-03`, `+1.05`
- Attribution at cost `1.00`:
  - output: `results/backtest/portfolio_r186_r196_r212_r211_r213_dec_guard_attribution_cost100_20260525.md`
  - `2024-12` month profit `+54.64`
  - R213D contribution `+44.34` on `6` executed trades, with `5` skipped after the shared monthly profit target.

Preflight:
- command: `python scripts\portfolio_preflight_win.py --schedule r186_r196_r212_r211_r213_dec_guard --profile-name WaiTrade2_Portfolio_BTC_R212_R211_R213_DryRun --guard-key-suffix dryrun_20260525 --output-prefix portfolio_r186_r196_r212_r211_r213_dec_guard_preflight_20260525 --output results\backtest\portfolio_r186_r196_r212_r211_r213_dec_guard_preflight_20260525.md --compile`
- result: pass
- proxy: total `231111.91`, daily `7.01`, bad `0`
- stress cost `1.00`: bad `0`, weakest `2026-03`, profit `+1.05`
- shared-return proxy: daily `6.91`, bad `0`
- generated/installed profile audit: pass
- compile: pass

Implication:
- Current best proxy moves to `r186_r196_r212_r211_r213_dec_guard`.
- R213 is a targeted December coverage leg that improves the stress boundary without changing the existing four-leg core.
- The main remaining proof gap is unchanged: this is a CSV path-level portfolio proxy plus deployable profile/preflight, not a true MT5 same-account multi-stream 720d Strategy Tester run.

## 2026-05-25 R216 March coverage patch

Diagnosis:
- After adding R213, fixed-cost `1.00/entry` had zero bad months, but the weakest month was still thin:
  - `2026-03`: `+1.05`
- Attribution showed:
  - R211M contributed `+2.37`
  - R186 and R196 each contributed `-0.66`
  - the March margin was therefore almost entirely dependent on a small R211M edge.

Candidate scan:
- A March-only proxy scan found old branch `v11_r39_j2_start1000_m16_g5k` could improve March in historical CSV form.
- First deployable screen:
  - Added `v11_r215_j2_r39_march_patch` with `entry_months: "3"` and `magic_number: 204374`.
  - Single-month high-balance command: `python scripts\mt5_backtest_win.py --strategy v11_r215_j2_r39_march_patch --symbol BTCUSDm --from 2026.03.01 --to 2026.04.01 --deposit 209905.64 --timeout 1200`
  - Result: `348` trades, final `$201355.43`, loss about `-8550.21`
  - Interpretation: the old CSV proxy was misleading under the current portfolio's high month-start balance. R215 rejected.

Bad-cluster diagnosis from R215:
- Digest: `results/backtest/v11_r215_j2_r39_march_patch_20260301_20260401_20260525.md`
- High-balance 2026-03 positive hours were concentrated in `23,2,13,16,11`.
- Major negative drag came from hours such as `14,0,15,8,5`.

R216 implementation:
- Added `v11_r216_j2_r215_march_hours_patch`:
  - inherits `v11_r215_j2_r39_march_patch`
  - `entry_months: "3"`
  - allowed hours: `2,11,13,16,23`
  - `magic_number: 204375`
- YAML/set audit showed:
  - `InpEntryMonths=3`
  - `InpNoEntryHours=0,1,3,4,5,6,7,8,9,10,12,14,15,17,18,19,20,21,22`

Single-month screen:
- command: `python scripts\mt5_backtest_win.py --strategy v11_r216_j2_r215_march_hours_patch --symbol BTCUSDm --from 2026.03.01 --to 2026.04.01 --deposit 209905.64 --timeout 1200`
- result: `88` trades, final `$226168.61`, profit about `+16262.97`
- digest: `results/backtest/v11_r216_j2_r215_march_hours_patch_20260301_20260401_20260525.md`

MT5 full-window validation:
- command: `python scripts\mt5_backtest_win.py --strategy v11_r216_j2_r215_march_hours_patch --symbol BTCUSDm --days 720 --timeout 1200 --deposit 200`
- result: `51` trades, final `$388.69`
- digest: `results/backtest/v11_r216_j2_r215_march_hours_patch_20240604_20260525_20260525.md`
- CSV: `results/backtest/v11_r216_j2_r215_march_hours_patch_20240604_20260525_20260525.trades.csv`

New best proxy:
- Added schedule `r186_r196_r212_r211_r213_r216_guard`.
- Proxy:
  - output: `results/backtest/portfolio_r186_r196_r212_r211_r213_r216_guard_20260525.md`
  - total `231278.14`
  - final `231478.14`
  - daily `7.05`
  - bad `0`
  - `2026-03`: `+225.39`
  - `2026-05`: `+6.93`
- Fixed-cost stress:
  - output: `results/backtest/portfolio_r186_r196_r212_r211_r213_r216_guard_stress_20260525.md`
  - cost `0.50`: bad `0`, weakest `2026-05`, `+4.93`
  - cost `1.00`: bad `0`, weakest `2026-05`, `+2.93`
- Attribution at cost `1.00`:
  - output: `results/backtest/portfolio_r186_r196_r212_r211_r213_r216_guard_attribution_cost100_20260525.md`
  - `2026-03` month profit `+178.39`
  - R216M contribution `+177.35` on `29` executed trades, with `2` skipped.

Preflight:
- command: `python scripts\portfolio_preflight_win.py --schedule r186_r196_r212_r211_r213_r216_guard --profile-name WaiTrade2_Portfolio_BTC_R212_R211_R213_R216_DryRun --guard-key-suffix dryrun_20260525 --output-prefix portfolio_r186_r196_r212_r211_r213_r216_guard_preflight_20260525 --output results\backtest\portfolio_r186_r196_r212_r211_r213_r216_guard_preflight_20260525.md --compile`
- result: pass
- proxy: total `231278.14`, daily `7.05`, bad `0`
- stress cost `1.00`: bad `0`, weakest `2026-05`, profit `+2.93`
- shared-return proxy: daily `6.95`, bad `0`
- generated/installed profile audit: pass
- compile: pass

Implication:
- Current best proxy moves to `r186_r196_r212_r211_r213_r216_guard`.
- The remaining weakest stress month is now `2026-05`, not March.
- R216 is a targeted March coverage leg discovered by rejecting the broad R215 with the single-month high-balance screen, then narrowing to positive-hour clusters.
- The main remaining proof gap is unchanged: this is a CSV path-level portfolio proxy plus deployable profile/preflight, not a true MT5 same-account multi-stream 720d Strategy Tester run.

Follow-up May scan:
- With `r186_r196_r212_r211_r213_r216_guard` as the new base, a May-only add-on scan found only two candidates that improved `2026-05` under cost `1.00`:
  - `v11_r197_j2_r195_pt1_min500`
  - `v11_r200_j2_r196_htfpb_122023_micro`
- Both improved `2026-05` only from `+2.93` to `+4.40`, and both are close relatives of the existing R196 lane.
- Rejected for now: the improvement is too small and mainly adds duplicate exposure rather than a clean independent patch.

Deployable May screen:
- Added `v11_r217_j2_r197_may_patch`:
  - inherits `v11_r197_j2_r195_pt1_min500`
  - `entry_months: "5"`
  - `magic_number: 204376`
- Added `v11_r218_j2_r200_may_patch`:
  - inherits `v11_r200_j2_r196_htfpb_122023_micro`
  - `entry_months: "5"`
  - `magic_number: 204377`
- Single-month high-balance screen used the current six-leg May start balance:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r217_j2_r197_may_patch --symbol BTCUSDm --from 2026.05.01 --to 2026.06.01 --deposit 231471.21 --timeout 1200`
  - result: `2` trades, final `$231474.47`, profit about `+3.26`
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r218_j2_r200_may_patch --symbol BTCUSDm --from 2026.05.01 --to 2026.06.01 --deposit 231471.21 --timeout 1200`
  - result: `2` trades, final `$231474.47`, profit about `+3.26`
- Conclusion: both candidates are real but too small. After a `1.00/entry` stress cost, their net contribution is only about `+1.26`; not enough to justify adding another duplicate R196-family lane.

Expanded May high-balance screen:
- Broadened the May screen to the top non-R196-family candidates from the full-window CSV scan.
- R208:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r208_j2_r142_no010919 --symbol BTCUSDm --from 2026.05.01 --to 2026.06.01 --deposit 231471.21 --timeout 1200`
  - result: `88` trades, final `$231451.21`, loss about `-20.00`
  - digest: `results/backtest/v11_r208_j2_r142_no010919_20260501_20260601_20260525.md`
- R203:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r203_htfpb_h12_sell_only_micro --symbol BTCUSDm --from 2026.05.01 --to 2026.06.01 --deposit 231471.21 --timeout 1200`
  - result: `1` trade, final `$231468.90`, loss about `-2.31`
  - digest: `results/backtest/v11_r203_htfpb_h12_sell_only_micro_20260501_20260601_20260525.md`
- R192:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r192_j2_r186_sweep13_only_probe --symbol BTCUSDm --from 2026.05.01 --to 2026.06.01 --deposit 231471.21 --timeout 1200`
  - result: `12` trades, final `$231466.06`, loss about `-5.15`
  - digest: `results/backtest/v11_r192_j2_r186_sweep13_only_probe_20260501_20260601_20260525.md`
- Conclusion: no non-duplicate May patch survived the high-balance single-month screen. The current best should stay at six legs.

May high-balance noise reduction:
- Instead of adding another lane, inspected the existing six-leg `2026-05` trades.
- The month had only two duplicated R186/R196 sweep signals:
  - `2026-05-01 06:48:39`, hour `6`, sweep buy, pnl `-0.1403` on each of R186/R196
  - `2026-05-01 07:31:51`, hour `7`, sweep buy, pnl `+3.6055` on each of R186/R196
- Hypothesis: reuse the existing high-balance sweep context guard to skip early-month hour `6` sweep in May, preserving the hour `7` winner and low-balance 2025-05 recovery.
- Implemented in schedule only:
  - `sweep_context_months: "3,5"`
  - added proxy drop filter `monthnum=5;signal=sweep;hour=0,1,6,23;min_start=100000;max_day=2`
  - no EA input change required
- Updated `portfolio_schedule_lint.py` so it accepts and validates multiple sweep context months derived from multiple proxy drop filters.
- New proxy:
  - output: `results/backtest/portfolio_r186_r196_r212_r211_r213_r216_guard_may_h6_20260525.md`
  - total `231278.42`
  - daily `7.04`
  - bad `0`
  - `2026-05`: `+7.21` no-cost
- New stress:
  - output: `results/backtest/portfolio_r186_r196_r212_r211_r213_r216_guard_may_h6_stress_20260525.md`
  - cost `0.50`: bad `0`, weakest `2026-05`, `+6.21`
  - cost `1.00`: bad `0`, weakest `2026-05`, `+5.21`
- New preflight:
  - command: `python scripts\portfolio_preflight_win.py --schedule r186_r196_r212_r211_r213_r216_guard --profile-name WaiTrade2_Portfolio_BTC_R212_R211_R213_R216_DryRun --guard-key-suffix dryrun_20260525 --output-prefix portfolio_r186_r196_r212_r211_r213_r216_guard_may_h6_preflight_20260525 --output results\backtest\portfolio_r186_r196_r212_r211_r213_r216_guard_may_h6_preflight_20260525.md`
  - result: pass
  - required cost pass: `1`
  - cost `1.00`: bad `0`, weakest `2026-05`, `+5.21`
- This is a cleaner improvement than R217/R218 because it reduces a known losing duplicate signal instead of adding duplicate same-family exposure.

Tooling note:
- `backtest_digest.py` hit `MemoryError` when reading the very large current Tester log without `--log-tail-mb`.
- Fixed `read_text_auto_tail()` so a whole-file `MemoryError` automatically falls back to tail reading (`64MB`) instead of aborting.
- Added regression coverage in `tests/test_mt5_common.py`.

Preflight gate hardening:
- Added schedule-level support for `preflight.require_cost_pass` in `scripts/portfolio_preflight_win.py`.
- Set current best schedule `r186_r196_r212_r211_r213_r216_guard` to require `1.0`.
- New preflight without an explicit CLI override:
  - command: `python scripts\portfolio_preflight_win.py --schedule r186_r196_r212_r211_r213_r216_guard --profile-name WaiTrade2_Portfolio_BTC_R212_R211_R213_R216_DryRun --guard-key-suffix dryrun_20260525 --output-prefix portfolio_r186_r196_r212_r211_r213_r216_guard_preflight_cost100_20260525 --output results\backtest\portfolio_r186_r196_r212_r211_r213_r216_guard_preflight_cost100_20260525.md`
  - result: pass
  - report explicitly shows `required_cost_pass=1`
  - cost `1.00`: bad `0`, weakest `2026-05 +2.93`
- Added regression coverage in `tests/test_portfolio_preflight_win.py`.

R55/R219 deployable context-filter check:
- Low-overlap CSV scan suggested the R55 family might be a useful independent add-on, but the proxy depended on source-level/month-hour guards that were not all deployable in the EA.
- Added three generic context-filter slots to the EA/YAML mapping so a strategy can filter by month, hour, direction, and month-start balance without hardcoding a specific version.
- Added `v11_r219_j2_r55_context_probe` as the deployable R55-family probe:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r219_j2_r55_context_probe --symbol BTCUSDm --from 2024.06.04 --to 2026.05.25 --timeout 1800`
  - result: `3837` trades, daily `5.3`, win `42.3%`, PF `1.31`, final balance `$34771.78`
  - digest: `results/backtest/v11_r219_j2_r55_context_probe_20240604_20260525_20260525.md`
- Monthly attribution still had seven losing months:
  - `2024-10 -204.25`
  - `2024-12 -8.39`
  - `2025-01 -3.91`
  - `2025-05 -337.70`
  - `2026-01 -11740.26`
  - `2026-03 -7038.08`
  - `2026-05 -7949.16`
- Incremental portfolio scan against the current best six-leg schedule:
  - output: `results/backtest/portfolio_incremental_scan_r219_context_probe_20260525.md`
  - base: total `231278.42`, daily `7.04`, bad `0`, weakest `2026-05 +7.21`
  - with R219: total `266662.99`, daily `11.60`, bad `3`, weakest `2026-05 -7937.80`, overlap `0.53`
- Conclusion: reject R219 for now. The true MT5 result is profitable as a standalone probe but far below the `90000u` target, and adding it to the current best schedule breaks the no-losing-month constraint. The earlier R55 CSV proxy was too optimistic and should not be used as evidence for a portfolio add-on without a full MT5 validation path.

R61/R220/R221 high-balance screen:
- Directly adding the R61 family to the current six-leg proxy gives large upside but breaks three high-balance months:
  - total `288828.97`, daily `11.20`, bad `3`
  - bad months: `2026-01 -1463.05`, `2026-03 -5689.56`, `2026-05 -5484.49`
- Source attribution showed those three losses were mainly from the R61 leg itself.
- First deployable variant `v11_r220_j2_r61_context_probe`:
  - inherits `v11_r61_j2_g30_shallow_soft`
  - filters high-balance January buy hours `1,2,3,12,15,16,17,18,23`
  - filters high-balance March sell hours `0,1,8`
  - filters high-balance May buy hours `6,13,20,21,22` and sell hours `0,2,11,15,16,23`
  - full-window MT5 command: `python scripts\mt5_backtest_win.py --strategy v11_r220_j2_r61_context_probe --symbol BTCUSDm --from 2024.06.04 --to 2026.05.25 --timeout 1800`
  - result: `3442` trades, daily `4.8`, win `41.8%`, PF `1.33`, final balance `$57556.77`
- Important path-dependency finding:
  - In a standalone `$200` full-window run, the R61 account month-start balance never reaches `$100000`, so high-balance context filters do not trigger.
  - Therefore the normal `.trades.csv` incremental scan cannot validate this type of portfolio add-on; it only consumes the standalone path.
  - The user's proposed single-month high-balance screen is the right fast feedback loop for this case.
- R220 single-month high-balance screens:
  - `2026-01`, deposit `$226105.41`: final `$233148.48`, about `+7043.07`
  - `2026-03`, deposit `$282890.51`: final `$277255.01`, about `-5635.50`
  - `2026-05`, deposit `$319740.21`: final `$320746.48`, about `+1006.27`
  - Note: the first three single-month commands were accidentally launched in parallel and produced cache/INI contamination symptoms. Re-ran them serially; only the serial results above are accepted.
- March diagnosis from `results/backtest/v11_r220_j2_r61_context_probe_20260301_20260401_20260525.md`:
  - top drag shifted to high-balance OB buy hour `14/15`, plus smaller OB direction-hour pockets.
  - Created `v11_r221_j2_r61_context_march_probe` by keeping R220's January/May filters and replacing March with:
    - no-buy hours `4,8,14,15,16,17`
    - no-sell hours `0,1,5,6,8,9,14`
- R221 high-balance March screen:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r221_j2_r61_context_march_probe --symbol BTCUSDm --from 2026.03.01 --to 2026.04.01 --deposit 282890.51 --timeout 1200`
  - result: `252` trades, final `$299672.41`, about `+16781.90`
- R221 standalone 720d full-window:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r221_j2_r61_context_march_probe --symbol BTCUSDm --from 2024.06.04 --to 2026.05.25 --timeout 1800`
  - result: same as R220, final `$57556.77`, because high-balance filters do not trigger on the standalone path.
- Conclusion: R221 is not proven as a final portfolio leg, but it is the strongest live-like R61 branch so far under the user's single-month high-balance screen. Next validation needs a true portfolio/profile path that replays the R61 chart with the combined account balance, or a purpose-built runner that replays month-start balance into EA-compatible context filters. Do not accept `portfolio_incremental_scan` failure for R221 as final evidence because it cannot model this dependency.

Seven-leg R221 schedule candidate:
- Added schedule `r186_r196_r212_r211_r213_r216_r221_guard`.
- It extends the current six-leg schedule with:
  - `R221C = v11_r221_j2_r61_context_march_probe`
  - CSV path: `results/backtest/v11_r221_j2_r61_context_march_probe_20240604_20260525_20260525.trades.csv`
- Proxy/live alignment:
  - R221's real EA context filters depend on account month-start balance.
  - Added `src=R221C` proxy drop filters for the same January/March/May high-balance direction-hour filters.
  - Added lint coverage so a strategy-level `context_filter*_mult: 0.0` now requires a matching `src=<series>` proxy `drop_filter`.
- Proxy result:
  - command: `python scripts\portfolio_schedule_runner.py --schedule r186_r196_r212_r211_r213_r216_r221_guard --output results\backtest\portfolio_r186_r196_r212_r211_r213_r216_r221_guard_20260525.md`
  - total `322935.05`
  - final `323135.05`
  - daily `11.04`
  - bad months `0`
  - weakest no-cost month: `2024-11 +74.67`
  - `2026-03 +191.23`, thin but positive
- Stress result:
  - command: `python scripts\portfolio_schedule_stress.py --schedule r186_r196_r212_r211_r213_r216_r221_guard --costs 0,0.5,1.0 --output results\backtest\portfolio_r186_r196_r212_r211_r213_r216_r221_guard_stress_20260525.md`
  - cost `0.50`: bad `0`, weakest `2024-12 +68.63`
  - cost `1.00`: bad `0`, weakest `2024-09 +28.87`
- Preflight:
  - command: `python scripts\portfolio_preflight_win.py --schedule r186_r196_r212_r211_r213_r216_r221_guard --profile-name WaiTrade2_Portfolio_BTC_R221_DryRun --guard-key-suffix dryrun_20260525_r221 --output-prefix portfolio_r186_r196_r212_r211_r213_r216_r221_guard_preflight_20260525 --output results\backtest\portfolio_r186_r196_r212_r211_r213_r216_r221_guard_preflight_20260525.md --compile`
  - lint: pass
  - proxy: pass
  - stress cost `1.00`: pass
  - profile audit: pass
  - compile: pass
  - shared-return proxy: fail with `2` bad months (`2024-11`, `2025-05`)
- Profile audit:
  - output: `results/backtest/portfolio_r186_r196_r212_r211_r213_r216_r221_guard_context_profile_audit_20260525.md`
  - charts `7`
  - unique magics `7`
  - chart07/R221C shows all three context-filter slots:
    - January buy hours `1,2,3,12,15,16,17,18,23`
    - March buy hours `4,8,14,15,16,17`; sell hours `0,1,5,6,8,9,14`
    - May buy hours `6,13,20,21,22`; sell hours `0,2,11,15,16,23`
- Conclusion:
  - This is the strongest current candidate by path-level proxy: it materially improves profit and frequency while preserving 0 bad months under fixed-cost stress.
  - It is not yet final because the shared-return proxy fails and because true multi-stream MT5 account replay is still missing. Treat it as the next dry-run/profile candidate, not as goal completion.

Shared-return diagnosis on seven-leg R221:
- The preflight shared-return proxy failed despite path proxy/stress passing.
- Baseline shared-return failures:
  - `2024-11 -33022.16`
  - `2025-05 -23256.96`
- Root cause in shared-return attribution:
  - `2024-11`: synchronized low-balance OB losses across R186/R212/R221C, especially OB buy hours `13/14/15`; the schedule's November OB guard was capped at month-start `25000`, while shared-return month-start was `39459.42`, so the guard did not fire.
  - `2025-05`: synchronized high-balance OB losses across R186/R212/R221C, especially buy `14`, sell `19`, buy `3`, and related pockets.
- Probe 1:
  - Temp config: `temp/portfolio_schedules_r221_probe.yaml`
  - Raised November OB guard cap to `65000`.
  - Added broader high-balance OB filters for March/May bad direction-hour pockets.
  - Result:
    - path proxy: total `323119.76`, daily `10.97`, bad `0`
    - shared-return proxy: bad `0`
    - stress `1.00`: bad `1`, `2026-03 -111.04`
  - Rejected: fixes shared-return but makes the path-level fixed-cost gate fail.
- Probe 2:
  - Temp config: `temp/portfolio_schedules_r221_probe2.yaml`
  - Raised November OB guard cap to `65000`.
  - Added only the most severe synchronized filters:
    - March buy `23`
    - May buy `14`
    - May sell `19`
  - Result:
    - path proxy: total `323126.17`, daily `11.00`, bad `0`
    - shared-return proxy: bad `0`
    - stress `1.00`: bad `1`, `2026-03 -106.82`
  - Rejected for now: still fails the fixed-cost gate.
- Additional March attribution:
  - Current official seven-leg schedule has `2026-03 +191.23` path proxy.
  - R216M is the main positive contributor (`+206.35`), while R221C is slightly negative (`-34.16`).
  - Most of the March cushion comes from a small number of R216M late-month OB trades, especially `2026-03-16 23:04:24` (`+170.30` proxy).
- Conclusion:
  - The shared-return model is useful as a severe stress lens but can push the optimization toward over-filtering and destroy the fixed-cost monthly cushion.
  - Do not apply the March/May broad OB filters to the official schedule yet.
  - The next productive direction is to add independent positive March margin, not just remove more March trades.

Low-overlap scan after R221:
- Command:
  - `python scripts\portfolio_incremental_scan.py --schedule r186_r196_r212_r211_r213_r216_r221_guard --candidate-glob "results/backtest/*.trades.csv" --top 40 --min-covered-months 20 --max-overlap 0.20 --output results\backtest\portfolio_incremental_scan_low_overlap_r221_guard_20260525.md`
- Findings:
  - Several old G-family candidates add small profit without breaking path-level monthly targets:
    - `v11_r35_j2_lg405_start2000_20240601_20260522_20260522.trades.csv`: pass, delta `+1788.55`, daily `+0.70`, weakest `2024-11 +84.60`
    - `v11_r58_j2_g30_swp_mid_001_20260523.trades.csv`: pass, delta `+1425.19`, daily `+1.01`
    - `v11_r57_j2_g30_add025_t15_20260523.trades.csv`: pass, delta `+1345.69`, daily `+1.01`
  - Larger G/R55/R61 candidates still fail mainly on `2026-03`, so the old "large upside but March poison" pattern remains.
- Conclusion:
  - Do not add these to the official schedule yet. They are old standalone CSV paths and need the same high-balance MT5 validation discipline used for R221.
  - Best next branch: validate `v11_r35_j2_lg405_start2000` as a deployable low-overlap micro add-on, with specific attention to high-balance `2026-03` and `2026-05` single-month screens before any full schedule change.

R35 high-balance validation:
- Candidate from low-overlap scan:
  - `v11_r35_j2_lg405_start2000_20240601_20260522_20260522.trades.csv`
  - proxy add-on result against seven-leg R221 schedule: pass, delta `+1788.55`, daily `+0.70`
- High-balance March screen:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r35_j2_lg405_start2000 --symbol BTCUSDm --from 2026.03.01 --to 2026.04.01 --deposit 283058.32 --timeout 1200`
  - result: `348` trades, final `$274508.43`, about `-8549.89`
  - digest: `results/backtest/v11_r35_j2_lg405_start2000_20260301_20260401_20260525.md`
  - exported CSV: `results/backtest/v11_r35_j2_lg405_start2000_20260301_20260401_20260525.trades.csv`
  - top bad clusters:
    - OB buy hour `14`: `-8998.29`
    - OB sell hour `0`: `-3955.95`
    - OB buy hour `15`: `-3352.59`
    - OB sell hour `1/8` also bad
- High-balance May screen:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r35_j2_lg405_start2000 --symbol BTCUSDm --from 2026.05.01 --to 2026.06.01 --deposit 318971.66 --timeout 1200`
  - result: `194` trades, final `$310066.56`, about `-8905.10`
  - digest: `results/backtest/v11_r35_j2_lg405_start2000_20260501_20260601_20260525.md`
  - note: digest did not match detailed trade logs for May, so only aggregate evidence is available, but the aggregate loss is already sufficient.
- Conclusion:
  - Reject R35 as an add-on to the current seven-leg schedule.
  - The old low-overlap CSV proxy overstates its usefulness under current high-balance account conditions.
  - Its March failure repeats the same high-balance OB damage pattern seen in R61/R220 rather than adding an independent clean edge.

R58 high-balance validation:
- Candidate from low-overlap scan:
  - `v11_r58_j2_g30_swp_mid_001_20260523.trades.csv`
  - proxy add-on result against seven-leg R221 schedule: pass, delta `+1425.19`, daily `+1.01`
- Current seven-leg month-start deposits used for the screen:
  - `2026-03`: `$283058.32`
  - `2026-05`: `$318971.66`
- High-balance March screen:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r58_j2_g30_swp_mid_001 --symbol BTCUSDm --from 2026.03.01 --to 2026.04.01 --deposit 283058.32 --timeout 1200`
  - result: `348` trades, win `43.7%`, final `$274508.43`, about `-8549.89`
  - digest: `results/backtest/v11_r58_j2_g30_swp_mid_001_20260301_20260401_20260525.md`
  - exported CSV: `results/backtest/v11_r58_j2_g30_swp_mid_001_20260301_20260401_20260525.trades.csv`
  - top dollar-loss clusters from the exported CSV:
    - OB buy hour `14`: `-8998.29`
    - OB sell hour `0`: `-3955.95`
    - OB buy hour `15`: `-3352.59`
    - OB sell hour `5`: `-1801.44`
    - OB sell hour `1`: `-1630.89`
    - OB buy hour `4`: `-1535.13`
    - OB buy hour `8`: `-1443.87`
    - OB sell hour `8`: `-1360.62`
  - Note: the digest's R-bucket wording highlights `sig:sweep | hour:09 | risk:200-300 | cp:>-0.6 | exit:sl`, while the exported dollar proxy shows the largest absolute damage in OB direction-hour pockets. Treat this as two views of the same high-balance March failure, not as a clean independent edge.
- High-balance May screen:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r58_j2_g30_swp_mid_001 --symbol BTCUSDm --from 2026.05.01 --to 2026.06.01 --deposit 318971.66 --timeout 1200`
  - result: `194` trades, win `38.1%`, final `$310066.56`, about `-8905.10`
  - digest: `results/backtest/v11_r58_j2_g30_swp_mid_001_20260501_20260601_20260525.md`
  - exported CSV: `results/backtest/v11_r58_j2_g30_swp_mid_001_20260501_20260601_20260525.trades.csv`
  - note: digest did not match detailed trade logs for May, so only aggregate evidence is used; the aggregate monthly loss is already enough to reject it.
- Conclusion:
  - Reject R58 as an add-on to the current seven-leg schedule.
  - R58 behaves like R35 under current high-balance account conditions: the low-overlap path proxy is green, but the MT5 single-month screen exposes large March/May losses.
  - Deprioritize the neighboring G30 mid family (`R57/R58/G30` variants) unless a future candidate has a materially different filter set and first passes high-balance March/May screens.

R94 high-balance validation:
- Candidate from low-overlap scan:
  - `v11_r94_j2_r32_cap2k_swp2k_mloss10_20240602_20260523_20260523.trades.csv`
  - proxy add-on result against seven-leg R221 schedule: pass, delta `+772.42`, daily `+0.70`, overlap `0.05`
- High-balance March screen:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r94_j2_r32_cap2k_swp2k_mloss10 --symbol BTCUSDm --from 2026.03.01 --to 2026.04.01 --deposit 283058.32 --timeout 1200`
  - result: `348` trades, win `43.7%`, final `$274508.43`, about `-8549.89`
  - digest: `results/backtest/v11_r94_j2_r32_cap2k_swp2k_mloss10_20260301_20260401_20260525.md`
  - exported CSV: `results/backtest/v11_r94_j2_r32_cap2k_swp2k_mloss10_20260301_20260401_20260525.trades.csv`
  - digest top bad R cluster: sweep hour `09`, risk `200-300`, confirm position `>-0.6`, exit `sl`
  - exported dollar proxy top bad clusters:
    - OB buy hour `14`: about `-10355.85`
    - OB sell hour `0`: about `-3955.95`
    - OB buy hour `15`: about `-3352.59`
    - OB buy hour `8`: about `-2804.49`
- Tooling note:
  - Initial digest export matched an older same-day `V11-R35-S2000` segment because `find_matching_log_segment` selected by symbol/date/final balance only.
  - Fixed `scripts/mt5_common.py` so equal-balance candidate ties prefer the latest log segment, and added a regression test in `tests/test_mt5_common.py`.
  - Re-generated the R94 digest/CSV; comments now correctly show `WT V11-R94-C2S2ML10`.
- Conclusion:
  - Reject R94 as an add-on. It has the same high-balance March loss magnitude as R35/R58 despite a different standalone low-overlap proxy profile.
  - This reinforces the screening rule: for near-neighbor strategies, a single high-balance bad-month MT5 screen is a valid fast rejection gate, but it is not a valid acceptance proof.

R90 high-balance validation:
- Candidate from low-overlap scan:
  - `v11_r90_j2_r89_mloss10_20240602_20260523_20260523.trades.csv`
  - proxy add-on result against seven-leg R221 schedule: pass, delta `+800.00`, daily `+0.47`, overlap `0.08`
  - shape: R89/R61 OB-only path with monthly loss stop from startup at `10%`
- High-balance March screen:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r90_j2_r89_mloss10 --symbol BTCUSDm --from 2026.03.01 --to 2026.04.01 --deposit 283058.32 --timeout 1200`
  - result: `33` trades, win `36.4%`, final `$273321.53`, about `-9736.79`
  - digest: `results/backtest/v11_r90_j2_r89_mloss10_20260301_20260401_20260525.md`
  - exported CSV: `results/backtest/v11_r90_j2_r89_mloss10_20260301_20260401_20260525.trades.csv`
  - top bad R cluster: hour `14`, risk `400+`, exit `sl`
  - exported dollar proxy top bad clusters:
    - OB sell/buy hour `14`: about `-10355.85`
    - OB hour `8`: about `-4282.65`
    - OB hour `0`: about `-3955.95`
- Conclusion:
  - Reject R90 as an add-on. Low frequency and OB-only isolation did not protect the high-balance March path.
  - Do not spend a May screen on R90; the March rejection gate is already decisive.

R208 / R222 HTFPB November patch probe:
- Motivation:
  - After rejecting R35/R58/R94/R90, the next search shifted away from low-overlap G/OB neighbors and toward independent HTFPB candidates that add positive margin in weak months.
  - Low-overlap CSV screening showed `v11_r208_j2_r142_no010919` had small positive proxy contribution in `2026-03` and `2024-11`.
- R208 high-balance single-month checks:
  - `2026-03`, deposit `$283058.32`:
    - command: `python scripts\mt5_backtest_win.py --strategy v11_r208_j2_r142_no010919 --symbol BTCUSDm --from 2026.03.01 --to 2026.04.01 --deposit 283058.32 --timeout 1200`
    - result: `245` trades, final `$283068.47`, about `+10.15`
    - digest: `results/backtest/v11_r208_j2_r142_no010919_20260301_20260401_20260525.md`
  - `2024-11`, shared-return month-start deposit `$39459.42`:
    - command: `python scripts\mt5_backtest_win.py --strategy v11_r208_j2_r142_no010919 --symbol BTCUSDm --from 2024.11.01 --to 2024.12.01 --deposit 39459.42 --timeout 1200`
    - result: `203` trades, final `$39437.31`, about `-22.11`
    - digest: `results/backtest/v11_r208_j2_r142_no010919_20241101_20241201_20260525.md`
  - Conclusion: R208 does not have the high-balance blow-up seen in R35/R58/R94/R90, but its edge is too thin and it fails the actual `2024-11` repair target.
- R222 variant:
  - Added `v11_r222_j2_r208_nov_highbal_cut`, inheriting R208, limited to `entry_months: "11"`.
  - Added high-balance HTFPB bad-hour cut:
    - `bad_cluster_min_balance: 100000.0`
    - `bad_cluster1_hours: "5,6,8,11,15,16,18,22"`
    - `bad_cluster1_risk_min/max: 200.0/300.0`
    - `bad_cluster1_signal: "htfpb"`
  - Mapping check:
    - `python scripts\yaml_to_set.py v11_r222_j2_r208_nov_highbal_cut` confirmed `InpEntryMonths=11`, `InpBadClusterMinBalance=100000.0`, `InpBadCluster1Signal=htfpb`, `InpVersion=V11-R222-HTFNOVCUT`.
- R222 high-balance single-month checks:
  - `2024-11`, deposit `$39459.42`:
    - result: `571` trades, final `$39499.33`, about `+39.91`
    - digest: `results/backtest/v11_r222_j2_r208_nov_highbal_cut_20241101_20241201_20260525.md`
  - `2026-03`, deposit `$283058.32`:
    - result after adding `entry_months: "11"`: `0` trades, no March interference.
- R222 full 720d MT5:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r222_j2_r208_nov_highbal_cut --symbol BTCUSDm --days 720 --timeout 1200`
  - result: `553` trades, daily `0.8`, final `$308.55`
  - digest: `results/backtest/v11_r222_j2_r208_nov_highbal_cut_20240604_20260525_20260525.md`
  - monthly behavior: only `2024-11` and `2025-11`, both positive in standalone path.
- Portfolio proxy with temporary schedule:
  - temp config: `temp/portfolio_schedules_r222_probe.yaml`
  - path proxy:
    - file: `results/backtest/portfolio_proxy_r222_probe_20260525.md`
    - total `322998.89`, daily `11.56`, bad `0`, pass true
  - fixed-cost stress:
    - file: `results/backtest/portfolio_stress_r222_probe_20260525.md`
    - `0.50/entry`: bad `0`
    - `1.00/entry`: bad `1`, weakest `2024-11 -418.35`
  - shared-return proxy:
    - file: `results/backtest/portfolio_return_proxy_r222_probe_20260525.md`
    - bad `3`: `2024-11`, `2025-03`, `2025-05`; still fail
- Conclusion:
  - R222 is a useful signal probe, not a deployable add-on yet.
  - It proves the November HTFPB lane can be made positive, but the edge is too thin and too high-frequency; execution-cost stress eats the exact month it was meant to repair.
  - Do not add R222 to the official schedule yet. Next direction: find or derive a lower-frequency, higher-per-trade November patch, likely by filtering R222 toward its strongest HTFPB buckets instead of adding all 553 November trades.

R223 thick-hour November patch:
- Derivation:
  - R222 trade-bucket analysis showed the November profit was concentrated in fewer direction-hour pockets:
    - examples: `2025-11 hour15 sell`, `2025-11 hour16 sell`, `2025-11 hour5 sell`, `2024-11 hour20 buy`, `2024-11 hour12 buy`, `2024-11 hour10 buy`
  - Added `v11_r223_j2_r222_nov_thick_hours`, inheriting R222 and keeping the strategy November-only.
  - Direction-hour narrowing:
    - buy allowed roughly `0,10,11,12,20`
    - sell allowed roughly `3,5,8,10,12,15,16,21`
  - Mapping check confirmed `InpEntryMonths=11`, `InpNoBuyHours`, `InpNoSellHours`, `InpBadClusterMinBalance=100000.0`, `InpVersion=V11-R223-HTFNOVTHICK`.
- Full 720d MT5:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r223_j2_r222_nov_thick_hours --symbol BTCUSDm --days 720 --timeout 1200`
  - result: `271` trades, daily `0.4`, final `$311.11`, PF `1.51`
  - digest: `results/backtest/v11_r223_j2_r222_nov_thick_hours_20240604_20260525_20260525.md`
  - monthly behavior: only `2024-11` and `2025-11`, both positive.
- Portfolio proxy with temporary schedule:
  - temp config: `temp/portfolio_schedules_r223_probe.yaml`
  - path proxy:
    - file: `results/backtest/portfolio_proxy_r223_probe_20260525.md`
    - total `323004.67`, daily `11.28`, bad `0`, pass true
    - `2024-11` improved from `74.67` to `81.29`
  - fixed-cost stress:
    - file: `results/backtest/portfolio_stress_r223_probe_20260525.md`
    - `1.00/entry`: bad `0`, weakest `2024-09 +28.87`
  - shared-return proxy:
    - file: `results/backtest/portfolio_return_proxy_r223_probe_20260525.md`
    - still fails with bad `3`: `2024-11`, `2025-03`, `2025-05`
    - `2024-11` improves only modestly, still about `-31475.42`
- Conclusion:
  - R223 is a better November patch than R222: fewer trades, higher PF, and it restores `1.0/entry` cost robustness.
  - It is still not enough to solve the shared-return failure, so do not treat it as goal completion.
  - It can be kept as a candidate patch if later combined with a much stronger shared-return fix, but the next search must target larger independent positive contribution in `2024-11`, `2025-03`, and `2025-05`.

Shared-return bad-month repair:
- Baseline:
  - Official `r186_r196_r212_r211_r213_r216_r221_guard` path proxy and `1.0/entry` stress passed, but shared-return preflight failed.
  - Baseline shared-return bad months:
    - `2024-11 -33022.16`
    - `2025-05 -23256.96`
  - R222/R223 HTFPB patches only modestly improved November and did not fix shared-return.
- Diagnose findings:
  - A single-variable `max_start=65000` November guard probe preserved path/stress and reduced shared-return bad months from `3` to `2`, but did not solve November by itself.
  - Shared-return attribution showed:
    - `2024-11`: synchronized OB losses dominated by buy hours `15/13/14` and sell hours `22/13/7/18`.
    - `2025-05`: synchronized OB losses dominated by buy hours `14/3/2/1` and sell hours `19/15/7/2/4/21`.
  - After applying those November/May filters, shared-return had only one bad month:
    - `2025-03 -7539.70`
  - `2025-03` attribution showed the remaining damage was concentrated in exact dated high-balance OB pockets:
    - buy hours `16/23`
    - sell hours `6/18/23`
    - broad `monthnum=3` filtering was avoided because previous probes damaged the important `2026-03` path cushion.
- New schedule:
  - Added `r186_r196_r212_r211_r213_r216_r221_shared_fix` to `config/portfolio_schedules.yaml`.
  - It keeps the seven strategy legs unchanged and changes only schedule/profile filters:
    - November OB guard cap raised to `65000` and live profile override aligned.
    - May high-balance OB filters:
      - buy `1,2,3,14`
      - sell `2,4,7,15,19,21`
    - Exact `2025-03` high-balance OB filters:
      - buy `16,23`
      - sell `6,18,23`
    - Existing R221C context filters are preserved.
- Evidence:
  - Path proxy:
    - file: `results/backtest/portfolio_proxy_shared_fix_20260525.md`
    - total `323290.58`, final `323490.58`, daily `11.03`, bad `0`, pass true
  - Fixed-cost stress:
    - file: `results/backtest/portfolio_stress_shared_fix_20260525.md`
    - `1.00/entry`: bad `0`, weakest `2024-09 +28.87`
  - Shared-return proxy:
    - file: `results/backtest/portfolio_return_proxy_shared_fix_20260525.md`
    - daily `11.63`, bad `0`, pass true
  - Windows preflight:
    - file: `results/backtest/portfolio_r186_r196_r212_r211_r213_r216_r221_shared_fix_preflight_20260525.md`
    - lint pass, proxy pass, stress pass, shared-return pass, generated/installed profile audit pass, result pass
- Conclusion:
  - `r186_r196_r212_r211_r213_r216_r221_shared_fix` is now the strongest current candidate.
  - It clears the previous shared-return blocker while preserving path-level and `1.0/entry` cost robustness.
  - It is still not final goal completion because these are CSV path/return proxies plus profile preflight, not a true MT5 multi-stream account replay. Treat it as the next dry-run/deployment candidate.

Deployable-context conversion:
- Concern:
  - `shared_fix` passed proxy/preflight, but several key repairs were schedule-only `drop_filters`.
  - The profile audit did not show those filters as EA inputs, so it was too easy to overstate it as a live-aligned solution.
- Probes:
  - `shared_fix_monthnum3_probe` generalized exact `2025-03` filters to all March:
    - path/shared-return passed, but `1.0/entry` stress failed with `2026-03 -123.77`.
    - cause: broad March filtering removed R216M's later positive March OB recovery.
  - `shared_fix_march_src_probe` kept the March repair on synchronized OB legs only and preserved R216M:
    - path proxy `323290.58`, daily `11.03`, bad `0`.
    - `1.0/entry` stress bad `0`.
    - shared-return bad `0`.
  - `shared_fix_context_equiv_probe` removed signal-type dependence to approximate deployable context filters:
    - path proxy `323286.01`, daily `11.03`, bad `0`.
    - `1.0/entry` stress bad `0`.
    - shared-return bad `0`.
  - `deployable_context_probe` converted the repair into per-stream context-style filters:
    - path proxy `323300.38`, daily `10.97`, bad `0`.
    - `1.0/entry` stress bad `0`, weakest `2024-09 +28.87`.
    - shared-return bad `0`.
- New strategy versions:
  - Added `v11_r224_j2_r186_ctx35`:
    - March high-balance context: buy `16,23`, sell `6,18,23`, min start `100000`.
    - May high-balance context: buy `1,2,3,14`, sell `2,4,7,15,19,21`, min start `50000`.
  - Added `v11_r225_j2_r196_ctx35` with the same March/May context filters.
  - Added `v11_r226_j2_r212_ctx3` with March high-balance context only; May remains handled by R212 high-balance no-entry.
  - Added `v11_r227_j2_r221_ctx35_merge`, merging shared-return March/May repair pockets into the existing R221C context filters.
- New schedule:
  - Added `r224_r225_r226_r211_r213_r216_r227_deployable_context`.
  - This is now the preferred candidate over `shared_fix` because the major repair filters are visible in generated MT5 profile inputs.
- Evidence:
  - Path proxy:
    - file: `results/backtest/portfolio_proxy_deployable_context_20260525.md`
    - total `323341.10`, final `323541.10`, daily `10.97`, bad `0`, pass true.
  - Fixed-cost stress:
    - file: `results/backtest/portfolio_stress_deployable_context_20260525.md`
    - `1.00/entry`: bad `0`, weakest `2024-09 +28.87`.
  - Shared-return proxy:
    - file: `results/backtest/portfolio_return_proxy_deployable_context_20260525.md`
    - daily `11.56`, bad `0`, pass true.
  - Windows preflight:
    - file: `results/backtest/portfolio_r224_r225_r226_r211_r213_r216_r227_deployable_context_preflight_20260525.md`
    - lint pass, proxy pass, stress pass, shared-return pass, generated/installed profile audit pass.
  - Profile audit:
    - generated: `results/backtest/portfolio_r224_r225_r226_r211_r213_r216_r227_deployable_context_preflight_20260525_generated_profile_audit.md`
    - installed: `results/backtest/portfolio_r224_r225_r226_r211_r213_r216_r227_deployable_context_preflight_20260525_installed_profile_audit.md`
    - 7 charts, 7 versions, 7 unique magic numbers, one shared key.
    - R224/R225/R226/R227 context filters are visible in chart inputs.
- Conclusion:
  - Preferred current candidate is now `r224_r225_r226_r211_r213_r216_r227_deployable_context`.
  - It is more live-aligned than `shared_fix` because the repair moved from proxy-only date/signal filters into deployable EA context inputs.
  - Still not final goal completion: there is no true MT5 multi-stream account-level Strategy Tester replay yet, only per-strategy MT5 CSVs plus account-level proxy/preflight.

2026-05-25 real-MT5 deployable-context validation:
- 目的:
  - 用真实 MT5 Strategy Tester CLI 720 天单腿回测补证 `deployable_context`，避免只依赖旧 CSV + schedule drop_filter 代理。
  - 将 R224/R225/R226/R227 的 schedule path 切到新生成的真实 MT5 trades CSV 后，重新跑组合代理、成本压力、共享收益代理和 Windows preflight。
- 单腿真实 MT5 结果:
  - `v11_r224_j2_r186_ctx35`:
    - trades `2287`, daily `3.2`, WR `43.6%`, PF `1.58`, final balance `$96941.72`.
    - digest: `results/backtest/v11_r224_j2_r186_ctx35_20240604_20260525_20260525.md`.
    - csv: `results/backtest/v11_r224_j2_r186_ctx35_20240604_20260525_20260525.trades.csv`.
  - `v11_r225_j2_r196_ctx35`:
    - trades `1576`, daily `2.2`, WR `41.8%`, PF `1.99`, final balance `$90264.98`.
    - digest: `results/backtest/v11_r225_j2_r196_ctx35_20240604_20260525_20260525.md`.
    - csv: `results/backtest/v11_r225_j2_r196_ctx35_20240604_20260525_20260525.trades.csv`.
  - `v11_r226_j2_r212_ctx3`:
    - trades `2031`, daily `2.8`, WR `43.0%`, PF `1.26`, final balance `$42320.57`.
    - digest: `results/backtest/v11_r226_j2_r212_ctx3_20240604_20260525_20260525.md`.
    - csv: `results/backtest/v11_r226_j2_r212_ctx3_20240604_20260525_20260525.trades.csv`.
  - `v11_r227_j2_r221_ctx35_merge`:
    - trades `3354`, daily `4.7`, WR `42.1%`, PF `1.41`, final balance `$66013.38`.
    - digest: `results/backtest/v11_r227_j2_r221_ctx35_merge_20240604_20260525_20260525.md`.
    - csv: `results/backtest/v11_r227_j2_r221_ctx35_merge_20240604_20260525_20260525.trades.csv`.
- 真实 CSV 组合代理:
  - Schedule: `r224_r225_r226_r211_r213_r216_r227_deployable_context`.
  - Path proxy:
    - file: `results/backtest/portfolio_proxy_deployable_context_realcsv_20260525.md`.
    - total `321956.95`, final `322156.95`, daily `10.98`, bad months `0`, pass true.
    - weakest visible months are still positive: `2024-11 +74.67`, `2024-12 +127.13`, `2026-03 +186.67`.
  - Fixed-cost stress:
    - file: `results/backtest/portfolio_stress_deployable_context_realcsv_20260525.md`.
    - `1.00/entry`: total `314095.88`, daily `11.00`, bad months `0`, weakest `2024-09 +28.87`.
  - Shared-return proxy:
    - file: `results/backtest/portfolio_return_proxy_deployable_context_realcsv_20260525.md`.
    - daily `11.57`, bad months `0`, pass true.
    - 注意: shared-return 复利放大极端，不作为真实收益估计，只作为共享余额路径方向检查。
- Windows preflight:
  - file: `results/backtest/portfolio_r224_r225_r226_r211_r213_r216_r227_deployable_context_realcsv_preflight_20260525.md`.
  - lint pass, proxy pass, stress pass, shared-return pass, generated/installed profile audit pass, result pass.
  - generated audit: `results/backtest/portfolio_r224_r225_r226_r211_r213_r216_r227_deployable_context_realcsv_preflight_20260525_generated_profile_audit.md`.
  - installed audit: `results/backtest/portfolio_r224_r225_r226_r211_r213_r216_r227_deployable_context_realcsv_preflight_20260525_installed_profile_audit.md`.
- Regression:
  - `python -m pytest tests\test_mt5_common.py tests\test_portfolio_schedule_lint.py tests\test_mt5_portfolio_profile_audit.py tests\test_portfolio_preflight_win.py tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_stress.py tests\test_portfolio_return_sim.py tests\test_portfolio_schedule_attribution.py tests\test_portfolio_incremental_scan.py tests\test_single_month_screen.py -q`
  - result: `108 passed in 9.58s`.
- Deploy-only compile validation:
  - command: `python scripts\mt5_portfolio_deploy_win.py --schedule r224_r225_r226_r211_r213_r216_r227_deployable_context --profile-name WaiTrade2_Portfolio_BTC_R227_DeployableContext --guard-key-suffix 20260525_realcsv --compile`.
  - result: generated and installed profile successfully, `not_started=true`.
  - MetaEditor logs:
    - `temp/compile_win/WaiTrade_OB.compile.log`: `Result: 0 errors, 0 warnings`.
    - `temp/compile_win/ClearSharedMonthlyGuard.compile.log`: `Result: 0 errors, 0 warnings`.
  - installed audit after compile:
    - file: `results/backtest/portfolio_r224_deployable_context_installed_after_compile_audit_20260525.md`.
    - result: 7 charts, 7 versions, 7 unique magic numbers, shared key `r224_r225_r226_r211_r213_r216_r227_deployable_context_20260525_realcsv`, pass true.
- Single-month speed-up assessment:
  - The repo already has `scripts/single_month_screen.py` for this exact workflow: read full-window trades/report, reconstruct month-start balances, and generate single-month MT5 commands with `--deposit` set to the historical month-start balance.
  - This is useful to reject similar variants quickly on known bad months such as `2024-11`, `2025-03`, `2025-05`, `2026-03`.
  - It is not a replacement for the fixed 720-day Real Ticks backtest because long-window path effects still matter: earlier/later months affect shared balance, guard state, profit-target stops, cooldown/concurrency exposure, and which trades exist after context filters.
  - Recommended workflow:
    - Use single-month screens as a fast negative filter.
    - Promote only variants that fix the bad month without damaging the known cushions.
    - Confirm with full-window 720-day MT5, then account-level proxy/preflight/profile audit.
- Extra regression after deploy script fix:
  - Fixed `scripts/mt5_portfolio_deploy_win.py` missing `subprocess` import in the `--start` path.
  - Added a narrow mock test for `start_terminal(..., "/profile:...")`.
  - `python -m pytest tests\test_mt5_common.py tests\test_mt5_compile_win.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_portfolio_schedule_lint.py tests\test_mt5_portfolio_profile_audit.py tests\test_portfolio_preflight_win.py tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_stress.py tests\test_portfolio_return_sim.py tests\test_portfolio_schedule_attribution.py tests\test_portfolio_incremental_scan.py tests\test_single_month_screen.py -q`
  - result: `114 passed in 10.25s`.
- 结论:
  - `r224_r225_r226_r211_r213_r216_r227_deployable_context` 继续是当前表现最好的方案。
  - 它满足当前代理层目标: 日均开单 `>4`, 总利润 `>90000`, 每月正收益，并通过每单 `$1.00` 固定额外成本压力。
  - 证据质量高于 `shared_fix`: 关键修复已进入 EA context inputs，且四条新增腿有真实 MT5 720 天单腿 CSV。
  - Deploy-only + compile 进一步证明它可以落入 Windows MT5 目录并通过 MetaEditor 编译，但仍未启动 MT5，未产生真实多图表执行日志。
  - 仍不能宣布最终完成: 组合层仍是 CSV path/account proxy + profile preflight/deploy-only compile，不是真正 MT5 多流账户级 Strategy Tester 回放。下一步应优先做真实多图表共享账户 dry-run/回放审计，或者补一个能从 MT5 多图表日志重建共享余额与过滤触发的验证环。

R228 dual monthly-profit-target probe:
- Motivation:
  - R227/R224 deployable-context already passes path/stress/shared-return, but `1.00/entry` stress weakest month was thin:
    - previous `1.00/entry` weakest: `2024-09 +28.87`.
  - Attribution showed `2024-09` had `158` executed trades and a large early profit peak that later got mostly given back.
- Rejected broad September stop:
  - Probe: add monthnum `9` to the existing `3%` profit target stop with `max_start=65000`.
  - Result: `2024-09` improved, but `2025-09` was cut off during the main profitable expansion.
  - Path proxy fell to about `125395.47`, and `2026-01` / `2026-03` became negative because the later balance path was damaged.
  - Conclusion: broad September stop is too blunt.
- Useful narrow shape:
  - Probe: add a September-only low-balance profit target:
    - monthnum `9`
    - max month-start balance `5000`
    - target `3%`
  - Path proxy:
    - total `321952.72`, daily `10.79`, bad `0`.
    - `2024-09` changes from `158` trades / `+186.87` to `21` trades / `+182.64`.
    - `2025-09` remains untouched because its month-start balance is above `5000`.
  - Cost stress:
    - `1.00/entry`: bad `0`, weakest improves to `2026-03 +58.67`.
    - This is materially stronger than the previous weakest `2024-09 +28.87`.
  - Shared-return proxy:
    - bad `0`, pass true.
- Implementation:
  - Added a second optional monthly profit-target slot to keep proxy and live/profile behavior aligned:
    - `InpMonthlyProfitTargetStop2Pct`
    - `InpMonthlyProfitTargetStop2MinBalance`
    - `InpMonthlyProfitTargetStop2MaxBalance`
    - `InpMonthlyProfitTargetStop2Months`
  - First slot remains unchanged and takes priority when both slots match.
  - Defaults are disabled (`0/empty`), so existing strategies keep old behavior.
  - Updated:
    - `mql5/Include/WaiTrade2/Config.mqh`
    - `mql5/Include/WaiTrade2/SignalEngine.mqh`
    - `scripts/yaml_to_set.py`
    - `scripts/portfolio_path_sim.py`
    - `scripts/portfolio_schedule_runner.py`
    - `scripts/portfolio_schedule_lint.py`
    - `config/strategies.yaml`
    - `config/portfolio_schedules.yaml`
  - Official schedule now keeps:
    - slot1: months `3,4,5,10,11,12`, max start `65000`, target `3%`.
    - slot2: month `9`, max start `5000`, target `3%`.
- Evidence:
  - Unit/regression tests:
    - `python -m pytest tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_lint.py tests\test_mt5_common.py -q`
    - result: `89 passed`.
  - Full related suite:
    - `python -m pytest tests\test_mt5_common.py tests\test_mt5_compile_win.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_portfolio_schedule_lint.py tests\test_mt5_portfolio_profile_audit.py tests\test_portfolio_preflight_win.py tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_stress.py tests\test_portfolio_return_sim.py tests\test_portfolio_schedule_attribution.py tests\test_portfolio_incremental_scan.py tests\test_single_month_screen.py -q`
    - result: `117 passed`.
  - Path proxy:
    - file: `results/backtest/portfolio_proxy_r228_dual_profit_target_20260525.md`.
    - total `321952.72`, daily `10.79`, bad `0`, pass true.
  - Fixed-cost stress:
    - file: `results/backtest/portfolio_stress_r228_dual_profit_target_20260525.md`.
    - `1.00/entry`: total `314228.66`, daily `10.81`, bad `0`, weakest `2026-03 +58.67`.
  - Shared-return proxy:
    - file: `results/backtest/portfolio_return_r228_dual_profit_target_20260525.md`.
    - daily `11.57`, bad `0`, pass true.
  - Windows preflight:
    - file: `results/backtest/portfolio_r228_dual_profit_target_preflight_20260525.md`.
    - lint pass, proxy pass, stress pass, shared-return pass, generated/installed profile audit pass, result pass.
  - Installed profile direct input check:
    - `InpMonthlyProfitTargetStop2Pct=3.0`
    - `InpMonthlyProfitTargetStop2MinBalance=0.0`
    - `InpMonthlyProfitTargetStop2MaxBalance=5000.0`
    - `InpMonthlyProfitTargetStop2Months=9`
  - MetaEditor compile:
    - `WaiTrade_OB.mq5`: `0 errors, 0 warnings`.
    - `ClearSharedMonthlyGuard.mq5`: `0 errors, 0 warnings`.
- Conclusion:
  - R228 is now preferred over the prior deployable-context schedule because it preserves the same target pass while improving fixed-cost weakest-month cushion.
  - This is still not final goal completion because the combination proof remains CSV proxy/preflight/profile compile, not true MT5 multi-stream account-level execution replay.

R228 single-leg MT5 validation:
- Purpose:
  - Prove the new second monthly profit-target slot is executed by the real MT5 EA, not only by the CSV proxy/profile generator.
  - Use the exact target month: `2024-09`, with the portfolio month-start balance `2197.11`.
- Added validation strategy:
  - `v11_r228_j2_r224_sep_pt2`
  - inherits `v11_r224_j2_r186_ctx35`
  - only adds:
    - `monthly_profit_target_stop2_pct: 3.0`
    - `monthly_profit_target_stop2_min_balance: 0.0`
    - `monthly_profit_target_stop2_max_balance: 5000.0`
    - `monthly_profit_target_stop2_months: "9"`
    - `magic_number: 204387`
  - `yaml_to_set.py` check confirmed:
    - `InpMonthlyProfitTargetStop2Pct=3.0`
    - `InpMonthlyProfitTargetStop2MaxBalance=5000.0`
    - `InpMonthlyProfitTargetStop2Months=9`
- Real MT5 single-month A/B:
  - Baseline command:
    - `python scripts\mt5_backtest_win.py --strategy v11_r224_j2_r186_ctx35 --symbol BTCUSDm --from 2024.09.01 --to 2024.10.01 --deposit 2197.11 --timeout 1200`
  - Baseline result:
    - `31` trades, win `35.5%`, PF `0.44`, final balance `$-1311.24`.
    - digest: `results/backtest/v11_r224_j2_r186_ctx35_20240901_20241001_20260525.md`
    - csv: `results/backtest/v11_r224_j2_r186_ctx35_20240901_20241001_20260525.trades.csv`
  - R228 validation command:
    - `python scripts\mt5_backtest_win.py --strategy v11_r228_j2_r224_sep_pt2 --symbol BTCUSDm --from 2024.09.01 --to 2024.10.01 --deposit 2197.11 --timeout 1200`
  - R228 validation result:
    - `7` trades, win `42.9%`, PF `12.69`, final balance `$3997.31`.
    - digest: `results/backtest/v11_r228_j2_r224_sep_pt2_20240901_20241001_20260525.md`
    - csv: `results/backtest/v11_r228_j2_r224_sep_pt2_20240901_20241001_20260525.trades.csv`
  - R228 last executed trade:
    - `2024-09-04 00:48:45`, OB sell, `+1883.33` proxy PnL.
    - After this trade, profit exceeds `3%` of the `2197.11` month-start balance, so the second profit-target slot should block later entries.
- Conclusion:
  - The second monthly profit-target slot is live in the real MT5 EA path.
  - The single-leg MT5 A/B confirms the exact intended behavior: low-balance September gives back far less by stopping after early profit.
  - This strengthens R228 beyond proxy/profile evidence, but still does not prove true multi-stream account-level behavior across all seven charts.

R228 full-window rejection:
- Why this was needed:
  - The single-month screen proved the mechanism, but it did not prove full-window path safety.
  - Because MT5 position sizing and later trades depend on the account path, accepting R228 from a single 2024-09 screen would violate the project rule that fast screens are rejection gates, not acceptance proof.
- Full 720d MT5:
  - command: `python scripts\mt5_backtest_win.py --strategy v11_r228_j2_r224_sep_pt2 --symbol BTCUSDm --days 720 --timeout 1200`
  - result: `2617` trades, daily `3.6`, WR `41.8%`, PF `1.49`, final balance `$52400.21`.
  - digest: `results/backtest/v11_r228_j2_r224_sep_pt2_20240604_20260525_20260525.md`
  - csv: `results/backtest/v11_r228_j2_r224_sep_pt2_20240604_20260525_20260525.trades.csv`
- Full-window side effect:
  - Compared with R224, R228 improves the early 2024-09 pocket:
    - R224 2024-09: `46` trades, about `+0.89` proxy PnL in its own standalone CSV.
    - R228 2024-09: `6` trades, about `+225.62` proxy PnL.
  - But the changed balance path materially reshapes later months:
    - R228 standalone has `10` losing months.
    - final `$52400.21` is much lower than R224's `$96941.72`.
    - large negative deltas appear in `2025-11`, `2026-01`, `2026-02`, `2026-03`, and `2026-05`.
- Portfolio real-leg probe:
  - Temporary schedule: `temp/portfolio_schedules_r228_realleg_probe.yaml`.
  - Change: replace only R224 path/strategy with the real R228 720d CSV.
  - Path proxy result:
    - file: `results/backtest/portfolio_proxy_r228_realleg_probe_20260525.md`.
    - total `277527.09`, daily `11.10`, bad `2`, fail.
    - bad months: `2026-03 -3285.01`, `2026-05 -1608.90`.
  - Fixed-cost stress:
    - file: `results/backtest/portfolio_stress_r228_realleg_probe_20260525.md`.
    - already bad at zero extra cost; `1.00/entry` keeps `2` bad months.
  - Shared-return proxy:
    - file: `results/backtest/portfolio_return_r228_realleg_probe_20260525.md`.
    - bad `1`, `2026-05`, fail.
- Decision:
  - Reject R228 as a replacement for the R224 leg.
  - Reverted the official `r224_r225_r226_r211_r213_r216_r227_deployable_context` schedule back to the prior deployable-context guard set, without the second profit-target slot.
  - Keep the second profit-target slot implementation and `v11_r228_j2_r224_sep_pt2` as validated tooling/candidate research, but do not use it in the current best portfolio.
- Current best after rejection:
  - Official schedule: `r224_r225_r226_r211_r213_r216_r227_deployable_context`.
  - Recheck path proxy:
    - file: `results/backtest/portfolio_proxy_deployable_context_after_r228_reject_20260525.md`.
    - total `321956.95`, daily `10.98`, bad `0`, pass true.
  - Recheck stress:
    - file: `results/backtest/portfolio_stress_deployable_context_after_r228_reject_20260525.md`.
    - `1.00/entry`: bad `0`, weakest `2024-09 +28.87`.
  - Recheck shared-return:
    - file: `results/backtest/portfolio_return_deployable_context_after_r228_reject_20260525.md`.
    - daily `11.57`, bad `0`, pass true.
- Lesson:
  - The user's proposed single-month month-start-balance screen is excellent for fast rejection and mechanism validation.
  - It is not sufficient for acceptance when the change affects the full-window balance path. Full 720d MT5 plus real CSV replacement in the portfolio proxy remains mandatory.

## 2026-05-25 continuation: deployable-context weak-month check

User question assessed:
- Using the previous full-window month-start balance as the deposit for a single bad-month MT5 run can reduce iteration time.
- Current answer: yes, it is a strong fast-rejection and mechanism-validation workflow.
- Acceptance rule remains unchanged: a candidate that passes the single-month screen still needs full fixed-window 720d MT5 Real Ticks, real CSV replacement in the portfolio proxy, stress, shared-return proxy, and profile/preflight audit.

Validated helper:
- `scripts/single_month_screen.py` generates commands with the reconstructed month-start balance.
- Example against R224/R228 September:
  - source CSV: `results/backtest/v11_r224_j2_r186_ctx35_20240604_20260525_20260525.trades.csv`
  - report: `results/backtest/v11_r224_j2_r186_ctx35_20240604_20260525_20260525.txt`
  - generated command uses `--from 2024.09.01 --to 2024.10.01 --deposit 692.77`
- Test:
  - `python -m pytest tests\test_single_month_screen.py -q`
  - result: `5 passed`.

Current best remains:
- Official schedule: `r224_r225_r226_r211_r213_r216_r227_deployable_context`.
- Latest preflight: `results/backtest/portfolio_deployable_context_after_r228_reject_preflight_20260525.md`.
- Metrics: total `321956.95`, daily `10.98`, bad months `0`, stress `1.00/entry` bad months `0`, weakest `2024-09 +28.87`.

Weak-month attribution:
- Files:
  - `results/backtest/portfolio_deployable_context_weak_month_attribution_20260525.md`
  - `results/backtest/portfolio_deployable_context_weak_month_attribution_cost1_20260525.md`
- No-cost weakest: `2024-11 +74.67`.
- Cost `1.00/entry` weakest: `2024-09 +28.87`.
- Diagnosis:
  - `2024-09` cost sensitivity is mostly many correlated small executions across R224/R226/R227, not one obvious missing filter.
  - `2024-11` is currently held up by low-balance OB bad-hour filtering plus the shared 3% monthly profit target stop.

Low-overlap add-on scan:
- File: `results/backtest/portfolio_incremental_scan_low_overlap_deployable_context_20260525.md`.
- Best passing add-ons are small:
  - R35 start2000: delta `+1788.55`, daily delta `+0.70`, bad `0`.
  - R58/R57 family: delta about `+1250` to `+1384`, daily delta about `+1.01`, bad `0`.
- Large-delta R55/R61/shallow family still fails by reintroducing `2026-03` or `2026-05` bad months.
- Conclusion:
  - Do not add a new leg from this scan yet. The passing candidates are only marginal proxy improvements, while the high-upside candidates still need a deployable real MT5 variant with bad-month controls.
  - Near-term priority is evidence hardening: shared monthly guard log audit / true multi-chart same-account behavior, not another broad portfolio add-on.

## 2026-05-25 continuation: shared guard OnInit audit hardening

Diagnose loop:
- Reproduced current best with `portfolio_preflight_win.py`.
- Reproduced evidence gap with `shared_guard_log_audit.py`:
  - existing terminal/tester logs had `events=0`, `pass=false`.
  - profile audit proved inputs were installed, but not that the shared monthly guard state was initialized by all charts.
- Ranked hypotheses:
  1. The largest remaining blocker is not path-profit but missing real multi-chart shared-guard runtime evidence.
  2. `SHARED_GUARD` events are too late because shared monthly state initializes only when later entry/monthly guard code calls `SyncMonthlyRiskState()`.
  3. Adding another low-overlap leg is lower priority because recent R35/R58/R55/R61 lines either failed high-balance screens or added only marginal proxy profit.

Implementation:
- Updated `mql5/Experts/WaiTrade2/WaiTrade_OB.mq5`:
  - call `SyncMonthlyRiskState()` inside `OnInit()` after `SymbolSelect(_Symbol, true)`.
  - Purpose: when `InpSharedMonthlyGuard=true` and debug is on, each chart should emit `SHARED_GUARD init/load` as soon as the EA loads.
  - This does not change entry filters or send orders by itself; it initializes/audits shared monthly state earlier.
- Added `tests/test_shared_guard_log_audit.py::test_shared_guard_log_audit_accepts_oninit_only_events`.
  - The audit accepts a profile-load-only evidence pattern: one `init` plus `load` events from the other versions.

Validation:
- Unit/tool tests:
  - `python -m pytest tests\test_shared_guard_log_audit.py tests\test_mt5_compile_win.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_profile_audit.py -q`
  - result: `10 passed`.
- MetaEditor compile:
  - `python scripts\mt5_compile_win.py`
  - `WaiTrade_OB.mq5`: `0 errors`, `0 warnings`.
  - `ClearSharedMonthlyGuard.mq5`: `0 errors`, `0 warnings`.
- Full relevant regression:
  - `python -m pytest tests\test_mt5_common.py tests\test_portfolio_schedule_lint.py tests\test_portfolio_preflight_win.py tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_stress.py tests\test_portfolio_return_sim.py tests\test_portfolio_schedule_attribution.py tests\test_portfolio_incremental_scan.py tests\test_single_month_screen.py tests\test_shared_guard_log_audit.py -q`
  - result: `112 passed`.
- Windows preflight with compile:
  - file: `results/backtest/portfolio_deployable_context_oninit_guard_preflight_20260525.md`
  - proxy total `321956.95`, daily `10.98`, bad `0`, pass.
  - `1.00/entry` stress: bad `0`, weakest `2024-09 +28.87`.
  - shared-return proxy: daily `11.57`, bad `0`, pass.
  - generated/installed profile audit: pass.
  - compile: pass.

Conclusion:
- Current best remains `r224_r225_r226_r211_r213_r216_r227_deployable_context`.
- This turn improves final-evidence readiness: a real multi-chart profile start should now produce `SHARED_GUARD init/load` events immediately, making `scripts/shared_guard_log_audit.py` usable for the missing runtime proof.
- Still not final goal completion:
  - We have not started a true MT5 multi-chart session and captured the new runtime logs.
  - We still lack a true MT5 multi-stream same-account replay; current account-level validation remains proxy/preflight plus profile audit.

No-entry guard-audit profile prepared:
- Temp schedule: `temp/portfolio_schedules_guard_audit_noentry.yaml`.
- Generated profile: `temp/portfolio_profiles_guard_audit/r224_r225_r226_r211_r213_r216_r227_deployable_context`.
- Override:
  - each stream has `entry_months: "13"` so the profile should not open trades in real calendar months.
  - shared guard key suffix: `oninit_audit_20260525`.
- Audit:
  - file: `results/backtest/portfolio_guard_audit_noentry_profile_audit_20260525.md`
  - 7 charts, 7 versions, 7 unique magic numbers, one shared key, pass true.
- Spot input check:
  - chart01/chart02/chart07 contain `InpSharedMonthlyGuard=true`, `InpSharedMonthlyGuardDebug=true`, and `InpEntryMonths=13`.
- Not started:
  - The MT5 terminal was not started automatically.
  - Next manual/approved step: start this no-entry profile, wait for chart load, then run `scripts/shared_guard_log_audit.py` against the new terminal logs and expect one `init` plus six `load` events for the shared key.

## 2026-05-25 continuation: no-entry audit profile tooling

Problem:
- The first no-entry guard-audit profile was generated by copying/editing a temporary schedule.
- That was useful once, but not repeatable enough for final verification.

Implementation:
- Added `--no-entry-month` support to `scripts/mt5_portfolio_live_profile.py`.
  - It overrides every stream with `InpEntryMonths=N`.
  - It records `no_entry_month` in `portfolio_manifest.yaml`.
  - Intended use: generate a load-only profile that initializes shared guard state and emits `SHARED_GUARD init/load`, while not allowing real calendar-month entries.
- Added `--no-entry-month` passthrough to `scripts/mt5_portfolio_deploy_win.py`.
  - Existing callers remain compatible via `getattr(..., None)`.
- Updated `scripts/mt5_portfolio_profile_audit.py`.
  - It now reads `no_entry_month` from the generated profile manifest and treats that override as expected input, not drift.

Tests:
- Added/updated:
  - `tests/test_mt5_portfolio_live_profile.py`
  - `tests/test_mt5_portfolio_deploy_win.py`
  - `tests/test_mt5_portfolio_profile_audit.py`
- Fast suite:
  - `python -m pytest tests\test_mt5_portfolio_live_profile.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_profile_audit.py -q`
  - result: `8 passed`.
- Broader relevant suite:
  - `python -m pytest tests\test_mt5_common.py tests\test_mt5_compile_win.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_mt5_portfolio_profile_audit.py tests\test_portfolio_preflight_win.py tests\test_portfolio_schedule_lint.py tests\test_portfolio_schedule_runner.py tests\test_portfolio_schedule_stress.py tests\test_portfolio_return_sim.py tests\test_shared_guard_log_audit.py -q`
  - result: `110 passed`.

Tool-generated no-entry audit profile:
- Command:
  - `python scripts\mt5_portfolio_live_profile.py --schedule r224_r225_r226_r211_r213_r216_r227_deployable_context --output-dir temp\portfolio_profiles_guard_audit_tool --guard-key-suffix oninit_audit_tool_20260525 --no-entry-month 12`
- Generated profile:
  - `temp/portfolio_profiles_guard_audit_tool/r224_r225_r226_r211_r213_r216_r227_deployable_context`
- Audit:
  - `results/backtest/portfolio_guard_audit_tool_noentry_profile_audit_20260525.md`
  - 7 charts, 7 versions, 7 unique magic numbers, one shared key, pass true.
- Spot input check:
  - chart01/chart02/chart07 contain:
    - `InpSharedMonthlyGuard=true`
    - `InpSharedMonthlyGuardDebug=true`
    - `InpSharedMonthlyGuardKey=r224_r225_r226_r211_r213_r216_r227_deployable_context_oninit_audit_tool_20260525`
    - `InpEntryMonths=12`

Normal schedule regression:
- Preflight:
  - `results/backtest/portfolio_deployable_context_noentry_tool_regression_preflight_20260525.md`
  - proxy total `321956.95`, daily `10.98`, bad `0`, pass.
  - `1.00/entry` stress bad `0`, weakest `2024-09 +28.87`.
  - shared-return daily `11.57`, bad `0`, pass.
  - generated/installed profile audit pass.

Conclusion:
- The no-entry audit profile is now a repeatable tool, not an ad hoc temp YAML edit.
- This still does not complete the objective because MT5 has not been started and no new runtime `SHARED_GUARD` log has been captured.
- Next approved runtime command should use `mt5_portfolio_deploy_win.py --no-entry-month 12 --start` with a unique guard key suffix, then run `shared_guard_log_audit.py` on the new terminal log.

## 2026-05-25 continuation: manifest-driven shared guard log audit

Problem:
- `scripts/shared_guard_log_audit.py` previously required manual `--expect-key` and seven `--expect-version` arguments.
- That was error-prone for the deployable-context portfolio and made runtime evidence collection harder to repeat.

Implementation:
- Enhanced `scripts/shared_guard_log_audit.py`:
  - `--manifest PATH` reads `portfolio_manifest.yaml`.
  - It infers the single expected shared guard key from chart metadata.
  - It infers all expected chart versions.
  - If `--log` is omitted, it scans the newest logs under MT5 `logs/` and `Tester/logs/`.
  - `--mt5-data` and `--latest-logs` allow overriding the log root and count.
- Added tests:
  - manifest key/version inference.
  - latest terminal/tester log discovery.

Validation:
- Unit test:
  - `python -m pytest tests\test_shared_guard_log_audit.py -q`
  - result: `5 passed`.
- Related suite:
  - `python -m pytest tests\test_mt5_portfolio_live_profile.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_profile_audit.py tests\test_shared_guard_log_audit.py tests\test_portfolio_preflight_win.py -q`
  - result: `16 passed`.
- Current-log audit using no-entry profile manifest:
  - command:
    - `python scripts\shared_guard_log_audit.py --manifest temp\portfolio_profiles_guard_audit_tool\r224_r225_r226_r211_r213_r216_r227_deployable_context\portfolio_manifest.yaml --output results\backtest\shared_guard_log_audit_noentry_manifest_current_logs_20260525.md`
  - result:
    - `events=0`, `pass=false`.
    - error: `no SHARED_GUARD events found`.
  - Interpretation:
    - This is expected before starting the new no-entry profile.
    - It confirms the remaining gap is runtime log capture, not manual audit argument drift.
- Normal schedule regression:
  - `results/backtest/portfolio_deployable_context_manifest_audit_tool_preflight_20260525.md`
  - proxy total `321956.95`, daily `10.98`, bad `0`, pass.
  - `1.00/entry` stress bad `0`, weakest `2024-09 +28.87`.
  - shared-return daily `11.57`, bad `0`, pass.
  - generated/installed profile audit pass.

Next runtime evidence command sequence after approval:
1. Deploy no-entry profile with a fresh suffix:
   - `python scripts\mt5_portfolio_deploy_win.py --schedule r224_r225_r226_r211_r213_r216_r227_deployable_context --profile-name WaiTrade2_Portfolio_BTC_GuardAudit_NoEntry --guard-key-suffix oninit_audit_<runid> --no-entry-month 12 --compile --start`
2. Wait for charts to load and logs to flush.
3. Audit logs with the generated manifest:
   - `python scripts\shared_guard_log_audit.py --manifest temp\portfolio_profiles\r224_r225_r226_r211_r213_r216_r227_deployable_context\portfolio_manifest.yaml --output results\backtest\shared_guard_log_audit_noentry_<runid>.md`
4. Expected proof:
   - events include one `init` and six `load` events.
   - all seven deployable-context versions appear.
   - all events use the same suffixed shared guard key.

## 2026-05-25 continuation: one-command guard audit prepare

Problem:
- Runtime shared-guard proof still required several manual steps: deploy profile, audit generated profile, audit installed profile, compile, then run log audit separately.
- The manual chain made it easy to mix suffixes or manifests while collecting the final evidence.

Implementation:
- Added `scripts/portfolio_guard_audit_prepare.py`.
  - Generates a no-entry deployable-context profile with a unique shared guard suffix.
  - Installs it into the Windows MT5 data directory.
  - Optionally compiles the portfolio EA sources.
  - Audits both generated and installed profiles.
  - Runs current-log shared guard audit from the generated manifest.
  - Writes a summary report plus profile/log audit reports.
- The script defaults to deploy/audit only; it does not start MT5 unless `--start` is explicitly supplied.
- `--require-log-audit` can force current logs to pass without starting MT5, which keeps the failure path testable.

Validation:
- Focused suite:
  - `python -m pytest tests\test_portfolio_guard_audit_prepare.py tests\test_shared_guard_log_audit.py tests\test_mt5_portfolio_live_profile.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_profile_audit.py -q`
  - result: `15 passed`.
- Syntax check:
  - `python -m py_compile scripts\portfolio_guard_audit_prepare.py scripts\shared_guard_log_audit.py scripts\mt5_portfolio_live_profile.py scripts\mt5_portfolio_deploy_win.py scripts\mt5_portfolio_profile_audit.py`
  - result: pass.
- Broader relevant suite:
  - `python -m pytest tests\test_mt5_common.py tests\test_mt5_compile_win.py tests\test_mt5_portfolio_deploy_win.py tests\test_mt5_portfolio_live_profile.py tests\test_mt5_portfolio_profile_audit.py tests\test_shared_guard_log_audit.py tests\test_portfolio_guard_audit_prepare.py tests\test_portfolio_preflight_win.py -q`
  - result: `98 passed`.

Prepared official no-entry guard audit package:
- Command:
  - `python scripts\portfolio_guard_audit_prepare.py --schedule r224_r225_r226_r211_r213_r216_r227_deployable_context --guard-key-suffix oninit_prepare_20260525 --no-entry-month 12 --compile --output-prefix portfolio_guard_audit_prepare_oninit_20260525 --output results\backtest\portfolio_guard_audit_prepare_oninit_20260525.md`
- Summary:
  - `generated_profile=temp/portfolio_profiles/r224_r225_r226_r211_r213_r216_r227_deployable_context`
  - `installed_profile=%APPDATA%/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Profiles/Charts/WaiTrade2_Portfolio_BTC_GuardAudit_NoEntry`
  - `compiled=true`
  - `started=false`
  - summary pass true because profile audits passed and runtime logs were not required in deploy-only mode.
- Reports:
  - `results/backtest/portfolio_guard_audit_prepare_oninit_20260525.md`
  - `results/backtest/portfolio_guard_audit_prepare_oninit_20260525_profile_audit.md`
  - `results/backtest/portfolio_guard_audit_prepare_oninit_20260525_log_audit.md`
- Profile audit:
  - generated and installed profiles both pass.
  - 7 charts, 7 versions, 7 unique magic numbers.
  - one shared key: `r224_r225_r226_r211_r213_r216_r227_deployable_context_oninit_prepare_20260525`.
- Current log audit:
  - `events=0`, `pass=false`, `no SHARED_GUARD events found`.
  - This is expected because MT5 was not started.

Conclusion:
- The guard evidence chain is now one repeatable command up to the point of runtime log capture.
- Remaining blocker for final objective: start the prepared no-entry MT5 profile with a fresh suffix, then collect and audit the actual `SHARED_GUARD init/load` events.
