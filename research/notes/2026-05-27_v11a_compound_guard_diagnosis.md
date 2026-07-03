# 2026-05-27 v11a 小余额复利 guard 诊断

## 目标

在 v11a（v11btc-mix）不退化的前提下，让低余额阶段更快复利、减少刚达到极小月盈利目标后整月停手的问题。

## 复现

live 观察发现当前账户在 2026-05-26 没有开单，EA/MT5 本身在线，主因是 3% 月盈利目标触发 `profit_target_stop`。以约 200 美元月初余额计算，盈利约 6 美元就会整月停止新单，过早锁死小账户复利。

## 假设

1. 如果问题主因是低余额阶段 3% 月目标过低，则只在低余额区间提高目标，可以释放复利而不改变中高余额防守。
2. 如果低余额宽松窗口太高，会重新放出历史坏月，尤其 2024-10/2024-12。
3. 放大 R224/R225/R227 等腿在 CSV proxy 里能提高收益，但这会改变真实手数、保证金和路径，不能直接作为 live 改动。

## 验证

基线：

```powershell
python scripts\portfolio_schedule_runner.py --schedule r224_r225_r226_r211_r213_r216_r227_deployable_context --output results\backtest\portfolio_v11a_original_guard_proxy_20260527.md
```

结果：`final=322156.95`，`daily=10.98`，`bad=0`，`pass=true`。

低余额 guard 矩阵：

- `0-2000` 使用 35% 月盈利目标、`2000-65000` 使用 3% 月盈利目标：结果与基线等价，`bad=0`。
- `0-2500` 使用 10%-100% 月盈利目标：开始退化，2024-10 最弱为 `-571.88`，出现负月。
- 因此当前可证明边界取 `2000`，不取 `2500`。

压力：

```powershell
python scripts\portfolio_schedule_stress.py --schedule v11a --costs 0,0.05,0.1,0.25,0.5,1.0 --output results\backtest\portfolio_v11a_compound_2000_stress_20260527.md
```

结果：每笔额外成本到 `0.50` 仍 `bad=0`；到 `1.00` 出现 5 个负月。

profile 审计：

```powershell
python scripts\mt5_portfolio_live_profile.py --schedule v11a --guard-key-suffix 20260527compound2000
python scripts\mt5_portfolio_profile_audit.py --profile-dir temp\portfolio_profiles\v11a --schedule v11a --output results\backtest\portfolio_v11a_compound_2000_profile_audit_20260527.md
```

结果：7 个 chart 全部通过，`InpMonthlyProfitTargetStopMinBalance=2000.0`，`InpMonthlyProfitTargetStop2MaxBalance=2000.0`。

## 结论

采用双档月盈利目标：

- 月初余额 `0-2000`：35% 月盈利目标后停手。
- 月初余额 `2000-65000`：3% 月盈利目标后停手。
- 适用月份仍为 `3,4,5,10,11,12`。

这能解决当前 200 美元附近账户 3% 过早停手的问题，同时在现有 720 天 v11a proxy 中不退化。`2500` 是已验证的危险边界，暂不采用。

## 未采用

CSV proxy 显示 R224/R225/R227 轻微放大能提升总收益，但这是非 MT5 组合回测的筛选信号，不能直接上线。若要继续追求更高收益，应为放大腿生成真实 MT5 Strategy Tester 结果后再进入组合 proxy。

## 第二轮：R248 增益腿与 35% 月收益审计

用户目标升级为：v11a（v11btc-mix）不退化，更快复利，单月盈利至少 35%，越多越好。

新增反馈环：

```powershell
python scripts\portfolio_monthly_return_audit.py --schedule v11a --target-pct 35 --output results\backtest\portfolio_v11a_monthly_return35_audit_20260527.md
```

口径：每月收益率 = `month_profit / month_start_balance`。这不是 MT5 组合回测，只用于量化“月收益率 35%”缺口。

当前 v11a 审计：

- `below=16/24`
- `total_shortfall=386831.01`
- 最弱月 `2026-03:0.07%`
- 说明如果把目标理解为“每个自然月实际收益率 >=35%”，当前 v11a 明确未达标。

新增候选 schedule：`v11btc_mix_r248`

- 结构：v11a 七腿 + `R248`（`v11_r248_j2_r243_oct_ctx4` / v11b 增益腿）
- 先修正 proxy/live 对齐：R248 使用 `context_filter1-4`，必须把 R248 专属 `drop_filters` 加到 portfolio proxy，否则 proxy 不能代表 live 过滤。
- 同时扩展 `portfolio_schedule_lint.py`，从检查 `context_filter1-3` 扩到 `context_filter1-5`，避免 R248 的 `context_filter4` 漏检。

验证：

```powershell
python scripts\portfolio_schedule_lint.py --schedule v11btc_mix_r248
python scripts\portfolio_schedule_runner.py --schedule v11btc_mix_r248 --output results\backtest\portfolio_v11btc_mix_r248_proxy_aligned_20260527.md
python scripts\portfolio_monthly_return_audit.py --schedule v11btc_mix_r248 --target-pct 35 --output results\backtest\portfolio_v11btc_mix_r248_monthly_return35_aligned_20260527.md
python scripts\portfolio_schedule_stress.py --schedule v11btc_mix_r248 --costs 0,0.05,0.1,0.25,0.5,1.0 --output results\backtest\portfolio_v11btc_mix_r248_stress_20260527.md
python -m pytest tests\test_portfolio_schedule_lint.py tests\test_portfolio_monthly_return_audit.py -q
```

结果：

- lint: pass
- proxy: `final=458600.90`, `daily=15.14`, `bad=0`, `pass=true`
- 对比 v11a 当前 proxy：`final=322156.95`, `daily=10.98`, `bad=0`
- 增益：`+136443.95` final，日均交易 `+4.16/day`，未新增坏月
- stress: 每笔额外成本到 `1.00` 仍 `bad=0`
- pytest: `11 passed`

35% 月收益审计：

- `v11btc_mix_r248`: `below=18/24`, `total_shortfall=603880.81`, 最弱月 `2026-05:1.25%`
- R248 明显提高余额积累速度，但因为余额增长更快，高余额阶段 2026-03/04/05 的 35% 缺口变大。

结论：

- `v11btc_mix_r248` 是当前已验证的“不退化且更快积累”候选。
- 它不满足“每个自然月实际收益率 >=35%”这个强口径。
- 继续优化应聚焦高余额低收益月补丁，优先 `2026-03`、`2026-05`、`2026-04`，而不是继续把月盈利停手目标从 3% 简单提高到 35%；直接提高会放出 2024-10/2025-05 等亏损月。

## 第三轮：live/profile 等价口径纠偏

第二轮的 `v11btc_mix_r248` 先用 R248 原版 CSV 叠加组合级 proxy filters。继续按 diagnose 流程复核 live/profile 口径后，发现一个关键偏差：

- `mt5_portfolio_live_profile.py` 会先载入单腿策略参数，再应用 `live_profile.guard_overrides`。
- R248 原策略自带 `low_balance_ob_bad_months=3,5,9,10,11,12`、`low_balance_ob_bad_max_month_start_balance=10000`，以及 `10,11` 月高余额 `1%` 月盈利停手。
- v11btc-mix profile 会把这些覆盖成组合级：仅 `11` 月低余额 OB 过滤、`0-2000` 用 `35%` 停手、`2000-65000` 用 `3%` 停手。
- 因此“R248 原版 CSV + 组合级 proxy”不能代表将要挂 live 的 R248 参数。

修正动作：

1. 新增 `v11_r249_j2_r248_mix_guard`，把 R248 在 v11btc-mix profile 中实际会得到的 guard 覆盖固化成一个可 MT5 回测策略。
2. `v11btc_mix_r248` 的第 8 腿改用 R249 策略和 R249 MT5 CSV。
3. `mt5_portfolio_profile_audit.py` 的 context filter 展示从 `1-3` 扩展到 `1-5`，避免 R248/R249 的 `context_filter4` 在 profile 报告中隐身。

真实 MT5 Strategy Tester：

```powershell
python scripts\mt5_backtest_win.py --strategy v11_r249_j2_r248_mix_guard --symbol BTCUSDm --from 2024.06.06 --to 2026.05.26 --timeout 1800
python scripts\backtest_digest.py --report results\backtest\v11_r249_j2_r248_mix_guard_20240606_20260526_20260527.txt --export-csv --csv-output results\backtest\v11_r249_j2_r248_mix_guard_20240606_20260526_20260527.trades.csv
```

结果：

- R249 单腿：`2683` 笔，余额 `$800.20`，弱于 R248 原版漂亮数字，但这是 profile/live 等价口径。
- 新 v11btc-mix proxy：`final=338007.88`，`daily=13.64`，`bad=0`，`pass=true`。
- 对比 v11a：`final=322156.95`，`daily=10.98`，`bad=0`。
- 等价口径增益：`+15850.93` final，`+2.66/day`，仍不新增亏损月。
- 压力：每笔额外成本到 `0.50` 仍 `bad=0`；到 `1.00` 出现 1 个亏损月。v11a 在 `1.00` 成本下为 5 个亏损月。

35% 月收益审计：

- R249 等价 mix：`below=18/24`，`total_shortfall=415168.82`，最弱 `2026-03:0.09%`。
- 强口径仍未达标；R249 提高余额速度，但高余额阶段 2026-03/05 的目标额也随之抬高。

候选纠偏：

新增 `portfolio_shortfall_scan.py`，按 35% 月收益缺口减少排序，而不是按总利润排序。扫描显示，在“不新增亏损月”的约束下，当前候选对 2026-03/05 巨大缺口帮助很小；部分总利润更高的腿反而会扩大高余额阶段 shortfall。

对 R235 做同样等价验证：

```powershell
python scripts\mt5_backtest_win.py --strategy v11_r250_j2_r235_mix_guard --symbol BTCUSDm --from 2024.06.06 --to 2026.05.26 --timeout 1800
python scripts\backtest_digest.py --report results\backtest\v11_r250_j2_r235_mix_guard_20240606_20260526_20260527.txt --export-csv --csv-output results\backtest\v11_r250_j2_r235_mix_guard_20240606_20260526_20260527.trades.csv
```

结果：

- R250 单腿：`1737` 笔，余额 `$326.78`，PF `0.70`，本体很弱。
- 叠入当前 mix 仅增加 `+44.16`，但 35% shortfall 变差 `-5186.06`，不采用。

当前结论：

- `v11btc_mix_r248` 名称保留为组合候选，但实际第 8 腿现在是 `v11_r249_j2_r248_mix_guard`，这是可部署等价口径。
- R249 mix 是当前“未退化且更快积累”的保守候选，不是 35% 强月收益目标的完成方案。
- 下一轮不应继续把旧单腿 CSV 直接叠入组合；所有新腿都要先生成 mix guard 等价 MT5 CSV，再进入组合 proxy/shortfall scan。

## 第四轮：R252 保留 R248 自身过滤，只接入 shared guard

继续诊断 R248 原版与 R249 等价口径的差异：

- R248 原版在 `2026-03` / `2026-05` 分别贡献约 `9427.26` / `2708.64`。
- R249（组合 guard 全覆盖）在同月只剩 `103.09` / `-195.53`。
- 关键差异不是 `context_filter4`，而是 R249 把 R248 自身的低余额 OB 弱小时过滤和 10/11 月 1% 停手整体覆盖成组合级防守，抹掉了 R248 的原策略结构。

实验：

新增 `v11_r252_j2_r248_shared_only`：

- 继承 R248 原策略参数。
- 只开启 `shared_monthly_guard=true` 和组合 shared key。
- 不覆盖 R248 自身的 `low_balance_ob_bad_*`、`sweep_context_*`、`monthly_profit_target_stop_*`。

真实 MT5 Strategy Tester：

```powershell
python scripts\mt5_backtest_win.py --strategy v11_r252_j2_r248_shared_only --symbol BTCUSDm --from 2024.06.06 --to 2026.05.26 --timeout 1800
python scripts\backtest_digest.py --report results\backtest\v11_r252_j2_r248_shared_only_20240606_20260526_20260527.txt --export-csv --csv-output results\backtest\v11_r252_j2_r248_shared_only_20240606_20260526_20260527.trades.csv
```

结果：`3835` 笔，余额 `$128448.56`，PF `1.50`。R248 优势恢复。

为了让 profile 与 proxy 对齐，新增 `guard_override_mode: shared_only`：

- `mt5_portfolio_live_profile.py` 默认仍应用全部组合 guard overrides。
- 对 `guard_override_mode: shared_only` 的流，只从组合覆盖里拿 `shared_monthly_guard*` 三个字段。
- `portfolio_schedule_lint.py` 增加保护：只要存在 shared_only 流，所有 `drop_filters` 必须显式带 `src`，避免无 `src` 全局过滤在 proxy 中误伤 shared_only 流。

当前 `v11btc_mix_r248` 第 8 腿改为：

- `strategy: v11_r252_j2_r248_shared_only`
- `path: results/backtest/v11_r252_j2_r248_shared_only_20240606_20260526_20260527.trades.csv`
- `guard_override_mode: shared_only`

并将原本三条全局 drop_filter 展开到 7 条原 v11a 腿，避免作用到 R252。

验证：

```powershell
python scripts\portfolio_schedule_lint.py --schedule v11btc_mix_r248
python scripts\portfolio_schedule_runner.py --schedule v11btc_mix_r248 --output results\backtest\portfolio_v11btc_mix_r252_scoped_proxy_20260527.md
python scripts\portfolio_monthly_return_audit.py --schedule v11btc_mix_r248 --target-pct 35 --output results\backtest\portfolio_v11btc_mix_r252_scoped_monthly_return35_20260527.md
python scripts\portfolio_schedule_stress.py --schedule v11btc_mix_r248 --costs 0,0.05,0.1,0.25,0.5,1.0 --output results\backtest\portfolio_v11btc_mix_r252_scoped_stress_20260527.md
python scripts\mt5_portfolio_live_profile.py --schedule v11btc_mix_r248 --guard-key-suffix 20260527r252scoped
python scripts\mt5_portfolio_profile_audit.py --profile-dir temp\portfolio_profiles\v11btc_mix_r248 --schedule v11btc_mix_r248 --output results\backtest\portfolio_v11btc_mix_r252_scoped_profile_audit_20260527.md
```

结果：

- lint: pass
- proxy: `final=462303.52`，`daily=15.24`，`bad=0`，`pass=true`
- 对比 v11a：`final=322156.95`，`daily=10.98`，`bad=0`
- 增益：`+140146.57` final，`+4.26/day`
- stress: 到 `$1.00` 每单额外成本仍 `bad=0`，最弱月 `2024-11:79.99`
- profile audit: 8 charts pass；R252 腿显示 `s1-s4` 自身 context filters，`sweep_months`/`sweep_no_hours` 为空，证明没有继承组合 sweep override。

35% 强月收益审计：

- `below=18/24`
- `total_shortfall=608988.89`
- 最弱月 `2026-05:1.26%`

结论：

- R252 scoped 是目前最强的“不退化 + 更快复利积累”候选。
- 它仍不满足“每个自然月实际收益率 >=35%”强口径；余额增长越快，高余额阶段 35% 绝对目标越大，2026-03/04/05 仍需专门高余额加速/风险缩放方案。
- `portfolio_return_sim.py` shared-return proxy 对 R252 会出现极端复利放大和早期亏损月，说明 CSV path proxy 仍只能作为筛选，不可替代 MT5/真实组合验证。
