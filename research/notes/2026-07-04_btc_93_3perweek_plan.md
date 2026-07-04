# BTC 93+ + 3+/周 攻关计划 (2026-07-04)

> 在 docs/CONTEXT.md 中已确立领域词汇。本文记录攻关计划与各方案状态。
> **执行原则**: 先做低风险改动, 效果不及预期再做高风险高潜力改动。

## 目标

| 指标 | 当前 (trend111) | 目标 | 差距 |
|------|----------------|------|------|
| WFYS 分数 | 87.34 | 93+ | +5.66 |
| 交易数量 | 117 / 24月 | 288+ | +171 |
| 周均交易 | 1.1 | 3+ | +1.9 |
| 大赢单比例 | 23.8% | 40%+ | +16.2% |
| 24月盈月 | 22/24 | 24/24 | +2 |
| 单笔 >3R | 9 笔 | 19+ | +10 |

## 关键发现 (从 docs/CONTEXT.md 与历史 research 总结)

1. **结构上限 87.34**: 200+ 参数变体测试 + 3 个代码级改造 (CheckFastSL, CheckLossCut, disable HTF) 均无法突破
2. **HTF Skip 屏蔽**: `htf_skip_dtp: true` + `htf_skip_trail: true` 让所有 DTP/Trail/NoMFE 改动无效 (这是之前 trend111-180 实验全部失效的根因)
3. **峰值 R 矛盾**: SL 交易的 peak_profit_r ≥ 2.0R, FastSL 阈值无法在不杀中等赢单的情况下生效
4. **此消彼长**: Trade 数量与 WFYS 分数是反比 — 趋势111 (1.1周, 87.34) vs 趋势186 (5周, 62.78)

## 方案汇总 (按风险与优先级)

### Phase 1 (低风险, 立即执行)

| 方案 | 类型 | 风险 | 预期 | 描述 |
|------|------|------|------|------|
| **B1. 启用 HTF 方向门控** | 参数调优 | 低 | 0.5-1.0 | trend64-66 验证过, 改善 big_win 0.5-1.0 |
| **B2. 启用 entry_momentum_filter** | 参数调优 | 低 | 0.3-0.5 | trend44-50 验证过, 微调 OB 触发 |
| **B3. 启用 entry_context_filter** | 参数调优 | 低 | 0.3-0.5 | qual 系列常用, 加强 context |
| **B4. 启用 entry_htf_shape_filter** | 参数调优 | 低 | 0.3-0.5 | qual 系列, trend111 已启用 |
| **B5. 启用 double_sweep_confirm** | 参数调优 | 低 | 0.5-1.0 | 双扫确认, 提高信号质量 |
| **B6. 启用 monthly_profit_lock** | 参数调优 | 低 | 0.5-1.0 | 锁住月度利润, 防止 24m 变损月 |
| **C1. v10_m3 family 移植** | 代码改造 | 中 | 3-5 | 已有 BTC 适配先例 (trend44/50/60/61), DTP 续持 |
| **C2. htf_skip_dtp=false + DTP** | 参数调优 | 低 | 1-2 | 让 DTP 在 BTC HTF 模式生效 |
| **C3. 启用 addon (StrongAddOn)** | 参数调优 | 低 | 1-2 | 趋势单加仓, 已有 BTC 支持 |
| **C4. FVG 单独通道** | 参数调优 | 中 | 0.5-1.0 | enable_fvg=true + 严格过滤 |

### Phase 2 (中风险, Phase 1 效果 < 1.0 时执行)

| 方案 | 类型 | 风险 | 预期 | 描述 |
|------|------|------|------|------|
| **D1. HTF 目标动态化** | 代码改造 | 中 | 2-4 | 改 HTF 目标计算 (ATR-based, swing + buffer) |
| **D2. LossCut 修复** | 代码改造 | 中 | 1-2 | peak_profit_r 实时追踪, bar 0 起算 |
| **D3. FastSL 修复** | 代码改造 | 中 | 1-2 | peak_profit_r 实时追踪 |
| **D4. 跨 timeframe 信号融合** | 代码改造 | 中 | 2-4 | OB M5 + 动量 M15 + 趋势 H4 综合 |
| **D5. 部分平仓优化** | 参数调优 | 低 | 0.5-1.0 | htf_partial_r 调整 |

### Phase 3 (高风险, Phase 1+2 累计效果 < 3.0 时执行)

| 方案 | 类型 | 风险 | 预期 | 描述 |
|------|------|------|------|------|
| **E1. 新高频信号模块 (突破)** | 代码改造 | 高 | 5-10 | 从零写 H4 break-and-retest 或 M15 momentum |
| **E2. XAU v10 移植 + 多策略组合** | 代码改造 | 高 | 5-10 | BTC OB 主 + XAU 趋势辅 |
| **E3. 完全重写策略逻辑** | 代码改造 | 高 | 10+ | 跳出 OB 范式, 全新入场信号 + 出场机制 |

## 执行策略

1. **先并行测试 Phase 1 全部 10 个方案** (回测 5min/个, 共 50min)
2. **若累计 < 1.0**: 进入 Phase 2 (代码改造)
3. **若累计 < 3.0**: 进入 Phase 3 (根本性重构)
4. **每阶段结束**: 更新 CONTEXT.md, 记录新术语与决策
5. **关键决策 (如达到 93+ 或 3+/周)**: 创建 ADR

## 已完成实验 (作为基线)

- trend1-200: 200+ 参数变体
- CheckFastSL, CheckLossCut, disable HTF: 3 个代码改造
- WFYS bug fix + 24m attribution fix
- 全 M1/M3/M5 timeframe 测试
- 全 HTF pullback + FVG + Sweep 测试

## 期望路径

```
Phase 1 (B + C 低风险)  → 预期 score 87.34 → 89-90
         (若不足 1.0 增益)
Phase 2 (D 中风险代码)  → 预期 score → 90-92
         (若不足 3.0 增益)
Phase 3 (E 高风险重构)  → 预期 score → 93+
```

## Token 状态

- 本轮: 0 (新开始)
- 累计: ~9.1M (历史)
- 预算: 无限制

## References

- `docs/CONTEXT.md` — 领域词汇表
- `research/notes/2026-07-02_v11-btc1-trend_wfys_iteration.md` — 上一轮详细数据
- `research/notes/2026-07-04_btc_3perweek_final.md` — 本轮 (1.1/周) 攻关总结
