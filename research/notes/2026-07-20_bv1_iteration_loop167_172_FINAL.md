# BV1 迭代总结（2026-07-20，loop167-172）

## 目标
突破 BV1 baseline WFYS 89.57 → ≥90，且周均单数 ≥2.0。

## Baseline 现状
- v11-btc1-bv1 (loop160): 110 trades, 41.8% WR, \, WFYS 89.57
- 1 硬失败：720d周均单数 1.07（< 2.0 门槛）
- top_drags：趋势利润结构 11.57/15、风险质量周单数分级 21.67/25、稳定性 26.33/30

## 已尝试 12 个变体（5 个 loop，36 次 720d 回测）

| Loop | 变体 | 单变量方向 | 720d 单数 | 周均 | 720d 余额 | WFYS |
|------|------|-----------|----------:|-----:|----------:|-----:|
| 167 | mbosr | MicroBOS Retest 开启 | 189 | 1.84 | \ | 20.72 |
| 167 | cpwb | ConfirmPullback 开启 | 33 | 0.32 | -\.74 | 48.54 |
| 167 | mitonr | MitigationEntry 关闭 OnlyDefensive | 185 | 1.80 | \ | - |
| 168 | obreec0 | OB 重入冷却 30→0 | 28 (90d) | - | -\.89 (90d) | - |
| 168 | obpct40 | min_ob_body_pct 50→40 | 174 | 1.69 | \ | 34.54 |
| 169 | htfpb | HTF Pullback 开启 + max_lot 0.5 | 265 | 2.57 ✓ | \ | 27.87 |
| 169 | swplp | sweep_pos_mult 0→0.5 | 591 | 5.74 ✓ | \ | 24.34 |
| 170 | obreec60 | OB 重入冷却 30→60 | 529 | 5.14 ✓ | \ | 25.79 |
| 170 | maxent2 | max_entries_per_ob 3→2 | 32 | 0.31 | -\ | - |
| 171 | mrsr7 | min_risk_spread_ratio 5→7 | (90d 180) | - | - | - |
| 171 | trail2 | Trail2 2.0/1.5（被默认禁用） | 621 | 6.03 | \ | - |
| 172 | bbmin30 | bad_bounce_min_pct 0.22→0.30 | 73 | 0.71 | \.28 | - |

## 核心结论

1. **BV1 89.57 是当前 OB-only 架构的稳定上限**：任何放宽/激活新入口都破坏稳定性
2. **Sweep OB（swplp）能达成 6 单/周，但盈亏比 1.82 << 3.0 硬门槛**：avg_W/L = \.2/\.7
3. **稳定性破坏是不可逆的**：12 个变体中只有 BV1 baseline 1 个 WFYS ≥ 80
4. **2024-10、2025-12、2026-03 是 sweep 信号必然大亏的月份**：与 OB 路径相反
5. **Trail 参数默认禁用**（InpTrailLevels=0）：出场机制已优化到 BE+DTP+结构锁利

## 突破 90+ 的必要条件（架构级改动）

要突破 BV1 89.57 必须满足：
1. **频次 ≥2.0 单/周**：新增入场信号（Sweep/HTFPB/MicroBOS）但保持稳定性
2. **保持稳定性 ≥22/24 盈利月、≤2 亏损月、0 大亏月**
3. **盈亏比 ≥3.0**：sweep 信号盈亏比仅 1.82，需源码级优化出场

## 下一步建议

- **架构级 EA 源码改动**：
  - 添加 sweep 信号的多重确认（OB + sweep + HTF 顺势）
  - 改进 sweep 入场的 SL/TP（让 avg_W/L > 3.0）
  - 大赢单放大器（R≥3 锁 50% 继续 trail）
- **已识别风险**：BV1 baseline 已经接近架构极限，EA 改动需要大量测试
- **次优方案**：接受 BV1 89.57 作为当前最佳，仅做高频次但低 WFYS 的研究版

## 文件

- 12 个变体 .set：mql5/Presets/v11-btc1-loop16*.set
- 完整 evidence 包：research/loops/loop_16[7-9]_*.json, loop_17*.json
- 详细诊断报告：research/notes/2026-07-20_bv1_iteration_loop167_171_summary.md
