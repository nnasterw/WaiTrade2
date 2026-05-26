# 2026-05-26 BTC 单策略 R234-R240 诊断

## 目标

继续优化 BTC 单一策略，使用隔离 MT5 Strategy Tester 720 天回测、`backtest_digest.py` 和坏簇分析，目标为：

- 日均开单数 > 4
- 盈利 > 90000u
- 每个月都盈利

窗口：`2024.06.06 ~ 2026.05.26`，脚本计算为 `719` 天，品种 `BTCUSDm`，初始资金 `$200`。

## 基线 R227

`v11_r227_j2_r221_ctx35_merge`

- 交易：3357
- 日均：4.7
- 余额：$66009.26
- 亏损月：8

R227 满足日均，但利润不达标，且 2026-01 / 2026-03 为大额亏损月。诊断发现其一月、三月 context filter 的月初余额门槛为 `100000`，而实际 2026-01/03 月初余额约 `5.3~5.9万`，过滤未生效。

## R234：当前最优候选

`v11_r234_j2_r227_ctx50`

改动：

- 继承 R227
- `context_filter1_min_month_start_balance: 50000.0`
- `context_filter2_min_month_start_balance: 50000.0`

结果：

- 交易：3466
- 日均：4.821
- 余额：$93339.93
- PnL proxy：约 `$93199.72`
- 亏损月：6

R234 已满足日均和盈利两个门槛，并将 R227 的 2026-01 / 2026-03 大亏月修为盈利月：

- 2026-01：+$8452.52
- 2026-03：+$9261.86

剩余亏损月均为低余额启动阶段：

- 2024-09：-$10.50
- 2024-10：-$198.55
- 2024-11：-$221.44
- 2024-12：-$38.11
- 2025-03：-$35.73
- 2025-05：-$153.29

结论：R234 是当前最佳继续迭代起点。

## 失败反例

### R235：启动期 OB 坏簇过滤过宽

`v11_r235_j2_r234_startup_ob_cut`

思路：在月初余额 <=1000 时，用 4 组 startup bad cluster 过滤低余额亏损月的 OB 坏簇。

结果：

- 交易：1998
- 日均：2.8
- 余额：$594.40

结论：静态逐单估计显示能过滤约 `$1029` 历史亏损，但真实 MT5 路径被严重破坏，低余额滚动增长失败。不能沿“大面积启动期 OB 过滤”继续加码。

### R236 / R238 / R239 / R240：低余额月度盈利停手副作用大或等价

`v11_r236_j2_r234_lowbal_pt3`

- 交易：2881
- 日均：4.007
- 余额：$91357.54
- 亏损月：2024-11、2025-10、2025-11

该方案把 2024-09/10/12、2025-03/05 修为正月，但改变了复利路径，导致 2025-10/11 变成高余额负月。

`v11_r238_j2_r234_lowbal_pt3_no_nov` 与 R236 等价，因为 2024-11 月初余额约 `1018`，已经高于 `monthly_profit_target_stop_max_balance=1000`，所以是否列入 11 月不影响。

`v11_r239_j2_r234_lowbal_pt3_max2500` 仍与 R236 汇总一致，说明该路径下 2024-11 不是简单靠扩大低余额盈利停手上限解决。

`v11_r240_j2_r234_lowbal_pt6` 仍与 R236 汇总一致。源码确认月度盈利停手按 `月初余额 * pct / 100` 计算，说明这些月份很早就同时越过 3% 和 6% 阈值，调高到 6% 没有形成路径差异。

### R237：11 月 OB 局部过滤引入 12 月坏路径

`v11_r237_j2_r234_lowbal_pt3_nov_ob`

- 交易：3315
- 日均：4.611
- 余额：$87912.02
- 亏损月：2024-12、2025-11

该方案让 2024-11 转正，但 2024-12 变为 -$1362，并且总盈利跌破 90000。不能使用该组合。

## 下一步建议

继续以 R234 为基线，不要使用 R235 的大面积启动期 OB 过滤，也不要直接使用 R236/R237。

更可能有效的方向：

- 针对 R234 剩余 6 个低余额小负月做更窄的月份/方向/小时过滤，但现有 context filter 只有 3 组，已用于 Jan/Mar/May 高余额修复；如果继续用 context，需要扩展 EA 支持更多 context filter slots，或新增低余额专用 context filter。
- 避免改变高余额复利路径。凡是会让 2025-10/11 月初余额大幅偏离 R234 的方案，需要优先警惕。
- 若只用现有参数，优先尝试较窄的 `low_balance_ob_bad_months/hours` 单月版本，并每次只动一个月份，避免 R237 这种路径跳变。

## 03:00-04:40 后续迭代：R241-R247

### R241：低余额 OB 弱小时过滤

`v11_r241_j2_r234_lowbal_ob_weak`

改动：在 R234 上启用 `low_balance_ob_bad_*`，仅当月初余额 <=2500 时，过滤 3/5/9/10/11/12 月普通 OB 的弱小时。

结果：

- 交易：3853
- 日均：5.36
- 余额：$99376.36
- 亏损月：2025-03、2025-05、2025-10、2025-11

结论：启动期 2024-09/10/11/12 转正，频率和利润更好；但中余额/高余额阶段暴露出新的 2025-03/05/10/11 尾部亏损。

### R242：将低/中余额 OB 过滤上限提高到 10000

`v11_r242_j2_r241_midbal_ob_weak`

改动：继承 R241，仅将 `low_balance_ob_bad_max_month_start_balance` 从 2500 提高到 10000。

结果：

- 交易：3937
- 日均：5.48
- 余额：$118894.97
- 亏损月：2025-10、2025-11

关键月：

- 2025-03：+$0.65
- 2025-05：+$20.03
- 2025-10：-$8168.24
- 2025-11：-$7341.10

结论：R242 是当前比 R234 更强的基线，满足日均和盈利，且只剩两个高余额亏损月。

### R243/R244：高余额 10/11 月盈利停手

`v11_r243_j2_r242_hi_octnov_pt1`

- 交易：3829
- 日均：5.33
- 余额：$128477.73
- 亏损月：2025-10

该版本用 10/11 月高余额 1% 月度盈利停手修复了 2025-11，但 2025-10 仍亏损。

`v11_r244_j2_r242_hi_octnov_pt025` 与 R243 汇总一致。说明 2025-10 在触发 0.25%/1% 停手前已经进入亏损路径，不能靠更低盈利停手修复。

### R247：10 月高余额方向小时过滤

`v11_r247_j2_r242_oct_highbal_dircut_tight`

改动：用 `context_filter3` 改为 10 月高余额方向小时过滤。

结果：

- 交易：4139
- 日均：5.76
- 余额：$123689.92
- 亏损月：2025-11、2026-05

结论：R247 修复了 2025-10，但因为占用了 R242/R234 原本的 May context filter，导致 2026-05 路径变坏；同时 2025-11 也重新变坏。因此不应直接采用 R247。

## 当前最佳与下一步

当前最佳候选：

1. `v11_r242_j2_r241_midbal_ob_weak`：利润最高的未完成候选之一，只剩 2025-10/11 两个负月。
2. `v11_r243_j2_r242_hi_octnov_pt1`：只剩 2025-10 一个负月，余额 $128477.73，日均 5.33。

关键结构性发现：

- 现有 3 个 `context_filter` slot 不够用。R234/R242 需要 Jan/Mar/May context；R247 证明用 slot3 去修 October 会释放 May 保护，导致 2026-05 变坏。
- 下一步更合理的是扩展 EA/YAML 映射，增加 `context_filter4/5`，然后从 R243 或 R242 出发，追加 October high-balance direction-hour filter，而不是替换 May filter。
- 在扩展 slot 前，继续用现有参数会反复出现“修一个月、坏另一个月”的路径搬家。

## 安全状态

所有回测均通过 `scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated` 运行。回测后 live 状态检查通过：

- `streams=7 pass=true`
- `total_pos=0`
- `total_errors=0`
- `stale_heartbeats=0`

未触碰当前 v11a live portable 终端。

## 05:00 复核：R248 / v11a 新隔离回测脚本 720 天通过

策略：`v11_r248_j2_r243_oct_ctx4`

实现改动：扩展 EA/YAML 参数映射，新增 `context_filter4/5` 两组 context filter slot。R248 继承 R243，保留原 `context_filter3` 的 May 保护，并用 `context_filter4` 单独处理 10 月高余额方向小时过滤，避免 R247 那种为了修 2025-10 而释放 2026-05 风险的路径。

回测方式：

```powershell
python scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated -- --strategy v11_r248_j2_r243_oct_ctx4 --symbol BTCUSDm --from 2024.06.06 --to 2026.05.26 --timeout 5400
python scripts\backtest_digest.py --report results\backtest\v11_r248_j2_r243_oct_ctx4_20240606_20260526_20260526.txt --log temp\mt5_tester_isolated\Tester\Agent-127.0.0.1-3000\logs\20260526.log --export-csv
```

结果：

- 交易数：3721
- 日均：5.175
- 胜率：42.1%
- PF：1.62
- 最终余额：$137351.17
- digest 逐单归因覆盖：3721/3721
- 亏损月数：0
- `pnl_proxy` 合计：$137712.03

月度审计：

| 月份 | PnL proxy |
|---|---:|
| 2024-06 | 35.19 |
| 2024-07 | 353.40 |
| 2024-08 | 142.87 |
| 2024-09 | 325.39 |
| 2024-10 | 291.16 |
| 2024-11 | 32.73 |
| 2024-12 | 401.65 |
| 2025-01 | 3438.87 |
| 2025-02 | 831.17 |
| 2025-03 | 0.66 |
| 2025-04 | 1499.04 |
| 2025-05 | 20.12 |
| 2025-06 | 19527.74 |
| 2025-07 | 8827.77 |
| 2025-08 | 29482.60 |
| 2025-09 | 16762.28 |
| 2025-10 | 878.11 |
| 2025-11 | 2777.27 |
| 2025-12 | 17276.52 |
| 2026-01 | 7721.09 |
| 2026-02 | 5486.48 |
| 2026-03 | 9426.62 |
| 2026-04 | 9464.65 |
| 2026-05 | 2708.64 |

结论：按当前 MT5 Strategy Tester CLI + isolated tester 标准，R248 已满足“日均开单数 >4、最终盈利 >90000u、720 天每个月都盈利”。但 2025-03 只有 +$0.66，2025-05 只有 +$20.12，月度安全垫很薄；这说明目标达成的是当前样本内约束，不代表未来能确保盈利，后续如果继续优化，应优先做鲁棒性和扰动验证，而不是只追求更高最终余额。

验证：

- `python -m pytest tests\test_mt5_common.py tests\test_mt5_backtest_isolated_win.py tests\test_mt5_backtest_win.py -q`：104 passed
- live 后验：`streams=7 pass=true`，`stale_heartbeats=0`，`total_errors=0`，当前只有 7 个 v11a portable live terminal，没有 tester/metatester 残留。

## 08:48 固化 v11b 与最近 30 天测试

已将 `v11_r248_j2_r243_oct_ctx4` 固化为正式策略键 `v11b`：

```yaml
v11b:
  <<: *v11_r248_j2_r243_oct_ctx4
  version: V11B
  description: "Official v11b: R248 single BTC strategy with context_filter4 October high-balance protection"
  magic_number: 204408
```

set 生成核对通过：`InpVersion=V11B`、`InpMagicNumber=204408`，并继承 R248 的 May `context_filter3`、October `context_filter4`、low/mid-balance OB weak-hour filter、October/November high-balance monthly profit target stop。

### 最近 30 天主口径：从 $200 独立启动

命令：

```powershell
python scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated -- --strategy v11b --symbol BTCUSDm --from 2026.04.26 --to 2026.05.26 --deposit 200 --timeout 2400
python scripts\backtest_digest.py --report results\backtest\v11b_20260426_20260526_20260526.txt --log temp\mt5_tester_isolated\Tester\Agent-127.0.0.1-3000\logs\20260526.log --export-csv
```

结果：

- 交易数：46
- 日均：1.5
- 胜率：32.6%
- PF：0.51
- 最终余额：$186.82
- `pnl_proxy`：-$13.08
- 月度：2026-04 -$0.13，2026-05 -$12.95

结论：如果把 v11b 当作“今天新账户从 $200 独立启动”的最近 30 天策略，表现不合格，且交易频率低于目标。主要坏簇来自 sweep 信号，尤其 2026-05 的 hour 13 / risk 150-200 / confirm_pos -1.0~-0.6 / SL。

### 最近 30 天辅助口径：承接 720 天尾段高余额

因为 v11b 含多组月初余额阈值过滤，独立 `$200` 启动和 720 天尾段的高余额状态不是同一口径。为判断最近行情本身，补跑高余额近似续跑：

```powershell
python scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated -- --strategy v11b --symbol BTCUSDm --from 2026.04.26 --to 2026.05.26 --deposit 125228.10 --timeout 2400
```

结果另存为 `results\backtest\v11b_20260426_20260526_deposit125228_20260526.*`：

- 交易数：150
- 日均：5.0
- 胜率：45.3%
- PF：0.57
- 最终余额：$125896.70
- `pnl_proxy`：+$668.86

结论：同一最近 30 天，在高余额续跑口径下为小幅盈利且频率达标；与 `$200` 主口径差异来自 v11b 的余额/月初状态依赖，而不是新回测脚本失效。后续若准备把 v11b 用于新小账户 live，必须重新优化“低余额启动期”或拆成启动版/高余额版，不能直接拿 720 天复利路径的尾段表现当新账户预期。

验证：

- `python -m pytest tests\test_mt5_common.py -q`：77 passed
- live 后验：`streams=7 pass=true`，`total_pos=0`，`total_errors=0`，`stale_heartbeats=0`；当前 live 仍是 7 个 v11a portable terminal，未被本次回测影响。

## 10:18 v11b 跨品种 60 天 / 720 天探测

说明：`v11b` 是 BTC-M5 单策略参数，以下跨品种测试是“同参数移植探测”，不是对 XAU/XAG/ETH/USOIL/JPY 的专门调参。JPY 使用 `USDJPYm`，USOIL 使用 `USOILm`，均可被 MT5 tester 正常识别。

命令：

```powershell
python scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated -- --strategy v11b --symbols BTCUSDm,XAUUSDm,XAGUSDm,ETHUSDm,USOILm,USDJPYm --days 60 --timeout 2400
python scripts\mt5_backtest_isolated_win.py --tester-home temp\mt5_tester_isolated -- --strategy v11b --symbols BTCUSDm,XAUUSDm,XAGUSDm,ETHUSDm,USOILm,USDJPYm --from 2024.06.06 --to 2026.05.26 --timeout 5400
```

60 天结果，区间 `2026.03.27 ~ 2026.05.26`，初始资金 $200：

| 品种 | 交易 | 日均 | 胜率 | PF | 余额 |
|---|---:|---:|---:|---:|---:|
| BTCUSDm | 291 | 4.8 | 37.5% | 1.31 | 871.08 |
| XAUUSDm | 14 | 0.2 | 28.6% | 0.74 | 150.77 |
| XAGUSDm | 9 | 0.1 | 55.6% | 0.72 | 149.12 |
| ETHUSDm | 14 | 0.2 | 21.4% | 2.60 | 233.41 |
| USOILm | 35 | 0.6 | 37.1% | 0.14 | 106.68 |
| USDJPYm | 98 | 1.6 | 44.9% | 1.94 | 221.30 |

720 天结果，区间 `2024.06.06 ~ 2026.05.26`，初始资金 $200：

| 品种 | 交易 | 日均 | 胜率 | PF | 余额 |
|---|---:|---:|---:|---:|---:|
| BTCUSDm | 3727 | 5.2 | 42.2% | 1.62 | 137351.62 |
| XAUUSDm | 453 | 0.6 | 39.7% | 0.86 | 39.88 |
| XAGUSDm | 11 | 0.0 | 18.2% | 0.20 | 30.50 |
| ETHUSDm | 236 | 0.3 | 38.6% | 0.75 | 65.26 |
| USOILm | 728 | 1.0 | 40.2% | 0.93 | 147.13 |
| USDJPYm | 1717 | 2.4 | 42.4% | 1.02 | 152.17 |

结论：v11b 的优势高度集中在 BTCUSDm。60 天里 ETH/USDJPY 有小赚，但 720 天不稳定且最终低于初始资金；XAU/XAG/USOIL 在两个窗口都不适合直接套用该参数。不要把 v11b 作为多品种通用策略上线；如果要扩品种，应为每个品种单独重做参数矩阵和风控。

验证：回测均通过 isolated tester；回测后 live 状态 `streams=7 pass=true`，`total_pos=0`，`total_errors=0`，`stale_heartbeats=0`，当前进程只有 7 个 v11a live terminal。
