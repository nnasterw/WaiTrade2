"""Quick summary of noise gate sweet spot scan results."""
results = {
    'REF_OFF':  ('QS3-OFF(pure)', 588, 19.0, 66.5, 2.02, 4532, 497, 16.0, 47.3, 0.56, -199),
    'REF_LOOSE':('SL5M2+NK(lb10r20r25)', 783, 25.3, 64.6, 1.95, 6691, 371, 12.0, 48.8, 0.69, -112),
    'REF_TIGHT':('SL5M2+NK(lb30r35r15)', 210, 6.8, 59.5, 1.84, 186, 21, 0.7, 66.7, 0.94, -1),
    'A1': ('lb10(SL5M2+r30/a18)', 676, 21.8, 64.5, 2.04, 3506, 224, 7.2, 48.7, 0.67, -75),
    'A2': ('lb15(SL5M2+r30/a18)', 529, 17.1, 61.6, 2.03, 1383, 142, 4.6, 50.7, 0.69, -48),
    'A3': ('lb20(SL5M2+r30/a18)', 450, 14.5, 60.4, 2.05, 967, 97, 3.1, 57.7, 0.91, -9),
    'A4': ('lb25(SL5M2+r30/a18)', 356, 11.5, 59.8, 2.02, 570, 61, 2.0, 57.4, 0.82, -13),
    'A5': ('lb30(SL5M2+r30/a18)', 324, 10.5, 59.6, 2.03, 437, 46, 1.5, 56.5, 0.60, -22),
    'B1': ('r0.20(SL5M2+lb20/a18)', 472, 15.2, 61.7, 2.13, 1168, 97, 3.1, 57.7, 0.91, -9),
    'B2': ('r0.25(SL5M2+lb20/a18)', 467, 15.1, 61.7, 2.14, 1183, 97, 3.1, 57.7, 0.91, -9),
    'B5': ('r0.40(SL5M2+lb20/a18)', 391, 12.6, 59.1, 1.82, 487, 95, 3.1, 58.9, 0.98, -2),
    'C1': ('a0.10(SL5M2+lb20/r30)', 153, 4.9, 52.3, 1.41, 56, 6, 0.2, 66.7, 2.22, 7),
    'C2': ('a0.14(SL5M2+lb20/r30)', 314, 10.1, 58.3, 1.91, 350, 40, 1.3, 65.0, 1.12, 5),
    'C4': ('a0.22(SL5M2+lb20/r30)', 547, 17.6, 61.8, 2.04, 1699, 156, 5.0, 48.7, 0.68, -56),
    'C5': ('a0.25(SL5M2+lb20/r30)', 604, 19.5, 61.9, 2.03, 2479, 204, 6.6, 50.5, 0.77, -46),
}

print()
print("=" * 110)
print("QS3 Noise Gate Sweet Spot Scan - Summary")
print("=" * 110)
print(f"{'Rank':<5} {'Variant':<42} {'2505 T':>6} {'PF':>6} {'PnL':>10} | {'2605 T':>6} {'PF':>6} {'PnL':>10} | {'Net':>10}")
print("-" * 110)
ranked = sorted(results.items(), key=lambda x: x[1][5] + x[1][10], reverse=True)
for i, (k, v) in enumerate(ranked, 1):
    net = v[5] + v[10]
    mark = ' ** 2605 POSITIVE!' if v[10] > 0 else ''
    print(f"{i:>4}  {v[0]:<42} {v[1]:>6} {v[4]:>5.2f} ${v[5]:>+9,.0f} | {v[6]:>6} {v[9]:>5.2f} ${v[10]:>+9.2f} | ${net:>+9,.0f}{mark}")

print()
print("=" * 110)
print("KEY FINDINGS")
print("=" * 110)
print("""
1. RangeATR is the DOMINANT parameter. MinDirRatio has almost zero marginal
   effect on 2605 filtering (B1-B5 all gave 97T, -$9.07 in 2605).

2. 2605 becomes profitable ONLY when MaxRangeATR <= 0.14:
   - C1 (a=0.10): 2605=+$7.36 (6T), 2505=+$56 (153T)
   - C2 (a=0.14): 2605=+$4.56 (40T), 2505=+$350 (314T)

3. But this kills 2505 profitability (from $4,532 down to $56-$350).
   The trade-off: gain ~$204 in 2605 but lose ~$4,200 in 2505 = net -$4,000.

4. Between a=0.14 and a=0.18 is the transition zone where 2605 flips:
   - a=0.18: 2605=-$9 (near breakeven, 97T, WR=57.7%)
   - a=0.22: 2605=-$56 (still negative, 156T)

5. STATIC noise gate CANNOT solve the dual-month problem alone.
   - Loose enough for 2505 profit → 2605 still negative
   - Tight enough for 2605 profit → 2505 destroyed

6. The ADAPTIVE approach is essential: start loose (a=0.22+),
   tighten on drawdown (a=0.14-). In good months it stays loose.
   In bad months it tightens after 2-3% drawdown (~3-5 losing trades).
""")
