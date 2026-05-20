# V10 Hybrid 策略回测结果

日期: 2026-05-20
品种: XAUUSDm
初始资金: $200 | 杠杆: 1:2000 | Model 4 Real Ticks

## 设计思路

Hybrid系列 = FAGE入场质量过滤 + RANGE出场保护

- **FAGE提供**: structure_break + 坏簇OB过滤(age40-79/non_deep) + BH1方向降权
- **RANGE提供**: 宽SL(0.2-0.3ATR) + BE锁定 + DTP/TP + time_exit

## 180天回测（2025.11.21~2026.05.20，含趋势+震荡）

| # | 策略 | 交易 | 日均 | WR | PF | 余额 | 核心配置 |
|---|------|------|------|-----|-----|------|----------|
| 1 | **v10a** | 654 | 3.6 | 46.6% | 0.53 | **$6566** | 无过滤纯OB(复利最高) |
| 2 | **hybrid_c** | 786 | 4.4 | 57.9% | 0.91 | **$5449** | FAGE+SL0.2+DTP3/r25+nomfe |
| 3 | fage_dtp7_r15_bh1 | 586 | 3.3 | 70.6% | 1.99 | $5311 | FAGE+DTP7(质量最高) |
| 4 | hybrid_a | 773 | 4.3 | 58.5% | 1.03 | $4104 | FAGE+SL0.2+DTP2/r30 |
| 5 | hybrid_i | 809 | 4.5 | 57.7% | 1.14 | $3429 | FAGE+SL0.3+TP1R |

## 2345月回测（2026.02.20~2026.05.20，纯震荡期89天）

| # | 策略 | 交易 | 日均 | WR | PF | 余额 | 盈亏 |
|---|------|------|------|-----|-----|------|------|
| 1 | **hybrid_i** | 334 | 3.8 | 59.0% | 1.25 | **$411** | +$211 |
| 2 | hybrid_a | 327 | 3.7 | 58.4% | 1.24 | $374 | +$174 |
| 3 | hybrid_c | 349 | 3.9 | 57.0% | 1.04 | $354 | +$154 |
| 4 | hybrid_k | 326 | 3.7 | 59.2% | 1.06 | $263 | +$63 |
| 5 | hybrid_l | 325 | 3.7 | 59.7% | 1.05 | $250 | +$50 |
| 6 | hybrid_h | 309 | 3.5 | 58.9% | 1.19 | $248 | +$48 |
| 7 | hybrid_d | 327 | 3.7 | 59.9% | 1.06 | $243 | +$43 |
| 8 | hybrid_p | 335 | 3.8 | 60.0% | 0.43 | $241 | +$41 |
| 9 | hybrid_b | 323 | 3.6 | 59.8% | 1.04 | $233 | +$33 |
| 10 | hybrid_f | 302 | 3.4 | 60.9% | 1.06 | $296 | +$96 |
| 11 | hybrid_n | 332 | 3.7 | 59.6% | 1.10 | $191 | -$9 |
| 12 | hybrid_g | 310 | 3.5 | 61.9% | 1.15 | $192 | -$8 |
| 13 | fage_dtp7_r15_bh1 | 240 | 2.7 | 66.2% | 1.11 | $144 | -$56 |
| 14 | hybrid_j | 297 | 3.3 | 60.9% | 1.03 | $132 | -$68 |
| 15 | hybrid_e | 339 | 3.8 | 58.1% | 0.87 | $132 | -$68 |
| 16 | v10a | 216 | 2.4 | 37.5% | 0.47 | $93 | -$107 |
| 17 | hybrid_m | 156 | 1.8 | 66.0% | 0.92 | $91 | -$109 |
| 18 | hybrid_o | 293 | 3.3 | 67.9% | 0.85 | $67 | -$133 |

## 策略配方详情

### v10a（180天冠军 $6566）
- 无过滤纯OB，M1框架
- 趋势月暴利（复利），震荡月巨亏（-54%）
- 适合：能承受大回撤+趋势主导期

### hybrid_c（180天亚军 $5449 + 震荡期保本）
```yaml
filter_cont_age_min_bars: 40
filter_cont_age_max_bars: 79
filter_cont_non_deep_only: true
filter_buy_no_h1_pos_mult: 0.40
sl_buffer_atr: 0.20
max_concurrent: 4
breakeven_r: 0.50
breakeven_lock_r: 0.40
dtp_trigger_r: 3.0
dtp_retrace: 0.25
no_mfe_exit_bars: 5
no_mfe_min_peak_r: 0.3
no_mfe_exit_r: -0.2
time_exit_bars: 30
```

### fage_dtp7_r15_bh1（质量最高 WR70.6%/PF1.99）
```yaml
filter_cont_age_min_bars: 40
filter_cont_age_max_bars: 79
filter_cont_non_deep_only: true
filter_buy_no_h1_pos_mult: 0.40
sl_buffer_atr: 0.15
max_concurrent: 4
breakeven_r: 0.25
breakeven_lock_r: 0.08
dtp_trigger_r: 7.0
dtp_retrace: 0.15
time_exit_bars: 30
```

### hybrid_i（震荡月冠军 $411）
```yaml
filter_cont_age_min_bars: 40
filter_cont_age_max_bars: 79
filter_cont_non_deep_only: true
filter_buy_no_h1_pos_mult: 0.40
sl_buffer_atr: 0.30         # 宽SL防liquidity sweep
max_concurrent: 5
breakeven_r: 0.50
breakeven_lock_r: 0.40
fixed_tp_r: 1.0             # 固定1R止盈(range内可达)
dtp_trigger_r: 0.0          # 不用DTP
time_exit_bars: 20
```

## 关键发现

1. **趋势 vs 震荡的结构性矛盾**：DTP高(3-7R)抓大赢→趋势月暴利，但震荡月几乎不触发→亏损。TP1R在range内快速收割→震荡月盈利，但限制趋势月上限。

2. **宽SL(0.3ATR)是震荡期生存关键**：SL0.2 vs SL0.3在震荡月差距显著（hybrid_h $248 vs hybrid_i $411），因BTC/XAU震荡期频繁liquidity sweep扫窄止损。

3. **FAGE过滤是必需品**：hybrid_e(无FAGE)亏$68 vs hybrid_d(有FAGE)+$43，入场质量对PF的贡献约+0.2。

4. **BE参数敏感**：BE0.3锁0.2(hybrid_o)虽然WR68%但PF仅0.85 — 低BE让太多单锁在微利后被time_exit清出。

5. **Risk5%在PF<1.5时适得其反**：hybrid_f(risk5%)反而不如hybrid_a(risk2%)，因为PF~1.2时大仓位放大回撤速度>放大收益。

6. **Partial exit不适合震荡**：hybrid_p(1R平50%+DTP2) PF仅0.43，因震荡期剩余仓位几乎必定被清。

7. **时段过滤降低频率但不提高质量**：hybrid_m(仅London/NY)日均仅1.8单且亏损 — OB在所有时段生成质量相似。

## 推荐组合

| 场景 | 策略 | 预期 |
|------|------|------|
| 追求最高绝对收益 | v10a | 180天+3183%，需承受震荡期-54% |
| 稳定曲线+高质量 | fage_dtp7_r15_bh1 | WR70%/PF2，趋势月+2556% |
| 全周期兼顾 | hybrid_c | 180天+2625%，震荡期+77% |
| 震荡期专用 | hybrid_i | 震荡89天+106%，180天+1615% |

## BTC测试结论

所有v10/hybrid策略在BTC上全军覆没（60天和365天均爆仓）。根因：M1框架的OB risk仅3-5点，BTC spread/risk=6-10%，结构性亏损。BTC需要独立的M30框架+SL1.5ATR+BE2R重新设计。
