#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""优化汇总：大表格 + 汇总结论"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

DEPOSIT = 200

P25 = {
    'Q2':        [ 39.94,  176.73, 117.96, 1648.91, 1013.65],
    'QS3':       [ 23.86,  211.33,  66.93, 4586.72, 2351.44],
    'QS4':       [ 11.42,  107.04,  48.81, 1056.30,  667.14],
    'Q2+NOISE':  [ -2.79,  -19.96,  24.46,  320.72,   26.80],
    'QS3+NOISE': [ -5.50,   -3.25,   8.05,   51.25,   50.42],
    'QS4+NOISE': [ -2.74,   -1.05,   2.67,   20.90,   22.13],
}
P26 = {
    'Q2':        [ 26.75, -198.50, -172.90, -198.02, -197.92],
    'QS3':       [-31.93, -156.88, -180.72, -142.76, -199.01],
    'QS4':       [  5.85, -149.26, -159.48, -116.64, -169.32],
    'Q2+NOISE':  [223.43,   56.19,  -97.27,   -7.06,  -36.09],
    'QS3+NOISE': [ 49.98,   14.77,  -50.72,   -8.73,   -0.01],
    'QS4+NOISE': [ 63.43,   16.31,  -50.72,   -8.73,   -0.01],
}
META = {
    'Q2':        { 'trades': 1586, 'wr': 61.9, 'pf': 1.63 },
    'QS3':       { 'trades': 1971, 'wr': 62.6, 'pf': 1.67 },
    'QS4':       { 'trades': 1849, 'wr': 62.6, 'pf': 1.68 },
    'Q2+NOISE':  { 'trades':  197, 'wr': 60.9, 'pf': 1.56 },
    'QS3+NOISE': { 'trades':  210, 'wr': 62.9, 'pf': 1.69 },
    'QS4+NOISE': { 'trades':  130, 'wr': 61.5, 'pf': 1.60 },
}
META26 = {
    'Q2':        { 'trades': 1877, 'wr': 45.3, 'pf': 0.83 },
    'QS3':       { 'trades': 2351, 'wr': 47.5, 'pf': 0.91 },
    'QS4':       { 'trades': 2139, 'wr': 48.5, 'pf': 0.94 },
    'Q2+NOISE':  { 'trades':  245, 'wr': 57.6, 'pf': 1.36 },
    'QS3+NOISE': { 'trades':  188, 'wr': 52.7, 'pf': 1.11 },
    'QS4+NOISE': { 'trades':  176, 'wr': 54.0, 'pf': 1.17 },
}

STRATS = ['Q2','QS3','QS4','Q2+NOISE','QS3+NOISE','QS4+NOISE']

def fmt_tbl(year, mp, mm):
    print(f"\n{'='*110}")
    print(f"  {year} - 汇总大表格 (${DEPOSIT} initial)")
    print(f"{'='*110}")
    hdr = f"  {'Strategy':<12} | {'Deposit':>8} | {'Daily':>6} | {'WR':>6} | {'PF':>6} | {'Net PnL':>10} | {'Final Bal':>10}"
    print(hdr)
    print(f"  {'-'*76}")
    best_total = max(sum(mm[s]) for s in STRATS)
    for s in STRATS:
        t = mp[s]; m = mm[s]
        total = sum(m)
        bal = DEPOSIT + total
        daily = t['trades'] / 151
        mark = ' *' if total == best_total else '  '
        print(f"  {s:<12} | ${DEPOSIT:>7} | {daily:>5.1f} | {t['wr']:>4.1f}% | {t['pf']:>4.2f} | ${total:>+8,.0f}{mark} | ${bal:>8,.0f}{mark}")

fmt_tbl('2025', META, P25)
fmt_tbl('2026', META26, P26)

# ========== 汇总结论 ==========
print(f"""

{'='*110}
  汇总结论 / CONCLUSIONS
{'='*110}

[1]  2025 (Trend Market) vs 2026 (Chaos Market) - Complete Reversal

  Year  |  Best Strategy    |  Net PnL  |  Final Bal  |  WR   |  PF
  ------|-------------------|----------:|------------:|------:|----:
  2025  |  QS3 (OFF)        |  +$7,240  |   $7,440    | 62.6% | 1.67
  2026  |  Q2+NOISE         |    +$139  |     $339    | 57.6% | 1.36

  The same QS3 strategy went from +$7,440 to -$511 (blowout) as
  market regime shifted. Win rate collapsed from 62.6% to 47.5%,
  PF dropped from 1.67 to 0.91 (below breakeven).

[2]  NOISE Filter - Double-edged Sword

  Scenario      |  OFF Best  |  NOISE Best  |  NOISE Impact
  --------------|-----------:|-------------:|:--------------
  2025 (Trend)  |  QS3+$7240 |  Q2+N +$349  |  96% profit loss
  2026 (Chaos)  |  QS4 -$589 |  Q2+N +$139  |  Saved from blowout

  NOISE cuts trade volume by ~90% regardless of market. In trending
  markets it destroys returns; in adverse markets it prevents death.

[3]  Cross-Year Ranking

  2025:  QS3 > Q2 > QS4 >> Q2+N > QS3+N > QS4+N  (OFF dominates)
  2026:  Q2+N > QS4+N > QS3+N > QS4 > QS3 > Q2  (NOISE dominates)

  Complete rank reversal. No static configuration works across regimes.

[4]  Key Takeaway

  The data shows a market-regime dependency so strong that it
  overwhelms intra-year strategy differences. An adaptive mechanism
  that detects trend vs chaos conditions and adjusts entry density
  and filter tightness accordingly is the logical next step.
  Q2+NOISE as the only cross-year positive strategy ($349 -> $139)
  is worth studying as a "defensive baseline".
""")
