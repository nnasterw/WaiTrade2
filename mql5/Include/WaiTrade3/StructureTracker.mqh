// WaiTrade3 StructureTracker — 市场结构跟踪（BOS/CHOCH）
// 基于道氏理论：HH/HL → 多头, LH/LL → 空头
#ifndef __STRUCTURE_TRACKER_MQH__
#define __STRUCTURE_TRACKER_MQH__

#include <WaiTrade3/TypesSMC.mqh>
#include <WaiTrade3/ConfigSMC.mqh>

// ── 检测3-bar pivot ──
bool IsSwingHighV3(const MqlRates &rates[], int i, int bars)
{
    if(i < bars || i >= ArraySize(rates) - bars) return false;
    double mid_high = rates[i].high;
    for(int b = 1; b <= bars; b++)
    {
        if(rates[i - b].high >= mid_high) return false;
        if(rates[i + b].high >= mid_high) return false;
    }
    return true;
}

bool IsSwingLowV3(const MqlRates &rates[], int i, int bars)
{
    if(i < bars || i >= ArraySize(rates) - bars) return false;
    double mid_low = rates[i].low;
    for(int b = 1; b <= bars; b++)
    {
        if(rates[i - b].low <= mid_low) return false;
        if(rates[i + b].low <= mid_low) return false;
    }
    return true;
}

// ── 向swing点数组添加 ──
void AddSwingPointV3(SMCSwingPoint &points[], int &count, double price, datetime time,
                   SMCSwingPointType type, int bar_index)
{
    if(count >= MAX_SWING_POINTS)
    {
        // 移除最旧的，平移
        for(int i = 1; i < count; i++)
            points[i - 1] = points[i];
        count--;
    }
    points[count].price = price;
    points[count].time = time;
    points[count].type = type;
    points[count].strength = SWING_STRONG;
    points[count].bar_index = bar_index;
    points[count].broken = false;
    points[count].break_price = 0;
    points[count].break_time = 0;
    count++;
}

// ── 更新swing点强度（突破检查） ──
void UpdateSwingPointsV3(SMCSwingPoint &points[], int &count, double current_high,
                       double current_low, int current_bar)
{
    for(int i = 0; i < count; i++)
    {
        if(points[i].broken) continue;

        bool broken = false;
        if(points[i].type == SWING_HIGH && current_high > points[i].price)
            broken = true;
        else if(points[i].type == SWING_LOW && current_low < points[i].price)
            broken = true;

        if(broken)
        {
            points[i].broken = true;
            points[i].strength = SWING_BROKEN;
            points[i].break_price = (points[i].type == SWING_HIGH) ? current_high : current_low;
            points[i].break_time = TimeCurrent();
        }
    }
}

// ── 从swing点判断趋势状态 ──
TrendState DetermineTrend(const SMCSwingPoint &points[], int count)
{
    if(count < 4) return TREND_UNKNOWN;  // 至少需要2个high + 2个low

    // 找最近的swing high和swing low
    double last_hh1 = 0, last_hh2 = 0;  // 最近的两个高点
    double last_hl1 = 0, last_hl2 = 0;  // 最近的两个低点
    int h_count = 0, l_count = 0;

    for(int i = count - 1; i >= 0 && (h_count < 2 || l_count < 2); i--)
    {
        if(points[i].type == SWING_HIGH && h_count < 2)
        {
            if(h_count == 0) last_hh1 = points[i].price;
            else last_hh2 = points[i].price;
            h_count++;
        }
        if(points[i].type == SWING_LOW && l_count < 2)
        {
            if(l_count == 0) last_hl1 = points[i].price;
            else last_hl2 = points[i].price;
            l_count++;
        }
    }

    if(h_count < 2 || l_count < 2) return TREND_UNKNOWN;

    // 多头: HH + HL (高点更高 + 低点更高)
    bool bullish = (last_hh1 > last_hh2) && (last_hl1 > last_hl2);
    // 空头: LH + LL (高点更低 + 低点更低)
    bool bearish = (last_hh1 < last_hh2) && (last_hl1 < last_hl2);

    if(bullish) return TREND_BULLISH;
    if(bearish) return TREND_BEARISH;

    // 混合 → 震荡
    return TREND_CHOP;
}

// ── 趋势强度计算 (0.0=无趋势, 1.0=极强趋势) ──
// 用于区分"可靠回调"(强趋势逆势) vs "趋势延续"(弱趋势逆势)
double CalcTrendStrength(const SMCSwingPoint &points[], int count, TrendState trend)
{
    if(trend == TREND_UNKNOWN || trend == TREND_CHOP) return 0.0;
    if(count < 4) return 0.0;

    // 1. 连续确认的趋势 swing 对数
    int confirming_pairs = 0;
    double prev_h = 0, prev_l = 0;
    bool first = true;

    for(int i = count - 1; i >= 1; i--)
    {
        if(points[i].broken) continue;
        if(trend == TREND_BULLISH && points[i].type == SWING_HIGH)
        {
            if(first) { prev_h = points[i].price; first = false; continue; }
            if(points[i].price > prev_h) { confirming_pairs++; prev_h = points[i].price; }
            else break;
        }
        if(trend == TREND_BEARISH && points[i].type == SWING_LOW)
        {
            if(first) { prev_l = points[i].price; first = false; continue; }
            if(points[i].price < prev_l) { confirming_pairs++; prev_l = points[i].price; }
            else break;
        }
    }

    // 2. 归一化: 5对以上 = 满分
    double pair_score = MathMin((double)confirming_pairs / 5.0, 1.0);

    // 3. 最近 swing 的幅度 (相对合理范围)
    // 有足够 swing 时才计算
    double amplitude_score = 0.5; // 默认中等
    if(confirming_pairs >= 2)
    {
        // 找最近两个同向 swing 的距离
        double dist = 0;
        int found = 0;
        double last_price = 0;
        for(int i = count - 1; i >= 0 && found < 2; i--)
        {
            if(points[i].broken) continue;
            if((trend == TREND_BULLISH && points[i].type == SWING_HIGH) ||
               (trend == TREND_BEARISH && points[i].type == SWING_LOW))
            {
                if(found == 0) { last_price = points[i].price; found++; }
                else { dist = MathAbs(points[i].price - last_price); found++; }
            }
        }
        // 距离合理(不是过小震荡也不是过大跳空) = 趋势健康
        // 这里只是相对度量，实际ATR校准在调用方
        if(dist > 0) amplitude_score = 0.7;
    }

    return pair_score * 0.6 + amplitude_score * 0.4;
}

// ── 检测BOS（结构突破） ──
// BOS = 同方向结构的延续突破
// - 多头BOS: 当前HL被跌破 → 但趋势仍可能延续
// - 空头BOS: 当前LH被突破 → 但趋势仍可能延续
StructureSignal DetectBOS(const SMCSwingPoint &points[], int count,
                          TrendState current_trend, double current_close)
{
    if(count < 3) return SIG_NONE;
    if(current_trend != TREND_BULLISH && current_trend != TREND_BEARISH)
        return SIG_NONE;

    // 找最近未被突破的swing low（多头检查）
    if(current_trend == TREND_BULLISH)
    {
        double recent_hl = 0;
        for(int i = count - 1; i >= 0; i--)
        {
            if(points[i].type == SWING_LOW && !points[i].broken)
            {
                if(InpStructureRequireClose)
                {
                    if(current_close < points[i].price)
                        return SIG_BOS_BULL;
                }
                else
                {
                    return SIG_BOS_BULL;
                }
                break;
            }
        }
    }

    // 空头：找最近未被突破的swing high
    if(current_trend == TREND_BEARISH)
    {
        for(int i = count - 1; i >= 0; i--)
        {
            if(points[i].type == SWING_HIGH && !points[i].broken)
            {
                if(InpStructureRequireClose)
                {
                    if(current_close > points[i].price)
                        return SIG_BOS_BEAR;
                }
                else
                {
                    return SIG_BOS_BEAR;
                }
                break;
            }
        }
    }

    return SIG_NONE;
}

// ── 检测CHOCH（趋势转换） ──
// CHOCH = 趋势反转
// - 多转空: 更低的低点(LH) + 更低的高点(LL) → 前一个bullish结构被破坏
// - 空转多: 更高的高点(HH) + 更高的低点(HL) → 前一个bearish结构被破坏
StructureSignal DetectCHOCH(const SMCSwingPoint &points[], int count,
                            TrendState previous_trend)
{
    if(count < 4) return SIG_NONE;

    double h1 = 0, h2 = 0, l1 = 0, l2 = 0;
    int hc = 0, lc = 0;

    for(int i = count - 1; i >= 0 && (hc < 2 || lc < 2); i--)
    {
        if(points[i].type == SWING_HIGH && hc < 2)
        {
            if(hc == 0) h1 = points[i].price; else h2 = points[i].price;
            hc++;
        }
        if(points[i].type == SWING_LOW && lc < 2)
        {
            if(lc == 0) l1 = points[i].price; else l2 = points[i].price;
            lc++;
        }
    }

    if(hc < 2 || lc < 2) return SIG_NONE;

    // 多转空: 之前bullish → 现在出现 LH + LL
    if(previous_trend == TREND_BULLISH && h1 < h2 && l1 < l2)
        return SIG_CHOCH_BEAR;

    // 空转多: 之前bearish → 现在出现 HH + HL
    if(previous_trend == TREND_BEARISH && h1 > h2 && l1 > l2)
        return SIG_CHOCH_BULL;

    return SIG_NONE;
}

// ── 判断方向是否和趋势一致 ──
bool IsDirectionAlignedWithTrend(int direction, TrendState trend)
{
    if(trend == TREND_BULLISH && direction == OB_BUY) return true;
    if(trend == TREND_BEARISH && direction == OB_SELL) return true;
    if(trend == TREND_CHOP || trend == TREND_UNKNOWN) return true; // 震荡/未知→允许
    return false; // 逆势
}

// ── 主更新函数（新bar调用） ──
// trend_state 会被更新; structure_signal 输出 BOS/CHOCH 信号
void UpdateStructureTracker(const MqlRates &rates[], int copied,
                            SMCSwingPoint &points[], int &point_count,
                            TrendState &trend_state, EAState &state,
                            int &structure_signal)
{
    if(!InpEnableStructureTracker) return;

    int pivot_bars = InpStructurePivotBars;
    if(pivot_bars < 1) pivot_bars = 1;
    int lookback = MathMin(InpStructureLookbackBars, copied - pivot_bars - 1);

    // 扫描新swing points
    for(int i = copied - lookback; i < copied - pivot_bars; i++)
    {
        if(i < pivot_bars || i >= copied - pivot_bars) continue;

        if(IsSwingHighV3(rates, i, pivot_bars))
        {
            AddSwingPointV3(points, point_count, rates[i].high, rates[i].time,
                         SWING_HIGH, state.bar_count - (copied - 1 - i));
        }
        if(IsSwingLowV3(rates, i, pivot_bars))
        {
            AddSwingPointV3(points, point_count, rates[i].low, rates[i].time,
                         SWING_LOW, state.bar_count - (copied - 1 - i));
        }
    }

    // 更新swing点强度（突破检查）
    if(point_count > 0)
    {
        UpdateSwingPointsV3(points, point_count,
                         rates[copied - 1].high, rates[copied - 1].low,
                         state.bar_count);
    }

    // 保存旧趋势
    TrendState old_trend = trend_state;

    // 重新计算趋势（使用工作TF的swing points）
    trend_state = DetermineTrend(points, point_count);

    // 如果配置了HTF趋势周期，用HTF重新计算趋势覆盖工作TF结果
    int trend_tf_min = InpStructureTrendTF;
    if(trend_tf_min > 0)
    {
        ENUM_TIMEFRAMES trend_tf = (ENUM_TIMEFRAMES)CfgMinutesToTF(trend_tf_min);
        int trend_len = MathMin(InpStructureTrendLookback, 200);
        MqlRates trend_rates[];
        int trend_copied = CopyRates(_Symbol, trend_tf, 0, trend_len, trend_rates);
        if(trend_copied >= 20)
        {
            // 在HTF上重新检测swing points for trend
            SMCSwingPoint htf_points[MAX_SWING_POINTS];
            int htf_count = 0;
            int htf_pivot = MathMin(InpStructurePivotBars, 3);
            for(int ti = htf_pivot; ti < trend_copied - htf_pivot; ti++)
            {
                if(IsSwingHighV3(trend_rates, ti, htf_pivot))
                    AddSwingPointV3(htf_points, htf_count, trend_rates[ti].high, trend_rates[ti].time, SWING_HIGH, 0);
                if(IsSwingLowV3(trend_rates, ti, htf_pivot))
                    AddSwingPointV3(htf_points, htf_count, trend_rates[ti].low, trend_rates[ti].time, SWING_LOW, 0);
            }
            if(htf_count >= 4)
                trend_state = DetermineTrend(htf_points, htf_count);
        }
    }

    // 检测BOS和CHOCH

    // 检测BOS和CHOCH
    StructureSignal bos = DetectBOS(points, point_count, trend_state, rates[copied - 1].close);
    StructureSignal choch = DetectCHOCH(points, point_count, old_trend);

    // 将信号存储供SignalEngine使用
    structure_signal = SIG_NONE;
    if(bos != SIG_NONE || choch != SIG_NONE)
    {
        structure_signal = (choch != SIG_NONE) ? choch : bos;
        // CHOCH是更强信号
        if(choch != SIG_NONE && InpStructureLogBOS)
            Print("[SMC] CHOCH: ", EnumToString(choch),
                  " 趋势: ", EnumToString(old_trend), "→", EnumToString(trend_state));
        else if(bos != SIG_NONE && InpStructureLogBOS)
            Print("[SMC] BOS: ", EnumToString(bos),
                  " 趋势: ", EnumToString(trend_state));
    }

    // 趋势变化日志
    if(old_trend != trend_state && InpStructureLogBOS)
        Print("[SMC] 趋势变化: ", EnumToString(old_trend), "→", EnumToString(trend_state));
}

// ── H4 大周期趋势检测 (用于HTF结构确认) ──
TrendState DetectH4Trend(string symbol, int pivot_bars = 3, int lookback = 60)
{
    MqlRates h4_rates[];
    int copied = CopyRates(symbol, PERIOD_H4, 0, lookback, h4_rates);
    if(copied < 20) return TREND_UNKNOWN;

    SMCSwingPoint h4_points[MAX_SWING_POINTS];
    int h4_count = 0;
    int h4_pivot = MathMin(pivot_bars, 3);

    for(int i = h4_pivot; i < copied - h4_pivot; i++)
    {
        if(IsSwingHighV3(h4_rates, i, h4_pivot))
            AddSwingPointV3(h4_points, h4_count, h4_rates[i].high, h4_rates[i].time,
                          SWING_HIGH, 0);
        if(IsSwingLowV3(h4_rates, i, h4_pivot))
            AddSwingPointV3(h4_points, h4_count, h4_rates[i].low, h4_rates[i].time,
                          SWING_LOW, 0);
    }

    if(h4_count < 4) return TREND_UNKNOWN;
    return DetermineTrend(h4_points, h4_count);
}

#endif
