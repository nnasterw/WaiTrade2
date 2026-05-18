# 2026-05-18 入场模式与 live 对齐分析

## 问题

同样想复刻 v95c 参数时，为什么新版 `WaiTrade2\WaiTrade_OB` 与旧版 `WaiTrade\WaiTrade_OB` 交易数曾经差很多？

## 根因

不是 OB 检测差异，而是入场路径没有对齐：

- 旧版对照 `v95c_oldob_control` 继承默认 `enable_entry_engine=false`，走 `ScanSignals()` 直接入场。
- 新版复刻 `v95c_newob_legacyfast` 设置了 `enable_entry_engine=true`，走 EntryEngine：触及 OB → 等 bounce → offset guard → `FinalizeEntryEngineSignal()` 复核 → 下单。

补充同模式策略 `v95c_newob_direct` 后，结果与旧版完全一致。

## 对比结果

XAUUSDm，Model 4 Real Ticks，初始资金 200 USD。

### 7 天：2026.05.11 ~ 2026.05.18

| 策略 | 入场路径 | 交易数 | 胜率 | PF | 余额 |
|------|----------|--------|------|----|------|
| `v95c_newob_direct` | 新版 direct | 332 | 56.0% | 0.67 | 44.74 |
| `v95c_oldob_control` | 旧版 direct | 332 | 56.0% | 0.67 | 44.74 |
| `v95c_newob_legacyfast` | 新版 EntryEngine | 22 | 50.0% | 0.99 | 176.46 |

### 30 天：2026.04.18 ~ 2026.05.18

| 策略 | 入场路径 | 交易数 | 胜率 | PF | 余额 |
|------|----------|--------|------|----|------|
| `v95c_newob_direct` | 新版 direct | 175 | 48.0% | 0.52 | 45.61 |
| `v95c_oldob_control` | 旧版 direct | 175 | 48.0% | 0.52 | 45.61 |
| `v95c_newob_legacyfast` | 新版 EntryEngine | 64 | 54.7% | 0.89 | 124.18 |

## 哪个更接近 live

更接近 live 的是新版 EntryEngine + `FinalizeEntryEngineSignal()` 路径。

理由：

1. direct 模式会在价格触及 OB 后立即按 tick 直接入场，高频重复触发明显。7 天 332 笔、日均 47.4 笔，对单图 M1 OB 策略来说偏离 live 可执行性。
2. EntryEngine 需要先触及 OB，再等待反弹确认，天然更接近人工/实盘“确认后入场”的流程。
3. 新版 `FinalizeEntryEngineSignal()` 在下单前用真实 bid/ask 重算 entry、risk、lot，并复核 spread、offset、margin、最小风险。旧 direct 在 EntryEngine 确认路径里曾直接用确认阶段的 risk 和简单 lot 计算，容易低估真实成交约束。
4. live 端会受到保证金、滑点、成交偏移、重复下单防护、速率限制等约束。direct 模式的高频回测结果更可能是 Tester 中的执行路径膨胀。

## 设计结论

新版应保留两类模式：

- 兼容复刻模式：`enable_entry_engine=false`。用于复现旧版、做历史回归和差异定位。
- live-safe 模式：`enable_entry_engine=true`，并使用 `FinalizeEntryEngineSignal()`。用于实盘候选和未来优化。

不要把新版默认回退成 direct。direct 可以兼容旧版，但不应作为 live 默认。

## 后续实现建议

当前通过 `enable_entry_engine` 已经能完成旧版兼容。后续可进一步把命名升级为更清晰的入场模式枚举：

- `entry_mode=0`: direct legacy，完全复刻旧版。
- `entry_mode=1`: EntryEngine + legacy finalize，用于隔离 EntryEngine 本身影响。
- `entry_mode=2`: EntryEngine + live-safe finalize，默认 live 模式。

这样新版会更通用：既能完全兼容旧版，也能保留更接近 live 的执行路径。
