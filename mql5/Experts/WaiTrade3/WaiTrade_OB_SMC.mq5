#property copyright "WaiTrade3 — SMC Enhanced"
#property version   "1.00"
#property strict

// ── v2 共用模块（直接引用，零改动）──
#include <WaiTrade2/Config.mqh>
#include <WaiTrade2/Types.mqh>
#include <WaiTrade2/Utils.mqh>
#include <WaiTrade2/MarketState.mqh>
#include <WaiTrade2/ScoreEngine.mqh>
#include <WaiTrade2/DecayDetector.mqh>
#include <WaiTrade2/OBDetector.mqh>
#include <WaiTrade2/SignalEngine.mqh>
#include <WaiTrade2/EntryEngine.mqh>
#include <WaiTrade2/PositionManager.mqh>
#include <WaiTrade2/FVGDetector.mqh>
#include <WaiTrade2/BarTracker.mqh>
#include <WaiTrade2/RangeDetector.mqh>
#include <WaiTrade2/MathUtils.mqh>
#include <WaiTrade2/TradeOps.mqh>

// ── v3 SMC 扩展 ──
#include <WaiTrade3/ConfigSMC.mqh>
#include <WaiTrade3/TypesSMC.mqh>
#include <WaiTrade3/StructureTracker.mqh>
#include <WaiTrade3/LiquidityPool.mqh>
#include <WaiTrade3/DiscountPremium.mqh>
#include <WaiTrade3/OBScorer.mqh>
#include <WaiTrade3/MultiTFOB.mqh>
#include <WaiTrade3/RegimeDetector.mqh>
// ── BD08双轨制: PathA(震荡/趋势自适应) + PathB(纯BOS驱动) ──
input bool InpEnableRegimeDetector  = false;  // 启用体制检测(PathA)
input bool InpEnableBOSOnlyMode     = false;  // 启用纯BOS模式(PathB)
// ── BOS Retest内联: swing突破检测+回踩入场 ──
// 状态机: IDLE → BREAK_DETECTED(突破) → RETEST_READY(价格已远离,等回踩) → 入场 → EXECUTED
enum ENUM_BOS_STATE {
    BOS_IDLE,            // 等待突破
    BOS_BREAK_DETECTED,  // 突破已发生, 等待价格延伸远离突破位(确认有效突破)
    BOS_RETEST_READY,    // 价格已延伸远离, 正在监控回踩
    BOS_EXECUTED         // 已执行入场(防止重复)
};
struct SwingBreakSignal {
    double break_level;       // 被突破的swing点价格
    int    direction;         // OB_BUY/OB_SELL
    double sl_price;          // 止损价
    double atr;               // SL用ATR (H1: M15_ATR, H4: H4_ATR×0.3)
    double h1_atr;            // 容差用ATR (H1: H1_ATR, H4: H4_ATR)
    int    age_bars;          // 信号年龄(M1 bars)
    double extension_extreme;
    ENUM_BOS_STATE state;
    datetime break_time;
    int    monitor_attempts;
    bool   from_h4;           // true=H4 BOS(需要更长MaxBars+更宽容差)
    int    custom_max_bars;   // 自定义MaxBars(0=使用InpBOSRetestMaxBars)
};
SwingBreakSignal g_sb_signal;
bool g_sb_inited = false;

// ── BOS双轨并行: 独立仓位/过滤器 ──
int    g_bos_pos_count = 0;
#define BOS_MAX_CONCURRENT 3


void InitSwingBreak()
{
    ZeroMemory(g_sb_signal);
    g_sb_signal.state = BOS_IDLE;
    g_sb_signal.direction = 0;
    g_sb_signal.monitor_attempts = 0;
    g_sb_inited = true;
}

// ── BOS Retest: 扩展延伸检测辅助 ──
// 检查自突破以来M1价格是否已延伸远离突破位(确认有效突破)
bool HasExtendedAway(string symbol, const SwingBreakSignal &sb, double min_atr_mult = 0.5)
{
    MqlRates m1[];
    int copied = CopyRates(symbol, PERIOD_M1, 0, MathMin(sb.age_bars + 5, 480), m1);
    if(copied < 1) return false;

    double ext_threshold = sb.atr * min_atr_mult;  // v10: M15 ATR做延伸确认

    if(sb.direction == OB_BUY)
    {
        // 多头突破: 价格需要先继续上涨(延伸), 远离突破位上方
        for(int i = 0; i < copied; i++)
        {
            if(m1[i].high > sb.break_level + ext_threshold)
            {
                // 记录延伸极值
                return true;
            }
        }
    }
    else  // OB_SELL
    {
        // 空头突破: 价格需要先继续下跌, 远离突破位下方
        for(int i = 0; i < copied; i++)
        {
            if(m1[i].low < sb.break_level - ext_threshold)
                return true;
        }
    }
    return false;
}

// ── BOS Retest: 检查价格是否正在回踩突破位 ──
bool IsRetesting(string symbol, const SwingBreakSignal &sb, double tolerance_atr_mult = 0.3)
{
    double tolerance = sb.atr * tolerance_atr_mult;
    double current_price;

    if(sb.direction == OB_BUY)
    {
        // 做多回踩: 价格从上方回落到突破位附近 (用Bid=卖方报价, 实际成交价)
        current_price = SymbolInfoDouble(symbol, SYMBOL_BID);
        // 价格需要低于突破位+tolerance (从上方回来)
        double prev_m1_high = 0;
        MqlRates m1[3];
        if(CopyRates(symbol, PERIOD_M1, 0, 3, m1) >= 3)
            prev_m1_high = MathMax(m1[1].high, m1[2].high);
        // 确认: 价格曾在突破位上方(延伸过) && 现在回到突破位附近
        return (prev_m1_high > sb.break_level + tolerance) &&
               (MathAbs(current_price - sb.break_level) < tolerance);
    }
    else  // OB_SELL
    {
        // 做空回踩: 价格从下方回升到突破位附近 (用Ask=买方报价)
        current_price = SymbolInfoDouble(symbol, SYMBOL_ASK);
        double prev_m1_low = 999999;
        MqlRates m1[3];
        if(CopyRates(symbol, PERIOD_M1, 0, 3, m1) >= 3)
            prev_m1_low = MathMin(m1[1].low, m1[2].low);
        // 确认: 价格曾在突破位下方(延伸过) && 现在回到突破位附近
        return (prev_m1_low < sb.break_level - tolerance) &&
               (MathAbs(current_price - sb.break_level) < tolerance);
    }
}


// ── H4 BOS: 大周期结构突破(独立于H1 BOS) ──
void DetectH4BOS(string symbol)
{
    if(!InpBOSRetestEntry) return;
    static datetime s_last_h4 = 0;
    MqlRates h4[60];
    int n = CopyRates(symbol, PERIOD_H4, 0, 60, h4);
    if(n < 20) return;
    if(h4[0].time == s_last_h4) return;
    s_last_h4 = h4[0].time;
    double h4_atr = CalcATR(h4, n, 14);
    double sh=0, sl=999999;
    for(int i=2; i<n-2; i++) {
        if(IsSwingHighV3(h4,i,2)) sh=h4[i].high;
        if(IsSwingLowV3(h4,i,2))  sl=h4[i].low;
    }
    if(sh>0 && h4[1].high<sh && h4[0].high>sh) {
        g_sb_signal.break_level=sh; g_sb_signal.direction=OB_BUY;
        g_sb_signal.atr=h4_atr*0.3; g_sb_signal.h1_atr=h4_atr;
        g_sb_signal.sl_price=sh-h4_atr*0.3*InpBOSRetestSLBuffer;
        g_sb_signal.age_bars=0; g_sb_signal.state=BOS_BREAK_DETECTED;
        g_sb_signal.monitor_attempts=0; g_sb_signal.from_h4=true;
        g_sb_signal.custom_max_bars=7200;  // H4: 5天窗口
        if(InpStructureLogBOS) Print("[BOS-H4] H4突破: ",sh," H4ATR=",h4_atr);
    }
    if(sl<999999 && h4[1].low>sl && h4[0].low<sl) {
        g_sb_signal.break_level=sl; g_sb_signal.direction=OB_SELL;
        g_sb_signal.atr=h4_atr*0.3; g_sb_signal.h1_atr=h4_atr;
        g_sb_signal.sl_price=sl+h4_atr*0.3*InpBOSRetestSLBuffer;
        g_sb_signal.age_bars=0; g_sb_signal.state=BOS_BREAK_DETECTED;
        g_sb_signal.monitor_attempts=0;
        if(InpStructureLogBOS) Print("[BOS-H4] H4跌破: ",sl," H4ATR=",h4_atr);
    }
}

void DetectSwingBreakInline(string symbol, int bar_count)
{
    if(!InpBOSRetestEntry) return;


    // ── 过期检查(所有活跃状态) ──
    if(g_sb_signal.state == BOS_BREAK_DETECTED || g_sb_signal.state == BOS_RETEST_READY)
    {
        g_sb_signal.age_bars++;
        int max_bars = (g_sb_signal.custom_max_bars > 0)
            ? g_sb_signal.custom_max_bars : InpBOSRetestMaxBars;
        if(g_sb_signal.age_bars >= max_bars)
        {
            if(InpStructureLogBOS)
                Print("[BOS] 信号过期清除 age=", g_sb_signal.age_bars,
                      " state=", (g_sb_signal.state == BOS_BREAK_DETECTED ? "BREAK" : "RETEST"));
            g_sb_signal.state = BOS_IDLE;
            g_sb_signal.direction = 0;
            g_sb_signal.monitor_attempts = 0;
            g_sb_signal.from_h4 = false;
            g_sb_signal.custom_max_bars = 0;
        }
    }

    // ── 状态: BREAK_DETECTED → 检查延伸是否已远离突破位 ──
    if(g_sb_signal.state == BOS_BREAK_DETECTED)
    {
        // 使用H1 bars检查延伸(每H1 bar更新一次, 降低M1噪声)
        static datetime s_last_ext_check = 0;
        MqlRates h1_chk[];
        if(CopyRates(symbol, PERIOD_H1, 0, 1, h1_chk) >= 1)
        {
            if(h1_chk[0].time != s_last_ext_check)
            {
                s_last_ext_check = h1_chk[0].time;
                // 检查自突破以来价格是否已延伸远离(>0.5×ATR)
                // 延伸确认用H1 ATR(≈$20×0.5=$10), 不用M15 ATR(≈$6×0.5=$3→噪音)
                if(HasExtendedAway(symbol, g_sb_signal, 0.5))  // uses sb.h1_atr
                {
                    g_sb_signal.state = BOS_RETEST_READY;
                    g_sb_signal.monitor_attempts = 0;
                    if(InpStructureLogBOS)
                        Print("[BOS] 价格已延伸远离 break=", g_sb_signal.break_level,
                              " → 进入回踩监控 dir=", (g_sb_signal.direction == OB_BUY ? "BUY" : "SELL"));
                }
            }
        }
        return;  // 仍在等延伸, 不检测新突破
    }

    // ── 状态: RETEST_READY → 等待RegisterChannelMonitors发现回踩确认(不在此处理) ──
    if(g_sb_signal.state == BOS_RETEST_READY)
        return;  // 等待入场或过期

    // ── 状态: EXECUTED → 重置后可检测新突破 ──
    if(g_sb_signal.state == BOS_EXECUTED)
    {
        // 冷却: 入场后至少等30根M1 bar再允许新BOS信号
        g_sb_signal.age_bars++;
        if(g_sb_signal.age_bars < 30) return;
        g_sb_signal.state = BOS_IDLE;
        g_sb_signal.direction = 0;
        g_sb_signal.monitor_attempts = 0;
    }

    // ── 状态: IDLE → 检测H1 swing突破 ──
    // 每个H1 bar检测一次
    static datetime s_last_check = 0;
    MqlRates h1_rates[];
    int h1_count = CopyRates(symbol, PERIOD_H1, 0, 2, h1_rates);
    if(h1_count < 2) return;
    if(h1_rates[0].time == s_last_check) return;
    s_last_check = h1_rates[0].time;

    // 获取H1数据用于swing检测
    int h1_lookback = CopyRates(symbol, PERIOD_H1, 0, 48, h1_rates);
    if(h1_lookback < 10) return;

    double h1_atr = CalcATR(h1_rates, h1_lookback, 14);

    // BOS SL: 使用M15 ATR替代H1 ATR (更小SL→风险可控→允许BOS入场)
    // M15 ATR≈$5-7 vs H1 ATR≈$20, 0.01手风险从$12降到$3-5
    double m15_atr = h1_atr * 0.3;  // M15 ATR ≈ 30% of H1 ATR (approximation)
    MqlRates m15_rates[];
    int m15_count = CopyRates(symbol, PERIOD_M15, 0, 30, m15_rates);
    if(m15_count >= 14)
        m15_atr = CalcATR(m15_rates, m15_count, 14);

    // 找最近(时间上)的swing high/low (用3-bar pivot)
    // CopyRates索引0=最新, 从小到大迭代→第一个找到的=时间上最近的
    int pivot = MathMin(InpStructurePivotBars, 3);
    double nearest_swing_high = 0, nearest_swing_low = 0;
    for(int i = pivot; i < h1_lookback - pivot; i++)
    {
        if(nearest_swing_high == 0 && IsSwingHighV3(h1_rates, i, pivot))
            nearest_swing_high = h1_rates[i].high;
        if(nearest_swing_low == 0 && IsSwingLowV3(h1_rates, i, pivot))
            nearest_swing_low = h1_rates[i].low;
        if(nearest_swing_high > 0 && nearest_swing_low > 0)
            break;
    }

    // 突破swing high: 前bar最高点<swing, 当前bar最高点突破swing → bullish breakout
    double prev_high = h1_rates[1].high;
    double curr_high = h1_rates[0].high;
    double prev_low_fix = h1_rates[1].low;
    double curr_low_fix = h1_rates[0].low;
    double curr_close = h1_rates[0].close;

    if(nearest_swing_high > 0 &&
       prev_high < nearest_swing_high && curr_high > nearest_swing_high)
    {
        g_sb_signal.break_level = nearest_swing_high;
        g_sb_signal.direction = OB_BUY;
        g_sb_signal.atr = m15_atr;
        g_sb_signal.h1_atr = h1_atr;
        g_sb_signal.sl_price = nearest_swing_high - m15_atr * InpBOSRetestSLBuffer;
        g_sb_signal.age_bars = 0;
        g_sb_signal.extension_extreme = curr_high;
        g_sb_signal.state = BOS_BREAK_DETECTED;
        g_sb_signal.break_time = h1_rates[0].time;
        g_sb_signal.monitor_attempts = 0;
        if(InpStructureLogBOS)
            Print("[BOS] H1 Swing High突破: ", nearest_swing_high,
                  " M15ATR=", DoubleToString(m15_atr, 1),
                  " SL=", DoubleToString(g_sb_signal.sl_price, _Digits),
                  " → 等待延伸远离后回踩做多");
        return;
    }

    // 跌破swing low: 前bar最低点>swing, 当前bar最低点跌破swing → bearish breakdown
    if(nearest_swing_low > 0 &&
       prev_low_fix > nearest_swing_low && curr_low_fix < nearest_swing_low)
    {
        g_sb_signal.break_level = nearest_swing_low;
        g_sb_signal.direction = OB_SELL;
        g_sb_signal.atr = m15_atr;  // 使用M15 ATR(小SL→大仓位)
        g_sb_signal.sl_price = nearest_swing_low + m15_atr * InpBOSRetestSLBuffer;
        g_sb_signal.age_bars = 0;
        g_sb_signal.extension_extreme = curr_low_fix;
        g_sb_signal.state = BOS_BREAK_DETECTED;
        g_sb_signal.break_time = h1_rates[0].time;
        g_sb_signal.monitor_attempts = 0;
        if(InpStructureLogBOS)
            Print("[BOS] H1 Swing Low跌破: ", nearest_swing_low,
                  " M15ATR=", DoubleToString(m15_atr, 1),
                  " SL=", DoubleToString(g_sb_signal.sl_price, _Digits),
                  " → 等待延伸远离后回踩做空");
        return;
    }
}

// ── 全局状态 ──
OBZone      g_zones[MAX_OB_ZONES];
OBZone      g_htf_zones[MAX_OB_ZONES];
PosTrack    g_tracks[MAX_POSITIONS];
EAState     g_state;
TradeSignal g_signals[10];
int         g_track_count = 0;
int         g_htf_zone_count = 0;

// v9.8a EntryEngine
EntryMonitor g_monitors[MAX_MONITORS];
EntryMonitor g_htf_monitors[MAX_MONITORS];
int          g_monitor_count = 0;
int          g_htf_monitor_count = 0;
datetime     g_last_entry_attempt = 0;

// 双zone通道
OBZone      g_zones_osc[MAX_OB_ZONES];
EAState     g_state_osc;
EntryMonitor g_monitors_osc[MAX_MONITORS];
int          g_monitor_count_osc = 0;
bool         g_osc_active = false;

// ── v3 SMC 全局状态 ──
TrendState     g_trend_state = TREND_UNKNOWN;
TrendState     g_trend_state_h4 = TREND_UNKNOWN; // H4大周期结构确认
int            g_trend_stable_bars = 0;
double         g_trend_strength = 0.0;
SMCSwingPoint     g_swing_points[MAX_SWING_POINTS];
int            g_swing_point_count = 0;
LiquidityPool  g_lpools[MAX_LIQUIDITY_POOLS];
int            g_lpool_count = 0;
SMCZoneData    g_smc_data[MAX_OB_ZONES];
int            g_structure_signal = SIG_NONE;

// ── OB新鲜度追踪 (平行数组, 不修改v2 OBZone) ──
int            g_ob_mitigations[MAX_OB_ZONES];  // 每个OB被缓解的次数
bool           g_ob_dead[MAX_OB_ZONES];          // OB已完全突破(死亡)

// ── P0: OB多周期重叠检测 (M1 OB聚类替代多TF CopyRates) ──
int CountOverlappingTFs(const OBZone &zone, const OBZone &all_zones[], int ob_count, double atr)
{
    double tolerance = atr * 2.0;
    double mid = (zone.high + zone.low) / 2.0;
    int overlap = 1;

    for(int i = 0; i < ob_count; i++)
    {
        if(all_zones[i].expired) continue;
        if(all_zones[i].created_bar == zone.created_bar
           && MathAbs((all_zones[i].high+all_zones[i].low) - (zone.high+zone.low)) < 0.01) continue;
        if(all_zones[i].direction != zone.direction) continue;
        double other_mid = (all_zones[i].high + all_zones[i].low) / 2.0;
        if(MathAbs(mid - other_mid) < tolerance
           && MathAbs(zone.created_bar - all_zones[i].created_bar) < 40)
        {
            overlap++;
            if(overlap >= 3) break;
        }
    }

    return overlap;
}

// ── H4自适应重入控制 (趋势市宽松 vs 震荡市限制) ──
// H4自适应趋势判断: 使用H1趋势(g_trend_state)而非H4
// H1数据量=H4的6倍, swing point检测更稳定可靠
// 仅显式CHOP才收紧, BULL/BEAR/UNKNOWN都用趋势宽松参数
bool IsRegimeTrending()
{
    TrendState regime = g_trend_state;
    // 如果StructureTracker未启用, 回退到H4检测
    if(!InpEnableStructureTracker)
        regime = g_trend_state_h4;
    // BULL/BEAR → 趋势市; UNKNOWN → 默认宽松(数据不足不惩罚)
    // 仅CHOP → 震荡市紧参数
    return (regime != TREND_CHOP);
}

int GetH4AdaptiveMaxEntriesPerOB()
{
    if(!InpEnableH4Adaptive) return CfgMaxEntriesPerOB();
    return IsRegimeTrending() ? InpH4TrendMaxEntriesPerOB : InpH4ChopMaxEntriesPerOB;
}

int GetH4AdaptiveReentryCooldownMin()
{
    if(!InpEnableH4Adaptive) return CfgOBReentryCooldownMin();
    return IsRegimeTrending() ? InpH4TrendReentryCooldownMin : InpH4ChopReentryCooldownMin;
}

int GetH4AdaptiveCooldownBars()
{
    if(!InpEnableH4Adaptive) return CfgCooldownBars();
    return IsRegimeTrending() ? InpH4TrendCooldownBars : InpH4ChopCooldownBars;
}

// H4自适应: OB级重入检查 (读取zone.entry_count/last_entry_time, 用H4阈值)
bool PassH4AdaptiveReentry(const OBZone &zone)
{
    if(!InpEnableH4Adaptive) return true;

    int max_entries = GetH4AdaptiveMaxEntriesPerOB();
    if(zone.entry_count >= max_entries)
    {
        if(InpStructureLogBOS)
            Print("[SMC] H4自适应拦截: OB入场达上限 entry_count=", zone.entry_count,
                  " >= ", max_entries, " (trend=", g_trend_state, " h4=", g_trend_state_h4, ")");
        return false;
    }

    int cooldown_min = GetH4AdaptiveReentryCooldownMin();
    if(cooldown_min > 0 && zone.last_entry_time > 0)
    {
        int elapsed_min = (int)((TimeCurrent() - zone.last_entry_time) / 60);
        if(elapsed_min < cooldown_min)
        {
            if(InpStructureLogBOS)
                Print("[SMC] H4自适应拦截: OB冷却中 elapsed=", elapsed_min,
                      "min < ", cooldown_min, "min (trend=", g_trend_state, ")");
            return false;
        }
    }

    return true;
}

// ── OB新鲜度追踪: 检测OB被缓解次数 ──
void UpdateOBFreshness(OBZone &zones[], int ob_count, const MqlRates &rates[], int copied)
{
    if(!InpOBFreshnessFilter) return;
    if(copied < 3) return;

    int curr = copied - 2;  // 刚完成的K线
    int prev = copied - 3;  // 前一根K线

    for(int z = 0; z < ob_count; z++)
    {
        if(zones[z].expired || g_ob_dead[z]) continue;

        double prev_close = rates[prev].close;
        double curr_high  = rates[curr].high;
        double curr_low   = rates[curr].low;
        double curr_close = rates[curr].close;

        if(zones[z].direction == OB_SELL)
        {
            // 价格从下方穿越进入OB区 → 缓解+1
            if(prev_close < zones[z].low && curr_high > zones[z].low)
                g_ob_mitigations[z]++;
            // 收盘突破OB上沿 → OB死亡
            if(curr_close > zones[z].high)
                g_ob_dead[z] = true;
        }
        else
        {
            // 价格从上方穿越进入OB区 → 缓解+1
            if(prev_close > zones[z].high && curr_low < zones[z].high)
                g_ob_mitigations[z]++;
            // 收盘跌破OB下沿 → OB死亡
            if(curr_close < zones[z].low)
                g_ob_dead[z] = true;
        }
    }
}

// ── P0: OB边缘入场过滤 (仅上沿Sell/下沿Buy, 过滤区间中部噪声) ──
bool PassEdgeBounceFilter(const OBZone &zone, double bid, double ask)
{
    if(!InpEdgeBounceOnly) return true;

    double price = (zone.direction == OB_BUY) ? ask : bid;
    double range = zone.high - zone.low;
    if(range <= 0) return true;

    if(zone.direction == OB_SELL)
    {
        double depth = (zone.high - price) / range;
        if(depth > 0.3) return false;
    }
    else
    {
        double depth = (price - zone.low) / range;
        if(depth > 0.3) return false;
    }
    return true;
}

// H4自适应: 全局冷却检查
bool IsInH4AdaptiveCooldown(const EAState &state)
{
    if(!InpEnableH4Adaptive) return false;
    int bars = GetH4AdaptiveCooldownBars();
    if(bars <= 0) return false;
    if(state.last_entry_bar == 0) return false;
    bool in_cooldown = (state.bar_count - state.last_entry_bar) < bars;
    if(in_cooldown && InpStructureLogBOS)
        Print("[SMC] H4自适应全局冷却: bar=", state.bar_count,
              " last_entry=", state.last_entry_bar, " < ", bars, "bars");
    return in_cooldown;
}

// ── OB动态年龄管理 ──
void ExpireOldZones(OBZone& zones[], int ob_count, int bar_count)
{
    if(InpMaxOBAgeBarsTF <= 0) return;
    for(int z = 0; z < ob_count; z++)
    {
        if(zones[z].expired) continue;
        if(bar_count - zones[z].created_bar > InpMaxOBAgeBarsTF)
            zones[z].expired = true;
    }
}

// ── 双通道辅助：注册监视器 ──
void RegisterChannelMonitors(OBZone& zones[], EAState& state,
                              EntryMonitor& mons[], int& mon_count,
                              bool new_active_bar, string symbol)
{
    if(!new_active_bar) return;

    // H4自适应: 全局冷却检查 (震荡市限制连续入场)
    if(IsInH4AdaptiveCooldown(state))
    {
        if(InpStructureLogBOS)
            Print("[SMC] H4自适应全局冷却: 跳过本bar全部入场");
        return;
    }

    double spread = GetSpread(symbol);
    double local_bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    double local_ask = SymbolInfoDouble(symbol, SYMBOL_ASK);

    for(int z = 0; z < state.ob_count; z++)
    {
        if(zones[z].expired || zones[z].used) continue;
        if(!PassOBReentryCooldown(zones[z])) continue;
        // H4自适应: OB级重入限制 (读v2 entry_count/last_entry_time, H4阈值覆盖)
        if(!PassH4AdaptiveReentry(zones[z])) continue;

        // P1: H4趋势强制对齐 — 明确趋势时禁止逆势入场
        if(InpMTFBlockCounterTrend)
        {
            if(g_trend_state_h4 == TREND_BULLISH && zones[z].direction == OB_SELL)
            {
                if(InpStructureLogBOS)
                    Print("[SMC] P1趋势对齐: H4=BULL 禁Sell z=", z);
                continue;
            }
            if(g_trend_state_h4 == TREND_BEARISH && zones[z].direction == OB_BUY)
            {
                if(InpStructureLogBOS)
                    Print("[SMC] P1趋势对齐: H4=BEAR 禁Buy z=", z);
                continue;
            }
        }

        // P0: OB边缘入场 — 仅上沿Sell/下沿Buy, 过滤区间中部噪声
        if(!PassEdgeBounceFilter(zones[z], local_bid, local_ask))
            continue;

        // OB新鲜度过滤: 反复缓解的OB→跳过 (4580教训: 第1次赚钱, 第2+次亏钱)
        if(InpOBFreshnessFilter)
        {
            if(g_ob_dead[z])
            {
                if(InpStructureLogBOS)
                    Print("[SMC] OB新鲜度: z=", z, " OB已死亡(被突破)");
                continue;
            }
            if(g_ob_mitigations[z] >= InpOBMaxMitigations)
            {
                if(InpStructureLogBOS)
                    Print("[SMC] OB新鲜度: z=", z, " 缓解", g_ob_mitigations[z],
                          "次 >= ", InpOBMaxMitigations);
                continue;
            }
        }

        if(CfgEnableStateFilter() && state.market_state != 0
           && state.market_state != zones[z].direction) continue;

        // -- v3 SMC: OB质量评分过滤 (使用v3 OBScorer的quality_score, 非v2 strength) --
        if(InpEnableOBScoring && g_smc_data[z].quality_score < InpOBScoreMinPass)
        {
            if(InpStructureLogBOS)
                Print("[SMC] OB评分不足 z=", z, " score=", g_smc_data[z].quality_score,
                      " < ", InpOBScoreMinPass);
            continue;
        }

        bool is_counter_trend = false;
        if(InpEnableStructureTracker
           && g_trend_state != TREND_CHOP && g_trend_state != TREND_UNKNOWN)
        {
            if(!IsDirectionAlignedWithTrend(zones[z].direction, g_trend_state))
                is_counter_trend = true;
        }

        // v3: SL用H1_ATR替代工作TF_ATR (M1_ATR=$1.6→$0.65SL vs H1_ATR≈$20→$8SL)
        double sl_atr = state.atr_value;
        if(InpSLUseH1ATR && g_state.atr_1h > 0)
            sl_atr = g_state.atr_1h;

        double risk_dist = (zones[z].direction == OB_BUY)
            ? ((zones[z].high + zones[z].low) / 2.0) - (zones[z].low - sl_atr * CfgSLBufferATR())
            : (zones[z].high + sl_atr * CfgSLBufferATR()) - ((zones[z].high + zones[z].low) / 2.0);
        if(spread > 0 && risk_dist / spread < CfgMinRiskSpreadRatio()) continue;

        TradeSignal tmp;
        ZeroMemory(tmp);
        tmp.direction  = zones[z].direction;
        // 逆势入场: 紧SL (保留v2 TP/DTP/BE参数不变)
        double sl_buffer = CfgSLBufferATR();
        if(InpEnableTrendAdaptiveExit && is_counter_trend)
            sl_buffer *= InpCounterTrendSLMult;  // 0.4x normal = 收紧60%
        tmp.sl = (zones[z].direction == OB_BUY)
            ? zones[z].low  - sl_atr * sl_buffer
            : zones[z].high + sl_atr * sl_buffer;
        tmp.risk_price = MathAbs(((zones[z].high + zones[z].low) / 2.0) - tmp.sl);
        tmp.ob_index   = z;
        tmp.pos_mult   = 1.0;

        if(CfgEnableScoring())
        {
            double prox = (state.atr_m15 > 0) ? state.atr_m15 : state.atr_value * 5;
            int score   = CalcSignalScore(zones[z], state, state.market_state, prox, tmp.risk_price, 0);
            if(score < CfgMinScore()) continue;
            double mult = ScoreToMultiplier(score);
            if(mult < 0) continue;
            tmp.pos_mult = mult;
        }

        // P0: OB多周期堆叠加仓 (评分后, 相乘而非覆盖)
        if(InpEnableOBStacking)
        {
            int overlap = CountOverlappingTFs(zones[z], zones, state.ob_count, state.atr_value);
            if(overlap >= 3)      tmp.pos_mult *= 1.6;
            else if(overlap >= 2) tmp.pos_mult *= 1.3;
            if(overlap >= 2 && InpStructureLogBOS)
                Print("[SMC] OB堆叠 z=", z, " overlap=", overlap, "TF mult=", tmp.pos_mult);
        }

        AddEntryMonitor(tmp, zones[z], mons, mon_count);
    }

    // ── MTF: 多周期OB加权入场 ──
    // H4趋势门控: 仅H4=BULL/BEAR时允许宽SL swing, CHOP/UNKNOWN→只跑M1 scalper
    if(InpEnableMultiTFOB && IsRegimeTrending())
    {
        for(int mz = 0; mz < g_mtf_zone_count; mz++)
        {
            if(g_mtf_zones[mz].expired || g_mtf_zones[mz].used) continue;
            if(!PassMTFReentryCooldown(g_mtf_zones[mz])) continue;

            // 检查价格是否进入MTF OB区域
            double chk_price = (g_mtf_zones[mz].direction == OB_BUY) ? local_ask : local_bid;
            if(!IsPriceInMTFZone(chk_price, g_mtf_zones[mz])) continue;

            // 方向门控: H4自适应检查
            if(InpEnableStructureTracker
               && g_trend_state != TREND_CHOP && g_trend_state != TREND_UNKNOWN)
            {
                if(!IsDirectionAlignedWithTrend(g_mtf_zones[mz].direction, g_trend_state))
                {
                    if(InpStructureLogBOS)
                        Print("[MTF] 方向门控拦截 z=", mz, " dir=", g_mtf_zones[mz].direction,
                              " trend=", g_trend_state);
                    continue;
                }
            }

            TradeSignal tmp;
            ZeroMemory(tmp);
            tmp.direction = g_mtf_zones[mz].direction;
            tmp.sl = g_mtf_zones[mz].sl_price;
            tmp.risk_price = g_mtf_zones[mz].risk_price;
            tmp.ob_index = mz + 10000;  // offset区分MTF vs M1 OB
            // MTF仓位: weight × base, 上限2.0 (防DD过高)
            double mtf_w = g_mtf_zones[mz].total_weight > 0 ?
                g_mtf_zones[mz].total_weight : g_mtf_zones[mz].weight;
            if(mtf_w > InpMTFMaxWeight) mtf_w = InpMTFMaxWeight;
            tmp.pos_mult = mtf_w;

            // MTF仓位上限: 不超过 InpMaxPosMult
            if(tmp.pos_mult > CfgMaxPosMult())
            {
                if(InpStructureLogBOS)
                    Print("[MTF] 仓位上限裁剪 z=", mz, " weight=", tmp.pos_mult,
                          " → ", CfgMaxPosMult());
                tmp.pos_mult = CfgMaxPosMult();
            }

            // Spread检查
            if(spread > 0 && tmp.risk_price / spread < CfgMinRiskSpreadRatio())
                continue;

            if(InpStructureLogBOS)
                Print("[MTF] 信号 z=", mz, " tf=", EnumToString(g_mtf_zones[mz].tf),
                      " dir=", (g_mtf_zones[mz].direction == OB_BUY ? "BUY" : "SELL"),
                      " weight=", tmp.pos_mult,
                      " sl=", DoubleToString(tmp.sl, _Digits),
                      " risk=", DoubleToString(tmp.risk_price, _Digits));

            // 使用M1 EntryEngine做精确入场确认
            // 创建临时OBZone供EntryMonitor使用
            OBZone tmp_zone;
            ZeroMemory(tmp_zone);
            tmp_zone.high = g_mtf_zones[mz].high;
            tmp_zone.low = g_mtf_zones[mz].low;
            tmp_zone.direction = g_mtf_zones[mz].direction;
            tmp_zone.entry_count = g_mtf_zones[mz].entry_count;
            tmp_zone.last_entry_time = g_mtf_zones[mz].last_entry;

            AddEntryMonitor(tmp, tmp_zone, mons, mon_count);
        }
    }

    // ── BOS回踩入场: swing突破→延伸远离→回踩被突破位→直接入场(无需M1 OB) ──
    // v9血训: M1 OB确认导致30+次"回踩等待"→0入场。BOS自身已有三重确认(H1突破+延伸+回踩)
    // 取消M1 OB要求→回踩到位即入场
    if(InpBOSRetestEntry && g_sb_signal.state == BOS_RETEST_READY)
    {
        double bos_tolerance = g_sb_signal.atr * InpBOSRetestTolerance;

        if(IsRetesting(_Symbol, g_sb_signal, InpBOSRetestTolerance))
        {
            g_sb_signal.monitor_attempts++;

            TradeSignal tmp;
            ZeroMemory(tmp);
            tmp.direction = g_sb_signal.direction;
            tmp.sl = g_sb_signal.sl_price;

            // 入场价: 当前市价(回踩到位即入场)
            double entry_price = (g_sb_signal.direction == OB_BUY)
                ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                : SymbolInfoDouble(_Symbol, SYMBOL_BID);
            tmp.risk_price = MathAbs(entry_price - g_sb_signal.sl_price);
            tmp.ob_index = 20000 + (int)g_sb_signal.break_level;
            tmp.pos_mult = InpBOSRetestWeight * InpMTFH1Weight;

            // BOS不使用固定TP, 由DTP动态止盈(v10验证最优)
            tmp.tp = 0;

            if(tmp.pos_mult > CfgMaxPosMult())
                tmp.pos_mult = CfgMaxPosMult();

            if(InpStructureLogBOS)
                Print("[BOS] 回踩入场: dir=", (tmp.direction == OB_BUY ? "BUY" : "SELL"),
                      " break=", DoubleToString(g_sb_signal.break_level, _Digits),
                      " entry=", DoubleToString(entry_price, _Digits),
                      " SL=", DoubleToString(tmp.sl, _Digits),
                      " TP=", DoubleToString(tmp.tp, _Digits),
                      " risk=", DoubleToString(tmp.risk_price, _Digits),
                      " attempt=", g_sb_signal.monitor_attempts);

            OBZone tmp_zone;
            ZeroMemory(tmp_zone);
            tmp_zone.high = g_sb_signal.break_level + bos_tolerance;
            tmp_zone.low  = g_sb_signal.break_level - bos_tolerance;
            tmp_zone.direction = g_sb_signal.direction;

            AddEntryMonitor(tmp, tmp_zone, mons, mon_count);

            if(g_sb_signal.monitor_attempts >= 5)
            {
                if(InpStructureLogBOS)
                    Print("[BOS] 超过最大尝试次数→放弃");
                g_sb_signal.state = BOS_IDLE;
                g_sb_signal.direction = 0;
                g_sb_signal.monitor_attempts = 0;
            }
        }
    }

}

// ── 双通道辅助：执行确认入场 ──
void ExecuteChannelConfirmed(OBZone& zones[], EAState& state,
                              EntryMonitor& mons[], int& mon_count,
                              double bid, double ask, string symbol)
{
    TradeSignal confirmed[10];

    // ── BOS Retest优先通道: 绕过双扫门控, H1结构突破信号不需要LP确认 ──
    bool allow_bos_direct = false;
    // 检查是否有活跃的BOS monitor
    for(int mi = 0; mi < mon_count; mi++)
    {
        if(mons[mi].active && mons[mi].ob_index >= 20000)
        {
            allow_bos_direct = true;
            break;
        }
    }

    // 标准双扫确认门控 (BOS信号绕过)
    if(!allow_bos_direct && !PassDoubleSweepConfirm(zones, state.ob_count, state.bar_count))
        return;

    SetMitigationContext(state.market_state);
    int conf_count = UpdateEntryMonitors(bid, ask, TimeCurrent(), mons, mon_count, confirmed, 10);
    for(int i = 0; i < conf_count; i++)
    {
        if(state.pos_count >= CfgMaxConcurrent()) break;

        // ── BOS双轨并行独立通道 ──
        if(confirmed[i].ob_index >= 20000 && allow_bos_direct)
        {
            // H4趋势过滤(仅拦逆大势BOS)
            if(g_trend_state_h4 == TREND_BULLISH && confirmed[i].direction == OB_SELL) continue;
            if(g_trend_state_h4 == TREND_BEARISH && confirmed[i].direction == OB_BUY) continue;

            // 共用state.pos_count(由SyncPositions自动管理)
            if(state.pos_count >= CfgMaxConcurrent()) continue;

            if(ExecuteSignalMTF(confirmed[i]))
            {
                state.pos_count++;
            }
            continue;
        }

        // MTF OB信号 (ob_index >= 10000) → 直接执行, 跳过v2 Finalize
        if(confirmed[i].ob_index >= 10000)
        {
            if(ExecuteSignalMTF(confirmed[i]))
            {
                state.last_entry_bar = state.bar_count;
                state.pos_count++;
            }
            continue;
        }

        // M1 OB信号 → 标准流程
        if(confirmed[i].ob_index < 0 || confirmed[i].ob_index >= state.ob_count) continue;

        // ══ BD08趋势方向锁+顺势宽TP ══
        bool h4_aligned = false;
        if(InpBOSRetestEntry && g_trend_state_h4 != TREND_UNKNOWN && g_trend_state_h4 != TREND_CHOP)
        {
            bool h4_bull = (g_trend_state_h4 == TREND_BULLISH);
            h4_aligned = (h4_bull && confirmed[i].direction == OB_BUY) ||
                        (!h4_bull && confirmed[i].direction == OB_SELL);
            if(!h4_aligned) continue;  // 逆势→拦截
        }

        // PathB: BOS-only(跳过Bounce)
        if(InpEnableBOSOnlyMode) continue;

        if(!FinalizeEntryEngineSignal(symbol, zones[confirmed[i].ob_index], state, confirmed[i])) continue;

        if(ExecuteSignal(confirmed[i]))
        {
            state.last_entry_bar = state.bar_count;
            state.pos_count++;
            // H4方向锁→结构止损模式(跳过DTP, M5结构管理)
            if(h4_aligned && g_track_count > 0)
                g_tracks[g_track_count-1].use_structure_sl = true;
        }
    }
}

// ── OnInit ──
int OnInit()
{
    ZeroMemory(g_state);
    ZeroMemory(g_zones);
    ZeroMemory(g_htf_zones);
    ZeroMemory(g_tracks);
    g_track_count = 0;
    g_htf_zone_count = 0;
    g_monitor_count = 0;
    g_htf_monitor_count = 0;
    ZeroMemory(g_state_osc);
    ZeroMemory(g_zones_osc);
    ZeroMemory(g_monitors_osc);
    g_monitor_count_osc = 0;
    g_last_entry_attempt = 0;

    // v3 SMC init
    g_trend_state = TREND_UNKNOWN;
    g_trend_state_h4 = TREND_UNKNOWN;
    g_trend_stable_bars = 0;
    g_trend_strength = 0.0;
    g_swing_point_count = 0;
    g_lpool_count = 0;
    g_structure_signal = SIG_NONE;
    ZeroMemory(g_swing_points);
    ZeroMemory(g_lpools);
    ZeroMemory(g_smc_data);
    ZeroMemory(g_ob_mitigations);
    ZeroMemory(g_ob_dead);
    InitSwingBreak();
    InitRegimeDetector();
    g_bos_pos_count = 0;

    if(CfgRiskPercent() <= 0 || CfgRiskPercent() > 50)
    {
        Print("参数错误: RiskPercent=", CfgRiskPercent());
        return INIT_PARAMETERS_INCORRECT;
    }

    SymbolSelect(_Symbol, true);
    SyncMonthlyRiskState();
    Print("WaiTrade3 ", InpVersion, " v1.00 SMC 已加载 | ", _Symbol, " | Magic=", InpMagicNumber);

    if(InpEnableStructureTracker)
        Print("  [SMC] 结构跟踪已启用");
    if(InpEnableLiquidityPool)
        Print("  [SMC] 流动性池已启用");

    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    Print("WaiTrade3 ", InpVersion, " v1.00 已卸载 | 原因=", reason);
}

// ── OnTick ──
void OnTick()
{
    string symbol = _Symbol;
    ENUM_TIMEFRAMES tf = GetWorkTF();

    // 月初重置
    if(InpMonthlyZoneReset)
    {
        static int s_prev_month = 0;
        MqlDateTime dt;
        TimeToStruct(TimeCurrent(), dt);
        int cur_month = dt.year * 100 + dt.mon;
        if(s_prev_month != 0 && cur_month != s_prev_month)
        {
            ZeroMemory(g_zones);
            ZeroMemory(g_htf_zones);
            g_state.ob_count = 0;
            g_htf_zone_count = 0;
            g_monitor_count = 0;
            g_htf_monitor_count = 0;
            g_state.last_entry_bar = 0;
            ZeroMemory(g_zones_osc);
            g_state_osc.ob_count = 0;
            g_monitor_count_osc = 0;
            g_state_osc.last_entry_bar = 0;
            // v3 SMC reset
            g_trend_state = TREND_UNKNOWN;
            g_trend_stable_bars = 0;
    g_trend_strength = 0.0;
            g_swing_point_count = 0;
            g_lpool_count = 0;
            g_structure_signal = SIG_NONE;
            ZeroMemory(g_swing_points);
            ZeroMemory(g_lpools);
            ZeroMemory(g_smc_data);
            Print("月初Zone+SMC重置 ", dt.year, ".", StringFormat("%02d", dt.mon));
        }
        s_prev_month = cur_month;
    }

    // 双通道/单通道切换清除
    bool s_dual = InpEnableDualZoneChannel && InpEnableXAUTrendProfile;
    if(InpEnableXAUTrendProfile && !s_dual)
    {
        static bool s_last_trend_profile = false;
        bool cur_trend = UseXAUTrendProfile();
        if(cur_trend != s_last_trend_profile)
        {
            ZeroMemory(g_zones);
            ZeroMemory(g_htf_zones);
            g_state.ob_count = 0;
            g_htf_zone_count = 0;
            g_monitor_count = 0;
            g_htf_monitor_count = 0;
            s_last_trend_profile = cur_trend;
            Print("Profile切换zone清除(单通道): ", cur_trend ? "→Trend" : "→FAGE");
        }
    }

    // 1. 加载K线数据
    ENUM_TIMEFRAMES act_tf = s_dual ? (ENUM_TIMEFRAMES)CfgMinutesToTF(InpXAUTrendBarTF) : tf;
    MqlRates rates[];
    int copied = CopyRates(symbol, act_tf, 0, InpBars, rates);
    if(copied < 100) {
        static datetime s_last_copy_fail = 0;
        if(TimeCurrent() - s_last_copy_fail >= 300) {
            s_last_copy_fail = TimeCurrent();
            Print("CopyRates失败: symbol=", symbol, " tf=", act_tf, " copied=", copied);
        }
        return;
    }

    g_state.atr_value = CalcATR(rates, copied, InpATRPeriod);

    // 2. 新bar处理
    bool new_bar = IsNewBar(symbol, act_tf);
    if(new_bar)
    {
        g_state.bar_count++;

        // v3 SMC: 结构跟踪（新bar更新）
        if(InpEnableStructureTracker)
        {
            TrendState old_trend = g_trend_state;
            UpdateStructureTracker(rates, copied, g_swing_points, g_swing_point_count,
                                  g_trend_state, g_state, g_structure_signal);
            // 趋势稳定性 + 强度
            if(g_trend_state == old_trend && g_trend_state != TREND_UNKNOWN)
                g_trend_stable_bars++;
            else
                g_trend_stable_bars = (g_trend_state != TREND_UNKNOWN) ? 1 : 0;

            // 计算趋势强度 + H4大周期结构
            g_trend_strength = CalcTrendStrength(g_swing_points, g_swing_point_count, g_trend_state);
            g_trend_state_h4 = DetectH4Trend(symbol, InpStructurePivotBars, 60);
        }

        // BOS回踩: swing突破检测 (独立于StructureTracker, 有自己的InpBOSRetestEntry开关)
        DetectSwingBreakInline(symbol, g_state.bar_count);

        // v3 H4趋势检测: StructureTracker或H4Adaptive或BOS Retest都需要H4方向
        // 每4小时更新一次, 减少CopyRates开销
        if(!InpEnableStructureTracker)
        {
            bool need_h4 = InpEnableH4Adaptive || InpBOSRetestEntry;
            if(need_h4)
            {
                static datetime s_last_h4_detect = 0;
                if(TimeCurrent() - s_last_h4_detect >= 14400 || g_trend_state_h4 == TREND_UNKNOWN)
                {
                    g_trend_state_h4 = DetectH4Trend(symbol, InpStructurePivotBars, 60);
                    s_last_h4_detect = TimeCurrent();
                }
            }
        }

        // v3 SMC: 流动性池检测（新bar扫描）
        if(InpEnableLiquidityPool)
        {
            DetectLiquidityPools(rates, copied, g_lpools, g_lpool_count, g_state);
        }

        DetectOrderBlocks(rates, copied, g_zones, g_state.ob_count, g_state);
        if(InpConsolidateOB) ConsolidateOBs(g_zones, g_state.ob_count);
        ExpireOldZones(g_zones, g_state.ob_count, g_state.bar_count);

        // v3: OB新鲜度追踪 (检测缓解次数/OB死亡)
        UpdateOBFreshness(g_zones, g_state.ob_count, rates, copied);

        // BOS回踩: 更新过期状态 + 更新体制检测
        // BOS age tracking is inside DetectSwingBreakInline
        if(InpEnableRegimeDetector || InpEnableBOSOnlyMode)
        {
            // 更新体制检测器输入
            g_regime.h4_trend = g_trend_state_h4;
            g_regime.active_ob_count = g_state.ob_count;

            // OB触碰追踪
            int max_touch = 0;
            for(int z = 0; z < g_state.ob_count; z++)
                if(g_zones[z].touch_count > max_touch)
                    max_touch = g_zones[z].touch_count;
            g_regime.max_ob_touches = max_touch;

            // BOS活跃度: 检查是否有BOS信号活跃或最近执行
            int bos_recent = 0;
            if(g_sb_signal.state == BOS_BREAK_DETECTED || g_sb_signal.state == BOS_RETEST_READY)
                bos_recent = 1;
            else if(g_sb_signal.state == BOS_EXECUTED && g_sb_signal.age_bars < 480)
                bos_recent = 1;
            g_regime.bos_signals_recent = bos_recent;

            UpdateRegime(symbol, g_state.bar_count);
        }


        // v3 SMC: 填充OB流动性关联标记（在评分前）
        if(InpEnableLiquidityPool && InpEnableOBScoring)
        {
            for(int z = 0; z < g_state.ob_count; z++)
            {
                g_smc_data[z].liquidity_linked = IsZoneLiquidityLinked(
                    g_zones[z], g_lpools, g_lpool_count, g_state.atr_value);
            }
        }

        // v3 SMC: OB评分赋值（在Consolidate后，Expire前）
        if(InpEnableOBScoring)
        {
            ScoreAllZones(g_zones, g_state.ob_count, g_state, g_smc_data, rates, copied, g_trend_state);
        }

        // v3 MTF: 多周期OB加权检测 (H4/H1 swing → HTF OB zone)
        if(InpEnableMultiTFOB)
        {
            DetectMultiTFOBs(symbol, g_state.bar_count);
            ScoreMTFConfluence();
            ExpireMTFZones(g_state.bar_count);
        }

        if(InpEnableHTFPullback && !InpHTFPullbackOnly)
        {
            CompactZones(g_htf_zones, g_htf_zone_count);
            DetectHTFPullbacks(g_htf_zones, g_htf_zone_count, g_state, GetSpread(symbol));
        }

        MqlRates rates_h1[];
        int h1_count = CopyRates(symbol, PERIOD_H1, 0, 100, rates_h1);
        if(h1_count > InpATRPeriod)
            g_state.atr_1h = CalcATR(rates_h1, h1_count, InpATRPeriod);

        int h1_dir = Detect1HOBDirection(symbol);
        Update1HAlignment(g_zones, g_state.ob_count, h1_dir);
        if(InpEnableHTFPullback && !InpHTFPullbackOnly)
            Update1HAlignment(g_htf_zones, g_htf_zone_count, h1_dir);

        if(CfgEnableStateFilter() || CfgEnableScoring())
        {
            double target = 0;
            g_state.market_state = (int)DetectMarketState(symbol, target);
            g_state.target_price = target;

            MqlRates rates_m15[];
            int m15_count = CopyRates(symbol, PERIOD_M15, 0, CfgTrendLookback(), rates_m15);
            if(m15_count > 14)
                g_state.atr_m15 = CalcATR(rates_m15, m15_count, InpATRPeriod);
        }
    }

    // 双通道：M3振荡通道
    bool new_osc_bar_tick = false;
    if(s_dual)
    {
        ENUM_TIMEFRAMES osc_tf = (ENUM_TIMEFRAMES)CfgMinutesToTF(InpBarTF);
        MqlRates osc_rates[];
        int osc_copied = CopyRates(symbol, osc_tf, 0, InpBars, osc_rates);
        if(osc_copied >= 100)
        {
            g_state_osc.atr_value = CalcATR(osc_rates, osc_copied, InpATRPeriod);
            bool new_osc = IsNewBar(symbol, osc_tf);
            new_osc_bar_tick = new_osc;
            if(new_osc)
            {
                g_state_osc.bar_count++;
                DetectOrderBlocks(osc_rates, osc_copied, g_zones_osc, g_state_osc.ob_count, g_state_osc);
                if(InpConsolidateOB) ConsolidateOBs(g_zones_osc, g_state_osc.ob_count);
                ExpireOldZones(g_zones_osc, g_state_osc.ob_count, g_state_osc.bar_count);

                MqlRates osc_h1[];
                int osc_h1c = CopyRates(symbol, PERIOD_H1, 0, 100, osc_h1);
                if(osc_h1c > InpATRPeriod)
                    g_state_osc.atr_1h = CalcATR(osc_h1, osc_h1c, InpATRPeriod);
                int osc_h1dir = Detect1HOBDirection(symbol);
                Update1HAlignment(g_zones_osc, g_state_osc.ob_count, osc_h1dir);

                if(CfgEnableStateFilter() || CfgEnableScoring())
                {
                    double osc_target = 0;
                    g_state_osc.market_state = (int)DetectMarketState(symbol, osc_target);
                    g_state_osc.target_price = osc_target;
                    MqlRates osc_m15[];
                    int osc_m15c = CopyRates(symbol, PERIOD_M15, 0, CfgTrendLookback(), osc_m15);
                    if(osc_m15c > 14)
                        g_state_osc.atr_m15 = CalcATR(osc_m15, osc_m15c, InpATRPeriod);
                }
            }
        }
    }

    // 3. 更新OB状态
    g_osc_active = s_dual && !UseXAUTrendProfile();
    double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
    UpdateOBStatus(g_zones, g_state.ob_count, bid, ask, g_state);
    UpdateFVGStatus(g_zones, g_state.ob_count, bid, ask, g_state);

    // v3 SMC: 更新流动性池状态（每tick）
    if(InpEnableLiquidityPool)
        UpdateLiquidityPools(g_lpools, g_lpool_count, bid, ask, g_state);

    if(s_dual)
    {
        UpdateOBStatus(g_zones_osc, g_state_osc.ob_count, bid, ask, g_state_osc);
        UpdateFVGStatus(g_zones_osc, g_state_osc.ob_count, bid, ask, g_state_osc);
    }
    else if(InpEnableHTFPullback && !InpHTFPullbackOnly)
        UpdateOBStatus(g_htf_zones, g_htf_zone_count, bid, ask, g_state);

    // 4. 扫描入场信号
    bool new_active_bar = g_osc_active ? new_osc_bar_tick : new_bar;

    if(g_osc_active)
        g_state_osc.pos_count = CountActivePositions();
    else
        g_state.pos_count = CountActivePositions();

    if(InpEnableEntryEngine)
    {
        if(g_osc_active)
            RegisterChannelMonitors(g_zones_osc, g_state_osc, g_monitors_osc, g_monitor_count_osc, new_active_bar, symbol);
        else
            RegisterChannelMonitors(g_zones, g_state, g_monitors, g_monitor_count, new_active_bar, symbol);

        if(!g_osc_active && new_bar && InpEnableHTFPullback && !InpHTFPullbackOnly)
        {
            for(int z = 0; z < g_htf_zone_count; z++)
            {
                if(g_htf_zones[z].expired || g_htf_zones[z].used) continue;
                if(!PassOBReentryCooldown(g_htf_zones[z])) continue;
                if(CfgEnableStateFilter() && g_state.market_state != 0 &&
                   g_state.market_state != g_htf_zones[z].direction) continue;

                TradeSignal tmp;
                ZeroMemory(tmp);
                tmp.direction  = g_htf_zones[z].direction;
                tmp.sl         = (g_htf_zones[z].direction == OB_BUY)
                    ? g_htf_zones[z].low  - g_state.atr_value * CfgSLBufferATR()
                    : g_htf_zones[z].high + g_state.atr_value * CfgSLBufferATR();
                tmp.risk_price = MathAbs(((g_htf_zones[z].high + g_htf_zones[z].low) / 2.0) - tmp.sl);
                tmp.ob_index   = z;
                tmp.pos_mult   = 1.0;
                AddEntryMonitor(tmp, g_htf_zones[z], g_htf_monitors, g_htf_monitor_count);
            }
        }

        // 5. 执行确认入场
        if(g_osc_active)
            ExecuteChannelConfirmed(g_zones_osc, g_state_osc, g_monitors_osc, g_monitor_count_osc, bid, ask, symbol);
        else
            ExecuteChannelConfirmed(g_zones, g_state, g_monitors, g_monitor_count, bid, ask, symbol);

        if(!g_osc_active && InpEnableHTFPullback && !InpHTFPullbackOnly)
        {
            if(PassDoubleSweepConfirm(g_htf_zones, g_htf_zone_count, g_state.bar_count, false))
            {
                TradeSignal htf_confirmed[10];
                SetMitigationContext(g_state.market_state);
                int htf_conf_count = UpdateEntryMonitors(bid, ask, TimeCurrent(), g_htf_monitors, g_htf_monitor_count, htf_confirmed, 10);
                for(int i = 0; i < htf_conf_count; i++)
                {
                    if(g_state.pos_count >= CfgMaxConcurrent()) break;
                    if(htf_confirmed[i].ob_index < 0 || htf_confirmed[i].ob_index >= g_htf_zone_count) continue;
                    if(!FinalizeEntryEngineSignal(symbol, g_htf_zones[htf_confirmed[i].ob_index], g_state, htf_confirmed[i])) continue;
                    if(ExecuteSignalFromZone(htf_confirmed[i], g_htf_zones, g_htf_zone_count, false))
                    {
                        g_state.last_entry_bar = g_state.bar_count;
                        g_state.pos_count++;
                    }
                }
            }
        }
    }
    else
    {
        int sig_count;
        if(g_osc_active)
        {
            sig_count = ScanSignals(symbol, g_zones_osc, g_state_osc.ob_count, g_state_osc, g_signals, 10);
            for(int i = 0; i < sig_count; i++)
            {
                if(g_state_osc.pos_count >= CfgMaxConcurrent()) break;
                if(!PassSMCDirectionGate(g_signals[i].direction)) continue;
                if(ExecuteSignal(g_signals[i])) { g_state_osc.last_entry_bar = g_state_osc.bar_count; g_state_osc.pos_count++; }
            }
        }
        else
        {
            sig_count = ScanSignals(symbol, g_zones, g_state.ob_count, g_state, g_signals, 10);
            for(int i = 0; i < sig_count; i++)
            {
                if(g_state.pos_count >= CfgMaxConcurrent()) break;
                if(!PassSMCDirectionGate(g_signals[i].direction)) continue;
                if(ExecuteSignal(g_signals[i])) { g_state.last_entry_bar = g_state.bar_count; g_state.pos_count++; }
            }
        }
    }

    // 6. 心跳
    {
        static datetime s_last_hb = 0;
        datetime now_t = TimeCurrent();
        if(now_t - s_last_hb >= 3600)
        {
            s_last_hb = now_t;
            double spread = (double)(SymbolInfoInteger(symbol, SYMBOL_SPREAD));
            Print("HEARTBEAT ", "WaiTrade3 v1.00", " | ", symbol, " ", EnumToString(tf),
                  " | bar=", g_state.bar_count,
                  " | ob=", g_state.ob_count,
                  " | pos=", g_state.pos_count,
                  " | atr=", DoubleToString(g_state.atr_value, _Digits),
                  " | spread=", spread,
                  " | state=", g_state.market_state,
                  " | trend=", g_trend_state,
                  " | H4=", g_trend_state_h4,
                  " | H4Adapt=", InpEnableH4Adaptive);
        }
    }

    // 7. 持仓管理
    SyncPositions(g_tracks, g_track_count);
    ManagePositions(g_tracks, g_track_count, g_state);

    // ══ BD08结构止损: 持仓管理器跳过DTP→EA层M5结构管理 ─═
    if(InpBOSRetestEntry && g_trend_state_h4 != TREND_UNKNOWN && g_trend_state_h4 != TREND_CHOP)
    {
        bool h4_bull = (g_trend_state_h4 == TREND_BULLISH);
        MqlRates m5[30];
        if(CopyRates(_Symbol, PERIOD_M15, 0, 30, m5) >= 10)  // M15抗噪
        {
            for(int t = 0; t < g_track_count; t++)
            {
                if(g_tracks[t].ticket == 0) continue;
                // 只处理H4方向的顺势持仓
                if((h4_bull && g_tracks[t].direction != OB_BUY) ||
                   (!h4_bull && g_tracks[t].direction != OB_SELL))
                    continue;

                // 找M5 swing high (做空用) 或 swing low (做多用)
                double structure_sl = 0;
                if(g_tracks[t].direction == OB_SELL)
                {
                    // SELL: 找最近M5摆动高点→SL放在其上方
                    for(int i = 2; i < 28; i++)
                        if(IsSwingHighV3(m5, i, 2))
                            { structure_sl = m5[i].high + g_state.atr_value * 2.0; break; }  // M15+1.5ATR宽缓冲
                }
                else
                {
                    for(int i = 2; i < 28; i++)
                        if(IsSwingLowV3(m5, i, 2))
                            { structure_sl = m5[i].low - g_state.atr_value * 2.0; break; }
                }

                if(structure_sl <= 0) continue;

                // 只在SL改善时更新(朝盈利方向移动)
                bool sl_improved = (g_tracks[t].direction == OB_SELL && structure_sl < g_tracks[t].sl_initial) ||
                                  (g_tracks[t].direction == OB_BUY && structure_sl > g_tracks[t].sl_initial);

                if(sl_improved && MathAbs(structure_sl - g_tracks[t].sl_initial) > g_state.atr_value * 0.3)
                {
                    if(ModifySL(g_tracks[t].ticket, structure_sl))
                    {
                        g_tracks[t].sl_initial = structure_sl;
                    }
                }
            }
        }
    }
}

// ── v3 SMC: 方向门控辅助 (非EntryEngine路径, 默认放行) ──
bool PassSMCDirectionGate(int direction)
{
    // 自适应出场已在 RegisterChannelMonitors 中处理逆势
    // 此函数保留向后兼容: 除非显式启用旧版二元拦截
    if(InpEnableStructureTracker && InpStructureBlockCounterTrend
       && g_trend_state != TREND_CHOP && g_trend_state != TREND_UNKNOWN)
    {
        if(InpStructureTrendStableBars > 0 && g_trend_stable_bars < InpStructureTrendStableBars)
            return true;
        if(!IsDirectionAlignedWithTrend(direction, g_trend_state))
        {
            if(InpStructureLogBOS)
                Print("[SMC] 旧版门控拦截(非EntryEngine) dir=", direction, " trend=", g_trend_state);
            return false;
        }
    }
    return true;
}

// ── 辅助函数 ──
int CountActivePositions()
{
    if(CfgFreeRunMinR() <= 0)
        return CountPositions();
    int count = 0;
    for(int i = 0; i < g_track_count; i++)
    {
        if(g_tracks[i].ticket == 0) continue;
        if(g_tracks[i].peak_profit_r >= CfgFreeRunMinR())
            continue;
        count++;
    }
    return count;
}

bool ShouldSkipEntryAttempt()
{
    if(CfgCloseRetryCooldownSec() <= 0)
        return false;
    datetime now = TimeCurrent();
    return (g_last_entry_attempt > 0 &&
            now - g_last_entry_attempt < CfgCloseRetryCooldownSec());
}

void MarkEntryAttemptFailed()
{
    if(CfgCloseRetryCooldownSec() <= 0)
        return;
    datetime now = TimeCurrent();
    g_last_entry_attempt = now;
}

// ── MTF OB信号执行 (宽SL, 权重仓位, 无分层/微仓) ──
bool ExecuteSignalMTF(const TradeSignal &sig)
{
    if(ShouldSkipEntryAttempt())
        return false;

    // MTF仓位计算: 基于risk_price的固定风险仓位 × 权重
    double base_lot = CalcLotSize(_Symbol, CfgRiskPercent(), sig.risk_price);
    double mtf_lot = NormalizeDouble(base_lot * sig.pos_mult, 2);
    double lot_min = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    double lot_max = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
    if(mtf_lot < lot_min) mtf_lot = lot_min;
    if(CfgMaxLotSize() > 0 && mtf_lot > CfgMaxLotSize()) mtf_lot = CfgMaxLotSize();
    if(mtf_lot > lot_max) mtf_lot = lot_max;

    MqlTradeRequest request = {};
    MqlTradeResult  result  = {};

    string dir_str = (sig.direction > 0) ? "B" : "S";
    string tf_str = "";
    int mz = sig.ob_index - 10000;
    if(mz >= 0 && mz < g_mtf_zone_count)
        tf_str = EnumToString(g_mtf_zones[mz].tf);

    string comment = StringFormat("WT %s MTF %s x%.1f", InpVersion, dir_str, sig.pos_mult);

    request.action    = TRADE_ACTION_DEAL;
    request.symbol    = _Symbol;
    request.volume    = sig.lot;
    request.type      = sig.direction > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    request.price     = sig.direction > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                          : SymbolInfoDouble(_Symbol, SYMBOL_BID);
    request.volume    = mtf_lot;
    request.sl        = BrokerStopFromVirtualSL(sig.sl, request.price, sig.risk_price, sig.direction);
    request.tp        = sig.tp;
    request.magic     = InpMagicNumber;
    request.comment   = comment;
    request.deviation = 20;
    request.type_filling = ORDER_FILLING_IOC;
    request.type_time    = ORDER_TIME_GTC;

    if(!OrderSend(request, result))
    {
        if(result.retcode == 10016 || result.retcode == TRADE_RETCODE_INVALID_STOPS)
        {
            static int s_invalid_stops = 0;
            s_invalid_stops++;
            if(s_invalid_stops <= 10)
                Print("[MTF] 止损无效: ", comment, " sl=", DoubleToString(sig.sl, _Digits));
            return false;
        }
        static int s_fail = 0;
        s_fail++;
        if(s_fail <= 10)
            Print("[MTF] 开仓失败: ", result.comment, " retcode=", result.retcode);
        MarkEntryAttemptFailed();
        return false;
    }

    if(result.retcode == TRADE_RETCODE_DONE)
    {
        Print("[MTF] 开仓成功: ", comment, " ticket=", result.order,
              " price=", result.price, " lot=", sig.lot,
              " sl=", DoubleToString(request.sl, _Digits),
              " tf=", tf_str, " weight=", DoubleToString(sig.pos_mult, 1));

        RecordMonthlyEntry();
        RecordRuntimeEntry();
        RegisterPosition(result.order, sig.direction, result.price, sig.sl, sig.risk_price,
                         false, 0, 0, 0, false, g_tracks, g_track_count);

        if(g_track_count > 0)
        {
            g_tracks[g_track_count - 1].open_bar = g_state.bar_count;
            g_tracks[g_track_count - 1].entry_market_state = g_state.market_state;
        }

        // MTF OB标记
        MarkMTFZoneUsed(mz);

        return true;
    }

    return false;
}

bool ExecuteSignal(const TradeSignal &sig)
{
    return ExecuteSignalFromZone(sig, g_zones, g_state.ob_count, true);
}

bool ExecuteSignalFromZone(const TradeSignal &sig, OBZone &zones[], int zone_count, bool allow_layered)
{
    if(ShouldSkipEntryAttempt())
        return false;

    MqlTradeRequest request = {};
    MqlTradeResult  result  = {};

    request.action    = TRADE_ACTION_DEAL;
    request.symbol    = _Symbol;
    request.volume    = sig.lot;
    request.type      = sig.direction > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    request.price     = sig.direction > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                          : SymbolInfoDouble(_Symbol, SYMBOL_BID);
    request.sl        = BrokerStopFromVirtualSL(sig.sl, request.price, sig.risk_price, sig.direction);
    request.tp        = sig.tp;
    request.magic     = InpMagicNumber;
    request.comment   = sig.comment;
    request.deviation = 20;
    request.type_filling = ORDER_FILLING_IOC;
    request.type_time    = ORDER_TIME_GTC;

    if(!OrderSend(request, result))
    {
        if(result.retcode == 10016)
        {
            static int s_invalid_stops_count = 0;
            s_invalid_stops_count++;
            if(s_invalid_stops_count <= 10 || s_invalid_stops_count % 1000 == 0)
                Print("止损无效(已跳过", s_invalid_stops_count, "次): ", sig.comment);
            if(sig.ob_index >= 0 && sig.ob_index < zone_count)
                zones[sig.ob_index].used = true;
            return false;
        }

        if(result.retcode == TRADE_RETCODE_REQUOTE)
        {
            request.price = sig.direction > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                              : SymbolInfoDouble(_Symbol, SYMBOL_BID);
            if(!OrderSend(request, result))
            {
                Print("开仓失败(重试): ", result.comment, " retcode=", result.retcode);
                MarkEntryAttemptFailed();
                return false;
            }
        }
        else
        {
            static int s_fail_count = 0;
            s_fail_count++;
            if(s_fail_count <= 10 || s_fail_count % 500 == 0)
                Print("开仓失败(第", s_fail_count, "次): ", result.comment, " retcode=", result.retcode);
            MarkEntryAttemptFailed();
            return false;
        }
    }

    if(result.retcode == TRADE_RETCODE_DONE)
    {
        Print("开仓成功: ", sig.comment, " ticket=", result.order,
              " price=", result.price, " lot=", sig.lot,
              " bounce_sec=", sig.bounce_seconds,
              " bounce_ob=", DoubleToString(sig.bounce_ob_pct, 3),
              " confirm_pos=", DoubleToString(sig.confirm_ob_pos, 3),
              " touch=", DoubleToString(sig.touch_price, _Digits),
              " confirm=", DoubleToString(sig.confirm_price, _Digits));

        RecordMonthlyEntry();
        RecordRuntimeEntry();
        RegisterPosition(result.order, sig.direction, result.price, sig.sl, sig.risk_price,
                         sig.deep_entry,
                         sig.htf_target, sig.htf_partial_r, sig.htf_partial_pct,
                         sig.failure_reverse,
                         g_tracks, g_track_count);

        if(g_track_count > 0)
        {
            g_tracks[g_track_count - 1].open_bar = g_state.bar_count;
            g_tracks[g_track_count - 1].entry_market_state = g_state.market_state;
        }

        if(allow_layered && InpLayeredEntryCount >= 2)
            ExecuteLayeredOrders(sig, result.price);
        ExecuteMicroEntryOrders(sig);

        // BOS retest (ob_index >= 20000) vs MTF OB (>= 10000) vs M1 OB
        if(sig.ob_index >= 20000)
        {
            g_sb_signal.state = BOS_EXECUTED;
            g_sb_signal.age_bars = 0;
        }
        else if(sig.ob_index >= 10000)
            MarkMTFZoneUsed(sig.ob_index - 10000);
        else if(sig.ob_index >= 0 && sig.ob_index < zone_count)
            MarkZoneUsed(zones, sig.ob_index);

        return true;
    }

    return false;
}

bool ExecuteLayeredOrders(const TradeSignal &sig, double base_price)
{
    if(InpLayeredEntryCount < 2) return false;
    if(sig.ob_index < 0 || sig.ob_index >= g_state.ob_count) return false;

    double ob_h = g_zones[sig.ob_index].high - g_zones[sig.ob_index].low;
    if(ob_h <= 0) return false;

    double spacing = ob_h * InpLayeredSpacingPct;
    int layers = MathMin(InpLayeredEntryCount - 1, 3);

    for(int i = 1; i <= layers; i++)
    {
        double offset = spacing * i;
        double limit_price = (sig.direction > 0) ? base_price - offset : base_price + offset;

        double lot_mult = 1.0 + (InpLayeredLotMult - 1.0) * i / layers;
        double layer_lot = NormalizeDouble(sig.lot * lot_mult, 2);
        double lot_min = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
        if(layer_lot < lot_min) layer_lot = lot_min;

        MqlTradeRequest req = {};
        MqlTradeResult  res = {};
        req.action = TRADE_ACTION_PENDING;
        req.symbol = _Symbol;
        req.volume = layer_lot;
        req.type   = (sig.direction > 0) ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
        req.price  = NormalizeDouble(limit_price, _Digits);
        double layer_risk = MathAbs(limit_price - sig.sl);
        req.sl     = BrokerStopFromVirtualSL(sig.sl, limit_price, layer_risk, sig.direction);
        req.tp     = sig.tp;
        req.magic  = InpMagicNumber;
        req.comment = sig.comment + "_L" + IntegerToString(i+1);
        req.deviation = 20;
        req.type_filling = ORDER_FILLING_RETURN;
        req.type_time = ORDER_TIME_GTC;

        if(OrderSend(req, res))
        {
            if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
                Print("分层挂单L", i+1, ": price=", req.price, " lot=", layer_lot);
        }
    }
    return true;
}

bool ExecuteMicroEntryOrders(const TradeSignal &sig)
{
    if(InpMicroEntryCount <= 0 || InpMicroEntryLotMult <= 0)
        return false;

    int count = MathMin(InpMicroEntryCount, 5);
    double lot_min = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    if(InpMicroEntryMaxLotSize > 0 && InpMicroEntryMaxLotSize < lot_min)
        return false;

    double micro_lot = sig.lot * InpMicroEntryLotMult;
    if(InpMicroEntryMaxLotSize > 0 && micro_lot > InpMicroEntryMaxLotSize)
        micro_lot = InpMicroEntryMaxLotSize;
    micro_lot = NormalizeDouble(micro_lot, 2);
    if(micro_lot < lot_min)
        micro_lot = lot_min;

    bool placed = false;
    for(int i = 1; i <= count; i++)
    {
        MqlTradeRequest req = {};
        MqlTradeResult  res = {};
        req.action    = TRADE_ACTION_DEAL;
        req.symbol    = _Symbol;
        req.volume    = micro_lot;
        req.type      = sig.direction > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
        req.price     = sig.direction > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                          : SymbolInfoDouble(_Symbol, SYMBOL_BID);
        req.sl        = BrokerStopFromVirtualSL(sig.sl, req.price, sig.risk_price, sig.direction);
        req.tp        = sig.tp;
        req.magic     = InpMagicNumber;
        req.comment   = sig.comment + "_M" + IntegerToString(i);
        req.deviation = 20;
        req.type_filling = ORDER_FILLING_IOC;
        req.type_time    = ORDER_TIME_GTC;

        if(!OrderSend(req, res) || res.retcode != TRADE_RETCODE_DONE)
            continue;

        placed = true;
        Print("微仓副单成功 ", req.comment, " ticket=", res.order,
              " price=", res.price, " lot=", micro_lot);
        RecordMonthlyEntry();
        RecordRuntimeEntry();
        RegisterPosition(res.order, sig.direction, res.price, sig.sl, sig.risk_price,
                         sig.deep_entry,
                         sig.htf_target, sig.htf_partial_r, sig.htf_partial_pct,
                         sig.failure_reverse,
                         g_tracks, g_track_count);
        if(g_track_count > 0)
        {
            g_tracks[g_track_count - 1].open_bar = g_state.bar_count;
            g_tracks[g_track_count - 1].entry_market_state = g_state.market_state;
        }
    }

    return placed;
}
