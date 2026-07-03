# v99g1 XAU 线上基准 vs 本地 Win MT5 EA 回测对比

> 日期: 2026-05-17  
> 目标: 用 WaiTrade2 的 MT5 EA 模块复现线上 `v99g1` XAU 180天结果，并核对日均单数、胜率、盈亏比/PF 等指标。

## 结论

本地 Win MT5 EA 回测的核心交易结果与线上/文档基准对齐：

| 来源 | 周期 | 品种 | 交易 | 日均 | 胜率 | PF | 净利润 | 余额 |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| 线上基准 `strategy_versions/v9.9_final.md` | 180天 | XAUUSDm | 390 | 2.2 | 57.2% | 1.13 | +$147 | $347 |
| 本地 Win MT5 `v99g1_XAUUSDm_20260517.htm` | 180天 | XAUUSDm | 390 | 2.2 | 57.18% | 1.13 | +$146.73 | $346.73 |

因此：参数、EA 执行路径、交易数、胜率和 PF 都已复现线上 XAU 结果。

## 本地回测配置

- 项目: WaiTrade2
- EA: `WaiTrade\WaiTrade_OB`
- Preset: `v99g1.set`
- Symbol: `XAUUSDm`
- Period: `M1`
- Model: `4` (Every tick based on real ticks)
- From/To: `2025.11.17` → `2026.05.16`
- Deposit: `$200`
- INI Leverage: `2000`
- 关键参数:
  - `InpBarTF=5`
  - `InpBouncePct=0.4`
  - `InpTimeoutMin=90`
  - `InpBreakevenR=1.0`
  - `InpBreakevenLockR=0.5`
  - `InpDTPTriggerR=2.0`
  - `InpDTPRetrace=0.2`
  - `InpMaxConcurrent=1`
  - `InpEnableEntryEngine=true`

## 必须注意的环境差异

本地报告虽然复现了核心结果，但环境有效性仍要打标：

- HTML 报告实际杠杆显示 `1:100`，不是 INI 写入的 `1:2000`。
- HTML 历史质量显示 `75%真实报价`。
- Tester 日志显示真实 tick 从 `2026.05.01` 才开始，且存在 `real ticks absent ... every tick generation used`。
- 因此本地 Win 回测可用于“复现线上结果/排查执行路径”，但不应单独作为上线选型依据；上线判断仍需使用线上 Mac MT5 的完整报告头部和日志核验。

## 工具问题

`scripts/mt5_backtest_win.py` 本次实际跑完并生成了 HTML 报告，但脚本只查找 `Tester/Agent-127.0.0.1-3000/logs/YYYYMMDD.log`，本机实际日志在 `Tester/logs/YYYYMMDD.log`，导致 CLI 汇总写成“回测失败或无数据”。

真实结果应以生成的 HTML 报告为准。后续建议修复 Windows 回测脚本：当 Agent 日志不存在时，回退解析 `Tester/logs` 或 HTML 报告。