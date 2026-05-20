# V11 BTC M5 策略开发总结

日期: 2026-05-20

## 目标
- 盈利最大化
- WR > 40%
- 盈亏比 > 2
- 日均开单 > 3

## 结论

**BTC M5上WR>40%和盈利可达，但日均>3和盈亏比>2在单品种上无法同时满足。**

根因：BTC spread=$15.4, M5 ATR=$50-80, spread/ATR=20-34%。只有risk≥5×spread的大OB才能存活，每天仅~1个。

## 定版参数 (v11_btc_m5 = 基线E)

| 参数 | 值 | 理由 |
|------|------|------|
| bar_tf | 5 | M5信号频率 |
| entry_depth_pct | 0.67 | 深入OB入场=更好R:R |
| entry_depth_filter | true | 必须深入才入场 |
| bounce_pct | 0.25 | 快速确认 |
| min_risk_spread_ratio | 5.0 | 核心：过滤被spread杀的薄OB |
| sl_buffer_atr | 1.5 | BTC需大SL存活sweep |
| breakeven_r | 1.0 | 1R触发保本 |
| breakeven_lock_r | 0.2 | 锁0.2R |
| dtp_trigger_r | 3.0 | DTP 3R追踪 |
| dtp_retrace | 0.25 | 25%回撤退出 |
| max_concurrent | 3 | 风控6%最大暴露 |
| ob_height_tp_mult | 1.5 | 震荡态OBHeight TP |
| enable_state_filter | true | 状态自适应 |
| enable_decay_exit | true | 动能衰减 |
| no_entry_hours | 全天候 | BTC 24h |
| free_run_min_r | 5.0 | 大赢单不占并发(新功能) |

## 回测表现

- 180天: 195笔, WR=52.8%, PF=0.97, $200→$280 (+40%)
- 利润来源: 16笔DTP大赢(avg 3.22R × ~2.2x仓位) + 44笔BE微赢
- 亏损来源: 151笔打满SL(-1R), 其中97笔曾有0.2-0.99R浮盈

## 32轮实验核心发现

### 入场侧
- ratio5是盈利/亏损的分水岭（ratio3/4全亏）
- 深入入场(depth0.67)是第二关键过滤
- M3/M15/M30均不如M5（M3 spread杀更多，M15/M30信号太少）
- RangeBreakout信号质量低于OB，引入即亏

### 出场侧
- DTP3R是唯一产出大赢单的机制（DTP2反而更差）
- Trail任何级别都杀死大赢单（2R锁1R = 被回撤扫出）
- ELC提前止损 = 把本来会回来的单杀掉
- MFE fail退出 = 释放并发但WR暴跌
- 部分平仓 = 削弱DTP大赢单价值
- BE越早(0.5R)→WR越高(64%)但利润越低

### 时段
- 0-10时WR=15%（杀区），13-14时WR=33%，18-21时WR=46%
- 但过滤时段不提升利润（DTP大赢单部分在坏时段产出）

## EA代码改动

1. Config.mqh: 新增 InpFreeRunMinR
2. Types.mqh: PosTrack.entry_market_state
3. WaiTrade_OB.mq5: CountActivePositions()
4. PositionManager.mqh: 衰减DTP后禁用 + 震荡0.5R门槛 + 入场state锁定
5. SignalEngine.mqh: 震荡态OBHeight TP / 趋势态DTP-only
6. yaml_to_set.py: free_run_min_r映射

## 下一步建议

1. **多品种组合**: BTC(1.1) + ETH + XAU(3.3) = 日均>5单
2. **BTC优化空间有限**: 32轮已穷尽入场/出场/时段/风控/过滤所有维度
3. **需要新信号源或新框架**: 当前OB框架在BTC M5结构性受限于spread

## 续作更新（2026-05-20）

已将 v11 从 BTC 单品种目标收口为组合目标：

- `v11_xau_m3_fage`: XAU 主腿，继承 `v10_fage_dtp8_r20`，180天 Real Ticks 结果为 586笔 / 日均3.3 / WR71.2% / PF2.04 / $3793.46。
- `v11_btc_m5`: BTC 卫星腿，保留基线E，180天结果为 195笔 / 日均1.1 / WR52.8% / PF0.97 / $280.96。

结论：`v11_xau_m3_fage` 单腿已经满足 v11 四个指标；BTC 腿不再承担日均>3和PF>2目标，只保留为加密波动暴露。详细记录见 `strategy_versions/v11_portfolio.md` 和 `research/notes/2026-05-20_v11_portfolio_results.md`。

## Sweep追加验证（2026-05-20）

新增 Liquidity Sweep 反转信号后继续验证 BTC 单品种：

- 严格 sweep：`v11_swp_m5_dtp` 62笔 / 日均0.3 / WR51.6% / PF1.22 / $263.80，盈利但低频。
- 放宽 sweep：`v11_swp_m5_loose` 1294笔 / 日均7.2 / WR50.5% / PF0.97 / $1.44，高频但爆亏。
- 放宽 sweep + 1.5区间TP：1791笔 / 日均9.9 / WR51.0% / PF0.99 / $1.44，增加目标距离无效。

结论不变：BTC 单品种当前 SMC/OB/sweep 框架无法同时满足 PF>2 和日均>3；严格信号能盈利但低频，放宽信号会被 spread/risk 和噪音吞掉。

## Round4-Round8 追加：BTC M5 日均>1 + PF>2 + 盈利6000目标

用户将 BTC M5 单腿目标更新为：盈亏比 > 2、日均交易 > 1、盈利至少 6000。

完成事项：

- 从 MT5 `20260520.log` 中解析 `V11-BTC-M5` 195 笔完整交易链路，导出 `research/notes/v11_btc_m5_trades_20260520.csv`。
- 新增小时仓位加权参数：`InpLowRiskHours / InpLowRiskHourMult / InpHighRiskHours / InpHighRiskHourMult`，默认不影响旧策略。
- 新增并回测 Round4-Round8 策略，核心记录见 `research/notes/2026-05-20_v11_btc_m5_log_round4_round8.md`。

关键发现：

- 基线右尾来自 `MARKET_CLOSE/DTP`，26 笔贡献 +58.79R；亏损端 112 笔 SL 贡献 -84.77R。
- PF>2 的核心小时约为 `12,14,16,20,23`，但这组只有约 50 笔/180天，无法单独满足日均>1。
- `15` 时段 R 值为正，但放大仓位后实际资金亏损，是高仓毒点。
- 低仓倍数低于约 0.15 后，订单常因最小手数/最小风险过滤消失，无法“保频”。

最好结果：

- `v11_r6_core_l15`: 145 笔 / 日均0.8 / WR48.3% / PF1.82 / $2052.45，质量最好但日均不达标。
- `v11_r7_freq_profit`: 174 笔 / 日均0.97 / WR50.6% / PF1.58 / $2979.65，利润最高但严格日均不达标。
- `v11_r8_hw_fix15`: 185 笔 / 日均1.03 / WR51.9% / PF1.38 / $2099.87，当前最实用但 PF 未达标。

实事求是结论：当前 BTC M5 OB/sweep 框架尚未找到同时满足 PF>2、日均>1、盈利>=6000 的单腿策略。继续加杠杆会先放大残余亏损簇，不能解决 PF 瓶颈。

## Round9-Round11 追加：入场质量加权

基于 Round6-Round8 的价格日志继续分层，新增了入场质量仓位乘数：

- 晚确认：`InpLateBounceSec / InpLateBounceMult`
- bounce 甜点：`InpBounceSweetMinPct / InpBounceSweetMaxPct / InpOutsideBounceSweetMult`
- 风险档：`InpBadRiskMin / InpBadRiskMax / InpBadRiskMult / InpLargeRiskMin / InpLargeRiskMult`

关键日志规律：

- `bounce_sec > 30` 的确认整体亏损。
- `bounce_ob=0.26-0.28` 最强，过浅/过深都差。
- `risk=150-200` 美元是坏档，`risk>=300` 大结构更容易贡献右尾。
- `16/20` 在最新高仓路径里不稳定，`12/17` 更稳，`13/14/23` 只能谨慎使用。

最好结果：

- `v11_r9_quality_soft`: 169 笔 / 严格日均0.94 / WR52.7% / PF2.05 / $1284.15。首次证明 PF>2 可达，但频率不足。
- `v11_r11_qsoft_add1120`: 172 笔 / 严格日均0.96 / WR51.2% / PF2.08 / $1391.86。PF 最好，但仍低频。
- `v11_r10_qsoft_6k`: 185 笔 / 严格日均1.03 / WR53.5% / PF1.43 / $4001.60。本轮余额最高，但未达 PF 和 $6000。

补频结论：

- 低仓从 0.35 提到 0.45/0.55 能把交易数推到 186-190，但 PF 降到 1.55-1.58。
- 放松质量降权或放大 13/14 时，交易数和余额会上升，但 PF 回到 1.28-1.64。
- 当前 BTC M5 单腿仍未找到同时满足 PF>2、日均>1、盈利>=6000 的配置。下一步需要新增 M15/H1 真动能确认或入场后 5-15 分钟 no-progress 管理，而不是继续调仓位。

详细记录见 `research/notes/2026-05-20_v11_btc_m5_log_round9_round11.md`。
