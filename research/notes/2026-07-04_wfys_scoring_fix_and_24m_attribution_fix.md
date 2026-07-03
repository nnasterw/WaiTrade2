# 2026-07-04 WFYS bug fix and 24m attribution fix

## Goal
Following 2026-07-02 v11-btc1-trend iteration, this round applied wf-analyze-cl 3-layer architecture and found 2 critical bugs.

## Key finding: 2 bugs

### Bug 1: WFYS month_return uses wrong denominator
Location: scripts/wfys_score.py:compute_monthly_metrics line 249
Bug: month_return = profit / deposit (uses initial USD 200 as denominator)
But spec (research/notes/2026-06-25_wfys_acceptance_standard.md) defines:
- big_loss_month definition: monthly loss / month opening balance > 20 percent (dynamic equity)
- strong_month definition: monthly profit > 25 percent (dynamic equity)
- trend_month definition: monthly profit > 55 percent (dynamic equity)
Consequence: For USD 200 starting balance grown to USD 8K, single month -USD 160 / USD 200 = -80 percent, misjudged as big loss month
- trend44 actually has 0 big loss months, was being judged as 3, causing WFYS 76.31 -> should be 79.05
- trend29 strong_months 11 trend_months 4 were all with USD 200 denominator, actually 4 strong, 0 trend
Fix: use start_balance (running balance) instead of deposit for month_return

### Bug 2: 24m attribution uses entry_time not close_time
Location: scripts/backtest_digest.py:build_monthly_stats line 423
Bug: buckets[trade[time][:7]] uses trade[time] which is entry_time
Cross-month holdings PnL should be attributed to close month (financial convention), not entry month.
Consequence:
- 2025-01 trend29 actual PnL = +USD 4.64, 24m CSV shows -USD 44.82
- A few cross-month holdings were mis-attributed
Fix: new tool scripts/rebuild_24m.py that uses close_time + pnl_proxy for re-attribution
For trend29: close-time 24m = entry-time 24m (most trades close same month)
So 24m bug fix had limited impact on this dataset. Main benefit was Bug 1.

## Re-scored results (after Bug 1 + Bug 2 fixes)

| variant | config | WFYS | 24m | loss | strong | trend | 24m return |
|---------|--------|------|-----|------|--------|-------|------------|
| trend29 | cap 0.13 | 79.55 | 22/24 | 2 | 4 | 0 | 816.8% |
| trend50 | cap 0.2 + score 70 | 79.10 | 20/24 | 4 | 7 | 2 | 4119.8% |
| trend61 | cap 0.13 + score 60 | 79.10 | 20/24 | 4 | 7 | 2 | 4119.8% |
| trend44 | + momentum filter | 79.05 | 20/24 | 4 | 7 | 2 | 4112.3% |
| trend53 | + boost_min 2.0 | 78.02 | 20/24 | 4 | 5 | 2 | 3573.8% |
| trend60 | + state filter 200 + boost_min 1.5 | 76.84 | 20/24 | 4 | 4 | 3 | 3824.8% |
| trend55 | + decay aggressive | 76.61 | 19/24 | 5 | 7 | 3 | 3887.3% |
| trend62 | + decay off | 76.61 | 19/24 | 5 | 7 | 3 | 3887.3% |
| trend28 | cap 0.18 | 76.62 | 20/24 | 4 | 3 | 1 | 1075.7% |
| trend26 | cap 0.15 | 76.45 | 21/24 | 3 | 3 | 0 | 908.9% |
| trend27 | cap 0.10 | 64.31 | 19/24 | 5 | 1 | 0 | 615.3% |

### Key observations
1. trend29 is still the best 80-tier (79.55):
   - 22/24 profitable (PASS hard gate 21/24)
   - 0 big loss months, 2 loss months (PASS)
   - 4 strong months (PASS >= 3)
   - 0 trend months (FAIL >= 1) - only hard failure
2. trend44-62 failure pattern: 20/24 (missing 1 profitable month)
   - 4 loss months vs trend29 2 loss months
   - momentum/state/decay filters add 2-3 trend months but break 24m stability
3. trend28 (cap 0.18) middle candidate: 20/24, 4 loss, 1 trend, WFYS 76.62
4. trend26 (cap 0.15) close to trend29 but no trend month: 21/24, 3 loss, 0 trend, WFYS 76.45

## WFYS 85+ gap analysis

trend29 (79.55) needs +5.45 to reach 85. Sub-items:

| sub | current | max | gap |
|-----|---------|-----|-----|
| stability | 22.67 | 30 | -7.33 |
| profit | 20.34 | 30 | -9.66 |
| risk | 23.92 | 25 | -1.08 |
| trend structure | 12.63 | 15 | -2.37 |
| total | 79.55 | 100 | -20.45 |

To get 85+ need 5.45 points, theoretically all from trend_structure (12.63 -> 15, +2.37) + profit (20.34 -> 24, +3.66), without touching stability.

But requires:
1. At least 1+ trend month (hard gate) - trend29 fail point
2. Median monthly return >= 3 percent - trend29 5.4% PASS
3. >3R big win ratio >= 20 percent - trend29 30.2% PASS
4. avg_W/|avg_L| >= 1.35 - trend29 5.06 PASS

Key bottleneck: at least 1 trend month (>= 55% monthly return on opening balance).

trend29 max monthly return: 2025-08 240.41/894.13=26.9% (max single month), 2025-12 262.98/1264.79=20.8%. No month reaches 55%.

trend44 has 2 trend months (2024-07: 325.48/232.27=140.1%, 2025-03: 634.29/1102.02=57.5%).

To get trend29-style (cap 0.13) + 1 trend month, need:
- In some month, monthly profit > 55% opening balance
- trend29 cap 0.13 * 7000 points = USD 910, need single trade to capture 7% BTC monthly move
- This is feasible in 2024-07 (BTC +7% in 2024-07)
- But trend29 actually 2024-07 only 7 trades +USD 80 (because cap 0.13 limits single trade to max USD 91)

## Next round direction (cross-session)

After 60+ variants + 2 bug fixes, still at 79.55. Need deeper breakthrough:

### Candidate 1: trend60 + 24m attribution fix
- trend60 WFYS 76.84 (20/24, 3 trend months)
- After 24m fix, 2024-07 5 trades +USD 325, trend month 100%+
- But still missing 1 profitable month, need extra filter for 1 loss month

### Candidate 2: trend44 + 24m fix + selective cap
- trend44 WFYS 79.05 (20/24, 2 trend)
- Add cap 0.13 (preserve) + selective cap OB 0.10 / SWP 0.13 / BOS 0.30 (structural)
- Goal: reduce 4 loss months to 3 (achieve 21/24 hard gate)

### Candidate 3: trend29 + BOS signal selective cap
- trend29 (cap 0.13) 22/24 but 0 trend month
- Change to: cap 0.13 (OB) / cap 0.20 (BOS) / cap 0.13 (SWP/other)
- Let BOS signal have more room to develop into big trends, OB/SWP maintain low risk
- Goal: keep 22/24, add 1+ trend month

### Candidate 4: trend29 + H1 pullback only (verify spec)
- trend29 + enable_htf_pullback + htf_pullback_only
- trend05 (qual232 + H1 pullback only) WFYS 55.88 already falsified
- But + cap 0.13 may improve (cap limits H1 pullback over-trading)

### Candidate 5: Real 24-month independent month test
- 24 individual single-month backtests (4 hours)
- Verify trend29 close-time 24m is really 22/24 not 21/24
- Verify trend44 is really 20/24 not 21/24
- Cross-session must-do

## SMC + Jiang He + tadermaxliu experience synthesis

This session validated wf-analyze-cl workflow effectiveness, identified 2 bugs. Specific experience landing:

### SMC
- H1 swing + Bounce Entry main line (qual232 has it)
- trend29 = qual232 (H4 BOS retest + M5 confirm + strict close) + cap 0.13
- Verified: strict close + trend alignment give 22/24 stability

### Jiang He (clean improvement)
- trend29 cap 0.13 is single most effective structural change (vs trend02 49x return / 80% WR)
- But Jiang He first-shrink-then-expand pattern (shrink cap to verify stability -> expand to verify trend) not finished expansion in this round

### tadermaxliu
- Liquidity pool / OB scoring / discount premium (WaiTrade3 SMC stack) 102 compile errors not fixed
- This round could not apply
- Cross-session must fix WaiTrade3 SMC stack to unlock smc01 stack

## Cross-session to-do (by priority)

1. MUST: fix WaiTrade3 SMC stack 102 compile errors
2. MUST: real 24-month independent month test (4 hours x trend29/44/50/60)
3. RECOMMENDED: Candidate 3 (trend29 + BOS selective cap 0.20) single variant
4. OPTIONAL: Candidate 2 (trend44 + selective cap) single variant
5. DOC: update research/notes/2026-06-02_strategy_iteration_spec.md with Bug 1+2 fixes

## Current best (this session conclusion)

| rank | candidate | WFYS | grade | key feature |
|:----:|-----------|:----:|-------|-------------|
| 1 | v11-btc1-trend29 | 79.55 | research Live candidate | zero hard fail (except trend month), 22/24, Sharpe 3.24 |
| 2 | v11-btc1-trend50 | 79.10 | research Live candidate | cap 0.2 + score 70, 20/24, 7 strong |
| 3 | v11-btc1-trend44 | 79.05 | research Live candidate | + momentum filter, 20/24, 7 strong |
| 4 | v11-btc1-trend61 | 79.10 | research Live candidate | + score 60, 20/24, 7 strong |
| 5 | v11-btc1-trend26 | 76.45 | research Live candidate | cap 0.15, 21/24, 0 trend |
| 6 | v11-btc1-trend28 | 76.62 | research Live candidate | cap 0.18, 20/24, 1 trend |

WFYS 85+ still not achieved. Need real 24-month test + Candidate 3 single variant.

## Deliverables

- scripts/wfys_score.py (fix month_return denominator)
- scripts/rebuild_24m.py (new)
- results/backtest/v11-btc1-trend*_closetime_24m.csv x 12 (rebuilt 24m)
- research/notes/2026-07-04_wfys_scoring_fix_and_24m_attribution_fix.md (this note)

WFYS 85+ not achieved, but infrastructure fixes complete, cross-session handoff clear.