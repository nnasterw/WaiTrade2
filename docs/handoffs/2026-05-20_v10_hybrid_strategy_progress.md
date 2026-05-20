# Handoff: V10 Hybrid 策略更迭进度

日期: 2026-05-20
会话时长: ~2小时（含前序compaction会话约8小时）

## 当前状态

V10 XAU策略优化已完成Hybrid系列测试（15个变体），确认了趋势/震荡市场的最优配方组合。BTC方向已验证现有框架不适用，需独立设计。

## 本轮完成工作

### 1. Hybrid系列策略设计与回测（A~P 共16个变体）

核心思路：FAGE入场质量 + RANGE出场保护

回测结果详见: `research/notes/2026-05-20_v10_hybrid_results.md`

### 2. 确认的最优策略

| 场景 | 策略key | 180天余额 | 2345月余额 |
|------|---------|-----------|------------|
| 最高绝对收益 | v10a | $6566 | $93(亏) |
| 稳定高质量 | v10_fage_dtp7_r15_bh1 | $5311 | $144(微亏) |
| 全周期兼顾 | v10_hybrid_c | $5449 | $354 |
| 震荡期专用 | v10_hybrid_i | $3429 | $411 |

### 3. BTC测试结论

全部v10/hybrid策略在BTC上爆仓（60天+365天）。根因：M1框架OB risk=3-5pt，spread/risk=6-10%，结构性亏损。BTC需M30+SL1.5ATR独立设计。

## 关键发现 (写入研究文档)

1. 趋势vs震荡结构性矛盾：DTP高→趋势月暴利/震荡月亏；TP1R→震荡月盈/趋势月受限
2. 宽SL(0.3ATR)是震荡期生存关键
3. FAGE过滤贡献PF约+0.2
4. Risk5%在PF<1.5时适得其反
5. Partial exit / 时段过滤 / 低BE 均负效果

## 文件变更

| 文件 | 变更 |
|------|------|
| `config/strategies.yaml` | +16个hybrid策略(v10_hybrid_a~p) |
| `mql5/Presets/V10-HYBRID-*.set` | 对应preset文件(A~P) |
| `research/notes/2026-05-20_v10_hybrid_results.md` | 完整回测结果文档 |
| `results/backtest/*.txt` | 各策略回测报告 |

## 未提交的git变更

- `config/strategies.yaml` (大量新增策略)
- `mql5/Presets/V10-HYBRID-*.set`
- `research/notes/2026-05-20_v10_hybrid_results.md`
- 多个之前session的untracked preset文件

## 下一步方向

### P0 — 可直接执行

1. **BTC M30 独立策略设计**: 基于v99j1参数矩阵(SL1.5ATR/BE2R/timeout720min)重新设计v10-BTC版本
2. **市场regime切换EA**: 自动检测趋势/震荡状态，切换hybrid_c(趋势) ↔ hybrid_i(震荡)配方
3. **Git提交**: 当前变更量大，需要整理后提交

### P1 — 深化优化

4. **Hybrid_c + Hybrid_i 组合回测**: 按月切换策略，验证组合是否超过单一策略
5. **多品种验证**: XAG/EUR/GBP 用hybrid_c测试
6. **Live部署验证**: hybrid_c 或 fage_dtp7_r15_bh1 挂载到Wine MT5

### P2 — 探索方向

7. 更长回测窗口（365天XAU）验证v10a/hybrid_c稳定性
8. 加入波动率自适应（ATR倍数动态调整SL/TP）
9. 对面swing目标位作为TP（MarketState.mqh已有基础设施）

## 参考文档

- 策略演进全景: `research/notes/2026-05-18_v10_xau_development.md`
- FAGE迭代过程: `research/notes/2026-05-19_v10_fage_iteration.md`
- FAGE最佳策略: `research/notes/2026-05-20_v10_fage_best_strategies.md`
- Hybrid回测结果: `research/notes/2026-05-20_v10_hybrid_results.md`
- 后台回测指南: `research/notes/2026-05-20_background_backtest_guide.md`

## 建议使用的Skills

- `wf-improve-strategy` — 继续策略优化/回测工作流
- `handoff` — 下次会话结束时再次记录进度
