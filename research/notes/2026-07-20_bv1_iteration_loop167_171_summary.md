Variants tested summary (2026-07-20, BV1 path with WaiTrade_OB.ex5,  deposit, 720d Model 4):
Baseline:
  v11-btc1-bv1 (loop160): 110 trades, 41.8% WR, , WFYS 89.57, weekly 1.07, 1 hard fail (weekly)

Loop 167 (signal-source activation, all destructive):
  mbosr (MicroBOS Retest): 189 trades, 32.8% WR, , WFYS 20.72, weekly 1.84
  cpwb (ConfirmPullback): 33 trades, --, -.74, WFYS 48.54 (promoted but bankrupted)
  mitonr (MitigationEntry): 185 trades, 31.9% WR, , weekly 1.80

Loop 168 (OB quality micro-tunes, all destructive):
  obreec0 (OB reentry cooldown 30->0): 28 trades 90d, -.89 (bankrupted)
  maxent5 (max entries/ob 3->5): 43 trades 90d, 
  obpct40 (min OB body 50->40): 174 trades, 28.7% WR, , WFYS 34.54

Loop 169 (additional signal sources, high freq but unstable):
  htfpb (HTF Pullback): 265 trades, 29.8% WR, , WFYS 27.87, weekly 2.85 PASS
  htfpb-strict: 189 trades, 32.8% WR,  (same as mbosr - min_day ineffective)
  swplp (Sweep OB pos_mult 0->0.5): 591 trades, 39.6% WR, , WFYS 24.34, weekly 6.03 PASS

Loop 170 (sweep-tweaks, all destructive):
  swplp30 (sweep_pos 0.3): 90d 120 trades, 
  obreec60 (OB reentry cooldown 60): 529 trades, 36.9% WR, , WFYS 25.79
  maxent2 (max entries/ob 2): 32 trades, 40.6% WR, - (bankrupted early in 2024-10)

Loop 171 (sweep-quality tweaks):
  mrsr7 (min risk/spread 7): 90d 180 trades, 
  slot10 (sweep max lot 0.10): 90d 151 trades, 
  trail2 (Trail2 2.0/1.5): 621 trades,  (identical to swplp - trail_levels disabled)

Key findings:
1. BV1 89.57 is the architecture ceiling for OB-only entry
2. Any activation of new entry signal (Sweep/HTFPB/MicroBOS/Mitigation/ConfirmPullback) increases weekly trades but breaks monthly stability
3. Sweep OB (swplp) achieves 6 weekly but 4 big-loss months, avg_W/L=1.82 << 3.0 hard gate
4. Quality relaxation (min_ob_body 50->40) destroys both quality and stability
5. 2024-10, 2025-12, 2026-03 are persistent big-loss months under sweep signal activation
6. Trail enhancements are disabled by InpTrailLevels design
