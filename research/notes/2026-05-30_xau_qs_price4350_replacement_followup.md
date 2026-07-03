# XAU QS: `price >= 4350` 替代条件复盘

日期: 2026-05-30
窗口: XAUUSDm, deposit 200, MT5 Model 4

## 问题

`price >= 4350` 在 2026-04-29 ~ 2026-05-29 的 30 天窗口里近似等于常开开关，能救近期 QS 亏损，但本质是绝对价位条件。它依赖当前样本所在的金价区间，后视镜过强，不能作为最终策略条件。

## 更合理的替代方向

`4350` 真正想表达的不是价格数字，而是:

- 行情进入高位扩张/高波动区域；
- 小账户阶段需要防止宽订单块和点差噪音把止损刺穿；
- 防守不能在真正趋势段长期常开，否则会截断 QS 的主要复利段。

因此优先测试了三类非后视镜条件:

1. 月内亏损触发: 只用当前账户和当月已发生盈亏。
2. 入场质量触发: `risk/ATR` 与 `risk/spread`，下单前可见。
3. 滚动高位触发: 当前价位处于历史滚动区间上沿，而不是固定绝对价。

## 关键结果

### 30 天基线

- `v11xau-qs`: 189 笔，胜率 38.6%，余额 45.71。

### 月内亏损触发

- `v11xau-qs-monthloss-core-vsl2-l025-t1-m220`: 160 笔，胜率 51.9%，余额 176.97。
- `v11xau-qs-monthloss-core-vsl2-l050-t1-m220`: 164 笔，胜率 51.2%，余额 178.26。
- `v11xau-qs-monthloss-core-vsl2-l100-t2-m220`: 161 笔，胜率 50.3%，余额 177.84。
- `v11xau-qs-monthloss-obvsl-re2-l025-t1-m220`: 26 笔，胜率 50.0%，余额 196.67。

结论: 亏损触发太晚，最伤账户的交易已经在开关启动前发生。

### 全局入场质量触发

- `v11xau-qs-lowbal-core-vsl2-ratr065-220`: 30 天 212.86；180 天 1191.48。
- `v11xau-qs-lowbal-core-vsl2-ratr075-220`: 30 天 213.62；180 天 1506.08。
- `v11xau-qs-lowbal-core-vsl2-spr4-220`: 30 天 213.27；180 天 950.88。
- `v11xau-qs-lowbal-core-vsl2-ratr075-spr4-220`: 30 天 210.97；180 天 1022.27。

结论: `risk/ATR` 是目前最有解释力的非后视镜替代，能显著修复最近 30 天，但全局使用会误伤 180 天的 2025-12 主利润段。

### 防守态入场质量触发

新增 EA 参数: `defensive_max_risk_atr`，仅在防守态启用最大 `risk/ATR`。

- `v11xau-qs-defrisk-core-vsl2-ratr065-220`: 30 天 211.32；180 天 1445.69。
- `v11xau-qs-defrisk-core-vsl2-ratr075-220`: 30 天 214.12；180 天 1407.22。
- `v11xau-qs-defrisk-core-vsl2-ratr085-220`: 30 天 213.07；180 天 1474.84。
- `v11xau-qs-defrisk-core-vsl2-ratr075-215`: 30 天 207.04；180 天 1362.24。
- `v11xau-qs-defrisk-core-vsl2-ratr075-210`: 30 天 199.27。
- `v11xau-qs-defrisk-core-vsl2-ratr075-205`: 30 天 194.80。

结论: 防守态 `risk/ATR` 比绝对价格条件干净，也比全局限制语义更正确，但仍未保住 180 天 QS 基线 2396.58，不能 promoted。

### 滚动高位触发

- `v11xau-qs-rollhi-lowbal-core-vsl2-d90p80-220`: 30 天 44.23。
- `v11xau-qs-rollhi-lowbal-core-vsl2-d90p90-220`: 30 天 44.23。
- `v11xau-qs-rollhi-lowbal-core-vsl2-d180p80-220`: 30 天 44.23。
- `v11xau-qs-rollhi-lowbal-core-vsl2-d180p90-220`: 30 天 44.23。

结论: 当前 tester 窗口里，D1 长回看滚动区间未能有效触发/区分，暂不作为候选。

## 当前判断

`price >= 4350` 的最佳替代候选不是另一个价格，而是:

> 小账户防守态 + 入场订单块风险质量，尤其 `risk/ATR <= 0.75`。

但它还不是 QS 改进版。原因是 180 天主要利润来自 2025-12 的小账户启动复利段，而任何低余额防守都会与这段行情冲突。下一轮应转向“识别小账户启动时是否处于高密度顺风趋势”，例如近期成交/信号密度、最近 N 笔同向质量、或启动后前几笔的 MFE/胜负反馈，而不是单纯低余额常开防守。

## 验证

- `python -m pytest tests\test_mt5_common.py -q`: 89 passed。
- `python scripts\mt5_compile_win.py --mt5-home temp\mt5_tester_isolated --mt5-data temp\mt5_tester_isolated --log-dir temp\compile_win_isolated`: success, warnings 0。
- `python scripts\mt5_compile_win.py --mt5-home temp\mt5_tester_isolated --mt5-data C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\8B9AA56FE80DC787002685F3915FED97 --log-dir temp\compile_win_isolated_appdata`: success, warnings 0。
