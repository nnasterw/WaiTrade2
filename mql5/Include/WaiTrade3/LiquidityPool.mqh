// WaiTrade3 LiquidityPool — 流动性池检测
// 双顶/双底、历史高低点 sweep 识别
#ifndef __LIQUIDITY_POOL_MQH__
#define __LIQUIDITY_POOL_MQH__

#include <WaiTrade3/TypesSMC.mqh>
#include <WaiTrade3/ConfigSMC.mqh>
#include <WaiTrade3/StructureTracker.mqh>  // for IsSwingHigh/IsSwingLow

// ── 检测双顶/双底 ──
// 找两个相近高度的swing high / swing low
void DetectDoubleTopBottom(const MqlRates &rates[], int copied,
                           LiquidityPool &pools[], int &pool_count,
                           int lookback_bars)
{
    int start = copied - lookback_bars;
    if(start < 3) start = 3;

    double sim_pct = InpLPSwingHighSimilarityPct / 100.0; // 0.2% → 0.002
    double min_range = InpLPMinRangeATR;

    // 扫描swing high对（双顶）
    for(int i = start; i < copied - 2; i++)
    {
        if(!IsSwingHighV3(rates, i, 1)) continue;

        for(int j = i + 2; j < copied - 1; j++)
        {
            if(!IsSwingHighV3(rates, j, 1)) continue;

            double diff_pct = MathAbs(rates[i].high - rates[j].high) / rates[i].high;
            if(diff_pct > sim_pct) continue;

            // 找到双顶 — 在pool中注册
            if(pool_count >= MAX_LIQUIDITY_POOLS) break;

            double range_high = MathMax(rates[i].high, rates[j].high);
            double range_low  = MathMin(rates[i].low, rates[j].low);

            pools[pool_count].type = LP_DOUBLE_TOP_BOTTOM;
            pools[pool_count].level = range_high;           // 上方诱多区域
            pools[pool_count].range_high = range_high;
            pools[pool_count].range_low = range_low;
            pools[pool_count].similarity_pct = diff_pct * 100;
            pools[pool_count].formed_time = rates[j].time;
            pools[pool_count].swept = false;
            pools[pool_count].active = true;
            pool_count++;
            break; // 每个i只找一次
        }
    }

    // 扫描swing low对（双底）
    for(int i = start; i < copied - 2; i++)
    {
        if(!IsSwingLowV3(rates, i, 1)) continue;

        for(int j = i + 2; j < copied - 1; j++)
        {
            if(!IsSwingLowV3(rates, j, 1)) continue;

            double diff_pct = MathAbs(rates[i].low - rates[j].low) / rates[i].low;
            if(diff_pct > sim_pct) continue;

            if(pool_count >= MAX_LIQUIDITY_POOLS) break;

            double range_high = MathMax(rates[i].high, rates[j].high);
            double range_low  = MathMin(rates[i].low, rates[j].low);

            pools[pool_count].type = LP_DOUBLE_TOP_BOTTOM;
            pools[pool_count].level = range_low;            // 下方诱空区域
            pools[pool_count].range_high = range_high;
            pools[pool_count].range_low = range_low;
            pools[pool_count].similarity_pct = diff_pct * 100;
            pools[pool_count].formed_time = rates[j].time;
            pools[pool_count].swept = false;
            pools[pool_count].active = true;
            pool_count++;
            break;
        }
    }
}

// ── 检测历史高低点 sweep ──
// 找前N根K线内的最高/最低 → 如果当前K线突破后收盘回撤 → liquidity sweep
void DetectSwingHighLowSweep(const MqlRates &rates[], int copied,
                             LiquidityPool &pools[], int &pool_count,
                             int lookback_bars)
{
    int start = copied - lookback_bars;
    if(start < 2) start = 2;

    double range_high = rates[start].high;
    double range_low  = rates[start].low;
    int high_bar = start, low_bar = start;

    // 找区间最高最低
    for(int i = start; i < copied; i++)
    {
        if(rates[i].high > range_high) { range_high = rates[i].high; high_bar = i; }
        if(rates[i].low  < range_low)  { range_low  = rates[i].low;  low_bar  = i; }
    }

    int last = copied - 1;

    // 检测最高点sweep: 突破前高后收盘回落
    if(high_bar < last && rates[last].high > range_high
       && rates[last].close < range_high)
    {
        if(pool_count < MAX_LIQUIDITY_POOLS)
        {
            double min_points = InpLPMinSweepDistancePoints * _Point;
            if(rates[last].high - range_high >= min_points)
            {
                pools[pool_count].type = LP_SWING_HIGH_LOW;
                pools[pool_count].level = range_high;
                pools[pool_count].formed_time = rates[last].time;
                pools[pool_count].swept = true;
                pools[pool_count].sweep_time = rates[last].time;
                pools[pool_count].sweep_distance = (rates[last].high - range_high) / _Point;
                pools[pool_count].active = true;
                pool_count++;
                if(InpLPLogDetection)
                    Print("[LP] 高点Sweep: level=", range_high,
                          " dist=", pools[pool_count-1].sweep_distance, "pts");
            }
        }
    }

    // 检测最低点sweep
    if(low_bar < last && rates[last].low < range_low
       && rates[last].close > range_low)
    {
        if(pool_count < MAX_LIQUIDITY_POOLS)
        {
            double min_points = InpLPMinSweepDistancePoints * _Point;
            if(range_low - rates[last].low >= min_points)
            {
                pools[pool_count].type = LP_SWING_HIGH_LOW;
                pools[pool_count].level = range_low;
                pools[pool_count].formed_time = rates[last].time;
                pools[pool_count].swept = true;
                pools[pool_count].sweep_time = rates[last].time;
                pools[pool_count].sweep_distance = (range_low - rates[last].low) / _Point;
                pools[pool_count].active = true;
                pool_count++;
                if(InpLPLogDetection)
                    Print("[LP] 低点Sweep: level=", range_low,
                          " dist=", pools[pool_count-1].sweep_distance, "pts");
            }
        }
    }
}

// ── 主扫描函数（新bar调用） ──
void DetectLiquidityPools(const MqlRates &rates[], int copied,
                          LiquidityPool &pools[], int &pool_count,
                          EAState &state)
{
    if(!InpEnableLiquidityPool) return;

    int lookback = MathMin(InpLPPoolLookbackBars, copied - 2);
    if(lookback < 5) return;

    // 年龄管理：标记过期pool
    for(int i = 0; i < pool_count; i++)
    {
        if(!pools[i].active) continue;
        pools[i].age_bars++;
        if(pools[i].age_bars > lookback * 2)
            pools[i].active = false;
    }

    DetectDoubleTopBottom(rates, copied, pools, pool_count, lookback);
    DetectSwingHighLowSweep(rates, copied, pools, pool_count, lookback);
}

// ── 每tick更新：检测新的sweep事件 ──
void UpdateLiquidityPools(LiquidityPool &pools[], int pool_count,
                          double bid, double ask, EAState &state)
{
    if(!InpEnableLiquidityPool) return;

    for(int i = 0; i < pool_count; i++)
    {
        if(pools[i].swept || !pools[i].active) continue;

        // 双顶/底: 价格突破level后收盘回落才算sweep（由新bar检测）
        // 这里只做tick更新age
        pools[i].age_bars++;
        if(pools[i].age_bars > InpLPPoolLookbackBars * 2)
            pools[i].active = false;
    }
}

// ── 检查指定zone是否被流动性池增强 ──
bool IsZoneLiquidityLinked(const OBZone &zone, const LiquidityPool &pools[],
                           int pool_count, double atr_value)
{
    if(!InpEnableLiquidityPool) return false;

    for(int i = 0; i < pool_count; i++)
    {
        if(!pools[i].active) continue;

        // 多头OB关联:
        // - 最近有低点sweep + OB在sweep区域附近
        if(zone.direction == OB_BUY && pools[i].type == LP_SWING_HIGH_LOW
           && pools[i].swept)
        {
            if(MathAbs(zone.low - pools[i].level) < atr_value * 0.5)
                return true;
        }

        // 空头OB关联:
        // - 最近有高点sweep + OB在sweep区域附近
        if(zone.direction == OB_SELL && pools[i].type == LP_SWING_HIGH_LOW
           && pools[i].swept)
        {
            if(MathAbs(zone.high - pools[i].level) < atr_value * 0.5)
                return true;
        }
    }
    return false;
}

#endif
