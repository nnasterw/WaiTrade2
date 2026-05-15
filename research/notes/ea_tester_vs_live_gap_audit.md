# EA Strategy Tester vs Live 执行差异完全审计

**日期**: 2026-05-15
**目标**: 找出同一 EA 代码在回测和 live 中的所有行为差异，评估能否做到「回测=live」

---

## 结论：7 个确认的 Gap + 2 个不可消除的平台限制

### 确认可修复的 Gap (代码层面)

| # | Gap | 严重度 | 可修复 |
|---|-----|--------|--------|
| 1 | Spread 模型差异 | 🔴 高 | 部分 |
| 2 | Tick 生成模式差异 | 🔴 高 | 选 Model 4 |
| 3 | 滑点/执行质量 | 🟠 中 | 无法完全 |
| 4 | 当前 bar 的 CopyRates 行为 | 🟡 低 | 已正确 |
| 5 | DTP 的 Adaptive 阈值计算 | ✅ 无 | 已对齐 |
| 6 | Breakeven/Trailing 触发精度 | 🟠 中 | 无法完全 |
| 7 | OB 超时(TimeCurrent) | 🟡 低 | 已正确 |

### 不可消除的平台限制（无论代码如何完美）

| # | 限制 | 原因 |
|---|------|------|
| A | Tester 无真实滑点 | Tester 中 OrderSend 总是以 request.price 成交 |
| B | Tester 无 requote/reject | Live 中高波动时订单可能被拒绝 |

---

## 逐项详细分析

### Gap 1: Spread 模型差异 🔴

**代码**: `GetSpread()` → `SymbolInfoInteger(symbol, SYMBOL_SPREAD) * SYMBOL_POINT`

**Tester 行为**:
- Model 0 (Every Tick): spread 使用历史数据中记录的固定 spread，或 broker 设定的最小 spread
- Model 4 (Real Ticks): spread 动态变化（来自真实 tick 数据库），最接近 live
- 关键问题: Exness 的历史 tick 数据 spread 通常低于 live 实际 spread（特别是在新闻/低流动性时段）

**Live 行为**:
- spread 实时变化，高波动时可达正常值的 3-10 倍
- 凌晨/新闻时段 XAU spread 可从 0.3 飙到 2.0+

**影响路径**:
```
GetSpread() → min_ob_range = spread × InpMinOBSpreadMult(2.0)
                           → OB 过滤门槛
            → PassSpreadRatio() → risk_distance / spread 检查
```

**差距量化**: Tester 中 spread 偏低 → min_ob_range 偏小 → 更多 OB 通过过滤 → Tester 信号数 > Live 信号数。但因为是同一个 GetSpread 函数，如果 Model 4 数据包含真实 spread，这个 gap 可以缩小到 ~10%。

**建议**:
- 使用 `Model=4` (Real Ticks) 回测，spread 接近真实
- 或在 EA 中加 `InpMinSpreadFloor` 参数，设置 spread 下限

---

### Gap 2: Tick 生成模式差异 🔴

**当前配置**: `model: 0` (Every Tick — 基于 M1 OHLC 生成合成 tick)

**Tester Model 0 行为**:
- 每根 M1 bar 生成约 4-12 个合成 tick (Open→High→Low→Close 或 Open→Low→High→Close)
- tick 是确定性生成的，间隔均匀
- **不模拟真实市场微结构**：无急涨急跌、无价格跳空、无流动性缺口

**Live 行为**:
- 每根 M1 bar 有 50-500+ 个真实 tick
- tick 间隔不均匀（毫秒到秒级）
- 存在价格跳空、sudden spike、流动性真空

**影响路径**:
```
每个 tick → UpdateOBStatus() → 触碰检测
         → CheckEntryConditions() → IsZoneTouched()
         → ManagePositions() → CheckBreakeven/CheckTrailing/CheckDTP
```

**差距量化**:
- Tester M1 bar ~8 ticks vs Live M1 bar ~200 ticks
- Tester 中 breakeven 从 "满足条件" 到 "执行" 是 0-1 tick 延迟
- Live 中 breakeven 从 "满足条件" 到 "ModifySL 执行完成" 可能有 50-200ms 延迟
- 在这 200ms 内价格可能已经回落，导致 breakeven lock 位被再次穿越

**建议**: 改用 `Model=4` (Real Ticks)。Exness 为 XAU/BTC 提供真实 tick 数据。

---

### Gap 3: 滑点/执行质量 🟠 (不可完全消除)

**代码**: `ExecuteSignal()` → `request.deviation = 20`

**Tester 行为**:
- OrderSend **总是以 request.price 精确成交**
- deviation 参数被忽略
- SL/TP 设置即时生效
- ModifySL 即时执行

**Live 行为**:
- 市价单可能有 1-5 points 滑点（within deviation=20）
- SL 触发时实际成交价可能比 SL 价差 1-3 points（gap over SL）
- ModifySL 有网络延迟（50-300ms）
- 高波动时可能 requote (retcode != DONE)

**影响路径**:
```
入场: request.price 实际成交价可能偏移 → SL distance 被压缩
SL触发: 精确 vs 可能 gap
Breakeven: ModifySL 延迟期间价格可能回落
Trailing: ModifySL 延迟期间 peak_profit_r 可能更新
```

**差距量化**:
- XAU: 滑点 ~0.5-1.5 points (SL distance ~5 points → 10-30% R 偏移)
- BTC: 滑点 ~5-15 points (SL distance ~112 points → 4-13% R 偏移)
- 这意味着 Tester 中 0.2R breakeven 锁定位，Live 中可能因滑点变成 0.15R 或 0.05R

**不可修复原因**: Strategy Tester 不模拟滑点。MT5 没有原生滑点模拟功能。

**缓解方案**: 在 EA 参数层面补偿：
- breakeven_lock_r 设置时留出滑点 buffer（0.15R 而非 0.05R）→ v96b_live 已修复
- SL 计算时加入 `InpSLBufferATR` → 已有
- 考虑加入 `InpSlippageBuffer` 参数，在 SL 计算中额外加 N 点

---

### Gap 4: 当前 bar 的 CopyRates 🟡 (已正确处理)

**代码**: `CopyRates(symbol, tf, 0, InpBars, rates)` — 包含当前正在形成的 bar

**Tester 行为**:
- rates[count-1] 是当前 bar，其 OHLC 在每个 tick 更新
- 但 DetectOrderBlocks 的 scan_start = `count - (InpImpulseLookback + 1)` → **跳过最后 3-4 根 bar**
- 所以 OB 检测只看已完成的历史 bar

**Live 行为**: 完全相同 — 同一个 scan_start 计算。

**结论**: ✅ 无 gap。EA 代码正确处理了未完成 bar 问题（之前 Python 版本有此 bug，EA 版本没有）。

---

### Gap 5: DTP Adaptive 阈值 ✅ (已对齐)

**代码**:
```cpp
if(InpAdaptiveDTP)
    threshold = track.dtp_peak_r * InpDTPRetrace;  // 动态：峰值×回撤比
else
    threshold = InpDTPTriggerR * InpDTPRetrace;    // 固定：触发值×回撤比
```

**Tester vs Live**: 完全相同。无差异。

---

### Gap 6: Breakeven/Trailing 触发精度 🟠

**代码**: CheckBreakeven 用 `POSITION_PRICE_CURRENT` 计算 current_r，满足条件后调用 ModifySL。

**Tester 行为**:
- `POSITION_PRICE_CURRENT` 在每个 tick 精确更新
- ModifySL 即时生效（同一 tick 内完成）
- 不存在 "条件满足但 SL 还没改" 的窗口

**Live 行为**:
- `POSITION_PRICE_CURRENT` 实时更新
- ModifySL 需要 50-300ms 网络往返
- **竞态条件**: 价格触及 0.2R → EA 发送 ModifySL 请求 → 等待 200ms → 此时价格可能已回落到 0.05R 以下
- 如果 ModifySL 在价格低于 new_sl 时到达服务器，broker 可能拒绝（invalid SL）

**差距量化**:
- Tester 中 breakeven 成功率 = 100%（只要条件满足就成功）
- Live 中 breakeven 可能失败（price moved against）→ 交易以原始 SL 平仓
- 这解释了为什么 breakeven_r=0.2 在 Tester 中 "保护" 了利润，但 Live 中经常保本失败

**缓解方案**: 
- 已在 v96b_live 中将 breakeven_r 从 0.2 放宽到 0.5（给更多空间）
- 可考虑在 CheckBreakeven 中加入重试逻辑

---

### Gap 7: OB 超时计算 🟡 (行为一致)

**代码**: `UpdateOBStatus()` 中 `datetime now = TimeCurrent();` 用于超时判断

**Tester 行为**: TimeCurrent() 返回当前模拟时间，随 tick 推进
**Live 行为**: TimeCurrent() 返回服务器最后 tick 时间

两者在 EA 上下文中行为一致 — 都是基于最后收到的 tick 时间。无 gap。

---

## 不可消除的平台限制

### 限制 A: Tester 无真实滑点

MT5 Strategy Tester 的设计原则是「确定性重放」— 给定相同参数和数据，回测结果必须完全可复现。这意味着它**故意不模拟随机滑点**。

Live 中的滑点来源：
- 流动性不足（大单需要多层 LP 报价填充）
- 网络延迟（报价变化）
- 高频事件（新闻）

**结果**: Tester 的入场/出场价格总是优于或等于 Live。回测永远不会比 Live 差（在执行质量维度）。

### 限制 B: Tester 无 Requote/Reject

Live 中 OrderSend 可能返回:
- `TRADE_RETCODE_REQUOTE` (报价已变)
- `TRADE_RETCODE_REJECT` (broker 拒绝)
- `TRADE_RETCODE_TIMEOUT` (超时)

Tester 中 OrderSend 只会返回 `TRADE_RETCODE_DONE`（除非参数错误）。

当前 EA 代码在 ExecuteSignal 中只检查 `retcode == DONE`，不重试。
**Live 中**: 如果被 requote/reject，该信号永远丢失。Tester 中不会丢失。

---

## 最终评估：能否做到「回测 = Live」？

### 可以做到 95% 对齐的部分

1. **切换到 Model 4 (Real Ticks)** → 消除 Gap 1 和 2 的大部分（spread 真实、tick 真实）
2. **参数层面补偿** → 已在 v96b_live 中实施（BE 0.5R, offset 0.8R）
3. **代码层面完全一致** → ✅ 同一个 EA 运行在两个环境，无代码分叉

### 永远无法做到 100% 的部分（~5% gap）

1. **执行滑点** (1-3%): Tester 精确成交 vs Live 有滑点
2. **ModifySL 延迟** (1-2%): Tester 即时 vs Live 50-300ms
3. **Requote/Reject** (0.5-1%): Tester 永不拒绝 vs Live 偶尔拒绝
4. **流动性缺口** (0.5%): Tester 连续 vs Live 可能 gap over SL

**总结**: 在使用 Model 4 + 合理参数缓冲的条件下，回测和 Live 的差距可以压缩到 **~5% 胜率差** 和 **~0.1-0.2R 平均盈亏差**。不可能完全消除，但可以使回测作为「Live 表现的保守下界估计」有效。

---

## 立即可执行的改进

### 1. 回测模型升级 [最高优先]

将 `config/strategies.yaml` 中 `backtest_defaults.model` 从 0 改为 4:

```yaml
backtest_defaults:
  model: 4          # Real ticks (原来是 0=Every tick)
```

**注意**: Model 4 需要 broker 提供真实 tick 数据。Exness 为主要品种提供。如果某品种无真实 tick，MT5 会自动降级到 Model 0。

### 2. 加入 Spread Floor 参数 [建议]

在 Config.mqh 中新增:
```cpp
input double InpSpreadFloor = 0.0;  // 最小spread(用于OB过滤, 0=使用实时spread)
```

在 GetSpread 或 DetectOrderBlocks 中:
```cpp
double spread = GetSpread(symbol);
if(InpSpreadFloor > 0 && spread < InpSpreadFloor)
    spread = InpSpreadFloor;
```

这样在 Tester 中可以人为设置一个 spread 下限，模拟 Live 的最低 spread 水平。

### 3. 加入 ModifySL 重试逻辑 [建议]

当前 ModifySL 失败时直接返回 false，不重试。Live 中应重试 1-2 次:
```cpp
bool ModifySL_Retry(ulong ticket, double new_sl, int max_retries=2)
{
    for(int attempt = 0; attempt <= max_retries; attempt++)
    {
        if(ModifySL(ticket, new_sl)) return true;
        Sleep(100);  // 等 100ms 重试
    }
    return false;
}
```

**注意**: `Sleep()` 在 Tester 中无效（被跳过），所以这段代码在 Tester 中等效于单次调用，不影响回测。

### 4. ExecuteSignal 加入重试 [建议]

```cpp
// 当 retcode == TRADE_RETCODE_REQUOTE 时，刷新价格重试一次
if(result.retcode == TRADE_RETCODE_REQUOTE)
{
    request.price = sig.direction > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                      : SymbolInfoDouble(_Symbol, SYMBOL_BID);
    OrderSend(request, result);
}
```

---

## 验证方法

### A/B 对比验证
1. Model 4 回测同一时段 (比如 2026.05.01-05.15)
2. 同时段 Live 交易记录
3. 逐笔对比：
   - 信号数是否一致
   - 入场价差 (Tester vs Live)
   - 出场方式是否一致
   - 盈亏差异

### 预期对齐度
- Model 0 回测 vs Live: 胜率差 ~15-20pp
- Model 4 回测 vs Live: 胜率差 ~3-5pp ← 目标
- 完美对齐 (不可能): 0pp
