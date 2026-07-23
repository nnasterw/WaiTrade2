# 2026-07-23 最终进度报告

## 目标
WFYS 90+ 且周均 2+ 单

## 关键基础设施问题 (致命障碍)

所有 MT5 portable 终端 (mt5_portable_bt, mt5_portable_btc_bv1, mt5_portable_btc_trend111 等)
**仅有 2026.01-2026.07 的 tick 数据, 2024-2025 数据完全缺失**。

后果:
- Model 4 (Real Ticks) 720d 回测全部失败 ("回测失败或无数据")
- 历史基线 v11-btc1-bv1 (WFYS 89.57) 无法在当前环境复现
- 所有历史"突破"loop170 (89.75) 等都无法验证

## 临时方案
使用 Model 0 (Every tick generated from M1 OHLC bars):
- 修改 scripts/_loop_batch.py 添加 get_strategy_model() 函数从 YAML 读取 model 字段
- 每个新策略的 YAML 添加 `model: 0` 字段
- 接受 Model 0 数据不准确的现实

## 重大突破 (Loop 196)

**v11-btc1-loop196-bv1-clean-m0-bp22**:
- bounce_pct: 0.25 → 0.22 (放宽 OB 反弹确认)
- iron rule: 通过
- 720d 回测: **235 trades, weekly 2.06 ✓**, WFYS 26.27
- 净利: $230 (15% return)

这是首次达到 weekly 2+ 单的目标。

## 所有变体结果

| 变体 | 改动 | Trades | Weekly | Pass | WFYS | 净利 |
|------|------|--------|--------|------|------|------|
| **loop196-bp22** | bounce_pct 0.22 | 235 | **2.06** | **YES** | 26.27 | $230 |
| loop201-bp20 | bounce_pct 0.20 | 158 | 1.53 | NO | 47.33 | $3908 |
| loop204-bp20+bbmin20 | bp20 + bbmin20 | 177 | 1.72 | NO | 25.13 | $328 |
| loop219-req-bb | close confirm | 174 | 1.69 | NO | 35.28 | $1153 |
| bv1-clean-m0 (baseline) | - | 187 | 1.82 | NO | 27.62 | $475 |

## 迭代经验

### 单变量微调结果 (vs loop196 baseline)
- bounce_pct 0.20 (loop201): trade count 下降但 WFYS 提升
- bounce_pct 0.22 + 各种 entry filter (momentum/exhaustion/double-sweep/structure-confirm): 大多无效
- bounce_pct 0.22 + trail 3-stage: 无效
- bounce_pct 0.22 + DTP/BE/SL buffer changes: 无效
- bounce_pct 0.22 + drawdown control (rdd015): 太严, 6 trades total
- bounce_pct 0.22 + bb_close_confirm: 0 trades

### 关键参数
- **bounce_pct** 是 trade count 的关键控制
- bounce_pct 0.22 给出 ~235 trades
- bounce_pct 0.20 给出 ~158 trades
- bounce_pct 0.25 给出 ~187 trades

## WFYS 90+ 的根本障碍

Model 0 生成的 tick 数据与 Model 4 (real ticks) 差异巨大:
- 历史 89.57 baseline: 1 loss month, max DD 9%
- loop196 (Model 0): 8 loss months, max DD 58.6%
- WFYS 评分依赖 24月盈利月数 / Top3集中度 / 回撤 等指标
- Model 0 环境下这些指标必然偏差

## 建议的解决方案 (后续)

1. **恢复 2024-2025 tick 数据**: 通过 broker API 下载
2. **升级 EA 源码**: 让策略对 Model 0 数据更鲁棒
3. **改进 WFYS 评分**: 在数据缺失情况下使用更宽松的评分标准
4. **混合 Model 0 + Model 4**: 使用现有 2026 数据 + 部分历史数据

## 实际可达成的最佳状态

**iron rule 合规 + Model 0 环境下**:
- Weekly 2+: ✓ (loop196-bp22, 235 trades)
- WFYS: 26.27 (距离 90 还差 63.73)

**距离目标还有巨大gap**, 主要因为:
1. tick data 缺失导致 Model 0 偏差
2. WFYS 评分依赖 24月历史 (而我们只能测 6月)
3. Iron rule 严格 (不允许 hour/month filter)

## 代码改动

- scripts/_loop_batch.py: 新增 get_strategy_model() 函数, 支持 YAML model 字段
- config/strategies.yaml: 新增 24 个变体 (loop194-loop219)
- mql5/Presets/: 24 个新 .set 文件
- results/backtest/: 24 个新回测结果

## 建议

推荐下一步:
1. 修复 tick data 问题 (最关键)
2. 恢复 Model 4 后重新测试 loop196-bp22
3. 如果 Model 4 下 loop196 仍接近 89+ WFYS, 则每周均 2+ 是真正突破
4. 否则需要继续探索 entry quality filter
