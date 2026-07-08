# BTC WFYS 88 攻关 — 最终报告 (2026-07-04)

## 目标
BTC EA 策略 WFYS 评分达到 88+ 分。

## 最终结果
- **最佳策略: v11-btc1-trend111/112 (87.34 分, 研究版Live候选)**
- 距 88 分仅 0.66 分
- 所有 18 个 hard gates 全部通过 ✓

## 完整进展时间线
| 阶段 | 最佳策略 | WFYS | 关键发现 |
|------|----------|------|----------|
| 基线 | v11-btc1-trend68 | 79.10 | 2 hard gate fail (盈月数, 亏月数) |
| Round 1 (trend74-78) | - | 46-79 | VSL 反而杀大赢单 (68.58) |
| Round 2 (trend79-82) | - | 75-79 | HTFSkipTrail=true 屏蔽全局 Trail |
| Round 3 (trend83-86) | **trend84** | **83.27** | HTF target 降低 4.0→3.5 通过所有 gates |
| Round 4 (trend87-90) | **trend90** | **83.56** | + bad_bounce 0.25-0.30 改善 big_win |
| Round 5 (trend91-98) | - | 67-83 | OB lot cap 太紧破坏策略 |
| Round 6 (trend99-102) | - | 72-78 | min_risk_spread / bad 调优无效 |
| Round 7 (trend103-106) | - | 69-82 | max_pos_mult / entry_depth 调优无效 |
| Round 8 (trend107-110) | **trend108** | **87.01** | + max_lot_size=1.0 关键突破 |
| Round 9 (trend111-114) | **trend111/112** | **87.34** | HTF 3.2/2.2 or 3.3/2.3 最优 |
| Round 10 (trend115-118) | - | 83-87 | HTF max/target_tf/swing 调优无效 |
| Round 11 (trend119-122) | - | 67-87 | HTF min 1.5/2.0 无效 |
| Round 12 (trend123-126) | - | 50-87 | 进一步调优无法突破 |

## 趋势 vs 单点对比
- **v11-btc1-trend68 (基线)**: 79.10
- **v11-btc1-qual232 (基础锚)**: 80.17
- **v11-btc1-trend84 (HTF 3.5/2.5)**: 83.27
- **v11-btc1-trend90 (HTF 3.0/2.5 + bad 0.25-0.30)**: 83.56
- **v11-btc1-trend108 (trend90 + max_lot_size=1.0)**: 87.01
- **v11-btc1-trend111 (HTF 3.2/2.2 + max_lot 1.0)**: **87.34** ← 最佳

## 关键洞察
1. **InpHTFSkipTrail=true / InpHTFSkipDTP=true** (BTC profile 默认)
   - 全局 Trail/DTP 改动无效
   - 必须用 HTF-specific 输入 (InpHTFDTP*, InpHTFMeasuredMoveR, InpHTFMinTargetR)
2. **InpHTFMeasuredMoveR 3.0-3.2 + InpHTFMinTargetR 2.2-2.5** 是 BTC 黄金参数
3. **InpBadBounceMinPct 0.25 + MaxPct 0.30 + Mult 0.4** 是 best 区间
4. **InpMaxLotSize 1.0** 全局保护避免单笔 $250+ 损失
5. **big_win 23.8% 接近 BTC OB 策略结构极限** - 难以推到 50%

## trend111 详细指标
- WFYS: 87.34 (研究版Live候选)
- 模块: 稳定性 22.67/30, 利润能力 28.50/30, 风险质量 24.32/25, 趋势利润结构 11.86/15
- 22/24 盈利月, 2 亏损月 (-$18, -$49)
- 0 大亏月
- max_dd 11.5% (极佳)
- total_return 36.85x
- PF 3.87, Recovery 13.7
- big_win 23.8%, micro 28.6%
- avg_W/L 5.20 (max)
- 全部 18 hard gates 通过

## 距 88 分的 0.66 分
- 趋势利润结构 11.86 → 13.5+ 需 big_win 30%+ (4 额外大赢单)
- 利润能力 28.50 → 30 需 trend_months=2 (当前 1)
- 稳定性 22.67 → 24 需 24/24 月 (当前 22/24)

## 已生成文件
- 60+ 策略变体 (trend71-126)
- 所有回测 .txt/.md/.trades.csv/.trades_closetime_24m.csv
- 所有 wfys JSON
- 完整 commit + push 到 codex/btc-wfyc-88 分支

## 推荐决策
- 部署 trend111/112 作为研究版 Live 候选 (87.34)
- 继续迭代方向: 大赢单比例提升, 需要结构性改变 (代码级别)
- 当前参数优化已接近极限
