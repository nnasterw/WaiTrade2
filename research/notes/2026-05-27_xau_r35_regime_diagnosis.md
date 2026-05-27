# 2026-05-27 XAU R35 行情共性诊断

## 结论

`v11b_xau_r35_m1_tp15_nomonth` 不应继续用月份或绝对价格窗口解释。更合理的定位是：

- R35 是 M1 高频趋势爆发/趋势回踩腿，适合大周期有持续净推进、M1 信号密集且前期兑现的行情。
- R35 弱月更像震荡、假突破、方向来回切换或极端抛物线后的高噪音行情；此时应切到低频高 PF 的 FAGE/保守 OB 腿，而不是强行让 R35 交易。
- 下一轮应构建未来可观测的 regime selector：趋势腿启用 R35，震荡/弱反馈腿启用 FAGE 或 R7 保守腿。

## R35 强弱月摘要

按 30 天启动窗口、初始资金 200U、目标余额 270U 划分：

- 强月：2024-08~2024-12、2025-02~2025-12，多数月余额达标，典型强月如 2025-04 915 单、WR 62.2%、PF 2.02、余额 25794.20。
- 弱月：2024-06、2024-07、2025-01、2026-01、2026-04。

逐单 CSV 聚合显示：

| 分组 | 月数 | 日均单 | WR | 总R/月均 | 前5天R | 前10天R |
|---|---:|---:|---:|---:|---:|---:|
| 强月 | 16 | 22.2 | 59.3% | +123.2R | +15.2R | +39.3R |
| 弱月 | 5 | 17.6 | 47.7% | -26.1R | -6.2R | -12.2R |

关键差异不是价格本身，而是“开局反馈 + 持续兑现”：

- 强月前 10 天通常已经净正，并且 TP 单足以覆盖 SL 单。
- 弱月前 5/10 天普遍给负反馈；即使交易密度很高，也是在放大错误 regime。
- 2025-01 是重要反例：绝对价格处在中间区间，但 R35 只到 234.09，说明价格窗口不是主因。
- 2026-01 是另一类反例：价格大幅单边但 R35 亏损，说明“趋势强”还要区分有序趋势和过热/噪音趋势。

## 弱月可用替代腿

从已有报告看，弱月并不是无策略可做，而是 R35 不适合：

| 月份 | R35余额 | 更优已有腿 | 余额 | 特征 |
|---|---:|---|---:|---|
| 2024-06 | 196.23 | v11_single_selector | 526.75 | 低频、高 PF |
| 2024-07 | 171.59 | v11xau_start_fage_2026_monthgate | 610.30 | 低频、高 WR |
| 2025-01 | 234.09 | v11_single_selector | 308.19 | FAGE 更稳 |
| 2026-01 | 133.11 | v11_single_selector_nomonth | 455.63 | R35 高频失效，保守腿有效 |
| 2026-04 | 46.42 | v11_single_selector | 307.22 | 保守腿有效 |

这支持双腿架构：趋势爆发用 R35，震荡/弱反馈用 FAGE/保守腿。

## 下一轮假设

1. **HTF 净推进过滤**
   - 如果 R35 只在 H1/H4 最近 N 根 K 线与入场方向同向推进超过 ATR 阈值时交易，弱月会减少假突破和逆大周期单。
   - 可直接复用现有 `enable_htf_net_push_filter`、`htf_net_push_tf`、`htf_net_push_bars`、`htf_net_push_min_atr`、`htf_net_push_counter_mult`。

2. **趋势爆发确认**
   - 如果加入 ATR 扩张、连续实体推进、MACD/EMA 斜率或成交量比率，R35 应保留 2025-04/05/10/11 的大盈利，同时避开 2024-06、2025-01 的低质量震荡。
   - 优先使用 EA 已有 `CalcVolumeRatio`、`HTFNetPush`、`MomentumRegime`，暂不硬编码新指标。

3. **早期反馈熔断**
   - 如果月初前 5~10 天 R35 交易已经净负，后续继续高频交易的赔率明显变差。
   - 应设计成通用反馈条件，例如 `min_trades` 后月内净利润/胜率/SL占比触发降频或切回 FAGE，而不是月份过滤。

4. **震荡腿增强**
   - R35 弱月中，FAGE/保守 OB 腿表现更好，说明震荡期应做低频、高确认、高 PF，而不是增加 M1 频率。
   - 后续可把震荡态定义为 HTF 净推进不足、ATR 扩张不足、早期反馈弱，然后启用 FAGE/R7 参数。

## 推荐实验顺序

1. R35 + HTFNetPush 硬过滤：只保留同向 H1/H4 净推进单。
2. R35 + HTFNetPush 软过滤：同向加仓，中性降频，反向禁入。
3. R35 + 月内反馈熔断：前 N 单或前 5 天净负时切回 FAGE/保守腿。
4. 双腿 selector：趋势 regime 用 R35，震荡/弱反馈 regime 用 FAGE。

所有实验禁止使用具体月份过滤；绝对价格只可作为诊断对照，不进入最终策略。

## R36/R37/R38 回测更新

新增三组无月份、无价格窗口实验：

- `v11b_xau_r36_m1_tp15_htfpush_hard`：R35 + H1 3bar 净推进硬过滤，反向/中性禁入。
- `v11b_xau_r37_m1_tp15_htfpush_soft`：R35 + H1 3bar 净推进软过滤，同向 1.2x、中性 0.45x、反向禁入。
- `v11b_xau_r38_m1_tp15_h4push_hard`：R35 + H4 2bar 净推进硬过滤。

阶段性结果：

| 月份 | R35 | R36 H1硬 | R37 H1软 | R38 H4硬 | 结论 |
|---|---:|---:|---:|---:|---|
| 2024-07 弱月 | 171.59 | 232.04 | 197.55 | 未跑 | H1硬过滤能减亏，但不达标 |
| 2025-01 弱月 | 234.09 | 279.93 | 270.60 | 未跑 | H1净推进可修复到达标边缘 |
| 2025-04 强月 | 25794.20 | 3308.69 | 15651.63 | 未跑 | 过滤保留趋势收益，软过滤更适合复利 |
| 2026-04 极端坏月 | 46.42 | 61.82 | 47.05 | 61.78 | H1/H4趋势过滤均失败，应切保守腿 |

诊断：

- HTF 净推进是有效因子，但不是完整 regime selector。
- 2026-04 属于“看似趋势、实际高噪音假延续”的坏簇，不能靠更大周期净推进解决。
- 下一步必须做双腿配合：默认 FAGE/保守腿保障 35% 月盈利，只有在 R35 自身早期反馈为正、或更强的趋势质量信号出现时，才提高 R35 权重。
- 单纯把 R35 继续收紧，只会把强月复利砍掉，仍无法解决 2026-04。

## 双腿收敛：`v11xau_range` + `v11xau_trend`

本轮把 XAU 候选池压缩为两条互补腿：

- `v11xau_range`：继承 `v11_single_selector`，定位为震荡/弱趋势反馈下的低频保守腿。
- `v11xau_trend`：继承 `v11b_xau_r35_m1_tp15_nomonth`，定位为 R35 M1 高频趋势爆发腿。

按 2024-06~2026-05 的 24 个 30 天启动窗口、初始资金 200U、目标余额 270U，两个静态候选取更优腿可做到 `pass=24/24`。关键选择如下：

| Regime | 代表月份 | 更优腿 | 说明 |
|---|---|---|---|
| 保守/震荡防守 | 2024-06、2024-07、2025-01、2026-01~05 | `v11xau_range` | R35 在这些窗口易高频放大假突破或过热噪音 |
| 趋势爆发/可持续兑现 | 2024-08~2024-12、2025-02~2025-12 | `v11xau_trend` | 高频 R35 能显著放大复利，尤其 2025-04/05/10/11 |

两腿最差达标月是 2024-09，`v11xau_trend` 余额 274.72，安全垫很薄；后续优化应优先保护这类边缘月。

## 可观测 Selector V2

避免月份和绝对价格筛选，使用月初前 5 天的真实交易反馈作为 regime 识别：

1. 默认运行/信任 `v11xau_range`。
2. 用小风险趋势 probe 观察 `v11xau_trend` 前 5 天反馈。
3. 满足以下条件才切到/放大趋势腿：
   - R35 前 5 天交易数 `>=20`。
   - R35 前 5 天净 R `>= -10R`。
   - R35 前 5 天 SL 占比 `<=78%`。

用已有 CSV 回放该规则：

| 指标 | 结果 |
|---|---:|
| 覆盖窗口 | 24 |
| 达标窗口 | 24 |
| 最低余额 | 274.72 |
| 余额合计 | 86890.96 |
| CSV一致性 | csv_mismatches=0 |

该规则修复了 R35 在 2026-01/02/04/05 的误启用问题：这些月份 R35 前 5 天交易密度高，但净 R 分别约为 -16.7、-56.9、-17.8、-34.8，属于“高频错误 regime”，应切回保守腿。

2026-05-27 复核时发现，部分 `v11_single_selector` 的 `.trades.csv` 缺失或来自旧归因，导致保守腿前 5 天反馈不可靠。已重新用 `backtest_digest.py --export-csv --brief` 对齐 9 个 range CSV，并确认 ledger 交易数与 CSV 行数 `mismatches=0`。

复核后证伪了“保守腿前 5 天净 R `< +5R` 才允许趋势腿”的附加条件：2025-12 保守腿前 5 天 `+8.7R`，但趋势腿前 5 天 `113` 笔、`+10.9R`、SL 占比 `56%`，最终趋势腿余额 `2892.79`，保守腿只有 `339.24`。取消该附加条件后，2024-07 仍因趋势 probe 交易数只有 `14` 笔而不会误切，整体仍为 `pass=24/24`、最低余额 `274.72`、余额合计 `86890.96`。

新增 `scripts/xau_dual_selector_eval.py --grid` 做阈值稳健性扫描，并缓存 feedback/CSV 行数，避免重复读取逐单 CSV。Top 结果显示当前规则不是孤点：

| 排名 | probe天数 | 最小交易数 | 最小净R | 最大SL占比 | 达标 | 最低余额 | 余额合计 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 15 | -15 | 78% | 24/24 | 274.72 | 86890.96 |
| 2 | 5 | 15 | -10 | 78% | 24/24 | 274.72 | 86890.96 |
| 3 | 5 | 20 | -15 | 78% | 24/24 | 274.72 | 86890.96 |
| 4 | 5 | 20 | -10 | 78% | 24/24 | 274.72 | 86890.96 |
| 5 | 7 | 15 | -30 | 70% | 24/24 | 274.72 | 86890.96 |

建议 EA 化时优先用较保守且可解释的 `5天/20笔/-10R/78%SL`，但把 `5天/15笔/-15R/78%SL` 作为敏感性对照回测。

## 趋势腿边缘月坏簇对比

新增 `scripts/xau_trend_cluster_contrast.py`，直接基于 selector 选出的趋势腿月份，对比最低余额边缘月和最高余额强月的逐单簇，不读取原始 Agent 日志。

当前默认边缘月：

- 2024-09：余额 274.72，188 笔。
- 2024-12：余额 297.80，174 笔。
- 2025-03：余额 342.98，327 笔。

当前默认强月：

- 2025-04：余额 25794.20，915 笔。
- 2025-05：余额 14460.24，655 笔。
- 2025-10：余额 21968.45，614 笔。
- 2025-11：余额 11286.78，594 笔。

按 `hour` 对比后，候选坏簇如下：

| 小时 | 边缘月R | 边缘月笔数 | 强月R | 强月笔数 | 全趋势月R | 判断 |
|---:|---:|---:|---:|---:|---:|---|
| 10 | -14.42 | 47 | +40.24 | 136 | +65.58 | 修边缘月但明显伤强月，不宜先做硬过滤 |
| 03 | -12.59 | 38 | +12.47 | 87 | +35.48 | 有伤害，需谨慎 |
| 04 | -12.20 | 22 | +3.03 | 96 | +5.65 | 最像可泛化坏簇，可作为候选实验 |
| 02 | -6.41 | 22 | +71.33 | 114 | +108.99 | 强月核心收益，不能过滤 |

离线 `pnl_proxy` 估算显示，单纯过滤这些小时对最终余额提升很小，且不等同于 MT5 回测；因此结论只是“候选实验”，不是上线规则。下一轮若做 EA 参数实验，优先测 `v11xau_trend` 的 `04:00` 禁入或降仓，而不是大范围禁入 `03/10`。

## 04:00 候选 MT5 实验

新增两个真实 MT5 候选：

- `v11xau_trend_h04_block`：继承 `v11xau_trend`，设置 `no_entry_hours: "4"`。
- `v11xau_trend_h04_half`：继承 `v11xau_trend`，设置 `low_risk_hours: "4"`、`low_risk_hour_mult: 0.5`。

已用 MT5 后台模式回测 3 个边缘月和 4 个强月：

| 月份 | 原趋势 | 04禁入 | 04半仓 | 当前最优 |
|---|---:|---:|---:|---|
| 2024-09 | 274.72 | 306.92 | 277.58 | 04禁入 |
| 2024-12 | 297.80 | 303.36 | 300.15 | 04禁入 |
| 2025-03 | 342.98 | 382.22 | 368.85 | 04禁入 |
| 2025-04 | 25794.20 | 25215.45 | 26011.58 | 04半仓 |
| 2025-05 | 14460.24 | 13077.48 | 14492.45 | 04半仓 |
| 2025-10 | 21968.45 | 22308.27 | 21914.84 | 04禁入 |
| 2025-11 | 11286.78 | 12123.12 | 11402.53 | 04禁入 |

7 个已测窗口汇总：

| 策略 | 最低余额 | 余额合计 | 观察 |
|---|---:|---:|---|
| 原趋势 | 274.72 | 74425.17 | 最低月安全垫薄 |
| 04禁入 | 303.36 | 73716.82 | 明显修边缘月，但 2025-05 伤害较大 |
| 04半仓 | 277.58 | 74767.98 | 总余额最高，但最低月安全垫提升有限 |

digest 复核：

- `v11xau_trend_h04_block_202409`：181 笔，`total_r=21.74`，`04:00` 已不再出现在负小时 Top；余额从 274.72 提到 306.92。
- `v11xau_trend_h04_half_202504`：916 笔，`total_r=320.70`，`04:00` 仍为小正 `+1.60R`，说明强趋势月不宜简单硬禁。

阶段结论：

- 如果目标优先是“每月 35% 安全垫”，`04禁入` 更好。
- 如果目标优先是“更快复利/余额合计”，`04半仓` 在已测窗口更好。
- 还不能定稿；必须补全剩余趋势月份后再把其中一个纳入双腿 selector。

2026-05-27 复核当前工作区报告时，已测覆盖为 `7/16` 个趋势月份：

- 已测：2024-09、2024-12、2025-03、2025-04、2025-05、2025-10、2025-11。
- 未测：2024-08、2024-10、2024-11、2025-02、2025-06、2025-07、2025-08、2025-09、2025-12。

临时 ledger 汇总：

| 策略 | 已测窗口 | 最低余额 | 已测余额合计 |
|---|---:|---:|---:|
| 原趋势 | 7 | 274.72 | 74425.17 |
| 04禁入 | 7 | 303.36 | 73716.82 |
| 04半仓 | 7 | 277.58 | 74767.98 |

当前 Codex 运行环境为 `workspace-write`，无法写入 Wine/MT5 的 `MQL5/Profiles/Tester/*.set`，继续 MT5 后台回测会报 `PermissionError: Operation not permitted`。因此本轮不能补完剩余 9 个窗口；恢复可写 Wine 目录后，应第一优先补跑这些窗口。

已新增 `scripts/xau_trend_variant_matrix.py` 固化该检查。当前命令：

```bash
python3 scripts/xau_trend_variant_matrix.py --available-to 2026.05.26 --commands
```

输出会同时给出：

- 16 个趋势月份的 `v11xau_trend` / `v11xau_trend_h04_block` / `v11xau_trend_h04_half` 覆盖矩阵。
- 每个变体的已测窗口数、最低余额、余额合计。
- 剩余缺口月份。
- 可直接执行的 MT5 后台补跑命令。

2026-05-27 进一步从已测 7 个窗口中抽取可观测选择规则：

- 候选规则：趋势腿前 5 天净 R `>=25R` 时使用 `04半仓`，否则使用 `04禁入`。
- 当前已测表现：`tested=7/16`，最低余额 `303.36`，余额合计 `75927.92`。
- 已测选择：
  - `04禁入`：2024-09、2024-12、2025-03、2025-10、2025-11。
  - `04半仓`：2025-04、2025-05。

该规则能解释当前 7 个窗口中“边缘月需要抬安全垫、极强趋势月不宜硬禁 04:00”的分叉。但仍只是候选，不能定稿；剩余 9 个趋势月份补跑完成前，禁止把它写入最终 EA selector。

`--h04-rule` 现在会打印缺失窗口的预测选择，便于补跑后直接核对。当前 9 个待测窗口预测：

| 月份 | 预测 | tf5反馈 |
|---|---|---|
| 2024-08 | 04禁入 | n50 / +9.7R / SL56% |
| 2024-10 | 04禁入 | n57 / +12.1R / SL53% |
| 2024-11 | 04禁入 | n29 / -5.2R / SL76% |
| 2025-02 | 04禁入 | n47 / -3.1R / SL62% |
| 2025-06 | 04禁入 | n128 / +15.5R / SL64% |
| 2025-07 | 04禁入 | n65 / +23.1R / SL55% |
| 2025-08 | 04禁入 | n90 / +23.5R / SL59% |
| 2025-09 | 04半仓 | n188 / +37.8R / SL60% |
| 2025-12 | 04禁入 | n113 / +10.9R / SL56% |

这会形成一个清晰的下一轮验证标准：补跑后如果 2025-09 不是半仓更优，或多个 `+10R~+23R` 月份反而半仓更优，则 `25R` 阈值需要下调或增加第二个特征。

新增 `--h04-grid` 扫描半仓阈值。已测 7 个窗口上，`23R/25R/28R` 并列最优：

| 阈值 | 已测 | 最低余额 | 余额合计 | 半仓月份数 | 说明 |
|---:|---:|---:|---:|---:|---|
| 23R | 7/16 | 303.36 | 75927.92 | 5 | 更激进，待测 2025-07/08 也会偏向半仓 |
| 25R | 7/16 | 303.36 | 75927.92 | 3 | 当前推荐，解释性较稳 |
| 28R | 7/16 | 303.36 | 75927.92 | 3 | 与 25R 在已测窗口等价 |
| 20R | 7/16 | 303.36 | 75207.33 | 6 | 合计下降 |
| 30R | 7/16 | 303.36 | 75131.79 | 2 | 合计下降 |

因此 `25R` 不是孤点，但真正敏感区在待测月份：2025-07 `+23.1R`、2025-08 `+23.5R`。补跑后若这两个月半仓优于禁入，阈值应考虑下调到 `23R`；若禁入更优，维持 `25R`。

命令：

```bash
python3 scripts/xau_trend_variant_matrix.py --available-to 2026.05.26 --h04-rule --commands
python3 scripts/xau_trend_variant_matrix.py --available-to 2026.05.26 --h04-grid
```

2026-05-27 继续补强低 token 反馈环：

- `xau_trend_variant_matrix.py` 支持按阈值敏感度排序缺口窗口：

```bash
python3 scripts/xau_trend_variant_matrix.py --available-to 2026.05.26 --h04-rule --h04-todo-sort sensitivity --commands --commands-sort sensitivity
```

当前补跑优先级：

| 优先级 | 月份 | 预测 | tf5反馈 | 距25R阈值 |
|---:|---|---|---|---:|
| 1 | 2025-08 | 04禁入 | n90 / +23.5R / SL59% | 1.5R |
| 2 | 2025-07 | 04禁入 | n65 / +23.1R / SL55% | 1.9R |
| 3 | 2025-06 | 04禁入 | n128 / +15.5R / SL64% | 9.5R |
| 4 | 2025-09 | 04半仓 | n188 / +37.8R / SL60% | 12.8R |
| 5 | 2024-10 | 04禁入 | n57 / +12.1R / SL53% | 12.9R |
| 6 | 2025-12 | 04禁入 | n113 / +10.9R / SL56% | 14.1R |
| 7 | 2024-08 | 04禁入 | n50 / +9.7R / SL56% | 15.3R |
| 8 | 2025-02 | 04禁入 | n47 / -3.1R / SL62% | 28.1R |
| 9 | 2024-11 | 04禁入 | n29 / -5.2R / SL76% | 30.2R |

解释：2025-07/08 直接决定 `23R` 与 `25R/28R` 的阈值分歧；2025-09 用来验证“强趋势月 04:00 只降仓、不硬禁”的假设。若只恢复一次 MT5 权限，优先跑前 4 个窗口。

`xau_trend_cluster_contrast.py` 新增 `--numeric-bins`，用于对连续字段做低 token 分桶坏簇分析，例如：

```bash
python3 scripts/xau_trend_cluster_contrast.py --available-to 2026.05.26 --field duration_min --numeric-bins 0.5,1,2,5,15,60 --top 10
python3 scripts/xau_trend_cluster_contrast.py --available-to 2026.05.26 --field bounce_sec --numeric-bins 30,120,300,900,1800 --top 10
```

当前结果没有发现比 `04:00` 更值得优先实测的数值坏簇：

- `duration_min <1` 在边缘月仅 `-0.28R`，强月 `+244.08R`，不适合过滤。
- `bounce_sec <120` 在边缘月 `-1.78R`，强月 `+64.58R`，也不适合单独过滤。
- 因此本轮不新增复杂出场/等待过滤，继续优先验证 `04禁入/04半仓` 的可观测选择规则。

新增 `--combined-h04` 把已验证 h04 结果合并回完整双腿 selector。规则：

- range 月份仍用 `v11xau_range`。
- trend 月份按 `tf5净R>=25R` 选择 `04半仓` 或 `04禁入`。
- 若该 h04 月份尚未真实 MT5 回测，则明确标记为 `fallback` 并使用原趋势腿，不把预测当证据。

命令：

```bash
python3 scripts/xau_trend_variant_matrix.py --available-to 2026.05.26 --combined-h04
```

当前证据下的完整 24 个月结果：

| 口径 | 达标 | 最低余额 | 余额合计 | 说明 |
|---|---:|---:|---:|---|
| 原双腿 V2 | 24/24 | 274.72 | 86890.96 | 2024-09 安全垫很薄 |
| 双腿 + 已验证 h04，缺口 fallback | 24/24 | 287.68 | 88393.71 | h04 已真实提升整体安全垫，但 9 个 trend 月仍未补测 |

解释：

- 2024-09 从 `274.72` 提到 `306.92` 后，当前最低月变为 2026-01 的 range 腿 `287.68`。
- 余额合计净增约 `1502.75`，来自 7 个已验证 h04 趋势月。
- 该结果可以作为“当前最保守可引用进展”，但不能作为最终上线 selector；最终仍需补完 9 个 h04 缺口。

## Range 腿补强方向

趋势腿 h04 修复后，完整双腿当前最低月变成 2026-01 的 range 腿 `287.68`。因此下一轮不应只补趋势腿，也要给 range 腿找低成本安全垫。

`xau_trend_cluster_contrast.py` 已扩展 `--leg range`，同一工具现在可以对趋势腿和震荡腿做坏簇对比：

```bash
python3 scripts/xau_trend_cluster_contrast.py --available-to 2026.05.26 --leg range --field hour --edge-count 3 --strong-count 3 --top 12
python3 scripts/xau_trend_cluster_contrast.py --available-to 2026.05.26 --leg range --field duration_min --numeric-bins 5,15,30,60,180,720,1440 --edge-count 3 --strong-count 3 --top 10
```

当前 range 腿边缘月：

- 2026-01：`287.68`，57 笔。
- 2026-04：`307.22`，19 笔。
- 2025-01：`308.19`，18 笔。

当前 range 腿强月：

- 2026-02：`611.87`，3 笔。
- 2024-06：`526.75`，10 笔。
- 2026-03：`378.23`，7 笔。

主要坏簇：

| 簇 | 边缘月R | 强月R | 全range月R | 判断 |
|---|---:|---:|---:|---|
| hour=15 | -2.32 | 0.00 | -1.85 | 可测硬禁，样本少但伤害低 |
| hour=14 | -6.73 | +12.53 | +18.18 | 不宜硬禁，更适合半仓 |
| hour=14/15 且 duration<5 | -7.83 | +0.15 | -10.18 | 核心现象，但 duration 是事后字段，不能直接作为入场过滤 |
| duration<5 | -11.76 | -2.52 | -16.47 | 说明 range 腿薄弱月主要死于快速反向 SL |

基于此新增两个真实 MT5 候选：

- `v11xau_range_h15_block`：继承 `v11xau_range`，在基线禁入小时 `0,9,12,17,18` 外追加 `15`，最终 `no_entry_hours: "0,9,12,15,17,18"`。
- `v11xau_range_h1415_half`：继承 `v11xau_range`，`low_risk_hours: "14,15"`、`low_risk_hour_mult: 0.5`。

2026-05-27 复查时发现一个重要配置陷阱：YAML 继承里直接写 `no_entry_hours: "15"` 会覆盖基线禁入小时，而不是追加。已修复并加测试锁定：

```text
v11xau_range        InpNoEntryHours=0,9,12,17,18
v11xau_range_h15   InpNoEntryHours=0,9,12,15,17,18
v11xau_range_h1415 InpNoEntryHours=0,9,12,17,18; InpLowRiskHours=14,15
```

注意：`v11xau_range` 是 `v11_single_selector` 的正式 range 腿命名，但历史报告多以 `v11_single_selector` 记录。恢复 MT5 权限后建议一起跑正式名和两个候选：

```bash
python3 scripts/xau_trend_variant_matrix.py --available-to 2026.05.26 --leg range --variants v11xau_range,v11xau_range_h15_block,v11xau_range_h1415_half --commands
```

若只想和已有历史基线对齐，可用：

```bash
python3 scripts/xau_trend_variant_matrix.py --available-to 2026.05.26 --leg range --variants v11_single_selector,v11xau_range_h15_block,v11xau_range_h1415_half --commands
```

建议补跑时按当前基线余额从低到高排序，先验证最薄月份：

```bash
python3 scripts/xau_trend_variant_matrix.py --available-to 2026.05.26 --leg range --variants v11_single_selector,v11xau_range_h15_block,v11xau_range_h1415_half --commands --commands-sort balance
```

当前排序：

1. 2026-01：`287.68`
2. 2026-04：`307.22`
3. 2025-01：`308.19`
4. 2026-05：`370.23`
5. 2024-07：`372.63`
6. 2026-03：`378.23`
7. 2024-06：`526.75`
8. 2026-02：`611.87`

优先验证 2026-01、2026-04、2025-01 三个 edge 月；若半仓/禁入能把 2026-01 抬到 `300+` 且不明显伤害 2024-06/2026-02，则 range 腿安全垫有望继续提升。

## 统一补跑队列

新增 `scripts/xau_backtest_queue.py`，把 range 腿和 trend 腿的缺口统一成一个低 token 队列：

```bash
python3 scripts/xau_backtest_queue.py --available-to 2026.05.26 --top 12 --commands
```

默认排序原则：

1. 先跑前 `3` 个 range 薄弱月，按当前基线余额从低到高排序，用来抬当前最低月。
2. 再跑 trend h04 缺口，按 `abs(tf5净R - 25R)` 从小到大排序，用来验证半仓阈值和趋势复利。
3. 最后补 range 其余控制月，确认 range 小时过滤没有伤害强月。

当前队列摘要：

| 排名 | 腿 | 月份 | 原因 |
|---:|---|---|---|
| 1 | range | 2026-01 | low_balance=$287.68 |
| 2 | range | 2026-04 | low_balance=$307.22 |
| 3 | range | 2025-01 | low_balance=$308.19 |
| 4 | trend | 2025-08 | h04_delta=1.5R |
| 5 | trend | 2025-07 | h04_delta=1.9R |
| 6 | trend | 2025-06 | h04_delta=9.5R |
| 7 | trend | 2025-09 | h04_delta=12.8R |
| 8 | trend | 2024-10 | h04_delta=12.9R |
| 9 | trend | 2025-12 | h04_delta=14.1R |
| 10 | trend | 2024-08 | h04_delta=15.3R |
| 11 | trend | 2025-02 | h04_delta=28.1R |
| 12 | trend | 2024-11 | h04_delta=30.2R |

如果只想继续趋势腿：

```bash
python3 scripts/xau_backtest_queue.py --available-to 2026.05.26 --include trend --top 4 --commands
```

如果只想继续抬安全垫：

```bash
python3 scripts/xau_backtest_queue.py --available-to 2026.05.26 --include range --top 3 --commands
```

## 补跑结果消化

新增 `scripts/xau_ingest_reports.py`，用于外部 MT5 补跑完成后，把新报告消化成低 token digest 和逐单 CSV，再刷新 audit。

```bash
python3 scripts/xau_ingest_reports.py --dry-run
python3 scripts/xau_ingest_reports.py --audit --commands
```

默认只扫描当前双腿相关策略：

- `v11_single_selector`
- `v11xau_range`
- `v11xau_range_h15_block`
- `v11xau_range_h1415_half`
- `v11b_xau_r35_m1_tp15_nomonth`
- `v11xau_trend`
- `v11xau_trend_h04_block`
- `v11xau_trend_h04_half`

需要历史全量 XAU 报告时，显式使用：

```bash
python3 scripts/xau_ingest_reports.py --strategies all --dry-run
```

实现细节：

- 若能匹配 Agent/Tester 日志，则生成 `.md` 和 `.trades.csv`。
- 若未匹配逐单日志，则只保留 `.md`，删除空 `.trades.csv`，避免 0 行 CSV 污染后续 first-days feedback。
- `--audit` 会在 ingest 后运行 `xau_goal_audit.py --refresh-ledger`。

## 目标完成度审计

新增 `scripts/xau_goal_audit.py`，用于在每轮补跑后快速判断当前目标是否真的完成，而不是只看已有 24/24 月达标就误判。

```bash
python3 scripts/xau_goal_audit.py --available-to 2026.05.26 --details
```

当前输出：

```text
AUDIT status=incomplete reasons=trend_h04_missing,range_candidate_missing months=24 pass=24/24 min=$287.68 balance_sum=$88393.71 missing_trend_h04=9 missing_range_candidates=8 next=range:2026-01:low_balance=$287.68
MISSING_TREND_H04 2024-08,2024-10,2024-11,2025-02,2025-06,2025-07,2025-08,2025-09,2025-12
MISSING_RANGE_CANDIDATES 2024-06,2024-07,2025-01,2026-01,2026-02,2026-03,2026-04,2026-05
```

解释：

- 当前已验证口径仍是 `24/24` 达标，最低余额 `287.68`，但这只是“已验证 h04 + 未测缺口 fallback”的保守进展。
- 目标不能标记完成，因为 trend h04 还缺 `9` 个真实 MT5 窗口，range 候选还缺 `8` 个真实 MT5 窗口。
- 每次外部补跑后，先跑 audit，再决定是否更新最终 selector 或继续补缺口。

2026-05-28 增强 audit 门禁能力：

```bash
python3 scripts/xau_goal_audit.py --available-to 2026.05.26 --commands
python3 scripts/xau_goal_audit.py --available-to 2026.05.26 --fail-on-incomplete
python3 scripts/xau_goal_audit.py --refresh-ledger --available-to 2026.05.26 --commands
```

- `--commands` 会输出下一条建议 MT5 后台命令，当前是 2026-01 range 腿候选补跑。
- `--fail-on-incomplete` 在缺口未补完时返回非 0，适合放在定稿/推送前作为自动门禁。
- `--refresh-ledger` 会从当前 `results/backtest/*.txt` 临时重建 ledger 后审计，避免新报告已落盘但默认 JSONL 过期。
- 当前返回码为 `1`，这是正确行为，因为还有 `9` 个 trend h04 缺口和 `8` 个 range 候选缺口。

2026-05-28 继续补强 MT5 可信度证据：

- 新生成的 MT5 报告会在 meta 行写入 `模型: 4`。
- `parse_backtest_report_content()` 和 `backtest_ledger.py` 会保留 `model` 字段。
- `xau_goal_audit.py` 默认要求 `--required-model 4`；老报告没有模型字段，会被计入 `model_unverified`。

当前 audit 因此新增一个未完成原因：

```text
AUDIT status=incomplete reasons=trend_h04_missing,range_candidate_missing,model_unverified ...
model_unverified=24
```

这不是说旧结果一定不是 Real Ticks，而是当前报告文本无法证明它是 Model 4。后续补跑的新报告会带 `模型: 4`，审计才能把对应月份从 `model_unverified` 里移除。

2026-05-28 修复模型证据选择规则：

- 同一策略/窗口若同时存在旧“模型未知”报告和新 `Model 4` 报告，audit / variant matrix 会优先选择 `Model 4` 报告。
- 即使旧报告余额更高，也不会遮蔽新 Model 4 证据。
- 若没有 Model 4 报告，才回退旧报告并继续标记 `model_unverified`。

这保证后续补跑进入目录后，审计会用更可信的 Real Ticks 结果，而不是自动挑历史最高余额。

实现注意：

- 当前 V2 是离线 selector 回放，不等同于已部署 EA。
- 单账号单 EA 下要实盘化，需要在 EA 内支持“保守腿 + 小风险趋势 probe + 月内 profile 切换”。
- 若只用单一静态 preset，`v11xau_range` 能保底但会错过 2025 年趋势复利；`v11xau_trend` 复利强但 2026 年多个月会爆亏。
