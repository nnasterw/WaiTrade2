# 2026-05-18 v99g2 深度改进方案与实现记录

## 结论先行

v99g2 不应该在 v99g1 的入场端一次性叠太多过滤。v99g1 的优势来自 M5 + EntryEngine + 8-Gap + BE1.0R 的稳定组合，当前最有解释力的改进空间在“2R 以后如何处理大赢”。本轮实现把 v99g2 定义为 DTP runner：首次 DTP 回撤时先平 50%，剩余仓锁到 1R，并重置余仓 DTP 峰值，让剩余仓真正继续跑，而不是沿旧峰值很快二次退出。

## 基线认知

- `v99g1`: 贵金属+外汇基线，M5，bounce40%，timeout90，DTP 2R/20%，首次回撤全平。
- `v99j1`: 加密基线，M30，SL 1.5ATR，BE2R/lock1R，DTP 3R/20%。
- 本地 2026-05-18 Agent 日志只覆盖了 `v99g1` 与旧 `v99g3` 的 XAU 30天快速验证，两者都是 52笔、55.8%WR、余额 $222.08，未覆盖新 v99g2 runner 行为。

## 改进空间展开

### 1. 出场端: 大赢保护与右尾扩展

现象假设：v99g1 在 2R 后触发 DTP，20%回撤全平。它能防止大幅回吐，但对趋势延展的单子不友好。历史记录也反复显示，早 trail 会伤害大赢，纯放宽 DTP 又可能增加回吐。

| 方向 | 实现状态 | 备注 |
|------|----------|------|
| DTP首次回撤部分平仓 | 已实现 | `dtp_exit_mode=1`, `dtp_partial_pct=50` |
| 余仓单独回撤阈值 | 已实现 | `dtp_post_partial_retrace=0.30` |
| 部分落袋后余仓锁R | 已实现 | `dtp_post_partial_lock_r` |
| 部分落袋后重置DTP峰值 | 已实现 | `dtp_reset_peak_after_partial` |
| 阶梯DTP 3R/4R | 已有参数 | 仍需单变量测试 |
| 固定TP混合DTP | 未采用 | 可能破坏 v99 的右尾优势 |

最终选择：v99g2 = 50%落袋 + 余仓锁1R + 余仓重置峰值。原因是它同时限制坏处和保留好处：首段利润兑现，剩余仓最坏也有 1R 保护，且余仓不会被旧峰值立刻二次 DTP。

### 2. 入场端: 信号质量再参数化

8-Gap 中还有一些硬编码阈值，过去只能改源码试验，不适合批量 MT5 回测。本轮把它们参数化，但默认值完全保持原行为：

- `min_ob_body_pct`: 默认 50.0，可试 55/60，提高实体质量。
- `no_ob_start_hour` / `no_ob_end_hour`: 默认 23-06，可试 22-07 或禁用。
- `min_ob_strength`: 默认 0.5，可试 0.8/1.0。
- `max_risk_atr`: 默认 3.0，可试 2.5，过滤超宽风险。
- `max_counter_risk_atr`: 默认 1.5，可试 1.2，压制逆势大R。

这些没有直接放进 v99g2，原因是它们会改变交易集合，不利于判断 DTP runner 是否有效。下一轮应单变量跑。

### 3. EntryEngine 与 live/回测一致性

发现：EntryEngine 监控阶段产生的信号在确认后直接按旧 risk/pos_mult 算手数，缺少直接入场路径已有的最终成交价复核。这样 live 与回测都可能在 bounce 后偏移、spread/risk、risk/ATR、保证金和评分口径上漂移。

本轮实现：新增 `FinalizeEntryEngineSignal()`，在真实 bid/ask 上重新计算 entry/risk/lot/tp，并复核 offset、spread/risk、OB strength、risk/ATR、逆势大risk、评分、最小风险、保证金和 volume step。`WaiTrade_OB.mq5` 的 EntryEngine 执行路径改为先 finalize 再下单。

### 4. 工具链与参数同步

- 修复 `scripts/mt5_compile.py`：EA 已迁到 `WaiTrade2` include 路径，编译脚本不能继续拷贝 `Include/WaiTrade`。
- `Config.mqh` 新增 input 后，同步更新 `scripts/yaml_to_set.py`、`config/strategies.yaml` defaults、`tests/test_mt5_common.py`。
- 已全量重建 `mql5/Presets/*.set`，确保每个 preset 显式包含新增 input，不依赖默认值。

## 已落地策略

### v99g2

```yaml
v99g2:
  <<: v99g1
  dtp_exit_mode: 1
  dtp_partial_pct: 50
  dtp_post_partial_retrace: 0.30
  dtp_post_partial_lock_r: 1.0
  dtp_reset_peak_after_partial: true
```

### v99g3 对照组

```yaml
v99g3:
  <<: v99g2
  dtp_reset_peak_after_partial: false
```

### v99j3 加密候选

```yaml
v99j3:
  <<: v99j1
  dtp_exit_mode: 1
  dtp_partial_pct: 50
  dtp_post_partial_retrace: 0.30
  dtp_post_partial_lock_r: 1.5
  dtp_reset_peak_after_partial: true
```

## 下一轮实验矩阵

### 必跑 Model 4

```bash
python3 scripts/mt5_cli_backtest.py --strategies v99g1,v99g2,v99g3 --symbol XAUUSDm --days 180 --timeout 360
python3 scripts/mt5_cli_backtest.py --strategies v99g1,v99g2,v99g3 --symbol XAGUSDm --days 180 --timeout 360
python3 scripts/mt5_cli_backtest.py --strategies v99g1,v99g2,v99g3 --symbol EURUSDm --days 180 --timeout 360
python3 scripts/mt5_cli_backtest.py --strategies v99j1,v99j2,v99j3 --symbol BTCUSDm --days 365 --timeout 600
python3 scripts/mt5_cli_backtest.py --strategies v99j1,v99j3 --symbol ETHUSDm --days 365 --timeout 600
```

### 交易日志分析重点

- 统计 `dtp_partial`、`dtp_part_lock`、`dtp2` 事件数量。
- 对部分平仓后的余仓单独计算贡献：是否增加 3R+ 右尾，还是只是把原本 2R 附近的全平拆成两次。
- 比较最大回撤和连续亏损。v99g2 可能牺牲单笔确定性，必须看 equity 曲线而不是只看余额。

### 后续单变量候选

| 实验 | 参数 | 值 |
|------|------|----|
| 入场更精 | `min_ob_body_pct` | 55, 60 |
| 规避噪音 | `no_ob_start_hour/no_ob_end_hour` | 22/7, -1/-1 |
| 严控大R | `max_risk_atr` | 2.5 |
| 严控逆势 | `max_counter_risk_atr` | 1.2 |
| 追价更严 | `max_entry_offset_r` | 0.35 |
| 点差更严 | `min_risk_spread_ratio` | 4.0 |
| 余仓锁利 | `dtp_post_partial_lock_r` | 0.5, 1.0, 1.5 |
| 部分比例 | `dtp_partial_pct` | 33, 50, 67 |

## 2026-05-18 烟测更新

### 路径校正

第一次 30天烟测意外跑到了旧路径 `Experts\WaiTrade\WaiTrade_OB.ex5`，结果是 `v99g1/v99g2/v99g3` 全部 52笔、55.8%WR、余额 $222.08。该结果只能说明旧 EA 路径仍可运行，不能作为本轮实现验证。

已修复：

- `backtest_defaults.expert` 改为 `WaiTrade2\WaiTrade_OB`。
- `scripts/mt5_cli_backtest.py` 和 `scripts/mt5_backtest_win.py` 默认 expert 改为 WaiTrade2。
- 修复本机 `.ex5` 存在性检查，避免把 Windows 反斜杠当成本机文件名。

### 当前 WaiTrade2 EA 30天 XAU 烟测

命令：

```bash
python3 scripts/mt5_compile.py WaiTrade2/WaiTrade_OB
python3 scripts/mt5_cli_backtest.py --strategies v99g1,v99g2,v99g3 --symbol XAUUSDm --days 30 --timeout 240
```

结果：

| 策略 | EA路径 | 交易 | 胜率 | PF | 余额 |
|------|--------|------|------|----|------|
| v99g1 | WaiTrade2 | 41 | 53.7% | 0.88 | $157.65 |
| v99g2 | WaiTrade2 | 45 | 53.3% | 1.61 | $130.95 |
| v99g3 | WaiTrade2 | 45 | 55.6% | 1.63 | $132.07 |

解释：这只是 30天烟测，但它暴露了一个更重要的问题：新 `WaiTrade2` EA 路径与旧 `WaiTrade` 路径的结果不一致。v99g2 的 DTP runner 已能运行，但当前样本不支持“优于 v99g1”的结论。下一步必须先完成 WaiTrade2 新路径下的长样本基线复验，再判断 v99g2。
