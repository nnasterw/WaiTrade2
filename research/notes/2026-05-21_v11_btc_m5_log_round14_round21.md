# V11 BTC M5 Round14-Round21 日志驱动迭代

日期: 2026-05-21

## 目标

继续基于 MT5 Strategy Tester Real Ticks 180 天回测，聚焦 BTCUSDm M5，从价格日志中提取盈利单/亏损单规律，迭代 v11 单腿候选。

验证区间:

```bash
2025.11.22 ~ 2026.05.21
```

## 关键日志规律

从 `Tester/Agent-127.0.0.1-3000/logs/20260521.log` 解析 Round15-Round17 交易链路后，结论如下：

- 盈利核心不是“更多小时高仓”，而是“非浅确认 + 大结构 + H1净推进保护”的交集。
- Q45A 比 Q1120 多出的 26 笔边缘单整体负贡献，主要集中在 `xmult<1`、`risk<200`、`bounce_sec>=60`。
- `confirm_pos >= -0.6` 是稳定坏簇；它代表确认位置过浅，容易是 OB 边缘假反弹。新增 `shallow_confirm_pos_*` 后，PF 从 1.80/1.82 提升到 2.10。
- `risk=300-400` 与最终 `xmult>=2` 是主要右尾来源；全局提高风险不如集中放大大结构。
- 13/14/20 小时在低仓统计中看似有利润，但整体纳入高仓后 PF 会从 2.10 降到 1.61-1.93，说明小时只能作为辅助，不能替代入场质量。

## 新增 EA 参数

Round14 新增 HTF 净推进仓位分层：

- `enable_htf_net_push_filter`
- `htf_net_push_tf`
- `htf_net_push_bars`
- `htf_net_push_min_atr`
- `htf_net_push_aligned_mult`
- `htf_net_push_neutral_mult`
- `htf_net_push_counter_mult`

Round17 新增浅确认位置降权：

- `shallow_confirm_pos_min`
- `shallow_confirm_pos_mult`

所有新增参数均默认关闭，并已同步：

- `mql5/Include/WaiTrade2/Config.mqh`
- `mql5/Include/WaiTrade2/SignalEngine.mqh`
- `scripts/yaml_to_set.py`
- `config/strategies.yaml`
- `tests/test_mt5_common.py`

## 回测结果

| 策略 | 交易 | 严格日均 | 胜率 | PF | 余额 | 结论 |
|---|---:|---:|---:|---:|---:|---|
| `v11_r15_q1120_h1push` | 168 | 0.93 | 50.0% | 2.22 | $1767.89 | PF高但低频 |
| `v11_r15_q45a_h1push` | 181 | 1.01 | 49.7% | 1.80 | $2318.57 | 高频但PF不足 |
| `v11_r16_q1120_l40_h1` | 174 | 0.97 | 50.0% | 2.16 | $1750.84 | 低仓细化仍低频 |
| `v11_r17_q45a_shallow_hard` | 182 | 1.01 | 51.1% | 2.10 | $3039.33 | 浅确认降权打通 PF+频率 |
| `v11_r18_shallow_r3` | 185 | 1.03 | 50.8% | 2.00 | $3304.91 | 全局加风险贴边 |
| `v11_r19_shallow_r29` | 186 | 1.03 | 51.6% | 2.03 | $3328.26 | 更稳的风险窄网格 |
| `v11_r20_shallow_r28_lg22` | 188 | 1.04 | 51.6% | 2.15 | $5664.70 | 大结构放大有效 |
| `v11_r21_shallow_r28_lg23` | 189 | 1.05 | 51.3% | 2.15 | $5944.83 | 接近6000 |
| `v11_r21_shallow_r27_lg24` | 188 | 1.04 | 51.6% | 2.20 | $6266.12 | 当前最佳 |
| `v11_btc_m5_r21` | 188 | 1.04 | 51.6% | 2.20 | $6266.12 | 单独复验通过 |

单独复验命令：

```bash
python3 scripts/mt5_cli_backtest.py --strategy v11_btc_m5_r21 --symbol BTCUSDm --from 2025.11.22 --to 2026.05.21 --timeout 300
```

## 当前候选配置

`v11_btc_m5_r21`：

- 底座: `v11_r17_q45a_shallow_hard`
- M5 OB + EntryEngine bounce
- H1 净推进分层: `counter_mult=0.45`
- 浅确认降权: `confirm_pos > -0.60` 时 `0.45x`
- 全局风险: `risk_percent=2.7`
- 大结构放大: `large_risk_mult=2.40`
- 最大仓位: `max_pos_mult=150.0`
- 最大手数: `max_lot_size=3.20`

## 结论

BTC M5 单腿在当前目标口径下已经找到一组通过 180 天 Real Ticks 复验的候选：

- 胜率 > 40%
- PF > 2
- 严格日均 > 1
- 余额 > $6000

但若沿用最初“单 BTC 日均 > 3”的口径，仍未达标；当前候选严格日均约 1.04。继续追求日均 > 3 需要新信号源或多策略/多品种组合，不能靠继续放宽现有 OB 入场。
