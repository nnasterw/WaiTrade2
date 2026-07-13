# 2026-07-13 loop159 PS1-simplified-v1 单变量放宽结果

## 实验
- 策略: v11-btc1-loop159
- 唯一改动: ob_reentry_cooldown_min 30 -> 5
- baseline: v11-btc1-bv1 (WFYS v2.2 = 89.57, 720d = 105 笔, 周均 1.07)
- 端口: temp/mt5_portable_btc_bv1 (WaiTrade2 EA, Real Ticks, Model 4, $200, 720d 2024-06-01 ~ 2026-05-31)

## 真实结果
| 指标 | baseline bv1 | loop159 |
|---|---:|---:|
| 720d 交易数 | 105 | 149 |
| 周均交易 | 1.07 | 1.55 |
| 胜率 | 40.0% | 49.7% |
| 720d 余额 | $8294.95 | $6207.65 |
| WFYS v2.2 | 89.57 | **76.71** |
| 24月盈利月 | PASS | **FAIL** |
| 亏损月数量 | PASS | **FAIL** |
| 720d最大回撤 | PASS | **FAIL** |

## 结论
1. **单变量放宽冷却时间会增加交易数和胜率**, 周均从 1.07 升到 1.55 (提升 45%).
2. **但 WFYS 整体退 12.86 分**, 因为月度稳定性崩溃 (24 月盈利月从 23 掉到 ?, 亏损月增加, 最大回撤恶化).
3. **盈亏比从 6.30 跌到 1.28**, 净值从 $8295 跌到 $6208 (-25%).
4. **PS1 的"冷却时间"不是瓶颈**: 缩短冷却到 5 min 让更多小额信号进入, 但它们的 PF 远低于 baseline 的 OB/BOS 大波段信号, 稀释了趋势利润.

## 下一步
- 进入结构探索 Loop 160: 需修改 v3 EA 增加 STRU_CAMPRLD 家族, OnTradeTransaction 维护 campaign 状态机.
- 不在 v2 参数层继续微调, 60+ 变体已证伪单变量路线.
- 当前 best is still v11-btc1-bv1 (89.57), objective gap = 3.43 + 需要消除 720d周均单数 硬失败.

## 风险
- 继续在 v2 上调参数已证伪为 0% 产出, 必须从结构层面突破.
- 3 个月内不做 EA 改造, 则会持续 stagnate.
- v3 EA 改造风险: STRU_CAMPRLD 必须是真正的 0.0-1.0 价/量/时间 gate, 而不是再调 max_entries.

## 证据
- research/loops/2026-07-13_loop_159_manifest.json (权威)
- research/loops/2026-07-13_loop_159_handoff.md (人类摘要)
- research/loops/current_pipeline.json (指针, next_loop=160)
- results/backtest/v11-btc1-loop159_20260613_20260713_20260713.txt (30d)
- results/backtest/v11-btc1-loop159_20260415_20260713_20260713.txt (90d)
- results/backtest/v11-btc1-loop159_20240601_20260531_20260713.txt (720d)
- results/backtest/v11-btc1-loop159_*.trades.csv + .trades_closetime_24m.csv
- results/backtest/v11-btc1-loop159_wfys_v22_20260713.json
- 工具链: scripts/mt5_backtest_win.py + scripts/backtest_digest.py + scripts/rebuild_24m.py + scripts/wfys_score.py

## Token 用量归因
- 真实 Codex token_count 不可用 (本次工作未经过 Codex 自身会话).
- MT5 实际回测成本: 3 次 7.0 分钟, 0 轮轮询.
- Agent 调用: 7 exec, 5 write_stdin, 0 poll.
