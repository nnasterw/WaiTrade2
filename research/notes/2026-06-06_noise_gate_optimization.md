# QS3+NOISE 噪音门控优化研究 — 2026-06-06

## 背景

目标：优化QS3+NOISE，使2505（好月）盈利不退化且2605（坏月）盈利。
方法：wf-analyze-cl 工作流 — Phase 1逐笔特征诊断 → Phase 2可证伪假说 → Phase 3回测验证。
规模：5轮110+次 Model 4 Real Ticks 回测 + 580万行EA日志逐笔分析。

## 核心发现

### D1: RangeATR是噪音门控唯一有效参数

MinDirRatio在2605零边际效应（97笔不变），Lookback仅次要影响2505交易量。
RangeATR直接控制过滤强度：a≤0.14→2605盈利(W=65%)，a≥0.18→2605亏损(W=49%)。

### D2: BE保本锁是震荡市杀手

分析出2605的DTP触发率仅5.8%（2505为21.3%）。当价格偏移不足时，BE触发后
剩余仓位被反转止损吃掉，造成净亏损。**关闭BE(BE=0)+降低DTP(1.5R→1.0R)是2605盈利的关键。**

### D3: 2605根本问题是价格偏移幅度不足

| 指标 | 2505 | 2605 | 倍差 |
|:---|---:|---:|:---|
| avg_W | $22.98 | $1.07 | 21x |
| avg_L | $22.60 | $1.72 | 13x |
| DTP触发率 | 21.3% | 5.8% | 3.7x |
| SL率 | 53.6% | 83.3% | 1.6x |
| 连亏后WR | 54.6% | 35.6% | 下降显著 |

2605市场跑不到DTP触发位，83%交易被止损。亏损有动量——亏损后WR从47%暴跌至35%。

### D4: 两月市场结构根本不同，静态参数无法同时最优

通过EA日志逐笔特征分析（bounce_sec, bounce_ob, position_mult, confirm_pos等）发现：

- bounce_sec<5s: 2505=WR59.8%/$+1,939, 2605=WR36.7%/-$32（**完全相反**）
- position_mult x1.4(默认主力): 2505=WR53.4%/$+1,450, 2605=WR36.0%/-$22（**完全相反**）
- 几乎所有实时可观测特征在两月中呈**相反相关性**

### D5: 信号强度评分在2605失效

position_mult x0.8在两月都高WR(2505=63.6%, 2605=66.7%)，但x1.4（55%交易量）在2605惨败。
信号强度评分在趋势市有效，在震荡市反向——需要自适应调整。

## 最优配置

| 优先级 | 配置 | 2505 | 2605 | Net | 适用 |
|:---:|:---|---:|---:|---:|:---|
| P0 | H5+LOOSE(lb10/r20/a25,DTP=1R,BE=0,SL=0.5) | +$8,153 | -$100 | +$8,053 | 极致利润 |
| P1 | H5+AD-LOOSE(dd3% a25→a16,SL=0.4) | +$5,964 | -$66 | +$5,898 | 最佳平衡 |
| P2 | H5+AD(dd3% a22→a16,SL=0.5) | +$1,954 | +$18 | +$1,972 | 2605正收益 |
| REF | QS3 OFF(原始) | +$4,532 | -$199 | +$4,333 | 基准 |

## 参数配方 (P1 H5+AD-LOOSE)

```
噪音门控:           H5出口机制:
InpEnableTickNoiseGate=true    InpDTPTriggerR=1.0
InpEnableDynamicSpread=true    InpDTPRetrace=0.20
InpTickNoiseGateLookback=10    InpBreakevenR=0.0  ← BE关闭
InpTickNoiseGateMinDirRatio=0.20  InpBreakevenLockR=0.0
InpTickNoiseGateMaxRangeATR=0.25

自适应:            风控:
InpAdaptiveNoiseDrawdownPct=3.0   InpSLBufferATR=0.4
InpAdaptiveNoiseDefMinDirRatio=0.30  InpMaxPosMult=2.0
InpAdaptiveNoiseDefMaxRangeATR=0.16
InpAdaptiveNoiseRecoveryPct=1.0
```

## 改进方向

1. **自适应仓位乘数**（本期实现）：防守态降低BoostIn1HOB和DeepEntryBoost，
   因EA日志显示低乘数(x0.6-0.9)在两月均高WR，x1.4在2605集中亏损。

2. **连亏条件冷卻**：2605亏损后WR从47%暴跌至35%，需要连亏N笔后暂停交易。
   现有CooldownBars是全局的，M1上无效（交易平均间隔62bars）。

3. **信号强度评分自适应**：需修改OB评分公式，在震荡体制中降低权重。

## 回测记录

5轮总计110+次MT5 Model 4 Real Ticks回测：
- Round 1: 噪声门控甜点扫描 (36 BT)
- Round 2: 自适应噪声门控验证 (10 BT)
- Round 3: 自适应宽松正常态 (12 BT)
- Round 4: 出口机制假说验证 (12 BT)
- Round 5: 最终组合+冷卻+SL缓冲+Boost (38 BT)
- Extra: Phase 2出口假说, Last Mile (22 BT)
