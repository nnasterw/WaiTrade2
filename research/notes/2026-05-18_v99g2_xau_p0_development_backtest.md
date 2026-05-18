# 2026-05-18 v99g2 XAU P0开发与回测对比

## 背景

基于 `v99g2` XAU 180天日志分析，本轮优先实现三个 P0 能力：

1. 入场小时黑名单：避开前次分析中净负的 `0,9,12,17,18` 点。
2. 仓位上限：支持 `max_pos_mult` 与 `max_lot_size`，控制高乘数/大手数尾部风险。
3. 交易请求失败冷却：闭市或请求失败后不再每 tick 暴力重试，覆盖开仓、SL修改、部分平仓、主动平仓。

所有新参数默认关闭，基线 `v99g2` 行为不变。

## 实现

- `Config.mqh` 新增：
  - `InpMaxPosMult`
  - `InpMaxLotSize`
  - `InpNoEntryHours`
  - `InpCloseRetryCooldownSec`
- `SignalEngine.mqh`：
  - 直接入场与 EntryEngine 最终确认均执行 `InpNoEntryHours`。
  - `CalcPositionMultiplier` / 评分乘数之后应用 `InpMaxPosMult`。
  - 手数计算和保证金缩量后应用 `InpMaxLotSize`。
- `WaiTrade_OB.mq5`：
  - `ExecuteSignal` 改为返回真实开仓成功与否，避免失败请求也推进本地仓位计数。
  - 开仓失败后按 `InpCloseRetryCooldownSec` 冷却。
- `PositionManager.mqh`：
  - BE、Trailing、DTP锁盈、DTP/Decay/Time 主动退出、部分平仓失败后按 `InpCloseRetryCooldownSec` 冷却。
- `yaml_to_set.py` / `strategies.yaml` / tests 同步参数映射。

## 实验设计

窗口：`2025.11.19 ~ 2026.05.18`，180天
品种：`XAUUSDm`
模型：MT5 Strategy Tester CLI，Real Ticks，初始资金 `$200`

| 策略 | 变量 |
| --- | --- |
| `v99g2` | 基线 |
| `xau_g2_nohours` | 仅禁入 `0,9,12,17,18` 点 |
| `xau_g2_cap8` | 仅 `max_pos_mult=8`, `max_lot_size=0.08` |
| `xau_g2_p0_guard` | 时段过滤 + cap + 失败冷却60秒 |

## 回测结果

| 策略 | 交易 | 日均 | 胜率 | PF | 余额 | 相对基线 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `v99g2` | 328 | 1.8 | 54.3% | 1.16 | `$313.06` | 1.00x |
| `xau_g2_nohours` | 235 | 1.3 | 59.1% | 2.62 | `$2211.12` | 7.06x |
| `xau_g2_cap8` | 328 | 1.8 | 54.3% | 1.05 | `$543.80` | 1.74x |
| `xau_g2_p0_guard` | 235 | 1.3 | 59.1% | 2.44 | `$1898.25` | 6.06x |

## Live贴近度检查

Agent日志中闭市请求噪声：

| 策略 | failed market entry | failed modify | Market closed总计 |
| --- | ---: | ---: | ---: |
| `v99g2` | 13062 | 28728 | 41803 |
| `xau_g2_nohours` | 13062 | 28728 | 41803 |
| `xau_g2_cap8` | 13062 | 28728 | 41803 |
| `xau_g2_p0_guard` | 79 | 282 | 374 |

说明：纯时段过滤收益最高，但仍保留大量闭市交易请求噪声；组合候选收益略低，但交易请求行为更接近 live，尤其避免闭市期间每 tick 重复开仓/改SL。

## 结论

1. XAU 的主要改进来自时段过滤，不是仓位 cap。过滤 `0,9,12,17,18` 后交易数减少 28.4%，胜率提高 4.8 pct，PF 从 1.16 提到 2.62。
2. 仓位 cap 单独使用能提高最终余额，但 PF 下降到 1.05，说明它更多是在改变复利路径和限制极端仓位，而不是提升信号质量。
3. `xau_g2_p0_guard` 更适合作为 live 候选：余额低于纯时段版，但大幅降低闭市请求噪声，避免回测与 live 在失败重试频率上失真。
4. 下一步不要直接定版为全品种参数。需要单独验证 XAG/EUR 是否适用同一 no-entry hours；XAU 可以继续细化小时集合，例如只禁 `0,9,12,17,18` 的子集或加入 `21` 闭市保护。
