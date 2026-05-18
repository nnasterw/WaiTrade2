# 2026-05-18 新版 OB 复刻旧 v95c 参数对比

## 目的

验证新版 `WaiTrade2\WaiTrade_OB` 是否可以通过参数复刻旧版 `WaiTrade\WaiTrade_OB` 的 v95c 行为，并用 MT5 Strategy Tester CLI 做同窗口对比。

## 实现

- `v95c_newob_legacyparams`: 新版 EA，复刻旧 v95c 参数，并关闭新版额外 8-Gap 过滤；`bars=5000`、`ob_scan_depth=0` 全量扫描。30 天回测超时，说明新版检测器不能用全量历史逐 bar 重扫来模拟旧版。
- `v95c_newob_legacyfast`: 新版 EA，保留旧 v95c 关键参数，但限制 `bars=300`、`ob_scan_depth=8`，用于可运行对比。
- `v95c_newob_direct`: 新版 EA，复刻旧 v95c 参数，并显式设置 `enable_entry_engine=false`，对齐旧 `WaiTrade` 默认直接入场路径。
- `v95c_oldob_control`: 旧版 EA 对照，`expert="WaiTrade\WaiTrade_OB"`，使用同一批 v95c 参数。
- 补齐 YAML 到 `.set` 映射：`InpImpulseATRMult`、`InpImpulseLookback`、`InpATRPeriod`、`InpFixedLotSize`、`InpEnablePosMult`、`InpOBScanDepth`、`InpMagicNumber`。

## 30 天 XAUUSDm 结果

窗口：2026.04.18 ~ 2026.05.18，Model 4 Real Ticks，初始资金 200 USD。

| 策略 | EA | 交易数 | 日均 | 胜率 | PF | 余额 |
|------|----|--------|------|------|----|------|
| `v95c_newob_direct` | `WaiTrade2\WaiTrade_OB` | 175 | 5.8 | 48.0% | 0.52 | 45.61 |
| `v95c_newob_legacyfast` | `WaiTrade2\WaiTrade_OB` | 64 | 2.1 | 54.7% | 0.89 | 124.18 |
| `v95c_oldob_control` | `WaiTrade\WaiTrade_OB` | 175 | 5.8 | 48.0% | 0.52 | 45.61 |

## 7 天 XAUUSDm 烟测

窗口：2026.05.11 ~ 2026.05.18。

| 策略 | EA | 交易数 | 日均 | 胜率 | PF | 余额 |
|------|----|--------|------|------|----|------|
| `v95c_newob_direct` | `WaiTrade2\WaiTrade_OB` | 332 | 47.4 | 56.0% | 0.67 | 44.74 |
| `v95c_newob_legacyfast` | `WaiTrade2\WaiTrade_OB` | 22 | 3.1 | 50.0% | 0.99 | 176.46 |
| `v95c_oldob_control` | `WaiTrade\WaiTrade_OB` | 332 | 47.4 | 56.0% | 0.67 | 44.74 |

直接入场模式下，新版 `WaiTrade2` 与旧版 `WaiTrade` 完全一致。旧版 7 天交易数异常高，根因不是 OB 检测差异，而是 `enable_entry_engine=false` 的直接入场路径会在 OB 未 `used` 前被 `ScanSignals` 高频触发；这更像旧回测路径，不适合作为 live-safe 默认。

## 结论

1. 新版 `WaiTrade2\WaiTrade_OB` 已经可以完全复刻当前 MT5 中旧版 `WaiTrade\WaiTrade_OB` 的 v95c 行为，前提是使用同一入场路径：`enable_entry_engine=false`。
2. 上一轮“新版 22/64 笔 vs 旧版 332/175 笔”的巨大差异，根因是入场路径不一致：新版复刻策略开了 EntryEngine，而旧版对照没有开。
3. 更接近真实 live 的是新版 EntryEngine + `FinalizeEntryEngineSignal()` 路径，而不是旧 direct 路径：
   - EntryEngine 触及后等待 tick 级 bounce，减少同一 OB 反复触发。
   - `FinalizeEntryEngineSignal()` 用真实 bid/ask 重新计算 entry/risk/lot，并复核 spread、margin、最小风险、offset。
   - direct 路径在 7 天产生 332 笔，明显存在同一区域高频重复入场，live 中会受到滑点、保证金、速率限制和实盘去重的强烈影响。
4. `v95c_newob_legacyparams` 全量扫描版 30 天超时，说明新版检测器不应以全量历史逐 bar 重扫来跑 M1；应使用有限 `ob_scan_depth` 或只检测近端完成 bar。

## 后续建议

- 保留 `enable_entry_engine=false` 作为旧版兼容/回归测试模式。
- live 默认应使用 `enable_entry_engine=true`，并保留 `FinalizeEntryEngineSignal()`，这比旧 direct 更贴近真实成交。
- 若要进一步通用化，应增加更细的执行模式开关，例如：
  - `entry_mode=0`: direct legacy，完全复刻旧版。
  - `entry_mode=1`: EntryEngine legacy finalize，只做旧手数算法。
  - `entry_mode=2`: EntryEngine live-safe finalize，默认 live 模式。
- 对旧 direct 模式的高频重复入场做单独归因，重点看同一 OB 未及时 `MarkZoneUsed`、多 tick/多 bar 重复触发、以及 `MaxConcurrent` 在快速止损后的路径依赖。
