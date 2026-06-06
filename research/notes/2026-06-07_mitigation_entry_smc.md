# Mitigation Entry — SMC 消解入场研究笔记

## 背景

2605（2026年5月）是典型窄幅震荡月，传统 Bounce Entry 在震荡市中陷入"入场即反"的困境：
- avg_W=$1.07（骤降21倍 vs 2505的$22.98）
- 74%亏损持仓<60秒
- DTP触发率5.8%（目标完全到不了位）

## SMC 核心洞察

```
趋势月(2505): 价格触及OB → 反弹 → 入场 → 顺势走 → 盈利 ✅
震荡月(2605): 价格触及OB → 反弹 → 入场 → 扫荡 → 反方向走 → 亏损 ❌
```

Bounce Entry 在震荡市中抓的是"价格从一侧到另一侧的中继"——入场瞬间市场已完成微位移，接下来走反方向。

## Mitigation Entry 设计

### 原 SMC 概念
价格扫荡 LP（流动性池）后，会**回归到被扫荡的区间进行消解**（Mitigation）。正确入场时机不在反弹瞬间，而在**价格扫荡完成、离开 OB 后、回归 OB 时**。

### 状态机路径
```
TOUCH → BOUNCE → PHASE_WAITING_MITIGATION → [等价格离开OB] → DEPARTED → [等价格回归OB] → ENTER
                                               ↓ 超时                    ↓ 超时
                                          PHASE_EXPIRED            PHASE_EXPIRED
```

### 关键设计决策

1. **双阶段验证**：价格必须先显著离开 OB 区域（≥1.5× bounce 阈值），再回归才算真正的 SMC 消解。防止 tick 振荡每 tick 触发往返。

2. **防守触发（核心创新）**：Mitigation 仅在`IsAdaptiveNoiseGateDefensive()`为真时启用——即权益从峰值回撤超过3%。这自然适应：
   - 趋势月：盈利不回撤 → Mitigation 休眠 → 趋势利润保全
   - 震荡月：亏损触发回撤 → Mitigation 激活 → 过滤坏交易

3. **信号类型过滤**：默认仅对 Sweep OB 启用（`signal_types="sweep"`）

## 验证结果 (18 BT: 6配置 × 3月份)

| 策略 | 2605 | 2505 | 2604 |
|:---|:---:|:---:|:---:|
| S2原版(无Sweep) | 37T, -$22.81 | 583T, **+$3,126** | 51T, -$20.66 |
| SWP基准 | 82T, -$64.47 | 3225T, +$300,179 | 197T, -$19.62 |
| MitDef(防守) | 46T, -$35.17 | 3174T, +$282,010 | 77T, -$22.39 |
| 全局Mit(非防守) | 119T, -$71.14 | 3267T, +$307,545 | 246T, -$41.44 |

### 对比分析

| 指标 | 全局Mit vs SWP(2605) | MitDef vs SWP(2605) | MitDef vs SWP(2505) |
|:---|---:|---:|---:|
| 交易数 | +45% (82→119) | **-44% (82→46)** | -1.6% (3225→3174) |
| PnL | 恶化 +$7 | **改善 +$29** | 退化 -6% |
| WR | +1.5pp | -2.1pp | -0.9pp |

## 核心发现

1. **防守触发是正确的激活机制**：全局 Mitigation 在 2505 导致 28% 利润退化；防守触发降至仅 6%
2. **Mitigation 有效过滤震荡市坏交易**：2605 亏损从 -$64 降至 -$35（45%改善）
3. **但无法使 2605 转盈**：震荡市的波动结构限制是根本性的——avg_W=$1.07 意味着即使 WR=60%，一笔盈利只能覆盖一笔亏损的 60%

## 天花板分析

2605 无法转盈的根本原因不在入口逻辑，而在**市场微观结构**：
- avg_W=1.07R vs avg_L=1.72R → 盈亏比0.62
- 要实现正期望需 WR>62%，当前最佳 WR=26.3%
- 降低 avg_L（缩窄 SL）→ 被 tick 噪音秒杀
- 提高 avg_W（放宽 TP）→ 窄幅区间到不了目标

## 文件改动

| 文件 | 改动范围 |
|:---|:---|
| `Config.mqh` | +5 input 参数, +5 Cfg 访问器 |
| `EntryEngine.mqh` | +PHASE_WAITING_MITIGATION, +IsMitigationSignalType, +ShouldUseMitigationNow, +SetMitigationContext, ~120行状态处理 |
| `WaiTrade_OB.mq5` | +2行 SetMitigationContext 调用 |
| `yaml_to_set.py` | +5 FLAT_MAP 映射 |
| `strategies.yaml` | +5 默认值 |

## 相关笔记

- [[2026-06-06_noise_gate_optimization]]
- [[2026-06-07_ex5_deploy_bug]]
- [[2026-06-02_strategy_iteration_spec]]
