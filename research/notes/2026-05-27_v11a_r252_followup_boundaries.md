# v11a/R252 后续加速实验边界

日期：2026-05-27

目标继续围绕“v11a 不退化基础上更快复利并积累余额”。本轮先用 CSV path proxy 建立 35% 月收益缺口反馈环，再只把少数候选落到 MT5 Strategy Tester Real Ticks。

## 1. R252 线性放大筛选

命令：

```powershell
python scripts\portfolio_scale_grid_scan.py --schedule v11btc_mix_r248 --scales 1 --source-scale R248=0,0.5,1,1.5,2,3,4,5,6,8,10,12 --include-failed --top 20 --output results\backtest\portfolio_v11btc_mix_r252_scale_grid_20260527.md
```

结论：

- R252 放大到 3x 仍 `bad=0`，但 4x/5x 开始制造 `2025-05` 负月。
- 即使 8x-12x 总余额很高，35% 月收益缺口仍扩大，因为高余额阶段目标分母同步抬高。
- 单纯“多加同一条腿/同一腿倍数”不是 35% 月收益目标的好形状。

## 2. 单月好小时补频腿（R253-R257）

从 R252 逐单 CSV 中筛出 1/2/3/4/5 月正贡献方向小时，新增单月补频策略：

- `v11_r253_j2_r252_jan_good_hours`
- `v11_r254_j2_r252_feb_good_hours`
- `v11_r255_j2_r252_mar_good_hours`
- `v11_r256_j2_r252_apr_good_hours`
- `v11_r257_j2_r252_may_good_hours`

先跑真实 MT5 最强的 2 月和 4 月候选：

```powershell
python scripts\mt5_backtest_win.py --strategy v11_r254_j2_r252_feb_good_hours --symbol BTCUSDm --from 2024.06.06 --to 2026.05.26 --timeout 1800
python scripts\backtest_digest.py --report results\backtest\v11_r254_j2_r252_feb_good_hours_20240606_20260526_20260527.txt --export-csv --csv-output results\backtest\v11_r254_j2_r252_feb_good_hours_20240606_20260526_20260527.trades.csv

python scripts\mt5_backtest_win.py --strategy v11_r256_j2_r252_apr_good_hours --symbol BTCUSDm --from 2024.06.06 --to 2026.05.26 --timeout 1800
python scripts\backtest_digest.py --report results\backtest\v11_r256_j2_r252_apr_good_hours_20240606_20260526_20260527.txt --export-csv --csv-output results\backtest\v11_r256_j2_r252_apr_good_hours_20240606_20260526_20260527.trades.csv
```

真实 MT5 结果：

- R254：40 笔，胜率 52.5%，余额 `$475.25`。
- R256：56 笔，胜率 37.5%，余额 `$966.06`。
- 追加到当前 mix 的 path proxy 后，总余额只从 `$462303.52` 到 `$463342.84`，35% 总缺口几乎不变（`608988.89` -> `608992.73`）。

结论：单月好小时补频腿为正，但火力太小，不能解决高余额阶段 10 万美元级月收益缺口；暂不加入正式组合 schedule。

## 3. 月内未达 35% 前加倍（R258）

新增 `v11_r258_j2_r252_warmup35_x2`：

- `monthly_warmup_profit_pct: 35.0`
- `monthly_warmup_pos_mult: 2.0`

真实 MT5：

```powershell
python scripts\mt5_backtest_win.py --strategy v11_r258_j2_r252_warmup35_x2 --symbol BTCUSDm --from 2024.06.06 --to 2026.05.26 --timeout 1800
python scripts\backtest_digest.py --report results\backtest\v11_r258_j2_r252_warmup35_x2_20240606_20260526_20260527.txt --export-csv --csv-output results\backtest\v11_r258_j2_r252_warmup35_x2_20240606_20260526_20260527.trades.csv
```

结果：

- R258：3833 笔，胜率 42.1%，PF `1.47`，余额 `$125813.78`。
- 对比 R252：3835 笔，胜率 42.1%，PF `1.50`，余额 `$128448.56`。

结论：月内前段粗暴 x2 会退化，不采用。

## 4. Sweep 低质量尾部坏簇过滤/软降权（R259/R260）

R252 digest 与逐单筛选都指向同一类低质量 sweep 尾部簇：

- signal=`sweep`
- hour=`0,1,2,7,8,9,23`
- risk=`150-400`
- confirm_pos `< -0.6`

新增：

- `v11_r259_j2_r252_sweep_tail_cut`：该簇过滤，`bad_cluster2_mult=0.0`
- `v11_r260_j2_r252_sweep_tail_soft`：该簇半仓，`bad_cluster2_mult=0.5`

真实 MT5：

```powershell
python scripts\mt5_backtest_win.py --strategy v11_r259_j2_r252_sweep_tail_cut --symbol BTCUSDm --from 2024.06.06 --to 2026.05.26 --timeout 1800
python scripts\backtest_digest.py --report results\backtest\v11_r259_j2_r252_sweep_tail_cut_20240606_20260526_20260527.txt --export-csv --csv-output results\backtest\v11_r259_j2_r252_sweep_tail_cut_20240606_20260526_20260527.trades.csv

python scripts\mt5_backtest_win.py --strategy v11_r260_j2_r252_sweep_tail_soft --symbol BTCUSDm --from 2024.06.06 --to 2026.05.26 --timeout 1800
python scripts\backtest_digest.py --report results\backtest\v11_r260_j2_r252_sweep_tail_soft_20240606_20260526_20260527.txt --export-csv --csv-output results\backtest\v11_r260_j2_r252_sweep_tail_soft_20240606_20260526_20260527.trades.csv
```

结果：

- R259：3407 笔，胜率 42.3%，PF `1.54`，余额 `$122250.97`。
- R260：3808 笔，胜率 42.1%，PF `1.51`，余额 `$127494.87`。
- 两者 PF 均优于/接近 R252，但余额都低于 R252。

结论：该簇确实低质量，但它也贡献了复利路径的交易频率；过滤或半仓会降低最终余额，不符合“更快积累余额”目标，不采用。

## 当前结论

- 正式组合仍保持 `v11btc_mix_r248` + 第 8 腿 `v11_r252_j2_r248_shared_only`，不加入 R253-R260。
- R252 scoped 仍是当前已验证的最佳“不退化 + 更快复利积累”候选。
- 已证伪方向：单月小补频、月初/未达标前粗暴加倍、低质量 sweep 尾部过滤/半仓。
- 下一轮应转向“新增独立信号来源”或“高余额阶段专用、但不牺牲交易频率的质量加速”，而不是继续在 R252 上做简单倍数或剪枝。
