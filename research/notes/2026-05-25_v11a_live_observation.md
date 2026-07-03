# 2026-05-25 v11a live 阶段观察

## 背景

用户要求暂停回测策略，先运行 v11a live，重点观察一天真实 live 表现。

v11a 当前以 7 条 BTC 腿运行：

- R224
- R225
- R226
- R211M
- R213D
- R216M
- R227

部署方式为 7 个 portable MT5 终端分别加载同一个 `WaiTrade_OB` EA 的不同参数实例。该方式共享 broker 账户持仓和成交，但 MT5 Global Variables 是终端本地状态，因此共享月度风控不等价于单终端多图表部署。当前 live 观察主要用于验证组合信号、真实执行、稳定性、重复入场风险和交易错误。

## 13:50 阶段状态

状态刷新时间：2026-05-25 13:50:51 +08:00。

状态报告：`results/live/v11a_live_status_current.md`。

结论：

- 7 个 `terminal64.exe` 均在线，路径均位于 `temp/mt5_portable_v11a/<stream>/terminal64.exe`。
- 7 条腿均显示 `authorized=true`、`trading=true`、`loaded=true`。
- `portfolio_live_status.py` 输出 `streams=7 pass=true`。
- 最近 24 小时窗口内开仓 0、平仓 0、交易错误 0。
- 心跳均新鲜，约 28-34 分钟前。
- R211M 与 R213D 当前检测到 `ob=1`，但尚未触发入场；其他腿 `ob=0`。
- R225 与 R227 各记录 1 次短线断连，当前已自动恢复，未伴随交易错误。

## 当前判断

启动后约 30 分钟，还不能评价“一天表现”或策略盈利性。当前有效结论仅限于：

1. v11a live 部署已经实际运行，而不是只生成 profile。
2. 7 条腿均能加载 EA、登录账户、开启自动交易并持续输出心跳。
3. 到目前为止没有乱开单、重复开仓或交易执行错误。
4. 后续复盘应重点看真实成交数量、成交质量、是否触发重复入场、断连是否扩大、以及净 PnL。

## 后续检查点

- 继续保持回测暂停，直到完成至少 24 小时 live 观察。
- 24 小时复盘时优先运行：

```powershell
python scripts\portfolio_live_status.py --since-hours 24 --max-heartbeat-age-min 75 --output results\live\v11a_live_status_review.md
```

- 若仍无成交，需要区分是行情没有触发、过滤过严，还是 live 与回测信号路径存在差异。

## 13:54 监控补强

`scripts/portfolio_live_status.py` 增加 `uptime_min` 与 `started` 两列，用于复盘时确认 7 个 portable 终端是否连续运行，而不是中途被重启后只保留了健康表象。

验证：

```powershell
python -m pytest tests\test_portfolio_live_status.py -q
```

结果：5 passed。

最新报告仍为 `streams=7 pass=true`，7 条腿运行约 32-38 分钟；开仓 0、平仓 0、交易错误 0。R211M 与 R213D 仍为 `ob=1`、`pos=0`。断连计数显示 R225、R226、R227 各 1 次，当前均已恢复且未伴随交易错误。

## 13:56 复盘元数据

`scripts/portfolio_live_status.py` 增加 `generated_at` 与 `window_since`，避免后续查看历史报告时混淆报告生成时间和日志心跳时间。

验证：

```powershell
python -m pytest tests\test_portfolio_live_status.py -q
python scripts\portfolio_live_status.py --since-hours 24 --output results\live\v11a_live_status_current.md
```

结果：6 passed；报告为 `streams=7 pass=true`，`generated_at=2026-05-25 13:56:41`，`window_since=2026-05-24 13:56:41`。

当前 live 状态仍为开仓 0、平仓 0、交易错误 0。R226 的短线断连计数增至 2，R225 与 R227 各 1；所有终端仍授权正常、自动交易正常、心跳新鲜。

## 13:58 连续运行门槛

`scripts/portfolio_live_status.py` 增加 `--min-uptime-min` 参数和 `uptime_ok` 列。普通健康检查不设置该参数时仍只判断进程、授权、自动交易、EA loaded、guard 和 heartbeat；24 小时复盘时设置 `--min-uptime-min 1320`，可识别终端是否中途重启或没有连续运行接近一天。

验证：

```powershell
python -m pytest tests\test_portfolio_live_status.py -q
python scripts\portfolio_live_status.py --since-hours 24 --output results\live\v11a_live_status_current.md
python scripts\portfolio_live_status.py --since-hours 24 --min-uptime-min 1320 --output results\live\v11a_live_status_uptime_probe.md
```

结果：

- 单测 7 passed。
- 普通 live 状态 `streams=7 pass=true`。
- 1320 分钟探针当前 `pass=false`，符合预期，因为 7 条腿只运行约 36-42 分钟；这证明明天复盘能抓到“没有连续跑满一天”的情况。

已同步更新 `v11a-live` 自动复盘任务，使其使用 `--min-uptime-min 1320`。

## 14:02 断连/错误摘要

`scripts/portfolio_live_status.py` 增加 `last_disconnect` 与 `last_error` 两列。这样一天复盘时不仅能看到断连/错误计数，还能直接看到最近一次断连或交易错误的日志摘要。

验证：

```powershell
python -m pytest tests\test_portfolio_live_status.py -q
python scripts\portfolio_live_status.py --since-hours 24 --output results\live\v11a_live_status_current.md
```

结果：9 passed；报告为 `streams=7 pass=true`，`generated_at=2026-05-25 14:02:41`。

当前 live 状态：

- 7 条腿均在线，运行约 40-46 分钟。
- 开仓 0、平仓 0、交易错误 0。
- R211M 与 R213D 仍为 `ob=1`、`pos=0`。
- R225 最近断连：13:31:37。
- R226 最近断连：13:54:32。
- R227 最近断连：13:31:22。
- `last_error` 全部为空，说明这些断连未伴随交易层错误。

## 14:03 当前巡检

状态刷新时间：2026-05-25 14:03:46。

结果：

- `streams=7 pass=true`。
- 7 条腿进程均仍来自 `temp/mt5_portable_v11a/<stream>/terminal64.exe`。
- 运行时长约 41-47 分钟。
- 开仓 0、平仓 0、交易错误 0。
- R211M 与 R213D 仍为 `ob=1`、`pos=0`。
- R225/R226/R227 的断连计数未造成交易错误；`last_error` 全部为空。
- 自动复盘任务 `v11a-live` 已确认包含命令参数 `--min-uptime-min 1320`，用于明天验证接近 24 小时连续运行。

当前结论仍只能评价 live 稳定性，不能评价策略盈利性。若 24 小时后仍无成交，需要检查 live 信号触发频率是否明显低于回测中的同类腿。

## 14:06 重连确认

`scripts/portfolio_live_status.py` 增加 `reconnects` 与 `last_reconnect` 两列。断连后只有出现新的 `authorized on ... through` 日志才计入重连，避免只看到 `disconnects` 而误判连接仍未恢复。

验证：

```powershell
python -m pytest tests\test_portfolio_live_status.py -q
python scripts\portfolio_live_status.py --since-hours 24 --output results\live\v11a_live_status_current.md
```

结果：10 passed；报告为 `streams=7 pass=true`，`generated_at=2026-05-25 14:06:35`。

连接状态：

- R225：断连 1 次，重连 1 次，最近重连 13:31:37。
- R226：断连 2 次，重连 2 次，最近重连 13:54:33。
- R227：断连 1 次，重连 1 次，最近重连 13:31:22。
- 其他腿无断连。
- 所有 `last_error` 为空。

交易状态仍为开仓 0、平仓 0、交易错误 0。R211M 与 R213D 仍有 OB 但没有持仓。

## 14:08 组合汇总

`scripts/portfolio_live_status.py` 增加 `Summary` 区，直接汇总 7 条腿的组合级状态：

- `total_pos`
- `ob_streams`
- `total_opens`
- `total_closes`
- `total_errors`
- `total_disconnects`
- `total_reconnects`
- `stale_heartbeats`
- `uptime_ok_streams`
- `min_uptime_min_seen`

验证：

```powershell
python -m pytest tests\test_portfolio_live_status.py -q
python scripts\portfolio_live_status.py --since-hours 24 --output results\live\v11a_live_status_current.md
```

结果：12 passed；报告为 `streams=7 pass=true`，`generated_at=2026-05-25 14:08:55`。

当前组合级状态：

- `total_pos=0`
- `ob_streams=2`
- `total_opens=0`
- `total_closes=0`
- `total_errors=0`
- `total_disconnects=4`
- `total_reconnects=4`
- `stale_heartbeats=0`
- `uptime_ok_streams=7/7`
- `min_uptime_min_seen=46`

该状态说明当前 live 观察仍是“稳定运行但尚无真实成交”的阶段。

## 14:11 巡检

状态刷新时间：2026-05-25 14:11:14。

验证：

```powershell
python scripts\portfolio_live_status.py --since-hours 24 --output results\live\v11a_live_status_current.md
python -m pytest tests\test_portfolio_live_status.py -q
```

结果：

- `streams=7 pass=true`
- `total_pos=0`
- `ob_streams=2`
- `total_opens=0`
- `total_closes=0`
- `total_errors=0`
- `total_disconnects=4`
- `total_reconnects=4`
- `stale_heartbeats=0`
- `uptime_ok_streams=7/7`
- `min_uptime_min_seen=48`
- 单测 12 passed

当前仍无真实成交，因此不能评价 live 盈利性。可确认的是 7 条腿继续稳定在线，短线断连均已重连，没有交易层错误。

## 14:13 自动复盘心跳提前触发

自动复盘 `v11a-live` 在 2026-05-25 14:12 左右触发，但距离 v11a live 启动只有约 50-56 分钟，尚未满足“一天 live 表现”窗口。

按任务要求运行：

```powershell
python scripts\portfolio_live_status.py --since-hours 24 --max-heartbeat-age-min 75 --min-uptime-min 1320 --output results\live\v11a_live_status_review.md
```

结果：

- `streams=7 pass=false`
- 失败原因：`uptime_ok_streams=0/7`，`min_uptime_min_seen=50`，未达到 `min_uptime_min=1320`
- 健康项本身正常：7 条腿均授权、交易启用、EA loaded、heartbeat 新鲜
- `total_pos=0`
- `total_opens=0`
- `total_closes=0`
- `total_errors=0`
- `total_disconnects=4`
- `total_reconnects=4`
- `stale_heartbeats=0`

额外抽查 `logs` 与 `MQL5/Logs`：

- 终端日志显示各实例同步时均为 `0 positions, 0 orders`
- MQL5 日志只有 `SHARED_GUARD event=init` 与 `HEARTBEAT`
- 未找到开仓、平仓、ticket、retcode、invalid stops、profit/balance/equity 类交易结果
- 当前持仓 0，已平仓成交 0，总 PnL 0，最大浮亏无数据

已更新 `v11a-live` heartbeat，让它继续在下一次 13:30 复查；这次提前触发不作为一天 live 结论。

## 16:08 无开单原因检查

按用户要求继续检查 v11a live 当前无开单是否正常；没有启动任何回测。

验证：

```powershell
python scripts\portfolio_live_status.py --since-hours 24 --max-heartbeat-age-min 75 --output results\live\v11a_live_status_current.md
rg -n 'TRADE|ORDER|DEAL|Position|POSITION|OrderSend|retcode|invalid|reject|OPEN|CLOSE|ENTRY_OK|ENTERED|FINAL_DIAG|MON_DIAG|OB_DIAG|SHARED_GUARD|HEARTBEAT' temp\mt5_portable_v11a -g 20260525.log
```

状态刷新时间：2026-05-25 16:08:29。

结果：

- `streams=7 pass=true`
- `total_pos=0`
- `ob_streams=7`
- `total_opens=0`
- `total_closes=0`
- `total_errors=0`
- `total_disconnects=15`
- `total_reconnects=15`
- `stale_heartbeats=0`
- `uptime_ok_streams=7/7`
- `min_uptime_min_seen=10`

健康性结论：

- 7 个 portable MT5 实例均为 authorized、trading enabled、EA loaded、heartbeat fresh。
- 终端同步日志多次显示 `0 positions, 0 orders`。
- 未发现 `OrderSend`、`retcode`、`invalid stops`、`reject`、开仓、平仓或交易层错误。
- R226 在 15:58 被 `LiveUpdate` 触发重启，日志为 `shutdown with 0`，随后重新加载同一个 `v11a_live_R226_startup.set`；这不是崩溃，但会打断连续 uptime。

无开单解释：

- 当前 7 条腿都有 OB，但有 OB 不等于立即入场。
- R213D/R216M 开启了 `InpEnableEntryDebug=true`，其余腿未开启 entry debug。
- R213D：`OB_DIAG=56`，其中 `skip=state_filter=52`，`status=REGISTERED=4`。
- R216M：`OB_DIAG=22`，其中 `skip=state_filter=20`，`status=REGISTERED=2`。
- 两条 debug 腿均未出现 `MON_DIAG`、`TOUCHED`、`BOUNCE`、`ENTERED`、`FINAL_DIAG`。
- 因此当前主要停在“早期卖向 OB 被 state filter 拦截；16:00 后有 OB 注册成功，但尚未触及 entry depth/bounce 条件”的阶段。

参数确认：

- 7 条腿 startup preset 均为 `InpEnableEntryEngine=true`。
- 入场条件包含 `InpEntryDepthFilter=true`、`InpEntryDepthPct=0.67`、`InpBouncePct=0.25`、`InpMaxEntryOffsetR=0.5`、`InpMinRiskSpreadRatio=5.0`、`InpEnableStateFilter=true`、`InpCooldownBars=1`。
- 启动日志确认读取的是各实例 `MQL5\Presets\v11a_live_<stream>_startup.set`，不是 R226 目录中的旧 Tester `WaiTrade_OB.set`。

当前判断：

短窗口无开单目前正常，表现为 EA 正常在线并等待严格入场条件，而不是授权、EA 加载、交易权限、订单拒绝或风控异常。若运行满 12-24 小时后仍然 0 opens，需要进一步打开更多腿的 entry debug，并统计 live tick 是否触达 depth/bounce 条件。

## 16:42 客户端更新后重启

用户反馈 MT5 客户端提示更新重启。重启前先运行：

```powershell
python scripts\portfolio_live_status.py --since-hours 24 --max-heartbeat-age-min 75 --output results\live\v11a_live_status_before_restart.md
```

重启前状态：

- 7 条腿进程已不可检测，终端日志显示 16:35 左右 `shutdown with 0`。
- 账户同步仍为 `0 positions, 0 orders`。
- `total_opens=0`，`total_closes=0`，`total_errors=0`。

随后按各自 portable 目录的 startup 配置重新启动：

```powershell
temp\mt5_portable_v11a\<stream>\terminal64.exe /portable /config:temp\mt5_portable_v11a\<stream>\v11a_live_<stream>_startup.ini
```

新进程：

- R211M pid=7824
- R213D pid=27016
- R216M pid=40024
- R224 pid=38968
- R225 pid=27516
- R226 pid=21624
- R227 pid=37160

重启后验证：

```powershell
python scripts\portfolio_live_status.py --since-hours 24 --max-heartbeat-age-min 75 --output results\live\v11a_live_status_after_restart.md
python -m pytest tests\test_portfolio_live_status.py -q
```

结果：

- `streams=7 pass=true`
- `total_pos=0`
- `ob_streams=6`
- `total_opens=0`
- `total_closes=0`
- `total_errors=0`
- `total_disconnects=26`
- `total_reconnects=26`
- `stale_heartbeats=0`
- `uptime_ok_streams=7/7`
- `min_uptime_min_seen=4`
- 单测 `13 passed`

额外修复：

- `scripts/portfolio_live_status.py` 的 `newest_log()` 之前会把 `logs\metaeditor.log` 当作最新终端日志，导致重启后编译日志较新时误判 authorized/trading/loaded 为 false。
- 已改为只选择 `YYYYMMDD.log` 形式的 MT5 terminal/MQL5 日志，并补充 `test_newest_log_ignores_metaeditor_log`。

结论：

v11a live 已按 7 个 portable 终端重启完成，全部重新授权、交易启用、EA loaded、shared guard load、heartbeat fresh。此次更新重启会打断 24h 连续 uptime，明天复盘时需要把 16:35-16:38 这段客户端更新重启作为已知维护窗口处理。

## 19:45 无开单复查

用户再次询问 live 没开单是否正常；本次仍未启动任何回测。

验证：

```powershell
python scripts\portfolio_live_status.py --since-hours 24 --max-heartbeat-age-min 75 --output results\live\v11a_live_status_current.md
rg -n "OrderSend|retcode|invalid|reject|ENTRY_OK|ENTERED|FINAL_DIAG|MON_DIAG|TOUCHED|BOUNCE|OB_DIAG|skip=|status=REGISTERED" temp\mt5_portable_v11a -g 20260525.log
```

状态刷新时间：2026-05-25 19:45:52。

健康状态：

- `streams=7 pass=true`
- 7 个 portable MT5 进程均仍在运行，重启后 uptime 约 188 分钟。
- `authorized=true`、`trading=true`、`loaded=true`、heartbeat 新鲜。
- `total_pos=0`
- `total_opens=0`
- `total_closes=0`
- `total_errors=0`
- `total_disconnects=31`
- `total_reconnects=31`
- `ob_streams=7`

入场诊断：

- R213D 开启 entry debug：`OB_DIAG=148`，`REGISTERED=64`，`MON_DIAG=114`，`TOUCHED=38`，`BOUNCE_CONFIRMED=38`，`ENTERED=19`，`FINAL_DIAG=19`。
- R216M 开启 entry debug：`OB_DIAG=84`，`REGISTERED=32`，`MON_DIAG=51`，`TOUCHED=17`，`BOUNCE_CONFIRMED=17`，`ENTERED=9`，`FINAL_DIAG=9`。
- 两条 debug 腿均无 `OrderSend`、`retcode`、`invalid stops`、`reject`。

无开单原因：

- 这次不是完全没到入场阶段；R213D/R216M 多次完成 touch 与 bounce，进入 EntryEngine 的 `ENTERED`。
- 多数最终被 `FINAL_DIAG ... skip=entry_hours` 拦截，或被 `MON_DIAG ... status=BLOCKED offset_r=... max=0.5` 拦截。
- 当前小时 19 对 R213D/R216M 本来就是禁入小时：R213D 的 `InpNoEntryHours` 包含 19；R216M 的 `InpNoEntryHours` 也包含 19。
- `InpMaxEntryOffsetR=0.5`，日志中多次 `offset_r` 为 0.59-1.22，超过允许追价范围，因此按配置拒绝入场。

当前判断：

19:45 的无开单属于策略过滤导致的正常无成交，不是 EA 停止、未授权、交易禁用、券商拒单或风控报错。后续若进入允许小时仍长期 0 opens，需要打开更多腿的 `InpEnableEntryDebug` 或增强 live status 统计，才能判断非 debug 腿是否也在被 context/offset/hour 过滤。

## 22:36 隔离回测改造评估

用户要求开始评估一边跑 v11a live 一边继续 MT5 Strategy Tester 回测迭代的隔离改造。

当前 live 状态：

- `streams=7 pass=true`
- `total_pos=8`
- R224/R225/R226/R227 各显示 `pos=2`
- `total_errors=0`
- 7 个 portable 终端均 authorized、trading enabled、EA loaded、heartbeat fresh

因此当前不允许做任何会全局影响 `terminal64.exe` 的实验性回测启动。

主要风险点：

- `scripts/mt5_backtest_win.py` 的 `run_mt5()` 在启动回测前会调用 `kill_mt5()`。
- `kill_mt5()` 当前执行 `taskkill /F /IM terminal64.exe` 与 `taskkill /F /IM metatester64.exe`，会杀掉所有同名进程，包括 v11a live 的 7 个 portable 终端。
- Wine/macOS 回测脚本也有类似 `pkill -f terminal64.exe` 风险。
- `mt5_backtest_win.py` 的 `MT5_DATA` 与 `MT5_HOME` 可由环境变量覆盖，但默认仍指向主 MT5 数据目录，不是专用隔离 tester。
- 编译脚本 `mt5_compile_win.py` 会把 MQL5 文件同步到传入的 `mt5_data`，所以隔离 runner 必须显式传入 tester 专用 `MT5_DATA`，不能写 live portable 目录。

建议的最小隔离方案：

1. 创建专用 tester portable 目录，例如 `temp\mt5_tester_isolated`，只用于回测。
2. 回测 runner 只使用该目录的 `terminal64.exe`、`MetaEditor64.exe`、`MQL5`、`Tester`、`config`。
3. 禁止全局 `taskkill /IM terminal64.exe`；改成只终止“路径在 tester isolated 目录内”的 terminal/metatester，或者只终止 runner 自己启动并记录的 PID。
4. `INI_DIR`、`REPORT_DIR`、`MT5_TESTER_PROFILES`、`MT5_EXPERTS`、`TESTER_LOG_DIRS` 全部绑定到 tester isolated 目录。
5. 启动前后自动运行 `portfolio_live_status.py`，若 live 持仓/进程/heartbeat 异常则立即停止回测任务。
6. 第一阶段只允许单实例、非优化回测；禁止并发多 MT5 tester。

当前结论：

隔离改造可行，但必须先实现 runner/路径/PID 级隔离后才能恢复 MT5 Strategy Tester 回测。当前 live 已有持仓，不能直接运行现有 `mt5_backtest_win.py`。

## 22:55 隔离回测改造第一阶段完成

已完成第一阶段最小安全改造，未启动任何 MT5 Strategy Tester 回测。

改造内容：

- `scripts/mt5_backtest_win.py` 的 `kill_mt5()` 不再全局 `taskkill /IM terminal64.exe` / `metatester64.exe`，改为 PowerShell 按 `MT5_HOME` 路径过滤，只停止运行路径等于 tester root 或位于 tester root 子目录内的 MT5 进程。
- `run_mt5()` 支持 `MT5_PORTABLE=1` 时追加 `/portable`，并以 `MT5_HOME` 作为工作目录启动，避免默认写入主 MT5 数据目录。
- `parse_agent_log()` 增加日志 offset 快照与 symbol/date 匹配，优先解析本轮回测新写入的 Tester 日志段，降低同日多次回测日志混段风险。
- 新增 `scripts/mt5_backtest_isolated_win.py`，作为隔离入口：显式要求 `--tester-home` 指向专用 portable 目录，设置 `MT5_HOME=MT5_DATA=tester_home` 和 `MT5_PORTABLE=1` 后再调用原 Windows 回测脚本。
- 隔离入口拒绝使用 `temp\mt5_portable_v11a` live portable 目录、其子目录、以及其父目录作为 tester home，防止误把 live 目录纳入回测清理范围。

验证：

```powershell
python -m pytest tests\test_mt5_backtest_win.py tests\test_mt5_backtest_isolated_win.py -q
python scripts\portfolio_live_status.py --since-hours 24 --max-heartbeat-age-min 75 --output results\live\v11a_live_status_current.md
```

阶段结论：

- 相关单测通过：`36 passed`，覆盖 Windows 回测 runner、隔离 wrapper、live status。
- live 复查通过：`streams=7 pass=true`，`total_pos=8`，`total_errors=0`，`stale_heartbeats=0`。
- 当前还没有创建/复制专用 `temp\mt5_tester_isolated` portable MT5，因此隔离 wrapper 现在会在缺少 `terminal64.exe` 时安全退出。
- 下一阶段才能准备 tester portable 目录，并在回测前后强制跑 live status；在此之前仍不启动 MT5 Strategy Tester。

## 23:45 隔离 tester 准备与 live guard 加固

继续按“不影响当前 live”的原则推进，仍未启动任何真实回测。

新增加固：

- `scripts/mt5_backtest_isolated_win.py` 增加 `run_live_guard()`：
  - 回测前运行 `portfolio_live_status.py --since-hours 24 --max-heartbeat-age-min 75`。
  - 必须看到 `streams=7 pass=true` 才允许调用底层 `mt5_backtest_win.py`。
  - 回测结束后使用 `finally` 再跑一次 live status，即使底层回测失败也会复查 live。
  - 报告写入 `results\live\v11a_live_status_before_isolated_backtest.md` 和 `results\live\v11a_live_status_after_isolated_backtest.md`。
- 新增 `scripts/mt5_prepare_isolated_tester_win.py`：
  - 默认从非 live 的 `temp\mt5_portable` 复制到 `temp\mt5_tester_isolated`。
  - 源目录和目标目录都拒绝 live portable 路径、live 子目录、live 父目录。
  - 源或目标目录下如有 `terminal64/metatester64` 进程在跑则拒绝复制/替换。
  - 路径判断使用目录边界，避免 `temp\mt5_portable` 误匹配 `temp\mt5_portable_v11a`。

实际执行：

```powershell
python -m pytest tests\test_mt5_backtest_win.py tests\test_mt5_backtest_isolated_win.py tests\test_mt5_prepare_isolated_tester_win.py tests\test_portfolio_live_status.py -q
python scripts\mt5_prepare_isolated_tester_win.py --source-home temp\mt5_portable --tester-home temp\mt5_tester_isolated
python scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated -- --strategy __missing_strategy__ --symbol BTCUSDm --days 1
python scripts\portfolio_live_status.py --since-hours 24 --max-heartbeat-age-min 75 --output results\live\v11a_live_status_current.md
```

验证结果：

- 单测通过：`47 passed`。
- `temp\mt5_tester_isolated` 已准备完成。
- 安全空转失败在“策略不存在”，未进入 MT5 terminal 启动阶段；但 live before/after guard 已实际执行。
- 当前 tester isolated 下没有运行中的 `terminal64/metatester64`。
- 当前全机 MT5 进程仍只有 v11a live 的 7 个 terminal，PID 未变。
- live 复查：`streams=7 pass=true`，`total_pos=0`，`total_errors=0`，`stale_heartbeats=0`，`uptime_ok_streams=7/7`。

## 23:59 v11a 近 30 天隔离 MT5 回测

用户要求回测 v11a 近 30 天表现。窗口按北京时间当前日期取 `2026.04.25 ~ 2026.05.25`，品种 `BTCUSDm`，Model 4 real ticks，初始资金 `$200`。

执行前保护：

- 使用隔离入口 `scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated`。
- live guard 回测前后均通过。
- 全程不启动、不停止、不修改 `temp\mt5_portable_v11a` 的 live 终端。
- 初次运行失败原因是隔离 tester 缺 `accounts.dat`，日志为 `tester not started because the account is not specified`；随后只读复制 R224 live portable 的 `accounts.dat/common.ini/servers.dat` 到 `temp\mt5_tester_isolated\config`，不改 live。
- 隔离 tester 的旧 `WaiTrade_OB.ex5` 为 2026-05-21 旧版；MetaEditor 在 portable 隔离目录下仍去默认 AppData include 目录找头文件，编译失败。因此改为只读复制 live R224 当前 `WaiTrade_OB.ex5` 到隔离 tester。live 七腿 ex5 hash 一致。

命令：

```powershell
python scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated -- --strategy v11_r224_j2_r186_ctx35 --symbol BTCUSDm --from 2026.04.25 --to 2026.05.25 --timeout 900
python scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated -- --strategies v11_r225_j2_r196_ctx35,v11_r226_j2_r212_ctx3,v11_r211_j2_r142_h20_risk220,v11_r213_j2_r104_dec_hours_patch,v11_r216_j2_r215_march_hours_patch,v11_r227_j2_r221_ctx35_merge --symbol BTCUSDm --from 2026.04.25 --to 2026.05.25 --timeout 900
python scripts\portfolio_live_status.py --since-hours 24 --max-heartbeat-age-min 75 --output results\live\v11a_live_status_after_backtest_30d.md
```

单腿结果：

| leg | strategy | trades | daily | win_rate | final | pnl |
|---|---|---:|---:|---:|---:|---:|
| R224 | `v11_r224_j2_r186_ctx35` | 36 | 1.2 | 38.9% | $141.63 | -$58.37 |
| R225 | `v11_r225_j2_r196_ctx35` | 36 | 1.2 | 38.9% | $141.63 | -$58.37 |
| R226 | `v11_r226_j2_r212_ctx3` | 49 | 1.6 | 36.7% | $124.77 | -$75.23 |
| R211M | `v11_r211_j2_r142_h20_risk220` | 0 | 0.0 | 0.0% | $200.00 | $0.00 |
| R213D | `v11_r213_j2_r104_dec_hours_patch` | 0 | 0.0 | 0.0% | $200.00 | $0.00 |
| R216M | `v11_r216_j2_r215_march_hours_patch` | 0 | 0.0 | 0.0% | $200.00 | $0.00 |
| R227 | `v11_r227_j2_r221_ctx35_merge` | 49 | 1.6 | 36.7% | $124.77 | -$75.23 |

汇总口径：

- 七腿独立 MT5 单腿结果简单相加：`170` 笔，合计 PnL `-$267.20`。
- 该汇总不是单终端 shared GlobalVariable 组合回测；当前 live 也是 7 个 portable 终端，GlobalVariable 型 shared monthly guard 不跨终端共享。
- 结论：近 30 天单腿 MT5 结果明显偏弱，亏损主要来自 R224/R225/R226/R227，R211M/R213D/R216M 在这个窗口没有成交。

live 后验：

- `streams=7 pass=true`
- `total_pos=0`
- `total_errors=0`
- `stale_heartbeats=0`
- `uptime_ok_streams=7/7`
- 全机 MT5 进程仍只有 v11a live 的 7 个 terminal，PID 未变。

## 2026-05-26 00:46 v11a 720 天隔离脚本复核

用户要求使用 v11a 重新对比 720 天回测，确认新的隔离回测脚本能正常发挥。

前置修复：

- 00:03 首次 live guard 显示 `pass=false`，原因是 R213D/R216M 在 00:00 换日后最新 `20260526.log` 尚未写入下一条 heartbeat，旧版 `portfolio_live_status.py` 只读最新日期日志，误判 `loaded=false` / stale heartbeat。
- 已修复状态脚本：健康检查合并最近两个 `YYYYMMDD.log`，继续忽略 `metaeditor.log`；窗口统计仍按 `--since-hours` 过滤。
- 回归测试：`python -m pytest tests\test_portfolio_live_status.py tests\test_mt5_backtest_isolated_win.py tests\test_mt5_backtest_win.py -q`，`41 passed`。
- 修复后 live guard：`streams=7 pass=true`。

回测设置：

- 隔离入口：`scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated`
- 窗口：`2024.06.06 ~ 2026.05.26`，脚本计算为 `719` 天。
- 品种：`BTCUSDm`
- Model：策略 YAML 内的 Model 4 real ticks。
- EA：隔离 tester 的 `WaiTrade_OB.ex5` 与 live R224 的 hash 一致。

命令：

```powershell
python scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated -- --strategies v11_r224_j2_r186_ctx35,v11_r225_j2_r196_ctx35,v11_r226_j2_r212_ctx3,v11_r211_j2_r142_h20_risk220,v11_r213_j2_r104_dec_hours_patch,v11_r216_j2_r215_march_hours_patch,v11_r227_j2_r221_ctx35_merge --symbol BTCUSDm --from 2024.06.06 --to 2026.05.26 --timeout 1800
```

结果：

| leg | trades | daily | win_rate | final | pnl |
|---|---:|---:|---:|---:|---:|
| R224 | 2287 | 3.2 | 43.6% | $96941.72 | $96741.72 |
| R225 | 1576 | 2.2 | 41.8% | $90264.98 | $90064.98 |
| R226 | 2031 | 2.8 | 43.0% | $42320.57 | $42120.57 |
| R211M | 25 | 0.0 | 80.0% | $222.58 | $22.58 |
| R213D | 19 | 0.0 | 47.4% | $351.59 | $151.59 |
| R216M | 51 | 0.1 | 47.1% | $388.69 | $188.69 |
| R227 | 3357 | 4.7 | 42.1% | $66009.26 | $65809.26 |

汇总：

- 单腿 PnL 简单相加：`$295099.39`
- 总交易数：`9346`
- 简单日均：`13.00`
- 与此前 v11a 基线同量级，说明新的隔离回测脚本、账户配置、EA 同步和日志解析能正常发挥。
- 这仍是七条腿逐条 MT5 Strategy Tester 结果，不是单终端多图共享 GlobalVariable 的组合回测；当前 live 也是 7 个 portable 终端，GlobalVariable 型 shared guard 不跨终端共享。

live 后验：

- `streams=7 pass=true`
- `total_pos=0`
- `total_errors=0`
- `stale_heartbeats=0`
- 全机 MT5 进程仍只有 v11a live 的 7 个 terminal，PID 未变。
