# v10a Windows MT5 回测对齐记录（2026-05-19）

## 背景

目标：回测 `v10a / XAUUSDm / 180d`，并排查 Windows 原生 MT5 脚本与 Wine 脚本的速度/行为差异。

## 发现

- `v10a` 文档定义为 M3，但策略配置没有显式 `period`，旧脚本会退回 `backtest_defaults.period=M1`。
- EA 参数里 `InpBarTF=3` 仍会让策略逻辑按 M3 工作，但 Strategy Tester 外层周期会显示/运行成 M1，和临时 `bt_v10a_180d.ini` 的 `Period=M3` 不一致。
- Windows MT5 的可解析日志实际在 `MT5_DATA/Tester/logs/YYYYMMDD.log`，旧脚本只找 `Tester/Agent-127.0.0.1-3000/logs`，导致回测成功但报告显示“无数据”。
- 部分平仓/多成交场景下，用 Agent 日志按成交两两配对会误算交易数、胜率和 PF；应优先使用 MT5 官方 HTML 报告汇总。

## 修复

- `scripts/mt5_common.py` 新增 `resolve_tester_period()`，策略无 `period` 时从 `bar_period_min` 推断 Tester Period。
- Windows/Wine 回测脚本都改用同一套周期推断逻辑。
- Windows 脚本增加真实日志目录兼容。
- Windows 脚本优先解析 MT5 官方 HTML 报告，并归档到 `results/backtest/`。

## v10a XAUUSDm 180天结果

命令：

```bash
python scripts/mt5_backtest_win.py --strategy v10a --symbol XAUUSDm --from 2025.11.19 --to 2026.05.18 --timeout 600
```

结果：

- Tester Period：M3
- Model：4 Real Ticks
- 端到端耗时：90s
- MT5 核心测试耗时：约 1分级别
- ticks：54,826,125
- bars：57,190
- 交易总计：764
- 胜率：57.72%
- PF：1.91
- 总净盈利：6,757.74 USD
- 余额：6,957.74 USD

输出：

- `results/backtest/v10a_20260519.txt`
- `results/backtest/v10a_XAUUSDm_180d_20260519.htm`
