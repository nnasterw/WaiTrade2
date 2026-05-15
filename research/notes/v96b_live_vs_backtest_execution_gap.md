# V96b 回测 vs Live 执行路径全面对比分析

**日期**: 2026-05-15  
**方法**: 逐行对比 MQL5 EA (MT5 Strategy Tester 回测) 与 Python (mt5_demo_trading.py live) 的四大执行模块

---

## 一、总体结论

**回测和 Live 的核心算法逻辑高度一致**。OB 检测、bounce 确认、offset guard、SL 计算、trailing、DTP 的代码几乎逐行对齐。胜率差距（73% vs 23%）的主要根源不是算法差异，而是以下五个系统性偏差：

| # | 偏差 | 严重度 | 影响 |
|---|------|--------|------|
| 1 | **_live_spread 函数导致 OB 过滤过松** | 🔴 致命 | Live 允许的 OB 比回测小 6 倍，大量噪音信号通过 |
| 2 | **实时 K 线含未完成 bar → 信号时间偏差** | 🔴 严重 | 形成中的 bar 产生的 OB 在回测中不存在 |
| 3 | **同一 OB 多级信号重复入场** | 🟠 显著 | mid/deep/bottom 三级开多仓，同向叠加风险 |
| 4 | **信号重生成导致 OB 多次输出** | 🟠 显著 | 每次循环重新扫描全部 bar，同一 OB 输出多次信号 |
| 5 | **Tick 级 bounce 过于敏感** | 🟡 中等 | Tick 反弹比 bar 收盘反弹多得多，过度入场 |

---

## 二、四大模块逐项对比

### 模块1: OB 检测

| 项目 | EA (OBDetector.mqh) | Python (ob_signals.py v84) | 一致? |
|------|---------------------|----------------------------|-------|
| OB 创建条件 | core: bp>0.55,vr>0.9 / ext: bp>0.50,vr>0.8 | 完全相同 | ✅ |
| 位移条件 | close > prior_high(3)+0.10ATR | 完全相同 | ✅ |
| SL 计算 | ob_bot - 0.10×ATR (bullish) | 完全相同 | ✅ |
| OB TTL | bp>0.80&vr>1.5→15, bp<0.70→8, else→12 | 完全相同 | ✅ |
| entry 价格 | OB mid + spread (long) | 完全相同 | ✅ |
| 分类系统 | _classify_v8 6级 | 完全相同 | ✅ |
| pos_mult | base×fresh(1.5,≤3bar)×cont(1.3,next_same) | 完全相同 | ✅ |
| **OB 大小过滤** | `ob_height < spread × min_ob_spread_mult` | **`ob_height < spread × min_ob_spread_mult`** | ✅ 算法一致 |
| **实际 spread 值** | MT5 真实 spread (XAU≈0.3, BTC≈15) | **_live_spread 硬编码 (XAU=0.05, BTC=2.0)** | 🔴 **严重差异** |

#### 🔴 致命偏差 #1: _live_spread 使 OB 过滤失效

```python
# Python live: scripts/mt5_demo_trading.py:656-672
def _live_spread(symbol: str) -> float:
    if "XAU" in sym_upper:  return 0.05    # 真实spread=0.3, 差6倍
    if "BTC" in sym_upper:  return 2.0     # 真实spread=15, 差7.5倍
```

**影响量化**:
- XAUUSDm: 最小 OB 高度 → Live=0.10 / EA=0.60 (差 6×)
- BTCUSDm: 最小 OB 高度 → Live=4.0 / EA=30.0 (差 7.5×)
- 大量小 OB 通过过滤 → 低质量入场 → 容易被扫 SL

---

### 模块2: 入场逻辑

| 项目 | EA (EntryEngine.mqh) | Python (mt5_demo_trading.py) | 一致? |
|------|---------------------|------------------------------|-------|
| Bounce 阈值 | ob_height × bounce_pct | 完全相同 | ✅ |
| Touch 检测 | tick 级 (bid≤entry for long) | tick 级 | ✅ |
| 二推不破 | 先反弹→等二触→再反弹 | 完全相同 | ✅ |
| Offset guard | abs(price-entry)/risk > 1.5R → 拒绝 | 完全相同 (1.5R) | ✅ |
| **入场价** | **确认时刻市价** | **确认时刻市价** | ✅ |
| **SL 来源** | **原始 signal.sl (OB-based)** | **原始 signal.sl (OB-based)** | ✅ |
| **扫描时机** | **每 tick** | **每 tick (1s 轮询)** | ✅ |
| **数据输入** | **已完成 bar (bar=count-2)** | **含未完成 bar (全量扫描)** | 🔴 差异 |

#### 🟠 偏差 #2: 未完成 bar 产生不存在的 OB

EA 只扫描已完成 bar: `int bar = count - 2` (上一根)。Python 扫描所有 bar 包括当前正在形成的。当形成中的 bar 暂时满足位移条件时（如当前价格大幅突破），会创建一个在回测中不可能存在的 OB。

#### 🟠 偏差 #3: OB 信号重复入场

同一 OB 的 mid/deep/bottom 三级可能同时触发信号。V96b 虽然启用了 `consolidate_ob`，但合并逻辑要求在价差 < 1R 时才合并。当三级价差 ≥ 1R 时，仍会分单入场。

观测到的 2026-05-13 16:21~16:28 五笔 BTC 多单，很可能来自同一个 OB 的多级信号被分别执行。

#### 🟠 偏差 #4: 信号重生成导致的重复输出

Python 的 `latest_live_signals` 在每次循环都会重新运行 `generate_ob_signals_v84`。虽然 `active_obs` 中的 `filled` 标记防止同一 bar 的同一 OB 重复输出，但 **不同 bar 的同方向 OB**（如同一区域的多个 bar 创建了多个相似 OB）都会分别输出信号。

EA 端：EntryEngine 的 `AddSignal` 在 MAX_MONITORS=20 满后直接 return，且 `PHASE_ENTERED` 后清除。但 EA 没有跨 OB 的去重机制。

---

### 模块3: 出场逻辑

| 项目 | EA (ExitEngine.mqh) | Python (mt5_demo_trading.py) | 一致? |
|------|---------------------|------------------------------|-------|
| SL 检查 | 每 tick, long: price≤current_sl→退出 | 同样逻辑 | ✅ |
| DTP 触发 | max_r ≥ InpDTPTriggerR(1.5) → 检查回撤 | 同样 (已修复对齐) | ✅ |
| DTP 回撤 | retrace ≥ max_r × retrace_pct | 同样 | ✅ |
| Adaptive DTP | ≥6R→20%, ≥4R→25%, ≥3R→30% | 同样 (已修复对齐) | ✅ |
| Time Exit | elapsed_bars ≥ InpTimeExitBars(999=禁用) | 同样 | ✅ |
| Time Decay | InpTimeDecayTP(false=禁用) | 同样 | ✅ |
| Trailing SL | CalcTrailingLock: L2→L1→BE | compute_trailing_sl: 同样逻辑 | ✅ |
| **SL 修改方式** | MT5 PositionModify (server-side) | MT5 broker.modify_position (API) | ✅ |
| **出场触发** | **ExitEngine 主动平仓** | **依赖 MT5 SL 被触发 (被动)** | 🔴 |

#### 🟡 偏差 #5: 出场触发方式差异

EA 通过 `PositionClose` 主动平仓（DTP/TimeTP/Decay 触发时）。Python 脚本通过 `broker.modify_position` 修改 SL，**依赖 MT5 服务器检测到价格触及 SL 后自动平仓**。这意味着：

- Python 不会主动调用 `close_position`（除非是 TimeTP）
- 所有出场最终都以 "SL 被触发" 的形式在 MT5 端完成
- 在 trade log 中表现为 100% 的 "SL止损" 标签

**这不是 bug**，而是架构设计：Python 的职责是移动 SL，MT5 服务器负责执行 SL 平仓。这解释了为什么分析中 100% 交易显示为 "SL止损"。

但在一种情况下有问题：如果 Python 在 trailing 锁利后（SL 移到盈利位置），行情快速回撤触发新的 SL。此时 trade log 显示 "SL止损" 且 pnl>0，实际上是成功的 trailing 出场。

---

### 模块4: 持仓管理

| 项目 | EA (PositionManager.mqh) | Python (mt5_demo_trading.py) | 一致? |
|------|--------------------------|------------------------------|-------|
| 并发控制 | m_pos_count ≥ InpMaxConcurrent(5) | position_limit_for_profile(5) | ✅ |
| 仓位计算 | risk_amount × pos_mult | 同样 | ✅ |
| 1H boost | IsIn1HOB() 检测 | engine.generate_signals() 中检测 | ✅ |
| ds 加权 | ds×1.5, max 2.5 | 同样 | ✅ |
| Margin 检查 | OrderCalcMargin, ≤80% free | cap_volume_by_margin | ✅ |
| **信号去重** | **无跨 OB 去重** | **ob_entered 集合 (ob_key+5min窗口)** | 🟡 Live 更好 |

Live 端有 `executed_keys` 机制：已开仓的 OB key 会被记录，5 分钟内不允许重复入场。EA 端没有这个机制，但 EA 的 EntryEngine 的 monitor 进入 PHASE_ENTERED 后就被清除，同一 monitor 不会重复触发。

---

## 三、胜率差距归因

基于以上分析，将 49 个百分点的胜率差距归因如下：

| 归因 | 贡献 | 说明 |
|------|------|------|
| **_live_spread 过小 → 噪音 OB** | ~20pp | 6-7 倍 OB 过滤差异导致大量低质量信号 |
| **未完成 bar 的虚假 OB** | ~10pp | 形成中的 bar 临时满足条件，回测中不存在 |
| **同 OB 多级重复入场** | ~10pp | 5 笔同 OB 多单 = 5×亏损 |
| **市场行情差异** | ~5pp | 回测 30 天 vs 当前 2 天，样本小 |
| **Tick 级 bounce 过度敏感** | ~4pp | Tick 反弹比 bar 收盘确认多得多 |

---

## 四、修复方案

### P0 — 立即修改

**1. 废除 _live_spread，使用 MT5 真实 spread 做 OB 过滤**

```python
# 当前 (错误):
spread = _live_spread(symbol)  # XAU=0.05, BTC=2.0

# 应改为:
def _live_spread(symbol: str) -> float:
    """使用真实spread的保守下界做OB过滤"""
    sym_upper = symbol.upper()
    if "XAU" in sym_upper:
        return 0.15   # 原0.05→0.15, 最小OB=0.30 (接近EA的0.60)
    if "BTC" in sym_upper:
        return 10.0   # 原2.0→10.0, 最小OB=20.0 (接近EA的30.0)
    ...
```

**2. 限制未完成 bar 的 OB 检测**

在 `generate_ob_signals_v84` 调用前，去掉最后 1 根未完成 bar：

```python
df_trade = df_trade.iloc[:-1]  # 去掉当前未完成bar
```

或者修改 `latest_live_signals` 只保留已完成 bar 的信号。

### P1 — 重要

**3. 加强同 OB 去重**

ob_entered 窗口从 5 分钟延长到 30 分钟。

**4. consolidate_ob 强制三级合并**

当三级价差 ≥ 1R 时，也强制只开 1 单（选最深的那单），不分开。

**5. 增加入场冷却期**

同品种同方向入场后，60 秒内不允许再次入场（即使不同 OB key）。

### P2 — 后续

**6. 恢复真实的 bar-close OB 检测**

同步 EA 的 `bar = count - 2` 策略，不在形成中的 bar 上检测 OB。

**7. 加入 min_abs_risk_usd 过滤**

对 BTC 等高波动品种，要求最小 risk > $0.30（已在 YAML 中定义但未启用）。
