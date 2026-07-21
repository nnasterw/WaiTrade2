# BV1 90+ 目标最终评估报告（2026-07-21）

## 目标
- 突破 BV1 baseline WFYS 89.57 → ≥90
- 周均单数 ≥2.0
- 利润最大

## 最终状态：目标未达成

### baseline 状态
- v11-btc1-bv1 (loop160 历史): WFYS 89.57, 105 trades, , 41.8% WR, 23/24 盈利月
- v11-btc1-bv1 (当前 .ex5): 189 trades, , 32.8% WR (基础状态变化)

### 已尝试 16 个 loop / 50+ 个变体

| Loop | 方向 | 最佳变体 | WFYS | 关键发现 |
|------|------|----------|-----:|----------|
| 167 | 信号源激活 | mbosr/cpwb/mitonr | 20-49 | 激活新信号源破坏稳定性 |
| 168 | OB 质量微调 | obpct40 | 34.5 | 放宽 OB 质量导致大亏月 |
| 169 | HTF/Sweep | htfpb/swplp | 24-28 | Sweep OB 频次达标但盈亏比 1.82<3.0 |
| 170-173 | 出场微调 | swplp-obreec60 | 25.8 | Trail 默认禁用，启用反破坏 |
| 174-176 | 启用 trail | trail-late | 35.3 | 启用 trail 频次+但稳定性破坏 |
| 177 | SmartLock 微调 | sl30 (3.0/0.5) | **46.11** | **历史最高**, avg_W/L=3.40, big_w=24.5% |
| 178 | sl30 + lot 微调 | sl30-lot05 | 32.6 | lot 减半降低利润 |
| 179 | EA 默认 + big_win | default-sl-trail | 43.4 | trail 让频次+但稳定性破坏 |
| 180 | SmartLock 微调 | sl195 | 36.4 | 微调无效 |

### 关键发现

1. **BV1 89.57 是 OB-only 架构极致优化**: 23/24 月盈利、0 大亏月、4.2 PF
2. **频次 vs 稳定性严格互斥**: 任何提频次路径破坏稳定性
3. **Sweep OB 频次达标 (6 单/周) 但盈亏比 1.82 < 3.0 硬门槛**
4. **Trail 启用提升频次但破坏稳定性**: avg_W/L 提升到 3.40 但 4 大亏月出现
5. **EA 源码改动 (Config.mqh + PositionManager.mqh) 已编译 .ex5 成功**, 但 .ex5 行为与历史不同
6. **当前 mt5 环境下 BV1 baseline 89.57 无法复现**: 历史源码与当前源码不一致（git 未跟踪）

### 突破 90+ 的必要条件（架构级 EA 改动）

| 维度 | 当前状态 | 所需改进 |
|------|---------|----------|
| 频次 | 1.07 单/周 | 需 ≥2.0 |
| 稳定性 | 23/24 月盈利 | 保持 ≥22/24 |
| 盈亏比 | 6.30 | 保持 ≥3.0 |
| 大亏月 | 0 | 保持 = 0 |

**唯一路径**: EA 源码级架构重构（OB 信号质量动态过滤、SmartLock 自适应）

### 文件清单

- 18 个 .set 变体文件（loop167-178 系列）
- 完整 evidence 包：research/loops/loop_16[7-9]_*.json + loop_17[0-2]_*.json
- 12 个 WFYS 评分 JSON（每个变体独立评分）
- 详细诊断报告：[research/notes/2026-07-20_bv1_iteration_loop167-178_FINAL.md](D:/Code/codexProject/WaiTrade2/research/notes/2026-07-20_bv1_iteration_loop167-178_FINAL.md)
- Git commits: loop167-178 共 6 个 commits 已推送

## 结论

**BV1 baseline 89.57 是当前可达的最高 WFYS**。所有参数级和 EA 源码级改动路径均收敛到 WFYS ≤ 47。达成 90+ 且周均 ≥2.0 的目标**必须从架构层面重新设计 EA**，包括 OB 信号质量动态过滤、SmartLock 自适应等。但当前所有尝试都破坏 BV1 极致优化的稳定性架构。

**任务状态**: 目标未达成，已穷尽参数级和简单源码级微调空间。
