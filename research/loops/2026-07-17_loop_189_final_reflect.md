# Loop 189 OB 评分系统启用 (最终)

**日期**: 2026-07-17

## loop189 (enable_scoring + min_score)
| 变体 | Trade | WR | Balance | 结果 |
|------|-------|-----|---------|------|
| loop189-score-1 | 113 | 42.5% | \ | 与 baseline 同 (score=1 等效) |
| loop189-score-3 | 99 | 41.4% | \ | 减少单数 |
| loop189-score-5 | 12 | 41.7% | \ | 急剧减少 |

**核心发现**: 评分过滤仅减少单数 (不能增加), 期望的反向不成立

## 53 个假设最终汇总

| 维度 | 假设数 | 最高分 |
|------|--------|--------|
| 出场机制 (SL 微调) | 9 | **89.75** |
| 信号源 (FVG/MBOS/BCC) | 4 | 灾难 |
| 入场门槛 (bounce/strength) | 3 | 89.57 |
| BE 维度 | 3 | 89.75 |
| HTF shape | 3 | 89.75 |
| 其它架构 (pullback/ticknoise等) | 5 | < 89.75 |
| BarTF (M3) | 3 | 灾难 |
| BTC profile 启用 | 9 | 54.77 max |
| StrongAddOn | 3 | 84.x |
| 持仓时间 | 3 | 89.75 |
| SL buffer (BTC) | 3 | 40.72 |
| 多架构组合 | 6 | < 89.75 |
| OB body 要求放宽 | 3 | 81.22 max |
| OB score 阈值 | 1+ | 89.75 |
| OB scoring 系统启用 | 3 | 89.75 |
| **总计** | **53** | **89.75** |

## 关键洞察 (WFYS v2.2)

周单数阶梯式评分 (满分 3 分):
- < 2.0: 0 分
- 2.0-3.0: 1 分 (+1)
- 3.0-4.0: 2 分 (+2)
- >= 4.0: 3 分 (+3)

要 WFYS 90+ 必须 trade_count >= 210 (周均 2.0) -> 至少 +1 分
但 BTC profile 启用虽然单数到 200+, 月度稳定性破坏 (24月9月亏损) -> 其他模块暴跌

## 当前最佳

**v11-btc1-loop170-sl18p3** = WFYS **89.75** (magic=207173)
- Trade 113, WR 42.5%, Balance \
- vs bv1 baseline (89.57) +0.18 分
- vs 用户目标 90+ 差 0.25 分

## 突破 90+ 必须的 EA 源码级改动

按 wf-yhcl 标准 53 个假设完全确认结构上限.
唯一突破路径是 EA 源码级改动 (200-500 行) + 编译 + 部署:

1. **OB 检测算法** (改善 OB 质量)
2. **加仓架构** (loop164 addon 100% WR)
3. **替代 SmartLock 的新出场机制**
4. **BTC profile 月度稳定性增强**

## Token 用量归因
- 来源: codex_token_count
- 估算: Loop 189 总计 ~200K tokens

## 推送状态
- 11 commits pushed to nnasterw/WaiTrade2 main
- 完整 research/loops/ 笔记
- 完整 strategies.yaml 变体
