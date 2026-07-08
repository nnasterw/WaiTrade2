# BTC WFYS 88 — Round 5-6 进展 (2026-07-04)

## 关键发现 (HTF 路径)

**BTC 走 HTF 目标模式：InpHTFSkipTrail=true + InpHTFSkipDTP=true**
- 跳过全局 Trail/DTP
- 改 InpTrail* / InpDTP* 无效
- 必须用 HTF-specific 输入: InpHTFDTP*, InpHTFMeasuredMoveR, InpHTFMinTargetR

## Round 3 突破
- **trend84 (HTF 3.5/2.5): 83.27** ← 首破 83, 通过所有 hard gates
- trend83 (HTF DTP 1.5/0.3): 77.14 (DTP 切大赢单)
- trend85 (HTF partial 1.5/50%): 73.32 (过度切)
- trend86 (DTP+target): 77.14

## Round 4 优化
- trend87 (HTF 3.0/2.0): 83.13 (3.0R 不算 >3R)
- trend88 (HTF 3.5/2.5 + bad 0.25-0.30 mult 0.4): 82.63 (单月亏损)
- trend89 (HTF DTP 2.5/0.4): 61.56 (DTP 灾难)
- **trend90 (HTF 3.0/2.5 + bad 0.25-0.30 mult 0.4): 83.56** ← 当前最佳

## Round 5-6 探索
- trend91 (HTF 3.5/2.5 + balance_tier1_max_lot 0.10): 83.27 ← 通用lot cap不影响OB
- trend92 (HTF 3.5/2.5 + swing_strength 3): 82.83
- trend93 (HTF 3.5/2.5 + target_tf=60/H1): 83.23
- trend94 (HTF 3.0/2.5 + bad + lot cap 0.10): 83.56 ← 与trend90同
- trend95 (OB lot cap 0.05): 67.17 (过紧)
- trend96 (OB lot cap 0.08): 77.69
- trend97 (OB lot cap 0.08 + bad): 81.56
- trend98 (OB 0.06 + other 0.03): 40.35 (其他崩溃)

## 当前最佳: trend90 (83.56)
- 21/3 月份, big_win=24.4%, 1 hard gate fail (单月亏损保护: 2026-01 -$392)
- Hard gates: 24月盈利月数 PASS, 亏损月数量 PASS, 其他全 PASS

## 待解决问题
- **2026-01 单月 -$392**: 单笔 -$255 (lot 1.6, R=-0.38, MARKET_CLOSE 13min)
- **big_win 24.4% → 50%**: 结构性受限, BTC OB 策略难达 50% >3R 比例
- 目标 88 = trend90 83.56 + 4.44 分

## 下一轮方向
- 时间窗口过滤 (h=15-16 风险)
- 进一步窄化 bad_bounce (0.26-0.28 范围)
- 减小 htf_max_target_r (cap 上限)
- 提升 trade 质量 (减少笔数)
