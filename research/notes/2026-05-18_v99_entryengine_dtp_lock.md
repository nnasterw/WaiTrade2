# 2026-05-18 v99 EntryEngine与DTP锁利改进记录

## 背景

读取 `docs/handoffs/2026-05-18_project_status.md` 后确认：`v99g1`/`v99j1` 是已验证基线，`v99g2`/`v99j2` 是待验证的新策略。当前优先级不是扩大参数搜索，而是先保证 v99 默认启用的 EntryEngine 路径与直接入场路径共享同一套信号质量纪律。

## 主要发现

1. `ScanSignals` 直接入场路径会在真实可成交价上检查 offset、spread/risk、OB strength、risk/ATR、逆势大risk、保证金与手数。
2. `EntryEngine` 确认路径在 bounce 后直接计算手数并执行，缺少部分 8-Gap 过滤，也没有基于最终 bid/ask 重新计算 risk、tp、lot 和 margin。
3. DTP partial close 已有参数，但首次部分落袋后，余仓只依赖既有 BE/trailing，缺少一个“部分落袋后立即抬高剩余仓保护位”的独立参数。

## 已实现

1. 新增 `FinalizeEntryEngineSignal()`：EntryEngine 确认后用真实 bid/ask 重新计算 entry/risk，并重新执行 8-Gap、offset、spread/risk、评分、固定TP/震荡TP、手数与保证金校正。
2. 新增 `InpDTPPostPartialLockR` / `dtp_post_partial_lock_r`：DTP 首次部分平仓成功后，可将剩余仓 SL 抬到指定 R，默认 `0.0` 关闭。
3. 新增候选策略：
   - `v99g3`: `v99g2 + dtp_post_partial_lock_r: 1.0`
   - `v99j3`: `v99j1 + DTP首次50%落袋 + dtp_post_partial_lock_r: 1.5`

## 快速验证

命令：

```bash
python3 -m pytest tests/test_mt5_common.py -q
python3 scripts/mt5_compile.py WaiTrade2/WaiTrade_OB
python3 scripts/mt5_cli_backtest.py --strategies v99g1,v99g3 --symbol XAUUSDm --days 30 --timeout 240
```

结果：

| 策略 | 品种 | 周期 | 交易 | 胜率 | 余额 |
|------|------|------|------|------|------|
| v99g1 | XAUUSDm | 2026-04-18 ~ 2026-05-18 | 52 | 55.8% | $222.08 |
| v99g3 | XAUUSDm | 2026-04-18 ~ 2026-05-18 | 52 | 55.8% | $222.08 |

30天样本中 v99g3 与 v99g1 完全一致，说明新策略链路可运行，但该样本不足以覆盖 DTP partial lock 的差异场景。需要跑 180天 XAU/XAG/EUR 和 365天 BTC/ETH 后再判断。

## 后续实验建议

1. `v99g1,v99g2,v99g3` 跑 XAUUSDm/XAGUSDm/EURUSDm 180天，判断 partial lock 是否降低大赢尾部或减少回吐。
2. `v99j1,v99j2,v99j3` 跑 BTCUSDm/ETHUSDm 365天，单独观察 BTC 是否继续支持 `SL2.0ATR`，ETH 是否更适合保留 `SL1.5ATR`。
3. 从 Agent 日志中提取 `dtp_partial`、`dtp_part_lock`、`dtp2` 事件，按“部分落袋后余仓最终贡献”统计，而不是只看最终余额。
4. 如果 v99g3 回撤收益不明显，下一轮优先做入场端实验：`min_risk_spread_ratio` 分品种提高、`max_entry_offset_r` 收紧到 0.35、以及 XAG/EUR 独立 `bounce_pct`。
