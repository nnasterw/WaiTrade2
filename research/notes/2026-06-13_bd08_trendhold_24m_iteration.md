# BD08 Trendhold 迭代阶段记录 - 2026-06-13

## 目标
- 2026-05 月盈利 > 1000
- 2025-05 月盈利 > 3000
- 24 个独立月全部盈利
- 口径: MT5 CLI / Model 4 Real Ticks / XAUUSDm M1 / $350 / 1:1000

## 当前基线
- 策略: BD07 .set 底座 + H4方向锁 + BOS回踩 + DTP 2.0/0.30 + risk 5%
- 24 独立月汇总: results/backtest/v11xau-bd08-trendhold_vs_bd07_24m_20260613_101820.csv
- 24月累计: 92574.67
- 盈利月份: 19/24
- 2025-05: 4021.75，达标
- 2026-05: 505.46，未达标
- 亏损月: 2024-08, 2024-11, 2026-02, 2026-03, 2026-04

## 订单级诊断
- 24月总计 <1m 持仓: n=2759, net=-17059.87，是最大亏损特征。
- 亏损月 <1m 持仓: n=492, net=-1986.48。
- 2026-05: <1m n=46, net=-430.00；>120m n=5, net=+700.92。
- 2026-05 的普通 OB: n=6, net=+66.11；SWP: n=87, net=+449.69，但 SWP <1m fast_net=-481.84。
- 因此问题不是简单“关 SWP”或“延迟入场”，SWP 同时贡献 2505/2605 的主要利润。

## 已验证变体小样本
小样本月份: 2024-08, 2024-11, 2026-02, 2026-03, 2026-04, 2026-05, 2025-05。
结果文件:
- results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260613_121638.csv
- results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260613_123637.csv
- results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260613_130941.csv
- results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260613_135641.csv
- results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260613_144842.csv

### 入口过滤类
- tick_mild: 与基线几乎一致，未改善。
- tick_mid: 降低交易数，但 2605=-50.83，2505=397.12，失败。
- bounce_close_1: 2605=-109.95，2505=44.30，失败。
- pullback_50: 2605=-120.38，2505=1103.64，失败。
- momentum_m1: 2605=505.46，2505=4069.07，基本等于基线。

结论: 延迟/确认入场会漏掉趋势利润，不能作为主解。

### 结构/动能持仓类
- struct_skip_mfe: 2605=415.84，2505=4068.98，失败。
- struct_mom_hold: 2605=505.46，2505=4021.75，基本无效。
- struct_hold_skip: 2605=415.84，2505=4068.98，失败。
- momentum_regime: 2605=469.98，2505=3602.27，失败。
- dtp_stage2: 2605=505.46，2505=3633.79，未改善2605。
- momentum_stage2: 2605=469.98，2505=3683.17，失败。

结论: 当前 2605 上限不是 DTP 回撤空间；强动能放宽 DTP 没有把 2605 推过1000。

### 账户状态防守类
- sweep_neg_03: 2605=540.25，2505=4021.75，亏损月仍4个。
- sweep_neg_00: 2605=543.12，2505=4021.75，亏损月仍5个。
- all_neg_05: 2605=505.46，2505=4021.75，亏损月仍4个。
- risk10_sweep_neg_03: 2605=688.75，2505=4028.92，亏损月仍5个。
- risk10_all_neg_05: 2605=642.59，2505=4028.92，亏损月仍5个。

结论: 账户状态型防守能略微提高2605，但远未达标；提高风险没有线性放大收益。

## 代码修复
- mql5/Experts/WaiTrade3/WaiTrade_OB_SMC.mq5
  - EntryEngine/H4 aligned 结构单现在在设置 use_structure_sl 时同步设置 skip_mfe_exits = InpStructSkipMFEExits。
  - 目的: 保证 InpStructSkipMFEExits 对所有结构持仓路径一致生效。
- 编译: python scripts/compile_and_deploy.py --v3 通过，0 errors 0 warnings。
- 测试: python -m pytest tests/test_mt5_common.py -q 通过，93 passed。

## 下一步建议
1. 继续从订单级特征提取 SWP 快速亏损的实时条件: bounce_seconds、confirm_ob_pos、risk_price、OB age、spread_risk。
2. 不要继续尝试 BounceClose/Pullback 这类延迟入场，它们已明确破坏 2505/2605 趋势利润。
3. 优先考虑 SWP 内部质量降权，而不是关闭 SWP；尤其是“快速确认/浅确认/特定 risk 区间”的组合特征。
4. 完成候选后必须重新跑 24 独立月，当前目标未完成。

## 追加验证 - 2026-06-13 16:xx

### 干净2605日志特征
- 单独回测: results/backtest/v11xau-bd08-trendhold_variant_subset_20260613_161004.csv
- 报告: TRENDHOLD_202605_161004.htm
- ENTRY_DIAG 与交易数均为93，可顺序对齐。

实时入场特征拆分:
- confirm_pos -0.7..0: n=53, net=-375.97, fast_net=-260.79
- confirm_pos <-0.7: n=40, net=+891.77, fast_net=-169.21
- risk_atr 0.5-0.8: n=65, net=-169.16
- risk_atr <0.5: n=20, net=+706.17
- spread_risk 0.15-0.25: n=56, net=-407.60
- spread_risk >=0.25: n=13, net=+897.03
- pos_mult 0.5-0.8: n=27, net=-278.98
- pos_mult >=1.1: n=4, net=-115.09
- pos_mult <0.5: n=54, net=+670.27

注意: 这些特征在2605内有解释力，但不能直接当结论，必须跨月验证。

### 浅确认位置变体
结果文件: results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260613_161337.csv
- shallow_07_03: 2605=172.09, 2505=5271.94，2605严重退化。
- shallow_07_filter: 2605=-13.76, 2505=3758.71，失败。
- neg_swp_shallow_filter / neg_swp_shallow_03: 与基线完全一致，说明该 BadCluster 条件未产生实际影响或未进入触发状态。

结论: confirm_pos 在单月诊断有效，但全局浅确认过滤会截断2605大赢，不能采用。

## 当前总体结论
- 尚无候选满足目标。
- 目标仍未完成: 2605仍低于1000，24独立月仍非全盈利。
- 已证伪方向: Tick噪音门控、BounceClose、Pullback、EntryMomentum、结构跳过MFE、结构动能SL保持、动能DTP放宽、DTP二阶段、月内负值SWP降权、浅确认全局过滤。
- 下一步应从多月ENTRY_DIAG交易级数据建立跨月特征表，不再只看2605；优先检查 confirm_pos/risk_atr/spread_risk/pos_mult 的跨月期望值，而不是继续单月假设。

## 追加验证 - 2026-06-14

### 当前最佳候选 24 独立月
候选: `risk8_fast02_swp_h1_05`

参数增量:
- `risk_percent=8`
- `sweep_early_bounce_sec=0..2` 过滤
- `sweep_h1_aligned_mult=0.5`

结果文件:
- `results/backtest/v11xau-bd08-trendhold_risk8_fast02_swp_h1_05_vs_bd07_24m_merged_20260614_000635.csv`
- `results/backtest/v11xau-bd08-trendhold_risk8_fast02_swp_h1_05_entry_features_20260614_003106.csv`

24月结果:
- 累计: 139652.37，BD07=1235783.75。
- 盈利月: 20/24，BD07=17/24。
- 2025-05: 10216.13，达标。
- 2026-05: 1017.08，达标。
- 亏损月: 2024-08=-19.02、2024-11=-60.00、2026-02=-206.72、2026-04=-89.51。

订单级事实:
- SWP slow(`hold>=1m`): n=1875, net=+146134.11。
- SWP fast(`hold<1m`): n=1569, net=-21457.26。
- OB fast: n=363, net=+3646.25。

结论: 不能关 SWP；问题是部分 SWP 秒杀，而不是 SWP 信号整体负期望。

### 假说: SWP高仓位倍数是坏簇
24月 ENTRY_DIAG 显示:
- SWP `pos_mult>=1.05`: n=111, net=-1468.43, fast_net=-1803.71。
- 该特征是入场前可观测，不依赖月份标签。

实现:
- 新增默认关闭参数:
  - `InpSweepHighPosMultMin=0.0`
  - `InpSweepHighPosMultMult=1.0`
- 映射已同步 `yaml_to_set.py` / `strategies.yaml` / `tests/test_mt5_common.py`。
- 编译: `python scripts/compile_and_deploy.py --v3` 通过，0 errors 0 warnings。
- 测试: `python -m pytest tests/test_mt5_common.py -q` 通过，93 passed。

关键月验证文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_012517.csv`

结果:
- hard cut: 2026-02 -191.27，2026-04 -88.54，2026-05 +1017.46，2025-05 首次 run FAIL。
- 0.5x: 与基线几乎一致，2026-02 -206.72，2026-04 -89.51，2026-05 +1017.08，2025-05 +10216.13。

结论: 证伪。该特征跨24月负期望，但无法覆盖剩余亏损月的主要亏损来源，只能小幅改善。

### 假说: DTP部分平仓释放趋势余仓
动机: 用户目标强调小周期趋势和K线动能未衰弱时继续持仓；现有 DTP 支持首次触发只部分平仓，余仓继续按更宽回撤跑。

关键月验证文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_015311.csv`

结果:
- `dtp_part50`: 2024-08 -12.63，2024-11 -62.46，2026-02 -218.90，2026-04 -93.86，2026-05 +1011.27，2025-05 +8053.09。
- `dtp_part30`: 2024-08 -14.25，2024-11 -65.60，2026-02 -219.07，2026-04 -100.69，2026-05 +1009.02，2025-05 +8239.52。

结论: 证伪。DTP部分平仓未改善亏损月，还压低 2505 趋势利润。当前问题不应继续从 DTP partial 参数找解。

## 2026-06-14 收敛状态
- 已达成: 2505 > 3000，2605 > 1000。
- 未达成: 24独立月全盈利。
- 当前剩余亏损并非单一入场可观测特征集中导致；继续加 SWP 过滤会损伤趋势利润且收益有限。
- 下一步方向应回到结构入口: 增加只在明确结构突破/回踩后触发的低频补偿单，目标是覆盖 2024-08/2024-11/2026-02/2026-04 的小额亏损，同时不能截断 2025 趋势大月。

## 追加验证 - 2026-06-14 03:xx

### 假说: 小周期强动能继续持仓，弱动能才退出
动机: 用户要求关注小周期趋势与K线动能；如果小周期未反转、动能未衰弱到强力反弹、且未出现延续失败，则继续持仓。

实现方式: 使用现有 `InpEnableMomentumRegime`，在强动能时放宽 DTP 回撤，在弱动能时允许 `momentum_weak` 退出；未新增 EA 逻辑。

关键月验证文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_022426.csv`

结果:
- `risk8_fast02_h105_mom`: 2024-08 -20.62，2024-11 -42.96，2026-02 -197.46，2026-04 -99.61，2026-05 +1011.15，2025-05 +6568.55。
- `risk8_fast02_h105_mom_wide`: 与上面一致，说明强动能放宽倍数没有产生额外效果。
- `risk8_fast02_h105_mom_stage2`: 2024-08 -27.94，2026-02 -197.46，2026-04 -99.61，2026-05 +1011.15，2025-05 +5945.75。

结论: 证伪。现有小周期动能持仓机制不能转正剩余亏损月，并明显压低 2505。继续调 `StrongDTPRetraceMult` 或 DTP stage 不应作为主路径。

### 假说: 过滤普通OB非H1对齐 + SWP早反弹 + 月内利润回吐锁
离线 ENTRY_DIAG 模拟显示，过滤:
- `SWP bounce_sec 0..5`
- 普通 `OB && h1=0`
- 月内利润峰值达到约 $8 后，回吐到峰值30%-40%时停手

可以让关键亏损月在订单序列模拟中转正，并保留 2505/2605 达标。但该模拟未覆盖 MT5 实际并发持仓、账户余额峰值和 EA 月内锁触发顺序，因此必须用 MT5 证伪。

实现:
- 新增默认关闭参数 `InpOBNoH1PosMult=1.0`。
- 仅作用于普通 OB，不影响 sweep/range/HTF pullback。
- 同步 `yaml_to_set.py`、`strategies.yaml`、`tests/test_mt5_common.py`。
- 编译: `python scripts/compile_and_deploy.py --v3` 通过，0 errors 0 warnings。
- 测试: `python -m pytest tests/test_mt5_common.py -q` 通过，93 passed。
- 一致性: `python scripts/check_strategy_consistency.py v11xau-bd08-trendhold --brief` 通过，ERROR 0。

关键月验证文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_025315.csv`
- `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_030653.csv`

结果:
- `risk8_fast05_obnoh1_lock8_30`: 2024-08 -9.56，2024-11 +2.72，2026-02 -145.96，2026-03 -129.85，2026-04 +3.65，2026-05 +1131.63，2025-05 +1608.59。
- `risk8_fast05_obnoh1_lock8_40`: 2024-08 -9.56，2024-11 +3.49，2026-02 -145.96，2026-03 -129.85，2026-04 +6.70，2026-05 +1131.63，2025-05 +1608.59。
- `risk8_fast05_obnoh1`: 2024-08 -9.56，2024-11 -52.61，2026-02 -145.96，2026-03 -129.85，2026-04 -50.56，2026-05 +1131.63，2025-05 +1608.59。
- `risk8_fast05_obnoh1_lock1000_50`: 2024-08 -9.56，2024-11 -52.61，2026-02 -145.96，2026-03 -129.85，2025-05 +1608.59；2026-04/2026-05 本轮报告失败，候选已无需补跑。

结论:
- 证伪。该组合救了 2024-11/2026-04，但 2026-02/2026-03 仍亏且 2505 跌破 3000。
- `OBNoH1` 过滤本身就会截断 2505 趋势利润，不能作为当前目标候选。
- 新参数保持默认关闭，可作为后续订单级工具，但不应纳入当前最佳策略。

### 当前状态
- 当前最佳仍是 `risk8_fast02_swp_h1_05`。
- 达标项: 2025-05 +10216.13，2026-05 +1017.08。
- 未达标项: 24个月仍有 4 个亏损月。
- 下一步应优先找“新增正期望结构入口/补偿单”，而不是继续过滤现有入口或锁月内利润；过滤和锁盈都容易损伤 2505 趋势利润。

## 追加验证 - 2026-06-14 05:xx

### 当前策略 24 独立月复跑并对比 BD07

候选: `risk8_fast02_h105_aligned_nocont_03`

参数增量:
- `risk_percent=8`
- `max_lot_size=5`
- `sweep_early_bounce_sec=0..2` 过滤
- `sweep_h1_aligned_mult=0.5`
- `aligned_no_cont_spread_risk_max=0.2`
- `aligned_no_cont_mult=0.3`

前置检查:
- `python scripts/check_strategy_consistency.py v11xau-bd08-trendhold --brief` 通过，ERROR 0。
- `python -m pytest tests/test_mt5_common.py -q` 通过，93 passed。

结果文件:
- `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_aligned_nocont_03_vs_bd07_24m_20260614_051538.csv`
- `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_aligned_nocont_03_vs_bd07_24m_20260614_051538.json`
- `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_aligned_nocont_03_vs_bd07_24m_20260614_051538.md`

汇总:
- 当前策略累计: 153889.06；BD07累计: 1235783.75；差值: -1081894.69。
- 当前策略盈利月: 20/24；BD07盈利月: 17/24。
- 当前策略优于 BD07: 8/24。
- 当前策略交易数: 4347；BD07交易数: 15228。
- 2025-05: 当前策略 +19148.27，BD07 +70088.00，达成 >3000。
- 2026-05: 当前策略 +1037.07，BD07 -12.46，达成 >1000。
- 当前策略亏损月: 2024-08 -13.24、2024-11 -57.49、2026-02 -189.42、2026-04 -59.31。
- BD07亏损月: 2024-06 -12.48、2024-11 -7.58、2026-01 -13.00、2026-02 -28.45、2026-03 -0.45、2026-04 -9.29、2026-05 -12.46。

关键结论:
- `aligned_no_cont` 降权保留了 2505/2605 趋势利润，并把累计从上一版 `risk8_fast02_swp_h1_05` 的 139652.37 提升到 153889.06。
- 但该候选仍有 4 个亏损月，未达成 24 独立月全盈利。
- 相比 BD07，该候选提高了月度稳定性和 2605 表现，但显著放弃了 BD07 在 2025-04、2025-10、2025-11、2025-12 的极端复利利润。
- 下一步不能把该候选定为终版；需要继续针对 2026-02 与 2026-04 的实时入场结构找补偿，而不是继续压缩 DTP 或全局过滤 SWP。

### 订单级坏簇筛选与结构补偿验证

特征采集:
- `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_aligned_nocont_03_entry_features_20260614_051901.csv`
- 关键7月: 2024-08、2024-11、2026-02、2026-03、2026-04、2026-05、2025-05。
- 配对质量: 2024-08 49/49、2024-11 69/69、2026-02 124/130、2026-03 119/121、2026-04 41/41、2026-05 45/45、2025-05 347/349。

订单级事实:
- 4个亏损月合计: 283笔，净值 -319.46。
- 亏损月 `<1m` 持仓: 156笔，净值 -408.05；但持仓时长不是入场前可观测特征，不能直接作为过滤条件。
- 亏损月卖单: 166笔，净值 -298.44；买单 117笔，净值 -21.02。方向是可观测特征，但单独方向过滤会损伤趋势月，不能作为月份后视规则。
- 当前 7 月样本中，所有基于 `bounce_sec/confirm_pos/risk_atr/spread_risk/pos_mult/h1/cont` 的单层或简单组合过滤，最多把亏损月从4个压到2-3个，不能同时转正 2026-02 与 2026-04。

结构补偿候选验证:
- 结果文件:
  - `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_052916.csv`
  - `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_060415.csv`
- `risk8_fast02_h105_htfpb_mic`: 完全无效果，关键7月与基线一致。
- `risk8_fast02_h105_htfpb_02`: 2024-08 -8.18、2024-11 -58.64、2026-02 -184.69、2026-04 -58.22、2026-05 +1044.62、2025-05 +6067.54。仍4个亏损月，2505明显被压缩，证伪。
- `risk8_fast02_h105_range_break_mic`: 完全无触发，关键7月与基线一致。
- `risk8_fast02_h105_range_break_wide`: 完全无触发，关键7月与基线一致。

结论:
- 继续堆现有入口过滤不是主路径；坏簇过滤不能把 2026-02/2026-04 同时转正。
- 现有 HTF pullback 与 range breakout 结构补偿没有覆盖剩余亏损月份；其中 HTF pullback 加大后会压缩趋势利润。
- 下一步必须做更细的价格行为结构分析，尤其是 2026-02 的连续秒级 SL 区域，找“入场前可观测的反转失败/延续失败”结构，而不是按月份或简单方向筛选。

### 假说: Sell入场 spread/risk 偏高是坏簇

动机:
- 当前候选亏损月卖单明显偏弱: 亏损月卖单 166笔，净值 -298.44；买单 117笔，净值 -21.02。
- ENTRY_DIAG 离线筛选显示，`direction=sell && spread/risk>=0.16` 是少数能把 2024-08/2024-11/2026-04 推近或推过转正的实时可观测特征。
- 该特征不使用月份、小时或持仓后结果，只使用入场方向、实时spread与已计算risk。

实现:
- 新增默认关闭参数:
  - `InpSellSpreadRiskMin=0.0`
  - `InpSellSpreadRiskMax=0.0`
  - `InpSellSpreadRiskMult=1.0`
- 接入 `FinalizeEntryEngineSignal` 与直接入场路径。
- 同步 `yaml_to_set.py` / `strategies.yaml` / `tests/test_mt5_common.py`。
- 编译: `python scripts/compile_and_deploy.py --v3` 通过，0 errors 0 warnings。
- 测试: `python -m pytest tests/test_mt5_common.py -q` 通过，93 passed。
- 一致性: `python scripts/check_strategy_consistency.py v11xau-bd08-trendhold --brief` 通过，ERROR 0。

关键月验证文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_062623.csv`
- `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_062623.csv`

结果:
- `risk8_fast02_h105_sell_spr16_cut`:
  - 2024-08 +21.05
  - 2024-11 +1.53
  - 2026-02 -169.32
  - 2026-03 +479.20
  - 2026-04 +0.54
  - 2026-05 +1066.30
  - 2025-05 +393.92
  - 结论: 首次把 3/4 个剩余亏损月转正，但 2505 跌破3000，不能采用。
- `risk8_fast02_h105_sell_spr16_03`:
  - 2024-08 -2.99
  - 2024-11 -43.68
  - 2026-02 -177.43
  - 2026-04 -38.58
  - 2026-05 +1060.45
  - 2025-05 +13750.38
  - 结论: 保住 2505/2605，但亏损月仍4个，不能采用。

当前收敛判断:
- `sell_spread_risk` 是有效特征，但硬过滤过宽，会砍掉 2505 的卖方趋势利润。
- 下一步应缩窄该特征，例如叠加 `signal/confirm_pos/risk_atr/pos_mult/h1/cont/bounce_sec`，目标是保留 2505 卖方大趋势，同时继续转正 2024-08/2024-11/2026-04。
- 2026-02 仍是独立硬缺口；即使硬过滤也只有 -169.32，需要额外结构入口或专门的实时反转失败识别。

### SellSpreadRisk 阈值收窄验证

离线筛选提示 `sell && spread/risk >= 0.20/0.24` 可能少砍 2505 趋势利润，因此仅改临时变体参数复测。

结果文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_064814.csv`
- `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_064814.csv`

结果:
- `risk8_fast02_h105_sell_spr20_cut`:
  - 2024-08 +22.40
  - 2024-11 -1.67
  - 2026-02 -180.51
  - 2026-04 -3.62
  - 2026-05 +1069.80
  - 2025-05 +1538.36
  - 结论: 亏损月改善明显，但 2505 未达标。
- `risk8_fast02_h105_sell_spr24_cut`:
  - 2024-08 -15.51
  - 2024-11 -13.61
  - 2026-02 -182.66
  - 2026-04 -50.95
  - 2026-05 +1081.72
  - 2025-05 +3007.87
  - 结论: 2505 勉强达标，但亏损月仍4个。

结论:
- 单一 `SellSpreadRisk` 阈值已经证伪为终版路径。
- 该特征可保留为工具，但不能单独实现 24/24。
- 下一步需要针对 2026-02 的价格行为结构做独立入口/反转失败识别；仅靠压缩卖单风险无法转正。

### SellSpreadRisk 月内盈利解锁验证

动机:
- `sell_spr16_cut` 可把 2024-08、2024-11、2026-04 转正，但过早砍掉 2505 卖方趋势利润。
- 假说: 只在月内尚未确认盈利前启用卖单 spread/risk 防守；月内盈利达到阈值后放开趋势单，可保留 2505 后段趋势利润。

实现:
- 新增默认关闭参数:
  - `InpSellSpreadRiskUntilProfitPct=0.0`
- 当本月已实现盈利达到 `month_start_balance * pct / 100` 后，`SellSpreadRisk` 过滤自动失效。
- 该条件使用入场时账户余额与月初余额，实时可观测，不使用月份标签。
- 编译: `python scripts/compile_and_deploy.py --v3` 通过，0 errors 0 warnings。
- 测试: `python -m pytest tests/test_mt5_common.py -q` 通过，93 passed。
- 一致性: `python scripts/check_strategy_consistency.py v11xau-bd08-trendhold --brief` 通过，ERROR 0。

结果文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_070750.csv`
- `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_070750.csv`

结果:
- `risk8_fast02_h105_sell_spr16_cut_until1`:
  - 2024-08 +18.04，2024-11 -8.19，2026-02 -169.32，2026-04 -14.40，2026-05 +1030.10，2025-05 +2807.64。
  - 2505 未达标，亏损月仍3个。
- `risk8_fast02_h105_sell_spr16_cut_until2`:
  - 2024-08 +18.04，2024-11 -0.29，2026-02 -169.32，2026-04 -14.40，2026-05 +1030.10，2025-05 +2807.64。
  - 2505 未达标，亏损月仍3个。
- `risk8_fast02_h105_sell_spr16_cut_until5`:
  - 2024-08 +12.53，2024-11 +1.53，2026-02 -169.32，2026-04 -14.40，2026-05 +1030.10，2025-05 +2807.64。
  - 亏损月降到2个，但 2505 未达标。
- `risk8_fast02_h105_sell_spr20_cut_until2`:
  - 2024-08 +20.74，2024-11 -0.79，2026-02 -180.51，2026-04 -16.63，2026-05 +1037.56，2025-05 +3211.95。
  - 2505/2605 达标，但亏损月仍3个。

结论:
- 月内盈利解锁无法成为终版路径。
- 它证明当前问题已经收敛: 2024-08/2024-11/2026-04 可通过实时卖单防守大幅改善，但 2026-02 仍无法靠同类过滤转正。
- 下一步必须单独分析 2026-02 的价格行为结构，寻找新增正期望入口或反转失败/延续失败识别，而不是继续在 `SellSpreadRisk` 上做阈值微调。

### 小 risk/ATR 噪音单验证

动机:
- ENTRY_DIAG 订单级筛选显示，2026-02 的亏损集中在 `risk_atr < 0.65/0.75` 的窄风险单，尤其是 sweep/OB 的小止损交易。
- 该特征使用入场时已知的 `risk_price / ATR`，不是月份标签；符合实时可观测要求。

实现:
- 新增默认关闭参数:
  - `InpSmallRiskATRMax=0.0`
  - `InpSmallRiskATRMult=1.0`
- 在 EntryEngine 与 direct 路径中，若 `risk_price / state.atr_value < InpSmallRiskATRMax`，按 `InpSmallRiskATRMult` 降权；`<=0` 时过滤。
- 同步 `yaml_to_set.py` / `strategies.yaml` / `tests/test_mt5_common.py`。
- 编译: `python scripts/compile_and_deploy.py --v3` 通过，0 errors 0 warnings。
- 测试: `python -m pytest tests/test_mt5_common.py -q` 通过，93 passed。
- 一致性: `python scripts/check_strategy_consistency.py v11xau-bd08-trendhold --brief` 通过，ERROR 0。

结果文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_080614.csv`
- `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_080614.csv`

关键月结果:
- `risk8_fast02_h105_smallrisk065_cut`:
  - 2024-08 -15.67，2024-11 -39.42，2026-02 -92.93，2026-04 -54.14，2026-05 +1164.97，2025-05 -39.64。
  - 结论: 2605改善，但2505趋势利润被彻底砍掉，不能采用。
- `risk8_fast02_h105_smallrisk075_cut`:
  - 2024-08 -24.83，2024-11 +7.73，2026-02 -65.38，2026-04 -19.30，2026-05 -33.24，2025-05 -40.29。
  - 结论: 过滤过强，2605/2505均失效。
- `risk8_fast02_h105_smallrisk075_03`:
  - 2024-08 -14.48，2024-11 -53.27，2026-02 -146.93，2026-04 -17.45，2026-05 +336.33，2025-05 +2372.39。
  - 结论: 降权保留部分交易，但2505/2605均未达标，亏损月仍4个。

反证结论:
- 单独使用小 `risk/ATR` 做防守不是终版路径。它确实减少 2026-02 损失，但同时删除了 2505/2605 的关键趋势入场。
- 小 `risk/ATR` 只能作为交互特征继续观察，不能作为硬过滤或全局降权。
- 下一步要在订单级特征交互中查找更窄条件，或为 2026-02 增加正期望结构入口；单纯过滤会破坏趋势月收益。

### 小 risk/ATR 交互过滤与路径依赖反证

离线订单级筛选:
- `risk_atr < 0.75/0.85 && entry_count < 5` 看似可把 2024-08、2024-11、2026-02 转正，并保留 2505/2605。
- `risk_atr < 0.75/0.85 && ob_age < 160` 也看似可把多数坏月推近转正。

MT5验证结果:
- `risk8_fast02_h105_smallrisk075_ec5_cut`:
  - 2024-11 +3.01，但 2026-02 -65.38，2026-04 -19.30，2026-05 -33.24，2025-05 -40.29。
- `risk8_fast02_h105_smallrisk075_ec5_age160_cut`:
  - 2026-02 -59.19，2026-05 -33.91，2025-05 -17.11。
- `risk8_fast02_h105_smallrisk085_ec5_age160_cut`:
  - 2026-02 -22.51，但 7/7关键月全亏或目标月失败，2505 -24.42，2605 -46.52。
- `risk8_fast02_h105_smallrisk075_age160_cut`:
  - 2026-02 -59.19，2025-05 -17.11，2026-05 -33.91。
- `risk8_fast02_h105_smallrisk085_age160_cut`:
  - 2026-02 -22.51，2025-05 -24.42，2026-05 -46.52。
- 降权而非过滤:
  - `risk8_fast02_h105_smallrisk075_age160_03`: 2026-02 -144.70，2026-04 -17.45，2025-05 +2142.85，2026-05 +336.33。
  - `risk8_fast02_h105_smallrisk085_age160_03`: 2026-02 -128.27，2026-04 -32.91，2025-05 +5562.74，2026-05 +404.27。
  - `risk8_fast02_h105_smallrisk075_age160_05`: 2026-02 -164.80，2026-04 -28.91，2025-05 +4134.21，2026-05 +552.02。

结果文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_083911.csv`
- `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_091144.csv`
- `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_094446.csv`

结论:
- `entry_count` 是路径依赖特征。过滤早期入场后，`entry_count` 不再增长，导致后续本该放行的趋势单继续被拦；离线筛选严重高估。
- `ob_age` 虽非自引用，但小 `risk/ATR` 仍会破坏关键趋势序列。
- 小 `risk/ATR` 只能解释一部分噪音 SL，不能作为策略改进方向。保留默认关闭参数作诊断工具，但不纳入当前候选。

### 动能持仓/出场候选反证

用户目标强调“小周期没有反转且动能没有衰弱时继续持有”。已有出口候选复核:
- `risk8_fast02_h105_dtp_part50`: 2505 +8053.09，2605 +1011.27，但亏损月仍4个，最差 -218.90。
- `risk8_fast02_h105_dtp_part30`: 2505 +8239.52，2605 +1009.02，但亏损月仍4个，最差 -219.07。
- `risk8_fast02_h105_mom`: 2505 +6568.55，2605 +1011.15，但亏损月仍4个，最差 -197.46。
- `risk8_fast02_h105_mom_stage2`: 2505 +5945.75，2605 +1011.15，但亏损月仍4个。

结论:
- 当前剩余亏损不是“大赢单被DTP截断”主导，而是入场后 <1m SL 主导。
- 2026-02: 70笔 <1m 净 -177.03，SL 59笔净 -254.91；DTP/TP本身是正贡献。
- 2026-04: 27笔 <1m 净 -74.96，SL 19笔净 -107.49；DTP仍是正贡献。
- 因此继续放宽DTP或加动能持仓无法解决24/24，全局出口调参会偏离问题根因。下一步需要新增正期望结构入口或入场前反转失败识别，而不是继续做出场宽放。

### risk/ATR组合坏簇过滤反证

动机:
- `risk8_fast02_h105_sell_spr20_cut_until2` 24个月结果满足 2505/2605 目标，但仍有 5 个亏损月。
- 离线订单级筛选显示一个实时可观察坏簇:
  - `risk_atr < 0.85`
  - `spread_risk < 0.20`
  - `OB年龄 >= 20 bars`
  - `touch_count >= 100`
- 另一个好簇是 `risk_atr >= 0.85` 的宽风险趋势单。

实现:
- 新增默认关闭参数:
  - `InpRiskATRBandBadMax`
  - `InpRiskATRBandBadSpreadRiskMax`
  - `InpRiskATRBandBadAgeMinBars`
  - `InpRiskATRBandBadTouchMin`
  - `InpRiskATRBandBadMult`
  - `InpRiskATRBandGoodMin`
  - `InpRiskATRBandGoodTouchMin`
  - `InpRiskATRBandGoodMult`
- 同步 `yaml_to_set.py` / `strategies.yaml` / `tests/test_mt5_common.py`。
- 编译: `python scripts/compile_and_deploy.py --v3` 通过，0 errors 0 warnings。
- 测试: `python -m pytest tests/test_mt5_common.py -q` 通过，93 passed。
- 一致性: `python scripts/check_strategy_consistency.py v11xau-bd08-trendhold --brief` 通过，ERROR 0。

结果文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_115635.csv`
- `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_115635.csv`

关键月结果:
- `risk8_fast02_h105_sell_spr20_until2_badband_cut`:
  - 2024-08 +125.59，2024-11 +2.63，2026-02 -159.70，2026-03 -134.32，2026-04 -11.58，2026-05 +1102.45，2025-05 +2782.21。
  - 修复了 2408/2411，2605 改善，但 2603 被打成亏损，2505 跌破 3000。
- `risk8_fast02_h105_sell_spr20_until2_badband_good2`:
  - 2026-02 -147.72，2026-03 -138.45，2025-05 +2781.87。
  - 高risk/ATR加权没有恢复趋势利润。
- `risk8_fast02_h105_sell_spr20_until2_badband_good2_touch500`:
  - 2024-11 +1.57，2026-02 -145.89，2026-03 -138.45，2025-05 +2781.87。
  - 高touch约束无法解决 2505 退化和 2603 反转。

结论:
- 组合坏簇过滤是路径依赖假阳性。离线筛选看似剔除亏损单，但实时过滤会改变后续OB触达/入场序列，使 2603 和 2505 的趋势捕捉失效。
- `risk/ATR + spread/risk + age + touch_count` 保留为诊断维度，不进入最终候选。

### DTP延续持仓门反证

动机:
- 用户要求关注小周期趋势、K线动能、小周期反转、动能衰弱、强力反弹、动能延续性。
- 旧 `MomentumRegime` 只是放宽DTP回撤倍数，不能表达“DTP触发后如果小周期仍延续则继续持有”。

实现:
- 新增默认关闭参数:
  - `InpDTPHoldOnContinuation`
  - `InpDTPHoldTF1`
  - `InpDTPHoldTF2`
  - `InpDTPHoldLookbackBars`
  - `InpDTPHoldMinNetATR`
  - `InpDTPHoldReverseBodyATR`
  - `InpDTPHoldBreakBufferATR`
- 在 `CheckDTP` 中，DTP回撤达到平仓阈值时先检查 M1/M5:
  - 若同向实体净推进达到阈值或存在强动能；
  - 且没有小结构反转突破；
  - 且没有强反向实体；
  - 且没有动能衰弱；
  - 则跳过本次DTP平仓，继续持有。
- 编译: `python scripts/compile_and_deploy.py --v3` 通过，0 errors 0 warnings。
- 测试: `python -m pytest tests/test_mt5_common.py -q` 通过，93 passed。
- 一致性: `python scripts/check_strategy_consistency.py v11xau-bd08-trendhold --brief` 通过，ERROR 0。

结果文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_130509.csv`
- `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_130509.csv`

关键月结果:
- `risk8_fast02_h105_sell_spr20_until2_dtp_hold`:
  - 2024-08 +20.57，2024-11 -1.31，2026-02 -180.51，2026-03 +224.43，2026-04 -15.77，2026-05 +1027.71，2025-05 +2780.59。
  - 2505 跌破 3000，2602 不改善。
- `risk8_fast02_h105_sell_spr20_until2_dtp_hold_strict`:
  - 2024-08 +20.74，2024-11 -0.79，2026-02 -180.51，2026-03 +232.36，2026-04 -16.63，2026-05 +1037.56，2025-05 +3090.37。
  - 基本等同基线，未修复亏损月。

结论:
- “DTP触发后继续持有”不是当前亏损月瓶颈。2602/2604 的亏损仍由入场后快速SL主导，出场层无法修复。
- 小周期动能延续可以作为利润保留工具，但必须先解决错误入场；否则放大持仓只会损害 2505。

### 入场前小周期动能与M5净推进验证

动机:
- 用户要求深入小周期趋势、K线动能、小周期反转、动能衰弱、强力反弹、动能延续性。
- 前述DTP持仓验证说明出口层不是主瓶颈，必须把动能条件前置到入场层。

已反证的候选:
- `InpEnableEntryMomentumFilter`:
  - `entry_mom_m1`: 2505 +2711.19，2605 +1037.56，2602/2604无改善。
  - `entry_mom_m1_requireweak`: 2505 +117.26，2605 +3.05，趋势月被破坏。
  - `entry_mom_m5`: 与基线等同。
  - 结论: 现有强/弱动能函数太粗，不能作为当前入场过滤。
- sweep confirm 浅确认过滤:
  - 离线显示 `SWP && confirm_pos >= -0.5` 可改善 2411/2604，但MT5中 `BadCluster1Signal=sweep` 未改变交易序列；诊断标签 `SWP` 与运行时 `zone.is_liquidity_sweep` 不是同一表达路径。
  - 不继续把它作为终版路径，避免离线标签过拟合。

有效候选:
- `risk8_fast02_h105_sell_spr20_until2_plain_m5push_c05`
- 参数:
  - 当前最佳基线 `risk8_fast02_h105_sell_spr20_cut_until2`
  - `InpEnableHTFNetPushFilter=true`
  - `InpHTFNetPushTF=5`
  - `InpHTFNetPushBars=3`
  - `InpHTFNetPushMinATR=0.35`
  - `InpHTFNetPushAlignedMult=1.0`
  - `InpHTFNetPushNeutralMult=1.0`
  - `InpHTFNetPushCounterMult=0.5`
- 含义:
  - 入场前观察最近3根M5的净推进。
  - 若出现反向延续动能，不硬过滤，而是降权到0.5，避免把2605/2505趋势回踩单全部删掉。

关键月MT5验证:
- 结果文件:
  - `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_155848.csv`
  - `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_155848.csv`
  - `results/backtest/v11xau-bd08-trendhold_variant_subset_20260614_161927.csv`
  - `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_161927.csv`
- 对比当前最佳基线:
  - 2024-08: +20.74 -> +10.12
  - 2024-11: -0.79 -> -11.93
  - 2026-02: -180.51 -> -150.30
  - 2026-03: +232.36 -> +298.36
  - 2026-04: -16.63 -> +24.32
  - 2026-05: +1037.56 -> +1159.26
  - 2025-05: +3211.95 -> +3127.75
- 结论:
  - M5净推进降权是目前最好的入场前动能改进：保住2505/2605目标、修复2604、改善2602、提升7关键月合计。
  - 但仍未解决2602，且2024-11小幅恶化。

24独立月与BD07对比:
- 结果文件:
  - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr20_until2_plain_m5push_c05_vs_bd07_24m_20260614_164631.csv`
  - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr20_until2_plain_m5push_c05_vs_bd07_24m_20260614_164631.json`
  - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr20_until2_plain_m5push_c05_vs_bd07_24m_20260614_164631.md`
- 汇总:
  - Trendhold累计 +112890.90，BD07 +1235783.75。
  - Trendhold盈利月 20/24，BD07 17/24。
  - Trendhold优于BD07月份 7/24。
  - 2505 +3127.75，2605 +1159.26。
  - 亏损月: 2024-06 -34.44，2024-07 -15.53，2024-11 -11.93，2026-02 -150.30。
- 结论:
  - 当前最佳满足“2505 > 3000、2605 > 1000”，但不满足“2605 > 3000”与“24/24全盈利”。
  - 与BD07相比，它牺牲长趋势月爆发收益，换取更高盈利月占比和2605修复。

延续加权与风险倍率反证:
- 同向M5延续加权:
  - `a13`: 2505 +3158.26，2605 +1145.43，2602 -148.27。
  - `a15`: 2505 +3160.60，2605 +1138.93，2602 -153.05。
  - `a20`: 2505 +3644.92，2605 +1118.98，2602 -152.39。
  - 结论: 同向延续加权改善2505，但不能推高2605；2605瓶颈不是同向单仓位倍数不足。
- 风险倍率:
  - risk10: 2505 +3274.86，2605 +1080.56，2602 -149.67。
  - risk12: 2505 +3591.75，2605 +1072.31，2602 -151.11。
  - 结论: 提高risk没有放大2605，反而略降；2605受结构机会和入场路径限制，不是风险上限锁住。

下一步:
- 若目标坚持2605 > 3000，不能再靠DTP、risk或同向加权；需要新增正期望结构入口，尤其是M5/H1 BOS回踩或小周期强反弹后的延续入场。
- 2602剩余亏损需要找“入场前反向延续 + 未产生同向强反弹”的更细分类，当前M5净推进只能降权，不能完全过滤。

### 2026-06-14: 订单级趋势细节继续迭代

当前最佳:
- `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05`
- 含义:
  - Sell 低 `spread/risk` 过滤从 0.20 放宽到 0.16，避免误删部分低成本趋势单。
  - M5 最近3根净推进如果与入场方向相反，仓位降到 0.5，而不是硬过滤。
- 24独立月结果:
  - 结果文件:
    - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_vs_bd07_24m_20260614_175410.csv`
    - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_vs_bd07_24m_20260614_175410.json`
    - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_vs_bd07_24m_20260614_175410.md`
  - 盈利月: 21/24。
  - 仍亏: 2024-07 -14.85，2024-11 -13.26，2026-02 -136.00。
  - 2505 +3123.45，2605 +1155.20。
  - 满足 2505 > 3000 和 2605 > 1000；不满足 24/24 全盈利。

已验证的局部改善:
- `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_ratr085_spr18_cut`
- 条件:
  - `risk_atr < 0.85`
  - `spread_risk < 0.18`
  - 仓位倍数 0，即过滤。
- 关键月结果:
  - 2026-02: -136.00 -> -27.97
  - 2025-05: +3123.45 -> +5399.42
  - 2026-05: +1155.20 -> +1271.28
  - 但 2024-07 仍 -14.85，2024-11 仍 -6.19。
- 24独立月反证:
  - 结果文件:
    - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_ratr085_spr18_cut_vs_bd07_24m_20260614_185315.csv`
    - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_ratr085_spr18_cut_vs_bd07_24m_20260614_185315.md`
  - 盈利月降到 16/24。
  - 新增亏损: 2024-06、2025-06、2025-12、2026-03、2026-04。
- 结论:
  - 低 `risk_atr` + 低 `spread_risk` 是 2602 的有效坏单特征，但不能全局硬过滤。
  - 它必须叠加小周期趋势/反弹延续条件：若入场后小周期没有反转、动能没有衰弱到强力反弹、且同向延续已经产生，则不能过滤。

已反证的候选:
- 老化高分 OB:
  - 参数: `InpOldHighScoreOBAgeMinBars=100`, `InpOldHighScoreOBScoreMin=5`, `InpOldHighScoreOBMult=0/0.3`
  - 关键月仅轻微改善 2024-11/2026-02，仍亏 3 月，且总收益略低。
  - 结论: `ob_age>=100 && score>=5` 不是主瓶颈。
- 老化高仓位 OB + 深确认低成本 OR 组合:
  - 参数:
    - `InpOldPosMultOBAgeMinBars=120`
    - `InpOldPosMultOBPosMin=0.5`
    - `InpOldPosMultOBMult=0.0`
    - `InpDeepConfirmLowSpreadConfirmMax=-0.7`
    - `InpDeepConfirmLowSpreadRiskMax=0.16`
    - `InpDeepConfirmLowSpreadMult=0.0`
  - 离线 24月订单特征表预测可修复 24/24，但 MT5 关键月验证失败:
    - 2024-06 +37.93 -> -18.45
    - 2024-07 -14.85 -> -24.74
    - 2026-02 -136.00 -> -75.79
    - 2025-05 +3123.45 -> +2991.85
  - 结论: 离线配对不适合表达会改变交易序列的 OR 过滤；必须用 MT5 CLI 作为准绳。

新增代码状态:
- 新增默认关闭输入:
  - `InpOldHighScoreOBAgeMinBars`, `InpOldHighScoreOBScoreMin`, `InpOldHighScoreOBMult`
  - `InpOldPosMultOBAgeMinBars`, `InpOldPosMultOBPosMin`, `InpOldPosMultOBMult`
  - `InpDeepConfirmLowSpreadConfirmMax`, `InpDeepConfirmLowSpreadRiskMax`, `InpDeepConfirmLowSpreadMult`
- 已同步:
  - `mql5/Include/WaiTrade2/Config.mqh`
  - `scripts/yaml_to_set.py`
  - `config/strategies.yaml`
  - `tests/test_mt5_common.py`
- 验证:
  - `python -m pytest tests/test_mt5_common.py -q`: 93 passed
  - `python scripts/check_strategy_consistency.py v11xau-bd08-trendhold --brief`: ERROR 0
  - `python scripts/compile_and_deploy.py --v3`: 0 errors, 0 warnings

下一步假设:
- 不再全局过滤低 `risk_atr/spread_risk`。
- 需要新增“低 risk/ATR 成本结构保护条件”:
  - 小周期没有反转时保留。
  - K线动能没有衰弱到强力反弹时保留。
  - 若 M1/M5 已经产生同向延续，保留并继续拿单。
  - 只有当低 `risk_atr/spread_risk` 同时出现小周期反向延续、同向反弹失败、动能无延续时，才降权或过滤。

### 2026-06-14 继续: 过滤路线收敛反证

新增验证:
- `InpRiskATRBandBadRequireCounterPush`
  - 作用: 只有当低 `risk_atr/spread_risk` 同时出现 M5 配置周期反向净推进时，才触发 RiskATRBandBad。
  - 关键集合结果:
    - `ratr085_spr18_counter_cut`: 2505 +5276.37，2605 +1205.05，但 2024-11 -21.58，2026-02 -109.11，2026-04 -24.67。
    - `ratr085_spr18_counter_m03`: 2505 +3136.84，2605 +1194.32，但 2024-11 -20.48，2026-02 -101.43，2026-04 -15.48。
  - 结论: “低成本结构 + 反向净推进”能保护部分已盈利月，但修复 2602 不够，且恶化 2024-11/2026-04。
- 更窄 `risk_atr` 阈值:
  - `ratr070_spr18_cut`: 2602 -71.24，但新增 2025-06/2025-12/2026-03/2026-04 亏损。
  - `ratr070_spr16_cut`: 2505 退化到 +2600.55，直接不达标。
  - `ratr070_spr18_counter_cut`: 2505 +4709.47，2605 +1199.51，但 2602 仍 -124.27，2025-12/2026-04 转负。
  - 结论: 收窄阈值不是解法。
- `BuyContNoH1Age` 窄过滤:
  - 参数: `InpBuyContNoH1AgeMinBars=100`, `InpBuyContNoH1SpreadRiskMax=0.36`, `InpBuyContNoH1AgeMult=0`
  - 离线目标是修复 2024-07 的 buy continuation 非H1老OB簇。
  - MT5 关键集合反证:
    - 2024-07 -14.85 -> -24.74
    - 2505/2605 不变
  - 结论: 删除该簇会改变交易序列并误删/错过后续唯一大盈利路径，不能采用。

当前路线判断:
- 剩余亏损不是一个“坏单过滤器”能解决。
- 2024-07 的亏损簇看似是 buy continuation 非H1老OB，但 MT5 证明硬删会更差，说明这类订单中包含后续结构利润路径。
- 2024-11/2602 的问题更集中在 sell/SWP 或低 `risk_atr` 的 SL，但全局删单会破坏其他盈利月。

下一步应转向正期望结构入口/持仓:
- 不再把“小周期反向推进”直接作为删除条件。
- 新增可验证入口:
  - M5/M1 出现同向强反弹后，等待延续K确认再入，而不是触碰即入。
  - 对低 `risk_atr/spread_risk` 单，如果入场后 M1/M5 没有结构反转且动能延续，继续持有，不被早期 MFE/DTP 切掉。
  - 对 2024-07 这类连续 buy continuation，重点验证“第一笔或第二笔失败后是否应等待同向延续确认，而非继续即时重入”。

### 2026-06-14 23:xx: 月内锁利与BOS锁局部放行验证

#### 实时月内利润回吐锁

动机:
- 当前最佳 `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05` 仍亏 2024-07、2024-11、2026-02。
- 2024-11 与 2026-02 都是先出现已实现盈利后回吐；该特征来自实时账户余额/峰值，不依赖月份标签。

关键月验证:
- `lock5_10`:
  - 参数: `InpMonthlyProfitLockStartPct=5.0`, `InpMonthlyProfitLockKeepPct=10.0`
  - 2024-07 -14.85
  - 2024-11 +2.05
  - 2026-02 +4.30
  - 2025-05 +3123.45
  - 2026-05 +1155.20
- `lock5_20`:
  - 2024-11 +4.26，2026-02 +10.00，2505/2605不变，但仍无法修复2024-07。
- `lock6_30`:
  - 2024-11/2602转正，但 2505 被锁到 +9.74，证伪。
- `lock10_50`:
  - 2602 +26.76，2505/2605达标，但 2024-11 仍 -13.26。

24独立月验证:
- 候选: `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10`
- 结果文件:
  - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10_vs_bd07_24m_20260614_223507.csv`
  - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10_vs_bd07_24m_20260614_223507.md`
- 汇总:
  - Trendhold累计 +112375.69，BD07 +1235783.75。
  - 盈利月 23/24，BD07 17/24。
  - 优于BD07月份 10/24。
  - 2505 +3123.45，2605 +1155.20。
  - 唯一亏损: 2024-07 -14.85。

结论:
- `lock5_10` 是当前最优稳定性候选，达成 2505>3000、2605>1000，并把 24独立月提升到 23/24。
- 但它不解决2024-07，因为2024-07几乎全程未形成月内盈利峰值，属于入口密度/结构机会不足，不是盈利回吐问题。

#### 2024-07 入口密度缺口与BOS锁反证

观察事实:
- 当前最佳 2024-07 只有 14 笔，净值 -14.85。
- BD07 2024-07 有 84 笔，净值 +15.43。
- 这说明 2024-07 的问题不是单笔DTP没拿住，而是当前 BD08 的 BOS锁/过滤栈漏掉了大量小周期反弹机会。

入口密度恢复验证:
- `no_ds` 关闭双扫确认:
  - 2024-07 -126.18，2505 +22.43，2605 +152.68，证伪。
- `no_bos_lock` 关闭 BOS bounce 方向锁:
  - 2024-07 +89.00，2024-11 +2.05，2602 +4.37，2505 +5465.35，但 2605 只有 +4.00，证伪。
- `bd07_entry` 同时关闭双扫与BOS锁:
  - 2024-07 +2.47，2505 +366739.61，但 2605 -216.88，证伪。
- `no_bos_lock` + 更高锁利阈值:
  - `lock10_50_no_bos_lock`: 2024-07 +89.00，2505 +5465.35，但 2605 +19.80。
  - `lock20_50_no_bos_lock`: 2024-07 +89.00，2505 +5465.35，但 2605 +21.62，2602 -56.34。

结论:
- 关闭 BOS 锁能修 2024-07，但会破坏 2605；2024-07 与 2605 对 BOS 锁的需求方向冲突。
- 不能采用全局关闭 BOS 锁；必须做更窄的结构入口或局部放行。

#### BOS锁逆向强动能放行

实现:
- 新增默认关闭参数:
  - `InpBOSLockAllowCounterMomentum`
  - `InpBOSLockCounterMomentumTF`
  - `InpBOSLockCounterMomentumBars`
  - `InpBOSLockCounterMomentumMinATR`
- BOS方向锁下，逆H4 bounce 只有在小周期最近N根同向实体净推进达到阈值时才放行。
- 该逻辑试图表达用户要求的“强力反弹且动能产生延续性”。
- 同步:
  - `mql5/Include/WaiTrade2/Config.mqh`
  - `mql5/Experts/WaiTrade3/WaiTrade_OB_SMC.mq5`
  - `scripts/yaml_to_set.py`
  - `config/strategies.yaml`
  - `tests/test_mt5_common.py`
- 验证:
  - `python -m pytest tests/test_mt5_common.py -q`: 93 passed
  - `python scripts/check_strategy_consistency.py v11xau-bd08-trendhold --brief`: ERROR 0
  - `python scripts/compile_and_deploy.py --v3`: 0 errors, 0 warnings

关键月结果:
- `bos_counter_m35`: 2024-07 -14.85，2505 +2.26，2605 +1038.40。
- `bos_counter_m45`: 2024-07 -14.85，2505 +5625.48，2605 +1078.56。
- `bos_counter_m60`: 2024-07 -14.85，2505 +4703.12，2605 +1078.56。

结论:
- 小周期净实体推进放行没有覆盖2024-07缺失交易，证伪为 24/24 解法。
- 但 m45/m60 能提高2505，说明该参数可作为趋势月利润增强工具；当前不纳入最终候选，因为它不解决唯一亏损月。

### 当前最优与未完成项

- 当前最优候选: `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10`
- 已达成:
  - 2505 +3123.45 > 3000
  - 2605 +1155.20 > 1000
  - 24独立月盈利 23/24
- 未达成:
  - 2024-07 仍 -14.85，未达到 24/24 全盈利。

下一步:
- 2024-07 需要新增更窄的正期望结构入口，而不是继续过滤现有入口。
- 可验证方向:
  - BOS锁仍开启，但对“逆H4、非双扫、已出现M1/M5强反弹后回踩”的结构入口单独建通道。
  - 使用小周期结构突破/回踩，而不是仅用净实体推进；当前净推进阈值没有命中2024-07。
  - 目标是补足约 +15 美元，不改变 2605 的 BOS 锁保护。

### 2026-06-15 00:xx: 逆H4成熟反弹、月亏风控、延续OB过滤反证

#### 订单级差集复核

特征采集:
- 当前最佳 `lock5_10`:
  - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10_entry_features_20260614_232327.csv`
- 关闭BOS方向锁 `lock5_10_no_bos_lock`:
  - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10_no_bos_lock_entry_features_20260614_232800.csv`

观察:
- `no_bos_lock` 相对当前最佳新增 338 笔，离线差集净值 +2637.86，胜率 37.0%。
- 新增交易中 2024-07 为 30 笔 +74.85，2026-05 为 8 笔 +23.26，2026-02 为 35 笔 +6.81。
- 但全局 `no_bos_lock` 的 MT5 路径会破坏 2026-05，实际只剩 +4.00，错过当前最佳中 2026-05 的大趋势单。

结论:
- 离线差集只能说明“被拦截信号中有正期望片段”，不能直接推出真实 MT5 路径。
- 关闭/局部放松 BOS 锁会改变 OB 入场次数、冷却、月内锁利与后续交易序列；所有候选必须以 MT5 CLI 为准。

#### 假说: 逆H4成熟反弹放行

动机:
- 2024-07 `no_bos_lock` 的有效补单多数是逆H4方向的 sell bounce/SWP。
- 离线看 `bounce_sec=12..18` 对 2024-07 贡献 +121.81，且没有触发 2026-05 的早期 no_bos 交易。

实现:
- 新增默认关闭参数:
  - `InpBOSLockAllowCounterBounce`
  - `InpBOSLockCounterBounceSecMin`
  - `InpBOSLockCounterBounceSecMax`
- 在 BOS 方向锁下，逆H4 bounce 只有在 EntryEngine 确认后的反弹耗时处于窗口内才放行。
- 该逻辑保持默认关闭，不进入当前最佳参数。

验证:
- 测试: `python -m pytest tests/test_mt5_common.py -q` -> 93 passed。
- 一致性: `python scripts/check_strategy_consistency.py v11xau-bd08-trendhold --brief` -> ERROR 0。
- 编译: `python scripts/compile_and_deploy.py --v3` -> 0 errors, 0 warnings。

关键月结果:
- 结果文件: `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_234137.csv`
- `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10_bos_bounce12_18`:
  - 2024-07 -14.85，未改善。
  - 2026-05 +1151.93，基本保住。
  - 2025-05 +7272.03，改善。
  - 2024-11 +2.05，不变。
  - 2026-02 -175.85，严重退化。

复查:
- 特征文件: `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10_bos_bounce12_18_entry_features_20260614_234638.csv`
- 2024-07 只有 15 条 ENTRY_DIAG / 14 笔成交，没有实际补单。
- 2026-02 放出大量坏单，说明 `bounce_sec` 窗口在真实路径上不是稳定结构条件。

结论:
- 证伪。成熟反弹秒数不是足够稳的 BOS 锁局部放行条件。

#### 假说: 月内亏损停止补 2024-07

动机:
- 2024-07 只差约 $15 转正，尝试用实时权益风控截断尾部亏损。

关键月结果:
- 结果文件: `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260614_235124.csv`
- `mloss2_t10` 与 `mloss3_t14` 均完全等同当前最佳:
  - 2024-07 -14.85
  - 2026-05 +1155.20
  - 2025-05 +3123.45
  - 2024-11 +2.05
  - 2026-02 +4.30

结论:
- 证伪。2024-07 的亏损没有被这些实时月亏阈值截断；问题不是月内亏损停止参数。

#### 假说: continuation OB 是坏簇

观察:
- 当前最佳特征表中，2024-07 的 `cont=1` 为 5 笔 -15.04，刚好覆盖亏损缺口。
- 但该特征可能参与 2026-05 大趋势路径，因此必须用 MT5 验证。

关键月结果:
- 结果文件: `results/backtest/v11xau-bd08-trendhold_variant_subset_summary_20260615_000315.csv`
- `cont_cut`:
  - 2024-07 -24.74，恶化。
  - 2026-05 -19.67，严重破坏。
  - 2025-05 +2605.47，跌破目标。
- `cont03`:
  - 2024-07 -20.93，恶化。
  - 2026-05 +376.96，跌破目标。
  - 2025-05 +2803.38，跌破目标。

结论:
- 证伪。`cont=1` 虽在离线订单表中像坏簇，但真实 MT5 路径需要它维持趋势捕捉；不能过滤或降权。

### 当前最终状态

- 当前最佳仍是 `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10`。
- 已达成:
  - 2025-05 +3123.45 > 3000。
  - 2026-05 +1155.20 > 1000。
  - 24独立月盈利 23/24。
- 未达成:
  - 2024-07 仍 -14.85，未达到 24/24 全盈利。
- 本轮结论:
  - 不再沿 `bounce_sec`、月亏风控、`continuation_pos_mult` 三条路线继续调参。
  - 2024-07 需要新增正期望结构入口，不能靠过滤/降权现有入口解决。
  - 下一步应实现或验证“小周期结构突破/回踩”类独立入口，而不是继续用单笔静态特征打孔 BOS 方向锁。

## 2026-06-15 01:xx: 小周期反转/动能延续候选反证

目标:
- 聚焦小周期趋势、K线动能、小周期反转、动能衰弱、强力反弹和动能延续性。
- 尝试在不破坏 2505/2605 的前提下修复当前最佳唯一亏损月 2024-07。

当前基线:
- `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10`
- 24独立月 23/24 盈利，唯一亏损 2024-07 -14.85。
- 2505 +3123.45，2605 +1155.20。

新增默认关闭基础设施:
- `InpBOSLockAllowCounterBreak`
- `InpBOSLockCounterBreakTF`
- `InpBOSLockCounterBreakBars`
- `InpBOSLockCounterBreakMinATR`
- `InpBOSLockCounterBreakBufferATR`
- `InpBOSLockCounterBreakOBOnly`
- `InpBOSLockAllowCounterOB`

验证:
- `python -m pytest tests/test_mt5_common.py -q` -> 93 passed。
- `python scripts/check_strategy_consistency.py v11xau-bd08-trendhold --brief` -> ERROR 0。
- `python scripts/compile_and_deploy.py --v3` -> 0 errors, 0 warnings。

### 候选1: 失败后反手

结果文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_20260615_002039.csv`

关键月结果:
- `rev_mfe025_tp1`: 2024-07 -21.47，2605 +1196.73，2505 +4297.55，2411 +2.05，2602 +4.76。
- `rev_mfe050_tp1`: 2024-07 -16.49，2605 +1182.62，2505 +929.50，2411 +2.05，2602 +5.28。
- `rev_fail025_tp1`: 2024-07 -21.47，2605 +1196.73，2505 +4279.41，2411 +2.05，2602 +4.76。

结论:
- 失败后反手太晚，不能修复 2024-07。
- 0.50 倍破坏 2505，淘汰。

### 候选2: 逆H4小周期结构突破放行

结果文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_20260615_004425.csv`

关键月结果:
- `counter_break_m5_030`: 2024-07 -14.85，2605 +1155.20，2505 +3123.45，2411 +2.05，2602 +4.30。
- `counter_break_m5_045`: 同基线。
- `counter_break_m1_030`: 同基线。

结论:
- 没有新增交易。2024-07 被拦 sell 并非在入场瞬间完成 swing 突破。
- 结构突破可作为后续入口原语，但当前 H4 锁打孔通道无效。

### 候选3: 逆H4普通OB放行

观察:
- `no_bos_lock` 离线特征中，2024-07 逆向 sell OB 净 +55.73，sell SWP 净 +43.37。
- 2026-05 逆向额外 sell 主要是 SWP，表面上看“只放普通OB”可能避免破坏 2605。

结果文件:
- `results/backtest/v11xau-bd08-trendhold_variant_subset_20260615_010052.csv`

关键月结果:
- `counter_ob`: 2024-07 -14.85，2605 +1128.76，2505 +2971.58，2411 +2.05，2602 -174.96。

结论:
- 2024-07 未修复。
- 2602 被污染，2505 跌破 3000，淘汰。
- “普通OB”不是足够稳的实时结构质量条件。

### 路径依赖关键发现

`no_bos_lock` 离线额外交易在 2024-07 净正，但完整 MT5 路径破坏 2605:
- 当前最佳 2605 的核心利润来自 2026-05-07 buy SWP，最终 +1090.36。
- `no_bos_lock` 在 2026-05-05 放出多笔逆向 sell SWP 后，路径提前触发 `monthly_profit_lock`，整月只剩 +4.00。

结论:
- 2605 保护核心不是出场层，而是避免月初早期逆向小单改变账户/OB状态路径。
- 不能用静态 no_bos 特征差异作为最终规则，必须做路径等价 MT5 验证。

### 当前收敛状态

保持当前最佳:
- `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10`
- 24月结果仍使用 `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10_vs_bd07_24m_20260614_223507.csv`

下一步可证伪方向:
- 不再放宽 H4 锁，也不继续失败后反手。
- 需要“局部入口密度恢复”但不得改变 2605 月初关键趋势路径:
  - 连续同向失败后的下一次入场，等待 M1/M5 强反弹后的延续K确认，而不是即时重入。
  - 把 2024-07 no_bos 盈利簇抽成“局部下跌序列 + OB反弹确认 + 非Sweep + 未触发账户层早期锁”的独立入口，先记录 ENTRY_DIAG 特征再 MT5 验证。

## 2026-06-15 05:xx: 连续失败压力 + 高仓位重入阻断 + 早期利润锁

目标:
- 深入小周期趋势、K线动能、反转/衰弱/延续细节。
- 解决当前最佳 2024-07 -14.85，同时保持 2025-05 > 3000、2026-05 > 1000，并最终跑 24 个独立月。

新增默认关闭基础设施:
- `InpEnableFailureReentryConfirm`
- `InpFailureReentryConfirmLosses`
- `InpFailureReentryConfirmTF/Bars/MinATR`
- `InpFailureReentryConfirmMaxAgeMin`
- `InpFailureReentryBlockMin`
- `InpFailureReentryBlockOBOnly`
- `InpFailureReentryBlockMinPosMult`
- `InpFailureReentryClearWinR`

订单级发现:
- 2024-07 的主要坏串不是单一静态特征，而是同向失败压力后的高仓位重入:
  - 7/1 连续 buy `mfe_fail/sl`，普通 OB 高仓位重入把小亏扩大。
  - 7/29 盈利后立即重入普通 OB 又亏损。
- 2024-06 的恢复利润主要来自 SWP 低/中仓位强反弹:
  - 一刀切阻断同向重入会错过 6/3、6/5、6/7 的恢复利润。
- 因此规则必须是实时可见的“连续失败压力 + 仓位强度”组合，而不是按月份/时段归因。

关键反证:
- `fail_block_3_60`:
  - 修正前可把 2024-07 拉正，但 2026-04 被打坏；修正非失败出场清空后又救不了 2024-07。
- `fail_reentry_m1/m5`:
  - 可改善部分恢复段，但 2024-07 仍亏，且 2505 被压缩。
- `fail_obonly_2_60_noclear`:
  - 2024-06 +37.93，2505 +3480.94，2605 +1240.02，但 2024-07 -18.31。
- `fail_pos05_2_60_noclear`:
  - 关键五个月全部为正，但 24 月中 2024-08 -1.08。
- `pos04/pos045/pos06/pos07`:
  - 未修复 2024-08；0.7 破坏 2024-07 和 2505。

最终候选:
- `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock3_20_fail_pos05_2_60_noclear`

核心参数:
```text
InpRiskPercent=8.0
InpMaxLotSize=5.0
InpSweepEarlyBounceSecMin=0
InpSweepEarlyBounceSecMax=2
InpSweepEarlyBounceMult=0.0
InpSweepH1AlignedMult=0.5
InpAlignedNoContSpreadRiskMax=0.2
InpAlignedNoContMult=0.3
InpSellSpreadRiskMin=0.16
InpSellSpreadRiskMax=999.0
InpSellSpreadRiskMult=0.0
InpSellSpreadRiskUntilProfitPct=2.0
InpEnableHTFNetPushFilter=true
InpHTFNetPushTF=5
InpHTFNetPushBars=3
InpHTFNetPushMinATR=0.35
InpHTFNetPushAlignedMult=1.0
InpHTFNetPushNeutralMult=1.0
InpHTFNetPushCounterMult=0.5
InpMonthlyProfitLockStartPct=3.0
InpMonthlyProfitLockKeepPct=20.0
InpEnableFailureReentryConfirm=true
InpFailureReentryConfirmLosses=2
InpFailureReentryConfirmMaxAgeMin=180.0
InpFailureReentryBlockMin=60.0
InpFailureReentryBlockMinPosMult=0.5
InpFailureReentryClearWinR=-1.0
```

24 独立月 MT5 Real Ticks 结果:
- 结果文件:
  - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock3_20_fail_pos05_2_60_noclear_vs_bd07_24m_20260615_050649.csv`
  - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock3_20_fail_pos05_2_60_noclear_vs_bd07_24m_20260615_050649.md`
- 24/24 盈利。
- 2505 = +3011.34，达成 > 3000。
- 2605 = +1240.02，达成 > 1000。
- 24 月累计 = +129239.16。
- BD07 同期 = +1235783.75；新候选总收益低于 BD07，但盈利月数 24/24 vs BD07 17/24。

验证:
- `python -m pytest tests/test_mt5_common.py -q` -> 93 passed。
- `python scripts/check_strategy_consistency.py v11xau-bd08-trendhold --brief` -> ERROR 0 / WARN 6。
- `python scripts/compile_and_deploy.py --v3` -> 0 errors / 0 warnings。

结论修正:
- 该候选只达成旧目标：24/24 盈利、2505 > 3000、2605 > 1000。
- 用户当前目标已提高为 24 个独立月全部净利润 >= 300，因此该候选不再算达成。
- 当前候选 24 月中仍有 15 个月低于 300；最佳稳定候选 `lock5_10` 仍有 13 个月低于 300。

### 2026-06-15: >=300 新目标下的订单级缺口审计

目标:
- 2505 > 3000。
- 2605 > 1000。
- 24 个独立月全部 >= 300。

低收益月订单级样本:
- 基线: `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10`。
- ENTRY_DIAG 配对文件:
  - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10_entry_features_20260615_195353.csv`
  - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10_entry_features_20260615_200404.csv`
  - `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10_entry_features_20260615_200757.csv`
- 合计 13 个低收益月、716 笔配对交易。

订单级发现:
- SWP: 582 笔，净 +425.22，均值 +0.73；仍是正期望主入口。
- OB: 134 笔，净 -54.49，均值 -0.41；离线看是负期望，但 MT5 顺序验证不能硬删。
- 持仓 <1 分钟: 304 笔，净 -579.94；1..5 分钟: 329 笔，净 +430.25。
- DTP/TP/Decay 正贡献，SL 与 MFEFail 负贡献；继续放宽 DTP/持仓不是主瓶颈。

>=300 数学缺口:
- 多数低收益月需要额外 +260 到 +315。
- 这等价于每月新增约 20 笔、每笔净 +13 到 +16。
- 当前盈利单平均约 +6 到 +16，很多月份最大单笔也不到 +30；因此“少亏一点/拿久一点”无法补齐。
- 要达成 >=300，必须新增低频大R结构入口，或显著提高风险/账户规模；单腿微调过滤栈没有足够数学空间。

已证伪的新增验证:
- `InpOBPosMult=0.0`: 2024-07 -16.77、2505 +2565.64、2605 -31.35；硬删 OB 破坏关键月。
- `InpOBPosMult=0.5`: 2505 +3186.72，但 2605 只有 +564.93；不达标。
- `InpRiskATRBandGoodMin=0.45/0.65` 放大: 2505/2605可达标，但低收益月只从几美元推到十几/一百美元，离 300 远。
- BOS 锁局部放行:
  - bounce 12..18/15+：提高 2505，但不修 2024-07/2024-08。
  - counter momentum：2505 退化到 +2.26，淘汰。
  - counter break：无新增交易，等同基线。
- 高 risk + 月目标停止:
  - risk12/risk16 + target86 仍无法补低收益月。
  - no_bos_lock + target86 可修 2024-07 到 +100.56，但 2605 只有 +4.64，淘汰。
- StrongAddOn 动能延续加仓:
  - 对 2024-07/08/10 基本无触发，2505 小幅变化，2605 不变。
  - 低收益月缺的是源持仓/结构机会，不是已有趋势单未加仓。

当前收敛结论:
- 继续过滤、降权、月锁、简单小周期动能放行、趋势加仓都不足以达成“24月全部 >=300”。
- 下一步必须验证独立的大周期结构入口：小周期结构突破/回踩、HTF pullback、range fade 或其他能产生单笔 >10 美元净期望的低频补偿信号。
- 该入口必须只使用实时可观测特征，不能依赖月份标签。

### 2026-06-15 23:xx: 现成结构入口验证

验证目的:
- 不再继续调过滤/锁利，而是验证是否存在现成独立结构入口能补齐低收益月。
- 样本月: 2024-07、2024-08、2026-02、2025-05、2026-05；部分实验另含 2024-10。

StrongAddOn 动能延续加仓:
- `addon_1r_1x2`: 2024-07 -14.85，2024-08 +3.59，2024-10 +42.56，2505 +3123.10，2605 +1155.20。
- `addon_05r_1x3`: 2024-07 -14.85，2024-08 +3.59，2024-10 +42.56，2505 +3193.58，2605 +1155.20。
- `addon_1r_half3`: 2024-07 -14.85，2024-08 +3.59，2024-10 +42.56，2505 +3122.16，2605 +1155.20。
- 结论: 低收益月几乎无强势源持仓可加仓；这不是“已有趋势没加仓”的问题。

HTF Pullback 独立通道:
- `htfpb_m5_05`: 2024-07 +2.75，2024-08 +2.16，2026-02 +64.66，2505 +19925.03，2605 +1323.95。
- `htfpb_m15_08`: 2024-07 -14.17，2024-08 +2.25，2026-02 -165.35，2505 +8516.34，2605 +1405.25。
- `htfpb_m15_05_x2`: 2024-07 -20.06，2024-08 +4.03，2026-02 -166.15，2505 +4024.16；2605 未完整跑完，本轮已无需补跑。
- 结论: M5 HTFPB 能增强 2505/2605 并改善 2602，但不能把低收益月推到 300；M15版本污染 2602。

RangeFade 结构入口:
- `range_h4`: 2024-07 -4.07，2024-08 +3.59，2026-02 +4.30，2505 +3123.45，2605 +1155.20。
- `range_h1_loose`: 2024-07 -14.85，2024-08 +3.59，2026-02 +4.30，2505 +3125.58，2605 +1155.20。
- 结论: RangeFade 基本不触发有效补偿；不能解决 >=300。

当前状态:
- 没有候选满足新目标。
- 最接近的结构增强是 `htfpb_m5_05`，但最低收益月仍只有个位数到几十美元。
- 若坚持单策略、$350口径、Real Ticks Model 4，下一步需要新增真正的“小周期结构突破/回踩独立通道”，并且该通道必须产生每月约 +260~315 的额外净值；现成入口没有达到这个量级。

### 2026-06-16: PDF 经验转化与 MBOS/BOS 证伪

PDF 可编码经验:
- 大周期方向: 多头/空头以高低点结构判断，大周期 BOS 最严格标准是已收 K 收盘突破极限价。
- 中周期区域: 供需/OB 需要“突破结构、急速冲动、流动性陷阱、新鲜未缓解、打折/溢价位置”共同加分。
- 小周期入场: 突破回踩优先；回踩后必须有同向延续，不能把秒级 bounce 当作趋势延续。
- 持仓: 小周期没有反向强结构突破、没有强反弹并产生反向延续前，不急于收紧/退出。

代码改动:
- 新增默认关闭 MBOS 参数: bounce 秒数、最终仓位阈值、H4 对齐、小周期延续确认、结构持仓。
- MBOS 不再标记为 `is_htf_pullback=true`，避免被 HTF pullback 小固定 TP 截断趋势利润。
- MBOS 顺 H4 成交后可标记 `use_structure_sl/skip_mfe_exits`，接入现有结构持仓。
- 新增 `InpBOSStrictCloseBreak`，用于验证“大周期收盘突破”标准。
- 新增 `InpBOSRequireContinuation`，用于验证 BOS 成交前小周期延续过滤。

关键验证:
- `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock5_10_mbos_m1_pdf_hold`
  - 2024-07 -14.81，2024-08 +4.87，2026-02 -77.36，2505 +3488.35，2605 +1161.55。
  - 结论: PDF 版 MBOS/结构持仓保住两个关键月，但未解决低收益月；2602 被一笔 BOS S x5.0 长持 SL 拖累。
- `..._pdf_nobos`
  - 2024-07 +54.03，2024-08 +9.44，2026-02 +7.04，2505 +6457.26，2605 +1.95。
  - 结论: 关 BOS 能去掉 2602 大亏，但 2605 趋势利润几乎消失；BOS 是 2605 主要利润源，不能全关。
- `..._pdf_bos1`
  - 2024-07 -14.81，2024-08 +4.87，2026-02 -72.10，2505 +3488.35，2605 +1112.14。
  - 结论: 降 BOS 权重不能解决坏 BOS。
- `..._pdf_strictbos`
  - 2024-07 -16.69，2024-08 +1.75，2026-02 +1.46，2505 +550.12，2605 +869.75。
  - 结论: 大周期收盘突破标准可以过滤 2602 坏 BOS，但过严，显著丢失 2505/2605 趋势利润。
- `..._pdf_bos_cont`
  - 结果等同 `pdf_hold`。
  - 结论: 近 2 根 M1 同向延续过滤太弱，坏 BOS 成交时也满足。
- `lock3_20_noclear_mbos_pdf`
  - 2024-07 -5.12，2024-08 -1.69，2026-02 -75.01，2026-03 +369.39，2505 +3655.09，2605 +1246.69。
  - 结论: 在 24/24 为正底座上叠加 MBOS 提升关键月，但破坏全月为正；不能作为收敛候选。

订单级解释:
- PDF 经验里的“收盘突破”是有效过滤器，但全局应用会错过以影线扫损/流动性突破启动的趋势月。
- 当前矛盾不是“BOS 要不要”，而是“BOS 要保留趋势月收益，同时在个别假突破回踩中更快失效/降险”。
- 低收益月的核心缺口仍是入场源不足: `lock3_20...noclear` 已 24/24 为正，但 15 个月 <300，最低只有 +2.17；单纯减亏、降权、持仓优化无法补齐 +260~315 的月度缺口。

下一轮假设:
- 不再全局关 BOS 或严格化 BOS 生成。
- BOS 应增加“回踩后反向结构失效退出/仓位上限”，而不是用过严收盘突破替代生成。
- 低收益月需要独立正期望补偿入口，优先方向是“供需翻转/小周期结构突破回踩”而非现有 MBOS 追随；必须能产生单笔 >10 美元净期望，并通过 2024-07、2024-08、2026-02 与 2505/2605 交叉验证。

### 2026-06-16: 供需翻转入口 SDFLIP 证伪

实现:
- 新增默认关闭 `InpEnableSupplyDemandFlip` 通道。
- 严格版: 已存在反向 OB 被强实体已收 K 收盘吞没后，生成旧供需区翻转回踩位。
- 放宽版: 最近 M5 局部高低点被强实体已收 K 收盘突破后，生成旧高/旧低翻转回踩位。
- 成交前仍走 EntryEngine，并要求 H4 对齐与小周期同向延续；成交注释为 `SDFLIP`，便于订单级统计。

样本验证:
- `...noclear_sdflip_m5`: 2024-07 +39.31，2024-08 -1.69，2505 +3011.34，2025-09 +1.75，2026-02 +1.56，2026-04 +0.67，2605 +1240.02。
- `...noclear_sdflip_range_m5`: 2024-08 -1.69，2025-09 +1.75，2026-02 +1.56，2605 +1240.02。
- 对应报告中 `SDFLIP=0`，结果与同代码底座完全一致。

结论:
- 当前“供需翻转回踩 + EntryEngine + H4对齐 + 延续确认”没有转化为真实订单，不能补足低收益月。
- 继续放宽供需翻转条件大概率会退化成已证伪的 FVG/宽松失衡入口。
- 下一步不应盲调 SDFLIP 参数，而应先做候选区生命周期诊断: 生成数量、触碰数量、EntryEngine 拒绝原因、H4/延续过滤拒绝原因。若候选区数量本身不足，则停止该方向；若过滤链拒绝过多，再按订单级期望验证是否值得绕过部分过滤。

补充诊断:
- 加入 `SDFLIP_SUMMARY` 生命周期计数后发现，最初 `SDFLIP=0` 的根因不是没有候选区，而是候选区全部在注册前 `expired`。
- 修正: SDFLIP 使用专用触碰更新 `UpdateSignalZoneTouches`，只按 `InpSDFlipMaxBars` 过期，不再走普通 OB 的 TTL。
- 修正后 2026-02:
  - `detected=76 generated=76 monitors=8889 confirmed=373 executed=5`
  - 回测净值从 +1.56 提升到 +4.50，报告中 SDFLIP 实际成交 5 笔。
  - SDFLIP 订单级: -6.01、-0.05、-0.01、+19.14、-0.50，净约 +12.57；前 3 笔是同一段快速试错，主要正贡献来自一笔 DTP。
- 放大版 `...sdflip_range_m5_wide`:
  - 2026-02 +18.42，但 2605 降到 +913.63，跌破关键目标 >1000。

结论更新:
- SDFLIP 修复后不是 0 信号，而是“小正期望、低量级”的补偿入口。
- 它无法补齐低收益月 +260~315 的绝对缺口；提高权重/放宽 SL 会破坏 2605。
- 保留默认关闭与诊断计数，但不作为当前达标路径。
- 现有结果中最接近“月收益 >=300”的候选是 `risk8_fast02_h105_aligned_nocont_03`: 12/24 个月 >=300，2505/2605 达标，但最低 -189.42；24/24 为正底座只有 9/24 个月 >=300。下一步若继续推进，方向应是把“高收益候选”的负月风险结构化削掉，而不是继续给 24/24 为正底座加小信号。

### 2026-06-16: aligned_nocont_03 负月风险削减验证

候选分布:
- `risk8_fast02_h105_aligned_nocont_03`: 24月合计 +153889.06，12/24 月 >=300，2505 +19148.27，2605 +1037.07。
- 问题月: 2602 -189.42，2604 -59.31，2411 -57.49，2408 -13.24；另有 2407/2406/2410/2501/2412/2603/2508/2506 低于 300。

订单级分解:
- 2602: SWP 81笔净 -140.76，OTHER 41笔净 -33.46，BOS 2笔净 -15.20。亏损主因不是 BOS，而是 SWP/普通入场在震荡里连续 SL。
- 2604: OTHER 11笔净 -31.42，SWP 30笔净 -27.89。
- 2411: OTHER 12笔净 -39.17，SWP 57笔净 -18.32；方向上 sell 亏损明显，buy SWP 反而盈利。
- 2505 对照: SWP 276笔净 +19414.57，是趋势月主要利润来源；因此不能简单砍 SWP。
- 2605 对照: SWP buy 净 +1031.01，SWP sell 净 -30.99；关键月利润也主要来自 SWP。

证伪假设 1: 失败后阻断/降权能削掉负月。
- `...aligned_nocont_03_fail_pos05_2_60_noclear`
  - 2411 -55.42，2505 +6091.14，2602 -150.08，2604 -56.86，2605 +1037.07。
  - 结论: 2602 小幅改善，但负月仍远低于 +300；2505 从 +19148 降到 +6091，趋势收益被明显削弱。

证伪假设 2: M5 小周期净推进过滤可区分震荡噪声。
- `...aligned_nocont_03_m5push_c05`
  - 2411 -71.46，2505 +17391.79，2602 -160.18，2604 -52.35，2605 +1156.31。
  - 结论: 改善 2602/2604/2605，但恶化 2411，仍不能解决负月。
- `...aligned_nocont_03_m5push_cut`
  - 2411 -79.29，2505 +11164.73，2602 -127.72，2604 -69.28，2605 +930.57。
  - 结论: 强切逆推进虽改善 2602，但破坏 2605 关键目标，且 2411/2604 更差。

当前结论:
- 高收益候选的负月不是单一 BOS 坏单，也不是简单小周期逆推进可过滤；主要是 SWP/OTHER 在没有足够趋势延续的环境里多次小亏。
- 但 SWP 同时是 2505/2605 的主要利润来源，简单过滤或失败阻断都会削趋势利润。
- 下一步若坚持单策略，必须引入“趋势状态下提高 SWP 暴露、非趋势状态下切到 24/24 正底座”的实时 regime 组合；单一过滤器目前没有收敛到 24月全部 >=300。

### 2026-06-16: XAUTrendProfile 组合路径证伪

假设:
- 非趋势态使用 24/24 为正防守底座 `lock3_20...noclear`。
- 趋势态通过 `InpXAUTrend*` 覆盖为类似 `aligned_nocont_03` 的高收益暴露。
- 目标是保留 2505/2605 趋势利润，同时让 2602/2604/2411 进入防守状态。

实现验证:
- 新增默认关闭 `InpKeepZonesOnProfileSwitch=false`，用于研究时禁止 XAU trend/range profile 切换清空已有 zone。
- 候选 `risk8_regime_def_noclear_trend_aligned_h1` 开启 XAUTrendProfile，并启用 `InpKeepZonesOnProfileSwitch=true`。

结果:
- 未禁清空版本: 2411 +4.23，2505 +7.61，2602 +3.48，2604 -38.27，2605 -35.85。
- 禁清空版本: 2411 +4.23，2505 +7.61，2602 -10.70，2604 +2.29，2605 +0.77。

结论:
- XAUTrendProfile 可以把负月风险压低，但几乎完全错过 2505/2605 趋势利润，关键月失败。
- 问题不只是 profile 切换清空 zone；即使保留 zone，趋势态参数/触发机制也没有恢复 aligned_nocont 的 SWP 暴露。
- 现成 XAUTrendProfile 不适合作为本目标的组合器。若继续 regime 方向，需要单独实现“只调仓位/过滤强度、不切换整套 profile、不清空候选区”的轻量 regime 乘数，而不是复用 XAUTrendProfile。

### 2026-06-16: 小周期趋势/动能持仓经验吸收与证伪

文档映射:
- 大周期方向: 继续使用 H1/H4 结构/净推进，不按月份标签。
- 中周期区域: OB/Sweep/BOS/供需翻转候选区。
- 小周期入场/出场: M1/M5 的结构突破、强反向实体、实体净推进作为实时特征。
- “小周期没有反转且动能没有衰弱到强力反弹且动能没有产生延续性，考虑一直拿着订单”映射为两类可证伪出口:
  1. DTP 回撤时若 M1/M5 仍顺订单方向延续，则不出场。
  2. DTP 回撤时必须出现反向小结构突破 + 反向实体延续，才确认出场。

实现/验证:
- 修复轻量 regime 乘数: 原实现只改 `pos_mult`，但 `FinalizeEntryEngineSignal` 已提前计算 `lot`，导致乘数无效。修复为 `ApplyLightRegimeToSignal` 重新计算 lot。
- 新增默认关闭 `InpDTPExitRequireReverseContinuation=false`，要求 DTP 出场前有反向结构突破与反向动能延续确认。
- `pytest tests/test_mt5_common.py -q`: 94 passed。
- `python scripts/compile_and_deploy.py --v3`: `WaiTrade_OB_SMC.mq5` 0 errors / 0 warnings。

代表月份结果:
- `aligned_nocont_03_lreg_h1`: 2411 -37.14，2505 +3180.64，2602 -146.75，2604 -89.22，2605 +1150.74。
- `aligned_nocont_03_lreg_h1_cut`: 2411 -50.47，2505 +320.05，2602 -147.43，2604 -60.10，2605 +1237.22。
- `aligned_nocont_03_lreg_h1_all`: 2411 -11.83，2505 +1759.52，2602 -162.31，2604 -71.90，2605 +944.88。
- `aligned_nocont_03_lreg_h4_all`: 2411 +18.91，2505 +1329.24，2602 -110.10，2604 -47.68，2605 +828.20。
- `aligned_nocont_03_dtphold_m1m5`: 2411 -58.75，2505 +16148.40，2602 -189.42，2604 -58.45，2605 +1027.22。
- `aligned_nocont_03_dtphold_m1m5_strict`: 2411 -58.09，2505 +17657.70，2602 -189.42，2604 -59.31，2605 +1037.07。
- `aligned_nocont_03_dtp_revcont_m1m5`: 2411 -87.90，2505 +2752.12，2602 -186.20，2604 -95.93，2605 +1031.03。
- `aligned_nocont_03_dtp_revcont_m5`: 与 M1/M5 版一致。

结论:
- 轻量 regime 能削部分亏损，但代价是压低 2505/2605 趋势暴露；全信号降权不达标。
- 现有 `DTPHoldOnContinuation` 没有改善负月，说明主要问题不是 DTP 在顺势延续中提前截断。
- “等待反向延续确认再 DTP 出场”反而扩大回吐，2505 跌破 +3000，负月更差；当前 SWP 高频结构不适合全局延迟 DTP。
- PDF 经验不能机械翻译成“更晚出场”。对该 EA，更有效的落点应是入场后的失败确认/重入控制: 只有当反向结构突破并形成延续时，才允许同向继续重入；否则避免在未确认趋势里连续打同一方向。

下一轮:
- 不继续全局延迟 DTP。
- 转向订单级特征: 对负样本中的 SWP/OTHER，统计“前一笔主动失败后，同向重入前是否已有 M1/M5 同向延续”；若无延续的同向重入期望为负，则把 `FailureReentryConfirm` 从简单冷却升级为方向级小周期延续确认。
- 保留 `InpDTPExitRequireReverseContinuation` 默认关闭，仅作为研究开关；当前不进入正式策略。

### 2026-06-16: 被动失败重入确认验证

审计发现:
- `FailureReentryConfirm` 原本只记录 EA 主动关闭的 `early_loss/mfe_fail/no_mfe/time` 亏损。
- broker SL/BE 扫掉后，持仓只在 `SyncPositions/ManagePositions` 中消失，不会进入方向失败状态。
- 这会漏掉负月里最常见的连续小亏，导致“失败后同向重入需延续确认”覆盖面不足。

实现:
- 新增默认关闭参数:
  - `InpFailureReentryRecordPassiveLoss=false`
  - `InpFailureReentryPassiveLossMaxPeakR=0.5`
- 当持仓被动消失，且未 BE、未 trail、未 DTP、未分仓、峰值低于阈值时，记录一次同方向失败。
- 默认关闭，避免影响现有策略与 live。
- 同步 `Config.mqh`、`yaml_to_set.py`、`strategies.yaml`、`tests/test_mt5_common.py`。
- `pytest tests/test_mt5_common.py -q`: 94 passed。
- `python scripts/compile_and_deploy.py --v3`: `WaiTrade_OB_SMC.mq5` 0 errors / 0 warnings。

代表月份:
- `aligned_nocont_03_fail_passive_cont`
  - 2411 -57.91，2505 +7676.08，2602 -162.07，2604 -59.30，2605 +1037.07。
- `aligned_nocont_03_fail_passive_block30`
  - 2411 -55.53，2505 +9934.03，2602 -167.41，2604 -58.00，2605 +1029.08。

结论:
- 被动失败记录方向是正确的工程补洞，但不是达标解法。
- 2602 只改善约 $22~27，距离 +300 仍差约 $460。
- 2505 从 +19148 降到 +7.7K/+9.9K，说明失败后同向降频会明显压制趋势月的高频 SWP 复利。
- 下一步不能继续全局失败阻断；必须只作用于订单级负期望簇，例如“方向 + 信号族 + 小周期结构状态”的交集。

### 2026-06-16: 方向 + 信号族订单级交集过滤

订单级拆解:
- 亏损代表月(2411/2602/2604)合计: `sell` 净 -288.03，`buy` 净 -18.19。
- 亏损代表月最差交集:
  - `sell/SWP/<1m/sl`: 35 笔，净 -172.95。
  - `sell/OTHER/<1m/sl`: 15 笔，净 -96.51。
  - `buy/SWP/<1m/sl`: 20 笔，净 -90.81。
- 关键趋势月(2505/2605)的正贡献仍主要来自 SWP:
  - `sell/SWP/1-5m/dtp`: +7440.46。
  - `sell/SWP/>120m/sl`: +5345.30。
  - `buy/SWP/1-5m/dtp`: +4263.15。

验证:
- `aligned_nocont_03_sell_spr16_until2`
  - 2411 -0.29，2505 +2807.64，2602 -169.32，2604 -14.40，2605 +1030.10。
  - 能明显削 2411/2604，但 2505 跌破 +3000，2602仍很差。
- `aligned_nocont_03_sell_spr16_until1`
  - 2411 -8.19，2505 +2807.64，2602 -169.32，2604 -14.40，2605 +1030.10。
  - 提前恢复到 +1% 无法救 2505，说明早期被禁用的 sell 风险带正是趋势启动利润来源。
- `aligned_nocont_03_sell_spr16_03_until4`
  - 2411 -43.68，2505 +19148.27，2602 -177.43，2604 -38.58，2605 +1032.02。
  - 保住趋势月，但削亏不足。
- 新增默认关闭 `InpSellSpreadRiskOBOnly=false`，允许 SellSpreadRisk 仅作用普通 OB，不碰 Sweep。
- `aligned_nocont_03_sell_ob_spr16_until2`
  - 2411 -44.97，2505 +19148.27，2602 -174.78，2604 -40.74，2605 +1037.07。
  - 保住趋势月，但普通 OB-only 过滤不足以解决负月。
- `aligned_nocont_03_swp_high07_half`
  - 2411 -57.49，2505 +19148.27，2602 -186.22，2604 -58.84，2605 +1061.10。
- `aligned_nocont_03_swp_high07_cut`
  - 2411 -56.42，2505 +10222.22，2602 -172.79，2604 -58.50，2605 +1066.45。
  - SWP 高仓位过滤削不动负月，cut 还砍 2505。

结论:
- 负月确实集中在 sell 秒级 SL，但能看到的 sell spread/risk 保护与趋势月早期利润高度重叠。
- “普通 OB-only”太窄，“全部 sell spread/risk”太宽；都无法同时满足 2505>3000、2605>1000、负月转正。
- 下一步应以防守底座 `sell_spr16_until2` 或 24/24 正底座为基础，补一个独立结构趋势入口，而不是继续压 SWP/SELL。

补充验证:
- `aligned_nocont_03_sell_spr16_until2_mbos_pdf`
  - 2411 -22.59，2505 +3438.51，2602 -248.89，2604 -36.98，2605 +950.66。
  - 结论: 防守 + MBOS 可以把 2505 拉回 >3000，但 2605 跌破 >1000，2602更差；MBOS 在防守底座上引入坏结构单，不是当前组合解。

当前最接近但仍不达标:
- 高收益底座 `aligned_nocont_03`: 2505/2605达标，总收益高，但 2411/2602/2604为负。
- 防守候选 `sell_spr16_until2`: 2411/2604接近打平，2605达标，但 2505仅 +2807.64，2602仍 -169.32。
- 24/24为正底座 `lock3_20...noclear`: 关键月达标但多数月份 <300。

下一步方向:
- 2602 的缺口不是 sell 风险带单独造成，需要单独订单级诊断 2602 的 `buy/SWP` 与 `sell/SWP` 秒级 SL 前置特征。
- 优先找入场前可见的“假扫损后无延续”特征，而不是继续叠加出场延迟、全局失败阻断或 MBOS。

## 2026-06-16: tradermaxliu 交易经验吸收

用户提供文档核心:
- 市场结构: 多头=HH/HL，空头=LH/LL，横盘=区间无序；强高低点来自反向K线突破，强点被破后转弱，代表趋势转换。
- 突破标准: 收盘突破极限价最稳，影线突破次之，实体最高/最低收盘突破最激进；大周期优先用严格收盘，小周期入场可用影线/实体。
- 三重周期: 大周期定方向，中周期找供需区，小周期看反应入场。
- 流动性: 双顶/双底、趋势线、历史高低点附近的突破经常是假扫损；假突破后是否反向延续，决定是否值得跟随。
- 打折/溢价: 多头回到 50% 以下是打折区，空头反弹到 50% 以上是溢价区；未缓解区域会吸引价格回补，但不等于反转。
- 供需/OB: 有效区通常伴随突破强弱高低点、急速K线、流动性陷阱；OB能缩小止损，但小周期分形容易假止损。
- 出场: 跟踪强高低点能吃趋势，但容易被假突破扫；目标止盈看首个未缓解区域，但容易错过后续。

映射到当前 EA:
- 大周期方向: 继续用 H1/H4 swing/BOS 与净推进，不用月份标签。
- 中周期区域: 当前已有 OB、SWP、BOS回踩、MicroBOS、SDFLIP；供需翻转已做 SDFLIP 研究入口。
- 小周期动能: 当前已有 `PassDirectionalContinuationFilter`、`DTPHoldOnContinuation`、`DTPExitRequireReverseContinuation`、`StructureMomentumHold`。
- 强弱高低点: 当前 H1/H4 BOS 已能表达“强点被破”，MicroBOS 用 M1/M5 收盘突破表达小周期结构转换。
- 突破标准: `InpBOSStrictCloseBreak` 对应“大周期收盘突破极限价”，MicroBOS 当前也用已收 K 收盘突破。

已证伪/限制:
- 全局把 BOS 改成严格收盘突破能过滤部分坏 BOS，但会显著丢失 2505/2605 趋势利润；不能机械套用“大周期严格突破”。
- 全局延迟 DTP、等待反向延续确认再出场会扩大回吐；`dtp_revcont_m1m5/m5` 已证伪，不适合作为全局出场。
- 供需翻转 SDFLIP 修复后有少量正期望，但成交量级太低；放宽后会破坏 2605，不足以补齐低收益月。
- 继续压 SWP/SELL 风险带会和趋势月早期利润冲突；SWP 是 2505/2605 主利润源，不能直接关闭。

可保留的经验原则:
- “突破标准分层”应做成按信号类型使用: H4/H1 结构生成偏严格，小周期追随允许更快，但出场/失效必须看小周期收盘反破。
- “小周期没有反转且动能没有衰弱就继续持有”不能全局延迟 DTP；应只用于结构单或大 MFE 单，且必须有最大回吐约束。
- “假突破”应作为 SWP 的质量问题处理: 入场后若没有同向结构延续，而是快速反向强实体/反向小 BOS，则记录为该方向失败状态，限制同向重入。
- “打折/溢价”适合做仓位乘数，不适合硬过滤。买单处在冲动腿溢价区、卖单处在打折区时降权；趋势启动阶段不要直接禁止。
- “未缓解区域”只作为目标/吸引位和出场参考，不直接挂单；当前 SDFLIP 结果说明直接把区域翻转成入口信号量级不足。

下一轮可证伪假设:
1. `SWP_NO_CONT_REENTRY`: 对 SWP/OTHER 的快速亏损后同向重入，要求 M1/M5 已收K同向结构突破 + 实体净推进；否则降权或跳过。预测: 削掉 2602/2411 秒级 SL，2505/2605 若趋势延续真实存在则不应明显受损。
2. `SWP_FAKE_BREAK_INVALIDATE`: SWP 入场后若出现反向小周期收盘突破最近 swing，并伴随强反向实体，则立即标记方向失败并阻断短窗口重入。预测: 改善负月连续小亏，而不是扩大 DTP 回吐。
3. `PD_POS_MULT`: 基于最近一段冲动腿计算 50% 打折/溢价；买在溢价或卖在打折时只降仓，不硬禁。预测: 低波动震荡月亏损降低，2505/2605 大趋势利润保留在 80% 以上。
4. `STRUCT_ONLY_DTP_HOLD`: 只对 BOS/MicroBOS/SDFLIP 或 MFE>3R 的单启用小周期延续持仓，普通 SWP 不延迟 DTP。预测: 允许结构单吃满趋势，同时避免高频 SWP 回吐。

执行约束:
- 不再做全局出场放宽或全局 SWP 禁用。
- 每个假设必须先用订单级 ENTRY_DIAG/成交序列验证，不用月份标签。
- 验证集至少包含 2411、2505、2602、2604、2605；通过后再跑 24 独立月。

## 2026-06-16: 同族失败重入确认验证

假设:
- 之前 `FailureReentryConfirm` 按方向累计，会把 SWP/OB/BOS 混在一起；这会在趋势月压制大量正期望 SWP。
- PDF 经验里的“假突破后是否产生延续”更适合按信号族处理: SWP 快速失败后，只限制同族 SWP/OB 重入，不能全局阻断方向。

实现:
- 新增默认空字符串 `InpFailureReentryFamilyFilter`。
- 默认空值保持旧方向级行为；填 `SWP` 或 `SWP,OB` 时，只记录/限制这些信号族。
- 持仓新增 `entry_family`，成交时标记 OB/SWP/BOS/MBOS/SDFLIP/HTFPB/FVG/MTF/REV。
- 被动 broker SL 消失时，若启用 `InpFailureReentryRecordPassiveLoss`，会按该持仓 `entry_family` 记录失败。
- 同步 `Config.mqh`、`yaml_to_set.py`、`strategies.yaml`、`tests/test_mt5_common.py`。

验证:
- `python -m pytest tests/test_mt5_common.py -q`: 94 passed。
- `python scripts/check_strategy_consistency.py v12xau2`: ERROR 0 / WARN 0。
- `python scripts/compile_and_deploy.py --v3`: `WaiTrade_OB_SMC.mq5` 0 errors / 0 warnings。

代表月份:
- `aligned_nocont_03_fail_family_swpob_cont`
  - 2411 -51.51，2505 +4847.61，2602 -175.17，2604 -72.71，2605 +1057.09。
  - 结论: 同族延续确认能保住关键月，但 2505 从 +19148 降到 +4848，负月仍远低于 +300。
- `aligned_nocont_03_fail_family_swp_block30`
  - 2411 -54.40，2505 +16453.33，2602 -162.06，2604 -62.52，2605 +1057.09。
  - 结论: 只阻断 SWP 比延续确认更保留趋势月，但削亏仍不足。
- `aligned_nocont_03_fail_family_swpob_block30`
  - 2411 -57.15，2505 +16453.33，2602 -182.92，2604 -62.31，2605 +1057.09。
  - 结论: 同时限制普通 OB 更差，说明普通 OB 不是剩余缺口主因。

工程注意:
- 不要并行跑两个使用同一个 `temp/mt5_portable_bt` 的 runner；本轮并行时一个进程抢删 `2024.hcs` 导致 FileNotFoundError。后续代表月回测必须串行，或使用独立 portable 目录。

结论:
- 同族失败重入分层是必要基础设施，但不是达标方案。
- 剩余 2602/2604 缺口不是简单“失败后同族重入太快”；还需要直接诊断入场前的 SWP/OTHER 可见特征。
- 下一步回到 2602 订单级数据，优先检查 SWP 快速 SL 的 `confirm_pos / risk_atr / spread_risk / h1_aligned / bounce_seconds / direction` 组合期望。

## 2026-06-16: DTP动能衰弱确认与供需区消耗验证

吸收 tradermaxliu 经验后的两个可证伪方向:
- 出场: “小周期没有反转且动能没有衰弱，就继续持有订单”。
- 入场: “供需区/OB 被反复消耗后质量下降，假突破后必须看是否产生延续”。

实现:
- 新增默认关闭 input `InpDTPExitRequireMomentumWeakness`。
- 开启后，DTP 已触发且回撤达到阈值时，除已有反向结构延续可选条件外，还要求 M1/M5 至少一个周期出现原方向动能衰弱，才允许 DTP 平仓。
- 衰弱判断复用现有 `CheckMomentumWeakness`，不新增算法；同步 `Config.mqh`、`yaml_to_set.py`、`strategies.yaml`、`tests/test_mt5_common.py`。
- 供需区消耗方向先不新增 EA input，直接复用已有 `InpOldPosMultOBAgeMinBars/InpOldPosMultOBPosMin/InpOldPosMultOBMult` 做老化高仓位普通 OB 过滤。

验证:
- `python -m pytest tests/test_mt5_common.py -q`: 94 passed。
- `python scripts/check_strategy_consistency.py v12xau2`: ERROR 0 / WARN 0。
- `python scripts/compile_and_deploy.py --v3`: `WaiTrade_OB_SMC.mq5` 0 errors / 0 warnings。

代表月份结果:
- `aligned_nocont_03_dtp_weak_m1m5`
  - 2411 -58.14，2505 +17848.86，2602 -189.52，2604 -46.51，2605 +1033.51。
  - 结论: 单独要求动能衰弱出场基本不修复亏损月；2505/2605 保留，但缺口不收敛。
- `aligned_nocont_03_dtp_revweak_m1m5`
  - 2411 -87.90，2505 +2752.12，2602 -186.20，2604 -95.93，2605 +1031.03。
  - 结论: “反向延续 + 原方向衰弱”双确认过严，2505 跌破 +3000，且亏损月更差；全局延后 DTP 再次证伪。
- `aligned_nocont_03_sell_spr16_until2_oldob_cut`
  - 2411 +1.17，2505 +2871.19，2602 -166.26，2604 -19.82，2605 +1008.92。
  - 结论: 供需区老化消耗过滤能修复 2411、改善 2604，但 2505 低于 +3000，2602 仍亏；只能作为防守组件，不是达标方案。

离线订单级观察:
- 以 `aligned_nocont_03_entry_features_20260614_051901.csv` 的实时特征做过滤期望筛选，最强组合集中在 `sell spread_risk>=0.16`、`old/touch高`、`sell risk_atr 0.45-0.60`。
- 这些组合能把 2411/2604 拉近或拉到正数，但 2602 仍约 -50~-70，远低于 +300。
- 同时会明显牺牲 2505 的大趋势利润；因此“继续叠过滤”不是满足 24月每月 +300 的主路径。

结论:
- 文档的“持有趋势”原则不能作为全局 DTP 放宽；当前高频 SWP/OB 很容易把延迟出场变成回吐。
- 文档的“供需区反复消耗后质量下降”在普通 OB 上有效，但剩余缺口主要不在普通 OB。
- 要达成 24 个独立月都 >=300，必须新增能在 2602 这类低交易量/弱趋势月份产生正期望的结构入口，而不是继续从主策略里扣亏损单。

下一步:
- 优先开发/验证 `PD_POS_MULT` 或 `STRUCT_ONLY_DTP_HOLD`，但要限制在结构单/BOS/MicroBOS/SDFLIP，不作用普通 SWP。
- 更直接的方向是新增“供需翻转后的回踩确认”或“小周期强弱高低点收盘突破后的回踩入口”，用严格小周期收盘突破 + 回踩供需区，而不是直接追突破。
- 代表验证仍使用 2411、2505、2602、2604、2605；通过后再跑 24 独立月。

## 2026-06-16: MicroBOS/严格BOS吸收交易经验验证

吸收 tradermaxliu 经验后的结构解释:
- 大周期方向判断应该优先使用“收盘价突破极限价”，避免影线假突破。
- 小周期入口可以更敏感，但必须看到突破后回踩与动能延续。
- 强高低点未被反向突破、且小周期动能未衰弱时，不应被普通 `mfe_fail/decay` 过早切掉。

实现/诊断:
- 为 `MicroBOS` 加入生命周期汇总日志 `MICROBOS_SUMMARY`，计数包括 `detected/generated/monitors/confirmed/reject_* /executed`。
- 不改变交易逻辑，只用于判断小周期结构入口是否真实成交、被哪些过滤器拦截。
- 发现之前的 `MBOS_count=0` 不是策略实际无 MBOS；HTML 明细显示 2025-05/2026-05 均有 `MBOS` 成交，旧摘要口径不可靠。

代表结果:
- `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock3_20_fail_pos05_2_60_noclear_mbos_m1_struct_retest`
  - 24月: 总收益 +131294.60，22/24 月盈利，9/24 月 >=300；2025-03 -4.20，2024-08 -1.69。
  - 关键月: 2505 +4518.30，2605 +1230.84。
  - 结论: 关键月达标，但 24月每月 >=300 仍远未达标。
- `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock3_20_noclear_mbos_pdf`
  - 2411 +3.97，2505 +3655.09，2602 -75.01，2604 +748.12，2605 +1246.69。
  - 结论: 小周期结构持有改善 2604/2605，但 2602 亏损来自一笔 `BOS S x5.0` 假突破止损，不是 MBOS 问题。
- `..._mbos_pdf_nobos`
  - 2411 +3.97，2505 +20544.83，2602 +7.04，2604 +27.48，2605 +1.95。
  - 结论: 关闭大 BOS 修复 2602，但杀掉 2604/2605 的主要收益来源，不能用。
- `..._mbos_pdf_bos1`
  - 2411 +3.97，2505 +3655.09，2602 -69.75，2604 +741.72，2605 +1190.45。
  - 结论: 降低 BOS 权重不能修复 2602 假突破，说明问题不是仓位过大，而是突破有效性。
- `..._mbos_pdf_bos_cont`
  - 2411 +3.97，2505 +3655.09，2602 -75.01，2604 +748.12，2605 +1246.69。
  - 结论: 当前 BOS 延续过滤未挡住这笔假突破，执行路径需要进一步检查，或过滤必须放在 BOS 生成/监听阶段。
- `..._mbos_pdf_strictbos`
  - 2411 +3.97，2505 +3660.66，2602 +3.81，2604 +621.72，2605 +972.20。
  - 结论: 严格收盘突破验证了文档观点，能修复 2602 假突破并保住 2604，但 2605 低于 +1000，不能作为最终版。

当前收敛判断:
- 文档的“大周期用最严格突破标准”有效: `InpBOSStrictCloseBreak=true` 明显降低假突破伤害。
- 文档的“小周期结构突破回踩 + 动能延续”有效但补量不足: MBOS 在 2505/2605 有成交且有正贡献，但低收益月交易数仍太少。
- “一直拿着订单”不能全局用于普通 SWP/OB；必须限定在结构单，并且要同时检查小周期反向突破/强反弹/动能衰弱。
- 达标主路径不应继续调 SL/TimeExit/Cooldown，而应新增一个比现有 MBOS 更高频的“供需翻转后回踩确认/强弱高低点收盘突破回踩”入口。

下一步候选:
- BOS 生成阶段加入严格突破分级: H1/H4 用收盘突破极限价；M1/M5 小周期入口可用影线/实体，但必须有回踩和延续。
- 开发独立 `SupplyDemandFlip Retest` 或 `WeakHighLowRetest`，目标是在 2602/2411/低交易量月份提供正期望补量，而不是继续从原有 SWP/OB 过滤亏损。
- 若继续保留大 BOS，建议默认 `InpBOSStrictCloseBreak=true`，但需要配合补量入口把 2605 从 +972 拉回 +1000 以上。

## 2026-06-16: 供需翻转/FVG与BOS结构级持久化复验

继续吸收 tradermaxliu 经验后的可证伪解释:
- 供需翻转只有在“强实体吞没 + 回踩 + 小周期延续”时才可能有效；不能把未缓解区/FVG 当作直接挂单理由。
- 大周期 BOS 使用严格收盘突破可以过滤影线假突破，但结构级别的回踩窗口不能太短；有效突破位可能数天后才回踩。
- 如果小周期没有反转且动能未衰弱，结构单可以继续持有；但普通 FVG/Fade 高频补量会破坏这个原则。

新增研究 runner 候选:
- `...strictbos_mbos_sdflip`: 严格 BOS + MicroBOS + 供需翻转回踩。
- `...strictbos_mbos_fvg_follow`: 严格 BOS + MicroBOS + FVG follow/fade 对照。
- `...strictbos_mbos_boslong`: 严格 BOS + MicroBOS + `InpBOSRetestMaxBars=2160`。
- `...strictbos_mbos_boslong_w35`: 在 `boslong` 上把 `InpBOSRetestWeight` 从 3.0 提到 3.5。

代表月份结果:
- `...strictbos_mbos_sdflip`
  - 2411 +3.97，2505 +4381.02，2602 +3.81，2604 +671.46，2605 +897.21。
  - 诊断: 2605 的 SDFLIP 成交全部为负贡献或小亏，说明当前供需翻转实现更像宽松反转挂单，不符合“吞没后回踩且延续”的要求。
- `...strictbos_mbos_fvg_follow`
  - 2411 -130.40，2505 -100.69，2602 -254.42，2604 -74.04，2605 -101.95。
  - 诊断: FVG 产生大量重复 Fade/Follow 成交，小确认 K 过滤不足；与“未缓解区域只作观察辅助，不直接挂单”的经验一致，暂时证伪。
- `...strictbos_mbos_boslong`
  - 代表月: 2411 +3.97，2505 +3660.27，2602 +3.81，2604 +759.38，2605 +1146.60。
  - 24月: 总收益 +101772.97，16/24 月盈利，8/24 月 >=300，最差 2025-12 -51.25。
  - 低于 +300 月份: 2024-06、2024-07、2024-08、2024-10、2024-11、2024-12、2025-01、2025-03、2025-06、2025-07、2025-08、2025-09、2025-11、2025-12、2026-01、2026-02。
- `...strictbos_mbos_boslong_w35`
  - 代表月结果与 `boslong` 完全一致。
  - 诊断: BOS 权重已被 `max_pos_mult` 或其它仓位 cap 限制，继续调权重不是有效方向。

当前结论:
- `InpBOSStrictCloseBreak=true` + 延长 BOS 回踩窗口是目前最干净的结构性改进: 修复 2602 假突破，同时把 2605 从 +972.20 拉回 +1146.60，2505 保持 +3660.27。
- 关键月门槛当前满足: 2505 > +3000，2605 > +1000。
- 总目标仍未满足: 24 个独立月并非全部盈利，也远未全部 >=300。
- 剩余缺口不是 BOS 权重，而是低成交月份没有足够高质量结构单；需要新入口，但不能用 FVG/SDFLIP 当前这种宽松回补逻辑。

下一步:
- 固化候选方向优先级: `strict close BOS + long retest` 作为当前结构基础。
- 新增入口应更接近“强弱高低点收盘突破后的回踩确认”: 小周期可用 M1/M5，但必须包含突破、回踩、同向延续、反向强 K 失败过滤。
- 对 FVG/未缓解区仅作为辅助特征: 不能单独触发入场，最多作为 MicroBOS/WeakHighLowRetest 的区域加分。

补充组合验证:
- `risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock3_20_fail_pos05_2_60_noclear_mbos_strictbos_boslong`
  - 组合方式: 使用此前 22/24 正月的防守底座 + MicroBOS 结构持有，再叠加 `InpBOSStrictCloseBreak=true` 与 `InpBOSRetestMaxBars=2160`。
  - 代表月: 2411 +3.97，2505 +4617.55，2602 -0.03，2604 +63.95，2605 +1139.64。
  - 24月: 总收益 +128861.01，19/24 月盈利，8/24 月 >=300。
  - 负月: 2024-06 -33.03，2024-08 -1.69，2025-03 -4.20，2025-06 -2.05，2026-02 -0.03。
  - 低于 +300 月份仍有 14 个: 2024-06、2024-07、2024-08、2024-10、2024-11、2024-12、2025-01、2025-03、2025-06、2025-07、2025-08、2025-09、2025-12、2026-01、2026-02、2026-04。

阶段结论:
- 当前最佳折中是 `...fail_pos05_2_60_noclear_mbos_strictbos_boslong`: 比纯 `boslong` 的 16/24 盈利更好，且 2505/2605 达标；但 >=300 月份仍只有 8/24。
- 但它仍没有完成目标；2026-02 仅 -0.03，说明问题已经不是大亏，而是弱月缺少可放大的正期望结构。
- 下一轮应优先开发 `WeakHighLowRetest`: 以 M1/M5 强弱高低点收盘突破为触发，回踩突破位/OB/FVG重合区入场，必须检查同向净实体推进与反向强 K 失败；FVG 只能作为区域加分，不直接成交。

## 2026-06-16: 弱高低点回踩补量与高收益底座组合证伪

假设:
- 弱月主要不是大亏，而是结构单太少；放宽 MicroBOS 成为“小周期强弱高低点收盘突破回踩”可能补足低收益月。
- 另一条路径是用高收益底座保留更多月 >=300，再叠加 strict/long BOS 过滤 2602 假突破。

候选:
- `...mbos_strictbos_boslong_weakhl`
  - 基于当前最佳折中，放宽 MicroBOS: pivot=1、MinNetATR=0.22、ExtensionATR=0.25、取消 H4 对齐、低仓位 0.45、冷却 12。
  - 结果: 2406 -50.93，2408 -1.69，2503 +2.95，2505 +5.19，2506 +1.34，2602 +8.45，2605 +769.39。
  - 结论: 证伪。放宽小周期结构会把趋势月利润打碎，2505/2605 关键月不达标；“小周期敏感”必须仍保留很强的结构质量，不能靠宽松补量。
- `risk8_fast02_h105_aligned_nocont_03_strictbos_boslong`
  - 基于此前 12/24 月 >=300 的高收益底座，叠加 `InpBOSStrictCloseBreak=true` 与 `InpBOSRetestMaxBars=2160`。
  - 结果: 2406 -12.04，2408 -13.24，2503 +300.56，2505 +19551.02，2506 +58.25，2602 -196.60，2605 +940.62。
  - 结论: 证伪。高收益底座的 2602 深亏不是单靠 strict/long BOS 能修复，且 2605 跌破 +1000。

收敛判断:
- 当前不能继续“放宽小周期结构”或“简单叠 strict/long BOS 到高收益底座”。
- 目标剩余缺口需要新逻辑，而不是参数组合: 低收益月需要可独立正期望的结构入口，但它必须比 weakhl 更强，至少包含:
  1. 收盘突破强/弱高低点；
  2. 突破后有最小延伸；
  3. 回踩突破位或 OB/FVG 重合区；
  4. 入场前 M1/M5 同向净实体延续；
  5. 若出现反向强 K 或反向微结构突破，放弃。
- 现有 MicroBOS 已覆盖 1/2/3/4/5 的一部分；真正缺的是“区域质量/重合区”而不是更宽松的触发。

## 2026-06-16 文档经验吸收与结构/出口假设

输入经验要点转译为可交易特征：大周期方向用更严格收盘突破，入场在小周期突破回踩/供需翻转/假突破；供需区/OB/FVG 只作为实时区域质量，不按月份打标签；出场应在小周期真实反转、动能衰弱或反向延续出现后才落袋。

### MicroBOS 区域质量重合实验

新增可选参数：`InpMicroBOSRequireZoneConfluence`、`InpMicroBOSConfluenceAllowOB`、`InpMicroBOSConfluenceAllowFVG`、`InpMicroBOSConfluenceToleranceATR`。默认关闭。逻辑：MicroBOS 突破位必须贴近同向普通 OB 或 FVG，避免弱高低点噪音。

代表月结果：

| 候选 | 2406 | 2408 | 2503 | 2505 | 2506 | 2602 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| boslong_conf(OB+FVG) | -18.94 | +0.21 | -4.12 | +4690.60 | -28.73 | -95.48 | -29.77 | FVG 即使不直接入场也会改写信号池，2605 失败 |
| boslong_obconf | -33.03 | -1.69 | -4.20 | +3768.17 | +65.20 | -0.03 | +1094.97 | 2605保住，但低收益月未改善且2505退化 |
| weakhl_obconf | -33.03 | -1.69 | -4.20 | +963.53 | +66.69 | -0.03 | +1113.66 | 弱高低点本身噪音过大，区域质量不能修复趋势月 |

证伪：直接用 OB/FVG confluence 约束 MicroBOS 不是当前收敛方向；FVG 只适合作诊断，不应启用到当前主候选。

### DTP 小周期趋势持有实验

已有 DTP 持仓逻辑符合经验：DTP 触发后，若 M1/M5 没有反向结构突破、没有强反向K、没有动能衰弱且仍有顺向净推进，则继续持有。直接全局启用会拖死普通趋势单：

| 候选 | 2406 | 2408 | 2503 | 2505 | 2506 | 2602 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| dtphold | -33.03 | -1.69 | -4.20 | +4279.06 | -2.05 | -0.03 | +1106.79 | 影响小，未解决弱月 |
| dtp_revweak | -34.09 | -0.28 | +5.31 | +14.28 | +5.41 | +1.10 | +1411.40 | 2605提升但2505被拖死，拒绝全局启用 |
| dtp_structonly | -33.03 | -1.69 | -4.20 | +4481.09 | +26.35 | -0.03 | +1139.64 | 只对BOS/MBOS严格出场，关键月保住，轻微改善2506，待24月验证 |

新增 `InpDTPStrictExitFamilies`：空字符串保持旧全局行为；非空时严格 DTP 出场只作用于指定信号族。该参数默认空，不影响存量策略。

### `dtp_structonly` 24月验证

CSV: `results/backtest/v11xau-bd08-trendhold_risk8_fast02_h105_sell_spr16_until2_plain_m5push_c05_lock3_20_fail_pos05_2_60_noclear_mbos_strictbos_boslong_dtp_structonly_vs_bd07_24m_20260616_100242.csv`

结果：总利润 +128346.04，正月 19/24，>=300 月 10/24，最差 2024-06 -33.03。关键月 2505 +4481.09、2605 +1139.64 达标，但仍有 5 个负月：2024-06 -33.03、2024-08 -1.69、2025-03 -4.20、2026-02 -0.03，以及部分月份接近零收益。

结论：结构单专属严格 DTP 是小幅改善分支（>=300 月从 8/24 到 10/24），但没有解决“24个独立月全盈利且>=300”的核心约束。下一步不应继续放大 DTP 严格条件；需要寻找新的实时结构入场来源，尤其是低交易数月份的可证伪增量信号，而不是进一步拖延普通单出场。

勘误：上段24月汇总以CSV重新计算后应为：总利润 +128389.73，正月 20/24，>=300 月 8/24，最差 2024-06 -33.03。负月为 2024-06 -33.03、2024-08 -1.69、2025-03 -4.20、2026-02 -0.03。低于300的月份共16个。`dtp_structonly` 相比当前最佳没有提升 >=300 月数，只把 2025-06 从 -2.05 改到 +26.35、2024-07 从 +1.60 改到 +27.70、2026-04 从 +63.95 改到 +233.29。结论更新：该分支只改善少数低收益月幅度，不改善24月目标，不升级为主候选。

### 组合层面 sanity check

把 24/24 正收益 defensive best 与高收益 `aligned_nocont_03` 逐月相加：总利润 +283128.22，正月 20/24，>=300 月 14/24，仍有 10 个 <300 月，且 2026-02 -179.42、2026-04 -55.03 被高收益腿拖负。

结论：不能直接叠加高收益腿。下一轮应做“结构增量入口 + 实时反向结构/动能失效过滤”，重点避免 2602/2604 这种高收益腿反伤，而不是继续扩大仓位或拖延出场。

## 2026-06-16 交易经验文档转译与 EntryStructureConfirm 证伪

文档经验转成实时特征：
- 大周期方向优先使用收盘价突破极限价；小周期可更激进，但必须能区分强/弱高低点。
- 供需区、OB、FVG/未缓解区只作为区域质量，不应直接变成宽松挂单理由。
- 入场可来自突破回踩、供需翻转、假突破，但出场要等小周期真实反转、动能衰弱或反向延续。
- 若小周期没有反转、动能没有衰弱到强反弹、反向动能没有延续，结构单应继续持有。

逐笔诊断高收益底座 `risk8_fast02_h105_aligned_nocont_03` 后发现：
- 好样本中 SWP 多空均能靠少数 DTP/TP 大单覆盖大量小亏；2503+2506 合计 SWP_B +547.26、SWP_S +143.45。
- 反伤样本主要不是 BOS，而是 SWP/OB 小周期簇：2602+2604 中 SWP_S -143.62、SWP_B -45.76、OB_S -46.32。
- 亏损出场集中在 `<1m` SL 与 `mfe`：这更像供需区被反复消耗后的弱反转，不是简单 BOS 过滤问题。

新增默认关闭参数：
- `InpEnableEntryStructureConfirm`
- `InpEntryStructureConfirmFamilies`
- `InpEntryStructureConfirmTF`
- `InpEntryStructureLookbackBars`
- `InpEntryStructurePivotBars`
- `InpEntryStructureBreakBufferATR`
- `InpEntryStructureMinNetATR`
- `InpEntryStructureNetBars`
- `InpEntryStructureReverseBodyATR`

逻辑：指定信号族入场前，要求 M1/M5 收盘突破最近 swing，高低点突破后有最小同向实体净推进，且没有强反向K。

代表样本结果：

| 候选 | 2406 | 2408 | 2503 | 2505 | 2506 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| defensive + entrystruct_swpob | FAIL | -9.04 | +42.36 | -14.86 | -6.35 | -11.60 | -1.68 | -14.93 | 过滤过硬，打死关键趋势月 |
| aligned_nocont_03 + entrystruct_swpob | FAIL | +8.64 | +41.56 | -14.75 | -12.86 | -22.92 | -7.69 | -24.86 | 同样打死高收益腿 |

结论：
- “入场前必须已经小周期结构突破”不适合普通 SWP/OB bounce，因为这类利润常来自突破前的供需反应；硬确认会错过早期趋势利润。
- 文档经验应更多用于两类位置：1）结构单/BOS/MBOS 的出场持有；2）SWP/OB 的失败后再入场确认，而不是所有 SWP/OB 的首入场前置过滤。
- 当前新增参数保留为默认关闭的研究钩子，不升级为主策略。

## 2026-06-16 失败后结构重入确认实验

假设：
- `SWP/OB` 首入场不应硬等结构突破，但连续失败后的同向重入必须更严格。
- 失败后只有小周期同向实体净推进还不够，应增加：收盘突破最近强/弱高低点、无强反向K、无反向结构突破。

新增默认关闭参数：
- `InpFailureReentryRequireStructureBreak`
- `InpFailureReentryStructureLookbackBars`
- `InpFailureReentryStructurePivotBars`
- `InpFailureReentryBreakBufferATR`
- `InpFailureReentryReverseBodyATR`
- `InpFailureReentryBlockStrongReverse`
- `InpFailureReentryBlockReverseBreak`

代表样本结果：

| 候选 | 2406 | 2408 | 2503 | 2505 | 2506 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| defensive + failstruct | +35.57 | -1.69 | -4.20 | +1.57 | +18.01 | +4.30 | +0.67 | +1282.43 | 修复部分小亏，但打死2505 |
| aligned_fail + failstruct | +18.40 | -17.64 | +308.83 | +6382.10 | +220.36 | -152.43 | -56.86 | +1037.07 | 2505/2605达标，但2602/2604仍反伤 |

结论：
- 失败后结构重入确认只改变少量重入，不足以修复高收益腿的 2602/2604 反伤；对防守底座还会压低 2505 趋势月。
- 当前问题仍不是“重入确认不够严格”单点，而是高收益腿首入场信号在供需区反复消耗时本身不具备可过滤的结构优势。
- 不升级为主候选；保留默认关闭参数作为后续组合研究钩子。

## 2026-06-16 交易经验文档吸收后的反弹/动能代理验证

目标更新：2605 月盈利 >1000、2505 月盈利 >3000，24 个独立月均需 >=200。

文档经验进一步转译：
- “强力反弹”不能只看触发时间，应看入场前反弹幅度是否足够。现有实时代理为 `bounce_ob_pct`，对应 `InpBounceSweetMinPct/MaxPct`。
- “动能产生延续性”不能用事后持仓盈亏判断，入场侧先用 M5 净推进；出场侧用 `NoMFE` 验证“几根小周期内没有最小浮盈则小亏退出”。
- “供需区被消耗”优先用普通 OB sell 与 sweep 分开处理；不要砍掉 sweep 的 DTP/长持仓趋势腿。

订单级诊断（`aligned_nocont_03_m5push_c05`）：
- 关键盈利样本 2505+2605：SWP_B +9604.90、SWP_S +9272.25，普通 sell -827.18。趋势利润主要来自 SWP 的 DTP/长持仓，不应直接过滤 sweep。
- 反伤样本 2602+2604：SWP_S -131.36、普通 sell -72.74、SWP_B -40.70。普通 sell 负期望稳定，但过滤后只能小幅改善；SWP 弱反弹仍是主因。

代表月结果：

| 候选 | 2503 | 2505 | 2506 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---|
| `aligned_nocont_03_m5push_c05` | +347.24 | +17391.79 | +171.31 | -160.18 | -52.35 | +1156.31 | 高收益底座，2602/2604 反伤 |
| `m5push_ob_sell_cut_until2` | +347.24 | +17391.79 | +171.40 | -140.02 | -30.48 | +1156.31 | 普通 sell OB 过滤有效但不足 |
| `m5push_ob_sell_cut_all` | +343.44 | +4155.76 | +172.59 | -139.33 | -30.48 | +1239.75 | 保关键月，但仍不能解决 2602/2604 |
| `m5push_swp_high06_cut` | +271.82 | +3990.95 | +118.58 | -154.82 | -55.07 | +1370.55 | 高倍 sweep 不是坏簇专属，硬切证伪 |
| `m5push_swp_high06_half` | +345.82 | +16081.06 | +171.37 | -159.68 | -50.41 | +1184.90 | 半仓几乎不救坏月，证伪 |
| `m5push_nomfe3_015_m25` | +347.24 | +17391.79 | +171.31 | -160.18 | -52.35 | +1156.31 | NoMFE 触发太晚，无效 |
| `m5push_nomfe2_010_m20` | +419.16 | +17412.22 | +194.45 | -165.89 | -52.35 | +1159.10 | 改善部分低月但加重 2602 |
| `m5push_bounce_sweet_020_080` | +429.54 | +5275.59 | +219.11 | -10.58 | -67.25 | +1093.58 | 强反弹代理有效，2602 大幅改善，但 2604 变差 |
| `m5push_bounce_sweet_010_120` | +429.54 | +5227.66 | +219.11 | -10.58 | -67.25 | +1093.58 | 与 0.20-0.80 基本一致 |
| `m5push_bounce_sweet_010_999` | +429.54 | +5227.66 | +219.11 | -10.58 | -67.25 | +1093.58 | 说明主要过滤对象是过浅/无反弹幅度的入场 |

结论：
- 文档中的“强力反弹”可落地为 `bounce_ob_pct` 过滤，且确实把 2602 从 -160 改到 -10，同时保留 2505/2605 达标。
- 该特征仍不能达成 24 月 >=200，因为 2604 变差，且大量低频月本身信号太少。
- `NoMFE` 出场不是根因解法；坏单多是入场后直接 SL，来不及靠持仓后 no-progress 修复。

### 新目标（>=200）下的历史结果筛选

完整 24 月已测候选最高只到 15/24 月 >=200：

| 候选 | 总利润 | 正月 | >=200 月 | 最差 | 2505 | 2605 | 2602 | 2604 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `aligned_nocont_03` | +153889.06 | 20/24 | 15/24 | -189.42 | +19148.27 | +1037.07 | -189.42 | -59.31 |
| `swp_h1_05` | +139652.37 | 20/24 | 15/24 | -206.72 | +10216.13 | +1017.08 | -206.72 | -89.51 |
| `sell_spr20_until2_plain_m5push_c05` | +112890.90 | 20/24 | 13/24 | -150.30 | +3127.75 | +1159.26 | -150.30 | +24.32 |
| `defensive best` | +129239.16 | 24/24 | 10/24 | +2.17 | +3011.34 | +1240.02 | +10.00 | +4.28 |
| `mbos_m1_struct_retest` | +131294.60 | 22/24 | 10/24 | -4.20 | +4518.30 | +1230.84 | +1.56 | +62.99 |

逐月最佳扫描显示若干月份在所有已测候选中仍远低于 +200：
- 2024-06 最高 +44.50
- 2024-07 最高 +40.69
- 2024-08 最高 +20.74
- 2024-11 最高 +18.91
- 2025-01 最高 +162.74
- 2026-02 最高 +18.42

判断：在当前 SWP/OB/BOS/MBOS 体系内，仅靠参数过滤、反弹幅度、M5 推进、NoMFE 出场，不能把 24 个独立月全部抬到 >=200。下一轮必须新增互补信号源，优先考虑低频月份也能产生交易机会的结构类型；继续微调 sweep/OB 只会在关键趋势月和低频月之间搬利润。

## 2026-06-16 文档经验吸收后的 WaiTrade3 真实执行路径验证

文档观点转成可执行假设：
- `HTFPullback`：大/中周期净推进后，回踩供需区再顺势入场，对应“突破回踩”。
- `SupplyDemandFlip`：供需区被大实体吞没后，等待回踩再顺新方向，对应“供需翻转”。
- `MicroBOS + structure hold`：小周期强/弱高低点突破后，若未出现小周期反转、强反弹或动能衰弱，则继续持仓。
- `DTP strict exit`：DTP 回撤不立即出场，要求反向结构突破+反向延续，并要求原方向动能衰弱。

重要实现边界：
- 当前 `temp/_run_trendhold_24m.py` 跑的是 `WaiTrade3\\WaiTrade_OB_SMC.ex5`。
- `RangeBreakout / LiquiditySweep / RangeFade` 参数虽可写入 `.set`，但在这条研究路径下结果等同 `m5push_c05` 基线；它们不能作为 WaiTrade3 本轮有效增量判断。
- WaiTrade3 include `WaiTrade2/PositionManager.mqh`，所以 `InpDTPHoldOnContinuation / InpDTPExitRequireReverseContinuation / InpDTPExitRequireMomentumWeakness / InpDTPStrictExitFamilies` 对持仓管理有效。

代表切片结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2501 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `m5push_c05` | +18.88 | +16.04 | -3.07 | -71.46 | +100.65 | +17391.79 | -160.18 | -52.35 | +1156.31 | 真实基线，2505/2605达标但低频月不足 |
| `doc_htfpb_m15_dtp` | +60.85 | +37.34 | +37.50 | -72.41 | +159.60 | +7452.07 | -156.09 | -58.44 | +1359.70 | 突破回踩有效但补频不足 |
| `doc_sdflip_m5` | -2.02 | -7.46 | +67.01 | -84.76 | +88.93 | +22178.33 | -186.15 | -46.04 | +1092.20 | 供需翻转仅改善2408，不解决主问题 |
| `dtp_revweak_m1m5` | +144.02 | +139.98 | +89.13 | -87.90 | +12.53 | +2752.12 | -186.20 | -95.93 | +1031.03 | 持有到反转/动能衰弱能补2406/2407，但2505低于3000 |
| `mbos_struct_dtp_hold` | -4.32 | +40.68 | +18.58 | -87.85 | +38.44 | +19177.02 | -262.28 | +305.07 | +971.64 | 结构单严格DTP修复2604，但伤2602/2605 |
| `bounce + mbos_struct_dtp` | - | - | - | - | - | +3652.87 | -281.58 | +415.15 | +1002.27 | 关键月达标但2602恶化，不能进全量 |
| `mbos_pdf` | +5.92 | -5.63 | +10.15 | -22.59 | +55.49 | +3438.51 | -248.89 | -36.98 | +950.66 | 结构SL持有不是独立解 |

结论：
- 文档中的“继续拿单直到小周期反转/动能衰弱”是有效方向，但不能全局套在普通 scalping 出场上；全局严格 DTP 会把 2505 从 +17391 压到 +2752。
- 结构单严格 DTP 能把 2604 从 -52 提到 +305，但 2602 恶化到 -262，说明 MBOS 结构级别本身仍会在部分低频行情中产生反向假突破。
- `bounce_sweet` 与结构 DTP 的收益不可简单叠加：组合后 2604 提升、2505/2605过线，但 2602 恶化到 -281。
- 下一步不能继续加参数组合；需要在 WaiTrade3 内做“按 entry_family 的结构出场状态机”：普通 SWP/OB 保持原 scalping DTP，BOS/MBOS/SDFLIP 仅在 H4/H1 同向且 M1/M5 未反向突破时延迟出场；若出现强反弹K或反向结构延续，则立即释放 DTP/结构SL。该逻辑必须默认关闭，并记录每笔交易的 family、是否结构持有、反向突破、动能衰弱触发。

## 2026-06-16 第二轮：强弱高低点/完整反转退出验证

文档进一步提炼：
- 大周期方向应使用“收盘突破强高低点极限价”，不能用最近几根净K的短期推进替代。
- 小周期退出应区分“单根强反向K/刺破”与“完整反转”：收盘突破小结构、原方向动能衰弱、反向动能延续三者同时出现，才说明趋势利润不该继续拿。
- 供需区/OB利润保护要防止“假延续后强反弹回吐”，但保护不能早到截断 2604 这种结构趋势。

新增默认关闭参数：
- `InpDTPStrictRequireHTFAligned / InpDTPStrictHTF*`：严格DTP仅在HTF净推进同向时启用。
- `InpStructureSLRequireHTFAligned / InpStructureSLHTF*`：结构SL仅在HTF净推进同向时启用。
- `InpStructMomRequireFullReverseExit / InpStructMomFullReverseMinR`：结构持仓需完整小周期反转才放弃。
- `InpStructProfitLockTriggerR / InpStructProfitLockR / InpStructProfitTrailTriggerR / InpStructProfitTrailLockMult`：结构单专属利润保护。

关键切片结果：

| 候选 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---|
| `doc_mbos_dtp_htfonly` | +21217.29 | -196.98 | -45.02 | +1021.12 | HTF净推进门控保住2505/2605，但不能修2604 |
| `doc_bounce_mbos_dtp_htfonly` | +7318.80 | -199.13 | -85.16 | +1100.24 | bounce叠加后仍不能修2604 |
| `doc_mbos_structsl_htfonly_no_strictdtp` | +5772.56 | -234.56 | -73.22 | -1.76 | HTF结构SL门控误杀关键持仓 |
| `doc_mbos_struct_dtp_structsl_htfonly` | +5485.33 | -234.56 | -43.71 | -1.76 | 严格DTP不能救该误杀 |
| `doc_mbos_struct_fullrev` | +17621.36 | -273.47 | +416.27 | -112.05 | 完整反转退出修复2604，但2602/2605回吐恶化 |
| `doc_mbos_struct_dtp_fullrev` | +16730.65 | -273.47 | +416.27 | -112.05 | DTP不是瓶颈，结构持仓过宽才是瓶颈 |
| `doc_mbos_struct_fullrev_m05` | +17893.24 | -261.15 | +416.27 | -108.30 | 0.5R门槛仍挡不住回吐 |
| `doc_mbos_struct_fullrev_m10` | +17886.24 | -272.86 | +416.27 | -108.30 | 1.0R门槛仍挡不住回吐 |
| `doc_mbos_struct_lock` | +7199.73 | +51.72 | -35.32 | +25.03 | 结构利润锁救2602/2605，但截断2604 |
| `doc_mbos_struct_dtp_lock` | +6843.61 | +51.72 | -35.32 | +25.03 | 严格DTP无增量 |
| `doc_mbos_struct_lock_loose` | +5094.74 | -56.22 | +298.46 | -2.68 | 宽松保护保2604，但2602/2605回落 |
| `doc_mbos_struct_lock_mid` | +4560.68 | -52.33 | -30.85 | +10.55 | 折中仍不稳定 |

判伪结论：
- `HTF净推进同向`不是结构持仓的好门控。文档要求的是大周期“强高低点收盘突破”方向，而不是最近3根H1净实体推进；后者会过滤掉价格回踩结构位前后的关键单。
- `完整小周期反转退出`不能全局套到结构单。它确实吃到2604趋势，但在2605会把假延续和强反弹都当作可持有利润，造成回吐。
- `结构利润锁`能显著修复 2602/2605，但和“吃满趋势”冲突；锁太紧截断2604，锁太松又失去保护。

下一轮只保留两个可证伪方向：
1. 用“大周期强高低点收盘突破”替代 `HTF净推进` 作为结构持仓门控。候选规则：H1/H4 最近强高/强低被收盘突破后，结构单才允许完整反转退出；否则使用普通结构SL/利润锁。
2. 结构利润锁应由“小周期是否产生反向延续”控制，而非固定R。候选规则：达到1R后先不锁，只有出现强反弹K但未完整反转时锁0.4R；若完整反转则释放DTP/结构SL退出。

## 2026-06-16 第三轮：强高低点突破门控与强反弹利润锁

新增默认关闭参数：
- `InpStructureSLRequireStrongBreak`：结构SL/结构持仓需要 H1/H4 近期出现同方向强高低点收盘突破。
- `InpStructureSLStrongBreakTF1/TF2/Lookback/MaxAge/Pivot/BufferATR`：强突破检测周期、有效期和 swing 强度。
- `InpStructProfitLockRequireReverseSignal`：结构利润锁只有在 M1/M5 出现强反向K或小结构反向突破后才触发。

实现口径：
- 强高低点突破使用收盘价突破 swing 高/低加 ATR 缓冲，符合文档“大周期用第三种标准”的方向。
- 利润锁触发使用实时可见的强反向K或小结构反向突破，不使用月份标签。
- 所有参数默认关闭，不改变既有策略行为。

关键切片：

| 候选 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---|
| `doc_mbos_struct_strbreak` | +20021.08 | -262.28 | +305.07 | +971.64 | 与原结构持仓基本一致，强突破窗口过宽 |
| `doc_mbos_struct_fullrev_strbreak` | +17621.36 | -273.47 | +416.27 | -112.05 | 强突破门控挡不住2605回吐 |
| `doc_mbos_struct_fullrev_strbreak_h1a24` | +13357.27 | -273.47 | +416.27 | -112.05 | H1 24bar有效期仍挡不住，且压低2505 |
| `doc_mbos_struct_fullrev_strbreak_h1a48` | +17621.36 | -273.47 | +416.27 | -112.05 | 与宽窗口一致 |
| `doc_mbos_struct_lock_revsig` | +10662.84 | +62.28 | -35.32 | +25.03 | 反向信号触发锁保护2602/2605，但仍截断2604 |
| `doc_mbos_struct_fullrev_lock_revsig` | +7652.69 | +31.21 | -35.32 | +25.03 | 完整反转不改变利润锁截断 |
| `doc_mbos_struct_lock_loose_revsig` | +7444.66 | -62.92 | +298.46 | -2.68 | 宽松锁恢复2604，但2602/2605回弱 |
| `doc_mbos_struct_fullrev_lock_loose_revsig` | +5309.27 | -54.53 | +298.46 | -2.68 | 同样无法兼顾 |

判伪结论：
- 大周期强高低点突破能识别结构背景，但不能单独决定“是否继续拿单”。2605 的问题不是没有结构背景，而是假延续后回吐；强突破门控无法区分。
- 强反弹触发利润锁比固定R更合理，但本质 trade-off 仍存在：锁紧保护 2602/2605，锁松保 2604。出口侧继续调参难以同时满足。
- 下一步应回到入场侧，而不是继续调结构出口：用文档的“供需区筛选标准”提升结构单质量，只允许满足 `突破强高低点 + 急速K线 + 流动性陷阱/未缓解` 的结构单进入长持仓；其他结构单只走普通 DTP/利润锁。

## 2026-06-16 第四轮：结构长持仓质量门控、动态释放、SWP 延续确认

新增默认关闭参数：
- `InpStructureHoldRequireQuality / InpStructureHoldQuality*`：只有小周期顺向净推进、无强反向K、无微结构反破的订单才允许结构长持仓。
- `InpStructureHoldDynamicRelease / InpStructureHoldRelease*`：结构持仓出现小周期反转且原方向动能衰弱时，不直接平仓，而是恢复普通 DTP/Trail 管理。
- `InpEnableSWPContinuationConfirm / InpSWPContinuation*`：SWP 入场后若没有小周期同向延续，可硬过滤或按 `InpSWPContinuationFailMult` 降权。

关键切片：

| 候选 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---|
| `m5push_c05` | +17391.79 | -160.18 | -52.35 | +1156.31 | 当前有效基线，2505/2605达标 |
| `doc_mbos_struct_quality` | +2727.94 | -157.70 | +365.47 | +962.73 | 长持仓质量门控修2604，但2505/2605跌破目标 |
| `doc_mbos_struct_dtp_quality` | +2589.04 | -157.70 | +365.47 | +962.73 | 严格DTP无增量 |
| `doc_mbos_struct_quality_m5b1` | +2481.26 | -176.79 | +365.47 | +971.55 | 放宽门控仍达不到目标 |
| `doc_mbos_struct_release` | +3846.39 | -10.55 | -68.05 | +18.16 | 动态释放修2602，但过早交回2605趋势单 |
| `doc_mbos_struct_release_revcont` | +2912.12 | -11.71 | -68.05 | +18.16 | 要求反向延续仍截断2605 |
| `m5push_swp_cont_m5` | +676.49 | -82.27 | -47.16 | +954.41 | SWP硬延续过滤过严，杀2505 |
| `m5push_swp_cont_m1` | +196.65 | -80.42 | -47.41 | +1302.87 | M1硬过滤保2605但杀2505 |
| `m5push_swp_cont_m5_half` | +15291.14 | -138.21 | -52.52 | +1056.67 | SWP降权温和有效但不够 |
| `m5push_swp_cont_m1_half` | +12722.89 | -130.28 | -52.06 | +1115.64 | 2602小幅改善，2605更稳 |
| `h1push_c05` | +15996.08 | -171.22 | -53.55 | +1028.11 | H1净推进不如M5 |
| `h1push_c03` | +16845.78 | -197.16 | -52.50 | +981.20 | H1强降权证伪 |

订单级拆解（以 `m5push_swp_cont_m1_half` 为例）：
- 2602 净亏 -130.28，主要拖累是 `SWP Sell SL` -99.74、`OB Sell SL` -79.82；`MFEFail` 合计很小。
- 2604 净亏 -52.06，主要拖累是 `SWP Buy SL` -42.05、`OB Sell SL` -31.01。
- 2605 净利 +1131.14，虽然也有 SWP/OB SL，但少量顺势利润覆盖亏损。

判伪结论：
- “小周期无反转且动能延续就继续拿”只适合结构持仓子集；直接控制结构授权或动态释放，会在 2604 和 2605 之间搬利润。
- SWP 的“扫损后同向延续确认”作为硬过滤会错杀 2505 的假突破反转利润；作为降权可温和改善 2602，但不足以把低频月抬到 +200。
- 2602/2604 的瓶颈不是出口，而是 SWP/OB 入场方向在局部假突破中反复错；MFEFail/Decay 调整不是主路径。
- 下一步必须新增互补低风险信号源或独立防守子策略，用于低频月补利润；继续压现有 SWP/OB 会损伤 2505/2605 趋势收益。

## 2026-06-16 第五轮：强高低点扫损反转 + 打折/溢价

文档经验转成的新假设：
- 强高低点：用近期 pivot high/low 作为强高/强低。
- 假突破：已收盘 K 线刺破强高/强低，随后收回结构位内，且影线比例达标。
- 打折/溢价：做多必须位于 HTF 区间 50% 下方，做空必须位于 50% 上方。
- 小周期动能确认：入场前要求 M1/M5 同向净实体推进，避免只因刺破就反手。

新增默认关闭参数：
- `InpEnableStrongSweepReversal / InpStrongSweep*`：独立 `REVSWP` 入场族，走现有 EntryEngine、手数、DTP、失败重入框架。
- 修正点：强扫损 DP 过滤显式使用最新已收盘 HTF K 线计算区间位置，避免旧 `CalcHTFPositionRatio` 在数组方向下取到远端 close。

关键切片：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2501 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `m5push_c05` | +18.88 | +16.04 | -3.07 | -71.46 | +100.65 | +17391.79 | -160.18 | -52.35 | +1156.31 | 基线 |
| `doc_strongsweep_rev` | +18.88 | +4.55 | -8.08 | -68.75 | +162.20 | +17522.78 | -165.87 | -52.31 | +1009.38 | H1 DP + M5 sweep 太克制，只改善2501 |
| `doc_strongsweep_rev_probe` | +21.94 | -11.62 | +76.47 | -51.33 | +74.83 | +17505.34 | -201.90 | -123.19 | +978.22 | 放宽门控后交易数暴增但2602/2604恶化 |
| `doc_strongsweep_rev_m1m15` | +80.36 | +13.54 | +30.64 | -67.55 | +117.94 | +22317.79 | -209.84 | -140.15 | +1133.84 | M1/M15能补趋势利润，但低频防守失败 |

判伪结论：
- 文档的“假突破反向”是可用信号，但它不是低频月稳定补利润来源；放宽后在 2602/2604 变成反向接刀。
- M1/M15 组合符合“周期差距不宜过大”，能把 2406、2505、2605 抬高，说明小周期强扫损有趋势增益；但 2411/2602/2604 仍亏，无法达成 24 月 >=200。
- 继续在 REVSWP 上调宽/调窄只是在 2505/2605 与 2602/2604 之间搬利润。下一轮应转向“未缓解区域/目标止盈”的低风险套利信号，或将 `REVSWP` 只作为趋势增益组件而非低频月防守组件。

## 2026-06-16 第六轮：FVG 50% 回补 MIT 复验

文档经验转译：
- 未缓解区域/FVG 不能直接挂单，必须等待至少 50% 回补后再观察小周期反应。
- 小周期未反转且确认 K 仍同向，才允许顺 FVG 方向延续；反向 fade 单独验证。
- 因 MT5 Tester 报 `too many input parameters (1033)`，不能再新增 EA input。实现改为复用现有 `InpFVGFadeMaxEntryOffsetR` 的研究哨兵：`-1=MIT Follow`，`-2=MIT Fade`；默认正值不改变旧策略。

验证：
- `python -m pytest tests\test_mt5_common.py -q`：99 passed。
- `python scripts\check_strategy_consistency.py v11xau-qs3 --brief`：0 ERROR。
- `python scripts\mt5_compile_win.py --mt5-home temp\mt5_portable_bt --mt5-data temp\mt5_portable_bt --log-dir temp\compile_win_bt`：WaiTrade2/WaiTrade3 0 errors 0 warnings。

关键双月：

| 候选 | 2505 | 2505 Trades | 2605 | 2605 Trades | 结论 |
|---|---:|---:|---:|---:|---|
| `m5push_c05` | +17391.79 | - | +1156.31 | - | 当前有效基线 |
| `doc_fvg_mit_follow` | +104.70 | 99 | -42.09 | 49 | 目标月不达标，且 2605 转亏 |
| `doc_fvg_mit_fade` | -238.45 | 307 | -94.01 | 272 | 交易数过多，明显接刀 |

判伪结论：
- 直接把 FVG/未缓解区变成 50% 回补入场，仍然违背“未缓解区域只作观察辅助”的经验；即使加同向确认 K，也没有足够趋势利润，反而破坏 2505/2605。
- FVG 更适合作为区域质量/目标位/止盈参考，不应作为独立补偿入口；如果使用，只能叠加到 MicroBOS/强弱高低点回踩的质量评分中。
- 出口侧现有代码已经有 `DTPHoldOnContinuation`、严格 DTP、结构动态释放；释放后同 tick 会进入普通 DTP/Trail 管理。继续宽放结构持仓会在 2602/2605 回吐，继续锁利润会截断 2505/2604。

下一轮方向：
- 不再新增 FVG 直接入口；回到入场质量。优先做 `WeakHighLowRetest`：强高低点被收盘突破后变弱，价格回踩突破位/OB/FVG 重合区，只有出现小周期同向净实体推进、无强反向 K、无反向结构延续才入场。
- FVG/未缓解区只作为该入口的加分或目标止盈，不单独成交。

## 2026-06-16 第七轮：弱高低点回踩 OB 重合复验

文档经验转译：
- 小周期强/弱高低点突破不能直接追，必须等回踩；供需区/OB 用作区域质量。
- 未缓解区/FVG 不再作为直接入口，只允许后续作为目标位或质量加分。
- 若小周期没有反转、动能未衰弱且没有反向延续，可以继续持有；但前几轮已证伪该逻辑不能全局套普通单，因此本轮只验证入场质量，不再扩大结构长持仓。

候选实现：
- `doc_mbos_obconf_nohold`：基于现有 M1 MicroBOS，要求突破位贴近同向 OB，关闭结构长持仓。
- `doc_mbos_obconf_m1_small`：基于 `m5push_c05`，新增小仓位 M1 MicroBOS，严格 OB 重合、H4 对齐、同向延续。
- `doc_mbos_obconf_m5_small`：基于 `m5push_c05`，新增小仓位 M5 MicroBOS，严格 OB 重合、同向延续，不要求 H4 对齐。

验证：
- `python scripts\check_strategy_consistency.py v11xau-qs3 --brief`：0 ERROR。
- `python -m py_compile temp\_run_trendhold_24m.py`：通过。

关键切片结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2501 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `m5push_c05` | +18.88 | +16.04 | -3.07 | -71.46 | +100.65 | +17391.79 | -160.18 | -52.35 | +1156.31 | 基线 |
| `doc_mbos_obconf_nohold` | +18.04 | +3.66 | -13.24 | -65.45 | +41.38 | +19126.76 | -189.42 | -59.31 | +1037.07 | 关键月过线，但低频月更差 |
| `doc_mbos_obconf_m1_small` | +18.88 | +16.04 | -3.07 | -78.95 | +100.65 | +15983.45 | -160.18 | -52.35 | +1156.31 | 几乎无有效增量，2411变差 |
| `doc_mbos_obconf_m5_small` | +18.88 | +16.04 | -3.07 | -71.46 | +100.65 | +17391.79 | -160.18 | -52.35 | +1156.31 | 等同基线，M5 OB重合触发不足 |

判伪结论：
- “小周期强弱高低点收盘突破 + 回踩 + OB 重合 + 同向延续”作为参数化 MicroBOS 补量，不能抬高低频月；触发太少时等同基线，触发稍多时反而压低 2411/2602/2604。
- 文档里的 OB/供需区质量不是简单“突破位靠近 OB”可以表达；现有普通 OB 与 MicroBOS 的空间重合没有足够预测力。
- 当前瓶颈继续指向新信号源，而不是 MicroBOS 参数微调：需要能在低频月份产生独立正期望、且不吞掉 2505/2605 的小周期结构类型。

下一步：
- 不再继续在 `MicroBOSRequireZoneConfluence`、FVG MIT、结构长持仓上调参。
- 候选方向改为“失败簇后的反向供需翻转”：当同一方向 SWP/OB 连续短时 SL 后，只有出现反向收盘突破最近小结构 + 回踩被吞没供需区 + 同向净实体延续，才允许低仓位反向补偿；这更贴近文档的“供需翻转”和“假突破后反向运行”，也直接针对 2602/2604 的 SWP/OB 连续错向簇。

## 2026-06-16 第八轮：失败簇门控 SDFLIP 复验

实现：
- 不新增 input。复用 `InpSDFlipPosMult < 0` 作为研究哨兵：负值表示实际仓位取绝对值，但 SDFLIP 注册前必须检测到相反方向连续失败簇。
- 新增 `IsFailureClusterReadyForReverse(direction)`：要求 `FailureReentry` 已记录相反方向连续失败，未超时，并且当前方向具备小周期结构突破/实体净推进确认。
- 正数 `InpSDFlipPosMult` 行为不变，默认策略不受影响。

验证：
- `python -m pytest tests\test_mt5_common.py -q`：100 passed。
- `python scripts\check_strategy_consistency.py v11xau-qs3 --brief`：0 ERROR。
- `python scripts\mt5_compile_win.py --mt5-home temp\mt5_portable_bt --mt5-data temp\mt5_portable_bt --log-dir temp\compile_win_bt`：WaiTrade2/WaiTrade3 0 errors 0 warnings。

关键切片结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2501 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `m5push_c05` | +18.88 | +16.04 | -3.07 | -71.46 | +100.65 | +17391.79 | -160.18 | -52.35 | +1156.31 | 基线 |
| `doc_sdflip_failcluster` | +10.41 | -14.57 | -4.71 | -75.05 | +134.36 | +8821.94 | -159.20 | -58.55 | +1036.15 | 失败簇门控没有补弱月，且压低2505 |
| `doc_sdflip_failcluster_swp_half` | -8.11 | -17.91 | -15.09 | -82.18 | +49.59 | +7066.18 | -144.61 | -51.71 | +1047.23 | 2602小幅改善但整体退化 |

判伪结论：
- “失败簇后反向供需翻转”在当前 SDFLIP 实现下仍不能产生足够正期望。它能偶尔降低 2602 的亏损，但同时损伤 2406/2407/2408/2411/2505。
- 失败簇本身是风险状态，不是可直接反向交易的边际；反向补偿仍需要更强的独立价格行为信号，不能只依赖“前面错了两次”。
- 目前已证伪的入口侧方向包括：FVG 50% MIT、MicroBOS OB/FVG 重合、宽松弱高低点回踩、SDFLIP 直接/失败簇门控、强扫损反转宽放。

下一步：
- 转向“目标止盈/未缓解区域作为出场目标”而不是新入口：当前 2505/2605 趋势利润靠少数大单，弱月缺口来自没有足够大单；直接加低频入口很难补到 +200。需要验证把首个未缓解区/HTF swing 作为结构单分批目标，是否能把弱月中已有正确方向单的平均收益放大，而不削弱 2505/2605。

## 2026-06-16 第九轮：宽止损大周期区间/OB 复验

用户新增观察：
- 2605 的 4580 附近 OB 多次生效，近半个月无法向上突破，每次触达后转头向下；这类结构不能按短期 OB 过期处理。
- 2602 的 2026-02-02 下跌触及 2026-01-25 到 2026-02-01 形成的 4270-4545 大价格区间/大周期 OB 后，立刻反弹并拉出大下影。
- 若 M1 入场噪音过多，可提升执行周期到 M5/M15，或使用更宽 SL 抓大周期利润。

实现：
- `temp/_run_trendhold_24m.py` 回测配置修正：`Period=` 由 `.set` 中 `InpBarTF` 自动推导，避免 M5/M15 候选仍用 M1 Tester 周期。
- 复用 `InpRangeMaxWidthATR < 0` 作为研究哨兵，不新增 input：
  - `abs(value) < 20`：宽历史区间只在边界辅助，不在区间中部/突破态拦截主策略。
  - `abs(value) >= 20`：宽历史区间独立补偿腿，只在区间边界交易，中部/突破态跳过。
- `RangeDetector` 在负值哨兵下使用最近 HTF 历史高低点构造宽供需区，用于验证 4270-4545 这类宽区间边界。

验证：
- `python -m pytest tests\test_mt5_common.py -q`：100 passed。
- `python scripts\check_strategy_consistency.py v11xau-qs3 --brief`：0 ERROR。
- `python scripts\mt5_compile_win.py --mt5-home temp\mt5_portable_bt --mt5-data temp\mt5_portable_bt --log-dir temp\compile_win_bt`：WaiTrade2/WaiTrade3 0 errors 0 warnings。

关键切片结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2501 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `m5push_c05` | +18.88 | +16.04 | -3.07 | -71.46 | +100.65 | +17391.79 | -160.18 | -52.35 | +1156.31 | 基线 |
| `doc_htfpb_h1_wide_dtp` | +41.81 | +77.38 | -2.20 | -74.76 | +135.24 | +15838.81 | -161.38 | -54.63 | +1093.96 | 近期推进回踩不能捕捉2602大区间 |
| `doc_htfpb_h4_wide_dtp` | +21.50 | +21.22 | -2.20 | -74.76 | +102.11 | +15825.27 | -161.38 | -54.22 | +1093.96 | 同上 |
| `doc_range_h4_wide_m5` | +41.20 | +70.71 | +4.61 | -50.84 | +116.03 | +212.99 | -76.61 | -40.75 | -128.26 | 全局升M5破坏主趋势利润 |
| `doc_range_h4_extreme_m1` 覆盖型 | -12.79 | +16.39 | +0.20 | -48.66 | +47.26 | +5046.91 | -117.26 | -54.41 | +1230.06 | 保住关键月但2602仍不足 |
| `doc_range_h4_extreme_only_x2` 独立型 | -18.98 | -14.20 | -15.84 | -20.87 | -32.53 | +23.76 | +39.16 | -11.43 | +45.63 | H4宽区间补偿量级不足 |
| `doc_range_d1_extreme_only_x2` 独立型 | +20.60 | +37.90 | +184.92 | +37.66 | -12.17 | +263.14 | +347.13 | -13.09 | +6.23 | 验证D1宽区间对2602有效，但不是主趋势策略 |

判伪与保留结论：
- 用户关于 2602 的观察被验证：D1 宽历史区间边界能把 2602 从基线 -160.18 改到 +347.13，说明 4270-4545 这类大区间/大周期 OB 是有效实时结构特征。
- 用户关于 2605/4580 的方向也合理，但当前 RangeFade 独立腿在 2605 只有 +6.23，不能替代主趋势策略；4580 更像“持久化供给位 + 多次触达做空”的结构层级，不是普通震荡区间。
- 简单把 RangeFade 混入主 OB/SWP 会拦截或反转大量趋势单，2505 从 +17391.79 被压到 +5046.91 或更低；全局升 M5/M15 也会破坏主策略节奏。
- 宽止损/大周期边界适合做独立低频补偿腿，不能直接覆盖主策略入口方向。若继续推进，需要把“大周期 OB/供需区持久化 + 多次触达 + 边界反应确认”做成独立信号族，并与 `m5push_c05` 组合统计，而不是单策略互相污染。

下一步：
- 做组合口径验证：主腿 `m5push_c05` 或当前 v12xau2 与 D1 宽区间独立腿的逐月净值相加，先确认 24月目标是否数学上接近。
- 若组合仍不达标，再新增真正的 `HTF_OB_RETEST` 信号族：历史 H4/D1 强区间持久化、多次触达计数、M5/M15 下影/上影反应确认、宽 SL、目标到中轴/对侧，不改写普通 OB/SWP。

### 2026-06-17 补充：直接 HTRG 与 24月组合验证

新增实现：
- 在 WaiTrade2/WaiTrade3 EA 中加入研究型 `HTRG` 直接入口：`InpRangeMaxWidthATR <= -40` 才启用，使用 D1/H4 宽区间边界 + M5/M15 已收 K 的拒绝形态/同向实体确认。
- 直接入口不再绑定普通 OB/SWP，`ob_index=-1`，注释为 `HTRG TOP/BOT`，SMC 中映射到 `ENTRY_FAMILY_MTF`。
- 旧 `-24` D1-only 候选不触发直接 HTRG，避免污染上一轮已验证的 RangeFade 独立腿。

验证命令：
- `python -m py_compile temp\_run_trendhold_24m.py`
- `python -m pytest tests\test_mt5_common.py -q`：100 passed。
- `python scripts\check_strategy_consistency.py v11xau-qs3 --brief`：0 ERROR。
- `python scripts\mt5_compile_win.py --mt5-home temp\mt5_portable_bt --mt5-data temp\mt5_portable_bt --log-dir temp\compile_win_bt`：WaiTrade2/WaiTrade3 0 errors 0 warnings。
- 注意：`temp\mt5_portable_bt` 不能并行跑两个 MT5 runner；并行会互相清理 Tester 日志/覆盖 `.set`，结果不可信。

直接 HTRG 证伪：

| 候选 | 2505 | 2602 | 2605 | 结论 |
|---|---:|---:|---:|---|
| `doc_range_d1_extreme_only_x2` 旧 D1-only | +263.14 | +347.13 | +6.23 | 保留，能验证2602大区间反弹 |
| `doc_range_d1_htrg_strict` | +27.66 | -56.39 | +5.27 | 证伪，直接触边入场污染2602 |

关键原因：
- `HTRG` 捕捉到大量滚动 D1 区间边界交易，而不是只捕捉 2026-02-02 那类“大周期 OB 首次/少次触达 + 强拒绝”。
- 2602 中 `HTRG` 在 2月中后段反复 TOP/BOT 高抛低吸，交易从 24 笔变为 36 笔，净值从 +347.13 退化到 -52.14（较早 4小时冷却版本）；即使一天冷却 strict 仍为 -56.39。
- 因此“宽区间触边 + 小周期反应K”不是足够独立的正期望入口；有效信息在 D1 宽区间边界本身，直接追边界会过度交易。

24月完整验证：

| 月份 | 主腿 `m5push_c05` | D1-only | 组合 |
|---|---:|---:|---:|
| 2024-06 | +18.88 | +20.60 | +39.48 |
| 2024-07 | +16.04 | +37.90 | +53.94 |
| 2024-08 | -3.07 | +184.92 | +181.85 |
| 2024-09 | +530.70 | +117.02 | +647.72 |
| 2024-10 | +31.76 | -57.75 | -25.99 |
| 2024-11 | -71.46 | +37.66 | -33.80 |
| 2024-12 | +58.58 | -0.07 | +58.51 |
| 2025-01 | +100.65 | -12.17 | +88.48 |
| 2025-02 | +474.19 | +125.09 | +599.28 |
| 2025-03 | +347.24 | +184.66 | +531.90 |
| 2025-04 | +8852.63 | +160.48 | +9013.11 |
| 2025-05 | +17391.79 | +263.14 | +17654.93 |
| 2025-06 | +171.31 | +103.75 | +275.06 |
| 2025-07 | +349.86 | -22.87 | +326.99 |
| 2025-08 | +204.70 | -10.87 | +193.83 |
| 2025-09 | +830.33 | +31.51 | +861.84 |
| 2025-10 | +92199.42 | +755.12 | +92954.54 |
| 2025-11 | +3936.77 | +46.05 | +3982.82 |
| 2025-12 | +674.27 | +79.30 | +753.57 |
| 2026-01 | +330.52 | -36.89 | +293.63 |
| 2026-02 | -160.18 | +347.13 | +186.95 |
| 2026-03 | +104.46 | -62.72 | +41.74 |
| 2026-04 | -52.35 | -13.09 | -65.44 |
| 2026-05 | +1156.31 | +6.23 | +1162.54 |

组合结论：
- 2505 与 2605 目标满足：2505 = +17654.93，2605 = +1162.54。
- 24月每月 >=200 未满足，低于 200 的月份仍有：2024-06、2024-07、2024-08、2024-10、2024-11、2024-12、2025-01、2025-08、2026-02、2026-03、2026-04。
- 2024-08、2025-08、2026-02 已接近 200；核心缺口集中在低交易量或双腿都低迷的月份，继续加“触边直接入场”会污染有效月份。

下一步收敛方向：
- 不继续推进直接 HTRG；保留代码为研究哨兵，但不进入候选主线。
- 若要补 24月每月 >=200，优先做组合层资金分配/独立腿选择，而不是把所有逻辑塞进单 EA：主趋势腿覆盖 2505/2605，大周期 D1-only 覆盖 2602，另需针对低波动低交易月份寻找第三类小正期望补偿腿。
- 对 2605 的 4580，应转为“持久化结构位/供给位”问题：记录历史 H4/D1 结构破位价，不随普通 OB 过期；价格回测该价位且 M5/M15 没有向上延续时，只允许顺 H4 下跌方向持仓/加仓，而不是滚动区间高抛低吸。

### 2026-06-17 再补充：HTRG 一次性/延续确认与 D1 确认信号增强

用户补充的 2602 结构观察：
- 2026-02-02 下跌触及 2026-01-25 到 2026-02-01 形成的 4270-4545 大周期 OB/价格区间后，立刻反弹并形成大下影。
- 这个观察不能硬编码日期或价格，只能抽象成“D1 宽历史区间边界 + 小周期拒绝/延续 + 已有确认信号”。

本轮新增验证：
- `doc_range_d1_htrg_struct_once`：`InpRangeMaxWidthATR=-60`，同一 D1 区间同方向只允许一次直接 `HTRG`，并要求先离开边界再回触。
- `doc_range_d1_htrg_continue`：`InpRangeMaxWidthATR=-80`，在触边拒绝后等待 M15/M5 小周期延续确认，避免第一根 K 线接刀。
- `doc_range_d1_confirm_boost`：不启用直接 `HTRG`，只增强原 RangeFade 路径中的已有 SWP/OB/RG 确认信号；本质是“结构区只给确认信号加权，不创造第一触边订单”。

代表性月结果：

| 候选 | 2024-11 | 2025-05 | 2026-02 | 2026-05 | 结论 |
|---|---:|---:|---:|---:|---|
| `doc_range_d1_extreme_only_x2` | +37.66 | +263.14 | +347.13 | +6.23 | 旧 D1-only，保留 |
| `doc_range_d1_htrg_struct_once` | -6.95 | +262.78 | -72.90 | +14.42 | 证伪，仍在 2602 接刀 |
| `doc_range_d1_htrg_continue` | -7.74 | +279.69 | -72.90 | +21.56 | 证伪，小周期延续确认仍不能修复 2602 |
| `doc_range_d1_confirm_boost` | +37.66 | +301.74 | +379.82 | -11.51 | 部分成立：增强确认信号优于直接 HTRG，但伤 2605 |

2602 订单级结论：
- 旧 D1-only 的 2602 盈利不是来自直接 `HTRG`，而是 2月2日大引线后，后续已有 SWP/RGBOT 信号在 4617 附近买入并吃到大反弹；也就是“大周期区间提供背景，入场仍由小周期确认信号完成”。
- 直接 `HTRG` 在 2026-02-02 15:45 以 4675.960 买入，随后 `no_mfe` 出场亏 -22.98；这是典型第一触边接刀，不符合“动能产生延续性再拿单”的要求。
- 因此：大周期 OB/区间触边不是入场信号本身，只能作为已有 SWP/OB/RGBOT 信号的结构加权或目标/止损背景。

24月完整结果：`doc_range_d1_confirm_boost`

| 月份 | D1 confirm boost |
|---|---:|
| 2024-06 | -12.25 |
| 2024-07 | -7.08 |
| 2024-08 | +184.92 |
| 2024-09 | +110.09 |
| 2024-10 | -34.93 |
| 2024-11 | +37.66 |
| 2024-12 | -23.60 |
| 2025-01 | -16.34 |
| 2025-02 | +125.09 |
| 2025-03 | +200.96 |
| 2025-04 | +170.80 |
| 2025-05 | +301.74 |
| 2025-06 | +94.89 |
| 2025-07 | -33.87 |
| 2025-08 | -14.89 |
| 2025-09 | +27.56 |
| 2025-10 | +529.69 |
| 2025-11 | +57.58 |
| 2025-12 | +60.24 |
| 2026-01 | -44.14 |
| 2026-02 | +379.82 |
| 2026-03 | -85.70 |
| 2026-04 | -13.09 |
| 2026-05 | -11.51 |

组合数学：
- 主腿 `m5push_c05` + 旧 D1-only：2505 = +17654.93，2605 = +1162.54，仍有 11 个月低于 200。
- 主腿 `m5push_c05` + D1 confirm boost：2505 = +17693.53，2605 = +1144.80，低于 200 的月份降到 10 个；2602 从 +186.95 改到 +219.64，但 2406/2407/2412/2603 被压低。
- 在现有完整候选中，主腿 + 旧 D1-only 再叠加 3 个最佳补偿腿，最好仍有 4 个月低于 200：2024-06、2024-07、2024-08、2024-11。最优组合示例最低月仍为 2024-11 = -23.52。

收敛结论：
- 2505 和 2605 的盈利目标已经可由主趋势腿满足；当前真正瓶颈是 2024-06/07/08/11 等低收益月份。
- 现有候选无法把 2024-11 拉到 +200，最高只能从主+D1组合的 -33.80 拉到约 -23.52；这说明需要新的实时可观察信号族，而不是继续组合已有腿。
- 下一类可证伪假设应聚焦“已触发大周期结构反应后的二次回踩确认”：记录第一触边极值，等待 M5/M15 不再创新低/新高，并出现同向净推进后，才允许已有 SWP/OB/RGBOT 加权或入场。直接第一触边订单继续禁用。

### 2026-06-17 2602 大周期 OB 案例再拆解：4270-4545 区间触达后的反弹

用户补充的结构观察：
- 2026-02-02 下跌触及 2026-01-25 到 2026-02-01 产生的 4270-4545 大周期 OB/价格区间后，快速反弹并拉出大下影。
- 该观察应抽象为实时可观察特征：`D1/H4 大区间边界` + `触边拒绝` + `M5/M15 不再延续下跌` + `已有 SWP/OB/RGBOT 确认信号`。
- 不能硬编码日期或价格，也不能把“大周期触边”直接当入场信号。

订单级对照：
- 旧 D1-only 在 2026-02-02 15:35 和 15:37 两笔 SWP 买入先被扫，16:03 的 SWP 买入也被扫；真正盈利来自 18:19 约 4619.942 买入，19:00 出场 +212.75。
- HTRG continuation 在 15:45 约 4675.960 直接买入，15:48 `no_mfe` 出场 -22.98。这是第一段下跌中的接刀，而不是确认后的反弹单。
- 因此 2602 的有效经验不是“触到 D1 区间底就买”，而是“触底并拒绝后，等待小周期不再创新低/有同向净推进，再吃反弹”。

失败阻断实验：

| 候选 | 2024-06 | 2024-07 | 2024-08 | 2024-11 | 2025-05 | 2026-02 | 2026-05 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `m5push_fail1_all_block90` | +21.78 | -18.54 | -4.32 | -46.49 | +10413.64 | -67.13 | +1211.80 | 方向级阻断太粗，破坏趋势再入场 |
| `m5push_failcluster_p8_block90` | +28.11 | +9.60 | +2.45 | -31.62 | +6332.05 | -137.04 | +1123.72 | 同价位失败簇也误伤趋势，证伪 |

结论：
- 2024-11 的快速同价位止损簇是真问题，但“失败后停手/阻断”不是正期望修复；它会挡住 2505/2605 这类趋势中必要的再次确认。
- 失败簇信息更适合用于“反向确认信号需要更强”或“同价位第二次入场需 M5/M15 结构突破”，而不是固定分钟阻断。

温和 D1 确认加权实验：

| 候选 | 2024-06 | 2024-07 | 2024-08 | 2024-11 | 2025-05 | 2026-02 | 2026-05 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `doc_range_d1_confirm_soft` | +4.85 | +40.28 | +184.92 | +37.66 | +237.70 | +252.17 | +7.31 | 更均衡，可补 2602/2408，但力度不足 |
| `doc_range_d1_confirm_mid` | -9.98 | +37.90 | +184.92 | +37.66 | +273.68 | +337.07 | +4.02 | 2602 更强，但 2406/2605 变弱 |

组合含义：
- 主腿 `m5push_c05` + 旧 D1-only + soft：代表月中 2024-08 和 2026-02 可超过 200，但 2024-06、2024-07、2024-11 仍低于 200。
- 2605/2505 盈利目标仍由主趋势腿承担；D1 确认腿只是补偿大区间反弹，不应扩大到直接 HTRG 入口。

下一步可证伪方向：
- 新增“二次确认区间反弹”信号，而不是 HTRG 直接订单：记录 D1/H4 宽区间首次触边后的极值，只有当 M5/M15 最近 N 根不再创新低/高，并出现同向净推进或结构突破，才允许已有 SWP/OB/RGBOT 提权。
- 对 2605 的 4580 供应位同理：历史 H4/D1 结构位应持久化，价格多次回测且 M5/M15 没有向上延续时，只允许顺 H4 下跌方向持仓/加权；不要把它当普通滚动区间高抛低吸。

### 2026-06-17 RangeReaction 二次确认实验

新增默认关闭参数与研究信号：
- `InpRangeApplyAlignedSignal`：已有信号与区间反弹方向一致时，也允许套用 RangeFade 的区间 TP/SL/仓位。
- `InpEnableRangeReaction`：D1/H4 大区间触边后，不直接接刀；等待 M5/M15 同向净推进确认后，生成 `RGREACT` 研究信号。

工程验证：
- `python -m py_compile temp\_run_trendhold_24m.py scripts\yaml_to_set.py` 通过。
- `python -m pytest tests\test_mt5_common.py -q` 100 passed。
- `python scripts\check_strategy_consistency.py v11xau-qs3 --brief`：ERROR 0。
- `python scripts\mt5_compile_win.py --mt5-home temp\mt5_portable_bt --mt5-data temp\mt5_portable_bt --log-dir temp\compile_win_bt`：`WaiTrade_OB_SMC.mq5` 0 errors/0 warnings。

代表月结果：

| 候选 | 2024-06 | 2024-07 | 2024-08 | 2024-11 | 2025-05 | 2026-02 | 2026-04 | 2026-05 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `doc_range_d1_confirm_aligned` | +4.85 | +40.28 | +184.92 | +37.66 | +237.70 | +252.17 | -1.98 | +7.31 | 与 soft 基本一致，无边际收益 |
| `doc_range_d1_confirm_swpcont` | -24.71 | +7.26 | +122.90 | +29.12 | +131.09 | +172.65 | -8.48 | +4.39 | SWP延续确认过严，过滤掉有效反弹 |
| `doc_range_d1_confirm_struct_swpcont` | 多数月份无有效解析/极低交易 |  |  |  |  | -0.13 | +66.95 | 无有效解析 | 结构突破要求过严，证伪 |
| `doc_range_reaction_m5` | +4.85 | +40.28 | +184.92 | +37.66 | +237.70 | +252.17 | -1.98 | +7.31 | 未产生新增 `RGREACT` 成交 |
| `doc_range_reaction_m15` | 未全量跑；2602/2604 与 m5 完全一致 |  |  |  |  | +252.17 | -1.98 |  | 未产生新增成交 |

证伪结论：
- 现有 D1 RangeFade 的收益主要来自已有 SWP/RGBOT 信号在边界附近被加权或反向修正，不是来自独立“触边后追随”信号。
- 强制 SWP/M5 结构延续确认会把有效订单一起挡掉；这不符合“吃满反弹”的目标。
- `RangeReaction` 基础设施暂时保留为默认关闭研究代码，但当前没有证据支持纳入候选组合。
- 2602 的 4270-4545 案例仍应吸收为“区间背景 + 已有确认信号加权/目标背景”，而不是新增直接追单。

### 2026-06-17 RangeReaction 复测校正：直接独立信号证伪

工程校正：
- 发现 `InpEnableRangeReaction` 等 13 个新增 input 会把 `WaiTrade_OB_SMC` 推到 MT5 上限之外：`Tester too many input parameters (1037)`。
- 修复方向不是继续新增开关，而是删除默认关闭研究 input，改用既有 `InpRangeTPTarget` 哨兵控制研究模式；同时修复 `scripts/mt5_compile_win.py`，编译后同步 `.ex5` 回项目目录，避免 runner 继续复制旧二进制。
- `InpRangeTPTarget=2`：启用 `RGREACT` 独立二次反应信号；`InpRangeTPTarget=3`：只测试已有信号的区间方向一致加权。`CalcRangeTP` 已改为仅 `0=对侧边界`，其他值仍用中轴，避免哨兵污染 TP。

关键复测：

| 候选 | 2026-02 | Trades | 结论 |
|---|---:|---:|---|
| `doc_range_d1_confirm_soft` | +142.52 | 24 | 仍能把大区间背景用于已有信号，但力度低于旧结果 |
| `doc_range_d1_confirm_aligned` | -56.94 | 13 | 已有信号 aligned 加权/改写会错杀 2602 有效反弹 |
| `doc_range_reaction_m5` | -226.63 | 697 | `RGREACT` 真实生效后高频过度交易，证伪 |

订单级结论：
- `RGREACT` 在 2026-02 从 2月2日早盘开始连续生成买/卖订单，月内 697 笔，属于滚动 D1 区间边界反复追单，不是“触底拒绝后的小周期确认”。
- 2602 的有效经验继续收敛为：大周期 OB/宽区间只能作为背景，必须让已有 SWP/OB/RGBOT 这类小周期确认信号负责入场；独立区间反应订单会把假延续和震荡噪音放大。
- 后续不再推进直接 `RGREACT`。若继续吸收该经验，应做“已有信号质量加权/目标背景/止损背景”，而不是新增独立入场族。

### 2026-06-17 2602 大周期 OB 经验的方向闸门反证

用户补充：
- 2026-02-02 下跌触及 2026-01-25 到 2026-02-01 产生的 4270-4545 大周期 OB/价格区间后，立刻反弹并拉出大下影。

新增两个不增加 MT5 input 的哨兵研究模式：
- `InpRangeTPTarget=4`：只接受大区间边界同向的已有确认信号，但仍应用 Range TP/SL/仓位覆盖。
- `InpRangeTPTarget=5`：大区间只做方向闸门；上沿拦买、下沿拦卖，不反转、不独立下单、不覆盖同向 TP/SL/仓位。

代表月 MT5 回测：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `doc_range_d1_confirm_follow` | -12.00 | +37.50 | +88.81 | +73.39 | +114.21 | -86.97 | -16.08 | -0.60/FAIL | 中部过滤 + Range覆盖直接破坏趋势月 |
| `doc_range_d1_confirm_follow_overlay` | +31.84 | +20.70 | -1.24 | -81.00 | +1169.08 | -158.92 | -46.51 | FAIL | 不过滤中部仍因 Range覆盖伤趋势 |
| `doc_range_d1_direction_gate` | +29.52 | +16.04 | -0.73 | -85.96 | +3741.48 | -149.08 | -54.79 | -37.23 | 纯方向闸门仍错杀趋势突破段 |

结论：
- 2602 的 4270-4545 大周期 OB 案例是真结构，但不能泛化成“动态 D1 区间边界闸门”。
- 方向闸门会在 2505/2605 趋势月把突破段误判为边界反向，直接违背“吃满趋势利润”。
- 该经验的可用表达应更窄：必须包含“触达后已出现拒绝 K 线/大引线 + 小周期不再创新低/高 + 同向净推进”，不能只根据当前价格处于 D1 区间边界。
- 下一步若继续吸收 2602，应做“拒绝后确认”的结构质量加分或止损背景，而不是区间触边、区间同向或区间方向闸门。

### 2026-06-17 HTRG 拒绝确认全 24 月复测

候选：`risk8_fast02_h105_aligned_nocont_03_doc_range_d1_htrg_continue`

该候选对应更窄的规则：D1 大区间边界触达后，要求已经出现拒绝 K 线/大引线，并且后续小周期不再创新低/高，当前 K 线产生同向净推进。

24 独立月结果：
- 总收益：+3096.31
- 盈利月：16/24
- >=200 月：5/24
- 最差月：2024-10 = -26.85
- 2505：+153.28
- 2605：+17.76
- 2602：+255.79
- 2408：+443.55

关键观察：
- HTRG 拒绝确认能把 2602 做到 +255.79，证明用户给出的 2026-02-02 大周期 OB 经验成立，但只适合作为补偿腿。
- 它也能补 2024-08，但无法补 2024-06/2024-07/2024-11/2026-04。
- 这说明“大周期 OB 触达后拒绝确认”不是 24 月 >=200 的最终解，只解决部分结构行情。

完整 24 月组合扫描：

| 组合 | >=200 月 | 最低月 | 仍低于200月份 |
|---|---:|---:|---|
| 旧最佳5腿：D1-only + MBOS + fail_block + fail_pos + m5push | 20/24 | +30.21 | 2406 +30.21, 2407 +130.75, 2408 +186.00, 2411 +32.47 |
| 加入 HTRG continue 的最佳5腿 | 20/24 | +11.30 | 2406 +26.08, 2407 +82.00, 2411 +11.30, 2506 +177.31 |
| D1-only + HTRG + 主趋势/失败簇组合 | 20/24 | +9.18 | 2406/2407/2411/2604 仍低 |

结论：
- 当前 SWP/OB/MBOS/D1-only/HTRG 体系的组合上限约为 20/24 月 >=200。
- 低于 200 的稳定缺口不是 2602，而是 2024-06/2024-07/2024-11/2026-04 这类低频/低交易量月份。
- 下一条假设必须是新的低频补偿信号源，而不是继续调 D1 区间、DTP、SellSpreadRisk 或已有 MBOS。

下一条可证伪假设：
- **低波动结构延续补偿腿**：当 M15/H1 波动收窄、主策略交易密度低时，只交易小周期强弱高低点的收盘突破后回踩，不依赖月份标签；要求 M5/M15 同向净推进、无强反向 K、并用宽 SL/小仓位。目标不是吃 2505/2605 主趋势，而是在低频月补 +150~200。
- 验证重点：2406/2407/2411/2604 是否增加净利润，同时 2505/2605 不低于 +3000/+1000。

#### MicroBOS 低频补偿腿反证

新增 runner-only 候选，不增加 EA input：
- `doc_mbos_m5_lowfreq`：M5 小结构突破回踩，无 OB/FVG 重合要求，宽 SL，小仓位，要求 M5 延续。
- `doc_mbos_m15_lowfreq`：M15 小结构突破回踩，更慢周期，宽 SL，小仓位，要求 M5 延续。

代表月结果（两者结果相同，基本等同主基线）：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `doc_mbos_m5_lowfreq` | +18.88 | +16.04 | -3.07 | -71.46 | +17391.79 | -160.18 | -52.35 | +1106.20 | 无有效新增 |
| `doc_mbos_m15_lowfreq` | +18.88 | +16.04 | -3.07 | -71.46 | +17391.79 | -160.18 | -52.35 | +1106.20 | 无有效新增 |

结论：
- 当前 MicroBOS 检测路径没有命中低频月缺口；问题不是 H4 对齐或区位重合太严，而是该信号族本身没有在 2406/2407/2411/2604 提供足够交易。
- 下一步改查窄幅整理突破 `RangeBreakout`：它更符合低波动月“先收缩、再突破延续”的结构。

#### RangeBreakout 低频补偿腿反证

新增 runner-only 候选，不增加 EA input：
- `doc_range_breakout_lowfreq_m5`：M5 窄幅整理突破，要求 M5 净推进确认，宽 TP，小仓位。
- `doc_range_breakout_lowfreq_loose`：放宽整理宽度和突破阈值，允许弱逆向净推进小仓位入场。

代表月结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `doc_range_breakout_lowfreq_m5` | -6.16 | -15.02 | +3.21 | -70.30 | +11631.17 | -131.94 | -62.25 | +903.03 | 严格突破仍负期望，2605 未达 +1000 |
| `doc_range_breakout_lowfreq_loose` | +17.96 | +29.08 | +15.81 | -73.11 | +4694.83 | -166.71 | -49.17 | +993.72 | 低频月补偿太弱，且 2602/2604 恶化 |

结论：
- 窄幅整理突破能轻微改善 2406/2407/2408，但收益量级远低于每月 +200 的缺口。
- 2411、2602、2604 出现更稳定的负期望，说明这不是缺少突破信号，而是新增突破腿在反复制造“无延续”的假突破订单。
- `RangeBreakout` 不作为当前 24 月 >=200 的主路径；后续重点转向订单级诊断：比较稳定腿少量成交与 m5push/HTFPB/RangeBreakout 放量亏损订单的实时结构差异。

#### 失败簇反手补偿腿反证

订单级诊断（2024-11）：
- 稳定腿 `lock5_10_fail_pos05_2_60_noclear`：11 笔，+2.50；亏损集中在 10-60 秒 SL，失败保护把后续同向再入场挡掉。
- 放开 `m5push_c05` 后：68 笔，-71.46；`SL<1m` 23 笔合计 -114.30，卖单 37 笔合计 -88.70。
- `RangeBreakout`/HTFPB 放量亏损的形态相同：不是“趋势拿不住”，而是入场后 1 分钟内被反向动能击穿。

可证伪假设：连续失败簇可能代表小周期结构反转，反手可能比继续同向重入更优。

代表月结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `rev_mfe025` | -39.22 | -19.49 | -5.18 | +2.50 | +4872.19 | -13.96 | +28.25 | +1148.05 | MFE 失败反手破坏低频月，证伪 |
| `rev_nomfe025` | +39.29 | +39.31 | -1.08 | +2.50 | +3011.08 | +0.36 | +0.67 | +1194.81 | 温和，不破坏关键月，但补偿不足 |
| `rev_early025` | -30.29 | -5.75 | -12.33 | -14.08 | +1038.27 | -10.20 | +7.70 | +937.93 | EarlyLoss 反手破坏 2411/2505/2605，证伪 |

结论：
- “失败簇=可直接反手”不成立；MFE 和 EarlyLoss 反手都会把噪音失败放大成新亏损。
- NoMFE 反手只在“不产生最小浮盈”的订单上触发，风险较小，能保持 2505 >3000 与 2605 >1000，但仍不能解决 2406/2407/2411/2604 的 +200 缺口。
- 下一步只值得对 `rev_nomfe025` 做 24 独立月检查，作为稳定腿小改良；主突破口仍必须是新的高质量低频结构信号。

全 24 月复测（`rev_nomfe025`）：
- 总收益：+125160.36
- 盈利月：21/24
- >=200 月：11/24
- 最差月：2024-12 = -1.27
- 2505：+3011.08
- 2605：+1194.81
- 2602：+0.36
- 低于 200：2406 +39.29, 2407 +39.31, 2408 -1.08, 2411 +2.50, 2412 -1.27, 2501 +8.10, 2503 -0.64, 2506 +7.28, 2507 +29.16, 2508 +0.33, 2601 +2.63, 2602 +0.36, 2604 +0.67。

组合扫描（19 个已完成 24 月候选，最多取 6 腿）：
- 最佳组合提升到 21/24 月 >=200，最低月 +49.41。
- 仍低于 200：2406 +50.40、2407 +119.90、2411 +49.41。

结论更新：
- `rev_nomfe025` 可以替代原稳定腿作为“小幅稳定改良”，但不是目标解。
- 24 月全 >=200 的剩余缺口高度集中在 2406/2407/2411，且这些缺口不是靠 2602 大周期 OB、D1 Range、MicroBOS、RangeBreakout、失败反手能解决。
- 下一步应专门寻找“不依赖月份标签、在低交易量环境也会出现”的高周期结构补偿腿，例如 H1/H4 强弱高低点突破后的回踩订单块，而不是继续放大 M1/M5 反弹或反手。

#### 2602 大周期 OB / D1 区间样本吸收与反证

用户补充结构样本：2026-02-02 下跌触及 2025-12 至 2026-01 形成的 4270-4545 大周期价格区间/OB，下沿触达后立即反弹并拉出大下影线。

实时可观测抽象：
- 高周期价格区间或订单块边界已经由历史已收盘 K 线形成。
- 当前价触达区间下沿或上沿。
- 小周期 K 线出现拒绝影线，且后续不再创新低/新高。
- M5/M15 出现同向净推进延续后才入场。

已有代码对应通道：`ExecuteHTFRangeBoundarySignalSMC`。
- `InpRangeMaxWidthATR <= -40` 启用直接 HTRG 边界信号。
- `abs(InpRangeMaxWidthATR) >= 60` 限制同一边界只用一次。
- `abs(InpRangeMaxWidthATR) >= 80` 要求触达拒绝后的小周期延续结构。

新增 runner-only 候选，不增加 EA input：
- `doc_range_d1_htrg_continue_fulltp`：D1/H4 边界触达 + 拒绝影线 + 小周期延续，TP 改为区间对侧，宽 SL。
- `doc_range_d1_htrg_continue_fulltp_x2`：同上，只放大 HTRG 通道仓位。

代表月结果：

| 候选 | 2406 | 2407 | 2411 | 2505 | 2602 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---|
| `htrg_continue` | +16.47 | -10.85 | +1.18 | +153.28 | +255.79 | +17.76 | 2602 样本成立，但只是窄补偿腿 |
| `htrg_continue_fulltp` | +22.49 | -3.26 | +1.18 | +39.29 | +244.17 | +21.29 | 对侧 TP 没有吃满趋势，2505 被压缩 |
| `htrg_continue_fulltp_x2` | +16.76 | -12.57 | +9.16 | +35.08 | +389.65 | +14.76 | 2602 更强，但关键目标月破坏更明显 |

结论：
- 2602 的大周期 OB 拒绝反弹是有效结构样本；它能被“高周期边界触达 + 拒绝影线 + 小周期延续”实时识别。
- 该结构不能泛化成主力趋势腿：对侧 TP 会显著压缩 2505，且 2407 变负，说明在趋势月它更像低频区间反弹，不是持续趋势利润来源。
- 当前可保留方向是窄补偿：用中轴/短目标或小仓位增强 2602、2408，而不是把 HTRG 放大成主策略。
- 对 2406/2407/2411 的 +200 缺口仍需要新结构来源；单纯高周期区间边界、H4 wide、D1 full TP 都已证伪。

#### H4 持久 BOS 结构位验证

用户补充结构样本：
- 2605 的 4580 附近 OB/结构位：多次触达后向下，说明有效大周期供给位可能持续近半个月。
- 2602 的 2025-12 至 2026-01 大区间 4270-4545：2026-02-02 下跌触达下沿后立即反弹并拉出大下影线，说明大周期需求区触达后的拒绝反应有效。

实时可观测抽象：
- H4 已收 K 线突破强高低点形成结构位。
- 价格多日后回踩该结构位。
- 小周期没有反向结构击穿，且出现同向动能延续时才允许入场。

代码修正：
- `SwingBreakSignal` 增加 `last_entry_age`，H4 BOS 成交后保留信号年龄，不再像 H1 BOS 一样把 `age_bars` 归零。
- H4 BOS 的 `custom_max_bars` 改为 `max(InpBOSRetestMaxBars * 10, 7200)`；默认仍是 5 天，候选可测试 15/20 天。
- direct-entry 分支补齐 `PassBOSExecutionFilter`，保证 BOS 延续过滤在所有 BOS 执行路径一致。

代表月结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `h4persist15` | -33.03 | +39.31 | -1.08 | +2.50 | +3690.26 | +0.73 | -38.74 | +1049.28 | 抓到 2605，保住关键月，但新增坏触位 |
| `h4persist20` | -33.03 | -14.57 | -2.71 | +2.50 | +3624.44 | -5.31 | -38.74 | +1044.88 | 延长窗口恶化 2407/2602 |
| `h4persist15_m5cont` | -33.03 | +39.31 | -1.08 | +2.50 | +3690.26 | +8.54 | -38.74 | +1049.28 | M5 延续只小幅改善 2602 |
| `h4persist15_m15cont` | -33.03 | +39.31 | -1.08 | +2.50 | +3690.26 | +8.54 | -38.74 | +1049.28 | 与 M5 延续完全一致 |
| `h4persist15_m5strong` | -33.03 | +39.31 | -1.08 | +2.50 | +3690.26 | +8.54 | -38.74 | +1049.28 | 强延续仍不能过滤坏触位 |
| `h4persist15_m5cont_w12` | -33.03 | +39.31 | -1.08 | +2.50 | +3690.26 | -61.00 | -38.74 | +1049.28 | 降权触发不同风控路径，2602 恶化 |

全 24 月复测（`h4persist15`）：
- 总收益：+126250.45
- 盈利月：20/24
- >=200 月：9/24
- 亏损月：2406 -33.03、2408 -1.08、2412 -1.27、2604 -38.74
- 2505：+3690.26
- 2605：+1049.28
- 2602：+0.73

结论：
- H4 持久 BOS 结构位是有效的 2605 补偿机制，能把 2605 从 +1194 附近稳定维持在 >1000，同时让 2505 >3000。
- 但它不能达成 24 个独立月全盈利或全 >=200；新增结构位会在 2406/2604 放出错误触位单。
- 普通 M5/M15 延续、强 M5 延续都不能过滤这些错误单，说明坏单并非“无延续”，而是结构位质量不足或供需区方向/新鲜度失真。
- 下一步不再扫描普通动能阈值；应做“结构位质量”过滤：只保留突破了强高低点、带急速突破、伴随 sweep、且首次/少次数缓解的 H4/D1 OB。对 2605 4580 这类多次触达有效区，需要记录结构位生效次数与每次触达后的拒绝强度，而不是把所有 H4 BOS 回踩一视同仁。

#### 强 sweep 小仓位补偿腿验证

可证伪假设：
- 剩余低盈利月不是缺少主趋势腿，而是缺少高质量“流动性扫损后反向”的小补偿腿。
- 若 sweep 发生在折价/溢价区，并且小周期收回关键高低点后继续推进，则可作为低风险补偿，不应破坏 2505/2605。

代码一致性修正：
- `ExecuteStrongSweepReversalConfirmed` 原先没有调用 `PassSMCDirectionGate`，REVSWP 会绕过全局方向门控。
- 已补齐 REVSWP 成交前的方向门控，并重新编译通过 0 errors / 0 warnings。

代表月结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `rev_nomfe025` | +39.29 | +39.31 | -1.08 | +2.50 | +3011.08 | +0.36 | +0.67 | +1194.81 | 当前稳定底座 |
| `ssweep_tiny_m5` | +40.46 | +39.31 | -1.46 | +2.50 | +3177.04 | -16.14 | +0.67 | +1017.06 | M5 sweep 太低频，补偿不足 |
| `ssweep_tiny_m1` | +84.43 | +158.53 | +1.06 | +0.28 | +5182.97 | +6.66 | -84.10 | +1183.35 | 能补 2406/2407，但 2604 错误放量 |
| `ssweep_tiny_m1_h1dp_strict` | +29.65 | -21.81 | -1.13 | -3.62 | +3238.01 | -5.22 | +20.06 | +1184.13 | 严格 H1 DP 修 2604，但杀掉 2407 |

结论：
- 强 sweep 反转确实是一个实时可观测的补偿信号，尤其 M1 版本能显著改善 2406/2407。
- 但它不能直接作为目标解：M1 版在 2604 错误放量，严格版又过滤掉 2407 的有效反应。
- 问题不是 sweep 本身，而是缺少“高周期供需区/边界”上下文。下一步应把强 sweep 与 D1/H4 区间边界或订单块触达绑定：只在高周期折价/溢价区、未缓解或少缓解供需区附近接受 M1 sweep 反转。
- 不建议继续单独调 sweep wick/penetration/cooldown；这些参数只能在 2407 与 2604 之间转移损益，不能同时补齐低频月。

全 24 月复测（`ssweep_tiny_m1`，2026-06-17 11:17）：
- 总收益：+132698.57
- 盈利月：20/24
- >=200 月：11/24
- 2505：+5182.97
- 2605：+1183.35
- 新增/保留亏损月：2410 -17.73、2412 -9.27、2504 -0.31、2604 -84.10
- 低于 200：2406 +84.43、2407 +158.53、2408 +1.06、2410 -17.73、2411 +0.28、2412 -9.27、2501 +132.62、2504 -0.31、2506 +3.85、2507 +76.35、2601 +2.78、2602 +6.66、2604 -84.10。

订单级拆解：
- 2407：112 笔，净 +158.53；`SWP` +129.93，`REVSWP` +25.62。盈利来自 1-5 分钟内 DTP/TP 的少量大赢，`sell` 净 +163.07。
- 2604：73 笔，净 -84.10；`REVSWP` 50 笔净 -71.05，`SWP` 18 笔净 -15.73。亏损集中在 `<1m` 快速 SL，43 笔 SL 净 -150.81。
- 2602：32 笔，净 +6.66；`REVSWP` 净 -28.13，`PLAIN` 净 +45.51。用户给出的 2月2日 D1 大周期 OB 反弹，仍主要由已有确认信号吃到，不是 `REVSWP` 直接捕捉。
- 2605：92 笔，净 +1183.35；`REVSWP` +1071.61，其中一笔 `REVSWP B x0.4` 长持约 1047 分钟贡献 +1090.36，说明“没有小周期反转且动能未衰弱时继续持有”方向成立，但触发样本稀疏。

组合代理扫描（仅用 24 月月度净值相加，不是 MT5 组合回测）：
- 已完整载入 22 个 24 月候选。
- 最佳单腿仍是 `lock3_20_fail_pos05_2_60_noclear`：24/24 盈利，最差 +2.17，>=200 10/24，2505 +3011.34，2605 +1240.02。
- 最佳 5 腿按最差月排序：24/24 盈利，最差 +71.01，>=200 18/24，2505 +12531.57，2605 +3479.87；低点仍是 2410 +71.01、2411 +81.62、2406 +91.29、2412 +136.85、2407 +169.38、2501 +183.87。
- 最佳 5 腿按 >=200 覆盖：20/24 月 >=200，但最差仍只有 +50.99；低点集中在 2406/2407/2411/2604。

结论收敛：
- 当前主趋势腿、H4 持久 BOS、D1 宽区间拒绝、M1 强 sweep 的组合上限，仍无法把每月稳定抬到 +200。
- 用户的 2602 大周期 OB 经验已经被吸收为“高周期区间/OB 背景 + 小周期拒绝后确认”，不能转化为直接触边接刀，也不能作为全局方向闸门。
- 下一轮需要第三类低频正期望信号，目标不是再放大趋势腿，而是补 2406/2407/2411/2412/2501/2506 这类低交易量月的 $100-$150 缺口。
- 可证伪方向：记录 D1/H4 订单块的“新鲜度/缓解次数/触达后拒绝强度”，只有首次或少次缓解、触达后 M5/M15 不再继续破低/破高、并出现同向净实体推进时，才允许 `REVSWP` 或已有 SWP/OB 信号提权；禁止新增独立 HTRG 接刀单。

#### 2026-06-17 续：高周期 DP 与 OB 新鲜度硬过滤反证

可证伪假设 A：
- `REVSWP` 的问题不是 sweep 形态，而是缺少高周期折价/溢价背景。
- 若将 `InpStrongSweepDPTF` 从 M15 升到 H4/D1，并使用宽松/严格分位，则应保留 2407 的有效反弹，同时削掉 2604 的快速 SL。

代表月结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `ssweep_tiny_m1` 原版 | +84.43 | +158.53 | +1.06 | +0.28 | +5182.97 | +6.66 | -84.10 | +1183.35 | 补 2406/2407，但 2604 错误放量 |
| `h4dp_wide` | +20.31 | -42.32 | -0.94 | -3.62 | +4355.69 | -1.48 | -33.01 | +990.34 | H4 DP 杀 2407，2605 低于目标 |
| `h4dp_strict` | +17.69 | -44.83 | +4.59 | -3.62 | +3480.86 | -3.27 | -40.78 | +1188.81 | 仍杀 2407，2604 仍负 |
| `d1dp_wide` | +45.39 | -19.81 | +0.30 | +0.32 | +3.63 | -5.36 | -44.79 | +1181.74 | D1 DP 错杀 2505 主趋势 |
| `d1dp_strict` | +29.79 | -30.84 | +1.07 | +0.32 | +0.43 | -5.77 | -51.50 | +1180.48 | 更严重错杀 2505 |

结论：
- 高周期分位不是有效 OB/供需区上下文。它会把 2407 的有效扫损反转过滤掉，也会在 2505 趋势月错杀关键延续段。
- `2602` 的 4270-4545 大周期 OB 经验不能被简化成 D1/H4 分位；关键是“触达大区间后拒绝 + 小周期停止破低/破高 + 同向净推进”。
- 不继续扫描 DP 阈值；该方向已证伪。

可证伪假设 B：
- 低盈利月可能来自重复缓解的旧 OB 噪音。
- 若启用 `InpOBFreshnessFilter` 并限制 `InpOBMaxMitigations`，应削掉低质量 OB 反复交易，同时保住 2505/2605。

代表月结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `fresh1` | FAIL | FAIL | FAIL | -1.47 | -0.69 | -9.62 | FAIL | FAIL | 过严，几乎清空主腿 |
| `fresh2` | FAIL | -1.27 | -1.19 | +0.54 | +23.90 | -10.01 | -2.32 | +9.25 | 仍清空趋势收益 |

结论：
- 现有 `g_ob_mitigations` 计数不适合做全局硬过滤；它对主趋势腿过于敏感，会把 2505/2605 的有效反复触达也过滤掉。
- OB 新鲜度仍可能有价值，但只能作为局部提权/降权特征，并且必须和“触达后的拒绝强度、是否继续破低/破高、同向净实体推进”一起使用。
- 下一步实现方向应避免两个硬过滤：不做高周期 DP 硬闸门，不做 OB 缓解次数硬闸门；只在已有 `REVSWP/SWP/OB` 信号上增加“拒绝确认质量分”或小仓位补偿。

#### 2026-06-17 续：小周期延续确认与 DTP 严格出场复验

用户强调的实时结构：
- 若小周期没有反转，且动能没有衰弱到强力反弹，且反向动能没有产生延续性，应考虑继续持仓。
- 该经验不能用月份、日期或固定价格实现；只能落到 M1/M5/M15 的反向结构突破、动能衰弱、反向净推进等实时特征。

工程修正：
- 尝试新增 `InpStrongSweepRejectionQuality/Bars` 做 REVSWP 拒绝质量门控后，MT5 tester 从正常完成变为 `tester didn't start`；临时 `.set` 达到 607 行，判断为 EA input 上限风险。
- 已撤销这两个新增 input，避免污染后续 MT5 回测。
- 发现 `InpDTPStrictExitFamilies=REVSWP` 由于 `EntryFamilyName()` 未映射 `ENTRY_FAMILY_REVSWP`，严格 DTP 族过滤无法命中 REVSWP；已补齐 `REVSWP` 映射并重新编译，`WaiTrade_OB_SMC.mq5` 0 errors / 0 warnings。

可证伪假设 C：普通 M5/M15 延续确认可以替代新增拒绝质量门控。

代表月结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `ssweep_tiny_m1` 原版 | +84.43 | +158.53 | +1.06 | +0.28 | +5182.97 | +6.66 | -84.10 | +1183.35 | 补 2406/2407，但 2604 错误放量 |
| `m5cont` | +92.71 | -21.69 | +27.69 | +2.44 | +10849.92 | +18.25 | -38.78 | +1171.21 | M5 延续抬高 2505，但杀 2407，2604仍负 |
| `m15cont` | +40.75 | -13.57 | +30.76 | +2.29 | +3142.24 | +4.44 | +2.27 | +1163.33 | 2604转正，但 2407仍负，2505刚过线 |

结论：
- “提高小周期确认周期”能减少一部分噪音，但不是稳定解；M5/M15 会过滤掉 2407 的有效短周期反应，同时 2605 没有明显增加。
- 2602 的 4270-4545 大周期 OB 经验仍不能简化为普通动能确认；它需要“高周期结构位质量 + 触达后拒绝 + 小周期不再破极值 + 同向净推进”的组合特征。

可证伪假设 D：DTP 出场只在反向延续且原方向动能衰弱时触发，可以吃满趋势利润。

代表月结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `ssweep_tiny_m1` 原版 | +84.43 | +158.53 | +1.06 | +0.28 | +5182.97 | +6.66 | -84.10 | +1183.35 | 基线 |
| `dtp_revweak` 全局 | +138.72 | +240.45 | +2.09 | +2.82 | +2600.04 | -4.83 | -1.49 | +1455.49 | 2407/2605提升，但 2505跌破3000 |
| `dtp_allhold` 全局 | +138.72 | +240.45 | +2.09 | +2.82 | +2600.04 | -4.83 | -1.49 | +1455.49 | 与 revweak 完全一致，说明 DTPHoldOnContinuation 不是瓶颈 |
| `dtp_revonly` 仅 REVSWP | +54.71 | +176.45 | +0.68 | +2.11 | +7058.66 | -2.22 | +2.14 | +1180.58 | 保住 2505/2605，修 2604，但未明显放大2605 |

结论：
- “没有反向延续/动能衰弱就不出”的出场逻辑是有效局部改进：全局版能明显抬高 2407 与 2605。
- 但全局严格 DTP 会压缩 2505 主趋势利润，说明普通趋势腿的 DTP 不能全部延后。
- `REVSWP-only` 是更稳的实现边界：不破坏 2505，且把 2604 从 -84.10 改到 +2.14；但 2605 仍约 +1180，不能达成更高目标。

可证伪假设 E：放大已验证为正贡献的 REVSWP 仓位即可放大 2605。

代表月结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `dtp_revonly` | +54.71 | +176.45 | +0.68 | +2.11 | +7058.66 | -2.22 | +2.14 | +1180.58 | 稳定边界 |
| `dtp_revonly_p025` | +54.44 | +172.41 | +2.15 | +1.69 | +8401.31 | +1.57 | -2.92 | +1154.60 | 2505增加但 2605下降，2604转负 |
| `dtp_revonly_p035` | +57.08 | -0.51 | +2.80 | +1.34 | +6644.23 | -3.14 | -76.68 | +1123.72 | 明确退化，2407/2604被打坏 |

结论：
- REVSWP 仓位不是线性收益杠杆；放大仓位会改变风控/入场序列，2605 没有放大，2604与2407反而恶化。
- 当前可保留候选是 `ssweep_tiny_m1_dtp_revonly`，它吸收了“没有反向延续/动能衰弱就继续拿”的经验，但只能作为局部改良，不是最终目标解。
- 下一步不应继续调 REVSWP 仓位、wick、penetration、DP 或普通 M5/M15 延续；应做结构位质量评分：高周期 OB 是否突破强高低点、是否急速冲动、是否伴随 sweep、是否首次/少次缓解、触达后是否停止破极值并出现同向净推进。评分只用于 REVSWP/SWP/OB 局部提权/降权，禁止新增直接触边接刀。

全 24 月复测（`ssweep_tiny_m1_dtp_revonly`，2026-06-17 14:01）：
- 总收益：+144873.55
- 盈利月：23/24
- >=200 月：12/24
- 2505：+7058.66
- 2605：+1180.58
- 2602：-2.22
- 低于 200：2406 +54.71、2407 +176.45、2408 +0.68、2410 +62.48、2411 +2.11、2412 +11.66、2501 +64.29、2506 +17.81、2507 +40.43、2512 +5.58、2602 -2.22、2604 +2.14。

结论补充：
- `dtp_revonly` 是目前最好的单腿局部改良之一：修复 `ssweep_tiny_m1` 的 2604 错误放量，并保住 2505/2605。
- 但它仍未满足 24 月全盈利且全 >=200；剩余缺口仍是低交易/低净值月，而不是 2505/2605。
- 月度代理组合扫描显示，现有完整 24 月候选叠加最多仍约 20/24 月 >=200，且低点集中在 2408/2411/2602/2604；这只是筛选，不是有效 MT5 组合回测。

可证伪假设 F：严格 DTP 从 `REVSWP` 扩展到 `SWP/OB`，可以把普通扫损类趋势也吃满。

代表月结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `dtp_revonly` | +54.71 | +176.45 | +0.68 | +2.11 | +7058.66 | -2.22 | +2.14 | +1180.58 | 只作用 REVSWP，2505/2605达标 |
| `dtp_swp_rev` | +138.72 | +240.45 | +0.68 | +2.42 | +2825.44 | -4.83 | +2.73 | +1483.66 | 2407/2605提升，但 2505跌破3000 |
| `dtp_ob_swp_rev` | +138.72 | +240.45 | +2.09 | +2.82 | +2600.04 | -4.83 | -1.49 | +1455.49 | 等同全局严格DTP，2505进一步退化 |

结论：
- “继续拿单”规则不能按信号族粗暴扩大到全部 SWP/OB；它会改变 2505 主趋势路径，导致关键目标月跌破 3000。
- 下一步必须做 SWP/REVSWP 内部质量子集，而不是全族：例如高周期结构位附近、触达后未继续破极值、M5/M15 有同向净推进、且反向没有延续时才延后 DTP。
- 这也支持用户的 2602/2605 经验：核心不是“扫损单都拿久”，而是“高周期有效供需位触达后的确认反应单拿久”。

可证伪假设 G：HTF 净推进或高周期大区间边界可以作为 SWP/REVSWP 严格 DTP 的质量子集。

用户新增结构样本：
- 2602 在 2026-02-02 下跌触及 2026-01-25 至 2026-02-01 形成的 4270-4545 大周期 OB/价格区间后，立刻反弹并拉出大下影线。
- 该经验应抽象为实时特征：高周期区间/供需位边界触达，触达后拒绝，小周期停止继续破低/破高，并产生同向净推进；不能写成固定日期或固定价位。

工程实现：
- 新增 `InpRangeTPTarget=6` 研究语义：RangeDetector 只作为 DTP 严格持仓质量门，不改入场方向、不改 SL/TP。
- `REVSWP` 继续使用已验证的严格 DTP；`SWP` 额外要求入场价位处于 HTF 区间上沿做空或下沿做多，才允许严格 DTP。
- 同时验证了直接启用 range fade 入场：D1 能改善 2602，但会清空 2505/2605 主趋势收益，不能作为主腿覆盖。

代表月结果：

| 候选 | 2406 | 2407 | 2408 | 2411 | 2505 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `dtp_revonly` | +54.71 | +176.45 | +0.68 | +2.11 | +7058.66 | -2.22 | +2.14 | +1180.58 | 稳定边界 |
| `dtp_swp_rev_h1q` | +1.86 | +168.70 | +4.30 | -1.77 | +4045.44 | +6.66 | -98.86 | +1172.60 | H1净推进会放大2604亏损 |
| `dtp_swp_rev_m15q` | +204.11 | +135.30 | +0.68 | -3.41 | +5474.67 | +6.66 | -92.38 | +1399.18 | 2406/2605提升，但2604明显退化 |
| `dtp_revonly_d1_range_soft` | +9.66 | +15.51 | +160.15 | +13.51 | +179.96 | +140.92 | -25.24 | +0.77 | D1区间入场能抓2602，但清空主趋势 |
| `dtp_revonly_h4_range_soft` | -15.26 | +11.39 | -4.52 | -2.31 | +23.75 | +45.86 | -25.38 | +11.15 | H4区间入场更弱 |
| `dtp_swp_rev_d1rq` | +54.71 | +161.35 | +0.68 | +2.11 | +6490.78 | -2.22 | +2.14 | +1180.58 | D1质量门未带来净增益 |
| `dtp_swp_rev_h4rq` | +54.71 | +176.45 | +0.68 | +2.11 | +7325.55 | -2.22 | +2.14 | +1180.58 | 仅2505略增，其余等同REVSWP-only |

结论：
- 大周期区间边界是有效的独立入场/补腿信息：D1 range fade 能把 2602 从 -2.22 改到 +140.92。
- 但直接用大区间 fade 覆盖主腿，会极大牺牲 2505/2605 趋势利润；这违反“吃满趋势利润”的主目标。
- 把大区间边界只作为 SWP 严格 DTP 质量门，无法修复 2602，也无法提升 2605；说明 2602 的利润来自“边界触达后的新反应入场”，不是已有 SWP 持仓的出场延后。
- 当前最稳主腿仍是 `dtp_revonly`；若继续吸收 2602 经验，应开发独立的 HTF OB/Range Reaction 补腿，并让它只在低频、高质量边界触达后入场，且不得覆盖主趋势腿。

可证伪假设 H：低收益月主要是月度锁盈过早截断，放宽锁盈即可释放后续结构机会。

订单级观察：
- `dtp_revonly` 在 2024-11 只有 11月1日 一组交易，先盈利后回撤，月度锁盈参数为 `5%/10%`，具备“早期小盈利后停止”的表象。
- 但该特征不能按月份处理，只能抽象为实时风控假设：低余额账户中百分比锁盈阈值过低，可能提前关闭后续高质量结构机会。

代表月结果：

| 候选 | 2406 | 2408 | 2410 | 2411 | 2412 | 2505 | 2602 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `dtp_revonly` | +54.71 | +0.68 | +62.48 | +2.11 | +11.66 | +7058.66 | -2.22 | +1180.58 | 稳定边界 |
| `dtp_revonly_noplock` | +54.71 | +2.25 | +62.48 | -16.69 | +4.88 | +7058.66 | -168.19 | 未完成 | 关闭锁盈释放噪音，2602明显恶化 |
| `dtp_revonly_pl60_50` | 未测 | 未测 | 未测 | -16.69 | 未测 | +7058.66 | -168.19 | +1180.58 | 提高锁盈启动线同样恶化2602/2411 |

结论：
- “锁盈过早”只是 2024-11 的表象，不是可泛化收益缺口根因。
- 放宽锁盈没有恢复后续结构利润，反而释放反向噪音；这说明低收益月仍应从入场结构质量解决，而不是风控阈值解决。
- 该方向停止，不进入全 24 月。

可证伪假设 I：D1 宽区间触边 + M5 延续确认可以把 2602 的 HTF OB 反弹抽象成低频补腿。

工程实验：
- 临时新增 `InpRangeTPTarget=2` 研究语义：Range fade 触边后复用 SWP 小周期延续确认，要求没有反向微结构破坏、没有强反向K，且 M5 净推进/强动能成立。
- 编译后代表月回测，随后撤回 EA 代码，保留候选和结果作为证伪记录。

代表月结果：

| 候选 | 2411 | 2505 | 2602 | 2605 | 交易数特征 | 结论 |
|---|---:|---:|---:|---:|---|---|
| `dtp_revonly_d1_range_react_m5` | -281.13 | -240.61 | -153.89 | -235.08 | 613-1254 笔/月 | 宽区间触边导致过度交易，M5延续确认不足以约束 |

结论：
- 用户提出的 2602 4270-4545 大周期 OB 反弹是真实有效样本，但不能用“宽 D1 区间触边 fade”直接泛化。
- 正确抽象应是：HTF OB/供需区边界触达后，先出现拒绝反应，再等待小周期结构突破/回踩或同向延续；禁止直接触边接刀。
- 下一步应复用/增强 BOS Retest 或 HTF Pullback 结构通道，而不是继续扩大 Range fade。

现有候选池筛查结论（2026-06-17）：
- 在已完成的 `v11xau-bd08-trendhold_*_vs_bd07_24m_*.csv` 中，2024-11 是当前最硬缺口。
- 现有候选在 2024-11 的最高收益来自 `doc_range_d1_confirm_follow`：+73.39，但该候选 2505 仅 +114.21、2605 -0.60，不能作为主腿或补腿直接叠加。
- 保住 2505/2605 的结构候选，例如 `lock3_20_fail_pos05_2_60_noclear_mbos_m1_struct_retest`，2024-11 仅 +3.97，2602 +1.56，虽 2505 +4518.30、2605 +1230.84，但无法补足全月 >=200 目标。
- HTF Pullback 与 MBOS 低频候选普遍无法修复 2602/2411：常见表现是 2602 -150 附近、2411 -70 附近，说明“结构突破”若没有高周期 OB 边界拒绝质量门，会在错误位置追入。

当前收敛判断：
- 已有候选线性组合最多只能接近目标，无法证明 24 月全 >=200；特别是 2024-11 没有足够正贡献来源。
- 下一步必须新增一个比 Range fade 更窄的补腿：`HTF OB/区间边界触达 -> 拒绝K线 -> M5/M15 结构突破 -> 回踩入场`。
- 该补腿的关键不是扩大频率，而是把 2602 这类“宽止损抓大周期利润”的经验转成低频信号；若交易数超过几十笔/月，应立即判定为过宽。

可证伪假设 J：只在 HTF 宽区间边界触达后生成 MicroBOS 回踩区，可以低频捕捉 2602 反弹且保住 2505/2605。

工程实验：
- 在 `WaiTrade3/WaiTrade_OB_SMC.mq5` 的 `AddMicroBOSZone` 前加入研究门控：`InpMicroBOSRequireZoneConfluence=true` 且 `InpMicroBOSConfluenceToleranceATR<0` 时，不再找普通 OB/FVG 共振，而要求最近 8 根小周期K线触达 `RangeDetector` 的 D1 宽区间上/下边界。
- 该逻辑只影响 MBOS zone 生成，不直接触边入场，也不覆盖主信号方向。

代表月结果：

| 候选 | 2411 | 2505 | 2602 | 2605 | 交易数 | 结论 |
|---|---:|---:|---:|---:|---|---|
| `mbos_m1_struct_retest_htfrange` | +3.97 | +3011.34 | +1.56 | +1193.55 | 10/245/29/48 | 保住目标月，但没有新增补腿收益 |
| `mbos_m5_struct_retest_htfrange` | +3.97 | +3011.34 | +1.56 | +1193.55 | 10/245/29/48 | 与 M1 完全一致，说明门控后剩主腿 |

结论：
- 仅用“最近低/高触达 HTF Range 边界”作为 MBOS 质量门过窄，无法捕捉 2602 的强拒绝反弹。
- 2602 的可用特征还缺一环：触达后必须识别拒绝K线/大引线，并在其后允许结构突破回踩；不能要求 BOS 本身发生在边界触达窗口内。
- 下一步应把“边界拒绝事件”持久化为短期状态，例如 `HTF_REJECT_READY{direction, boundary, time}`，随后 N 根 M5/M15 内的 MBOS 才允许入场。

后续验证（2026-06-17 夜）：
- 已实现并编译验证短期 `MICRO_BOS_HTF_REJECT` 事件：当小周期K线触达 HTF Range 上/下边界、收回区间内、且影线 >= max(实体, 0.20 ATR) 时记录拒绝方向；随后同方向 MicroBOS 可使用该事件通过 HTF 共振门。
- 2602 单月调试结果：`MICROBOS_SUMMARY detected=65 generated=37 skip_confluence=28 monitors=3228 confirmed=302 reject_finalize=294 executed=0`。说明“拒绝事件 -> MicroBOS 区域”已经生效，但普通 EntryEngine 最终过滤全部拦截。
- 临时尝试给 HTF 拒绝型 MicroBOS 加专属 Finalize：能够出现 `PASS_HTF_REJECT`，但下单链触发 `止损无效`/资金约束，2602 净值仍为 +1.56，交易数仍 29；该执行 fallback 已撤回。

结论修正：
- HTF Range 边界拒绝事件本身不是足够好的可交易补腿；它识别的边界过宽，且生成的 MicroBOS retest SL/entry 结构不适合直接市价执行。
- 用户给出的 2026-02-02 样本更接近“明确 HTF OB/未缓解供需区触达 + 大引线拒绝 + M5/M15 二次结构确认”，不是宽 RangeDetector 边界。
- 下一轮应新增独立 `HTF OB Reaction` 补腿，而不是继续扩大 MicroBOS：先检测 HTF OB/未缓解区（如 2026-01-25 至 2026-02-01 形成的 4270-4545 区间），触达后记录拒绝事件，再用 M5/M15 结构突破/回踩入场，并用 OB 外侧宽 SL 承接大周期利润。

可证伪假设 K：`HTF OB Reaction` 独立补腿可以低频捕捉大周期 OB 拒绝反弹，同时保住 2505/2605 主趋势。

工程实验：
- 新增 `InpRangeTPTarget=7` 研究语义：复用 RangeReaction 执行链，但不使用宽 RangeDetector 直接触边；改为扫描 D1 级冲动K前一根 OB，价格触达 OB 附近后，要求 M15 拒绝影线确认，再生成 `RGREACT` 补腿。
- `RGREACT` zone 标记为 `is_htf_pullback=true`，因此进入 `HTFPB` 信号族；后续窄化版本给该族跳过 `mfe_fail/no_mfe`，并用 HTF 专属 DTP 管理。
- 同时验证了一个反例：把“继续拿单”粗暴扩展到所有 `OB/SWP/REVSWP/HTFPB`，会使错单活太久，不能使用。

代表月结果：

| 候选 | 2411 | 2505 | 2602 | 2605 | 交易数特征 | 结论 |
|---|---:|---:|---:|---:|---|---|
| `dtp_revonly` | +2.11 | +7058.66 | -2.22 | +1180.58 | 16/504/53/127 | 稳定边界 |
| `htfob_react_m15` | +2.11 | +6284.74 | -1.37 | +1227.97 | 16/504/53/127 | 保住目标月，但 2602 改善太小 |
| `htfob_react_m15_hold_m5m15` | -99.73 | +2987.71 | -77.36 | -0.14 | 161/453/7/11 | 全局放宽 OB/SWP 出场失败 |
| `htfob_react_m15_htfhold` | +1.45 | +3846.37 | -2.18 | +1260.00 | 16/506/58/119 | 只放宽 HTFPB 安全，但未修复 2602 |
| `htfob_rejectctx_m15` | +1.45 | +629.76 | -4.43 | +1054.21 | 16/380/26/92 | Range拒绝上下文给普通单放宽出场，破坏2505 |
| `htfob_react_m15_htfhold` 去固定TP后 | +1.45 | +3828.69 | -2.18 | +1265.39 | 16/504/58/118 | RGREACT跑更远仅小幅改善2605 |

订单级观察：
- 2602 的 2026-02-02 反弹起点并非没有入场；05:00-05:21 连续出现多笔普通多单，方向正确，但多数在几秒到几分钟内被 `mfe_fail`、短止损或小 TP 切碎。
- `RGREACT` 在 2026-02-03 触发 3 笔，约 +62、+16、-17，说明 HTF OB 拒绝补腿本身有正贡献，但没有覆盖 2026-02-02 的核心反弹窗口。

结论：
- 2602 样本的主矛盾不是“没有入口”，而是“高周期需求区拒绝后的同向普通订单没有被识别成 HTF 反弹订单，因此按短线保护被切掉”。
- 下一步应记录一个持久化的 `HTF_REJECT_CONTEXT{direction, expires}`：一旦 D1/H4 区间边界或 HTF OB 出现拒绝K线，随后 N 根 M5/M15 内同向 `OB/SWP/REVSWP` 才可跳过秒级 MFE 失败退出，并启用严格 DTP；禁止全局放宽。

后续验证：
- 已实现 `HTF_REJECT_CONTEXT` 研究路径：`InpRangeTPTarget=7` 时，D1 Range 边界拒绝K线会记录方向上下文，随后窗口内同向普通订单会标记为 HTF 目标单、跳过 MFE/NoMFE，并强制严格 DTP。
- 结果显示 2505 被大幅破坏，2602 未改善；说明“宽 Range 边界拒绝上下文”仍不是用户描述的 2026-02-02 HTF OB。
- 同时修正 `RGREACT`：在 `InpRangeTPTarget=7` 下不再挂 Range 固定 TP，并确保监控路径设置 `htf_target=true`。该修正只让 2605 从 +1260.00 小幅到 +1265.39，对 2602 无效。

当前结论：
- 2602 的关键结构不是 RangeDetector 的 D1 宽区间边界，也不是简单冲动K前一根日线 OB；它更可能是多日复合供需区/未缓解区（用户描述的 2026-01-25 至 2026-02-01 形成区间 4270-4545），需要独立 HTF OB 库保存“多日横盘/冲动前区间”，而不是单K订单块。
- 当前可保留但不全量扩展的最小有益改动是 `htfob_react_m15`/`htfhold`：保住 2605>1000 和 2505>3000，但不解决 2602 和 24月全盈利目标。
- 下一轮应停止复用 RangeDetector，改为开发 `HTFCompositeOB`：D1/H4 多根K线横盘积累区 -> 后续冲动离开 -> 回踩触达 + 拒绝影线 -> M5/M15 二次确认；宽 SL 放在复合区外侧。

可证伪假设 L：复合 HTF OB（多根 D1 横盘积累区 + 冲动离开 + M15 拒绝影线）可以替代单根订单块，捕捉 2602 大周期需求区反弹。

工程实验：
- 在 `FindRecentHTFOBReactionZone` 中优先扫描 3-8 根 HTF K 线组成的复合区，要求后续冲动 K 离开区间；当前价回踩复合区边界附近后，M15 出现拒绝影线才生成 `RGREACT`。
- 去重距离从 M1 ATR 改为 `max(M1_ATR*0.5, range_height*0.15)`，避免同一复合区重复生成。
- `comp_safe_m15` 把补腿风险压到 `RangeMaxLot=0.01`，避免再次触发 3% 月亏损停手。

代表月结果：

| 候选 | 2411 | 2505 | 2602 | 2605 | 交易数特征 | 结论 |
|---|---:|---:|---:|---:|---|---|
| `htfob_comp_m15` | -1.99 | +1.22 | -17.55 | +1187.43 | 17/82/33/114 | 触发月亏损停手，2505主趋势被清空 |
| `htfob_comp_safe_m15` | +0.52 | +4469.01 | -3.58 | +1165.34 | 17/481/33/95 | 保住关键月，但2602仍劣于基线 |

订单级观察：
- `htfob_comp_m15` 在 2505 中于 2025-05-06 连续触发多笔 `RGREACT B` 小亏，单笔损失不大，但叠加早期回撤触发 3% 月亏损停手，导致后续主趋势利润没有释放。
- 降到 0.01 手后，2505 恢复到 +4469.01、2605 +1165.34，证明风险污染可控；但 2602 仍未改善，说明“多根横盘 + 冲动离开”的通用复合区仍没有识别用户描述的核心供需位。

结论：
- 2602 不能靠 RangeDetector、单根日线 OB、通用多根复合 OB 三种泛化形式解决。
- 用户描述的 4270-4545 更像“指定时间段形成的未缓解价格区间/大供需盒”，需要检测更大尺度的价格区间：起涨/起跌点到高低点、50%打折/溢价、未完整回踩区域，而不是只用冲动K前横盘。
- 下一步应构建 `HTFUnmitigatedZone`：从 H4/D1 大幅推进段中提取未缓解区间，等待首次/二次触达 + 拒绝影线，且只允许一次小仓补腿；这个比 `HTFCompositeOB` 更贴近文档中的“未缓解区域”和用户样本。

可证伪假设 M：HTF 未缓解供需区 + 小周期强拒绝影线，可以把 2602 的 2026-02-02 反弹转成可拿久的 HTF 持仓。

工程实验：
- 在 `FindRecentHTFOBReactionZone` 中新增 `HTFUnmitigatedZone` 扫描：从 D1 冲动离开前的多根基础区间提取未缓解区，要求当前 M15 确认 K 线触达该区间并用大影线收回。
- 新增候选 `htfuz_safe_m15`：`RangeTPTarget=7`、M15 确认、`RangeMaxLot=0.01`、宽 SL、HTF DTP=2.5/0.30，目标是只做低频补腿。
- 同步测试“HTF 拒绝上下文持仓”：当 `RangeTPTarget=7` 时，HTF 拒绝事件后同向普通 `OB/SWP` 可标记为 `htf_target`，跳过 `mfe_fail/no_mfe`，并取消固定 TP。为验证机制，还做过一次强制探针：所有普通 `OB/SWP` 都按 HTF 持仓处理。

代表月结果：

| 候选/探针 | 2411 | 2505 | 2602 | 2605 | 交易数特征 | 结论 |
|---|---:|---:|---:|---:|---|---|
| `htfuz_safe_m15` | +2.92 | +4641.37 | -4.16 | +1183.85 | 16/460/35/100 | 保住 2505/2605，但 2602 未改善 |
| `htfhold_probe_m15`（强制普通 OB/SWP 持仓） | 未跑 | 未跑 | -4.57 | 未跑 | 2602 27 笔 | 机制接上但收益变差，证伪“普通单全部拿久” |

订单级观察：
- `htfuz_safe_m15` 在 2026-02-02 14:13 后触发 4 笔 `RGREACT S`，合计小亏；它捕捉到的是反弹后的回落，不是 05:00 需求区反弹。
- 2026-02-02 05:00-05:21 的普通多单本身方向正确，基线第一笔 `B x0.9` 在 4672.569 入场，固定 TP 4686.558 出场 +28.27。
- 强制 HTF 持仓探针后，同一笔单取消 TP 后变为 4680.594 附近保护/结构出场 +15.70；同时 2026-02-03 的盈利空单从 +12.45/+2.94 变成 -0.21/-0.04。说明“拿久”本身不是收益来源，已有 TP 对部分短线优势是保护。

结论：
- 2602 的 2026-02-02 样本不是“没有入口”，也不是“所有同向单都应该一直拿”。真正需要识别的是：触达 HTF 需求区后，哪些订单已经形成小周期延续性，可以取消短线 TP/秒退；哪些只是普通短线优势，应该保留 TP。
- 简单取消固定 TP 或跳过 MFE 会释放更多亏损，不能进入 24 月全量回测。
- `HTFUnmitigatedZone` 当前版本可保留为研究代码，但不是有效候选；不应命名/部署为新版本。

下一步方向：
- 对持仓放宽增加“入场后延续确认”而不是“入场前上下文”：只有当持仓达到 0.8R-1.2R 后，M5/M15 仍同向净推进、没有反向结构突破、没有强反向大实体，才取消/延后 DTP；否则保留原 TP/MFE。
- 对 HTF 区域识别加入“折价/溢价 + 未缓解区首次触达”评分，避免反弹后中段追 `RGREACT S`。
- 2602 不应继续用月标签优化；后续验证必须用订单级特征分组：强拒绝影线、后续 M5/M15 净推进、反向结构突破、持仓 MFE 后延续性。

可证伪假设 N：只在 DTP 已触发后，若 M5/M15 仍同向延续、没有小周期反转和动能衰弱，才继续持仓，可以释放 2605 趋势利润且不破坏 2505。

工程实验：
- 不新增 EA 代码，复用已有 `InpDTPHoldOnContinuation`、`InpDTPExitRequireReverseContinuation`、`InpDTPExitRequireMomentumWeakness`。
- 候选一 `mfe_cont_m5m15`：只在 DTP 回撤出场点检查 M5/M15 同向延续，成立则继续持有；不取消固定 TP、不跳过 MFE。
- 候选二 `mfe_revweak_m5m15`：DTP 出场还必须看到反向结构延续和原方向动能衰弱。
- 候选三 `swp_revweak_m5m15`：只对 `SWP/REVSWP` 家族启用严格 DTP，普通 OB 保持原逻辑。

代表月结果：

| 候选 | 2411 | 2505 | 2602 | 2605 | 交易数特征 | 结论 |
|---|---:|---:|---:|---:|---|---|
| `dtp_revonly` 基线 | +2.11 | +7058.66 | -2.22 | +1180.58 | 16/504/53/127 | 当前稳定边界 |
| `mfe_cont_m5m15` | +1.45 | +6027.32 | -2.22 | +1172.02 | 16/483/32/92 | 保住目标月，但无增益 |
| `mfe_revweak_m5m15` | +2.82 | +2600.09 | -4.83 | +1455.49 | 29/406/31/92 | 2605增益明显，但2505跌破3000 |
| `swp_revweak_m5m15` | +2.42 | +2738.68 | -4.83 | +1483.66 | 26/405/31/95 | 2605最好，但2505仍不达标 |

结论：
- “DTP 出场必须等反转延续+动能衰弱”能提升 2605，但会压缩 2505 主趋势利润，说明该规则对趋势月和震荡反弹月的作用不稳定。
- 只限制到 `SWP/REVSWP` 仍无法保住 2505 >3000；该方向不能作为当前主策略，也不进入 24 月全量。
- 可用收敛点：`mfe_cont_m5m15` 是安全但无增益；`swp_revweak_m5m15` 是 2605 增益来源，可作为未来组合里的小权重补腿，但需要新的实时质量门避免伤害 2505。

下一步方向：
- 不再继续加严 DTP 出场；转向更窄的补腿入口质量，例如 `RGREACT/HTFPB` 只在折价/溢价、未缓解区首次触达、M5/M15 二次突破三者同时成立时入场。
- 若继续做持仓延长，应加“盈利保护下限”：保留已有固定 TP 或至少把 SL/保护位锁到不低于原 TP 的等价收益，避免 2602 第一笔从 +28.27 被拖成 +15.70。

可证伪假设 O：用户补充的 2026-02-02 大周期 OB/需求区反弹，不能用“宽 Range/HTF 拒绝上下文”直接泛化；更接近“普通 OB 方向正确，但后续 SWP/BOS 追价污染”的订单级问题。

订单级复核：
- `no_revswp` 全量 24 月结果：2505 +3011.08、2605 +1194.81、2602 +0.36；关键月达标，但低收益月份仍大量存在。
- 2602 最新 `no_revswp` 报告中，2026-02-02 05:00-05:21 连续普通 OB 多单合计约 +34；其中 05:00 第一笔 +28.27，05:09 一笔 +29.99。
- 同月按信号族拆分：OB 18 笔 +33.90 至 +41.67（不同候选口径略有差异），SWP 约 -25 到 -37，BOS -8.18。说明 2602 的亏损根因不是“没有抓反弹入口”，而是反弹后/错误位置的 SWP/BOS 污染。
- 用户描述的 4270-4545 大周期 OB 与当前报告中的实际成交价 4667-4673 不一致；该线索仍可作为“大周期需求区强拒绝”经验，但不能把当前回测订单直接映射为 4270-4545 触达。

工程实验：
- 增加 `InpRangeTPTarget=8` 研究语义：只记录 HTF 拒绝上下文，不创建直接 `HTRG/HTFOB` 新入口。
- `CfgRangeHTFRejectContextEnabled()` 允许普通 OB/SWP 在 HTF 拒绝上下文下取消固定 TP、跳过 MFE/NoMFE，并进入 HTF DTP；同时新增 `CfgRangeContextDetectorEnabled()`，试图把 Range 检测和 RangeFade 主信号改写解耦。
- 候选 `no_revswp_htfrej_ctx`：关闭 REVSWP + HTF 拒绝上下文 + M5/M15 延续/反转弱化出场。
- 候选 `no_revswp_htfrej_ctx_narrow`：只保留 HTF 拒绝上下文，不改变全局 DTP。

代表月结果：

| 候选 | 2505 | 2602 | 2605 | 交易数特征 | 结论 |
|---|---:|---:|---:|---|---|
| `no_revswp` | +3011.08 | +0.36 | +1194.81 | 247/30/49 | 当前关键月最小可用边界 |
| `no_revswp_htfrej_ctx`（全局严格 DTP） | +6.88 | -3.39 | +1471.48 | 89/31/49 | 2605 增益，但 2505 被持仓占用/出场改变破坏 |
| `no_revswp_htfrej_ctx_narrow` | +3011.08 | +0.36 | +1194.81 | 247/30/49 | 等同 no_revswp，说明 HTF 拒绝上下文未命中核心 2602 OB 单 |

结论：
- “普通 OB/SWP 在 HTF 拒绝后一直拿”被证伪；2602 第一笔原本 +28.27 的短 TP 是保护，不是问题。
- `InpRangeTPTarget=8` 的上下文检测代码可作为研究工具保留，但当前参数不提供收益；不能进入候选主线。
- 下一步应转向“SWP/BOS 质量门”：在大周期需求区强拒绝后，区分反弹初段的普通 OB 与反弹后追价 SWP/BOS。规则必须用实时特征，如小周期是否二次 BOS、是否已经远离折价区、SWP 是否与 H1/H4 净推进一致、是否出现强反向 K 线。

可证伪假设 P：普通 SWP 入场前要求 M5/M15 已产生同向延续，可以过滤 2602 反弹后的坏扫损单，同时保留 2505/2605 的趋势利润。

工程实验：
- 不新增 MQL，复用已有 `InpEnableSWPContinuationConfirm`。
- 候选 `no_revswp_swpcont_m5_block`：SWP 延续失败直接过滤。
- 候选 `no_revswp_swpcont_m15_block`：M15 延续失败直接过滤。
- 候选 `no_revswp_swpcont_m5_half` / `m15_half`：延续失败不拒单，仅仓位乘数 0.5。

代表月结果：

| 候选 | 2408 | 2411 | 2412 | 2503 | 2505 | 2602 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `no_revswp` | -1.08 | +2.50 | -1.27 | -0.64 | +3011.08 | +0.36 | +1194.81 | 关键月边界候选 |
| `swpcont_m5_block` | -6.03 | -11.62 | +60.51 | +2.88 | +446.77 | +3.63 | +899.77 | 过滤过强，砍掉趋势月有效 SWP |
| `swpcont_m15_block` | -12.85 | +2.66 | +42.91 | +3.71 | -15.30 | -1.91 | +1149.50 | 2505 被破坏 |
| `swpcont_m5_half` | +6.19 | -8.34 | +2.89 | +194.73 | +398.42 | -9.38 | +1036.92 | 降仓仍破坏 2505 |
| `swpcont_m15_half` | +87.88 | +12.32 | +137.80 | +2.25 | +2247.10 | -7.58 | +1078.27 | 最温和但 2505 仍低于 3000 |

订单级观察：
- 2505/2605 的 SWP 胜率并不高，但利润来自少数长持/大 R 单：2505 SWP 219 笔 +3033.13，最大单 +1050.61；2605 SWP 36 笔 +1263.28，最大单 +1090.36。
- 2602 的亏损也集中在 SWP，特别是 buy SWP：11 笔约 -25.36，最差为 2026-02-04 的 buy SWP -15.44/-8.22。
- SWP 延续确认降低了部分噪音，但它同样降低趋势月早期扫损试单的仓位或数量，因此不是稳定预测因子。

结论：
- “入场前已延续”不是 SWP 好坏的充分条件；有效 SWP 往往是在延续前的扫损反转点入场，过早要求延续会错失大 R。
- 对 SWP 的质量门应转向“位置”：HTF 折价/溢价、未缓解区首次触达、反弹是否已远离需求区，而不是全局小周期延续确认。
- 发现 MT5 硬限制：当前 EA input 已超上限，新增 6 个 SWP 折价/溢价参数后 Strategy Tester 报 `too many input parameters (1030)` 并无法启动。后续新增策略逻辑必须复用现有参数槽，或先清理旧实验 input；禁止继续直接增加 input。

下一步方向：
- 先不再新增 input。可尝试复用已有 `InpStrongSweepRequireDP/InpStrongSweepDPTF/InpStrongSweepDPLookbackBars/InpStrongSweepDiscountMax/InpStrongSweepPremiumMin` 作为普通 SWP DP 门控的研究开关，或清理废弃实验参数后再引入正式字段。
- 若复用现有 DP 参数，必须保证默认关闭、只在候选中启用，并用代表月先验证 2505 不低于 3000、2605 不低于 1000。

可证伪假设 Q：普通 SWP 如果不在 H1 折价/溢价半区，则更像反弹后追价污染；用 H1 DP 门控可保留 2605 大赢并减少 2602 噪音。

工程实验：
- 不新增 input，复用强扫反转的 DP 参数槽。
- 新增 `PassPlainSweepDPGate()`：仅当 `InpEnableStrongSweepReversal=false` 且 `InpStrongSweepUseStructureHold=true` 且 `InpStrongSweepRequireDP=true` 时，普通 SWP 调用 `PassStrongSweepDP()`。默认候选不受影响。
- 首次接入只覆盖直接 `ScanSignals` 路径，结果与基线完全一致；随后补接 `ExecuteChannelConfirmed` 的 EntryEngine 确认路径，门控才实际生效。

代表月结果（接入确认路径后）：

| 候选 | 2408 | 2411 | 2412 | 2503 | 2505 | 2602 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `no_revswp` | -1.08 | +2.50 | -1.27 | -0.64 | +3011.08 | +0.36 | +1194.81 | 关键月边界候选 |
| `swpdp_h1_50` | -26.65 | -31.76 | +265.25 | +1.86 | -32.84 | -3.75 | +1370.72 | 2605 改善，但 2505 被摧毁 |
| `swpdp_h1_4555` | -30.58 | -31.76 | +254.12 | +1.86 | -32.84 | -3.98 | +1370.72 | 更严格无额外收益 |

结论：
- H1 折价/溢价门控能提升 2605，但它过滤掉 2505 的关键 SWP 利润，不能作为主策略。
- 这说明趋势月的有效 SWP 并不总发生在短 H1 区间折价/溢价半区；用 H1 48 根局部区间会把趋势中段延续单误判为“不在价值区”。
- 用户给的 2602 大周期区间线索应使用更高周期/更长区间的“复合供需区”，不能用短 H1 DP 代替。

下一步方向：
- 保留 `PassPlainSweepDPGate()` 作为 opt-in 研究代码，但不进入全量候选。
- 若继续位置过滤，应使用 D1/H4 或明确的未缓解区间，而不是 H1 48 根局部高低点。
- 当前最接近目标的仍是 `no_revswp`：2505/2605 达标、2602 微利，但 24 月低收益问题未解决。

可证伪假设 R：2602 的大周期需求区强拒绝已经被普通 OB 捕捉，问题不是“没入场”而是强拒绝后的同区重复入场质量衰减；应把低峰值被动 SL/BE 也计入失败簇，并降低失败后同向重入阻断的仓位阈值。

用户补充结构线索：
- 2602 可关注 2026-02-02：下跌触及 2026-01-25 到 2026-02-01 形成的大周期 OB/需求区后快速反弹并拉出大下影线。
- 该线索被抽象为实时可观测结构：HTF 需求/供给区触达 + 强拒绝影线 + 后续同区重复入场质量衰减。没有使用月份标签或固定价位作为交易规则。

订单级复核：
- `no_revswp` 2602 复测：+0.36，30 笔。
- 2026-02-02 05:00-05:21 普通 OB 多单确实抓到反弹初段：第一笔 +28.27，05:09 一笔 +29.99；窗口内普通 OB 多单先盈利，随后 05:10-05:21 的 x0.5/x0.3 重复买入被 `mfe_fail/sl` 吃回利润。
- 15:13-15:22 后续 `SWP` 买入没有延续，继续小亏。说明首段反弹有效，后续追价/重复入场污染有效性下降。
- 现有 `fail_pos05_2_60` 未充分阻断该污染：它只记录主动失败，且只限制 `pos_mult>=0.5` 的同向重入；被动 SL/低峰值失败和 x0.3 重复单仍可能漏过。

工程实验：
- 不新增 EA input，复用现有失败重入参数。
- `failpos03`：`InpFailureReentryBlockMinPosMult=0.3`。
- `failpos03_passive`：在 `failpos03` 基础上启用 `InpFailureReentryRecordPassiveLoss=true`、`InpFailureReentryPassiveLossMaxPeakR=0.5`。
- `fail1_pos03`：连续失败阈值降为 1，验证是否过严。
- 同时复测 `mfe_fail`/`early_loss` 反手；结果显示反手不是主解，容易破坏趋势月。

代表月结果：

| 候选 | 2408 | 2412 | 2503 | 2505 | 2508 | 2601 | 2602 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `no_revswp` | -1.08 | -1.27 | -0.64 | +3011.08 | +0.33 | +2.63 | +0.36 | +0.67 | +1194.81 | 关键月边界，但低收益月多 |
| `rev_mfe025` | -5.18 | +163.52 | +4.60 | +4337.70 | -3.01 | +2.55 | -14.77 | +28.25 | +1149.31 | 反手增厚2505，但2602恶化 |
| `rev_early025` | -12.33 | +3.62 | +52.15 | +1038.22 | +253.52 | +386.68 | -10.20 | +7.70 | +938.33 | 抓部分震荡反弹，但破坏趋势月 |
| `failpos03` | -1.08 | -1.27 | +360.30 | +9809.58 | +214.10 | -0.66 | -4.19 | +0.58 | +1116.08 | 趋势月大幅改善，但2602仍负 |
| `failpos03_passive` | -2.79 | +301.20 | +283.82 | +4161.24 | +236.66 | -0.80 | +8.87 | +35.30 | +1183.69 | 当前最佳平衡，关键月达标 |
| `fail1_pos03` | -5.20 | -2.51 | +274.64 | +2090.06 | -0.73 | +404.17 | -8.95 | +0.58 | +1345.90 | 一次失败阻断过严，2505不达标 |

24 独立月全量（`failpos03_passive`）：

| 指标 | 结果 |
|---|---:|
| 累计净利润 | +71253.31 |
| 盈利月 | 22/24 |
| 2505 | +4161.24 |
| 2605 | +1183.69 |
| 2602 | +8.87 |
| 未盈利月 | 2024-08 -2.79、2026-01 -0.80 |
| 低于 200 的盈利月 | 2024-06 +39.29、2024-07 +41.86、2024-10 +3.21、2024-11 +0.23、2025-01 +145.99、2025-06 +6.21、2025-07 +62.31、2026-02 +8.87、2026-03 +16.53、2026-04 +35.30 |

结论：
- `failpos03_passive` 是比 `no_revswp` 更强的当前边界：关键月 2505/2605 达标，2602 转正，24 月盈利月 22/24。
- 它仍未满足“24 个独立月全部盈利且每月 >=200”。低收益月的根因不是单纯亏损污染，而是有效交易机会/仓位暴露不足；继续加过滤只会让这些月份更接近 0。
- 2026-02-02 的经验应沉淀为“强拒绝后重复入场衰减”的失败簇规则，而不是“HTF 触达后所有单一直拿”。固定 TP 在第一段反弹中仍是保护。
- 下一步要补 24 月目标，需要新增低风险补腿入口或动态仓位增厚，而不是继续过滤。候选方向：D1/H4 复合供需区首次触达后的单次小仓 `RGREACT`；或在 `failpos03_passive` 基线下，对 PF 高但交易数少的月份用实时特征触发小仓 HTF 边界反应。新增 input 前必须先清理 EA input 上限问题。

## 2026-06-18 低收益月订单族拆解与补腿验证

目标：继续吸收 2602 经验，同时满足新目标：2505 > 3000，2605 > 1000，24 个独立月每月 >= 200。

约束：
- 不按月份标签写规则；只用订单族、方向、小周期结构、动能、HTF 边界触达等实时可观测特征。
- 不再调 SL/TimeExit/Cooldown 这类 scalping 主干参数。
- 先用订单级统计提出假设，再用 MT5 CLI 回测代表月验证。

### 订单族统计

基线：`failpos03_passive`。

低收益月合计订单族：

| 家族/方向 | 笔数 | 净利 | 胜率 | AvgW | AvgL | 主要出场 | 结论 |
|---|---:|---:|---:|---:|---:|---|---|
| OB buy | 74 | -23.34 | 35.1% | 8.43 | -5.05 | sl/mfe_fail/tp/dtp | 低收益样本负，但不能全局降权 |
| OB sell | 66 | -15.49 | 27.3% | 8.92 | -3.67 | sl/mfe_fail/tp | 同上 |
| BOS sell | 1 | -8.18 | 0.0% | 0.00 | -8.18 | mfe_fail | 样本太少 |
| SWP sell | 184 | +21.25 | 20.1% | 11.92 | -2.92 | sl/mfe_fail/dtp/decay | 微正，依赖少数大赢 |
| SWP buy | 288 | +381.97 | 25.7% | 12.08 | -2.40 | sl/mfe_fail/dtp/decay | 低收益样本主要正贡献 |

关键月订单族：

| 月份 | 家族/方向 | 笔数 | 净利 | 最大单 | 结论 |
|---|---|---:|---:|---:|---|
| 2505 | SWP buy | 116 | +1739.12 | +465.87 | 趋势利润主来源之一 |
| 2505 | SWP sell | 146 | +1473.69 | +219.13 | 趋势利润主来源之一 |
| 2505 | OB sell | 25 | +534.78 | +220.53 | 普通 OB 也参与关键复利链 |
| 2505 | OB buy | 31 | +413.65 | +219.79 | 不能全局砍 OB |
| 2605 | SWP buy | 23 | +1201.62 | +1090.36 | 2605 主要靠少数 SWP 大单 |
| 2605 | OB buy | 9 | +96.89 | +68.01 | 辅助正贡献 |

诊断：
- 低收益月不是“全族负期望”。SWP 低胜率但盈亏比好，尤其 buy SWP 在低收益样本合计显著为正。
- 普通 OB 在低收益样本合计为负，但关键月 OB 正贡献且影响复利链，不能简单全局降权。
- 低收益月的核心仍是暴露不足和大赢稀疏，而不是某个家族稳定负期望。

### 假设 S：用小周期净推进做 SWP 仓位再分配

逻辑：如果小周期趋势没有反转且动能有延续，则 SWP 顺势增厚；若逆势/震荡则降权。

复用 `InpEnableLightRegimePosMult`，不新增 input。

代表月结果：

| 候选 | 2406 | 2408 | 2410 | 2411 | 2501 | 2505 | 2506 | 2507 | 2601 | 2602 | 2603 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `failpos03_passive` | +39.29 | -2.79 | +3.21 | +0.23 | +145.99 | +4161.24 | +6.21 | +62.31 | -0.80 | +8.87 | +16.53 | +35.30 | +1183.69 | 当前基线 |
| `lreg_m15_swp` | +68.35 | -15.72 | +170.04 | -14.14 | +53.70 | +253.65 | +69.11 | +201.98 | +1.44 | +8.87 | +40.11 | +0.84 | +1157.14 | 2505 被破坏，证伪 |
| `lreg_h1_swp` | -27.12 | -5.23 | +23.75 | +9.96 | +102.38 | +541.86 | +16.25 | +6.99 | +2.04 | -17.93 | +0.69 | -35.04 | +1365.42 | 2605 改善但 2505/2602 失败，证伪 |

结论：
- “入场时已出现 M15/H1 净推进”不是 SWP 好坏的充分条件。
- 2505 的有效 SWP 仍有大量发生在趋势发动前，强行用净推进仓位再分配会砍掉早期扫损试单。

### 假设 T：把强扫/HTF 边界反应微仓叠回当前基线

逻辑：用户 2602 线索对应“HTF 需求区触达 + 强拒绝影线”，但现有基线关闭了强扫反转补腿；尝试以微仓叠加，不改普通 OB/SWP 主干。

代表月结果：

| 候选 | 2406 | 2408 | 2410 | 2411 | 2501 | 2505 | 2506 | 2507 | 2601 | 2602 | 2603 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `ssweep_m1_micro` | +24.50 | +57.09 | +2.74 | +0.08 | +106.11 | +4845.08 | +1.29 | +59.80 | +1.79 | -5.40 | -100.74 | +3.21 | +1167.18 | 补 2408/2505，但污染 2602/2603 |
| `ssweep_m1_h1dp` | +10.16 | -0.94 | +0.87 | +45.14 | +147.34 | +2716.78 | +17.68 | +26.60 | -128.54 | -8.99 | -25.46 | +41.78 | +1166.83 | 严格 DP 仍不稳，2505 不达标 |

结论：
- “HTF 边界强拒绝”作为交易经验方向成立，但现有 strong sweep 实现太碎片化，高频噪音仍会污染。
- 不能直接把 `SSWEEP` 补腿叠回主策略；需要更高周期、更少触发、边界单次使用的复合供需区实现。

### 假设 U：普通 OB 全局降权

逻辑：低收益样本 OB 合计为负，降低普通 OB 仓位。

结果：

| 候选 | 2505 | 2602 | 2605 | 关键失败 |
|---|---:|---:|---:|---|
| `ob05` | +3.83 | -123.56 | +576.55 | 2505/2605 均不达标，2602 大幅恶化 |

结论：
- OB 在低收益样本中负期望，但关键趋势月的复利链依赖普通 OB，不能全局降权。
- 这再次说明低收益月不能靠全局家族过滤解决。

### 假设 V：MicroBOS 小周期结构突破回踩补腿

逻辑：使用小周期结构突破 + 回踩 + H4 对齐 + 延续确认，贴近“趋势没有反转且动能延续就继续拿/入场”的经验。

代表月结果：

| 候选 | 2406 | 2408 | 2410 | 2411 | 2501 | 2505 | 2506 | 2507 | 2601 | 2602 | 2603 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `mbos_m5_micro` | +39.29 | -2.79 | +3.21 | +0.23 | +145.99 | +4161.24 | +6.21 | +62.31 | -0.80 | +8.87 | +16.53 | +35.30 | +1183.69 | 等同基线，几乎未触发 |
| `mbos_m1_micro` | +31.22 | -2.79 | +59.24 | +0.23 | +132.41 | +5095.93 | +7.30 | +8.00 | +387.17 | +8.87 | +9.12 | +2.92 | +1183.61 | 局部有效，但低收益月仍大量不足 200 |

结论：
- MicroBOS 是当前比 strong sweep 更接近可用的补腿：能提高 2505、2601，并不破坏 2605/2602。
- 但它无法覆盖 2408、2411、2506、2507、2603、2604 等低收益样本，不能满足 24 月每月 >=200。
- 下一步若继续，应围绕 MicroBOS 做“结构级别持久化/更高周期 M5-M15 回踩”而不是 M1 高频化；M5 版本当前未触发，说明参数或检测方式过严。

### 当前收敛结论

- 当前最佳仍是 `failpos03_passive`：2505 +4161.24，2605 +1183.69，2602 +8.87，24 月 22/24 盈利。
- 目标尚未达成：仍有 2024-08、2026-01 负收益，多个月份 < 200。
- 已证伪：
  - 全局 SWP 小周期净推进仓位再分配。
  - 强扫补腿简单叠加。
  - 普通 OB 全局降权。
  - M5 MicroBOS 当前参数直接叠加。
- 可保留方向：
  - 2602 经验沉淀为“HTF 边界强拒绝后首段有效，后续同区重复追价衰减”，当前由 `failpos03_passive` 部分吸收。
  - 下一轮应做更少、更高周期、更持久的复合供需区/结构回踩入口；避免 M1 噪音补腿。

## 2026-06-18 续：HTF 回踩与结构持有验证

目标不变：2505 > 3000，2605 > 1000，24 个独立月每月 >= 200。

### 假设 W：HTFPullback 高周期净推进回踩小仓叠加

逻辑：不改变普通 OB/SWP 主干，只在 M15/H1 出现净推进后，等待回踩区触达，用小仓补“趋势发动后的回踩”。

代表月结果：

| 候选 | 2406 | 2408 | 2410 | 2411 | 2501 | 2505 | 2506 | 2507 | 2601 | 2602 | 2603 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `failpos03_passive` | +39.29 | -2.79 | +3.21 | +0.23 | +145.99 | +4161.24 | +6.21 | +62.31 | -0.80 | +8.87 | +16.53 | +35.30 | +1183.69 | 当前基线 |
| `htfpb_h1_micro` | -32.23 | -6.63 | +151.11 | -0.43 | +34.70 | +1314.08 | +5.93 | +1.02 | -0.80 | +8.87 | +10.23 | +2.74 | +1062.89 | 2505/低收益失败 |
| `htfpb_m15_micro` | +16.47 | FAIL | +187.24 | -2.67 | +122.47 | +842.59 | +7.93 | +12.06 | +378.53 | -3.00 | +11.39 | -6.91 | +1113.97 | 2505失败且2408失败 |

结论：
- 现有 HTFPullback 入口是“净推进后回踩区”，不是用户 2602 所说的“大周期未缓解 OB 首次触达拒绝”。
- 叠加后会改变持仓序列/占用主链，2505 明显退化，不能作为当前主线。

### 假设 X：MicroBOS 结构持有，只在小周期未反转且动能未衰弱时继续拿

逻辑：沿用用户要求的出场经验。只对 MicroBOS 结构单启用结构 SL 和动态释放：有 M5/M15 反向结构/强反向 K 且达到最小浮盈后才恢复普通出场。

代表月结果：

| 候选 | 2406 | 2408 | 2410 | 2411 | 2501 | 2505 | 2506 | 2507 | 2601 | 2602 | 2603 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `mbos_m1_hold` | +57.65 | -1.85 | -4.60 | +0.23 | +160.83 | +9464.58 | +428.27 | +7.86 | +1.79 | +86.45 | +5.58 | +28.68 | -1.56 | 2505/2506/2602改善，但2605关键失败 |
| `mbos_m1_hold_m15q` | +48.57 | -1.85 | -4.60 | +0.23 | +159.52 | +4891.54 | +229.15 | +7.86 | +1.79 | -14.49 | +14.57 | +0.94 | -1.61 | 2505/2506改善，但2605关键失败 |
| `mbos_m1_hold_nomfeexit` | - | -2.79 | -4.60 | - | - | +10142.68 | +495.76 | - | +1.79 | -15.10 | - | - | -1.56 | 不跳过MFE仍无法恢复2605 |

2605 订单级复核：
- 基线 `failpos03_passive`：48 笔，+1183.69；核心为 2026-05-07 15:42 的 SWP buy +1090.36。
- `mbos_m1_hold`：21 笔，-1.56；同一 2026-05-07 SWP buy 变为 -8.84，且月内没有大赢。
- `mbos_m1_hold_m15q` 与 `hold` 订单结构几乎一致。

结论：
- 结构持有方向确实能吃到部分趋势利润：2505 和 2506 明显增强，2602 在 M5 质量版也增强。
- 但它会改变 2605 的持仓序列，错过或破坏原本的 SWP 大赢链；这不是 `InpStructSkipMFEExits` 单独造成的。
- 因此现有结构持有不能直接用于主策略。若继续，需要做更局部的工程约束：例如只给 MBOS 自己启用结构持有且不占用主策略 SWP 入口，或限制结构持有最大持仓/最大并发隔离。当前不满足目标。

补充复核：
- 尝试新增 `InpMicroBOSIsolateConcurrency` 会让 EA input 数达到 1025，MT5 Tester 报 `too many input parameters (1025)`；当前 EA 已在 1024 上限，不能再通过新增 input 扩展研究开关。
- 改为在 `InpMicroBOSUseStructureHold=true` 时自动隔离 MBOS 并发后，`mbos_m1_hold_iso` 的 2605 仍为 -1.56，和 `mbos_m1_hold` 逐笔一致，说明“共享 max_concurrent 占槽”不是主因。
- 2605 订单级差异：基线 2026-05-05 01:01 普通 buy x0.4 从 4527.694 一直持有到 2026-05-08 12:09，+1090.36；结构持有分支同一普通单在 2026-05-05 01:45 被 `time` 出场，只赚 +54.09。破坏点不是 MBOS 大单本身，而是 MicroBOS/结构参数改变了运行状态序列后，普通趋势单没被标记为结构持仓，仍被 TimeExit 截断。
- 不启用结构持仓的 `mbos_m1_micro` 复核：2505 +5095.93，2605 +1183.61，2602 +8.87；关键月达标，但低收益月仍未解决（2408 -2.79，2603 +9.12，2604 +2.92）。

### 假设 Y：TimeExit 延续保护与 HTF OB 边界反应组合

目标：不让普通趋势单在小周期仍顺向推进时被 `time` 截断，同时吸收用户提出的 2602 大周期 OB 强拒绝经验。

代表月结果：

| 候选 | 2408 | 2505 | 2602 | 2603 | 2604 | 2605 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---|
| `mbos_m1_micro` | -2.79 | +5095.93 | +8.87 | +9.12 | +2.92 | +1183.61 | 关键月达标，低收益月失败 |
| `mbos_m1_timehold_m5m15` | -2.79 | +2554.90 | +8.87 | +9.12 | +32.07 | +1175.10 | 保护2605但2505跌破3000 |
| `mbos_m1_timehold_obswp_strict` | +18.16 | +85.11 | +8.87 | -65.02 | -37.97 | +1147.98 | 全局OB/SWP TimeExit保护破坏短线获利结构 |
| `mbos_m1_htfob_react` | +2.51 | +3931.09 | +8.87 | +0.89 | -60.63 | +1240.29 | 关键月达标，但2604转负，低收益月仍失败 |

结论：
- TimeExit 延续保护不能全局作用到普通 OB/SWP；它会改变大量短线盈利链，尤其 2505 被严重压低。
- HTF OB/D1边界反应能轻微改善 2605 和部分边界月，但仍无法解决 2602；且会破坏 2604。
- 用户 2602 的 4270-4545 大周期 OB 强拒绝经验，不能用宽泛 D1 区间反应替代。需要更精确的实时特征：首次触达未缓解 HTF OB + 强拒绝影线 + 后续同区重复触达降权/不追，而不是持续加仓或全局 TimeExit 保护。
- 当前最稳的关键月达标候选仍是 `mbos_m1_micro`；它满足 2505/2605，但仍不满足 24月每月 >=200。

### 当前状态

- 仍未达成目标。
- 当前可交付的最佳候选仍是 `failpos03_passive`，但 24 月每月 >= 200 未满足。
- 新一轮证伪：
  - `HTFPullback` 现有实现叠加。
  - `MicroBOS` 结构持有直接叠加。
- 下一步如果继续代码改造，应考虑“隔离式结构补腿”：结构单单独并发/单独计数，不占用或不改变普通 OB/SWP 主链；否则 2605 大赢链容易被破坏。

## 2026-06-18 续：2602 大周期 OB 触达与宽止损验证

用户补充结构线索：
- 2026-02-02 下跌触及 2025-12~2026-01 形成的大周期需求/OB 区间，约 4270-4545，随后立刻反弹并拉出大引线。
- 若 M1 入场噪音太多，可提高到 M5/M15 并放宽止损，抓大周期利润。

订单级事实（当前可信基线 `failpos03_passive`，MT5 Real Ticks）：
- 2602 并不是完全没入场。2026-02-02 07:09:10 在 4550.472 附近开 buy，订单 SL 4543.591；2026-02-02 07:09:28 被 SL 扫掉，亏 -21.08。
- 该位置正处在用户给出的 4270-4545 大周期需求区上沿附近。之后同日 15:13 又在 4704/4696 附近出现小仓 buy SWP，但均被 MFE/短线机制切掉。
- 因此 2602 根因不是“缺少入场”，而是“大周期 OB 边界触达用 M1 普通 SL/短线出场处理”，导致边界扫损噪音先把单打掉。

代表验证：

| 候选/改动 | 2505 | 2602 | 2605 | 结论 |
|---|---:|---:|---:|---|
| `failpos03_passive` 当前复核 | +4161.24 | +8.87 | +1183.69 | 当前可信关键月基线 |
| `lock3_20` 当前复核 | +592.34 | +1.56 | +1257.32 | 与旧 CSV 漂移，不能再当关键月基线 |
| `lock3_20_mbos_m1_micro` | +1122.27 | +1.56 | +1259.19 | 2605可，2505失败 |
| `lock3_20_htfob_react_m15` | +878.62 | +1.24 | +1420.98 | RGREACT 过多，2505失败 |
| `lock3_20_wide_htf_range_m15` | -7.08 | -57.34 | -2.10 | 宽 RangeFade 全局过滤破坏主链 |
| `failpos03_passive_htfreject_ctx_m15` | +4308.44 | +8.87 | +1191.41 | 关键月保住，但未触发 2602 宽SL |
| `failpos03_passive_htfreject_ctx_m5`（近极值放宽） | - | -122.44 | - | 触发过宽，交易数 8→64，证伪 |

工程结论：
- `RangeFade/HTFOBReaction` 不能直接叠加：会生成大量 `RGREACT` 小单并改变主链，2505 从 +4161 降到 +878 或更低。
- “近多日极值即宽 SL”过宽，会把大量普通低点附近买入都升级成宽风险单，2602 直接变 -122.44。
- 更可取的下一步不是扩大触发范围，而是更精确识别：**首次触达未缓解 HTF OB + 已收盘 M5/M15 强拒绝 + 下一次回踩入场**。这比“触达当下直接放宽”更慢，但可避免 2602 这类下跌中的早接飞刀。
- 当前代码里已加入但证伪的研究路径应保持 opt-in：`RangeTPTarget=8` 作为上下文开关，默认不影响普通策略；不要把近极值 fallback 作为主线。

### 2026-06-18 补充：2602 大周期 OB 上沿触达不能用宽泛上下文吸收

用户新增订单级结构线索：
- 2026-02-02 下跌触及 2025-12~2026-01 形成的宽需求/OB 区间 4270-4545，上沿触达后快速反弹并拉出大引线。
- 这类场景若用 M1 普通窄 SL，会在大周期 OB 上沿被 tick/影线噪音先扫掉；但如果“近极值/宽区间”全局放宽，又会污染普通趋势月。

本轮实现与验证：
- 在 `WaiTrade_OB_SMC.mq5` 增加了 HTF 拒绝上下文的高低点/ATR/一次性使用状态，并尝试对 OB/SWP 普通信号做 `HTRJ` 宽 SL 升级。
- 尝试把 `RangeTPTarget=8` 接入 `FindRecentHTFOBReactionZone()`：能让 HTF OB 扫描参与上下文，但在 2505/2605 触发过宽，污染普通 SWP 链。
- 尝试“多日基地区 live-touch”后，2505 出现大量 `HTRJ x0`，结果从关键月达标退化为 +614，2605 退化为 -32.53，已证伪。
- 已回退 target=8 的直接接线和普通信号升级调用，保留不影响主链的上下文基础函数。

代表结果：

| 候选/状态 | 2505 | 2602 | 2605 | 结论 |
|---|---:|---:|---:|---|
| `htfreject_ctx_m5` live-touch 误触发版 | +614.05 | +9.57 | -32.53 | `HTRJ` 污染 SWP 主链，证伪 |
| `htfreject_ctx_m5` 回退后 | +3578.48 | +8.87 | -26.22 | M5 上下文仍破坏 2605，不可用 |
| `htfreject_ctx_m15` 回退后 | +4036.37 | +8.87 | +1191.37 | 关键月达标但未改善2602 |

订单级结论：
- 2602 的 07:09 buy 仍是普通 `B x0.9`，没有 `HTRJ`，说明当前 HTFRange/HTFOBReaction 检测没有识别出 4270-4545 这种宽大周期需求区。
- 不能继续通过放宽 `RangeBoundaryToleranceATR`、`RangeMaxWidthATR`、近极值触发来覆盖 2602；这些会在 2505/2605 把大量普通 SWP/OB 误升级，破坏趋势利润链。
- 下一步应独立重建 D1/H4 供需区检测：用“多周基地区 + 明确离开 + 首次回踩上沿/下沿 + 低频一次性事件”离线标注，再接入策略；不能复用当前 RangeFade/HTFOBReaction 的交易通道。

### 2026-06-18 补充：2602 4270-4545 区间离线标注与强 sweep 证伪

新增研究工具：
- `mql5/Experts/Research/ExportRatesCSV.mq5`：通过 MT5 Strategy Tester/Real Ticks 环境导出 D1/H4/H1/M15/M5 OHLC CSV。注意这是数据导出，不是策略回测。
- `scripts/export_mt5_rates.py`：运行导出 EA 并收集 CSV 到 `results/research/rates/`。
- `scripts/analyze_htf_ob_reactions.py`：离线标注 D1/H4 供需区触达反应；这是离线标注/模拟，不是 MT5 回测。

离线标注事实：
- 用户给出的 `2025.12.01..2026.01.31 / 4270-4545 / 需求区` 在 2026-02-02 05:45 首次触达，M15 触达 K 的拒绝分数高。
- 触达后 1/3/10/20 天顺向空间约 `+307/+542/+570/+570` 点，最大逆向约 `147` 点；这确实是大周期需求区强拒绝。
- 自动 D1/H4 标注同时发现大量相反供给/需求重叠区：2505 有 32 个事件，2602 有 48 个事件，2605 有 65 个事件。结论是“任意 HTF OB 触达”不可交易，必须加首触/未缓解/方向一致/小周期确认。

MT5 验证与证伪：

| 改动 | 2505 | 2602 | 2605 | 结论 |
|---|---:|---:|---:|---|
| `htfreject_ctx_m15` 当前稳定基线 | +4036.37 | +8.87 | +1191.37 | 关键月达标，2602未改善 |
| `htfob_swp_d1_m5`：强 sweep + D1 HTF OB 门控 | +4308.25 | -3.64 | -1.72 | 新入口污染/占用，2605关键月失败 |
| `htfob_swp_d1_m5` + 持仓触达升级尝试 | +4308.25 | -3.64 | -1.72 | 结果完全不变，升级路径未触发有效订单 |

订单级复核：
- 2026-02-02 05:00-05:09 多笔 buy 已经快速获利约 +68；系统并非没有识别反弹。
- 2026-02-02 07:09:10 在 4550.472 buy，SL 4543.591，18 秒后被 SL 扫掉，亏 -21.08；这笔正处于 4270-4545 大需求区上沿。
- 之后 15:13/15:14/15:35 的 SWP buy 都是 0.01 小仓，被 MFE/DTP 切碎，无法吃到大周期趋势利润。

结论：
- 2602 的主要问题不是缺入口，而是“上沿首触时用普通窄 SL + MFE/DTP 短线退出处理大周期需求区”。
- 强 sweep 新入口即使用 D1 OB 门控，也无法修复 2602，且会把 2605 从 +1191 打到接近 0，不能作为主线。
- 当前 EA input 已接近/达到 MT5 1024 上限；新增 8 个 strong_sweep_htf_ob 参数曾触发 `too many input parameters (1032)`，后已改为零新增 input 的内部门控。后续不能再靠新增 input 做研究开关。
- 下一步可证伪方向：不是新增入场，而是在已有普通 buy/sell 进入 HTF 首触区后，动态切换到“宽结构 SL + 只在 M5/M15 反向结构突破且反向延续时退出”。这需要真实 HTF OB 首触状态机，而不是 RangeFade 或 StrongSweep 交易通道。
