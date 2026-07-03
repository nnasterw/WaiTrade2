#ifndef __WAITRADE_RANGE_DETECTOR_MQH__
#define __WAITRADE_RANGE_DETECTOR_MQH__

#include "Config.mqh"
#include "MathUtils.mqh"

// ╔══════════════════════════════════════════════════════════════╗
// ║ HTF大周期震荡区间检测器                                       ║
// ║ 核心理念: 大周期（H4/D1）震荡区间提供可靠的高抛低吸边界       ║
// ║ 小周期（M1/M5）入场实现精确的R:R                            ║
// ╚══════════════════════════════════════════════════════════════╝

struct HTFRange
{
    double   high;              // 区间上沿（多次测试确认的阻力）
    double   low;               // 区间下沿（多次测试确认的支撑）
    double   mid;               // 区间中轴 (high+low)/2
    double   width_atr;         // 区间宽度（ATR倍数）
    double   width_price;       // 区间宽度（价格绝对值）
    int      touches_top;       // 上沿测试次数
    int      touches_bottom;    // 下沿测试次数
    int      age_bars;          // 区间已存在bar数
    datetime first_detected;    // 首次检测到区间的时间
    datetime last_touch_top;    // 最近一次接触上沿
    datetime last_touch_bottom; // 最近一次接触下沿
    bool     valid;             // 是否为有效可交易区间
    double   confidence;        // 置信度评分 0.0-1.0
    double   top_zone_high;     // 上沿卖出区域（上沿-0.2ATR ~ 上沿+0.1ATR）
    double   top_zone_low;
    double   bottom_zone_low;   // 下沿买入区域（下沿-0.1ATR ~ 下沿+0.2ATR）
    double   bottom_zone_high;
    bool     breaking_up;       // 是否正在向上突破
    bool     breaking_down;     // 是否正在向下突破
    datetime last_update;
};

// 价格在区间中的位置
enum ENUM_RANGE_POSITION
{
    RANGE_NEAR_TOP,      // 靠近上沿 → 考虑做空（高抛）
    RANGE_NEAR_BOTTOM,   // 靠近下沿 → 考虑做多（低吸）
    RANGE_MIDDLE,        // 区间中部 → 不交易或跟随趋势
    RANGE_BREAKING,      // 正在突破边界 → 观望
    NO_RANGE             // 无有效区间
};

// ═══════════════════════════════════════════════════════════════
// 区间检测核心函数
// 参数: tf=检测周期(建议PERIOD_H4), lookback=回溯bar数
// 返回: 填充的HTFRange结构
// ═══════════════════════════════════════════════════════════════
HTFRange DetectHTFRange(string symbol, ENUM_TIMEFRAMES tf, int lookback_bars = 120)
{
    HTFRange range;
    ZeroMemory(range);

    if(!CfgRangeContextDetectorEnabled())
        return range;

    // 1. 加载HTF K线数据
    MqlRates rates[];
    int count = CopyRates(symbol, tf, 0, lookback_bars, rates);
    if(count < CfgRangeMinBars())
    {
        Print("[RangeDetector] HTF数据不足: ", count, " bars");
        return range;
    }

    // 2. 计算ATR
    double atr = CalcATR(rates, count, 14);
    if(atr <= 0) return range;

    // 3. 用ATR定义区间边界公差
    double boundary_tolerance = atr * CfgRangeBoundaryToleranceATR(); // 默认0.15 ATR
    double min_range_width = atr * CfgRangeMinWidthATR();             // 默认1.5 ATR
    double max_range_width = atr * CfgRangeMaxWidthATR();             // 默认5.0 ATR

    // 研究哨兵: InpRangeMaxWidthATR < 0 时，使用最近HTF历史高低点构造宽供需区。
    // 用于验证类似 2602 的大区间OB边界触达反转；默认正值路径完全不变。
    if(CfgRangeMaxWidthATR() < 0.0)
    {
        int last_closed = count - 2;
        if(last_closed < CfgRangeMinBars())
            return range;

        // 大周期区间只能由已收盘K线定义，当前HTF K线只用于触达/反应判断。
        double top = rates[1].high;
        double bottom = rates[1].low;
        for(int i = 1; i <= last_closed; i++)
        {
            if(rates[i].high > top) top = rates[i].high;
            if(rates[i].low < bottom) bottom = rates[i].low;
        }

        double width = top - bottom;
        double max_width = atr * MathAbs(CfgRangeMaxWidthATR());
        if(width < min_range_width || width > max_width)
            return range;

        int touches_t = 0, touches_b = 0;
        double touch_tol = boundary_tolerance * 1.2;
        int bars_inside = 0;
        for(int i = 0; i <= last_closed; i++)
        {
            if(MathAbs(rates[i].high - top) <= touch_tol) touches_t++;
            if(MathAbs(rates[i].low - bottom) <= touch_tol) touches_b++;
            if(rates[i].close >= bottom - touch_tol && rates[i].close <= top + touch_tol)
                bars_inside++;
        }
        if(touches_t < MathMax(1, CfgRangeMinTouches()) ||
           touches_b < MathMax(1, CfgRangeMinTouches()))
            return range;

        double containment_pct = (double)bars_inside / (double)(last_closed + 1);
        if(containment_pct < CfgRangeMinContainment())
            return range;

        range.high = top;
        range.low = bottom;
        range.mid = (top + bottom) / 2.0;
        range.width_price = width;
        range.width_atr = width / atr;
        range.touches_top = touches_t;
        range.touches_bottom = touches_b;
        range.age_bars = last_closed + 1;
        range.first_detected = rates[0].time;
        range.valid = true;
        range.confidence = MathMax(0.0, MathMin(1.0,
                           0.20 + MathMin(containment_pct, 0.35) +
                           MathMin((touches_t + touches_b) / 8.0, 0.25) +
                           MathMin(range.width_atr / MathAbs(CfgRangeMaxWidthATR()), 0.20)));

        range.top_zone_high = top + boundary_tolerance * 0.8;
        range.top_zone_low = top - boundary_tolerance * 2.0;
        range.bottom_zone_high = bottom + boundary_tolerance * 2.0;
        range.bottom_zone_low = bottom - boundary_tolerance * 0.8;

        double current = rates[count - 1].close;
        if(current > top + boundary_tolerance && rates[count - 1].close > rates[count - 2].close)
            range.breaking_up = true;
        if(current < bottom - boundary_tolerance && rates[count - 1].close < rates[count - 2].close)
            range.breaking_down = true;
        range.last_update = TimeCurrent();
        return range;
    }

    // 4. 找所有swing high/low
    int swing_strength = CfgRangeSwingStrength();  // 默认3 (H4上3个bar确认swing)
    double swing_highs[];
    double swing_lows[];
    int sh_count = 0, sl_count = 0;
    ArrayResize(swing_highs, 50);
    ArrayResize(swing_lows, 50);

    for(int i = swing_strength; i < count - swing_strength; i++)
    {
        // 检测swing high
        bool is_high = true;
        for(int j = 1; j <= swing_strength; j++)
        {
            if(rates[i - j].high >= rates[i].high || rates[i + j].high >= rates[i].high)
            { is_high = false; break; }
        }
        if(is_high)
        {
            if(sh_count >= ArraySize(swing_highs)) ArrayResize(swing_highs, sh_count * 2);
            swing_highs[sh_count++] = rates[i].high;
        }

        // 检测swing low
        bool is_low = true;
        for(int j = 1; j <= swing_strength; j++)
        {
            if(rates[i - j].low <= rates[i].low || rates[i + j].low <= rates[i].low)
            { is_low = false; break; }
        }
        if(is_low)
        {
            if(sl_count >= ArraySize(swing_lows)) ArrayResize(swing_lows, sl_count * 2);
            swing_lows[sl_count++] = rates[i].low;
        }
    }

    if(sh_count < 2 || sl_count < 2)
        return range;

    // 5. 聚类swing高低点找区间边界
    // 上沿: 聚类相近的swing high
    double top_cluster = ClusterSwings(swing_highs, sh_count, boundary_tolerance);
    double bottom_cluster = ClusterSwings(swing_lows, sl_count, boundary_tolerance);

    if(top_cluster <= 0 || bottom_cluster <= 0 || top_cluster <= bottom_cluster)
        return range;

    double width = top_cluster - bottom_cluster;

    // 6. 验证区间宽度
    if(width < min_range_width || width > max_range_width)
        return range;

    // 7. 统计边界接触次数
    int touches_t = 0, touches_b = 0;
    double touch_tol = boundary_tolerance * 0.8;

    for(int i = 0; i < count; i++)
    {
        if(MathAbs(rates[i].high - top_cluster) <= touch_tol) touches_t++;
        if(MathAbs(rates[i].low - bottom_cluster) <= touch_tol) touches_b++;
    }

    if(touches_t < CfgRangeMinTouches() || touches_b < CfgRangeMinTouches())
        return range;

    // 8. 计算价格包容度（价格在区间内的比例）
    int bars_inside = 0;
    for(int i = 0; i < count; i++)
    {
        double bar_mid = (rates[i].high + rates[i].low) / 2.0;
        if(bar_mid >= bottom_cluster - touch_tol && bar_mid <= top_cluster + touch_tol)
            bars_inside++;
    }
    double containment_pct = (double)bars_inside / (double)count;

    if(containment_pct < CfgRangeMinContainment()) // 默认0.75
        return range;

    // 9. 检查是否有有效突破（突破后持续在区间外）
    bool has_valid_breakout = CheckRangeBreakout(rates, count, top_cluster, bottom_cluster,
                                                  boundary_tolerance, swing_strength);

    if(has_valid_breakout && containment_pct < 0.90)
        return range;  // 已突破的区间不再有效

    // 10. 填充区间数据
    range.high = top_cluster;
    range.low = bottom_cluster;
    range.mid = (top_cluster + bottom_cluster) / 2.0;
    range.width_price = width;
    range.width_atr = width / atr;
    range.touches_top = touches_t;
    range.touches_bottom = touches_b;
    range.age_bars = count;
    range.first_detected = rates[count - 1].time;
    range.valid = true;

    // 11. 置信度评分 (0-1)
    double score = 0.0;
    score += MathMin(touches_t / 4.0, 0.25);     // 上沿测试次数（最高0.25）
    score += MathMin(touches_b / 4.0, 0.25);     // 下沿测试次数（最高0.25）
    score += MathMin(containment_pct, 0.30);     // 包容度（最高0.30）
    score += MathMin(range.width_atr / 3.0, 0.20); // 宽度合理（最高0.20，过窄过宽都扣分）
    if(range.width_atr < 1.0 || range.width_atr > 4.0) score -= 0.10;

    range.confidence = MathMax(0.0, MathMin(1.0, score));

    // 12. 计算交易区域
    range.top_zone_high = top_cluster + boundary_tolerance * 0.5;
    range.top_zone_low = top_cluster - boundary_tolerance * 1.5;
    range.bottom_zone_high = bottom_cluster + boundary_tolerance * 1.5;
    range.bottom_zone_low = bottom_cluster - boundary_tolerance * 0.5;

    // 13. 检查突破状态
    double current = rates[count - 1].close;
    if(current > top_cluster + boundary_tolerance && rates[count - 1].close > rates[count - 2].close)
        range.breaking_up = true;
    if(current < bottom_cluster - boundary_tolerance && rates[count - 1].close < rates[count - 2].close)
        range.breaking_down = true;

    range.last_update = TimeCurrent();

    return range;
}

// ═══════════════════════════════════════════════════════════════
// 判断当前价格在区间中的位置
// ═══════════════════════════════════════════════════════════════
ENUM_RANGE_POSITION GetRangePosition(HTFRange &range, double current_price)
{
    if(!range.valid)
        return NO_RANGE;

    if(range.breaking_up || range.breaking_down)
        return RANGE_BREAKING;

    double top_zone_mid = (range.top_zone_high + range.top_zone_low) / 2.0;
    double bottom_zone_mid = (range.bottom_zone_high + range.bottom_zone_low) / 2.0;

    // 靠近上沿 → 高抛
    if(current_price >= range.top_zone_low && current_price <= range.top_zone_high)
        return RANGE_NEAR_TOP;
    if(current_price > range.top_zone_high)
        return RANGE_BREAKING;  // 已突破上沿

    // 靠近下沿 → 低吸
    if(current_price <= range.bottom_zone_high && current_price >= range.bottom_zone_low)
        return RANGE_NEAR_BOTTOM;
    if(current_price < range.bottom_zone_low)
        return RANGE_BREAKING;  // 已突破下沿

    return RANGE_MIDDLE;
}

// ═══════════════════════════════════════════════════════════════
// 区间方向建议: 入场信号应取的方向（区间交易反转SMC信号）
// direction: SMC原始信号方向 (OB_BUY=做多, OB_SELL=做空)
// 返回: 修正后的方向（在区间边界反转）
// ═══════════════════════════════════════════════════════════════
int GetRangeFadeDirection(HTFRange &range, ENUM_RANGE_POSITION pos, int original_direction)
{
    if(!range.valid)
        return original_direction;

    switch(pos)
    {
        case RANGE_NEAR_TOP:
            // 在区间上沿，所有buy信号转为sell（高抛）
            return OB_SELL;

        case RANGE_NEAR_BOTTOM:
            // 在区间下沿，所有sell信号转为buy（低吸）
            return OB_BUY;

        default:
            return original_direction;
    }
}

// ═══════════════════════════════════════════════════════════════
// 区间TP计算: TP设在区间对侧或中轴
// ═══════════════════════════════════════════════════════════════
double CalcRangeTP(HTFRange &range, ENUM_RANGE_POSITION pos, double entry, int direction)
{
    if(!range.valid) return 0;

    double tp = 0;

    switch(pos)
    {
        case RANGE_NEAR_TOP:
            if(direction == OB_SELL)
            {
                // 做空: TP1=中轴, TP2=下沿
                tp = CfgRangeTPTarget() == 0 ? range.low : range.mid;
            }
            break;

        case RANGE_NEAR_BOTTOM:
            if(direction == OB_BUY)
            {
                // 做多: TP1=中轴, TP2=上沿
                tp = CfgRangeTPTarget() == 0 ? range.high : range.mid;
            }
            break;

        default:
            break;
    }

    return tp;
}

// ═══════════════════════════════════════════════════════════════
// 区间止损: SL放在区间边界外0.5ATR处
// ═══════════════════════════════════════════════════════════════
double CalcRangeSL(HTFRange &range, ENUM_RANGE_POSITION pos, int direction, double atr)
{
    if(!range.valid) return 0;

    double sl_buffer = atr * CfgRangeSLBufferATR();  // 默认 0.5 ATR

    switch(pos)
    {
        case RANGE_NEAR_TOP:
            if(direction == OB_SELL)
                return range.high + sl_buffer;  // SL在上沿上方
            break;

        case RANGE_NEAR_BOTTOM:
            if(direction == OB_BUY)
                return range.low - sl_buffer;   // SL在下沿下方
            break;

        default:
            break;
    }

    return 0;
}

// ═══════════════════════════════════════════════════════════════
// 辅助函数: 聚类相近的swing点
// ═══════════════════════════════════════════════════════════════
double ClusterSwings(double &prices[], int count, double tolerance)
{
    if(count <= 0) return 0;

    // 简单实现: 找密度最高的价格区域
    int best_cluster_size = 0;
    double best_center = 0;

    for(int i = 0; i < count; i++)
    {
        int cluster_size = 0;
        double sum = 0;
        for(int j = 0; j < count; j++)
        {
            if(MathAbs(prices[j] - prices[i]) <= tolerance)
            {
                cluster_size++;
                sum += prices[j];
            }
        }

        if(cluster_size > best_cluster_size ||
           (cluster_size == best_cluster_size && i == 0))
        {
            best_cluster_size = cluster_size;
            best_center = sum / cluster_size;
        }
    }

    return (best_cluster_size >= 2) ? best_center : 0;
}

// ═══════════════════════════════════════════════════════════════
// 检查区间是否被有效突破
// ═══════════════════════════════════════════════════════════════
bool CheckRangeBreakout(MqlRates &rates[], int count,
                         double top, double bottom, double tolerance, int strength)
{
    if(count < strength + 3) return false;

    // 检查最近的K线是否在区间外并持续
    int bars_outside = 0;
    int start_check = count - strength * 2;

    for(int i = start_check; i < count; i++)
    {
        if(rates[i].close > top + tolerance || rates[i].close < bottom - tolerance)
            bars_outside++;
    }

    // 如果最近strength根K线中大多数都在区间外 → 有效突破
    return (bars_outside >= strength);
}

// ═══════════════════════════════════════════════════════════════
// 缓存: 避免每tick都重新检测（区间变化慢）
// ═══════════════════════════════════════════════════════════════
HTFRange g_cached_range;
datetime g_range_cache_time = 0;
int g_range_cache_bars = 0;

HTFRange GetHTFRange(string symbol)
{
    ENUM_TIMEFRAMES tf = MinutesToTF(CfgRangeTF());

    // 缓存过期检查: 每N根HTF K线更新一次
    int current_bars = Bars(symbol, tf);
    int cache_interval = CfgRangeUpdateBars();  // 默认1（每根HTF bar更新）

    if(g_range_cache_time == 0 ||
       MathAbs(current_bars - g_range_cache_bars) >= cache_interval ||
       g_range_cache_time < TimeCurrent() - 300)  // 至少5分钟更新一次
    {
        g_cached_range = DetectHTFRange(symbol, tf, CfgRangeLookback());
        g_range_cache_time = TimeCurrent();
        g_range_cache_bars = current_bars;

        if(g_cached_range.valid)
        {
            PrintFormat("[RangeDetector] 检测到HTF区间: %.2f-%.2f (宽%.1fATR, "
                        "上沿%d触/下沿%d触, 置信度%.0f%%)",
                        g_cached_range.low, g_cached_range.high,
                        g_cached_range.width_atr,
                        g_cached_range.touches_top, g_cached_range.touches_bottom,
                        g_cached_range.confidence * 100);
        }
    }

    return g_cached_range;
}

// 获取当前位置（方便SignalEngine调用）
ENUM_RANGE_POSITION GetCurrentRangePosition(string symbol, double current_price)
{
    HTFRange range = GetHTFRange(symbol);
    return GetRangePosition(range, current_price);
}

// 获取区间信息字符串（用于注释）
string RangePositionToString(ENUM_RANGE_POSITION pos)
{
    switch(pos)
    {
        case RANGE_NEAR_TOP:    return "TOP";
        case RANGE_NEAR_BOTTOM: return "BOT";
        case RANGE_MIDDLE:      return "MID";
        case RANGE_BREAKING:    return "BRK";
        default:                return "NO";
    }
}

#endif // __WAITRADE_RANGE_DETECTOR_MQH__
