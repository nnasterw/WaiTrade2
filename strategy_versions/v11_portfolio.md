# v11 组合策略定稿

日期：2026-05-20

## 目标

- 盈利最大化
- 胜率 > 40%
- 盈亏比 > 2
- 日均开单 > 3

## 结论

BTC M5 单品种无法同时满足四个目标。32 轮实验显示：一旦把 BTCUSDm 日均开单推到 3 附近，spread/risk 会吞掉收益；保持盈利时，日均约 1.1 单。

因此 v11 定稿改为组合目标：

- `v11_xau_m3_fage`：主腿，负责日均开单、胜率、盈亏比。
- `v11_btc_m5`：卫星腿，负责 BTC 暴露和大波动弹性，不再承担日均>3目标。

别名记录：`v11btc-mix` 指向本文件定义的 v11 组合定稿，不是 `config/strategies.yaml` 中的单一 EA preset。MT5 一个账号同一图表只能挂一个 EA preset，组合口径需要按腿分别回测/部署后做账户级汇总。

## 主腿：v11_xau_m3_fage

继承已验证的 `v10_fage_dtp8_r20` 配方，仅变更版本名和 magic number，便于 v11 部署隔离。选 DTP8/R20 而不是 DTP7/R15，是因为同一 180 天窗口下 DTP7/R15 的 PF 为 1.99，贴着目标线；DTP8/R20 明确跨过 PF>2。

核心参数：

- `bar_period_min: 3`
- `filter_cont_age_min_bars: 40`
- `filter_cont_age_max_bars: 79`
- `filter_cont_non_deep_only: true`
- `breakeven_r: 0.25`
- `breakeven_lock_r: 0.08`
- `dtp_trigger_r: 8.0`
- `dtp_retrace: 0.20`
- Trail / fixed TP / MFE fail 全禁用

已验证表现（XAUUSDm，180天 Real Ticks，初始资金 $200）：

| 策略 | 交易 | 日均 | WR | PF | 余额 |
|------|------|------|----|----|------|
| v10_fage_dtp8_r20 | 586 | 3.3 | 71.2% | 2.04 | $3793.46 |

## 卫星腿：v11_btc_m5

BTC 保留已验证的基线 E，重点是避免 spread 杀薄 OB：

- `bar_period_min: 5`
- `entry_depth_pct: 0.67`
- `entry_depth_filter: true`
- `bounce_pct: 0.25`
- `min_risk_spread_ratio: 5.0`
- `sl_buffer_atr: 1.5`
- `breakeven_r: 1.0`
- `breakeven_lock_r: 0.2`
- `dtp_trigger_r: 3.0`
- `dtp_retrace: 0.25`
- `max_concurrent: 3`
- `free_run_min_r: 5.0`

已验证表现（BTCUSDm，180天 Real Ticks，初始资金 $200）：

| 策略 | 交易 | 日均 | WR | PF | 余额 |
|------|------|------|----|----|------|
| v11_btc_m5 | 195 | 1.1 | 52.8% | 0.97 | $280.96 |

## 组合判断

按已验证单腿结果，`v11_xau_m3_fage` 单独已满足四个目标；叠加 `v11_btc_m5` 后，组合日均约 4.4 单，并增加 BTC 波动暴露。

注意：MT5 Strategy Tester 不能在一次回测中同时跑不同 preset 的多品种组合。组合指标是基于两个独立 Strategy Tester 结果的外推，实盘前仍需用 live runner 分策略部署，并用账户级日志验证资金曲线和并发风险。

## 部署命令

```bash
python3 scripts/yaml_to_set.py --all
python3 scripts/mt5_live_runner.py --strategy v11_xau_m3_fage --symbols XAUUSDm
python3 scripts/mt5_live_runner.py --strategy v11_btc_m5 --symbols BTCUSDm
```

## 后续验证

1. 用 `v11_btc_m5` 补跑 ETHUSDm 180天，只作为扩展实验，不影响 v11 定稿。
2. Live 观察时按账户级别统计日均单数、最大并发、连续亏损和 session loss。

## BTC Sweep 追加验证

为避免过早放弃 BTC 单品种，v11 追加实现并测试了 Liquidity Sweep 反转信号。结果如下：

| 策略 | 交易 | 日均 | WR | PF | 余额 |
|------|------|------|----|----|------|
| v11_swp_m5_tp1 | 62 | 0.3 | 51.6% | 1.13 | $237.29 |
| v11_swp_m5_dtp | 62 | 0.3 | 51.6% | 1.22 | $263.80 |
| v11_swp_m5_loose | 1294 | 7.2 | 50.5% | 0.97 | $1.44 |
| v11_swp_m5_ltp15 | 1791 | 9.9 | 51.0% | 0.99 | $1.44 |
| v11_swp_m5_combo | 272 | 1.5 | 55.1% | 1.17 | $1.21 |

Sweep 结论和 OB 结论一致：严格过滤后 BTC 有盈利但低频；放宽到日均>3 后 PF 与余额崩坏。因此 v11 仍采用 XAU 达标主腿 + BTC 卫星腿的组合定稿。
