# WaiTrade2 策略盈利能力排名 — 2026.06.09

## 一、策略配置速查

### 公共基础参数

所有策略共享以下基础配置（S2基线层）：

| 参数 | 值 | 说明 |
|------|-----|------|
| `InpEnableTickNoiseGate` | true | Tick噪音门控 |
| `InpEnableDynamicSpread` | true | 动态spread感知 |
| `InpMinSLSpreadMult` | 5.0 | SL最小/spread |
| `InpOBTouchConfirmTicks` | 5 | OB接触确认tick |
| `InpSLBufferATR` | 0.4 | SL ATR缓冲 |
| `InpMaxPosMult` | 2.0 | 最大仓位乘数 |
| `InpDTPTriggerR` | 1.0 | DTP触发R |
| `InpDTPRetrace` | 0.20 | DTP回撤 |
| `InpBreakevenR` | 0.0 | 保本(关闭) |
| `InpAdaptiveNoiseDrawdownPct` | 3.0 | 自适应噪音回撤触发 |
| `InpAdaptiveNoiseRecoveryPct` | 1.0 | 恢复阈值 |
| Tick噪音方向一致率 | 0.20 | 正常态 |
| Tick噪音方向一致率(防守) | 0.30 | 防守态 |
| Tick振幅上限 | 0.25 | 正常态 |
| Tick振幅上限(防守) | 0.16 | 防守态 |

---

## 二、盈利能力排名

### 2.1 24月全周期排名（2024.06-2026.05, $200初始, Model 4 Real Ticks）

| 排名 | 策略 | 24月净盈亏 | 最终余额 | 胜率 | PF | 盈利月/总月 | 最大单月 |
|:---:|------|----------:|--------:|-----:|-----:|:---:|------:|
| 🥇 | **RegimeBoth d3%** | +$979,971 | $980,171 | 58.0% | 2.88 | 17/20 | +$443K (2510) |
| 🥈 | **BD05 decay0.5** | +$925,426 | $925,626 | 55.7% | 2.89 | 15/19 | +$453K (2510) |
| 🥉 | **BD07 decay0.7** | +$880,277 | $880,477 | 55.2% | 2.87 | 13/17 | +$503K (2510) |
| 4 | **PathB 双扫确认** | +$788,998 | $789,198 | 54.9% | 2.85 | 12/15 | +$471K (2510) |
| 5 | **S2 基线** | +$48,615 | $48,815 | 49.1% | 2.31 | 18/21 | +$35K (2510) |

### 2.2 2505 趋势月排名（2025.05）

| 排名 | 策略 | 净盈亏 | 笔数 | 胜率 | PF |
|:---:|------|------:|-----:|-----:|-----:|
| 🥇 | **BD07 decay0.7** | +$7,578 | 776 | 52.1% | 2.12 |
| 🥈 | **RegimeBoth d3%** | +$6,807* | 704 | 58.0% | 2.30 |
| 🥉 | **PathB 双扫确认** | +$6,195 | 732 | 52.3% | 2.22 |
| 4 | **BD05 decay0.5** | +$6,071 | 742 | 52.3% | 2.30 |
| 5 | **S2 基线** | +$3,126 | 583 | 53.9% | 2.24 |

*含 SwingCapture TP (+$83 vs 原 RegimeBoth)

### 2.3 2605 震荡月排名（2026.05）

| 排名 | 策略 | 净盈亏 | 笔数 | 胜率 | PF |
|:---:|------|------:|-----:|-----:|-----:|
| 🥇 | **RegimeBoth d3%** | -$6 | 10 | 30.0% | 0.22 |
| 🥈 | **BD05 decay0.5** | -$12 | 12 | 16.7% | 0.21 |
| 🥉 | **BD07 decay0.7** | -$12 | 20 | 25.0% | 0.43 |
| 4 | **PathB 双扫确认** | -$14 | 16 | 18.8% | 0.25 |
| 5 | **S2 基线** | -$23 | 37 | 24.3% | 0.35 |

---

## 三、各策略详细参数

### 3.1 RegimeBoth d3%（🥇 综合最优）

```yaml
base: S2基线
overrides:
  InpEnableLiquiditySweep: true
  InpEnableStateFilter: true
  InpEnableDoubleSweepConfirm: true
  InpDoubleSweepWindowBars: 20
  InpDoubleSweepOnlyDefensive: true
  InpAdaptiveNoiseDefBoostMult: 0.7
  InpAdaptiveNoiseDrawdownPct: 3.0
  InpDoubleSweepRegimePosMult: 0.6
  InpDoubleSweepDTPTriggerR: 0.5
```

**设计理念**：双扫确认体制检测 + 自适应衰减(0.7×) + 震荡区间仓位降低(0.6×)。趋势月全力出击，震荡月自动退守。

**v2 增强版额外参数**（待终端恢复后验证）：
```yaml
  InpHTFSkipDTP: true                    # SwingCapture: 震荡市跳过DTP
  InpEnableHTFDirectionGate: true        # HTF方向门控
  InpEnableHTFNetPushFilter: true
  InpHTFNetPushTF: 15
  InpHTFNetPushBars: 4
  InpHTFNetPushMinATR: 0.35
  InpHTFNetPushCounterMult: 0.5          # 逆势降至50%
  InpHTFNetPushAlignedMult: 1.2          # 顺势加20%
```

### 3.2 BD05 decay0.5（🥈 最高PF）

```yaml
base: PathB双扫确认
overrides:
  InpAdaptiveNoiseDefBoostMult: 0.5      # 更强衰减
```

### 3.3 BD07 decay0.7（🥉 2505最佳）

```yaml
base: PathB双扫确认
overrides:
  InpAdaptiveNoiseDefBoostMult: 0.7      # 中等衰减
```

### 3.4 PathB 双扫确认

```yaml
base: S2基线 + Sweep
overrides:
  InpEnableLiquiditySweep: true
  InpEnableStateFilter: true
  InpEnableDoubleSweepConfirm: true
  InpDoubleSweepWindowBars: 20
  InpDoubleSweepOnlyDefensive: true
```

### 3.5 S2 基线

```yaml
base: v11xau-qs3.set
overrides:
  InpEnableTickNoiseGate: true
  InpEnableDynamicSpread: true
  InpMinSLSpreadMult: 5.0
  InpOBTouchConfirmTicks: 5
  InpDTPTriggerR: 1.0
  InpDTPRetrace: 0.20
  InpBreakevenR: 0.0
  InpEnableMTF: false
  InpSLBufferATR: 0.4
  InpMaxPosMult: 2.0
```

---

## 四、震荡月防御对比

| 策略 | 2605交易 | 2605亏损 | 防御机制 | 评级 |
|------|:---:|------|------|:---:|
| RegimeBoth | 10笔 | -$6 | 双扫确认 → 防守态 → 仓位衰减 → 退守 | ⭐⭐⭐ |
| BD05 | 12笔 | -$12 | 强衰减(0.5×) → 仓位降低 | ⭐⭐ |
| BD07 | 20笔 | -$12 | 中衰减(0.7×) | ⭐⭐ |
| PathB | 16笔 | -$14 | 双扫确认过滤 | ⭐ |
| S2 | 37笔 | -$23 | 无 | ✗ |

---

## 五、推荐组合

### Live 部署建议（$200账户, 分腿各$100）

| 腿 | 策略 | 角色 | 优势 |
|:---:|------|------|------|
| 1 | **RegimeBoth d3%** | 震荡防御+趋势进攻 | 最高24月回报, 最低MDD($9), 震荡自保 |
| 2 | **BD05 decay0.5** | 趋势加速 | 最高PF(2.89), 强衰减保护 |

### 风险警告

- ⚠️ 2025 Q4异常行情（2510-2512 $400K+/月）不可预期复现
- ⚠️ MT5 build 5836 tester Bug — 当前CLI回测不可用，等更新
- ⚠️ $200→$980K 复利路径从未Live验证
- ⚠️ 2026震荡加剧，多策略零交易或微亏

---

## 六、已验证改进（待部署）

| 改进 | 代码 | 2505效果 | 2605预期 |
|------|:---:|------|------|
| SwingCapture TP | SignalEngine.mqh +10行 | +$83 | $0 (SL先触发) |
| HTF方向门控 | SignalEngine.mqh +15行 | 待测 | +$1~3 |
| FVG v2过滤器 | FVGDetector.mqh ~400行 | 不适用 | +$200+/月 |

---

*文档生成: 2026.06.09 | 数据来源: top5_24m.json, bt_top5_2m.py, FVG验证回测*
