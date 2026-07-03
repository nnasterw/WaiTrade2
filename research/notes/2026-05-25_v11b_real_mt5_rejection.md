# 2026-05-25 v11b 真实 MT5 否决记录

## 背景

v11a 是当前最强 BTC 组合代理方案，包含 R224/R225/R226/R211M/R213D/R216M/R227 七条腿。风险审计发现，直接在 CSV 层缩放仓位并同步缩放余额阈值，可以得到一个看似更稳的 v11b 候选：

- R224 = 0.25
- R225 = 0.75
- R226 = 0.25
- R211M = 1.0
- R213D = 0.0
- R216M = 1.0
- R227 = 0.25
- balance threshold factor = 0.25

CSV proxy 结果见 `results/backtest/portfolio_v11b_scale025_threshold025_candidate_20260525.md`，当时显示 total=126023.44、daily=10.96、bad=0。

## 需要验证的假设

1. 如果 v11b 只是线性降仓，那么把 risk/max_lot 和高余额阈值落到真实 MT5 参数后，单腿结果应接近 CSV 缩放路径。
2. 如果 MT5 最小手数、手数 cap、低余额保护或月初余额阈值造成非线性偏移，那么真实 720 天回测会明显偏离 CSV proxy。
3. 如果偏移只发生在个别腿，组合账户级 guard 可能仍能修复；如果组合真实 CSV 代理也不过目标，则 v11b 应否决。

## 实验配置

新增真实 MT5 派生策略：

| 策略 | 来源 | 主要变化 |
|---|---|---|
| `v11_r229_j2_r224_ctx35_s025` | R224 | risk 1.35, max_lot 2.25, high-balance thresholds x0.25 |
| `v11_r230_j2_r225_ctx35_s075` | R225 | risk 4.05, max_lot 6.75, high-balance thresholds x0.25 |
| `v11_r231_j2_r226_ctx3_s025` | R226 | risk 1.35, max_lot 2.25, high-balance thresholds x0.25 |
| `v11_r232_j2_r227_ctx35_s025` | R227 | risk 1.35, max_lot 2.25, high-balance thresholds x0.25 |

重要保守处理：没有把 `sweep_max_lot_size=0.01` 继续缩小，因为 BTCUSDm 最小手数会把小于 0.01 的 cap 变成不可交易或路径失真。

## MT5 720 天真实回测结果

命令：

```bash
python scripts/mt5_backtest_win.py --strategies v11_r229_j2_r224_ctx35_s025,v11_r230_j2_r225_ctx35_s075,v11_r231_j2_r226_ctx3_s025,v11_r232_j2_r227_ctx35_s025 --symbol BTCUSDm --from 2024.06.04 --to 2026.05.25 --timeout 900
```

结果：

| 策略 | 交易 | 日均 | PF | 余额 | 结论 |
|---|---:|---:|---:|---:|---|
| R229 | 509 | 0.7 | 1.39 | 586.71 | 小正，但 11 个亏损月 |
| R230 | 353 | 0.5 | 0.76 | -352.07 | 失败，负余额 |
| R231 | 691 | 1.0 | 1.25 | 660.29 | 小正，但 10 个亏损月 |
| R232 | 691 | 1.0 | 1.25 | 660.29 | 与 R231 高度相同，需后续核查是否参数/缓存等价 |

Digest/CSV：

- `results/backtest/v11_r229_j2_r224_ctx35_s025_20240604_20260525_20260525.md`
- `results/backtest/v11_r230_j2_r225_ctx35_s075_20240604_20260525_20260525.md`
- `results/backtest/v11_r231_j2_r226_ctx3_s025_20240604_20260525_20260525.md`
- `results/backtest/v11_r232_j2_r227_ctx35_s025_20240604_20260525_20260525.md`

## 关键发现

CSV 缩放假设不成立。R229 的 509 笔交易里，333 笔是 0.01 最小手数；R231 的 691 笔里，500 笔是 0.01 最小手数。也就是说，0.25 暴露在真实 MT5 里大量被最小手数地板托住，并不是线性降风险。

R230 的失败不是简单的“收益变小”，而是路径失真：2025-11 月初余额约 1035，刚好超过原本 `monthly_profit_target_stop_max_balance=1000` 的低余额盈利停手上限，导致该保护失效，81 笔交易把余额打到 -352.07。降仓改变了余额路径，反而把账户推到保护边界外。

真实单腿 CSV 组合代理也不过目标：

```bash
python scripts/portfolio_path_sim.py ... > results/backtest/portfolio_v11b_reallegs_proxy_20260525.md
```

结果：

- total = 2787.97
- daily = 1.98
- bad months = 4
- 亏损月：2024-08、2025-07、2026-01、2026-05

账户级 guard 能挡住 R230 的 2025-11 大亏，但挡不住整体频率和收益目标崩塌。

## 结论

v11b 当前候选被真实 MT5 否决，不应升级为正式方案。

组合方案不会确保盈利。它只能在历史上利用不同腿的坏月不同步来抵消亏损；如果未来行情让多条腿同频失效，劣势也会合并。当前可用的工程纪律是：

1. 组合前必须做 source-risk、leave-one-out、stress、shared-return 代理。
2. CSV 缩放只能用于快筛，不能当作 live-ready 证据。
3. 任何降仓方案必须跑真实 MT5，因为最小手数、余额阈值和月内 guard 会造成非线性路径。
4. Live 必须有账户级 shared monthly guard、session loss 熔断、小仓 forward 观察，不能依赖“历史每月盈利”来承诺未来每月盈利。

下一步不再沿用 v11b 这组比例。若继续降低组合风险，应从真实 MT5 可交易手数出发，优先修复 R225/R230 的 2025-11 保护边界，或改用更少腿、更明确的账户级熔断，而不是继续线性缩放。
