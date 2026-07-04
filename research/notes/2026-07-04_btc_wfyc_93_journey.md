# BTC WFYS 93+ 攻关 — 完整旅程 (2026-07-04)

## 目标
BTC EA 策略 WFYS 评分达到 93+ 分 (用户明确允许代码级结构性改造)

## 最终结果
- **最佳策略: v11-btc1-trend111/112 (87.34 分, 研究版Live候选)**
- **距 93 分: 5.66 分**
- 90+ 仍需重大代码改造或重新设计策略

## 关键发现
1. **InpHTFSkipTrail=true / InpHTFSkipDTP=true** (BTC profile 默认) → 全局 Trail/DTP 改动无效, 必须用 HTF-specific 输入
2. **NoMFE/MFE-Fail 逻辑对 BTC HTF 目标模式不生效** → 实际 SL losses 在 NoMFE 之前 SL'd
3. **bounce_ob 0.25-0.30 区间同时包含大赢单和大损单** → bad_bounce 过滤无法精确区分
4. **big_win 23.8% 是 BTC OB 策略的结构极限** → 难以推到 50%

## 已尝试 60+ 个策略变体
- trend74-78: 单 lever 改动 (VSL/OB cap/score/MFE) 全部 ≤ 87
- trend83-90: HTF 目标 + bad_bounce 突破 87
- trend91-98: OB lot cap 探索 (太紧破坏)
- trend99-110: min_risk_spread, max_pos_mult, max_lot_size 探索
- trend111-114: HTF 3.2/2.2 达到 87.34
- trend115-150: 各种 HTF/swing/lot cap 调整, 全部 87.34 或更低
- trend151-154: 极限 NoMFE 设置 (1bar/1.0peak/-0.5R) 全部 87.34

## 趋势 vs 单点对比
| 策略 | WFYS | 等级 | 关键 |
|------|------|------|------|
| v11-btc1-trend68 (基线) | 79.10 | 淘汰 | 2 hard gate fail |
| v11-btc1-qual232 (基础锚) | 80.17 | 观察级候选 | base |
| v11-btc1-trend84 | 83.27 | 观察级候选 | HTF 3.5/2.5 |
| v11-btc1-trend90 | 83.56 | 淘汰 | + bad_bounce 0.25-0.30 |
| v11-btc1-trend108 | 87.01 | 研究版Live候选 | + max_lot_size 1.0 |
| **v11-btc1-trend111** | **87.34** | **研究版Live候选** | HTF 3.2/2.2 |
| v11-btc1-trend113 | 87.10 | 研究版Live候选 | HTF 3.1/2.0 |

## 87.34 的模块分解
- 稳定性: 22.67 / 30 (差 7.33, 主要: 22/24 盈月)
- 利润能力: 28.50 / 30 (差 1.50, 主要: trend_months=1)
- 风险质量: 24.32 / 25 (差 0.68, 接近 max)
- 趋势利润结构: 11.86 / 15 (差 3.14, 主要: big_win 23.8%)

## 93+ 所需
- 利润能力 +1.5: 需 2 trend months (2025-01 需 55%+, 当前 51.6%, 差 $24)
- 趋势利润结构 +3.14: 需 big_win 50% (当前 23.8%, 需 12 额外大赢单)
- 稳定性 +1.5: 需 24/24 月 (当前 22/24, 需预防 2024-11/2026-05 损月)
- 风险质量 +0.68: 推到 max

## 关键尝试
1. **bad_bounce BLOCK (trend127-130)**: 严重破坏, score 34-79
2. **NoMFE/MFE 强化 (trend139, 147-154)**: 对 BTC HTF 模式无影响, 全部 87.34
3. **HTF target 调整 (trend84-90)**: trend84 HTF 3.5/2.5 突破 83, trend90 加 bad_bounce 83.56
4. **max_lot_size 1.0 (trend108)**: 关键突破, 避免单笔大亏
5. **小时过滤 (trend131-134)**: 无效 (entry time vs OB creation time 不同)
6. **冷却/min_bounce 探索 (trend135-138)**: BTC-specific 才有效果但仍 87.34

## 代码级结构改造尝试
- 编译验证: metaeditor64.exe /portable /compile 成功 (2026-07-04 13:06)
- 添加的 BTC-specific 参数 (InpBTCNoMFEExitBars 等): 对 BTC HTF 模式无影响
- 原因: 现有 NoMFE/MFE Fail 检查在 HTF target 模式下不生效 (track.htf_target 触发 skip_mfe_exits 条件)

## 结论
BTC OB 策略 + HTF 目标系统的 WFYS 评分在 **87-88** 是参数优化能达到的极限。
93+ 需要:
1. **策略方向重新设计** (不只是参数调优)
2. **重大代码改造** (修改 HTF target 逻辑 / NoMFE skip 条件 / 引入新 filter)
3. **不同时间周期或品种** (BTC M5 可能本身有限)

## 文件
- config/strategies.yaml: 60+ trend71-154 变体
- mql5/Presets/v11-btc1-trend*.set: 对应 .set 文件
- results/backtest/: 所有回测 + WFYS
- 12+ git commits 推送至 codex/btc-wfyc-88 分支
