// WaiTrade3 MultiTFOB — 多周期OB加权入场
// 核心: H4/H1 swing points → HTF OB zone → TF权重×ATR宽SL
// H4 OB权重4.0 + SL=$15-25 → 抓$50-100波段
// H1 OB权重2.0 + SL=$8-15  → 抓$20-50波段
// M1 OB权重1.0 + SL=$1-3   → 抓$2-5波段(scalper保持)
// 多周期同价共振 → 权重叠加 → 最强信号
#ifndef __MULTITF_OB_MQH__
#define __MULTITF_OB_MQH__

#include <WaiTrade3/TypesSMC.mqh>
#include <WaiTrade3/ConfigSMC.mqh>
#include <WaiTrade3/StructureTracker.mqh>
#include <WaiTrade2/Utils.mqh>

// ── MTF OB Zone 结构 ──
struct MultiTFOBZone {
    double   high, low;          // OB价格区间
    int      direction;          // OB_BUY(1) / OB_SELL(-1)
    ENUM_TIMEFRAMES tf;          // 来源周期
    double   weight;             // TF权重 (H4=4, H1=2, M15=1.5, M5=1.2, M1=1.0)
    double   sl_price;           // 止损价 (已计算)
    double   atr;                // 该TF的ATR
    double   risk_price;         // 风险距离 = |entry_mid - sl|
    datetime created;            // 创建时间
    int      created_bar;        // 全局bar索引
    bool     expired;
    bool     used;
    int      entry_count;
    datetime last_entry;
    double   confluence_bonus;   // 多周期重叠加分 (乘数)
    double   total_weight;       // weight × confluence_bonus
};

MultiTFOBZone g_mtf_zones[MAX_OB_ZONES];
int g_mtf_zone_count = 0;

// ── TF权重查询 ──
double GetTFWeight(ENUM_TIMEFRAMES tf)
{
    switch(tf)
    {
        case PERIOD_H4:  return InpMTFH4Weight;
        case PERIOD_H1:  return InpMTFH1Weight;
        case PERIOD_M15: return InpMTFM15Weight;
        case PERIOD_M5:  return InpMTFM5Weight;
        default:         return InpMTFM1Weight;
    }
}

// ── 从swing point创建HTF OB zone ──
void CreateMTFZoneFromSwing(const SMCSwingPoint &sp, ENUM_TIMEFRAMES tf,
                             double atr, int bar_count)
{
    if(g_mtf_zone_count >= MAX_OB_ZONES) return;
    if(sp.broken) return;

    double buffer = atr * InpMTFOBSLBufferATR;

    g_mtf_zones[g_mtf_zone_count].tf = tf;
    g_mtf_zones[g_mtf_zone_count].atr = atr;
    g_mtf_zones[g_mtf_zone_count].weight = GetTFWeight(tf);
    g_mtf_zones[g_mtf_zone_count].created = sp.time;
    g_mtf_zones[g_mtf_zone_count].created_bar = bar_count;
    g_mtf_zones[g_mtf_zone_count].expired = false;
    g_mtf_zones[g_mtf_zone_count].used = false;
    g_mtf_zones[g_mtf_zone_count].entry_count = 0;
    g_mtf_zones[g_mtf_zone_count].last_entry = 0;
    g_mtf_zones[g_mtf_zone_count].confluence_bonus = 1.0;
    g_mtf_zones[g_mtf_zone_count].total_weight = 0;

    if(sp.type == SWING_HIGH)
    {
        // swing high → sell OB (阻力位)
        g_mtf_zones[g_mtf_zone_count].direction = OB_SELL;
        // OB区间: swing_price ± 0.3×buffer
        g_mtf_zones[g_mtf_zone_count].high = sp.price + buffer * 0.3;
        g_mtf_zones[g_mtf_zone_count].low  = sp.price - buffer * 0.3;
        // SL: swing上方1个buffer距离
        g_mtf_zones[g_mtf_zone_count].sl_price = sp.price + buffer;
    }
    else
    {
        // swing low → buy OB (支撑位)
        g_mtf_zones[g_mtf_zone_count].direction = OB_BUY;
        g_mtf_zones[g_mtf_zone_count].high = sp.price + buffer * 0.3;
        g_mtf_zones[g_mtf_zone_count].low  = sp.price - buffer * 0.3;
        g_mtf_zones[g_mtf_zone_count].sl_price = sp.price - buffer;
    }

    // risk_price = 从OB中点到SL的距离
    double mid = (g_mtf_zones[g_mtf_zone_count].high + g_mtf_zones[g_mtf_zone_count].low) / 2.0;
    g_mtf_zones[g_mtf_zone_count].risk_price = MathAbs(mid - g_mtf_zones[g_mtf_zone_count].sl_price);

    g_mtf_zone_count++;
}

// ── 检测HTF OB (每新bar调用) ──
void DetectMultiTFOBs(string symbol, int bar_count)
{
    if(!InpEnableMultiTFOB) return;

    // 重置 (每bar重新检测swing OB)
    g_mtf_zone_count = 0;

    // ── H4 OBs (从H4 swing points) ──
    if(InpMTFH4Weight > 0)
    {
        MqlRates h4_rates[];
        int h4_count = CopyRates(symbol, PERIOD_H4, 0, 60, h4_rates);
        if(h4_count > 20)
        {
            double h4_atr = CalcATR(h4_rates, h4_count, 14);

            SMCSwingPoint h4_swings[MAX_SWING_POINTS];
            int h4_sc = 0;
            int pivot = MathMin(InpStructurePivotBars, 3);
            for(int i = pivot; i < h4_count - pivot; i++)
            {
                if(IsSwingHighV3(h4_rates, i, pivot))
                    AddSwingPointV3(h4_swings, h4_sc, h4_rates[i].high,
                                   h4_rates[i].time, SWING_HIGH, 0);
                if(IsSwingLowV3(h4_rates, i, pivot))
                    AddSwingPointV3(h4_swings, h4_sc, h4_rates[i].low,
                                   h4_rates[i].time, SWING_LOW, 0);
            }

            // 最近N个未突破swing → OB
            for(int i = h4_sc - 1; i >= 0 && (h4_sc - 1 - i) < InpMTFMaxOBPerTF; i--)
            {
                if(!h4_swings[i].broken)
                    CreateMTFZoneFromSwing(h4_swings[i], PERIOD_H4, h4_atr, bar_count);
            }
        }
    }

    // ── H1 OBs ──
    if(InpMTFH1Weight > 0)
    {
        MqlRates h1_rates[];
        int h1_count = CopyRates(symbol, PERIOD_H1, 0, 100, h1_rates);
        if(h1_count > 30)
        {
            double h1_atr = CalcATR(h1_rates, h1_count, 14);

            SMCSwingPoint h1_swings[MAX_SWING_POINTS];
            int h1_sc = 0;
            int pivot = MathMin(InpStructurePivotBars, 3);
            for(int i = pivot; i < h1_count - pivot; i++)
            {
                if(IsSwingHighV3(h1_rates, i, pivot))
                    AddSwingPointV3(h1_swings, h1_sc, h1_rates[i].high,
                                   h1_rates[i].time, SWING_HIGH, 0);
                if(IsSwingLowV3(h1_rates, i, pivot))
                    AddSwingPointV3(h1_swings, h1_sc, h1_rates[i].low,
                                   h1_rates[i].time, SWING_LOW, 0);
            }

            for(int i = h1_sc - 1; i >= 0 && (h1_sc - 1 - i) < InpMTFMaxOBPerTF; i--)
            {
                if(!h1_swings[i].broken)
                    CreateMTFZoneFromSwing(h1_swings[i], PERIOD_H1, h1_atr, bar_count);
            }
        }
    }
}

// ── 多周期重叠检测 (共振加分) ──
void ScoreMTFConfluence()
{
    if(!InpEnableMultiTFOB) return;

    for(int i = 0; i < g_mtf_zone_count; i++)
    {
        if(g_mtf_zones[i].expired) continue;
        double mid_i = (g_mtf_zones[i].high + g_mtf_zones[i].low) / 2.0;

        int overlap = 0;
        for(int j = 0; j < g_mtf_zone_count; j++)
        {
            if(i == j || g_mtf_zones[j].expired) continue;
            if(g_mtf_zones[i].direction != g_mtf_zones[j].direction) continue;
            if(g_mtf_zones[i].tf == g_mtf_zones[j].tf) continue;

            double mid_j = (g_mtf_zones[j].high + g_mtf_zones[j].low) / 2.0;
            double tol = MathMax(g_mtf_zones[i].atr, g_mtf_zones[j].atr) * 2.0;

            if(MathAbs(mid_i - mid_j) < tol)
                overlap++;
        }

        if(overlap >= 1)
            g_mtf_zones[i].confluence_bonus = InpMTFConfluenceBonus * overlap;
        else
            g_mtf_zones[i].confluence_bonus = 1.0;

        g_mtf_zones[i].total_weight = g_mtf_zones[i].weight * g_mtf_zones[i].confluence_bonus;
    }
}

// ── 过期管理 ──
void ExpireMTFZones(int bar_count)
{
    for(int i = 0; i < g_mtf_zone_count; i++)
    {
        if(g_mtf_zones[i].expired) continue;
        int age = bar_count - g_mtf_zones[i].created_bar;
        if(age > InpMTFOBMaxAgeBars)
            g_mtf_zones[i].expired = true;
    }
}

// ── 检查价格是否在MTF OB区域内 ──
bool IsPriceInMTFZone(double price, const MultiTFOBZone &zone)
{
    return (price >= zone.low && price <= zone.high);
}

// ── MTF OB重入检查 (使用H4自适应阈值) ──
bool PassMTFReentryCooldown(const MultiTFOBZone &zone)
{
    if(!InpEnableH4Adaptive) return true;
    // 重入逻辑与M1 OB相同, 但MTF OB的entry_count阈值更低
    // 因为HTF OB应该更珍惜, 不能像M1那样频繁重入
    int max_entries = IsRegimeTrending() ?
        MathMin(InpH4TrendMaxEntriesPerOB, 3) :   // 趋势市MTF最多3次
        MathMin(InpH4ChopMaxEntriesPerOB, 1);      // 震荡市MTF仅1次

    if(zone.entry_count >= max_entries) return false;

    int cooldown = IsRegimeTrending() ?
        InpH4TrendReentryCooldownMin :
        InpH4ChopReentryCooldownMin;
    if(cooldown > 0 && zone.last_entry > 0)
        if(TimeCurrent() - zone.last_entry < cooldown * 60)
            return false;

    return true;
}

// ── 标记MTF OB已使用 ──
void MarkMTFZoneUsed(int index)
{
    if(index >= 0 && index < g_mtf_zone_count)
    {
        g_mtf_zones[index].entry_count++;
        g_mtf_zones[index].last_entry = TimeCurrent();
    }
}

#endif
