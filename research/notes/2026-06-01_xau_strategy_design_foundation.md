# XAU 策略设计基础文档

## 概述

本文档综合以下研究来源，形成 XAU 策略参数设计的基础参考：

- `2026-05-30_xau_qs_non_hindsight_followup.md` — 续测四：非后见之明过滤全扫描
- `2026-05-30_xau_qs_defense_verification.md` — 防守方案 30d/180d 对照
- `2026-05-29_zd_virtual_stop_optimization.md` — ZD 虚拟止损优化
- 0528-0529 Live Trade 完整清单与出场分类
- 779 个 XAU 回测结果的汇总分析
- `config/strategies.yaml` 全策略参数表
- `OBDetector.mqh` / `PositionManager.mqh` / `SignalEngine.mqh` 代码分析

**核心约束**：任何候选必须同时满足 (1) 30天窗口从 $200 盈利, (2) 180天不显著退化（不低于基线 $2,396.58 的 80%）。

---

## 第一部分：策略架构总览

### 两条策略线的根本差异

| 维度 | ZD（振荡腿） | QS（趋势腿） |
|------|-------------|-------------|
| 胜率基线 | 72.5% (720d) | 57% (720d) |
| 盈亏比基线 | ~0.4 (低) | ~1.2 (中) |
| 持仓管理 | DTP 8.0R, 无 Trail | 固定 TP 1.5R, Trail 1.0/2.5R |
| BE 参数 | 0.25R/0.08R（保守保本） | 0.5R/0.4R（宽松保本） |
| 最大并发 | 3 | 14 |
| 每OB最大入场 | 1 | 20 |
| 核心保护 | 宽DTP让利润奔跑 | 高频小盈利复利 |
| 最大回撤 | 较低 | 较高 |
| 弱点场景 | 强趋势中逆势 | 弱趋势中过度开火 |

**关键结论**：两条策略的胜率结构完全不同，参数不能互套。ZD 改进方向是 VSL 保留大赢单，QS 改进方向是入场质量过滤减少弱时段亏损。

### 分级参数体系

所有参数分为三个管理层次：

```
Tier 1: 全局硬门（永远生效）
  - 最低 OB 质量要求（bounce、body%、strength）
  - 硬止损（灾难保护）
  - 最大风险/ATR

Tier 2: 状态依赖门（仅在特定市场状态激活）
  - 低余额降权
  - 运行时防御
  - 月度亏损/利润锁定
  - 态势过滤（趋势/震荡切换）

Tier 3: 软权重（持续生效但不断然阻断）
  - Bounce 深度软权重
  - 确认位置软权重
  - 重入次数软权重
  - 坏簇降权
```

**0529 崩盘的根本教训**：Tier 3 的权重调整在极端行情中不足以阻止失血；Tier 2 的状态门触发太晚（余额已跌破 $250）；Tier 1 的全局门在 QS 中不存在（max_entries=20，cooldown=0）。改进方向是强化 Tier 1 的硬门，并将 Tier 2 的触发阈值前移。

---

## 第二部分：止损甜点值

### 核心证据

#### 0528-0529 Live 出场分类（35 笔入场）

| 类别 | 数量 | 占比 | 特征 |
|------|------|------|------|
| 实体突破（真实止损） | 20 | 62.5% | 出场价精确等于 SL 水平 |
| 影线刺破（假止损） | 7 | 21.9% | 出场价明显差于 SL 水平（反向滑价） |
| 手动平仓 | 5 | 15.6% | 人工干预 |
| 持仓未知 | 3 | — | 日志截止时未平 |

**影线刺破的价差分布**（7 笔）：

| 交易 | SL改价 | 出场价 | 价差(USD) | 价差(R倍数) | 证据强度 |
|------|--------|--------|-----------|-------------|----------|
| #15 0529 Buy 0.04 | 4513.029 | 4512.737 | -0.292 | **0.42R** | 强 |
| #5 0528 Buy 0.09 | 4468.866 | 4468.707 | -0.159 | **0.23R** | 中 |
| #12 0528 Buy 0.01 | 4471.068 | 4470.972 | -0.096 | **0.14R** | 中 |
| #8 0528 Buy 0.01 | 4471.052 | 4470.980 | -0.072 | **0.10R** | 中 |
| #23 0529 Buy 0.09 | 4512.163 | 4512.082 | -0.081 | **0.12R** | 强 |
| #19 0529 Buy 0.02 | 4513.478 | 4513.422 | -0.056 | **0.08R** | 弱 |
| #24 0529 Buy 0.04 | 4513.378 | 4513.357 | -0.021 | **0.03R** | 弱 |

- 影线刺破的最大偏移为 **0.42R**（#15），最小为 0.03R
- 0.42R 以上覆盖 **100%** 的假止损
- 0.25R 以上覆盖 **85.7%**（6/7）
- 0.15R 以上覆盖 **71.4%**（5/7）

#### ZD 虚拟止损回测（720 天，$200 起）

| 候选 | VSL确认Bar | 硬缓冲R | 720d余额 | vs ZD基线 | PF |
|------|-----------|---------|----------|-----------|-----|
| zd (基线) | 无 VSL | — | $30,450 | 基准 | 1.95 |
| **zd-vsl-r1** | **1** | **1.0** | **$42,516** | **+39.6%** | **2.25** |
| zd-vsl-hold | 1 | 0.5 | $113 (30d) | 淘汰 | 0.59 |

- VSL 1 bar M1 确认 + 1.0R 硬缓冲在 ZD 上表现最佳
- 0.5R 缓冲（vsl-mid）未在 ZD 独立测试，但在 QS 的 vsl-hold 中组合测试表现差
- 0.25R 缓冲（vsl-tight）在 ZD 未测试，在 QS 的 core-dir-vsl 中 720d $9,629（远低于 ZD 表现）

#### OB 外 SL 缓冲

| 参数 | 当前 QS 默认 | 测试范围 | 最优值推测 |
|------|-------------|---------|-----------|
| SLBufferATR | 0.0 | 0-1.0 | **0.3-0.5 ATR** |
| MaxRiskATR | 3.0 | 1.5-5.0 | **2.0-2.5 ATR** |
| DefensiveMaxRiskATR | 0.0(禁用) | — | **1.5 ATR** |

### 止损参数推荐

#### XAU 统一推荐

```
# ===== 硬止损 =====
InpSLBufferATR: 0.3              # OB外缓冲 0.3 ATR（覆盖大多数影线）
InpMaxRiskATR: 2.5               # 最大风险不超过 2.5 ATR

# ===== 虚拟止损确认 =====
InpVirtualSLConfirmBars: 1        # 1 根 M1 确认
InpVirtualSLConfirmTF: 1          # M1 确认周期
InpVirtualSLHardBufferR: 0.5      # 0.5R 硬缓冲（覆盖 85%+ 假止损）
InpVirtualSLRequireBody: true     # 要求实体突破而非影线

# ===== 影线加速退出 =====
InpWickExitMaxPenetrations: 3     # 3 次影线穿透后加速
InpWickExitConfirmBars: 1         # 加速后 1 bar 收盘确认
```

#### ZD 专用调整（宽止损，VSL 需要更大缓冲）

```
InpVirtualSLHardBufferR: 1.0      # ZD 的 OB 间距大，需要更大缓冲
InpSLBufferATR: 0.5              # 硬止损缓冲也放宽
```

**依据**：
- Live 数据：0.5R 覆盖 85.7% 的假止损，1.0R 覆盖 100%
- ZD 回测：1.0R 缓冲 + 1 bar 确认为最优（720d +39.6%）
- QS：0.5R 缓冲 + 1 bar 确认是合理的起点（需独立回测验证）
- 最大风险 2.5 ATR 是基于 XAU M1 平均 ATR ~0.8-1.2 美元计算的，2.5 ATR 约 2-3 美元，在 0.01 lot 下风险可控

---

## 第三部分：提损时机甜点值

### BE 触发甜点

#### 各策略 BE 参数对照

| 策略簇 | BE Trigger R | BE Lock R | 适用场景 | 180d/720d表现 |
|--------|-------------|-----------|---------|--------------|
| FAGE 基类 | 0.25 | 0.08 | 振荡腿保守保本 | ZD 720d $30,450 |
| QS 趋势基类 | 0.50 | 0.40 | 趋势腿默认 | QS 720d $481K |
| hold-r1 | 1.00 | 0.20 | 晚保本 | 30d $45（败） |
| hold-r3 | 1.50 | 0.20 | 更晚保本 | 30d $45（败） |
| hold-r4 | 0.00 | 0.00 | 禁用保本 | 30d $44（败） |
| mgmt-r5 | 1.00 | 0.10 | 晚保本低锁仓 | 30d $45（败） |

**0529 的关键教训**：QS 默认 BE 0.5/0.4 在正常趋势行情中工作良好，但在弱趋势/高波动的 Session 5/6 场景中，0.5R 的 BE 触发后，0.4R 的锁仓位置在价格快速波动中被反复扫掉。不是 BE 触发太早的问题，而是 BE 锁仓太浅（0.4R）——价格回撤 0.4R 在 XAU 上约 1.5-2 美元，在 M1 的高波动期轻易达到。

#### BE 参数推荐

```
# ===== QS 趋势腿 =====
InpBreakevenR: 0.6                # 从 0.5 提升到 0.6（给价格更多呼吸空间）
InpBreakevenLockR: 0.4            # 保持 0.4（足够保护成本）
InpBreakevenStage2R: 1.0          # 渐进式第二段 BE
InpBreakevenStage2LockR: 0.6      # 第二段锁仓更远

# ===== ZD 振荡腿 =====
InpBreakevenR: 0.4                # 从 0.25 提升（防止在宽DTP前被BE打掉）
InpBreakevenLockR: 0.15           # 稍微提高锁仓
InpBreakevenStage2R: 1.0          # 渐进式第二段
InpBreakevenStage2LockR: 0.5
```

**依据**：
- 0.5R → 0.6R 的提升在正常趋势中影响不大（大部分赢单远超 0.6R），但在振荡期避免过早 BE 被扫
- Stage 2 BE（1.0R/0.6R）在趋势延续时提供更好的 lock-in
- 渐进式 BE（从低到高）比固定单一 BE 更灵活
- ZD 的 BE 从 0.25 提升到 0.4 是为了避免在 DTP 8.0R 到达前被 BE 系统提前打断

### Trail 触发甜点

#### 各策略 Trail 参数

| 策略 | Trail1_R/LockR | Trail2_R/LockMult | Trail3 | 
|------|---------------|-------------------|--------|
| QS 默认 | 1.0 / 0.2 | 2.5 / 0.65 | 禁用 |
| 所有 ZD 变体 | 禁用 | 禁用 | 禁用 |
| hour-safe-r1 | 1.0 / 0.2 | 2.5 / 0.65 | 禁用 |

**QS 的 Trail 数据显示**：
- Level 1 (1.0R/0.2R)：当价格达到 1.0R 后，SL 推进到 0.2R。这相当于"保本后 0.2R 锁定"
- Level 2 (2.5R/0.65)：当价格达到 2.5R 后，SL 推进到 `peak * 0.65`。这是 35% 的回撤锁定
- 问题：Level 1 的 0.2R 锁仓太浅——如果价格从 1.0R 回撤到 0.2R，刚好触发 BE 水平，与 BE 系统冲突

#### Trail 参数推荐

```
# ===== QS 趋势腿 =====
InpTrail1TriggerR: 1.0            # 保持（首个目标达成后激活）
InpTrail1LockR: 0.4               # 从 0.2 提升到 0.4（与 BE 锁仓一致）
InpTrail2TriggerR: 2.5            # 保持
InpTrail2LockMult: 0.60           # 从 0.65 降至 0.60（更紧的回撤控制）
InpTrailOBDistanceATR: 0.5        # 离开 OB 至少 0.5 ATR 才允许 Trail

# ===== ZD 振荡腿 =====
InpTrail1TriggerR: 2.0            # ZD 不需要早期 Trail（靠 DTP）
InpTrail1LockR: 0.5
InpTrail2TriggerR: 4.0
InpTrail2LockMult: 0.50
```

**依据**：
- OB 距离守卫是关键补充：如果价格尚未远离 OB 边界，过早 Trail 容易被拉回扫掉
- 0.5 ATR 的 OB 距离守卫确保 Trail 不会在价格还在 OB 附近时激活（0529 Session 5 的典型问题）
- Trail1 的锁仓从 0.2R 提升到 0.4R，与 BE 锁仓统一，减少系统内部冲突

---

## 第四部分：影线过滤甜点值

### VSL 参数综合推荐

#### ZD 策略已验证的最优参数（720d 回测）

```
# ZD VSL 参数（已验证，720d +39.6% vs 基线）
InpVirtualSLConfirmBars: 1         # 1 根 M1 收盘确认
InpVirtualSLConfirmTF: 1           # M1 周期
InpVirtualSLHardBufferR: 1.0       # 1.0R 硬缓冲
InpVirtualSLRequireBody: true      # 要求实体突破
InpWickExitMaxPenetrations: 3      # 3 次影线后启用加速退出
InpWickExitConfirmBars: 1          # 加速退出仍要求 1 bar 确认
InpVirtualSLConsecutiveBars: 1     # 连续 1 bar 确认即可
```

#### QS 策略推测的最优参数（需回测验证）

```
# QS VSL 参数（基于证据推导）
InpVirtualSLConfirmBars: 1         # 1 根确认（vs-r2 的 2 根未显著更优）
InpVirtualSLConfirmTF: 1           # M1（QS 主图也是 M1，不需要跨周期）
InpVirtualSLHardBufferR: 0.5       # 0.5R（覆盖 85.7% 假止损）
InpVirtualSLRequireBody: true      # 实体确认模式
InpWickExitMaxPenetrations: 2      # 2 次影线后加速（QS 交易密集，2 次足够）
InpWickExitConfirmBars: 1          # 加速后 1 bar 确认
InpVirtualSLConsecutiveBars: 1     # 连续 1 bar
```

**缓冲值选择逻辑**：

```
0.0R → 不覆盖任何假止损（当前状态）
0.15R → 覆盖 42.9%（3/7）
0.25R → 覆盖 71.4%（5/7）
0.50R → 覆盖 85.7%（6/7）
1.00R → 覆盖 100%（7/7）
```

- 0.50R 是最好的权衡点：覆盖 85.7% 假止损，代价是延长亏损持仓暴露时间约 1-2 bar
- 1.00R 在 QS 上可能过宽（会过度延迟真实止损），但在 ZD 上已证明有效（ZD 的 8.0R DTP 提供了充分的空间）
- QS 使用 0.5R、ZD 使用 1.0R 是合理的策略特异性

### 确认 Bar 数选择

| 候选 | 确认条件 | ZD 720d | 结论 |
|------|---------|---------|------|
| vsl-r1 | 1 bar M1 确认 + 1.0R 缓冲 | $42,516 (+39.6%) | **最优** |
| vsl-r2 | 2 bar M1 确认 + 1.2R 缓冲 | 未测试 | 推测边际改善有限 |

**依据**：
- 从 Live 数据看，影线刺破的持续时间不超过 1 根 M1 bar——价格快速扫过 SL 后立即反转
- 2 bar 确认可能让假止损变为真实亏损（价格继续朝不利方向运行了 2 根 bar）
- 1 bar 确认是最佳平衡

### 确认周期（TF）选择

所有测试中仅使用 M1 作为确认周期。考虑的理由：
- 主策略周期为 M1，使用 M1 确认无需跨周期取数
- M1 在 XAU 上流动性充足，收盘价可信
- 如果主周期改为 M5+，可以考虑 M5 作为确认周期（但需重新验证）

---

## 第五部分：金字塔甜点值

### 当前问题的根源

0529 Live 的 Session 5（15:24-15:30）在 6 分钟内连续入场 6 次：

| 时间 | 间隔 | 方向 | 手数 | 出场 | 盈亏 |
|------|------|------|------|------|------|
| 15:24:48 | — | Buy | 0.01 | 手动微亏 | -$1.04 |
| 15:25:15 | 27s | Buy | 0.07 | BE | +$3.78 |
| 15:26:22 | 67s | Buy | 0.09 | BE(滑价) | +$3.38 |
| 15:27:06 | 44s | Buy | 0.04 | BE | +$3.31 |
| 15:28:27 | 81s | Buy | 0.06 | BE | +$5.13 |
| 15:29:05 | 38s | Buy | 0.04 | BE | +$3.22 |

**问题分析**：
- `InpMaxEntriesPerOB=20` 和 `InpCooldownBars=0` 导致无限制重入
- 每次入场盈利 $3-5，但一旦行情反转，一次 SL 损失 $8-12
- 形成"赚小钱亏大钱"的模式

### 入场频率甜点

```
# ===== 趋势腿（QS 系列）默认 =====
InpMaxEntriesPerOB: 5              # 从 20 降至 5
InpOBReentryCooldownMin: 5         # 从 0 设为 5 分钟
InpCooldownBars: 3                 # 从 0 设为 3 bar

# ===== 防守模式（低余额/亏损时激活）=====
InpDefensiveMaxEntriesPerOB: 3     # 防守态更严格
InpDefensiveOBReentryCooldownMin: 10

# ===== 振荡腿（ZD 系列）保持 =====
InpMaxEntriesPerOB: 2              # ZD 本来就不需要多次重入
InpOBReentryCooldownMin: 10
```

**依据**：
- 5 次/OB 配合 5 分钟冷却：在 30 分钟窗口内最多 5 次入场（vs 之前的 6 次/6 分钟）
- Session 5 的 6 次入场中，前 2-3 次是有效的（捕捉了早期波动），后 3 次是追涨
- 防守模式下的 3 次/10 分钟进一步压缩风险
- ZD 维持 2 次/10 分钟——作为振荡策略不需要频繁重入

### 加仓参数

```
# ===== 趋势腿加仓 =====
InpEnableStrongAddOn: true
InpStrongAddOnMaxCount: 2           # 最多加仓 2 次（原单+加仓=3 层）
InpStrongAddOnTriggerR: 1.5         # 首次加仓触发 1.5R
InpStrongAddOnStepR: 0.8            # 每层步进 0.8R（第二次在 2.3R）
InpStrongAddOnLotMult: 0.5          # 加仓手数是原单的 50%

# ===== 趋势腿激进模式（可选）=====
InpStrongAddOnMaxCount: 3
InpStrongAddOnTriggerR: 1.2
InpStrongAddOnStepR: 0.6
InpStrongAddOnLotMult: 0.33         # 金字塔递减：1, 0.33, 0.33
```

**依据**：
- 金字塔应该在 1.5R 后才开始（给原单足够的 buffer 空间）
- 步进 0.8R 确保加仓之间有"间隔"（避免过度集中）
- 0.5 倍手数保证总风险不会超过原单的 2 倍（`1 + 0.5 + 0.5 = 2.0` 对于 2 次加仓）
- 需要与 VSL 协调：加仓单的 VSL 应该独立管理还是继承原单？建议继承原单的 VSL 位置

### 需要进一步测试的参数组合

| 组合 | MaxEntry/OB | CooldownMin | MaxConc | 加仓触发 | 预期效果 |
|------|------------|-------------|---------|---------|---------|
| 保守 | 3 | 10 | 5 | 1.5R+0.8R×2 | 最少亏损，但可能错过行情 |
| 中等 | 5 | 5 | 8 | 1.5R+0.8R×2 | 推荐起点 |
| 激进 | 8 | 3 | 12 | 1.2R+0.6R×3 | 跟随趋势，但回撤较大 |

---

## 第六部分：OB 质量控制

### 各质量指标的预测能力排名

依据所有 30d/180d 回测证据，按预测能力排序：

#### 层级 A：强预测因子（独立使用即有区分度）

**1. OB 反弹深度（bounce_ob）**

| 阈值 | 30d 效果 | 180d 效果 | 结论 |
|------|---------|-----------|------|
| >= 0.30 (硬门) | 改善 WR 但余额下降 | **90% 退化** | 不能做硬门 |
| >= 0.25 (硬门) | 适度改善 | 未测 | 比 0.30 更可能存活 |
| 软权重 0.25-0.30 | 未测试 | 未测试 | **推荐方向** |

**推荐**：使用连续软权重替代硬门
```
InpDefensiveBounceSweetMinPct: 0.25     # 甜区下限 25%
InpDefensiveBounceSweetMaxPct: 0.55     # 甜区上限 55%
InpDefensiveOutsideBounceSweetMult: 0.50 # 甜区外 50% 权重
```
这样 bounce 25-55% 的 OB 正常权重，低于 25% 或高于 55% 的降权 50%。
- 低于 25% 的 OB 反弹不足，容易被直接打穿
- 高于 55% 的 OB 可能是假突破大幅甩开，入场追高风险大

**2. OB 收盘确认（confirm_close）**

| 参数 | 30d WR | 30d 余额 | 单独有效性 |
|------|--------|---------|-----------|
| 无确认 | 39.1% | $2.03 | 基线 |
| body45 | 54.9% | $160.68 | 改善但不独立盈利 |
| weakbody45 | 未单独测 | — | 推测更弱 |

**结论**：OB 收盘确认是**必要的成分**但不是充分条件。必须与其他过滤器组合使用。

**推荐**：
```
InpConfirmClose: "body45"           # 实体占比 >= 45%
InpConfirmDirection: true           # 确认 K 方向必须与 OB 方向一致
```

#### 层级 B：中预测因子（组合使用有效）

**3. 确认位置深度（confirm_pos）**

0529 Session 2/5/6 的所有亏损入场都集中在 `confirm_pos -1..-0.5` 区间。

但是软权重测试全部失败：

| 方案 | confirm_pos 处理 | 30d 余额 | 结论 |
|------|-----------------|---------|------|
| shallowsoft-m035 | 乘数 0.35 | $45.58 | 无效 |
| shallowsoft-m060 | 乘数 0.60 | $46.09 | 无效 |
| shallowsoft-m080 | 乘数 0.80 | $44.84 | 无效 |

**结论**：浅确认位置是**统计特征**而非**独立原因**。浅确认位置的交易亏损是因为它们发生在弱时段/弱行情，而非因为浅确认本身。硬过滤或降权浅确认会同时砍掉正常行情中的浅确认盈利交易。

**推荐**：不做独立过滤，但可以作为组合过滤的成分（例如：浅确认 + 低 bounce + 重入 > 2 次 三者同时满足时才降权）。

```
InpShallowConfirmPosMin: -1.5       # 只过滤极端浅确认（< -1.5R）
InpShallowConfirmPosMult: 0.5       # 极端浅确认降权 50%
```

**4. 实体占比（OB body pct）**

当前默认 `InpMinOBBodyPct: 50.0`。测试中 body45（>=45%）作为确认条件有效。

**推荐**：保持 50% 不变。body45 和 body50 的差异在回测中不显著。

**5. OB 强度（strength）**

当前 OBDetector 计算 strength 时使用的公式：
```
strength = 1.0 + displacement_ratio / 3.0 + impulse_body_pct / 100.0 + wick_pct / 25.0
```

**推荐**：使用 strength 而不是 bounce 作为主质量指标，因为 strength 综合了多个维度。

```
InpMinOBStrength: 0.8              # 从 0.5 提升到 0.8
InpBuyMinStrength: 0.0             # 不区分方向用统一值
InpSellMinStrength: 0.0
```

#### 层级 C：待验证的预测因子（需新建代码和数据）

**6. OB 实体收复强度（entity recovery strength）**

在 `2026-05-30_xau_qs_non_hindsight_followup.md` 中明确标注为"最高优先级后续分析方向"。当前无任何数据。

**定义**：OB 被价格刺破后，实体收盘是否能收复 OB 边界。如果价格刺破 OB 边界后实体收盘没有回到 OB 内，则 OB 结构被破坏；如果实体收复回来了，则 OB 仍然有效。

**建议实现**：
- 在 `UpdateOBStatus` 中增加状态：当价格穿入 OB 区间后，记录穿入深度和后续实体收盘的位置
- 分类：完全收复（实体收盘回到 OB 内）、部分收复（实体收盘在 OB 边界附近）、未收复（实体收盘在 OB 外）
- 对应不同收复强度的 OB 赋予不同的 entry quality

**7. 重入质量衰减（re-entry decay）**

同样标注为"最高优先级后续分析方向"。当前无数据。

**假设**：同一个 OB 被反复入场后，后续入场的质量递减。第 1 次入场质量最高，第 4+ 次入场质量大幅下降。

**建议实现**：
- 在 `PosTrack` 或 `OBZone` 中记录每个 OB 的入场序列
- 第 N 次重入应用 `mult = 1.0 / sqrt(N)` 或类似衰减函数
- 配合冷却机制：冷却期内衰减重置

**8. 高周期实体推进方向（HTF entity alignment）**

在 180 天测试中，`v11xau-qs-hour-core-dir` 的 720 天表现 $9,721 远优于其 180 天 $203.96，说明该候选在长期（跨越不同市场阶段）有效但在近期（特定市场阶段）不佳。核心原因是固定小时过滤过于僵化。

**更稳健的方案**：使用高周期实体推进方向替代固定小时过滤。当 M15/H1 实体推进与 OB 方向一致时允许入场，不一致时禁用或降权。

### OB 质量参数综合配置

```
# ===== Tier 1: 硬门 =====
InpMinOBStrength: 0.8              # 最低 0.8
InpMinOBBodyPct: 50.0              # 实体 >= 50%
InpBouncePct: 0.20                 # 最低 bounce 20%（宽松，配合软权重）

# ===== Tier 2: 软权重 =====
InpDefensiveBounceSweetMinPct: 0.25
InpDefensiveBounceSweetMaxPct: 0.55
InpDefensiveOutsideBounceSweetMult: 0.50
InpShallowConfirmPosMin: -1.5
InpShallowConfirmPosMult: 0.50
InpReentryPosMult: 0.70            # 非首次入场降权 30%

# ===== Tier 3: 收盘确认 =====
InpConfirmClose: "body45"          # 实体收盘确认
InpConfirmDirection: true          # 方向一致性
```

---

## 第七部分：风控甜点值

### 各风控机制的时效性分析

| 风控机制 | 触发条件 | 典型触发点 | 对 0529 崩盘的保护 |
|---------|---------|-----------|-----------------|
| 低余额门 | 余额 < 阈值($250) | 余额已亏 25%+ | 触发时已晚 |
| 运行时 DD | peak - current > 8% | 亏损发生后 | 触发时已晚 |
| 月度止损 | 月度亏损超限 | 多日累计 | 不防单日 |
| 日内止损 | 单日亏损超限 | 当日盘中 | 部分保护 |
| 连续亏损冷却 | N 笔连亏后暂停 | 3-5 笔后 | 部分保护 |
| **入场质量过滤** | **入场前** | **入场前** | **最有效** |

**核心结论**：所有反应式风控（balance/DD/monthly/daily）都在亏损发生后触发。对于 0529 这种在 30 分钟内完成 6 次入场 + 6 次亏损的快速崩溃，只有**入场前的前置过滤**能有效防止。

### 反应式风控参数

#### 月度风控

```
# ===== 月度亏损止损 =====
InpMonthlyLossStopPct: 30           # 亏 30% 停当月交易
InpMonthlyEarlyLossStopTrades: 5    # 前 5 笔累计亏损超 20% 则停
InpMonthlyEarlyLossStopPct: 20
InpMonthlyLossStopMinTrades: 3      # 至少 3 笔才触发

# ===== 月度利润锁定 =====
InpMonthlyProfitLockStartPct: 30    # 利润达到 30% 开始锁定
InpMonthlyProfitLockKeepPct: 60     # 回撤到峰值的 60% 锁利润
InpMonthlyProfitTargetStopPct: 100  # 利润达到 100% 停当月
InpMonthlyProfitTargetStopPct2: 200 # 二级利润目标

# ===== 月度防守模式 =====
InpMonthlyDefensiveLossPct: 15      # 亏 15% 进入防守
InpMonthlyDefensiveUntilProfitPct: 5  # 防守到盈利 5%
InpMonthlyDefensivePosMult: 0.5     # 防守态仓位置 50%
InpMonthlyDefensiveMaxMonthStartBalance: 500  # 仅对 $500 以下账户启用
```

**依据**：
- 30% 月度止损：从 $200 亏到 $140 停手。如果剩余 $140，下月仍可操作
- 早期止损（前 5 笔亏 20%）：对应 0529 情况——如果前 5 笔亏了 $20+（从 $200 → $180），直接暂停
- 利润锁定 30%/60%：当利润达到 $60（200→260）开始锁定，回撤到 $236（峰值 260 的 60% 锁仓利润）时停
- 防守模式 15%：提前触发较轻的仓位减半

#### 日内和运行时风控

```
# ===== 日内止损 =====
InpDailyLossStopPct: 15             # 单日亏 15% 停

# ===== 运行时防御 =====
InpRuntimeDefensiveDrawdownPct: 10  # 从峰值回撤 10%
InpRuntimeDefensiveMinTrades: 5     # 至少 5 笔交易后
InpRuntimeDefensivePosMult: 0.5     # 仓位减半
InpRuntimeDefensiveMinPeakBalance: 210  # 峰值至少 $210（避免刚启动就触发）

# ===== 连续亏损冷却 =====
InpConsecutiveLossCooldown: 3       # 3 笔连亏后触发
InpConsecutiveLossCooldownMin: 60   # 冷却 60 分钟
```

**依据**：
- 日内 15%：0529 从 $200 到 $45 是 77.5% 的单日亏损。15% 止损在 $170 就停了
- 运行时 10% 回撤：比当前的 8% 略高，避免过于敏感。从 $200 峰值亏到 $180 触发
- 连续亏损 3 笔：配合冷却 60 分钟，在 Session 2/5 的 2-3 笔连亏后暂停
- 运行时防御的 `InpRuntimeDefensiveMaxBalance` 保持 0（不限）

#### 低余额状态门

```
# ===== 低余额状态 =====
InpLowBalanceThreshold: 300         # 从 $250 提高到 $300（更早触发）
InpLowBalancePosMult: 0.5           # 仓位置半
InpLowBalanceMaxLotSize: 0.03       # 最大手数限制
```

**依据**：
- `$250` 阈值的问题：从 $200 开始，到 $250 意味着已经**盈利**了 $50，但亏损时余额一路下降经过 $250 时已经亏了 $50 以上的利润。这个门只对"从高位回落"有意义，对"从 $200 开始"没有保护。
- `$300` 仍是盈利态门槛（从 $200 涨到 $300 是 +50% 利润），但更靠近起始资金
- 更好的设计：以月初余额为基准。如果月初余额 $200，则阈值设为 `$200 * 1.2 = $240` 或 `$200 * 0.8 = $160`（根据盈利/亏损分别对待）

### 风控参数综合配置（两套模式）

#### 模式 A：保守（新策略/未知市场）

```
InpMonthlyLossStopPct: 20
InpDailyLossStopPct: 10
InpConsecutiveLossCooldown: 2
InpConsecutiveLossCooldownMin: 120
InpRuntimeDefensiveDrawdownPct: 8
InpRuntimeDefensivePosMult: 0.33
InpLowBalanceThreshold: 250
InpLowBalancePosMult: 0.33
```

#### 模式 B：标准（已验证策略）

```
InpMonthlyLossStopPct: 30
InpDailyLossStopPct: 15
InpConsecutiveLossCooldown: 3
InpConsecutiveLossCooldownMin: 60
InpRuntimeDefensiveDrawdownPct: 10
InpRuntimeDefensivePosMult: 0.50
InpLowBalanceThreshold: 300
InpLowBalancePosMult: 0.50
```

#### 模式 C：激进（高确信趋势市场）

```
InpMonthlyLossStopPct: 40
InpDailyLossStopPct: 20
InpConsecutiveLossCooldown: 5
InpConsecutiveLossCooldownMin: 30
InpRuntimeDefensiveDrawdownPct: 15
InpRuntimeDefensivePosMult: 0.75
InpLowBalanceThreshold: 0  # 禁用
InpLowBalancePosMult: 1.0
```

---

## 第八部分：各策略线参数变更汇总

### v11xau-qs（趋势腿）建议变更

| 参数 | 当前值 | 建议值 | 变更依据 |
|------|-------|-------|---------|
| InpBreakevenR | 0.5 | 0.6 | 增加呼吸空间 |
| InpBreakevenStage2R | 0 | 1.0 | 渐进式保本 |
| InpBreakevenStage2LockR | 0 | 0.6 | 第二段锁仓 |
| InpVirtualSLConfirmBars | 0 | 1 | 虚拟止损确认 |
| InpVirtualSLHardBufferR | 0.0 | 0.5 | 假止损缓冲 |
| InpVirtualSLRequireBody | false | true | 实体确认模式 |
| InpWickExitMaxPenetrations | 0 | 2 | 加速退出 |
| InpTrail1LockR | 0.2 | 0.4 | 与 BE 锁仓统一 |
| InpTrail2LockMult | 0.65 | 0.60 | 更紧回撤控制 |
| InpTrailOBDistanceATR | 0.0 | 0.5 | 新增 OB 距离守卫 |
| InpMaxEntriesPerOB | 20 | 5 | 限制重入 |
| InpOBReentryCooldownMin | 0 | 5 | 冷却时间 |
| InpDefensiveMaxEntriesPerOB | — | 3 | 防守态更严 |
| InpDefensiveOBReentryCooldownMin | — | 10 | 防守态冷却 |
| InpMinOBStrength | 0.5 | 0.8 | 提高质量门槛 |
| InpConfirmClose | "" | "body45" | 收盘确认 |
| InpConfirmDirection | false | true | 方向一致 |
| InpReentryPosMult | 1.0 | 0.70 | 重入降权 |

### v11xau-zd（振荡腿）建议变更

| 参数 | 当前值 | 建议值 | 变更依据 |
|------|-------|-------|---------|
| InpVirtualSLConfirmBars | 0 | 1 | **已验证 720d +39.6%** |
| InpVirtualSLHardBufferR | 0.0 | 1.0 | **已验证最优** |
| InpVirtualSLRequireBody | false | true | 实体确认 |
| InpWickExitMaxPenetrations | 0 | 3 | 影线加速退出 |
| InpBreakevenR | 0.25 | 0.4 | 防止被 BE 提前打断 |
| InpBreakevenLockR | 0.08 | 0.15 | 稍紧锁仓 |
| InpMaxEntriesPerOB | 1 | 2 | 允许一次重入 |
| InpOBReentryCooldownMin | 0 | 10 | 冷却 |

---

## 第九部分：需进一步验证的问题

### 高优先级（有数据但未充分测试）

1. **QS + VSL 组合的 180d/720d 回测**：ZD 的 VSL 验证已完成，QS 的 VSL 需要独立回测。关键参数：1 bar M1 确认 + 0.5R 缓冲。

2. **渐进式 BE + 统一 Trail 锁仓**：将 BE Stage 2（1.0R/0.6R）与 Trail1（1.0R/0.4R）对齐，消除系统内部冲突。

3. **ReentryPosMult 的衰减曲线**：当前建议固定 0.70，但实际衰减可能是非线性的（第 2 次 0.8、第 3 次 0.5、第 4 次 0.3）。需回测比较。

### 中优先级（需要新代码）

4. **OB 实体收复强度**：价格穿入 OB 后实体收盘是否收复边界。需在 `UpdateOBStatus` 中新增状态跟踪和对应的 entry quality 逻辑。

5. **HTF 实体推进方向过滤**：替代固定小时过滤。使用 M15/H1 实体净推进方向判断趋势，与 OB 方向对齐才允许入场。

6. **重入质量衰减**：统计每个 OB 上失败重入的次数，对后续重入动态降权。

### 低优先级（探索性）

7. **自适应 buffer**：VSL 缓冲随持仓时间收缩（初始 0.5R，1 小时后降到 0.3R）。

8. **不对称 BE**：Profit 端的 BE 与 Loss 端的 BE 使用不同参数（盈利时更宽松、亏损时更严格）。

---

## 附录 A：核心参数速查表

| 维度 | 参数 | QS 推荐 | ZD 推荐 | 证据来源 |
|------|------|---------|---------|---------|
| SL | InpSLBufferATR | 0.3 | 0.5 | Live: 假止损偏移 0.03-0.42R |
| SL | InpMaxRiskATR | 2.5 | 3.0 | XAU M1 ATR ~0.8-1.2 |
| VSL | InpVirtualSLConfirmBars | 1 | 1 | ZD 720d +39.6% |
| VSL | InpVirtualSLHardBufferR | 0.5 | 1.0 | Live: 0.5R 覆盖 85.7% |
| BE | InpBreakevenR | 0.6 | 0.4 | QS 趋势 vs ZD 振荡差异 |
| BE | InpBreakevenLockR | 0.4 | 0.15 | 策略特异性 |
| Trail1 | InpTrail1TriggerR | 1.0 | 2.0 | QS 高频 vs ZD 宽 DTP |
| Trail1 | InpTrail1LockR | 0.4 | 0.5 | 与 BE 对齐 |
| Trail2 | InpTrail2LockMult | 0.60 | 0.50 | 回撤控制更紧 |
| OB | InpMinOBStrength | 0.8 | 0.8 | 提升质量门槛 |
| OB | InpDefensiveBounceSweetMinPct | 25% | 25% | <25% 亏损集中 |
| OB | InpDefensiveOutsideBounceSweetMult | 0.50 | 0.50 | 软权重而非硬门 |
| OB | InpConfirmClose | "body45" | "body45" | 30d WR 54.9% |
| 重入 | InpMaxEntriesPerOB | 5 | 2 | 0529 Session 5 教训 |
| 重入 | InpOBReentryCooldownMin | 5 | 10 | 避免快速重入 |
| 重入 | InpReentryPosMult | 0.70 | 0.70 | 重入降权 |
| 风控 | InpMonthlyLossStopPct | 30% | 30% | 标准保护 |
| 风控 | InpDailyLossStopPct | 15% | 15% | 单日保护 |
| 风控 | InpConsecutiveLossCooldown | 3 | 3 | 连亏暂停 |
| 风控 | InpLowBalanceThreshold | $300 | $300 | 提前触发 |

---

## 附录 B：关键研究结论（不可挑战）

以下结论经过多次交叉验证，作为策略设计的不变约束：

1. **全局 bounce >= 30% 硬门不可用**：30d 盈利但 180d 退化 90%。只能做软权重。

2. **确认位置浅过滤无效**：`confirm_pos` 是统计特征而非独立原因，软权重测试全部失败。

3. **固定小时过滤是后见之明**：`v11xau-hour-core-dir` 在某些月份有效但在其他月份退化。应使用 HTF 实体推进替代。

4. **低余额状态门触发太晚**：余额从 $200 跌到门槛 $250 以下时，损失已经发生。应前置到入场质量过滤。

5. **运行时 DD 触发太晚**：DD 8% 在 0529 的 6 笔/6 分钟快节奏下来不及触发。连续亏损冷却更快。

6. **ZD 和 QS 参数不可互套**：两条策略的胜率结构完全不同（72% vs 57%），BE/VSL/Trail/RM 参数需要独立优化。

7. **VSL 在 ZD 上已验证有效**：1 bar M1 + 1.0R 缓冲，720d +39.6%。这是本文档中最强的单一证据。

8. **OB 质量是唯一的前置防御**：所有反应式风控都太慢。入场前的 bounce/strength/confirm/body 过滤是防止快速崩盘的核心机制。
