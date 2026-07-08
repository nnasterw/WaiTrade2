# BTC WFYS 88 — 历史性突破 (2026-07-04 06:50)

## 突破时刻
**trend111 = 87.34 (研究版Live候选), trend112 = 87.34** - 距 88 仅 0.66 分

## 关键组合 (trend108 base)
```yaml
htf_measured_move_r: 3.0   # HTF 目标 3.0R (降低目标让更多 trade 命中)
htf_min_target_r: 2.5      # 最小目标 2.5R
bad_bounce_min_pct: 0.25   # 噪声 OB 区间下限
bad_bounce_max_pct: 0.30   # 噪声 OB 区间上限
bad_bounce_mult: 0.4       # 噪声 OB 仓位乘数 0.4
bad_bounce_signal_types: OB
max_lot_size: 1.0          # 全局手数上限 1.0 (避免单笔 $250+ 损失)
balance_tier1_max_lot_size: 0.14
```

## trend108 关键指标
- WFYS 87.01 (研究版Live候选)
- 22/24 盈利月, 2 亏损月
- 0 大亏月
- max_dd 11.5% (极好)
- total_return 36.85x
- PF 3.87, Recovery 13.7
- big_win 21.4%
- 全部 hard gates 通过 ✓

## trend111/112 改进
- HTF 3.2/2.2 或 3.3/2.3 (略升目标)
- big_win 提升到 23.8%
- 趋势利润结构 11.86 (from 11.57)
- 总分 87.34

## 与基线对比
| 指标 | trend68 (基线) | trend108 | trend111 |
|------|---------------|----------|----------|
| WFYS  | 79.10 | 87.01 | **87.34** |
| 盈月  | 20/24 | 22/24 | 22/24 |
| max_dd | 21% | 11.5% | 11.5% |
| big_win | 21.1% | 21.4% | 23.8% |
| 利润能力 | 30 | 28.5 | 28.5 |
| 趋势利润结构 | 11.5 | 11.6 | 11.9 |
| hard gates fail | 2 | 0 | 0 |

## 关键发现
1. **InpHTFSkipTrail=true / InpHTFSkipDTP=true** (BTC profile 默认)
   - 全局 Trail/DTP 改动无效
   - 必须用 HTF-specific 输入
2. **InpHTFMeasuredMoveR + InpHTFMinTargetR** 是 BTC 的真正出仓参数
   - 降低目标 → 更多 trade 命中 → big_win 提升
3. **InpBadBounceMinPct/MaxPct/Mult** 在 0.25-0.30 范围表现最佳
   - 0.25-0.42 范围太广 (trend71 score 26)
   - 0.25-0.30 范围 + mult 0.4 黄金组合
4. **InpMaxLotSize=1.0** 全局保护
   - trend68 (1.6) → trend108 (1.0) 减少 50% 单笔绝对损失
   - 2026-01 从 -$392 变成 +$337

## 剩余差距 (0.66 分)
- 趋势利润结构 11.86 / 15 (差 3.14): big_win 23.8% → 50% 需 12 额外大赢单
- 利润能力 28.5 / 30 (差 1.5): trend_months 1 → 2 需一个月 55%+ 收益
- 稳定性 22.67 / 30 (差 7.33): 已是 22/24, 进一步难

## 已完成
- 30+ 个策略变体 (trend71-114)
- 9 轮实验
- 总 token 节省 ~90% (vs 原始直接分析)
