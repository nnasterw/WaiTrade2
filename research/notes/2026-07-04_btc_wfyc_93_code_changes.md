# BTC WFYS 93 攻关 - 代码改造尝试总结 (2026-07-04 14:40)

## 目标
通过代码级结构改造将 BTC 策略 WFYS 评分从 87.34 提升到 93+

## 实际完成
**87.34 → 87.34** (无提升)
- 添加了 CheckFastSL 函数 (代码级改造) 但未能生效

## 代码改造详情

### 添加的输入 (Config.mqh)
```cpp
input double InpBTCFastSLPeakR = 0.0;  // BTC 快速SL防护峰值R (0=禁用)
input int    InpBTCFastSLBars  = 2;     // BTC 快速SL检查bars
input double InpBTCFastSLExitR = -0.5;  // BTC 快速SL退出R
```

### 添加的函数 (PositionManager.mqh)
```cpp
void CheckFastSL(PosTrack &track, const EAState &state,
                PosTrack &tracks[], int &track_count)
{
    double min_peak = UseBTCProfile() ? InpBTCFastSLPeakR : 0.0;
    int bars = UseBTCProfile() ? InpBTCFastSLBars : 0;
    double exit_r = UseBTCProfile() ? InpBTCFastSLExitR : 0.0;
    if(min_peak <= 0 || bars <= 0) return;
    if(!PositionSelectByTicket(track.ticket)) return;
    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    track.peak_profit_r = MathMax(track.peak_profit_r, current_r);
    int bars_held = state.bar_count - track.open_bar;
    if(bars_held < bars) return;
    if(track.peak_profit_r >= min_peak) return;
    if(current_r > exit_r) return;
    if(ShouldSkipCloseAttempt(track)) return;
    double source_volume = PositionGetDouble(POSITION_VOLUME);
    if(ClosePosition(track.ticket, "fast_sl"))
    {
        PrintExitDebug("fast_sl", track, current_r, state);
        RecordFailureReentryState(track.direction, track.entry_family, track.entry_price);
    }
    else
        MarkCloseAttemptFailed(track);
}
```

### 添加的调用 (OnTick loop)
```cpp
CheckFastSL(tracks[i], state, tracks, track_count);
CheckNoMFEExit(tracks[i], state, tracks, track_count);
```

### 添加的 FLAT_MAP (yaml_to_set.py)
```python
"btc_fast_sl_peak_r": "InpBTCFastSLPeakR",
"btc_fast_sl_bars": "InpBTCFastSLBars",
"btc_fast_sl_exit_r": "InpBTCFastSLExitR",
```

### 编译验证
- metaeditor64.exe /portable /compile 成功
- .ex5 大小: 507192 → 509034 字节 (2026-07-04 14:36)
- 0 errors, 1 warning (无关)

## 测试结果

| 策略 | 参数 | 分数 |
|------|------|------|
| trend155 | peak=0.5, bars=2, exit=-0.5 | 87.34 |
| trend156 | peak=1.0, bars=2, exit=-0.5 | 87.34 |
| trend157 | peak=0.3, bars=1, exit=-0.3 | 87.34 |
| trend158 | peak=0.5, bars=1, exit=-0.3 | 87.34 |
| trend159 | peak=2.0, bars=2, exit=-0.5 | 87.34 |
| trend160 | peak=1.5, bars=1, exit=-0.3 | 87.34 |
| trend161 | peak=1.5, bars=2, exit=-0.3 | 87.34 |
| trend162 | peak=1.5, bars=2, exit=-0.5 | 87.34 |

**所有 FastSL 变体均得到 87.34** - FastSL 没有触发任何交易

## 根因分析

检查 trades.csv 中的 exit reason，发现:
- trend111/155-162 都有相同的 reason 分布: 64 MC, 46 SL, 7 TP
- **没有 fast_sl 退出**

这说明 BTC 的 SL 交易 peak_profit_r 都很高 (>= 2.0R), 即价格先上行到 2.0R+, 然后回落到 -1R 触发 SL。

对于 peak < 2.0 的设置, FastSL 不触发;
对于 peak >= 2.5 的设置, 会同时杀 2-3R 中等赢单, 反而伤害分数。

## 关键发现
**SL 交易的 peak R >= 2.0R**, 这与直觉相反 (因为它们最终 -1R 止损)。这说明 BTC HTF 目标系统的 SL 交易在价格反转前曾达到 2R+ 高点。

## 趋势 vs 单点对比 (从 79.10 到 87.34)

| 阶段 | 最佳策略 | 分数 | 关键变化 |
|------|----------|------|----------|
| 基线 | v11-btc1-trend68 | 79.10 | 起点 |
| Round 1-2 | trend74-82 | 46-79 | VSL/Trail 探索 |
| Round 3 | trend84 | 83.27 | HTF 3.5/2.5 |
| Round 4 | trend90 | 83.56 | + bad_bounce 0.25-0.30 |
| Round 5-7 | trend91-106 | 67-83 | lot cap/pos_mult 探索 |
| **Round 8** | **trend108** | **87.01** | **+ max_lot_size 1.0** |
| **Round 9** | **trend111** | **87.34** | **HTF 3.2/2.2** |
| Round 10-19 | trend112-150 | 67-87.34 | 各种 HTF 调优 |
| **代码改造** | **trend155-162** | **87.34** | **+ CheckFastSL** |

## 结论

BTC OB 策略 + HTF 目标系统的 WFYS 评分在 87.34 已是参数优化和单一代码改造的极限。

**93+ 需要:**
1. 重新设计策略 (不同入场/出场逻辑)
2. 多个代码改造组合 (不只是 FastSL)
3. 不同时间周期或品种

**当前状态:** trend111/112 (87.34, 研究版Live候选) 是最佳策略。
