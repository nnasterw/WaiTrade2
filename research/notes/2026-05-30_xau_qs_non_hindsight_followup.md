# 2026-05-30 XAU QS 非后视镜续测记录

## 目标

继续修复 `v11xau-qs` 在 `2026.04.29 ~ 2026.05.29` 近 30 天的亏损，同时不牺牲 180 天长期表现。所有测试坚持非后视镜条件：不使用月份过滤作为最终策略，只使用当前余额、当前价格、订单块反应、确认位置、初始风险、K 线动能等 live 时点可见信息。

基线为 MT5 Strategy Tester CLI / Model 4 / Real Ticks / XAUUSDm / 初始资金 `$200`：

- `v11xau-qs` 30 天：189 笔，胜率 38.6%，余额 `$45.71`。
- `v11xau-qs` 180 天：827 笔，胜率 57.3%，余额 `$2396.58`。

## 工具修正

- 修正 `scripts/mt5_compile_win.py` 的 Windows portable 编译命令，显式传入 `/portable`，避免 isolated tester 编译时读到 AppData 里的旧 include/EX5。
- 验证：`python -m pytest tests\test_mt5_common.py tests\test_mt5_compile_win.py -q`，结果 `93 passed`。
- 验证：`python scripts\mt5_compile_win.py --mt5-home temp\mt5_tester_isolated --mt5-data temp\mt5_tester_isolated --log-dir temp\compile_win_isolated_defprice`，`WaiTrade_OB.mq5` 编译 `success=true warnings=0`。

## 低余额强防守与浅确认

- `v11xau-qs-lowbal-shallowcut-250` / `v11xau-qs-lowbal-shallowsoft-250` / `v11xau-qs-lowbal-shallowcut-220`：
  - 30 天均为 22 笔、胜率 54.5%、余额 `$207.49`。
  - 180 天分别约 `$225.44` / `$230.75` / `$203.30`。
  - 结论：能把近期救回 `$200` 上方，但交易数被砍到过低，长期复利几乎消失，不能作为 QS 升级。
- `v11xau-qs-lowbal-onlyshallowcut/soft-250/300`：
  - 30 天均等同 QS 基线，189 笔、胜率 38.6%、余额 `$45.71`。
  - 结论：浅确认位置本身不是 0529 这一段亏损的独立主因。

## OB 收盘确认与虚拟止损拆分

- `v11xau-qs-lowbal-onlyvsl25-250`：30 天 240 笔、胜率 47.1%、余额 `$45.31`。
- `v11xau-qs-lowbal-onlyvsl50-250`：30 天 179 笔、胜率 36.9%、余额 `$45.73`。
- `v11xau-qs-lowbal-onlyobclose-250/300`：30 天 122 笔、胜率 54.9%、余额 `$160.68`。
- 结论：只改虚拟止损不能救近期；真正改善来自“订单块反应后等待收盘确认”，但单独使用仍不足以盈利。

## 高风险桶与动能

逐单归因显示，30 天亏损集中在卖单与 17 点，但 180 天里买卖都赚钱，固定小时也不是稳定负贡献，因此不应采用方向/小时表作为最终策略。

180 天中初始风险 `>=2.2` 的桶为负，但实测 `large_risk_min/mult` 候选没有救回 30 天：

- `v11xau-qs-largerisk22-soft`：30 天 `$44.73`。
- `v11xau-qs-largerisk22-cut`：30 天 `$44.63`。
- `v11xau-qs-largerisk20-soft`：30 天 `$44.68`。
- `v11xau-qs-largerisk25-soft`：30 天 `$44.74`。

已有动能候选也未通过：

- `v11xau-qs-mom-c1`：30 天 `$44.67`。
- `v11xau-qs-momweak-c1`：30 天 `$45.94`。

结论：宽风险单和单一动能门不是近期崩盘的独立主因，路径变化还会释放更多坏交易。

## 高价低余额但去掉固定方向小时

新增 defensive 价格门，默认关闭，不影响现有策略：

- `defensive_confirm_min_price` -> `InpDefensiveConfirmMinPrice`
- `defensive_confirm_max_price` -> `InpDefensiveConfirmMaxPrice`

用于测试“当前价格高位 + 当前余额低位”时启用防守。去掉固定方向小时后：

- `v11xau-qs-highprice-lowbal-obclose-250`：30 天 122 笔、胜率 54.9%、余额 `$160.68`。
- `v11xau-qs-highprice-lowbal-obvsl-250`：30 天 141 笔、胜率 53.9%、余额 `$180.09`。
- `v11xau-qs-highprice-lowbal-obvsl-220`：30 天 148 笔、胜率 55.4%、余额 `$161.04`。

结论：高价 + 低余额 + OB 收盘确认/虚拟止损本身不够；此前 `v11xau-qs-highprice-lowbal-core-vsl-250` 的 30 天 `$222.84` 主要来自固定方向小时过滤。该方向可作为 live 风险观察开关，但不建议作为最终通用 QS 升级。

## 当前结论

截至本轮，没有找到同时满足以下两点的 QS 候选：

1. 近 30 天从 `$200` 起步能盈利。
2. 180 天不低于原 QS 基线 `$2396.58`。

目前最接近的已跑候选仍是：

- `v11xau-qs-highprice-lowbal-core-vsl-250`：30 天 `$222.84`，180 天 `$1719.32`。
- `v11xau-qs-highprice-lowbal-core-vsl2-220`：30 天 `$203.69`，180 天 `$1816.24`。

但它们都明显低于 QS 180 天基线，且包含固定方向小时经验，不建议推广上线。下一轮如果继续 QS，应把重点从“过滤小时/方向”转到更细的订单块状态识别：反应收盘后的二次确认质量、假突破后重入质量、订单块被刺破后的实体收复强度、高周期实体推进是否与订单块方向一致。

## 2026-05-30 续测三：运行期防守与确认位置单变量

新增并验证了默认关闭的运行期防守输入：`runtime_defensive_drawdown_pct`、`runtime_defensive_min_trades`、`runtime_defensive_max_balance`、`runtime_defensive_pos_mult`。该逻辑只看 EA 本轮启动后的峰值回撤和已交易笔数，不依赖月份或固定小时。验证链路：

- `python -m pytest tests\test_mt5_common.py tests\test_mt5_compile_win.py -q`：`93 passed`。
- `python scripts\mt5_compile_win.py --mt5-home temp\mt5_tester_isolated --mt5-data temp\mt5_tester_isolated --log-dir temp\compile_win_isolated_rundef_risk`：`WaiTrade_OB.mq5 success=true warnings=0`。
- MT5 Strategy Tester CLI / Model 4 / Real Ticks / XAUUSDm / `$200` / `2026.04.29 ~ 2026.05.29`。

运行期触发后启用 OB 收盘确认 + 虚拟止损：

- `v11xau-qs-rundef-obvsl-body45-dd8`：137 笔，胜率 50.4%，余额 `$161.88`。
- `v11xau-qs-rundef-obvsl-body45-dd12`：144 笔，胜率 52.1%，余额 `$152.87`。
- `v11xau-qs-rundef-obvsl-weakbody45-dd8`：135 笔，胜率 50.4%，余额 `$163.78`。

运行期触发后只降仓，不改入场、不改虚拟止损：

- `v11xau-qs-rundef-risk50-dd8`：292 笔，胜率 41.8%，余额 `$45.84`。
- `v11xau-qs-rundef-risk35-dd8`：175 笔，胜率 34.3%，余额 `$85.35`。
- `v11xau-qs-rundef-risk50-dd12`：287 笔，胜率 42.2%，余额 `$44.65`。

确认位置归因显示，原 QS 近 30 天亏损集中在 `confirm_pos -1..-0.5` 区间，但单独按浅确认软降权并不能修复：

- `v11xau-qs-shallowsoft-m060`：249 笔，胜率 37.8%，余额 `$45.58`。
- `v11xau-qs-shallowsoft-m035`：216 笔，胜率 34.3%，余额 `$46.09`。
- `v11xau-qs-shallowsoft-m080`：203 笔，胜率 35.0%，余额 `$44.84`。

结论：

- “运行期回撤后补救”不是核心解法：无论补救方式是更严格的 OB 收盘确认/虚拟止损，还是只降低仓位，都不能把近 30 天拉回盈利。
- “确认位置太浅”是坏单统计特征，但不是足够的可交易因子；单独降权会同步砍掉恢复性收益。
- 能救近 30 天的候选主要仍来自“固定方向小时 + 核心过滤 + 虚拟止损”，这不适合作为最终通用策略。下一步需要用更完整的 entry debug 字段做逐单归因，重点看高周期实体推进、订单块刺破后收复强度、同一订单块连续失败后的重入质量，而不是继续调余额阈值、月份或小时表。

## 2026-05-30 续测四：OB 反应深度与防守专用过滤

用 `v11xau-qs-debug-probe` 打开入场/出场日志，交易参数不变；30 天结果与 QS 基线一致：189 笔、胜率 38.6%、余额 `$45.71`。逐单 CSV 归因显示，`bounce_ob`（入场时 OB 反应深度/OB 高度）是比固定小时/方向更干净的 live 可见信号：

- `bounce_ob < 0.25` 的桶亏损最集中；`bounce_ob >= 0.30` 的保留桶明显改善，但交易数变少。
- 单独全局过滤 `bounce_ob` 只能改善，不能救回：`v11xau-qs-bounce-min30-cut` 30 天 143 笔、胜率 40.6%、余额 `$135.81`。
- 单独降权无效：`v11xau-qs-bounce-min25-m035` / `min30-m035` 30 天余额约 `$44.72` / `$44.88`。

把 OB 反应深度与此前有效的 OB 收盘确认、虚拟止损组合后，近 30 天可以盈利：

- `v11xau-qs-obvsl-body45-bounce30`：30 天 167 笔、胜率 55.1%、余额 `$242.06`；180 天 763 笔、胜率 56.0%、余额 `$242.81`。
- `v11xau-qs-obvsl-weakbody45-bounce30`：30 天 168 笔、胜率 56.0%、余额 `$232.52`；180 天 763 笔、胜率 56.5%、余额 `$244.51`。

结论：全局组合能解释 0529 附近“弱 OB/引线扫损”的问题，但 180 天从原 QS `$2396.58` 退化到约 `$243`，不能直接替代 QS。

随后新增默认关闭的 defensive 专用 OB 反应深度输入，避免全局过滤拖累正常 QS 主路径：

- `defensive_bounce_sweet_min_pct` -> `InpDefensiveBounceSweetMinPct`
- `defensive_bounce_sweet_max_pct` -> `InpDefensiveBounceSweetMaxPct`
- `defensive_outside_bounce_sweet_mult` -> `InpDefensiveOutsideBounceSweetMult`

低余额防守结果：

- `v11xau-qs-lowbal-obvsl-body45-bounce30-250`：30 天 230 笔、胜率 50.4%、余额 `$201.57`；180 天 795 笔、胜率 54.6%、余额 `$194.52`。
- `v11xau-qs-lowbal-obvsl-body45-bounce30-220`：30 天 228 笔、胜率 53.9%、余额 `$171.62`。
- `v11xau-qs-lowbal-obvsl-body45-bounce30-205`：30 天 228 笔、胜率 50.9%、余额 `$163.69`。
- `v11xau-qs-lowbal-obvsl-body45-bounce25/28-250` 与 30 版本等同：30 天余额 `$201.57`。

运行期回撤触发防守结果：

- `v11xau-qs-rundef-obvsl-body45-bounce30-dd8`：30 天 232 笔、胜率 53.4%、余额 `$162.91`。
- `v11xau-qs-rundef-obvsl-body45-bounce30-dd12`：30 天 238 笔、胜率 52.9%、余额 `$154.57`。
- `v11xau-qs-rundef-obvsl-body45-bounce30-dd8-t12`：30 天 232 笔、胜率 53.4%、余额 `$162.91`。

当前判断：

- OB 反应深度是有效诊断维度，且符合 live 可见、非后视镜要求。
- 但是把它做成全局门会牺牲 QS 长期复利；做成低余额防守能刚好救回近 30 天，但长期仍低于 `$200`，余量不够上线。
- 运行期回撤触发太晚，无法修复 0529 这类快速连续亏损。
- 下一步应继续沿订单块质量而不是月份/小时表：优先分析“同一订单块连续重入后的质量衰减”和“订单块被刺破后实体收复强度”。目前不建议把本轮任一候选作为正式 QS 替换上线。
