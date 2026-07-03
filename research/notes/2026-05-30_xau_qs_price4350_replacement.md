# 2026-05-30 XAU QS: price >= 4350 替换条件复核

## 背景

用户指出最新 QS 候选里的 `price >= 4350` 后视镜味道过重，本轮专门验证其真实作用。所有测试均为 MT5 Strategy Tester CLI / Model 4 / Real Ticks / XAUUSDm / 初始资金 `$200`，且通过 `scripts\mt5_backtest_isolated_win.py` 跑在隔离 tester，未影响 live。

## 核心发现

在固定 30 天窗口 `2026.04.29 ~ 2026.05.29` 内，XAU 入场价已经全程高于 4350，因此该条件没有提供额外结构筛选，只是把“低余额阶段切核心小时 + 2 根虚拟止损”打开。

复跑对照：

- `v11xau-qs-highprice-lowbal-core-vsl2-220`：163 笔，胜率 53.4%，余额 `$203.69`。
- `v11xau-qs-lowbal-core-vsl2-220`：去掉绝对价格后同为 163 笔，胜率 53.4%，余额 `$203.69`。

因此 `price >= 4350` 应删除；它在该窗口里是冗余恒真开关。

## 已实现的非后视镜替换条件

新增默认关闭的 context filter 条件：

- `context_filter*_range_tf/range_bars/min_range_atr/max_net_range/min_range_pos/max_range_pos`：用已收盘 HTF 区间、ATR、净推进效率和区间位置替代绝对价格。
- `context_filter*_min_month_range_atr/min_month_range_pos`：用当月截至当前的 D1 区间扩张和当前价在月内区间位置替代绝对价格。
- `context_filter*_min_day/max_day`：验证月末低余额防守是否能解释高价条件收益来源。

验证：

- `python -m pytest tests\test_mt5_common.py -q` -> `89 passed`。
- `python scripts\mt5_compile_win.py --mt5-home temp\mt5_tester_isolated --mt5-data temp\mt5_tester_isolated --log-dir temp\compile_win_isolated` -> `WaiTrade_OB.mq5 success=true warnings=0`。
- `python scripts\mt5_compile_win.py --mt5-home temp\mt5_tester_isolated --mt5-data C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\8B9AA56FE80DC787002685F3915FED97 --log-dir temp\compile_win_isolated_appdata` -> `WaiTrade_OB.mq5 success=true warnings=0`。

## 30 天初筛结果

- HTF 区间扩张/低效率系列：`$45.01 ~ $48.31`，不能替代。
- HTF 区间位置系列：`$44.22 ~ $81.62`，不能替代。
- 月内扩张系列：`$44.23 ~ $78.85`，不能替代；固定 30 天 tester 对月初以来状态可能缺少足够预热历史。
- 月末代理系列：`$45.36 ~ $48.28`，不能替代。
- 低余额无价格版：`v11xau-qs-lowbal-core-vsl2-220` 为 `$203.69`，`218` 为 `$201.45`，`217` 为 `$200.89`。

## 180 天复核

- `v11xau-qs-lowbal-core-vsl2-220`：584 笔，胜率 60.4%，余额 `$1473.81`。
- `v11xau-qs-lowbal-core-vsl2-218`：584 笔，胜率 60.3%，余额 `$1473.31`。
- `v11xau-qs-lowbal-core-vsl2-217`：582 笔，胜率 60.0%，余额 `$1473.77`。

对比 QS 180 天基准 `$2396.58`，低余额无价格版仍明显退化，不能作为 QS 改进版。

## 结论

- 不建议推广任何含 `price >= 4350` 的 QS 候选。
- 不建议把无价格低余额版直接上线；它只解决 30 天，牺牲 180 天复利。
- 更合理的最终方向是“当月/高周期扩张 + 低余额 + OB 反应质量”的组合，但固定 30 天 tester 需要解决预热历史问题，否则所有依赖左侧历史的非后视镜条件都会被绝对价条件不公平压制。
- 下一轮优先做带预热窗口的归因验证，或让 EA 在 tester 中显式预热月内/高周期状态，再比较 30/180/720。
