# V11 策略设计方案 — BTC SMC高频盈利策略

## 目标指标
- 品种: BTCUSDm
- 周期: 180天回测
- 胜率 > 60%
- 盈亏比 > 2
- 日均开单 > 3
- 盈利最大化

## 核心设计理念

### SMC盈利核心规律（从历史数据提炼）

1. **高质量OB = 高胜率**: OB strength ≥ 0.6 + 1H对齐 = 趋势方向确认
2. **Bounce确认 = 减少假突破**: 触及OB后等反弹确认，不盲目入场
3. **动能衰减离场 = 保护利润**: M1级别吞没/二推不破 → 及时止盈
4. **状态自适应 = 灵活应对**: 趋势态用trail追踪利润，震荡态用固定TP快进快出
5. **多并发 = 增加单数**: 适当放宽并发限制，配合短冷却期

### 从亏损中规避的核心因素

1. **止损太窄被噪音扫**: BTC需要 ≥ 1.5 ATR 的SL buffer
2. **逆势入场**: 强趋势中逆势OB成功率极低，必须严格过滤
3. **无浮盈亏损单拖太久**: timeout必须合理，无浮盈单早离场
4. **假OB**: displacement不够强、实体占比低的OB过滤掉

## V11 策略参数设计

### 方案A: V11-BTC-M15-TREND（趋势跟踪型）

**核心思路**: M15时间框架，顺势捕捉大趋势波段，放宽止盈让利润奔跑

| 参数类别 | 参数 | 值 | 理由 |
|---------|------|------|------|
| 时间框架 | bar_tf | 15 (M15) | BTC M5 spread占比仍高(~3%)，M15降至1.5%，信号更可靠 |
| OB检测 | displacement_bars | 5 | M15需要5根K线验证位移力度 |
| OB检测 | body_ratio | 0.55 | 稍高于默认，过滤影线过长的假OB |
| OB检测 | min_ob_strength | 0.5 | 保证OB质量 |
| OB检测 | ob_ttl | 20 | M15×20=5小时，BTC大波段OB有效期更长 |
| 入场 | entry_mode | 1 (bounce) | Bounce确认减少假突破 |
| 入场 | bounce_pct | 0.3 | 30%反弹确认，不太严格以增加单数 |
| 入场 | offset_guard | 0.1 | 10% offset防止追价 |
| 过滤 | filter_counter_trend | 1 | 开启逆势过滤 |
| 过滤 | filter_max_risk_atr | 3.0 | risk超3倍ATR不入场 |
| 过滤 | filter_min_risk_atr | 0.3 | risk太小=OB太薄，容易被穿 |
| 过滤 | require_1h_alignment | 1 | 1H方向对齐，提高胜率 |
| 止损 | sl_buffer_atr | 1.5 | BTC需要充足SL空间 |
| 止盈 | tp_mode | 0 (R-based) | 固定R倍目标 |
| 止盈 | tp_r | 3.0 | 目标3R，配合60%+胜率=PF>2 |
| 保本 | be_trigger_r | 1.5 | 1.5R触发保本，保护利润 |
| 保本 | be_offset_r | 0.3 | 保本偏移，避免被回撤扫出 |
| DTP | dtp_trigger_r | 2.5 | 2.5R触发动态止盈 |
| DTP | dtp_trail_r | 0.8 | 动态追踪距离 |
| 动能衰减 | decay_enabled | 1 | 开启M1动能衰减检测 |
| 动能衰减 | decay_min_profit_r | 1.0 | 至少1R利润才考虑衰减离场 |
| 超时 | timeout_bars | 48 | 48×15min=12小时，BTC单笔合理持仓 |
| 并发 | max_concurrent | 4 | 允许4个并发持仓 |
| 冷却 | cooldown_bars | 2 | 2根M15=30分钟冷却 |
| 状态 | adaptive_state | 1 | 状态自适应：趋势用trail，震荡用固定TP |
| 评分 | score_threshold | 3.0 | 最低3分入场 |

### 方案B: V11-BTC-M5-SCALP（高频剥头皮型）

**核心思路**: M5时间框架，快进快出，用数量取胜，严格控制每单风险

| 参数类别 | 参数 | 值 | 理由 |
|---------|------|------|------|
| 时间框架 | bar_tf | 5 (M5) | 更多信号机会，需更严格过滤 |
| OB检测 | displacement_bars | 3 | M5位移3根足够 |
| OB检测 | body_ratio | 0.5 | 标准实体占比 |
| OB检测 | min_ob_strength | 0.6 | 提高门槛补偿M5噪音 |
| OB检测 | ob_ttl | 30 | 30×5min=2.5小时 |
| 入场 | entry_mode | 1 (bounce) | Bounce确认 |
| 入场 | bounce_pct | 0.25 | 25%快速确认 |
| 入场 | offset_guard | 0.05 | 5% offset |
| 过滤 | filter_counter_trend | 1 | 逆势过滤 |
| 过滤 | filter_max_risk_atr | 2.5 | 更严格的风险上限 |
| 过滤 | filter_min_risk_atr | 0.5 | M5最小风险更高避免spread杀 |
| 过滤 | require_1h_alignment | 1 | 1H对齐 |
| 止损 | sl_buffer_atr | 1.0 | M5止损更紧 |
| 止盈 | tp_mode | 0 (R-based) | R倍止盈 |
| 止盈 | tp_r | 2.0 | 快速2R止盈 |
| 保本 | be_trigger_r | 1.0 | 1R快速保本 |
| 保本 | be_offset_r | 0.2 | 小偏移 |
| DTP | dtp_trigger_r | 1.5 | 1.5R动态追踪 |
| DTP | dtp_trail_r | 0.5 | 紧追踪 |
| 动能衰减 | decay_enabled | 1 | 开启 |
| 动能衰减 | decay_min_profit_r | 0.5 | 0.5R就考虑衰减离场 |
| 超时 | timeout_bars | 60 | 60×5min=5小时 |
| 并发 | max_concurrent | 5 | 更多并发 |
| 冷却 | cooldown_bars | 3 | 15分钟冷却 |
| 状态 | adaptive_state | 0 | 不自适应，统一快出 |
| 评分 | score_threshold | 3.5 | 更高门槛 |

### 方案C: V11-BTC-M5-HYBRID（混合自适应型）⭐ 推荐

**核心思路**: M5框架增加信号密度，状态自适应切换策略行为，结合趋势追踪和震荡快出

**创新点**:
1. **入场OB区间中下位**: bounce_pct=0.2 + offset_guard=0.15 → 在OB下半区确认入场
2. **浮盈亏损单早离场**: decay_min_profit_r=0.3 极低门槛触发衰减检测 → 有浮盈就保护
3. **趋势态放利润**: DTP 3R + trail lock 让大单跑满
4. **震荡态快止盈**: 固定TP 1.5R 快进快出
5. **OB Height TP**: tp_mode=2 用OB量度移动作为震荡态目标
6. **多并发+短冷却**: max=5, cooldown=2 增加开单频率

| 参数类别 | 参数 | 值 | 理由 |
|---------|------|------|------|
| 时间框架 | bar_tf | 5 (M5) | 高频信号源 |
| OB检测 | displacement_bars | 3 | 快速检测 |
| OB检测 | body_ratio | 0.5 | 标准 |
| OB检测 | min_ob_strength | 0.55 | 平衡质量和数量 |
| OB检测 | ob_ttl | 25 | ~2小时有效期 |
| OB检测 | ob_merge | 1 | 合并相邻OB减少重复 |
| 入场 | entry_mode | 1 (bounce) | 确认入场 |
| 入场 | bounce_pct | 0.2 | 20%在OB中下部入场 |
| 入场 | offset_guard | 0.15 | 15% guard防追价 |
| 过滤 | filter_counter_trend | 1 | 逆势过滤 |
| 过滤 | filter_max_risk_atr | 3.0 | |
| 过滤 | filter_min_risk_atr | 0.4 | 避开spread杀 |
| 过滤 | require_1h_alignment | 1 | 大级别确认 |
| 止损 | sl_buffer_atr | 1.2 | 适中SL空间 |
| 止盈(趋势) | tp_r | 3.0 | 趋势态目标3R |
| 止盈(震荡) | tp_mode | 2 (OBHeight) | 震荡用OB量度TP |
| 止盈(震荡) | ob_height_mult | 1.5 | 1.5倍OB高度 |
| 保本 | be_trigger_r | 1.0 | 1R保本 |
| 保本 | be_offset_r | 0.2 | |
| DTP | dtp_trigger_r | 2.0 | 2R开始追踪 |
| DTP | dtp_trail_r | 0.6 | 中等追踪距离 |
| 动能衰减 | decay_enabled | 1 | 开启 |
| 动能衰减 | decay_min_profit_r | 0.3 | 极低门槛，有浮盈就保护 |
| Trail | trail1_trigger_r | 1.5 | 1.5R第一级trail |
| Trail | trail1_lock_r | 0.8 | 锁定0.8R |
| Trail | trail2_trigger_r | 2.5 | 2.5R第二级 |
| Trail | trail2_lock_r | 1.5 | 锁定1.5R |
| Trail | trail2_lock_mult | 0.6 | 60%回撤锁定 |
| 超时 | timeout_bars | 50 | ~4小时 |
| 并发 | max_concurrent | 5 | 高并发 |
| 冷却 | cooldown_bars | 2 | 10分钟冷却 |
| 状态 | adaptive_state | 1 | 状态自适应 |
| 评分 | score_threshold | 3.0 | 适中门槛 |
| 方向 | trade_direction | 0 (both) | 双向交易增加单数 |

## 实施步骤

### Phase 1: 配置文件准备
1. 在 `config/strategies.yaml` 添加 v11a/v11b/v11c 三个方案定义
2. 运行 `yaml_to_set.py` 生成 .set 文件
3. 编译EA确认无错误

### Phase 2: 回测验证（三方案对比）
4. 运行三方案 BTC 180天回测
5. 分析对比：WR、PF、日均单数、最大回撤、利润
6. 基于结果选择最优方案

### Phase 3: 参数微调
7. 对最优方案进行参数微调（±10-20%范围）
8. 重点调优：bounce_pct、be_trigger_r、tp_r、decay_min_profit_r
9. 最终确定v11定版参数

### Phase 4: 鲁棒性验证
10. 多时间段回测（分3个60天段）验证一致性
11. 不同市场条件下表现评估

## 风险评估

- M5+BTC的spread占比约3-5%，是结构性劣势 → 用min_risk_atr过滤太薄的OB
- BTC 24h交易但亚洲时段波动小 → 不做session过滤，让EA自动通过quality过滤
- 高并发5个持仓 = 单次最大风险5% → 需配合严格的BE保本
- 日均>3单在M5上可行（v10 FAGE在XAU M5已实现3.3单/日）

## 预期表现

基于v10 FAGE在XAU M5的表现(WR71%/PF2.01/日均3.3)，BTC由于波动更大：
- 方案A (M15): 预期WR 62-68%, PF 1.8-2.5, 日均 2-3单
- 方案B (M5 Scalp): 预期WR 58-65%, PF 1.5-2.0, 日均 4-6单
- 方案C (M5 Hybrid): 预期WR 60-68%, PF 2.0-2.5, 日均 3-5单 ⭐

方案C是最佳平衡点：M5提供足够信号密度，状态自适应在不同市况切换策略行为。
