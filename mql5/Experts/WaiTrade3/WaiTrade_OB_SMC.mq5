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
    int    last_entry_age;    // H4持久结构位上次入场时的信号年龄
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
    g_sb_signal.last_entry_age = 0;
    g_sb_inited = true;
}

bool FinalizeEntryEngineSignal(string symbol, const OBZone &zone, const EAState &state,
                               TradeSignal &signal);
bool ExecuteSignalFromZone(const TradeSignal &sig, OBZone &zones[], int zone_count, bool allow_layered);

int EntryFamilyFromSignal(const TradeSignal &sig, const OBZone &zone)
{
    if(StringFind(sig.comment, "SDFLIP") >= 0) return ENTRY_FAMILY_SDFLIP;
    if(StringFind(sig.comment, "REVSWP") >= 0) return ENTRY_FAMILY_REVSWP;
    if(StringFind(sig.comment, "MBOS") >= 0) return ENTRY_FAMILY_MBOS;
    if(StringFind(sig.comment, "BOS") >= 0) return ENTRY_FAMILY_BOS;
    if(StringFind(sig.comment, "FVG") >= 0 || zone.is_fvg) return ENTRY_FAMILY_FVG;
    if(zone.is_htf_pullback || StringFind(sig.comment, "HTFPB") >= 0) return ENTRY_FAMILY_HTFPB;
    if(zone.is_liquidity_sweep || IsLooseSweepZone(zone) ||
       StringFind(sig.comment, "SWP") >= 0 || StringFind(sig.comment, "LSWP") >= 0)
        return ENTRY_FAMILY_SWP;
    if(sig.ob_index >= 10000) return ENTRY_FAMILY_MTF;
    return ENTRY_FAMILY_OB;
}

int EntryFamilyFromSignalNoZone(const TradeSignal &sig)
{
    if(StringFind(sig.comment, "SDFLIP") >= 0) return ENTRY_FAMILY_SDFLIP;
    if(StringFind(sig.comment, "REVSWP") >= 0) return ENTRY_FAMILY_REVSWP;
    if(StringFind(sig.comment, "MBOS") >= 0) return ENTRY_FAMILY_MBOS;
    if(StringFind(sig.comment, "BOS") >= 0) return ENTRY_FAMILY_BOS;
    if(StringFind(sig.comment, "HTRG") >= 0) return ENTRY_FAMILY_MTF;
    if(StringFind(sig.comment, "FVG") >= 0) return ENTRY_FAMILY_FVG;
    if(StringFind(sig.comment, "HTFPB") >= 0) return ENTRY_FAMILY_HTFPB;
    if(StringFind(sig.comment, "SWP") >= 0 || StringFind(sig.comment, "LSWP") >= 0)
        return ENTRY_FAMILY_SWP;
    if(sig.ob_index >= 10000) return ENTRY_FAMILY_MTF;
    return ENTRY_FAMILY_OB;
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

double DirectionalNetBodyATR(const MqlRates &rates[], int count, int direction, int lookback, double atr)
{
    if(atr <= 0 || count < lookback + 2) return 0.0;
    double net = 0.0;
    int used = MathMin(lookback, count - 1);
    for(int i = 1; i <= used; i++)
        net += (rates[i].close - rates[i].open) * direction;
    return net / atr;
}

bool HasStrongReverseCandle(const MqlRates &rates[], int count, int direction, int lookback, double atr)
{
    if(atr <= 0 || count < lookback + 2) return false;
    int used = MathMin(lookback, count - 1);
    for(int i = 1; i <= used; i++)
    {
        double reverse_body = (rates[i].open - rates[i].close) * direction;
        if(reverse_body >= atr * InpStructMomStrongRevBodyATR)
            return true;
    }
    return false;
}

bool HasMicroReverseBreak(const MqlRates &rates[], int count, int direction, double atr)
{
    if(atr <= 0 || count < 8) return false;
    double buffer = atr * InpStructMomBreakBufferATR;
    double last_close = rates[1].close;
    double swing_high = 0.0;
    double swing_low = 999999.0;

    for(int i = 2; i < MathMin(count - 2, 18); i++)
    {
        if(swing_high <= 0 && IsSwingHighV3(rates, i, 1))
            swing_high = rates[i].high;
        if(swing_low >= 999999.0 && IsSwingLowV3(rates, i, 1))
            swing_low = rates[i].low;
    }
    if(swing_high <= 0)
        for(int i = 2; i < MathMin(count, 12); i++)
            swing_high = MathMax(swing_high, rates[i].high);
    if(swing_low >= 999999.0)
        for(int i = 2; i < MathMin(count, 12); i++)
            swing_low = MathMin(swing_low, rates[i].low);

    if(direction == OB_BUY)
        return (swing_low < 999999.0 && last_close < swing_low - buffer);
    return (swing_high > 0 && last_close > swing_high + buffer);
}

bool HasFullReverseExitOnTF(const MqlRates &rates[], int count, int direction,
                            int lookback, double atr)
{
    if(atr <= 0 || count < lookback + 2) return false;
    if(!HasMicroReverseBreak(rates, count, direction, atr)) return false;
    if(!CheckMomentumWeakness(_Symbol, direction, rates, count)) return false;

    int reverse_dir = (direction == OB_BUY) ? OB_SELL : OB_BUY;
    double reverse_net = DirectionalNetBodyATR(rates, count, reverse_dir, lookback, atr);
    return (reverse_net >= InpStructMomMinNetATR ||
            CheckStrongMomentum(_Symbol, reverse_dir, rates, count));
}

bool ShouldHoldStructureMomentum(const PosTrack &track)
{
    if(!InpEnableStructureMomentumHold) return false;
    if(!PositionSelectByTicket(track.ticket)) return false;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r <= 0.0) return false;

    int lookback = MathMax(2, InpStructMomLookbackBars);
    MqlRates m5[32], m15[32];
    int m5_count = CopyRates(_Symbol, PERIOD_M5, 0, 32, m5);
    int m15_count = CopyRates(_Symbol, PERIOD_M15, 0, 32, m15);
    if(m5_count < lookback + 2 || m15_count < lookback + 2) return false;

    double atr_m5 = CalcATR(m5, m5_count, 14);
    double atr_m15 = CalcATR(m15, m15_count, 14);
    if(atr_m5 <= 0 || atr_m15 <= 0) return false;

    if(InpStructMomRequireFullReverseExit && current_r >= InpStructMomFullReverseMinR)
    {
        bool m5_full_reverse = HasFullReverseExitOnTF(m5, m5_count, track.direction, lookback, atr_m5);
        bool m15_full_reverse = HasFullReverseExitOnTF(m15, m15_count, track.direction, lookback, atr_m15);
        return !(m5_full_reverse || m15_full_reverse);
    }

    bool m5_reverse = HasMicroReverseBreak(m5, m5_count, track.direction, atr_m5) ||
                      HasStrongReverseCandle(m5, m5_count, track.direction, lookback, atr_m5);
    bool m15_reverse = HasMicroReverseBreak(m15, m15_count, track.direction, atr_m15) ||
                       HasStrongReverseCandle(m15, m15_count, track.direction, lookback, atr_m15);
    if(m5_reverse || m15_reverse) return false;

    double m5_net = DirectionalNetBodyATR(m5, m5_count, track.direction, lookback, atr_m5);
    double m15_net = DirectionalNetBodyATR(m15, m15_count, track.direction, lookback, atr_m15);
    return (m5_net >= InpStructMomMinNetATR || m15_net >= InpStructMomMinNetATR);
}

bool HasStructureHoldReleaseOnTF(const MqlRates &rates[], int count, int direction,
                                 int lookback, double atr)
{
    if(atr <= 0.0 || count < lookback + 2)
        return false;

    bool reverse = HasMicroReverseBreak(rates, count, direction, atr) ||
                   HasStrongReverseCandle(rates, count, direction, lookback, atr);
    if(!reverse)
        return false;

    double forward_net = DirectionalNetBodyATR(rates, count, direction, lookback, atr);
    if(forward_net >= InpStructMomMinNetATR ||
       CheckStrongMomentum(_Symbol, direction, rates, count))
        return false;

    if(!CheckMomentumWeakness(_Symbol, direction, rates, count))
        return false;

    if(InpStructureHoldReleaseRequireReverseContinuation)
    {
        int reverse_dir = (direction == OB_BUY) ? OB_SELL : OB_BUY;
        double reverse_net = DirectionalNetBodyATR(rates, count, reverse_dir, lookback, atr);
        if(reverse_net < InpStructMomMinNetATR &&
           !CheckStrongMomentum(_Symbol, reverse_dir, rates, count))
            return false;
    }

    return true;
}

bool ShouldReleaseStructureHold(const PosTrack &track)
{
    if(!InpStructureHoldDynamicRelease) return false;
    if(!track.use_structure_sl) return false;
    if(!PositionSelectByTicket(track.ticket)) return false;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r < InpStructureHoldReleaseMinR)
        return false;

    int lookback = MathMax(2, InpStructMomLookbackBars);
    MqlRates m5[32], m15[32];
    int m5_count = CopyRates(_Symbol, PERIOD_M5, 0, 32, m5);
    int m15_count = CopyRates(_Symbol, PERIOD_M15, 0, 32, m15);
    if(m5_count < lookback + 2 || m15_count < lookback + 2)
        return false;

    double atr_m5 = CalcATR(m5, m5_count, 14);
    double atr_m15 = CalcATR(m15, m15_count, 14);
    if(atr_m5 <= 0.0 || atr_m15 <= 0.0)
        return false;

    return (HasStructureHoldReleaseOnTF(m5, m5_count, track.direction, lookback, atr_m5) ||
            HasStructureHoldReleaseOnTF(m15, m15_count, track.direction, lookback, atr_m15));
}

void UpdateStructureHoldRelease(PosTrack &tracks[], int track_count)
{
    if(!InpStructureHoldDynamicRelease)
        return;
    for(int i = 0; i < track_count; i++)
    {
        if(tracks[i].ticket == 0 || !tracks[i].use_structure_sl)
            continue;
        if(!ShouldReleaseStructureHold(tracks[i]))
            continue;

        tracks[i].use_structure_sl = false;
        tracks[i].skip_mfe_exits = false;
        if(InpStructureLogBOS)
            Print("STRUCT_HOLD_RELEASE ticket=", tracks[i].ticket,
                  " dir=", tracks[i].direction);
    }
}

bool HasBOSLockCounterMomentum(int direction)
{
    if(!InpBOSLockAllowCounterMomentum)
        return false;

    int lookback = MathMax(1, InpBOSLockCounterMomentumBars);
    ENUM_TIMEFRAMES tf = MinutesToTF(InpBOSLockCounterMomentumTF);
    int need = MathMin(lookback + 16, 64);

    MqlRates rates[64];
    int count = CopyRates(_Symbol, tf, 0, need, rates);
    if(count < lookback + 2)
        return false;

    double atr = CalcATR(rates, count, 14);
    if(atr <= 0)
        return false;

    double net = DirectionalNetBodyATR(rates, count, direction, lookback, atr);
    return (net >= InpBOSLockCounterMomentumMinATR);
}


// ── H4 BOS: 大周期结构突破(独立于H1 BOS) ──
bool HasCounterBreakOnTF(int direction, ENUM_TIMEFRAMES tf, int lookback)
{
    int need = MathMin(MathMax(lookback + 16, 24), 64);
    MqlRates rates[64];
    int count = CopyRates(_Symbol, tf, 0, need, rates);
    if(count < lookback + 8)
        return false;

    double atr = CalcATR(rates, count, 14);
    if(atr <= 0)
        return false;

    double net = DirectionalNetBodyATR(rates, count, direction, lookback, atr);
    if(net < InpBOSLockCounterBreakMinATR)
        return false;

    double buffer = atr * MathMax(InpBOSLockCounterBreakBufferATR, 0.0);
    double last_close = rates[1].close;
    double swing_high = 0.0;
    double swing_low = 999999.0;
    int limit = MathMin(count - 2, 18);

    for(int i = 2; i < limit; i++)
    {
        if(swing_high <= 0 && IsSwingHighV3(rates, i, 1))
            swing_high = rates[i].high;
        if(swing_low >= 999999.0 && IsSwingLowV3(rates, i, 1))
            swing_low = rates[i].low;
    }
    if(swing_high <= 0)
    {
        for(int i = 2; i < MathMin(count, 12); i++)
            swing_high = MathMax(swing_high, rates[i].high);
    }
    if(swing_low >= 999999.0)
    {
        for(int i = 2; i < MathMin(count, 12); i++)
            swing_low = MathMin(swing_low, rates[i].low);
    }

    if(direction == OB_BUY)
        return (swing_high > 0.0 && last_close > swing_high + buffer);
    return (swing_low < 999999.0 && last_close < swing_low - buffer);
}

bool HasBOSLockCounterBreak(int direction)
{
    if(!InpBOSLockAllowCounterBreak)
        return false;

    int lookback = MathMax(2, InpBOSLockCounterBreakBars);
    ENUM_TIMEFRAMES tf = MinutesToTF(InpBOSLockCounterBreakTF);
    return HasCounterBreakOnTF(direction, tf, lookback);
}

bool HasBOSLockCounterBounce(const TradeSignal &signal)
{
    if(!InpBOSLockAllowCounterBounce)
        return false;
    if(InpBOSLockCounterBounceSecMax <= 0)
        return false;
    if(signal.bounce_seconds < InpBOSLockCounterBounceSecMin)
        return false;
    if(signal.bounce_seconds > InpBOSLockCounterBounceSecMax)
        return false;
    return true;
}

bool IsPlainSupplyDemandZone(const OBZone &zone)
{
    return !zone.is_fvg &&
           !zone.is_liquidity_sweep &&
           !zone.is_loose_sweep &&
           !zone.is_range_breakout &&
           !zone.is_htf_pullback;
}

bool HasMicroBOSZoneConfluence(int direction, double level, double atr)
{
    if(!InpMicroBOSRequireZoneConfluence)
        return true;
    if(InpMicroBOSConfluenceToleranceATR < 0.0)
        return true;
    if(level <= 0.0 || atr <= 0.0)
        return false;

    double tolerance = atr * MathMax(InpMicroBOSConfluenceToleranceATR, 0.0);
    for(int z = 0; z < g_state.ob_count; z++)
    {
        if(g_zones[z].expired || g_zones[z].used)
            continue;
        if(g_zones[z].direction != direction)
            continue;

        bool is_valid_source = (InpMicroBOSConfluenceAllowFVG && g_zones[z].is_fvg) ||
                               (InpMicroBOSConfluenceAllowOB && IsPlainSupplyDemandZone(g_zones[z]));
        if(!is_valid_source)
            continue;

        if(level >= g_zones[z].low - tolerance && level <= g_zones[z].high + tolerance)
            return true;
    }
    return false;
}

bool HasMicroBOSHTFBoundaryConfluence(int direction, const MqlRates &rates[], int count, double atr)
{
    if(!InpMicroBOSRequireZoneConfluence)
        return true;
    if(InpMicroBOSConfluenceToleranceATR >= 0.0)
        return true;
    if(atr <= 0.0 || count < 4)
        return false;

    HTFRange range = GetHTFRange(_Symbol);
    if(!range.valid)
        return false;

    double tolerance = atr * MathAbs(InpMicroBOSConfluenceToleranceATR);
    int lookback = MathMin(count - 1, 8);
    double recent_low = rates[1].low;
    double recent_high = rates[1].high;
    for(int i = 2; i <= lookback; i++)
    {
        recent_low = MathMin(recent_low, rates[i].low);
        recent_high = MathMax(recent_high, rates[i].high);
    }

    if(direction == OB_BUY)
        return recent_low <= range.bottom_zone_high + tolerance;
    return recent_high >= range.top_zone_low - tolerance;
}

static int g_micro_bos_htf_reject_dir = 0;
static datetime g_micro_bos_htf_reject_time = 0;
static double g_micro_bos_htf_reject_low = 0.0;
static double g_micro_bos_htf_reject_high = 0.0;
static double g_micro_bos_htf_reject_atr = 0.0;
static bool g_micro_bos_htf_reject_used = false;

void ResetHTFRejectContext()
{
    g_micro_bos_htf_reject_dir = 0;
    g_micro_bos_htf_reject_time = 0;
    g_micro_bos_htf_reject_low = 0.0;
    g_micro_bos_htf_reject_high = 0.0;
    g_micro_bos_htf_reject_atr = 0.0;
    g_micro_bos_htf_reject_used = false;
}

void RecordHTFRejectContext(int direction, datetime event_time,
                            double event_low = 0.0, double event_high = 0.0,
                            double event_atr = 0.0)
{
    if(direction == 0 || event_time <= 0)
        return;
    bool same_event = (g_micro_bos_htf_reject_dir == direction &&
                       g_micro_bos_htf_reject_time == event_time);
    g_micro_bos_htf_reject_dir = direction;
    g_micro_bos_htf_reject_time = event_time;
    if(event_low > 0.0 && event_high > event_low)
    {
        g_micro_bos_htf_reject_low = event_low;
        g_micro_bos_htf_reject_high = event_high;
    }
    if(event_atr > 0.0)
        g_micro_bos_htf_reject_atr = event_atr;
    if(!same_event)
        g_micro_bos_htf_reject_used = false;
    if(InpStructureLogBOS)
        Print("HTF_REJECT_CONTEXT dir=", direction == OB_BUY ? "BUY" : "SELL",
              " time=", TimeToString(event_time));
}

void UpdateMicroBOSHTFRejectEvent(const MqlRates &rates[], int count, double atr)
{
    if(!InpMicroBOSRequireZoneConfluence || InpMicroBOSConfluenceToleranceATR >= 0.0)
        return;
    if(atr <= 0.0 || count < 3)
        return;

    HTFRange range = GetHTFRange(_Symbol);
    if(!range.valid)
        return;

    double tolerance = atr * MathAbs(InpMicroBOSConfluenceToleranceATR);
    MqlRates bar = rates[1];
    double body = MathAbs(bar.close - bar.open);
    double lower_wick = MathMin(bar.open, bar.close) - bar.low;
    double upper_wick = bar.high - MathMax(bar.open, bar.close);

    bool bottom_reject =
        bar.low <= range.bottom_zone_high + tolerance &&
        bar.close > range.bottom_zone_high &&
        lower_wick >= MathMax(body, atr * 0.20);
    bool top_reject =
        bar.high >= range.top_zone_low - tolerance &&
        bar.close < range.top_zone_low &&
        upper_wick >= MathMax(body, atr * 0.20);

    if(bottom_reject)
    {
        RecordHTFRejectContext(OB_BUY, bar.time, bar.low, bar.high, atr);
        if(InpStructureLogBOS)
            Print("MICRO_BOS_HTF_REJECT dir=BUY time=", TimeToString(bar.time),
                  " low=", DoubleToString(bar.low, _Digits),
                  " boundary=", DoubleToString(range.bottom_zone_high, _Digits));
    }
    else if(top_reject)
    {
        RecordHTFRejectContext(OB_SELL, bar.time, bar.low, bar.high, atr);
        if(InpStructureLogBOS)
            Print("MICRO_BOS_HTF_REJECT dir=SELL time=", TimeToString(bar.time),
                  " high=", DoubleToString(bar.high, _Digits),
                  " boundary=", DoubleToString(range.top_zone_low, _Digits));
    }
}

void UpdateHTFRejectContextFromRange(const MqlRates &rates[], int count, double atr)
{
    if(!CfgRangeHTFRejectContextEnabled())
        return;
    if(atr <= 0.0 || count < 3)
        return;

    HTFRange range = GetHTFRange(_Symbol);
    if(!range.valid)
        return;

    double tolerance = atr * MathMax(CfgRangeBoundaryToleranceATR(), 0.05);
    MqlRates bar = rates[1];
    double body = MathAbs(bar.close - bar.open);
    double lower_wick = MathMin(bar.open, bar.close) - bar.low;
    double upper_wick = bar.high - MathMax(bar.open, bar.close);

    bool bottom_reject =
        bar.low <= range.bottom_zone_high + tolerance &&
        bar.close > range.bottom_zone_high &&
        lower_wick >= MathMax(body, atr * 0.20);
    bool top_reject =
        bar.high >= range.top_zone_low - tolerance &&
        bar.close < range.top_zone_low &&
        upper_wick >= MathMax(body, atr * 0.20);

    if(bottom_reject)
        RecordHTFRejectContext(OB_BUY, bar.time, bar.low, bar.high, atr);
    else if(top_reject)
        RecordHTFRejectContext(OB_SELL, bar.time, bar.low, bar.high, atr);
}

bool HasRecentMicroBOSHTFReject(int direction, datetime break_time)
{
    if(!InpMicroBOSRequireZoneConfluence || InpMicroBOSConfluenceToleranceATR >= 0.0)
        return true;
    if(g_micro_bos_htf_reject_dir != direction || g_micro_bos_htf_reject_time <= 0)
        return false;

    int max_age_sec = MathMax(InpMicroBOSMaxBars, 1) * MathMax(InpMicroBOSTF, 1) * 60;
    int age = (int)(break_time - g_micro_bos_htf_reject_time);
    return (age >= 0 && age <= max_age_sec);
}

bool HasRecentHTFRejectContext(int direction)
{
    if(!CfgRangeHTFRejectContextEnabled())
        return false;
    if(g_micro_bos_htf_reject_dir != direction || g_micro_bos_htf_reject_time <= 0)
        return false;
    int max_age_sec = MathMax(CfgRangeMinBars() * 4, 30) * 60;
    int age = (int)(TimeCurrent() - g_micro_bos_htf_reject_time);
    return (age >= 0 && age <= max_age_sec);
}

bool HasHTFRejectPullbackContext(int direction)
{
    if(!CfgRangeHTFRejectContextOnly())
        return false;
    if(g_micro_bos_htf_reject_used)
        return false;
    if(g_micro_bos_htf_reject_dir != direction || g_micro_bos_htf_reject_time <= 0)
        return false;

    int max_age_sec = MathMax(CfgRangeMinBars() * 4, 30) * 60;
    if(CfgRangeTF() >= 1440)
        max_age_sec = MathMax(max_age_sec, MathMax(CfgRangeUpdateBars(), 1) * 3600);
    int age = (int)(TimeCurrent() - g_micro_bos_htf_reject_time);
    return (age >= 0 && age <= max_age_sec);
}

void MarkHTFRejectPullbackUsed()
{
    g_micro_bos_htf_reject_used = true;
}

void UpdateStrongWickRejectContext(string symbol)
{
    if(!CfgRangeHTFRejectContextEnabled())
        return;

    ENUM_TIMEFRAMES tf = MinutesToTF(MathMax(CfgRangeMinBars(), 1));
    MqlRates rates[80];
    int copied = CopyRates(symbol, tf, 0, 80, rates);
    if(copied < InpATRPeriod + 4)
        return;

    double atr = CalcATR(rates, copied, InpATRPeriod);
    if(atr <= 0.0)
        return;

    MqlRates bar = rates[1];
    double range = bar.high - bar.low;
    if(range < atr * MathMax(CfgRangeMinWidthATR(), 0.80))
        return;

    double body = MathAbs(bar.close - bar.open);
    double lower_wick = MathMin(bar.open, bar.close) - bar.low;
    double upper_wick = bar.high - MathMax(bar.open, bar.close);
    double close_pos = (range > 0.0) ? (bar.close - bar.low) / range : 0.5;

    bool buy_reject =
        lower_wick >= MathMax(body * 1.20, atr * 0.45) &&
        close_pos >= 0.65;
    bool sell_reject =
        upper_wick >= MathMax(body * 1.20, atr * 0.45) &&
        close_pos <= 0.35;

    if(buy_reject)
        RecordHTFRejectContext(OB_BUY, bar.time, bar.low, bar.high, atr);
    else if(sell_reject)
        RecordHTFRejectContext(OB_SELL, bar.time, bar.low, bar.high, atr);
}

bool ShouldUseHTFRejectHold(const TradeSignal &sig, int entry_family)
{
    if(!CfgRangeHTFRejectContextEnabled())
        return false;
    if(StringFind(sig.comment, "RGREACT") >= 0)
        return false;
    if(entry_family != ENTRY_FAMILY_OB && entry_family != ENTRY_FAMILY_SWP)
        return false;
    return HasRecentHTFRejectContext(sig.direction);
}

void AddMicroBOSZone(int direction, double level, double atr, datetime break_time, int bar_count,
                     bool htf_boundary_ok)
{
    if(!InpEnableMicroBOSRetest)
        return;
    if(g_micro_bos_zone_count >= MAX_OB_ZONES)
    {
        g_micro_bos_skip_capacity++;
        return;
    }
    if(atr <= 0.0 || level <= 0.0)
    {
        g_micro_bos_skip_invalid++;
        return;
    }
    if(InpMicroBOSRequireZoneConfluence &&
       InpMicroBOSConfluenceToleranceATR < 0.0 &&
       !htf_boundary_ok &&
       !HasRecentMicroBOSHTFReject(direction, break_time))
    {
        g_micro_bos_skip_confluence++;
        return;
    }
    if(!HasMicroBOSZoneConfluence(direction, level, atr))
    {
        g_micro_bos_skip_confluence++;
        return;
    }

    double height = atr * MathMax(InpMicroBOSZoneATR, 0.05);
    double tolerance = atr * MathMax(InpMicroBOSRetestToleranceATR, 0.0);
    double sl_dist = atr * MathMax(InpMicroBOSSLATR, 0.10);

    OBZone zone = {};
    if(direction == OB_BUY)
    {
        zone.low = level - tolerance;
        zone.high = zone.low + height;
    }
    else
    {
        zone.high = level + tolerance;
        zone.low = zone.high - height;
    }
    if(zone.high <= zone.low)
    {
        g_micro_bos_skip_invalid++;
        return;
    }

    for(int z = 0; z < g_micro_bos_zone_count; z++)
    {
        if(g_micro_bos_zones[z].expired || g_micro_bos_zones[z].used)
            continue;
        if(g_micro_bos_zones[z].direction != direction)
            continue;
        if(MathAbs(g_micro_bos_zones[z].mid - level) < atr * 0.20)
        {
            g_micro_bos_skip_duplicate++;
            return;
        }
    }

    zone.mid = level;
    zone.ob_top = zone.high;
    zone.ob_bottom = zone.low;
    zone.direction = direction;
    zone.created = break_time;
    zone.created_bar = bar_count;
    zone.touch_count = 0;
    zone.first_touch = 0;
    zone.last_touch = 0;
    zone.strength = 3.0;
    zone.is_fresh = true;
    zone.is_continuation = true;
    zone.is_1h_aligned = false;
    zone.ds_weight = 1.0;
    zone.entry_count = 0;
    zone.last_entry_time = 0;
    zone.used = false;
    zone.expired = false;
    zone.is_range_breakout = false;
    zone.is_liquidity_sweep = false;
    zone.is_loose_sweep = false;
    zone.is_htf_pullback = false;
    zone.range_height = 0.0;

    g_micro_bos_zones[g_micro_bos_zone_count] = zone;
    g_micro_bos_zone_count++;
    g_micro_bos_generated++;

    if(InpStructureLogBOS)
        Print("MICRO_BOS_ZONE dir=", direction,
              " level=", DoubleToString(level, _Digits),
              " zone=", DoubleToString(zone.low, _Digits), "..", DoubleToString(zone.high, _Digits),
              " sl_dist=", DoubleToString(sl_dist, _Digits));
}

void DetectMicroBOSRetestZones(string symbol, int bar_count)
{
    if(!InpEnableMicroBOSRetest)
        return;

    CompactZones(g_micro_bos_zones, g_micro_bos_zone_count);
    ExpireOldZones(g_micro_bos_zones, g_micro_bos_zone_count, bar_count);

    if(g_micro_bos_cooldown > 0)
    {
        g_micro_bos_cooldown--;
        return;
    }

    ENUM_TIMEFRAMES tf = MinutesToTF(InpMicroBOSTF);
    int lookback = MathMax(InpMicroBOSLookbackBars, 16);
    int pivot = MathMax(1, MathMin(InpMicroBOSPivotBars, 4));
    int need = MathMin(MathMax(lookback + pivot + InpATRPeriod + 4, 80), 180);

    MqlRates rates[180];
    int count = CopyRates(symbol, tf, 0, need, rates);
    if(count < lookback + pivot + 4)
        return;

    static datetime s_last_micro_bar = 0;
    if(rates[0].time == s_last_micro_bar)
        return;
    s_last_micro_bar = rates[0].time;

    double atr = CalcATR(rates, count, InpATRPeriod);
    if(atr <= 0.0)
        return;
    UpdateMicroBOSHTFRejectEvent(rates, count, atr);

    double swing_high = 0.0;
    double swing_low = 0.0;
    int limit = MathMin(count - pivot, lookback);
    for(int i = pivot + 2; i < limit; i++)
    {
        if(swing_high <= 0.0 && IsSwingHighV3(rates, i, pivot))
            swing_high = rates[i].high;
        if(swing_low <= 0.0 && IsSwingLowV3(rates, i, pivot))
            swing_low = rates[i].low;
        if(swing_high > 0.0 && swing_low > 0.0)
            break;
    }
    if(swing_high <= 0.0 || swing_low <= 0.0)
        return;

    double buffer = atr * MathMax(InpMicroBOSBreakBufferATR, 0.0);
    int look = MathMax(2, MathMin(6, count - 2));
    double buy_net = DirectionalNetBodyATR(rates, count, OB_BUY, look, atr);
    double sell_net = DirectionalNetBodyATR(rates, count, OB_SELL, look, atr);

    bool buy_break = (rates[2].close <= swing_high + buffer &&
                      rates[1].close > swing_high + buffer &&
                      rates[1].high >= swing_high + atr * MathMax(InpMicroBOSExtensionATR, 0.0) &&
                      buy_net >= InpMicroBOSMinNetATR);
    bool sell_break = (rates[2].close >= swing_low - buffer &&
                       rates[1].close < swing_low - buffer &&
                       rates[1].low <= swing_low - atr * MathMax(InpMicroBOSExtensionATR, 0.0) &&
                       sell_net >= InpMicroBOSMinNetATR);

    if(!buy_break && !sell_break)
        return;
    if(g_micro_bos_last_break_time == rates[1].time)
        return;

    g_micro_bos_detect_events++;
    bool buy_htf_boundary = buy_break ? HasMicroBOSHTFBoundaryConfluence(OB_BUY, rates, count, atr) : false;
    bool sell_htf_boundary = sell_break ? HasMicroBOSHTFBoundaryConfluence(OB_SELL, rates, count, atr) : false;
    if(buy_break)
        AddMicroBOSZone(OB_BUY, swing_high, atr, rates[1].time, bar_count, buy_htf_boundary);
    if(sell_break)
        AddMicroBOSZone(OB_SELL, swing_low, atr, rates[1].time, bar_count, sell_htf_boundary);

    g_micro_bos_last_break_time = rates[1].time;
}

bool PassStrongSweepDP(int direction, string symbol)
{
    if(!InpStrongSweepRequireDP)
        return true;

    ENUM_TIMEFRAMES tf = MinutesToTF(InpStrongSweepDPTF);
    int lookback = MathMax(InpStrongSweepDPLookbackBars, 8);
    int need = MathMin(MathMax(lookback + 4, 24), 220);
    MqlRates rates[220];
    int copied = CopyRates(symbol, tf, 0, need, rates);
    if(copied < lookback + 2)
        return false;

    double htf_high = rates[1].high;
    double htf_low = rates[1].low;
    for(int i = 2; i <= lookback && i < copied; i++)
    {
        htf_high = MathMax(htf_high, rates[i].high);
        htf_low = MathMin(htf_low, rates[i].low);
    }
    double range = htf_high - htf_low;
    if(range <= 0.0)
        return false;

    double ratio = (rates[1].close - htf_low) / range;
    if(direction == OB_BUY)
        return ratio <= InpStrongSweepDiscountMax;
    return ratio >= InpStrongSweepPremiumMin;
}

bool IsStrongSweepTouchingHTFOB(int direction, double extreme, string symbol)
{
    if(!InpStrongSweepUseStructureHold || !CfgRangeHTFRejectContextOnly())
        return true;
    if(extreme <= 0.0)
        return false;

    ENUM_TIMEFRAMES tf = PERIOD_D1;
    int min_base = 5;
    int max_base = 28;
    int lookback = 90;
    int need = MathMin(MathMax(lookback + InpATRPeriod + 12, 80), 260);

    MqlRates rates[260];
    int count = CopyRates(symbol, tf, 1, need, rates);
    if(count < max_base + 8)
        return false;

    double atr = CalcATR(rates, count, InpATRPeriod);
    if(atr <= 0.0)
        return false;

    int max_end = MathMin(count - 4, lookback);
    double max_width_atr = 8.0;
    double depart_atr = 0.35;
    double touch_buffer = atr * 0.25;

    for(int end_idx = 3; end_idx < max_end; end_idx++)
    {
        for(int base_len = min_base; base_len <= max_base; base_len++)
        {
            int start_idx = end_idx + base_len - 1;
            if(start_idx >= count)
                continue;

            double zone_high = rates[end_idx].high;
            double zone_low = rates[end_idx].low;
            double body_sum = 0.0;
            double range_sum = 0.0;
            for(int i = end_idx; i <= start_idx; i++)
            {
                zone_high = MathMax(zone_high, rates[i].high);
                zone_low = MathMin(zone_low, rates[i].low);
                body_sum += MathAbs(rates[i].close - rates[i].open);
                range_sum += MathMax(rates[i].high - rates[i].low, _Point);
            }

            double width = zone_high - zone_low;
            if(width <= 0.0 || width / atr > max_width_atr)
                continue;
            if(range_sum > 0.0 && body_sum / range_sum > 0.62)
                continue;

            double depart_close = rates[end_idx - 1].close;
            bool departed_up = depart_close > zone_high + atr * depart_atr;
            bool departed_down = depart_close < zone_low - atr * depart_atr;
            if(direction == OB_BUY && !departed_up)
                continue;
            if(direction == OB_SELL && !departed_down)
                continue;

            if(direction == OB_BUY &&
               extreme >= zone_low - touch_buffer &&
               extreme <= zone_high + atr * 1.20)
                return true;
            if(direction == OB_SELL &&
               extreme <= zone_high + touch_buffer &&
               extreme >= zone_low - atr * 1.20)
                return true;
        }
    }

    return false;
}

void UpgradeHTFOBTouchHolds(PosTrack &tracks[], int track_count)
{
    if(!CfgRangeHTFRejectContextOnly())
        return;
    if(!InpEnableStrongSweepReversal || !InpStrongSweepUseStructureHold)
        return;

    for(int i = 0; i < track_count; i++)
    {
        if(tracks[i].ticket == 0)
            continue;
        if(tracks[i].htf_target && tracks[i].skip_mfe_exits)
            continue;
        if(tracks[i].entry_family != ENTRY_FAMILY_OB && tracks[i].entry_family != ENTRY_FAMILY_SWP)
            continue;
        if(!PositionSelectByTicket(tracks[i].ticket))
            continue;

        double price = PositionGetDouble(POSITION_PRICE_CURRENT);
        if(price <= 0.0)
            continue;
        if(!IsStrongSweepTouchingHTFOB(tracks[i].direction, price, _Symbol))
            continue;
        tracks[i].htf_target = true;
        tracks[i].skip_mfe_exits = true;
        if(InpEnableEntryDebug)
            Print("HTFOB_HOLD_UPGRADE ticket=", tracks[i].ticket,
                  " dir=", tracks[i].direction,
                  " price=", DoubleToString(price, _Digits));
    }
}

bool PassPlainSweepDPGate(const OBZone &zone, int direction)
{
    if(InpEnableStrongSweepReversal)
        return true;
    if(!InpStrongSweepUseStructureHold)
        return true;
    if(!InpStrongSweepRequireDP)
        return true;
    if(!zone.is_liquidity_sweep && !IsLooseSweepZone(zone))
        return true;
    return PassStrongSweepDP(direction, _Symbol);
}

void AddStrongSweepReversalZone(int direction, double level, double extreme,
                                double atr, datetime sweep_time, int bar_count)
{
    if(g_rev_sweep_zone_count >= MAX_OB_ZONES || atr <= 0.0 || level <= 0.0 || extreme <= 0.0)
        return;

    if(!PassStrongSweepDP(direction, _Symbol))
    {
        g_rev_sweep_skip_dp++;
        return;
    }
    if(!IsStrongSweepTouchingHTFOB(direction, extreme, _Symbol))
    {
        g_rev_sweep_skip_dp++;
        return;
    }

    for(int z = 0; z < g_rev_sweep_zone_count; z++)
    {
        if(g_rev_sweep_zones[z].expired || g_rev_sweep_zones[z].used)
            continue;
        if(g_rev_sweep_zones[z].direction != direction)
            continue;
        if(MathAbs(g_rev_sweep_zones[z].mid - level) < atr * 0.20)
        {
            g_rev_sweep_skip_duplicate++;
            return;
        }
    }

    double height = atr * MathMax(InpStrongSweepZoneATR, 0.05);
    OBZone zone = {};
    if(direction == OB_BUY)
    {
        zone.low = extreme;
        zone.high = MathMin(level + height, level + atr * 0.80);
    }
    else
    {
        zone.high = extreme;
        zone.low = MathMax(level - height, level - atr * 0.80);
    }
    if(zone.high <= zone.low)
        return;

    zone.mid = level;
    zone.ob_top = zone.high;
    zone.ob_bottom = zone.low;
    zone.direction = direction;
    zone.created = sweep_time;
    zone.created_bar = bar_count;
    zone.touch_count = 0;
    zone.first_touch = 0;
    zone.last_touch = 0;
    zone.strength = 3.0;
    zone.is_fresh = true;
    zone.is_continuation = false;
    zone.is_1h_aligned = false;
    zone.ds_weight = 1.0;
    zone.entry_count = 0;
    zone.last_entry_time = 0;
    zone.used = false;
    zone.expired = false;
    zone.is_range_breakout = false;
    zone.is_liquidity_sweep = true;
    zone.is_loose_sweep = false;
    zone.is_htf_pullback = false;
    zone.range_height = MathAbs(level - extreme);

    g_rev_sweep_zones[g_rev_sweep_zone_count] = zone;
    g_rev_sweep_zone_count++;
    g_rev_sweep_generated++;
}

void DetectStrongSweepReversalZones(string symbol, int bar_count)
{
    if(!InpEnableStrongSweepReversal)
        return;

    CompactZones(g_rev_sweep_zones, g_rev_sweep_zone_count);
    ExpireSignalZones(g_rev_sweep_zones, g_rev_sweep_zone_count, bar_count, InpStrongSweepMaxBars);

    if(g_rev_sweep_cooldown > 0)
    {
        g_rev_sweep_cooldown--;
        return;
    }

    ENUM_TIMEFRAMES tf = MinutesToTF(InpStrongSweepTF);
    int lookback = MathMax(InpStrongSweepLookbackBars, 16);
    int pivot = MathMax(1, MathMin(InpStrongSweepPivotBars, 5));
    int need = MathMin(MathMax(lookback + pivot + InpATRPeriod + 6, 80), 220);
    MqlRates rates[220];
    int count = CopyRates(symbol, tf, 0, need, rates);
    if(count < lookback + pivot + 4)
        return;

    static datetime s_last_rev_sweep_bar = 0;
    if(rates[0].time == s_last_rev_sweep_bar)
        return;
    s_last_rev_sweep_bar = rates[0].time;

    double atr = CalcATR(rates, count, InpATRPeriod);
    if(atr <= 0.0)
        return;

    double swing_high = 0.0;
    double swing_low = 0.0;
    int limit = MathMin(count - pivot, lookback);
    for(int i = pivot + 2; i < limit; i++)
    {
        if(swing_high <= 0.0 && IsSwingHighV3(rates, i, pivot))
            swing_high = rates[i].high;
        if(swing_low <= 0.0 && IsSwingLowV3(rates, i, pivot))
            swing_low = rates[i].low;
        if(swing_high > 0.0 && swing_low > 0.0)
            break;
    }
    if(swing_high <= 0.0 || swing_low <= 0.0)
        return;

    double penetration = atr * MathMax(InpStrongSweepPenetrationATR, 0.0);
    double close_back = atr * MathMax(InpStrongSweepCloseBackATR, 0.0);
    double candle_range = rates[1].high - rates[1].low;
    if(candle_range <= 0.0)
        return;

    double body_high = MathMax(rates[1].open, rates[1].close);
    double body_low = MathMin(rates[1].open, rates[1].close);
    double upper_wick_pct = (rates[1].high - body_high) / candle_range * 100.0;
    double lower_wick_pct = (body_low - rates[1].low) / candle_range * 100.0;

    bool swept_high = rates[1].high > swing_high + penetration &&
                      rates[1].close < swing_high - close_back &&
                      upper_wick_pct >= InpStrongSweepWickPct;
    bool swept_low = rates[1].low < swing_low - penetration &&
                     rates[1].close > swing_low + close_back &&
                     lower_wick_pct >= InpStrongSweepWickPct;

    if(!swept_high && !swept_low)
        return;
    if(g_rev_sweep_last_time == rates[1].time)
        return;

    g_rev_sweep_detect_events++;
    if(swept_high)
        AddStrongSweepReversalZone(OB_SELL, swing_high, rates[1].high, atr, rates[1].time, bar_count);
    if(swept_low)
        AddStrongSweepReversalZone(OB_BUY, swing_low, rates[1].low, atr, rates[1].time, bar_count);
    g_rev_sweep_last_time = rates[1].time;
}

void ExpireSignalZones(OBZone &zones[], int zone_count, int bar_count, int max_bars)
{
    if(max_bars <= 0)
        return;
    for(int z = 0; z < zone_count; z++)
    {
        if(zones[z].expired)
            continue;
        if(bar_count - zones[z].created_bar > max_bars)
            zones[z].expired = true;
    }
}

void UpdateSignalZoneTouches(OBZone &zones[], int zone_count, double bid, double ask)
{
    datetime now = TimeCurrent();
    for(int z = 0; z < zone_count; z++)
    {
        if(zones[z].expired || zones[z].used)
            continue;

        bool touched = false;
        if(zones[z].direction == OB_BUY && bid <= zones[z].high)
            touched = true;
        else if(zones[z].direction == OB_SELL && ask >= zones[z].low)
            touched = true;

        if(touched)
        {
            zones[z].touch_count++;
            zones[z].last_touch = now;
            if(zones[z].first_touch == 0)
                zones[z].first_touch = now;
            zones[z].is_fresh = false;
        }
    }
}

void AddSupplyDemandFlipZone(int direction, const OBZone &source, double atr, datetime break_time, int bar_count)
{
    if(!InpEnableSupplyDemandFlip)
        return;
    if(g_sd_flip_zone_count >= MAX_OB_ZONES)
        return;
    if(atr <= 0.0 || source.high <= source.low)
        return;

    double tolerance = atr * MathMax(InpSDFlipRetestToleranceATR, 0.0);
    double height = atr * MathMax(InpSDFlipZoneATR, 0.05);
    double level = (direction == OB_BUY) ? source.high : source.low;

    OBZone zone = {};
    if(direction == OB_BUY)
    {
        zone.high = level + tolerance;
        zone.low = zone.high - height;
    }
    else
    {
        zone.low = level - tolerance;
        zone.high = zone.low + height;
    }
    if(zone.high <= zone.low)
        return;

    for(int z = 0; z < g_sd_flip_zone_count; z++)
    {
        if(g_sd_flip_zones[z].expired || g_sd_flip_zones[z].used)
            continue;
        if(g_sd_flip_zones[z].direction != direction)
            continue;
        if(MathAbs(g_sd_flip_zones[z].mid - level) < atr * 0.25)
            return;
    }

    zone.mid = level;
    zone.ob_top = zone.high;
    zone.ob_bottom = zone.low;
    zone.direction = direction;
    zone.created = break_time;
    zone.created_bar = bar_count;
    zone.touch_count = 0;
    zone.first_touch = 0;
    zone.last_touch = 0;
    zone.strength = MathMax(source.strength, 3.0);
    zone.is_fresh = true;
    zone.is_continuation = true;
    zone.is_1h_aligned = false;
    zone.ds_weight = 1.0;
    zone.entry_count = 0;
    zone.last_entry_time = 0;
    zone.used = false;
    zone.expired = false;
    zone.is_range_breakout = false;
    zone.is_liquidity_sweep = false;
    zone.is_loose_sweep = false;
    zone.is_htf_pullback = false;
    zone.range_height = 0.0;

    g_sd_flip_zones[g_sd_flip_zone_count] = zone;
    g_sd_flip_zone_count++;
    g_sd_flip_generated++;

    if(InpStructureLogBOS)
        Print("SD_FLIP_ZONE dir=", direction,
              " level=", DoubleToString(level, _Digits),
              " source=", DoubleToString(source.low, _Digits), "..", DoubleToString(source.high, _Digits),
              " zone=", DoubleToString(zone.low, _Digits), "..", DoubleToString(zone.high, _Digits));
}

void DetectSupplyDemandFlips(string symbol, OBZone &zones[], int zone_count, int bar_count)
{
    if(!InpEnableSupplyDemandFlip)
        return;

    CompactZones(g_sd_flip_zones, g_sd_flip_zone_count);
    ExpireSignalZones(g_sd_flip_zones, g_sd_flip_zone_count, bar_count, InpSDFlipMaxBars);

    if(g_sd_flip_cooldown > 0)
    {
        g_sd_flip_cooldown--;
        return;
    }

    ENUM_TIMEFRAMES tf = MinutesToTF(InpSDFlipTF);
    int need = MathMin(MathMax(InpATRPeriod + 12, 48), 96);
    MqlRates rates[96];
    int count = CopyRates(symbol, tf, 0, need, rates);
    if(count < InpATRPeriod + 4)
        return;

    static datetime s_last_sd_flip_bar = 0;
    if(rates[0].time == s_last_sd_flip_bar)
        return;
    s_last_sd_flip_bar = rates[0].time;

    double atr = CalcATR(rates, count, InpATRPeriod);
    if(atr <= 0.0)
        return;

    double body = MathAbs(rates[1].close - rates[1].open);
    if(body < atr * MathMax(InpSDFlipMinBodyATR, 0.0))
        return;

    double buffer = atr * MathMax(InpSDFlipBreakBufferATR, 0.0);
    bool bullish_body = rates[1].close > rates[1].open;
    bool bearish_body = rates[1].close < rates[1].open;

    if(InpSDFlipRequireSourceOB)
    {
        for(int z = 0; z < zone_count; z++)
        {
            if(zones[z].expired || zones[z].used)
                continue;
            if(zones[z].high <= zones[z].low)
                continue;

            if(zones[z].direction == OB_SELL && bullish_body &&
               rates[2].close <= zones[z].high + buffer &&
               rates[1].close > zones[z].high + buffer)
            {
            if(g_sd_flip_last_break_time != rates[1].time)
            {
                g_sd_flip_detect_events++;
                AddSupplyDemandFlipZone(OB_BUY, zones[z], atr, rates[1].time, bar_count);
                g_sd_flip_last_break_time = rates[1].time;
            }
                return;
            }

            if(zones[z].direction == OB_BUY && bearish_body &&
               rates[2].close >= zones[z].low - buffer &&
               rates[1].close < zones[z].low - buffer)
            {
            if(g_sd_flip_last_break_time != rates[1].time)
            {
                g_sd_flip_detect_events++;
                AddSupplyDemandFlipZone(OB_SELL, zones[z], atr, rates[1].time, bar_count);
                g_sd_flip_last_break_time = rates[1].time;
            }
                return;
            }
        }
        return;
    }

    int lookback = MathMax(8, MathMin(InpSDFlipLookbackBars, count - 4));
    double prior_high = rates[3].high;
    double prior_low = rates[3].low;
    for(int i = 3; i < lookback + 3 && i < count; i++)
    {
        prior_high = MathMax(prior_high, rates[i].high);
        prior_low = MathMin(prior_low, rates[i].low);
    }

    OBZone synthetic = {};
    if(bullish_body &&
       rates[2].close <= prior_high + buffer &&
       rates[1].close > prior_high + buffer)
    {
        synthetic.low = prior_high - atr * 0.10;
        synthetic.high = prior_high;
        synthetic.direction = OB_SELL;
        synthetic.strength = 3.0;
        if(g_sd_flip_last_break_time != rates[1].time)
        {
            g_sd_flip_detect_events++;
            AddSupplyDemandFlipZone(OB_BUY, synthetic, atr, rates[1].time, bar_count);
            g_sd_flip_last_break_time = rates[1].time;
        }
        return;
    }

    if(bearish_body &&
       rates[2].close >= prior_low - buffer &&
       rates[1].close < prior_low - buffer)
    {
        synthetic.low = prior_low;
        synthetic.high = prior_low + atr * 0.10;
        synthetic.direction = OB_BUY;
        synthetic.strength = 3.0;
        if(g_sd_flip_last_break_time != rates[1].time)
        {
            g_sd_flip_detect_events++;
            AddSupplyDemandFlipZone(OB_SELL, synthetic, atr, rates[1].time, bar_count);
            g_sd_flip_last_break_time = rates[1].time;
        }
        return;
    }
}

void DetectH4BOS(string symbol)
{
    if(!InpBOSRetestEntry) return;
    if(g_sb_signal.state == BOS_BREAK_DETECTED || g_sb_signal.state == BOS_RETEST_READY)
        return;
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
    bool h4_buy_break = InpBOSStrictCloseBreak
        ? (sh > 0 && h4[2].close <= sh && h4[1].close > sh)
        : (sh > 0 && h4[1].high < sh && h4[0].high > sh);
    bool h4_sell_break = InpBOSStrictCloseBreak
        ? (sl < 999999 && h4[2].close >= sl && h4[1].close < sl)
        : (sl < 999999 && h4[1].low > sl && h4[0].low < sl);

    if(h4_buy_break) {
        g_sb_signal.break_level=sh; g_sb_signal.direction=OB_BUY;
        g_sb_signal.atr=h4_atr*0.3; g_sb_signal.h1_atr=h4_atr;
        g_sb_signal.sl_price=sh-h4_atr*0.3*InpBOSRetestSLBuffer;
        g_sb_signal.age_bars=0; g_sb_signal.state=BOS_BREAK_DETECTED;
        g_sb_signal.monitor_attempts=0; g_sb_signal.from_h4=true;
        g_sb_signal.custom_max_bars=7200;  // H4: 5天窗口
        g_sb_signal.break_time=h4[0].time;
        g_sb_signal.custom_max_bars=MathMax(InpBOSRetestMaxBars * 10, 7200);
        g_sb_signal.last_entry_age=-999999;
        g_sb_signal.break_time=h4[0].time;
        g_sb_signal.extension_extreme=h4[0].high;
        if(InpStructureLogBOS) Print("[BOS-H4] H4突破: ",sh," H4ATR=",h4_atr);
    }
    if(h4_sell_break) {
        g_sb_signal.break_level=sl; g_sb_signal.direction=OB_SELL;
        g_sb_signal.atr=h4_atr*0.3; g_sb_signal.h1_atr=h4_atr;
        g_sb_signal.sl_price=sl+h4_atr*0.3*InpBOSRetestSLBuffer;
        g_sb_signal.age_bars=0; g_sb_signal.state=BOS_BREAK_DETECTED;
        g_sb_signal.monitor_attempts=0; g_sb_signal.from_h4=true;
        g_sb_signal.custom_max_bars=7200;  // H4: 5天窗口
        g_sb_signal.break_time=h4[0].time;
        g_sb_signal.custom_max_bars=MathMax(InpBOSRetestMaxBars * 10, 7200);
        g_sb_signal.last_entry_age=-999999;
        g_sb_signal.break_time=h4[0].time;
        g_sb_signal.extension_extreme=h4[0].low;
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
            g_sb_signal.last_entry_age = 0;
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
        if(g_sb_signal.from_h4)
        {
            int max_bars = (g_sb_signal.custom_max_bars > 0)
                ? g_sb_signal.custom_max_bars : InpBOSRetestMaxBars;
            if(g_sb_signal.age_bars >= max_bars)
            {
                g_sb_signal.state = BOS_IDLE;
                g_sb_signal.direction = 0;
                g_sb_signal.monitor_attempts = 0;
                g_sb_signal.from_h4 = false;
                g_sb_signal.custom_max_bars = 0;
                g_sb_signal.last_entry_age = 0;
                return;
            }
            if(g_sb_signal.age_bars - g_sb_signal.last_entry_age < 360)
                return;
            g_sb_signal.state = BOS_RETEST_READY;
            g_sb_signal.monitor_attempts = 0;
            return;
        }
        if(g_sb_signal.age_bars < 30) return;
        g_sb_signal.state = BOS_IDLE;
        g_sb_signal.direction = 0;
        g_sb_signal.monitor_attempts = 0;
        g_sb_signal.from_h4 = false;
        g_sb_signal.custom_max_bars = 0;
        g_sb_signal.last_entry_age = 0;
    }

    // ── 状态: IDLE → 检测H1 swing突破 ──
    // 每个H1 bar检测一次
    static datetime s_last_check = 0;
    MqlRates h1_rates[];
    int h1_count = CopyRates(symbol, PERIOD_H1, 0, 3, h1_rates);
    if(h1_count < 3) return;
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
    double prev_high = InpBOSStrictCloseBreak ? h1_rates[2].close : h1_rates[1].high;
    double curr_high = InpBOSStrictCloseBreak ? h1_rates[1].close : h1_rates[0].high;
    double prev_low_fix = InpBOSStrictCloseBreak ? h1_rates[2].close : h1_rates[1].low;
    double curr_low_fix = InpBOSStrictCloseBreak ? h1_rates[1].close : h1_rates[0].low;

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
        g_sb_signal.h1_atr = h1_atr;
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

OBZone      g_micro_bos_zones[MAX_OB_ZONES];
EntryMonitor g_micro_bos_monitors[MAX_MONITORS];
int          g_micro_bos_zone_count = 0;
int          g_micro_bos_monitor_count = 0;
datetime     g_micro_bos_last_break_time = 0;
int          g_micro_bos_cooldown = 0;
int          g_micro_bos_detect_events = 0;
int          g_micro_bos_generated = 0;
int          g_micro_bos_skip_capacity = 0;
int          g_micro_bos_skip_invalid = 0;
int          g_micro_bos_skip_duplicate = 0;
int          g_micro_bos_skip_confluence = 0;
int          g_micro_bos_monitor_added = 0;
int          g_micro_bos_confirmed = 0;
int          g_micro_bos_skip_inactive = 0;
int          g_micro_bos_skip_expired = 0;
int          g_micro_bos_skip_used = 0;
int          g_micro_bos_skip_cooldown = 0;
int          g_micro_bos_skip_risk = 0;
int          g_micro_bos_skip_posmult = 0;
int          g_micro_bos_reject_finalize = 0;
int          g_micro_bos_reject_bounce = 0;
int          g_micro_bos_reject_h4 = 0;
int          g_micro_bos_reject_cont = 0;
int          g_micro_bos_reject_failure = 0;
int          g_micro_bos_executed = 0;

OBZone      g_sd_flip_zones[MAX_OB_ZONES];
EntryMonitor g_sd_flip_monitors[MAX_MONITORS];
int          g_sd_flip_zone_count = 0;
int          g_sd_flip_monitor_count = 0;
datetime     g_sd_flip_last_break_time = 0;
int          g_sd_flip_cooldown = 0;
int          g_sd_flip_detect_events = 0;
int          g_sd_flip_generated = 0;
int          g_sd_flip_monitor_added = 0;
int          g_sd_flip_confirmed = 0;
int          g_sd_flip_skip_inactive = 0;
int          g_sd_flip_skip_expired = 0;
int          g_sd_flip_skip_used = 0;
int          g_sd_flip_skip_cooldown = 0;
int          g_sd_flip_skip_risk = 0;
int          g_sd_flip_skip_posmult = 0;
int          g_sd_flip_reject_finalize = 0;
int          g_sd_flip_reject_h4 = 0;
int          g_sd_flip_reject_cont = 0;
int          g_sd_flip_reject_failure = 0;
int          g_sd_flip_executed = 0;

OBZone      g_rev_sweep_zones[MAX_OB_ZONES];
EntryMonitor g_rev_sweep_monitors[MAX_MONITORS];
int          g_rev_sweep_zone_count = 0;
int          g_rev_sweep_monitor_count = 0;
datetime     g_rev_sweep_last_time = 0;
int          g_rev_sweep_cooldown = 0;
int          g_rev_sweep_detect_events = 0;
int          g_rev_sweep_generated = 0;
int          g_rev_sweep_skip_dp = 0;
int          g_rev_sweep_skip_duplicate = 0;
int          g_rev_sweep_monitor_added = 0;
int          g_rev_sweep_confirmed = 0;
int          g_rev_sweep_skip_inactive = 0;
int          g_rev_sweep_skip_expired = 0;
int          g_rev_sweep_skip_used = 0;
int          g_rev_sweep_skip_cooldown = 0;
int          g_rev_sweep_skip_risk = 0;
int          g_rev_sweep_skip_posmult = 0;
int          g_rev_sweep_reject_finalize = 0;
int          g_rev_sweep_reject_cont = 0;
int          g_rev_sweep_reject_failure = 0;
int          g_rev_sweep_executed = 0;

OBZone      g_range_reaction_zones[MAX_OB_ZONES];
EntryMonitor g_range_reaction_monitors[MAX_MONITORS];
int          g_range_reaction_zone_count = 0;
int          g_range_reaction_monitor_count = 0;
int          g_range_reaction_cooldown = 0;
int          g_range_reaction_generated = 0;
int          g_range_reaction_monitor_added = 0;
int          g_range_reaction_confirmed = 0;
int          g_range_reaction_reject_finalize = 0;
int          g_range_reaction_skip_risk = 0;
int          g_range_reaction_skip_posmult = 0;
int          g_range_reaction_executed = 0;
double       g_htf_ob_react_last_level = 0.0;
int          g_htf_ob_react_last_dir = 0;
datetime     g_htf_ob_react_last_time = 0;

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

            if(InpBOSRetestDirectEntry)
            {
                tmp.comment = StringFormat("WT %s BOS %s x%.1f", InpVersion,
                                           (tmp.direction == OB_BUY ? "B" : "S"),
                                           tmp.pos_mult);
                if(!PassFailureReentryConfirm(tmp.direction, false, tmp.pos_mult, ENTRY_FAMILY_BOS))
                    return;
                if(!PassBOSExecutionFilter(tmp))
                    return;
                if(ExecuteSignalMTF(tmp))
                {
                    state.pos_count++;
                    g_sb_signal.state = BOS_EXECUTED;
                    if(g_sb_signal.from_h4)
                        g_sb_signal.last_entry_age = g_sb_signal.age_bars;
                    else
                    {
                        g_sb_signal.last_entry_age = 0;
                        g_sb_signal.age_bars = 0;
                    }
                    g_sb_signal.monitor_attempts = 0;
                }
                return;
            }

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
void RegisterMicroBOSMonitors(EAState &state, bool new_active_bar, string symbol)
{
    if(!InpEnableMicroBOSRetest || !new_active_bar)
        return;

    double spread = GetSpread(symbol);
    for(int z = 0; z < g_micro_bos_zone_count; z++)
    {
        if(g_micro_bos_zones[z].expired)
        {
            g_micro_bos_skip_expired++;
            g_micro_bos_skip_inactive++;
            continue;
        }
        if(g_micro_bos_zones[z].used)
        {
            g_micro_bos_skip_used++;
            g_micro_bos_skip_inactive++;
            continue;
        }
        if(!PassOBReentryCooldown(g_micro_bos_zones[z]))
        {
            g_micro_bos_skip_cooldown++;
            continue;
        }

        double mid = (g_micro_bos_zones[z].high + g_micro_bos_zones[z].low) / 2.0;
        double risk_dist = state.atr_value * MathMax(InpMicroBOSSLATR, 0.10);
        if(risk_dist <= 0)
        {
            g_micro_bos_skip_risk++;
            continue;
        }
        if(spread > 0 && risk_dist / spread < CfgMinRiskSpreadRatio())
        {
            g_micro_bos_skip_risk++;
            continue;
        }

        TradeSignal tmp;
        ZeroMemory(tmp);
        tmp.direction = g_micro_bos_zones[z].direction;
        tmp.sl = (tmp.direction == OB_BUY) ? mid - risk_dist : mid + risk_dist;
        tmp.risk_price = risk_dist;
        tmp.ob_index = z;
        tmp.pos_mult = MathMax(InpMicroBOSPosMult, 0.0);
        if(tmp.pos_mult <= 0.0)
        {
            g_micro_bos_skip_posmult++;
            continue;
        }

        AddEntryMonitor(tmp, g_micro_bos_zones[z], g_micro_bos_monitors, g_micro_bos_monitor_count);
        g_micro_bos_monitor_added++;
    }
}

void RegisterSupplyDemandFlipMonitors(EAState &state, bool new_active_bar, string symbol)
{
    if(!InpEnableSupplyDemandFlip || !new_active_bar)
        return;

    double spread = GetSpread(symbol);
    for(int z = 0; z < g_sd_flip_zone_count; z++)
    {
        if(g_sd_flip_zones[z].expired)
        {
            g_sd_flip_skip_expired++;
            g_sd_flip_skip_inactive++;
            continue;
        }
        if(g_sd_flip_zones[z].used)
        {
            g_sd_flip_skip_used++;
            g_sd_flip_skip_inactive++;
            continue;
        }
        if(!PassOBReentryCooldown(g_sd_flip_zones[z]))
        {
            g_sd_flip_skip_cooldown++;
            continue;
        }

        double mid = (g_sd_flip_zones[z].high + g_sd_flip_zones[z].low) / 2.0;
        double risk_dist = state.atr_value * MathMax(InpSDFlipSLATR, 0.10);
        if(risk_dist <= 0.0)
        {
            g_sd_flip_skip_risk++;
            continue;
        }
        if(spread > 0 && risk_dist / spread < CfgMinRiskSpreadRatio())
        {
            g_sd_flip_skip_risk++;
            continue;
        }

        TradeSignal tmp;
        ZeroMemory(tmp);
        tmp.direction = g_sd_flip_zones[z].direction;
        tmp.sl = (tmp.direction == OB_BUY) ? mid - risk_dist : mid + risk_dist;
        tmp.risk_price = risk_dist;
        tmp.ob_index = z;
        if(InpSDFlipPosMult < 0.0 && !IsFailureClusterReadyForReverse(tmp.direction))
        {
            g_sd_flip_reject_failure++;
            continue;
        }
        tmp.pos_mult = MathAbs(InpSDFlipPosMult);
        if(tmp.pos_mult <= 0.0)
        {
            g_sd_flip_skip_posmult++;
            continue;
        }

        AddEntryMonitor(tmp, g_sd_flip_zones[z], g_sd_flip_monitors, g_sd_flip_monitor_count);
        g_sd_flip_monitor_added++;
    }
}

void RegisterStrongSweepReversalMonitors(EAState &state, bool new_active_bar, string symbol)
{
    if(!InpEnableStrongSweepReversal || !new_active_bar)
        return;

    double spread = GetSpread(symbol);
    for(int z = 0; z < g_rev_sweep_zone_count; z++)
    {
        if(g_rev_sweep_zones[z].expired)
        {
            g_rev_sweep_skip_expired++;
            g_rev_sweep_skip_inactive++;
            continue;
        }
        if(g_rev_sweep_zones[z].used)
        {
            g_rev_sweep_skip_used++;
            g_rev_sweep_skip_inactive++;
            continue;
        }
        if(!PassOBReentryCooldown(g_rev_sweep_zones[z]))
        {
            g_rev_sweep_skip_cooldown++;
            continue;
        }

        double mid = (g_rev_sweep_zones[z].high + g_rev_sweep_zones[z].low) / 2.0;
        double risk_dist = state.atr_value * MathMax(InpStrongSweepSLATR, 0.10);
        if(risk_dist <= 0.0)
        {
            g_rev_sweep_skip_risk++;
            continue;
        }
        if(spread > 0 && risk_dist / spread < CfgMinRiskSpreadRatio())
        {
            g_rev_sweep_skip_risk++;
            continue;
        }

        TradeSignal tmp;
        ZeroMemory(tmp);
        tmp.direction = g_rev_sweep_zones[z].direction;
        tmp.sl = (tmp.direction == OB_BUY) ? mid - risk_dist : mid + risk_dist;
        tmp.risk_price = risk_dist;
        tmp.ob_index = z;
        tmp.pos_mult = MathMax(InpStrongSweepPosMult, 0.0);
        if(tmp.pos_mult <= 0.0)
        {
            g_rev_sweep_skip_posmult++;
            continue;
        }

        AddEntryMonitor(tmp, g_rev_sweep_zones[z], g_rev_sweep_monitors, g_rev_sweep_monitor_count);
        g_rev_sweep_monitor_added++;
    }
}

bool PassDirectionalContinuationFilter(int direction, int tf_min, int bars, double min_net_atr)
{
    ENUM_TIMEFRAMES tf = MinutesToTF(tf_min);
    bars = MathMax(1, bars);
    int need = MathMin(MathMax(bars + InpATRPeriod + 4, 24), 80);
    MqlRates rates[80];
    int count = CopyRates(_Symbol, tf, 0, need, rates);
    if(count < bars + 2)
        return false;

    double atr = CalcATR(rates, count, InpATRPeriod);
    if(atr <= 0.0)
        return false;

    double net = DirectionalNetBodyATR(rates, count, direction, bars, atr);
    if(net < min_net_atr)
        return false;
    if(HasStrongReverseCandle(rates, count, direction, bars, atr))
        return false;
    if(HasMicroReverseBreak(rates, count, direction, atr))
        return false;

    return true;
}

bool PassStructureHoldQuality(int direction)
{
    if(!InpStructureHoldRequireQuality)
        return true;
    if(!PassDirectionalContinuationFilter(direction,
                                          InpStructureHoldQualityTF,
                                          InpStructureHoldQualityBars,
                                          InpStructureHoldQualityMinATR))
        return false;
    if(InpStructureHoldQualityRequireStrongBreak &&
       !HasRecentStrongStructureBreak(direction))
        return false;
    return true;
}

bool PassMicroBOSExecutionFilter(const TradeSignal &signal)
{
    if(InpMicroBOSMinBounceSec > 0 && signal.bounce_seconds < InpMicroBOSMinBounceSec)
    {
        g_micro_bos_reject_bounce++;
        return false;
    }
    if(InpMicroBOSMaxBounceSec > 0 && signal.bounce_seconds > InpMicroBOSMaxBounceSec)
    {
        g_micro_bos_reject_bounce++;
        return false;
    }
    if(InpMicroBOSMinFinalPosMult > 0 && signal.pos_mult < InpMicroBOSMinFinalPosMult)
    {
        g_micro_bos_skip_posmult++;
        return false;
    }

    if(InpMicroBOSRequireH4Aligned &&
       g_trend_state_h4 != TREND_UNKNOWN && g_trend_state_h4 != TREND_CHOP)
    {
        bool h4_bull = (g_trend_state_h4 == TREND_BULLISH);
        bool aligned = (h4_bull && signal.direction == OB_BUY) ||
                       (!h4_bull && signal.direction == OB_SELL);
        if(!aligned)
        {
            g_micro_bos_reject_h4++;
            return false;
        }
    }

    if(!InpMicroBOSRequireContinuation)
        return true;

    if(!PassDirectionalContinuationFilter(signal.direction,
                                          InpMicroBOSContinuationTF,
                                          InpMicroBOSContinuationBars,
                                          InpMicroBOSContinuationMinATR))
    {
        g_micro_bos_reject_cont++;
        return false;
    }
    return true;
}

bool PassBOSExecutionFilter(const TradeSignal &signal)
{
    if(!InpBOSRequireContinuation)
        return true;
    return PassDirectionalContinuationFilter(signal.direction,
                                             InpBOSContinuationTF,
                                             InpBOSContinuationBars,
                                             InpBOSContinuationMinATR);
}

bool PassSupplyDemandFlipExecutionFilter(const TradeSignal &signal)
{
    if(InpSDFlipRequireH4Aligned &&
       g_trend_state_h4 != TREND_UNKNOWN && g_trend_state_h4 != TREND_CHOP)
    {
        bool h4_bull = (g_trend_state_h4 == TREND_BULLISH);
        bool aligned = (h4_bull && signal.direction == OB_BUY) ||
                       (!h4_bull && signal.direction == OB_SELL);
        if(!aligned)
        {
            g_sd_flip_reject_h4++;
            return false;
        }
    }

    if(!InpSDFlipRequireContinuation)
        return true;

    if(!PassDirectionalContinuationFilter(signal.direction,
                                          InpSDFlipContinuationTF,
                                          InpSDFlipContinuationBars,
                                          InpSDFlipContinuationMinATR))
    {
        g_sd_flip_reject_cont++;
        return false;
    }
    return true;
}

bool PassStrongSweepReversalExecutionFilter(const TradeSignal &signal)
{
    if(!InpStrongSweepRequireContinuation)
        return true;

    if(!PassDirectionalContinuationFilter(signal.direction,
                                          InpStrongSweepContinuationTF,
                                          InpStrongSweepContinuationBars,
                                          InpStrongSweepContinuationMinATR))
    {
        g_rev_sweep_reject_cont++;
        return false;
    }
    return true;
}

bool PassRangeReactionContinuation(int direction)
{
    int confirm_tf = (CfgRangeTF() >= 1440) ? 5 : 15;
    int confirm_bars = (confirm_tf >= 15) ? 1 : 2;
    double min_net_atr = (confirm_tf >= 15) ? 0.12 : 0.18;
    return PassDirectionalContinuationFilter(direction,
                                             confirm_tf,
                                             confirm_bars,
                                             min_net_atr);
}

void AddRangeReactionZone(const HTFRange &range, ENUM_RANGE_POSITION pos,
                          double atr, int bar_count)
{
    if(g_range_reaction_zone_count >= MAX_OB_ZONES || atr <= 0.0)
        return;

    int direction = (pos == RANGE_NEAR_BOTTOM) ? OB_BUY :
                    (pos == RANGE_NEAR_TOP ? OB_SELL : 0);
    if(direction == 0)
        return;
    if(CfgRangeTF() >= 1440 &&
       IsHTFRangeBoundaryUsedSMC(range, direction, MathMax(atr, range.width_price * 0.05)))
        return;

    double level = (direction == OB_BUY) ? range.low : range.high;
    double height = atr * MathMax(CfgRangeEntryZoneATR() * 0.5, 0.05);
    for(int z = 0; z < g_range_reaction_zone_count; z++)
    {
        if(g_range_reaction_zones[z].expired || g_range_reaction_zones[z].used)
            continue;
        if(g_range_reaction_zones[z].direction == direction &&
           MathAbs(g_range_reaction_zones[z].mid - level) < atr * 0.30)
            return;
    }

    OBZone zone = {};
    if(direction == OB_BUY)
    {
        zone.low = range.low - height * 0.25;
        zone.high = range.low + height;
    }
    else
    {
        zone.high = range.high + height * 0.25;
        zone.low = range.high - height;
    }
    if(zone.high <= zone.low)
        return;

    zone.mid = level;
    zone.ob_top = zone.high;
    zone.ob_bottom = zone.low;
    zone.direction = direction;
    zone.created = TimeCurrent();
    zone.created_bar = bar_count;
    zone.strength = 3.0;
    zone.is_fresh = true;
    zone.is_continuation = false;
    zone.is_1h_aligned = false;
    zone.ds_weight = 1.0;
    zone.is_range_breakout = false;
    zone.is_liquidity_sweep = false;
    zone.is_loose_sweep = false;
    zone.is_htf_pullback = false;
    zone.range_height = range.width_price;

    g_range_reaction_zones[g_range_reaction_zone_count] = zone;
    g_range_reaction_zone_count++;
    g_range_reaction_generated++;
}

bool FindRecentHTFOBReactionZone(string symbol, int &direction,
                                 double &zone_low, double &zone_high,
                                 double &range_height)
{
    direction = 0;
    zone_low = 0.0;
    zone_high = 0.0;
    range_height = 0.0;

    ENUM_TIMEFRAMES htf = MinutesToTF(CfgRangeTF());
    int lookback = MathMax(CfgRangeLookback(), 12);
    int need = MathMin(MathMax(lookback + InpATRPeriod + 6, 40), 220);
    MqlRates htf_rates[220];
    int htf_count = CopyRates(symbol, htf, 0, need, htf_rates);
    if(htf_count < InpATRPeriod + 8)
        return false;

    double htf_atr = CalcATR(htf_rates, htf_count, InpATRPeriod);
    if(htf_atr <= 0.0)
        return false;

    double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
    double price = (bid + ask) / 2.0;
    double tolerance = htf_atr * MathMax(CfgRangeBoundaryToleranceATR(), 0.05);
    double min_impulse = htf_atr * MathMax(CfgRangeMinWidthATR(), 0.50);
    double max_ob_height = htf_atr * MathMax(CfgRangeEntryZoneATR(), 0.20);

    ENUM_TIMEFRAMES confirm_tf = MinutesToTF(MathMax(CfgRangeMinBars(), 1));
    MqlRates ltf[40];
    int ltf_count = CopyRates(symbol, confirm_tf, 0, 40, ltf);
    double ltf_atr = 0.0;
    if(ltf_count >= InpATRPeriod + 4)
        ltf_atr = CalcATR(ltf, ltf_count, InpATRPeriod);

    if(ltf_atr > 0.0)
    {
        int zone_window = MathMax(3, MathMin(CfgRangeSwingStrength(), 12));
        double max_unmitigated_height = htf_atr * MathMax(CfgRangeMaxWidthATR(), 1.50);
        MqlRates reject_bar = ltf[1];
        double reject_body = MathAbs(reject_bar.close - reject_bar.open);
        double reject_lower_wick = MathMin(reject_bar.open, reject_bar.close) - reject_bar.low;
        double reject_upper_wick = reject_bar.high - MathMax(reject_bar.open, reject_bar.close);

        for(int i = 2; i < MathMin(htf_count - zone_window - 1, lookback); i++)
        {
            double impulse_body = MathAbs(htf_rates[i].close - htf_rates[i].open);
            double impulse_range = htf_rates[i].high - htf_rates[i].low;
            if(impulse_body < min_impulse * 1.10 && impulse_range < min_impulse * 1.40)
                continue;

            int candidate_dir = (htf_rates[i].close > htf_rates[i].open) ? OB_BUY : OB_SELL;
            double base_low = htf_rates[i + 1].low;
            double base_high = htf_rates[i + 1].high;
            for(int j = i + 1; j <= i + zone_window && j < htf_count; j++)
            {
                base_low = MathMin(base_low, htf_rates[j].low);
                base_high = MathMax(base_high, htf_rates[j].high);
            }

            double uz_low = base_low;
            double uz_high = base_high;
            if(candidate_dir == OB_BUY)
            {
                uz_low = base_low;
                uz_high = MathMin(base_high, htf_rates[i].open);
            }
            else
            {
                uz_low = MathMax(base_low, htf_rates[i].open);
                uz_high = base_high;
            }
            if(uz_high <= uz_low)
            {
                uz_low = base_low;
                uz_high = base_high;
            }

            double zone_height = uz_high - uz_low;
            if(zone_height <= 0.0 || zone_height > max_unmitigated_height)
                continue;

            bool impulse_left_zone = (candidate_dir == OB_BUY)
                ? (htf_rates[i].close > uz_high + tolerance &&
                   htf_rates[i].high > uz_high + min_impulse * 0.50)
                : (htf_rates[i].close < uz_low - tolerance &&
                   htf_rates[i].low < uz_low - min_impulse * 0.50);
            if(!impulse_left_zone)
                continue;

            bool mitigated_after_impulse = false;
            for(int k = 1; k < i; k++)
            {
                if(htf_rates[k].low <= uz_high + tolerance &&
                   htf_rates[k].high >= uz_low - tolerance)
                {
                    mitigated_after_impulse = true;
                    break;
                }
            }
            if(mitigated_after_impulse)
                continue;

            bool touched = (reject_bar.low <= uz_high + tolerance &&
                            reject_bar.high >= uz_low - tolerance);
            if(!touched)
                continue;

            bool reject_buy = (candidate_dir == OB_BUY &&
                               reject_bar.low <= uz_high + tolerance &&
                               reject_bar.close > uz_high &&
                               reject_lower_wick >= MathMax(reject_body, ltf_atr * 0.20));
            bool reject_sell = (candidate_dir == OB_SELL &&
                                reject_bar.high >= uz_low - tolerance &&
                                reject_bar.close < uz_low &&
                                reject_upper_wick >= MathMax(reject_body, ltf_atr * 0.20));
            if(!reject_buy && !reject_sell)
                continue;

            RecordHTFRejectContext(candidate_dir, reject_bar.time,
                                   reject_bar.low, reject_bar.high, ltf_atr);
            direction = candidate_dir;
            zone_low = uz_low;
            zone_high = uz_high;
            range_height = MathMax(htf_atr, zone_height);
            return true;
        }

        int max_cluster = MathMax(3, MathMin(CfgRangeSwingStrength(), 10));
        double max_composite_height = htf_atr * MathMax(CfgRangeMaxWidthATR(), 1.50);
        MqlRates bar = ltf[1];
        double body = MathAbs(bar.close - bar.open);
        double lower_wick = MathMin(bar.open, bar.close) - bar.low;
        double upper_wick = bar.high - MathMax(bar.open, bar.close);

        for(int i = 2; i < MathMin(htf_count - max_cluster - 1, lookback); i++)
        {
            double impulse_body = MathAbs(htf_rates[i].close - htf_rates[i].open);
            double impulse_range = htf_rates[i].high - htf_rates[i].low;
            if(impulse_body < min_impulse && impulse_range < min_impulse * 1.20)
                continue;

            int candidate_dir = (htf_rates[i].close > htf_rates[i].open) ? OB_BUY : OB_SELL;
            for(int window = 3; window <= max_cluster && i + window < htf_count; window++)
            {
                double low = htf_rates[i + 1].low;
                double high = htf_rates[i + 1].high;
                double first_open = htf_rates[i + window].open;
                double last_close = htf_rates[i + 1].close;
                for(int j = i + 1; j <= i + window; j++)
                {
                    low = MathMin(low, htf_rates[j].low);
                    high = MathMax(high, htf_rates[j].high);
                }
                double height = high - low;
                if(height <= 0.0 || height > max_composite_height)
                    continue;

                double cluster_net = MathAbs(last_close - first_open);
                if(cluster_net > height * 0.90)
                    continue;

                bool impulse_left_zone = (candidate_dir == OB_BUY)
                    ? (htf_rates[i].close > high + tolerance || htf_rates[i].high > high + min_impulse * 0.50)
                    : (htf_rates[i].close < low - tolerance || htf_rates[i].low < low - min_impulse * 0.50);
                if(!impulse_left_zone)
                    continue;

                bool invalidated = false;
                for(int k = 1; k < i; k++)
                {
                    if(candidate_dir == OB_BUY && htf_rates[k].close < low - tolerance)
                    {
                        invalidated = true;
                        break;
                    }
                    if(candidate_dir == OB_SELL && htf_rates[k].close > high + tolerance)
                    {
                        invalidated = true;
                        break;
                    }
                }
                if(invalidated)
                    continue;

                bool reject_buy = (candidate_dir == OB_BUY &&
                                   bar.low <= high + tolerance &&
                                   bar.close > high &&
                                   lower_wick >= MathMax(body, ltf_atr * 0.20));
                bool reject_sell = (candidate_dir == OB_SELL &&
                                    bar.high >= low - tolerance &&
                                    bar.close < low &&
                                    upper_wick >= MathMax(body, ltf_atr * 0.20));
                if(!reject_buy && !reject_sell)
                    continue;

                RecordHTFRejectContext(candidate_dir, bar.time,
                                       bar.low, bar.high, ltf_atr);
                direction = candidate_dir;
                zone_low = low;
                zone_high = high;
                range_height = MathMax(htf_atr, height);
                return true;
            }
        }

    }

    for(int i = 2; i < MathMin(htf_count - 2, lookback); i++)
    {
        double impulse = MathAbs(htf_rates[i].close - htf_rates[i].open);
        if(impulse < min_impulse)
            continue;

        int candidate_dir = (htf_rates[i].close > htf_rates[i].open) ? OB_BUY : OB_SELL;
        MqlRates ob_bar = htf_rates[i + 1];
        double low = MathMin(ob_bar.open, ob_bar.close);
        double high = MathMax(ob_bar.open, ob_bar.close);
        if(high <= low)
        {
            low = ob_bar.low;
            high = ob_bar.high;
        }
        if(high <= low || high - low > max_ob_height)
            continue;

        bool touched = (price >= low - tolerance && price <= high + tolerance);
        if(!touched)
            continue;

        if(ltf_atr <= 0.0)
            continue;

        MqlRates bar = ltf[1];
        double body = MathAbs(bar.close - bar.open);
        double lower_wick = MathMin(bar.open, bar.close) - bar.low;
        double upper_wick = bar.high - MathMax(bar.open, bar.close);
        bool reject_buy = (candidate_dir == OB_BUY &&
                           bar.low <= high + tolerance &&
                           bar.close > high &&
                           lower_wick >= MathMax(body, ltf_atr * 0.20));
        bool reject_sell = (candidate_dir == OB_SELL &&
                            bar.high >= low - tolerance &&
                            bar.close < low &&
                            upper_wick >= MathMax(body, ltf_atr * 0.20));
        if(!reject_buy && !reject_sell)
            continue;

        RecordHTFRejectContext(candidate_dir, bar.time,
                               bar.low, bar.high, ltf_atr);
        direction = candidate_dir;
        zone_low = low;
        zone_high = high;
        range_height = MathMax(htf_atr, high - low);
        return true;
    }
    return false;
}

void AddHTFOBReactionZone(int direction, double low, double high,
                          double range_height, double atr, int bar_count)
{
    if(direction == 0 || high <= low || atr <= 0.0)
        return;
    if(g_range_reaction_zone_count >= MAX_OB_ZONES)
        return;

    double level = (direction == OB_BUY) ? high : low;
    if(CfgRangeHTFOBReactionOnly() &&
       g_htf_ob_react_last_dir == direction &&
       g_htf_ob_react_last_time > 0)
    {
        int cooldown_sec = MathMax(CfgRangeUpdateBars(), 12) * 3600;
        double repeat_tol = MathMax(atr * 1.50, range_height * 0.25);
        if((TimeCurrent() - g_htf_ob_react_last_time) < cooldown_sec &&
           MathAbs(g_htf_ob_react_last_level - level) <= repeat_tol)
            return;
    }
    for(int z = 0; z < g_range_reaction_zone_count; z++)
    {
        if(g_range_reaction_zones[z].expired || g_range_reaction_zones[z].used)
            continue;
        double duplicate_tol = MathMax(atr * 0.50, range_height * 0.15);
        if(g_range_reaction_zones[z].direction == direction &&
           MathAbs(g_range_reaction_zones[z].mid - level) < duplicate_tol)
            return;
    }

    OBZone zone = {};
    double pad = atr * MathMax(CfgRangeEntryZoneATR(), 0.10);
    zone.low = low - pad * 0.25;
    zone.high = high + pad * 0.25;
    zone.mid = level;
    zone.ob_top = zone.high;
    zone.ob_bottom = zone.low;
    zone.direction = direction;
    zone.created = TimeCurrent();
    zone.created_bar = bar_count;
    zone.strength = 3.5;
    zone.is_fresh = true;
    zone.is_continuation = false;
    zone.is_1h_aligned = false;
    zone.ds_weight = 1.0;
    zone.is_range_breakout = false;
    zone.is_liquidity_sweep = false;
    zone.is_loose_sweep = false;
    zone.is_htf_pullback = true;
    zone.range_height = range_height;

    g_range_reaction_zones[g_range_reaction_zone_count] = zone;
    g_range_reaction_zone_count++;
    g_range_reaction_generated++;
}

void DetectRangeReactionZones(string symbol, int bar_count, double bid, double ask)
{
    if((CfgRangeTPTarget() != 2 && !CfgRangeHTFOBReactionOnly()) || !CfgEnableRangeFade())
        return;

    CompactZones(g_range_reaction_zones, g_range_reaction_zone_count);
    ExpireSignalZones(g_range_reaction_zones, g_range_reaction_zone_count,
                      bar_count, (CfgRangeTF() >= 1440) ? 120 : 96);
    if(g_range_reaction_cooldown > 0)
    {
        g_range_reaction_cooldown--;
        return;
    }

    if(CfgRangeHTFOBReactionOnly())
    {
        int direction = 0;
        double low = 0.0, high = 0.0, range_height = 0.0;
        if(FindRecentHTFOBReactionZone(symbol, direction, low, high, range_height))
            AddHTFOBReactionZone(direction, low, high, range_height, g_state.atr_value, bar_count);
        return;
    }

    HTFRange range = GetHTFRange(symbol);
    if(!range.valid)
        return;

    double price = (bid + ask) / 2.0;
    ENUM_RANGE_POSITION pos = GetRangePosition(range, price);
    if(pos == RANGE_BREAKING)
    {
        if(price < range.bottom_zone_low)
            pos = RANGE_NEAR_BOTTOM;
        else if(price > range.top_zone_high)
            pos = RANGE_NEAR_TOP;
    }
    if(pos != RANGE_NEAR_TOP && pos != RANGE_NEAR_BOTTOM)
        return;

    AddRangeReactionZone(range, pos, g_state.atr_value, bar_count);
}

void RegisterRangeReactionMonitors(EAState &state, bool new_active_bar, string symbol)
{
    if((CfgRangeTPTarget() != 2 && !CfgRangeHTFOBReactionOnly()) || !new_active_bar)
        return;

    double spread = GetSpread(symbol);
    for(int z = 0; z < g_range_reaction_zone_count; z++)
    {
        if(g_range_reaction_zones[z].expired || g_range_reaction_zones[z].used)
            continue;
        if(!PassOBReentryCooldown(g_range_reaction_zones[z]))
            continue;

        int direction = g_range_reaction_zones[z].direction;
        double edge_sl = (direction == OB_BUY)
            ? g_range_reaction_zones[z].low - state.atr_value * MathMax(CfgRangeSLBufferATR(), 0.10)
            : g_range_reaction_zones[z].high + state.atr_value * MathMax(CfgRangeSLBufferATR(), 0.10);
        double entry_ref = (direction == OB_BUY) ? g_range_reaction_zones[z].high
                                                 : g_range_reaction_zones[z].low;
        double risk_dist = MathAbs(entry_ref - edge_sl);
        if(risk_dist <= 0.0 || (spread > 0 && risk_dist / spread < CfgMinRiskSpreadRatio()))
        {
            g_range_reaction_skip_risk++;
            continue;
        }

        TradeSignal tmp;
        ZeroMemory(tmp);
        tmp.direction = direction;
        tmp.sl = edge_sl;
        tmp.risk_price = risk_dist;
        tmp.ob_index = z;
        tmp.pos_mult = MathMax(CfgRangePosMult(), 0.0);
        if(CfgRangeHTFOBReactionOnly())
            tmp.htf_target = true;
        if(tmp.pos_mult <= 0.0)
        {
            g_range_reaction_skip_posmult++;
            continue;
        }

        AddEntryMonitor(tmp, g_range_reaction_zones[z],
                        g_range_reaction_monitors, g_range_reaction_monitor_count);
        g_range_reaction_monitor_added++;
    }
}

bool TryExecuteRangeReactionZone(int z, string symbol)
{
    if(z < 0 || z >= g_range_reaction_zone_count)
        return false;
    OBZone zone = g_range_reaction_zones[z];
    if(zone.expired || zone.used)
        return false;
    if(!PassRangeReactionContinuation(zone.direction))
        return false;

    double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
    double entry = (zone.direction == OB_BUY) ? ask : bid;
    double sl = (zone.direction == OB_BUY)
        ? zone.low - g_state.atr_value * MathMax(CfgRangeSLBufferATR(), 0.10)
        : zone.high + g_state.atr_value * MathMax(CfgRangeSLBufferATR(), 0.10);
    double risk_price = MathAbs(entry - sl);
    if(risk_price <= 0.0)
    {
        g_range_reaction_skip_risk++;
        return false;
    }

    double spread = GetSpread(symbol);
    if(spread > 0 && risk_price / spread < CfgMinRiskSpreadRatio())
    {
        g_range_reaction_skip_risk++;
        return false;
    }

    double pos_mult = MathMax(CfgRangePosMult(), 0.0);
    if(pos_mult <= 0.0)
    {
        g_range_reaction_skip_posmult++;
        return false;
    }

    double final_lot = CalcEntryLot(symbol, CfgRiskPercent(), risk_price, pos_mult);
    final_lot = ApplyLotCap(final_lot);
    if(CfgRangeMaxLot() > 0 && final_lot > CfgRangeMaxLot())
        final_lot = CfgRangeMaxLot();
    if(!PassMinRisk(final_lot, risk_price, symbol))
    {
        g_range_reaction_skip_risk++;
        return false;
    }

    double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    if(lot_step <= 0.0)
        return false;
    final_lot = MathFloor(final_lot / lot_step) * lot_step;
    if(final_lot < lot_min)
        return false;

    TradeSignal signal;
    ZeroMemory(signal);
    signal.direction = zone.direction;
    signal.entry = entry;
    signal.sl = sl;
    signal.risk_price = risk_price;
    signal.lot = NormalizeDouble(final_lot, 2);
    signal.pos_mult = pos_mult;
    signal.ob_index = z;
    signal.tp = 0.0;

    HTFRange range = GetHTFRange(symbol);
    ENUM_RANGE_POSITION pos = zone.direction == OB_BUY ? RANGE_NEAR_BOTTOM : RANGE_NEAR_TOP;
    if(!CfgRangeHTFOBReactionOnly())
    {
        double tp = CalcRangeTP(range, pos, entry, zone.direction);
        if(tp > 0)
            signal.tp = tp;
    }

    signal.comment = StringFormat("WT %s RGREACT %s x%.1f", InpVersion,
                                  signal.direction == OB_BUY ? "B" : "S",
                                  signal.pos_mult);
    return ExecuteSignalFromZone(signal, g_range_reaction_zones,
                                 g_range_reaction_zone_count, false);
}

bool ApplyRangeReactionLotCap(string symbol, TradeSignal &signal)
{
    if(CfgRangeMaxLot() <= 0.0 || signal.lot <= CfgRangeMaxLot())
        return true;

    double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    if(lot_step <= 0.0)
        return false;
    double capped = MathFloor(CfgRangeMaxLot() / lot_step) * lot_step;
    if(capped < lot_min)
        return false;
    signal.lot = NormalizeDouble(capped, 2);
    return true;
}

bool ApplyStrongSweepLotCap(string symbol, TradeSignal &signal)
{
    if(InpStrongSweepMaxLotSize <= 0.0 || signal.lot <= InpStrongSweepMaxLotSize)
        return true;

    double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    if(lot_step <= 0.0)
        return false;

    double capped = MathFloor(InpStrongSweepMaxLotSize / lot_step) * lot_step;
    if(capped < lot_min)
        return false;
    signal.lot = NormalizeDouble(capped, 2);
    return true;
}

double LightRegimeNetATR(int tf_min, int bars)
{
    ENUM_TIMEFRAMES tf = MinutesToTF(tf_min);
    bars = MathMax(1, bars);
    int need = MathMin(MathMax(bars + InpATRPeriod + 4, 24), 80);
    MqlRates rates[80];
    int count = CopyRates(_Symbol, tf, 0, need, rates);
    if(count < bars + 2)
        return 0.0;

    double atr = CalcATR(rates, count, InpATRPeriod);
    if(atr <= 0.0)
        return 0.0;

    double net = 0.0;
    for(int i = 1; i <= bars && i < count; i++)
        net += rates[i].close - rates[i].open;
    return net / atr;
}

bool IsSweepComment(const string comment)
{
    return StringFind(comment, "SWP") >= 0;
}

double ApplyLightRegimePosMult(const TradeSignal &signal, const OBZone &zone)
{
    if(!InpEnableLightRegimePosMult)
        return signal.pos_mult;
    if(InpLightRegimeSweepOnly && !zone.is_liquidity_sweep && !IsSweepComment(signal.comment))
        return signal.pos_mult;

    double net_atr = LightRegimeNetATR(InpLightRegimeTF, InpLightRegimeBars);
    double abs_net = MathAbs(net_atr);
    double mult = InpLightRegimeRangeMult;

    if(abs_net >= InpLightRegimeMinNetATR)
    {
        bool aligned = (net_atr > 0 && signal.direction == OB_BUY) ||
                       (net_atr < 0 && signal.direction == OB_SELL);
        mult = aligned ? InpLightRegimeTrendAlignedMult : InpLightRegimeTrendCounterMult;
    }

    if(mult <= 0.0)
        return -1.0;
    return signal.pos_mult * mult;
}

bool ApplyLightRegimeToSignal(string symbol, TradeSignal &signal, const OBZone &zone)
{
    double new_mult = ApplyLightRegimePosMult(signal, zone);
    if(new_mult < 0.0)
        return false;
    if(MathAbs(new_mult - signal.pos_mult) < 0.0001)
        return true;

    double final_lot = CalcEntryLot(symbol, CfgRiskPercent(), signal.risk_price, new_mult);
    final_lot = ApplyLotCap(final_lot);
    final_lot = ApplySignalTypeLotCap(zone, final_lot);
    final_lot = ApplyBalanceLotCap(final_lot);

    double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    double lot_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
    double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    if(lot_step <= 0.0)
        return false;

    final_lot = MathFloor(final_lot / lot_step) * lot_step;
    if(final_lot < lot_min)
        return false;
    if(final_lot > lot_max)
        final_lot = lot_max;

    signal.pos_mult = new_mult;
    signal.lot = NormalizeDouble(final_lot, 2);
    return true;
}

bool ApplyHTFRejectPullbackUpgrade(string symbol, TradeSignal &signal, const OBZone &zone, int entry_family)
{
    if(!HasHTFRejectPullbackContext(signal.direction))
        return true;
    if(entry_family != ENTRY_FAMILY_OB && entry_family != ENTRY_FAMILY_SWP)
        return true;
    if(StringFind(signal.comment, "RGREACT") >= 0 || StringFind(signal.comment, "HTRJ") >= 0)
        return true;
    if(g_micro_bos_htf_reject_low <= 0.0 || g_micro_bos_htf_reject_high <= g_micro_bos_htf_reject_low)
        return true;

    double entry_price = (signal.direction == OB_BUY) ?
        SymbolInfoDouble(symbol, SYMBOL_ASK) : SymbolInfoDouble(symbol, SYMBOL_BID);
    if(entry_price <= 0.0)
        entry_price = signal.entry;
    double atr = (g_micro_bos_htf_reject_atr > 0.0) ? g_micro_bos_htf_reject_atr : g_state.atr_value;
    if(atr <= 0.0 || entry_price <= 0.0)
        return true;

    double zone_low = MathMin(g_micro_bos_htf_reject_low, zone.low);
    double zone_high = MathMax(g_micro_bos_htf_reject_high, zone.high);
    double pullback_tol = atr * MathMax(CfgRangeEntryZoneATR(), 0.30);
    bool near_reject_zone = (entry_price >= zone_low - pullback_tol &&
                             entry_price <= zone_high + pullback_tol);
    if(!near_reject_zone)
        return true;

    double sl_buffer = atr * MathMax(CfgRangeSLBufferATR(), 0.80);
    double new_sl = (signal.direction == OB_BUY)
        ? MathMin(signal.sl, g_micro_bos_htf_reject_low - sl_buffer)
        : MathMax(signal.sl, g_micro_bos_htf_reject_high + sl_buffer);
    double new_risk = MathAbs(entry_price - new_sl);
    double old_risk = signal.risk_price;
    if(new_risk <= old_risk || old_risk <= 0.0)
        return true;

    double max_risk = atr * MathMax(CfgRangeMaxWidthATR(), 2.0);
    if(max_risk > 0.0 && new_risk > max_risk)
        return true;

    double new_mult = signal.pos_mult;
    if(CfgRangePosMult() > 0.0)
        new_mult *= CfgRangePosMult();
    new_mult = ApplyPositionMultiplierCap(new_mult);
    if(new_mult <= 0.0)
        return false;

    double final_lot = CalcEntryLot(symbol, CfgRiskPercent(), new_risk, new_mult);
    final_lot = ApplyLotCap(final_lot);
    final_lot = ApplySignalTypeLotCap(zone, final_lot);
    final_lot = ApplyBalanceLotCap(final_lot);
    if(CfgRangeMaxLot() > 0.0 && final_lot > CfgRangeMaxLot())
        final_lot = CfgRangeMaxLot();
    if(!PassMinRisk(final_lot, new_risk, symbol))
        return false;

    double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    double lot_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
    double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    if(lot_step <= 0.0)
        return false;
    final_lot = MathFloor(final_lot / lot_step) * lot_step;
    if(final_lot < lot_min)
        return false;
    if(final_lot > lot_max)
        final_lot = lot_max;

    signal.sl = NormalizeDouble(new_sl, _Digits);
    signal.risk_price = new_risk;
    signal.pos_mult = new_mult;
    signal.lot = NormalizeDouble(final_lot, 2);
    signal.tp = 0.0;
    signal.htf_target = true;
    signal.comment = signal.comment + " HTRJ";
    if(InpEnableEntryDebug)
        Print("FINAL_DIAG z=", signal.ob_index,
              " htf_reject_pullback entry=", DoubleToString(entry_price, _Digits),
              " sl=", DoubleToString(signal.sl, _Digits),
              " risk=", DoubleToString(signal.risk_price, _Digits),
              " lot=", DoubleToString(signal.lot, 2));
    MarkHTFRejectPullbackUsed();
    return true;
}

void ExecuteMicroBOSConfirmed(double bid, double ask, string symbol)
{
    if(!InpEnableMicroBOSRetest)
        return;

    TradeSignal confirmed[10];
    SetMitigationContext(g_state.market_state);
    int conf_count = UpdateEntryMonitors(bid, ask, TimeCurrent(),
                                         g_micro_bos_monitors, g_micro_bos_monitor_count,
                                         confirmed, 10);
    for(int i = 0; i < conf_count; i++)
    {
        g_micro_bos_confirmed++;
        if(InpMicroBOSUseStructureHold)
        {
            if(CountActivePositionsByFamily(ENTRY_FAMILY_MBOS) >= 1)
                break;
        }
        else if(g_state.pos_count >= CfgMaxConcurrent())
            break;
        if(confirmed[i].ob_index < 0 || confirmed[i].ob_index >= g_micro_bos_zone_count)
            continue;
        if(!FinalizeEntryEngineSignal(symbol, g_micro_bos_zones[confirmed[i].ob_index], g_state, confirmed[i]))
        {
            g_micro_bos_reject_finalize++;
            continue;
        }
        if(!PassMicroBOSExecutionFilter(confirmed[i]))
            continue;
        if(!PassFailureReentryConfirm(confirmed[i].direction, false, confirmed[i].pos_mult, ENTRY_FAMILY_MBOS))
        {
            g_micro_bos_reject_failure++;
            continue;
        }

        confirmed[i].comment = StringFormat("WT %s MBOS %s x%.1f", InpVersion,
                                            confirmed[i].direction == OB_BUY ? "B" : "S",
                                            confirmed[i].pos_mult);
        if(ExecuteSignalFromZone(confirmed[i], g_micro_bos_zones, g_micro_bos_zone_count, false))
        {
            g_state.last_entry_bar = g_state.bar_count;
            if(!InpMicroBOSUseStructureHold)
                g_state.pos_count++;
            g_micro_bos_executed++;
            g_micro_bos_cooldown = MathMax(InpMicroBOSCooldownBars, 0);
            if(InpMicroBOSUseStructureHold && g_track_count > 0 &&
               g_trend_state_h4 != TREND_UNKNOWN && g_trend_state_h4 != TREND_CHOP &&
               IsStructureSLHTFAligned(confirmed[i].direction) &&
               PassStructureHoldQuality(confirmed[i].direction))
            {
                bool h4_bull = (g_trend_state_h4 == TREND_BULLISH);
                bool aligned = (h4_bull && confirmed[i].direction == OB_BUY) ||
                               (!h4_bull && confirmed[i].direction == OB_SELL);
                if(aligned)
                {
                    g_tracks[g_track_count - 1].use_structure_sl = true;
                    g_tracks[g_track_count - 1].skip_mfe_exits = InpStructSkipMFEExits;
                }
            }
        }
    }
}

void ExecuteSupplyDemandFlipConfirmed(double bid, double ask, string symbol)
{
    if(!InpEnableSupplyDemandFlip)
        return;

    TradeSignal confirmed[10];
    SetMitigationContext(g_state.market_state);
    int conf_count = UpdateEntryMonitors(bid, ask, TimeCurrent(),
                                         g_sd_flip_monitors, g_sd_flip_monitor_count,
                                         confirmed, 10);
    for(int i = 0; i < conf_count; i++)
    {
        g_sd_flip_confirmed++;
        if(g_state.pos_count >= CfgMaxConcurrent())
            break;
        if(confirmed[i].ob_index < 0 || confirmed[i].ob_index >= g_sd_flip_zone_count)
            continue;
        if(!FinalizeEntryEngineSignal(symbol, g_sd_flip_zones[confirmed[i].ob_index], g_state, confirmed[i]))
        {
            g_sd_flip_reject_finalize++;
            continue;
        }
        if(!PassSupplyDemandFlipExecutionFilter(confirmed[i]))
            continue;
        if(!PassFailureReentryConfirm(confirmed[i].direction, false, confirmed[i].pos_mult, ENTRY_FAMILY_SDFLIP))
        {
            g_sd_flip_reject_failure++;
            continue;
        }

        confirmed[i].comment = StringFormat("WT %s SDFLIP %s x%.1f", InpVersion,
                                            confirmed[i].direction == OB_BUY ? "B" : "S",
                                            confirmed[i].pos_mult);
        if(ExecuteSignalFromZone(confirmed[i], g_sd_flip_zones, g_sd_flip_zone_count, false))
        {
            g_state.last_entry_bar = g_state.bar_count;
            g_state.pos_count++;
            g_sd_flip_executed++;
            g_sd_flip_cooldown = MathMax(InpSDFlipCooldownBars, 0);
            if(InpSDFlipUseStructureHold && g_track_count > 0 &&
               g_trend_state_h4 != TREND_UNKNOWN && g_trend_state_h4 != TREND_CHOP &&
               IsStructureSLHTFAligned(confirmed[i].direction) &&
               PassStructureHoldQuality(confirmed[i].direction))
            {
                bool h4_bull = (g_trend_state_h4 == TREND_BULLISH);
                bool aligned = (h4_bull && confirmed[i].direction == OB_BUY) ||
                               (!h4_bull && confirmed[i].direction == OB_SELL);
                if(aligned)
                {
                    g_tracks[g_track_count - 1].use_structure_sl = true;
                    g_tracks[g_track_count - 1].skip_mfe_exits = InpStructSkipMFEExits;
                }
            }
        }
    }
}

void ExecuteStrongSweepReversalConfirmed(double bid, double ask, string symbol)
{
    if(!InpEnableStrongSweepReversal)
        return;

    TradeSignal confirmed[10];
    SetMitigationContext(g_state.market_state);
    int conf_count = UpdateEntryMonitors(bid, ask, TimeCurrent(),
                                         g_rev_sweep_monitors, g_rev_sweep_monitor_count,
                                         confirmed, 10);
    for(int i = 0; i < conf_count; i++)
    {
        g_rev_sweep_confirmed++;
        if(g_state.pos_count >= CfgMaxConcurrent())
            break;
        if(confirmed[i].ob_index < 0 || confirmed[i].ob_index >= g_rev_sweep_zone_count)
            continue;
        if(!PassSMCDirectionGate(confirmed[i].direction))
            continue;
        if(!FinalizeEntryEngineSignal(symbol, g_rev_sweep_zones[confirmed[i].ob_index], g_state, confirmed[i]))
        {
            g_rev_sweep_reject_finalize++;
            continue;
        }
        if(!PassStrongSweepReversalExecutionFilter(confirmed[i]))
            continue;
        if(!ApplyStrongSweepLotCap(symbol, confirmed[i]))
        {
            g_rev_sweep_skip_posmult++;
            continue;
        }
        if(!PassFailureReentryConfirm(confirmed[i].direction, true,
                                      confirmed[i].pos_mult, ENTRY_FAMILY_REVSWP))
        {
            g_rev_sweep_reject_failure++;
            continue;
        }

        confirmed[i].comment = StringFormat("WT %s REVSWP %s x%.1f", InpVersion,
                                            confirmed[i].direction == OB_BUY ? "B" : "S",
                                            confirmed[i].pos_mult);
        if(ExecuteSignalFromZone(confirmed[i], g_rev_sweep_zones, g_rev_sweep_zone_count, false))
        {
            g_state.last_entry_bar = g_state.bar_count;
            g_state.pos_count++;
            g_rev_sweep_executed++;
            g_rev_sweep_cooldown = MathMax(InpStrongSweepCooldownBars, 0);
            if(InpStrongSweepUseStructureHold && g_track_count > 0 &&
               PassStructureHoldQuality(confirmed[i].direction))
            {
                g_tracks[g_track_count - 1].use_structure_sl = true;
                g_tracks[g_track_count - 1].skip_mfe_exits = InpStructSkipMFEExits;
            }
        }
    }
}

void ExecuteRangeReactionConfirmed(double bid, double ask, string symbol)
{
    if(CfgRangeTPTarget() != 2 && !CfgRangeHTFOBReactionOnly())
        return;

    TradeSignal confirmed[10];
    SetMitigationContext(g_state.market_state);
    int conf_count = UpdateEntryMonitors(bid, ask, TimeCurrent(),
                                         g_range_reaction_monitors,
                                         g_range_reaction_monitor_count,
                                         confirmed, 10);
    for(int i = 0; i < conf_count; i++)
    {
        g_range_reaction_confirmed++;
        if(g_state.pos_count >= CfgMaxConcurrent())
            break;
        if(confirmed[i].ob_index < 0 ||
           confirmed[i].ob_index >= g_range_reaction_zone_count)
            continue;
        if(!FinalizeEntryEngineSignal(symbol,
                                      g_range_reaction_zones[confirmed[i].ob_index],
                                      g_state, confirmed[i]))
        {
            g_range_reaction_reject_finalize++;
            continue;
        }
        if(!ApplyRangeReactionLotCap(symbol, confirmed[i]))
        {
            g_range_reaction_skip_posmult++;
            continue;
        }

        confirmed[i].comment = StringFormat("WT %s RGREACT %s x%.1f", InpVersion,
                                            confirmed[i].direction == OB_BUY ? "B" : "S",
                                            confirmed[i].pos_mult);
        if(ExecuteSignalFromZone(confirmed[i], g_range_reaction_zones,
                                 g_range_reaction_zone_count, false))
        {
            HTFRange used_range = GetHTFRange(symbol);
            if(used_range.valid && CfgRangeTF() >= 1440 && !CfgRangeHTFOBReactionOnly())
                MarkHTFRangeBoundaryUsedSMC(used_range, confirmed[i].direction);
            if(CfgRangeHTFOBReactionOnly())
            {
                OBZone executed_zone = g_range_reaction_zones[confirmed[i].ob_index];
                g_htf_ob_react_last_level = executed_zone.mid;
                g_htf_ob_react_last_dir = executed_zone.direction;
                g_htf_ob_react_last_time = TimeCurrent();
            }
            g_state.last_entry_bar = g_state.bar_count;
            g_state.pos_count++;
            if(CfgRangeHTFOBReactionOnly() && g_track_count > 0)
                g_tracks[g_track_count - 1].skip_mfe_exits = true;
            g_range_reaction_executed++;
            g_range_reaction_cooldown = CfgRangeHTFOBReactionOnly()
                ? MathMax(24, CfgRangeUpdateBars() * 24)
                : ((CfgRangeTF() >= 1440) ? 24 : 16);
        }
    }
}

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
            if(!PassBOSExecutionFilter(confirmed[i])) continue;

            // 共用state.pos_count(由SyncPositions自动管理)
            if(state.pos_count >= CfgMaxConcurrent()) continue;

            if(!PassFailureReentryConfirm(confirmed[i].direction, false, confirmed[i].pos_mult, ENTRY_FAMILY_BOS))
                continue;
            if(ExecuteSignalMTF(confirmed[i]))
            {
                state.pos_count++;
            }
            continue;
        }

        // MTF OB信号 (ob_index >= 10000) → 直接执行, 跳过v2 Finalize
        if(confirmed[i].ob_index >= 10000)
        {
            if(!PassFailureReentryConfirm(confirmed[i].direction, false, confirmed[i].pos_mult, ENTRY_FAMILY_MTF))
                continue;
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
        bool h4_counter_locked = false;
        if(InpBOSRetestEntry && InpBOSLockBounceEntries &&
           g_trend_state_h4 != TREND_UNKNOWN && g_trend_state_h4 != TREND_CHOP)
        {
            bool h4_bull = (g_trend_state_h4 == TREND_BULLISH);
            h4_aligned = (h4_bull && confirmed[i].direction == OB_BUY) ||
                        (!h4_bull && confirmed[i].direction == OB_SELL);
            h4_counter_locked = !h4_aligned;
            if(h4_counter_locked &&
               !InpBOSLockAllowCounterBounce &&
               !InpBOSLockAllowCounterOB &&
               !HasBOSLockCounterMomentum(confirmed[i].direction) &&
               !HasBOSLockCounterBreak(confirmed[i].direction))
                continue;
        }

        // PathB: BOS-only(跳过Bounce)
        if(InpEnableBOSOnlyMode) continue;

        if(!FinalizeEntryEngineSignal(symbol, zones[confirmed[i].ob_index], state, confirmed[i])) continue;
        if(!ApplyLightRegimeToSignal(symbol, confirmed[i], zones[confirmed[i].ob_index]))
            continue;
        bool counter_break_allowed = HasBOSLockCounterBreak(confirmed[i].direction);
        if(counter_break_allowed && InpBOSLockCounterBreakOBOnly &&
           (zones[confirmed[i].ob_index].is_liquidity_sweep ||
            IsLooseSweepZone(zones[confirmed[i].ob_index])))
            counter_break_allowed = false;
        bool counter_ob_allowed = InpBOSLockAllowCounterOB &&
                                  !zones[confirmed[i].ob_index].is_liquidity_sweep &&
                                  !IsLooseSweepZone(zones[confirmed[i].ob_index]);
        if(h4_counter_locked &&
           !HasBOSLockCounterMomentum(confirmed[i].direction) &&
           !counter_break_allowed &&
           !counter_ob_allowed &&
           !HasBOSLockCounterBounce(confirmed[i]))
            continue;
        bool failure_reentry_is_sweep = zones[confirmed[i].ob_index].is_liquidity_sweep ||
                                        IsLooseSweepZone(zones[confirmed[i].ob_index]);
        int failure_reentry_family = EntryFamilyFromSignal(confirmed[i], zones[confirmed[i].ob_index]);
        if(!PassPlainSweepDPGate(zones[confirmed[i].ob_index], confirmed[i].direction))
        {
            if(InpEnableEntryDebug) Print("FINAL_DIAG z=", confirmed[i].ob_index,
               " dir=", confirmed[i].direction, " skip=plain_swp_dp_confirmed");
            continue;
        }
        if(!PassFailureReentryConfirm(confirmed[i].direction, failure_reentry_is_sweep,
                                      confirmed[i].pos_mult, failure_reentry_family))
            continue;

        if(ExecuteSignal(confirmed[i]))
        {
            state.last_entry_bar = state.bar_count;
            state.pos_count++;
            // H4方向锁→结构止损模式(跳过DTP, M5结构管理)
            if(h4_aligned && g_track_count > 0 &&
               IsStructureSLHTFAligned(confirmed[i].direction) &&
               PassStructureHoldQuality(confirmed[i].direction))
            {
                g_tracks[g_track_count-1].use_structure_sl = true;
                g_tracks[g_track_count-1].skip_mfe_exits = InpStructSkipMFEExits;
            }
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
    ZeroMemory(g_micro_bos_zones);
    ZeroMemory(g_micro_bos_monitors);
    g_micro_bos_zone_count = 0;
    g_micro_bos_monitor_count = 0;
    g_micro_bos_last_break_time = 0;
    g_micro_bos_cooldown = 0;
    g_micro_bos_detect_events = 0;
    g_micro_bos_generated = 0;
    g_micro_bos_skip_capacity = 0;
    g_micro_bos_skip_invalid = 0;
    g_micro_bos_skip_duplicate = 0;
    g_micro_bos_skip_confluence = 0;
    g_micro_bos_monitor_added = 0;
    g_micro_bos_confirmed = 0;
    g_micro_bos_skip_inactive = 0;
    g_micro_bos_skip_expired = 0;
    g_micro_bos_skip_used = 0;
    g_micro_bos_skip_cooldown = 0;
    g_micro_bos_skip_risk = 0;
    g_micro_bos_skip_posmult = 0;
    g_micro_bos_reject_finalize = 0;
    g_micro_bos_reject_bounce = 0;
    g_micro_bos_reject_h4 = 0;
    g_micro_bos_reject_cont = 0;
    g_micro_bos_reject_failure = 0;
    g_micro_bos_executed = 0;
    ZeroMemory(g_sd_flip_zones);
    ZeroMemory(g_sd_flip_monitors);
    g_sd_flip_zone_count = 0;
    g_sd_flip_monitor_count = 0;
    g_sd_flip_last_break_time = 0;
    g_sd_flip_cooldown = 0;
    g_sd_flip_detect_events = 0;
    g_sd_flip_generated = 0;
    g_sd_flip_monitor_added = 0;
    g_sd_flip_confirmed = 0;
    g_sd_flip_skip_inactive = 0;
    g_sd_flip_skip_expired = 0;
    g_sd_flip_skip_used = 0;
    g_sd_flip_skip_cooldown = 0;
    g_sd_flip_skip_risk = 0;
    g_sd_flip_skip_posmult = 0;
    g_sd_flip_reject_finalize = 0;
    g_sd_flip_reject_h4 = 0;
    g_sd_flip_reject_cont = 0;
    g_sd_flip_reject_failure = 0;
    g_sd_flip_executed = 0;
    ZeroMemory(g_rev_sweep_zones);
    ZeroMemory(g_rev_sweep_monitors);
    g_rev_sweep_zone_count = 0;
    g_rev_sweep_monitor_count = 0;
    g_rev_sweep_last_time = 0;
    g_rev_sweep_cooldown = 0;
    g_rev_sweep_detect_events = 0;
    g_rev_sweep_generated = 0;
    g_rev_sweep_skip_dp = 0;
    g_rev_sweep_skip_duplicate = 0;
    g_rev_sweep_monitor_added = 0;
    g_rev_sweep_confirmed = 0;
    g_rev_sweep_skip_inactive = 0;
    g_rev_sweep_skip_expired = 0;
    g_rev_sweep_skip_used = 0;
    g_rev_sweep_skip_cooldown = 0;
    g_rev_sweep_skip_risk = 0;
    g_rev_sweep_skip_posmult = 0;
    g_rev_sweep_reject_finalize = 0;
    g_rev_sweep_reject_cont = 0;
    g_rev_sweep_reject_failure = 0;
    g_rev_sweep_executed = 0;
    ZeroMemory(g_range_reaction_zones);
    ZeroMemory(g_range_reaction_monitors);
    g_range_reaction_zone_count = 0;
    g_range_reaction_monitor_count = 0;
    g_range_reaction_cooldown = 0;
    g_range_reaction_generated = 0;
    g_range_reaction_monitor_added = 0;
    g_range_reaction_confirmed = 0;
    g_range_reaction_reject_finalize = 0;
    g_range_reaction_skip_risk = 0;
    g_range_reaction_skip_posmult = 0;
    g_range_reaction_executed = 0;
    g_htf_ob_react_last_level = 0.0;
    g_htf_ob_react_last_dir = 0;
    g_htf_ob_react_last_time = 0;
    ResetHTFRejectContext();
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
    if(InpEnableMicroBOSRetest)
    {
        Print("MICROBOS_SUMMARY detected=", g_micro_bos_detect_events,
              " generated=", g_micro_bos_generated,
              " skip_capacity=", g_micro_bos_skip_capacity,
              " skip_invalid=", g_micro_bos_skip_invalid,
              " skip_duplicate=", g_micro_bos_skip_duplicate,
              " skip_confluence=", g_micro_bos_skip_confluence,
              " monitors=", g_micro_bos_monitor_added,
              " confirmed=", g_micro_bos_confirmed,
              " skip_inactive=", g_micro_bos_skip_inactive,
              " skip_expired=", g_micro_bos_skip_expired,
              " skip_used=", g_micro_bos_skip_used,
              " skip_cooldown=", g_micro_bos_skip_cooldown,
              " skip_risk=", g_micro_bos_skip_risk,
              " skip_posmult=", g_micro_bos_skip_posmult,
              " reject_finalize=", g_micro_bos_reject_finalize,
              " reject_bounce=", g_micro_bos_reject_bounce,
              " reject_h4=", g_micro_bos_reject_h4,
              " reject_cont=", g_micro_bos_reject_cont,
              " reject_failure=", g_micro_bos_reject_failure,
              " executed=", g_micro_bos_executed);
    }
    if(InpEnableSupplyDemandFlip)
    {
        Print("SDFLIP_SUMMARY detected=", g_sd_flip_detect_events,
              " generated=", g_sd_flip_generated,
              " monitors=", g_sd_flip_monitor_added,
              " confirmed=", g_sd_flip_confirmed,
              " skip_inactive=", g_sd_flip_skip_inactive,
              " skip_expired=", g_sd_flip_skip_expired,
              " skip_used=", g_sd_flip_skip_used,
              " skip_cooldown=", g_sd_flip_skip_cooldown,
              " skip_risk=", g_sd_flip_skip_risk,
              " skip_posmult=", g_sd_flip_skip_posmult,
              " reject_finalize=", g_sd_flip_reject_finalize,
              " reject_h4=", g_sd_flip_reject_h4,
              " reject_cont=", g_sd_flip_reject_cont,
              " reject_failure=", g_sd_flip_reject_failure,
              " executed=", g_sd_flip_executed);
    }
    if(InpEnableStrongSweepReversal)
    {
        Print("REVSWP_SUMMARY detected=", g_rev_sweep_detect_events,
              " generated=", g_rev_sweep_generated,
              " skip_dp=", g_rev_sweep_skip_dp,
              " skip_duplicate=", g_rev_sweep_skip_duplicate,
              " monitors=", g_rev_sweep_monitor_added,
              " confirmed=", g_rev_sweep_confirmed,
              " skip_inactive=", g_rev_sweep_skip_inactive,
              " skip_expired=", g_rev_sweep_skip_expired,
              " skip_used=", g_rev_sweep_skip_used,
              " skip_cooldown=", g_rev_sweep_skip_cooldown,
              " skip_risk=", g_rev_sweep_skip_risk,
              " skip_posmult=", g_rev_sweep_skip_posmult,
              " reject_finalize=", g_rev_sweep_reject_finalize,
              " reject_cont=", g_rev_sweep_reject_cont,
              " reject_failure=", g_rev_sweep_reject_failure,
              " executed=", g_rev_sweep_executed);
    }
    Print("WaiTrade3 ", InpVersion, " v1.00 已卸载 | 原因=", reason);
}

// ── OnTick ──
double g_htrg_used_high[32];
double g_htrg_used_low[32];
int g_htrg_used_direction[32];
datetime g_htrg_used_time[32];
int g_htrg_used_count = 0;

bool IsHTFRangeBoundaryUsedSMC(const HTFRange &range, int direction, double atr)
{
    double tol = MathMax(atr * 1.0, range.width_price * 0.03);
    int ttl_sec = (CfgRangeTF() >= 1440) ? 20 * 86400 : 5 * 86400;
    datetime now = TimeCurrent();
    for(int i = 0; i < g_htrg_used_count; i++)
    {
        if(g_htrg_used_direction[i] != direction)
            continue;
        if(now - g_htrg_used_time[i] > ttl_sec)
            continue;
        if(MathAbs(g_htrg_used_high[i] - range.high) <= tol &&
           MathAbs(g_htrg_used_low[i] - range.low) <= tol)
            return true;
    }
    return false;
}

void MarkHTFRangeBoundaryUsedSMC(const HTFRange &range, int direction)
{
    int idx = g_htrg_used_count;
    if(idx >= 32)
    {
        idx = 0;
        datetime oldest = g_htrg_used_time[0];
        for(int i = 1; i < 32; i++)
        {
            if(g_htrg_used_time[i] < oldest)
            {
                oldest = g_htrg_used_time[i];
                idx = i;
            }
        }
    }
    else
    {
        g_htrg_used_count++;
    }

    g_htrg_used_high[idx] = range.high;
    g_htrg_used_low[idx] = range.low;
    g_htrg_used_direction[idx] = direction;
    g_htrg_used_time[idx] = TimeCurrent();
}

bool HasHTFRangeBoundaryReactionSMC(string symbol, const HTFRange &range,
                                    ENUM_RANGE_POSITION range_pos, int direction,
                                    double &touch_price, double &confirm_price,
                                    double &reaction_atr)
{
    int tf_min = (CfgRangeTF() >= 1440) ? 15 : 5;
    ENUM_TIMEFRAMES tf = MinutesToTF(tf_min);
    MqlRates rates[60];
    int count = CopyRates(symbol, tf, 0, 60, rates);
    if(count < 24)
        return false;

    double atr = CalcATR(rates, count, InpATRPeriod);
    if(atr <= 0.0)
        return false;

    MqlRates c = rates[1];
    double candle_range = c.high - c.low;
    if(candle_range <= 0.0)
        return false;

    double body_dir = (c.close - c.open) * direction;
    bool touched = false;
    bool rejected = false;
    bool strict_structure = (MathAbs(CfgRangeMaxWidthATR()) >= 60.0);
    bool continuation_structure = (MathAbs(CfgRangeMaxWidthATR()) >= 80.0);
    bool departed_from_boundary = false;

    if(range_pos == RANGE_NEAR_BOTTOM && direction == OB_BUY)
    {
        touched = (c.low <= range.bottom_zone_high && c.high >= range.bottom_zone_low);
        double lower_wick = MathMin(c.open, c.close) - c.low;
        double wick_ratio = lower_wick / candle_range;
        bool close_reject = (c.close - c.low) / candle_range >= 0.55;
        rejected = (lower_wick >= atr * 0.20 && close_reject) ||
                   (body_dir >= atr * 0.12 && c.close > range.bottom_zone_high);
        for(int i = 2; i < MathMin(count, 12); i++)
        {
            if(rates[i].close > range.bottom_zone_high + atr * 0.35)
            {
                departed_from_boundary = true;
                break;
            }
        }
        if(strict_structure)
            rejected = rejected && (wick_ratio >= 0.35 || body_dir >= atr * 0.20) &&
                       departed_from_boundary;
        touch_price = c.low;
    }
    else if(range_pos == RANGE_NEAR_TOP && direction == OB_SELL)
    {
        touched = (c.high >= range.top_zone_low && c.low <= range.top_zone_high);
        double upper_wick = c.high - MathMax(c.open, c.close);
        double wick_ratio = upper_wick / candle_range;
        bool close_reject = (c.high - c.close) / candle_range >= 0.55;
        rejected = (upper_wick >= atr * 0.20 && close_reject) ||
                   (body_dir >= atr * 0.12 && c.close < range.top_zone_low);
        for(int i = 2; i < MathMin(count, 12); i++)
        {
            if(rates[i].close < range.top_zone_low - atr * 0.35)
            {
                departed_from_boundary = true;
                break;
            }
        }
        if(strict_structure)
            rejected = rejected && (wick_ratio >= 0.35 || body_dir >= atr * 0.20) &&
                       departed_from_boundary;
        touch_price = c.high;
    }

    if(continuation_structure)
    {
        bool found_touch = false;
        bool continued = false;
        double t_price = 0.0;
        double t_close = 0.0;
        int max_scan = MathMin(count, 12);

        for(int i = 2; i < max_scan; i++)
        {
            MqlRates t = rates[i];
            double t_range = t.high - t.low;
            if(t_range <= 0.0)
                continue;

            if(range_pos == RANGE_NEAR_BOTTOM && direction == OB_BUY)
            {
                bool t_touched = (t.low <= range.bottom_zone_high && t.high >= range.bottom_zone_low);
                double lower_wick = MathMin(t.open, t.close) - t.low;
                bool t_rejected = (lower_wick / t_range >= 0.30 &&
                                   (t.close - t.low) / t_range >= 0.55);
                if(!t_touched || !t_rejected)
                    continue;

                bool no_lower_low = true;
                for(int j = 1; j < i; j++)
                {
                    if(rates[j].low < t.low - atr * 0.08)
                    {
                        no_lower_low = false;
                        break;
                    }
                }
                double net_from_touch = c.close - t.close;
                double last_body = c.close - c.open;
                continued = no_lower_low &&
                            c.close > range.bottom_zone_high &&
                            net_from_touch >= atr * 0.18 &&
                            last_body >= atr * 0.08;
                found_touch = true;
                t_price = t.low;
                t_close = t.close;
                break;
            }
            else if(range_pos == RANGE_NEAR_TOP && direction == OB_SELL)
            {
                bool t_touched = (t.high >= range.top_zone_low && t.low <= range.top_zone_high);
                double upper_wick = t.high - MathMax(t.open, t.close);
                bool t_rejected = (upper_wick / t_range >= 0.30 &&
                                   (t.high - t.close) / t_range >= 0.55);
                if(!t_touched || !t_rejected)
                    continue;

                bool no_higher_high = true;
                for(int j = 1; j < i; j++)
                {
                    if(rates[j].high > t.high + atr * 0.08)
                    {
                        no_higher_high = false;
                        break;
                    }
                }
                double net_from_touch = t.close - c.close;
                double last_body = c.open - c.close;
                continued = no_higher_high &&
                            c.close < range.top_zone_low &&
                            net_from_touch >= atr * 0.18 &&
                            last_body >= atr * 0.08;
                found_touch = true;
                t_price = t.high;
                t_close = t.close;
                break;
            }
        }

        touched = found_touch;
        rejected = continued;
        if(found_touch)
        {
            touch_price = t_price;
            reaction_atr = MathAbs(c.close - t_close) / atr;
        }
    }

    if(!touched || !rejected)
        return false;

    confirm_price = c.close;
    if(!continuation_structure)
        reaction_atr = MathMax(0.0, body_dir / atr);
    return true;
}

bool ExecuteHTFRangeBoundarySignalSMC(double bid, double ask, string symbol)
{
    if(!CfgEnableRangeFade() || CfgRangeMaxWidthATR() > -40.0)
        return false;
    if(g_state.pos_count >= CfgMaxConcurrent())
        return false;

    static datetime s_last_range_entry = 0;
    int cooldown_min = (CfgRangeTF() >= 1440) ? 1440 : MathMax(120, CfgRangeTF());
    if(s_last_range_entry > 0 && TimeCurrent() - s_last_range_entry < cooldown_min * 60)
        return false;

    HTFRange range = GetHTFRange(symbol);
    if(!range.valid)
        return false;

    double mid_price = (bid + ask) / 2.0;
    ENUM_RANGE_POSITION range_pos = GetRangePosition(range, mid_price);
    int direction = 0;
    if(range_pos == RANGE_NEAR_BOTTOM)
        direction = OB_BUY;
    else if(range_pos == RANGE_NEAR_TOP)
        direction = OB_SELL;
    else
        return false;

    if(!PassSMCDirectionGate(direction))
        return false;
    if(!PassDirectionEntryHours(direction, TimeCurrent()))
        return false;
    if(!PassMonthlyEntryGuard())
        return false;
    if(!PassEntryMomentumFilter(direction))
        return false;

    double touch_price = 0.0;
    double confirm_price = 0.0;
    double reaction_atr = 0.0;
    if(!HasHTFRangeBoundaryReactionSMC(symbol, range, range_pos, direction,
                                       touch_price, confirm_price, reaction_atr))
        return false;

    double entry = (direction == OB_BUY) ? ask : bid;
    double htf_atr = (g_state.atr_1h > 0.0) ? g_state.atr_1h : MathMax(g_state.atr_value, 0.0);
    if(MathAbs(CfgRangeMaxWidthATR()) >= 60.0 &&
       IsHTFRangeBoundaryUsedSMC(range, direction, htf_atr))
        return false;
    double sl_buffer = MathMax(htf_atr * MathMax(CfgRangeSLBufferATR(), 0.5),
                               range.width_price * 0.03);
    sl_buffer = MathMin(sl_buffer, range.width_price * 0.12);
    double sl = (direction == OB_BUY) ? range.low - sl_buffer : range.high + sl_buffer;
    double risk_price = MathAbs(entry - sl);
    double spread = GetSpread(symbol);
    if(risk_price <= 0.0 || !PassSpreadRatio(risk_price, spread))
        return false;

    double tp = CalcRangeTP(range, range_pos, entry, direction);
    double pos_mult = (CfgRangePosMult() > 0.0) ? CfgRangePosMult() : 1.0;
    pos_mult = ApplyDirectionPosMult(direction, pos_mult);
    pos_mult = ApplyHourPositionMultiplier(pos_mult);
    pos_mult = ApplyBalancePositionMultiplier(pos_mult);
    pos_mult = ApplyMonthlyPositionMultiplier(pos_mult);
    pos_mult = ApplyRuntimePositionMultiplier(pos_mult);
    pos_mult = ApplyPositionMultiplierCap(pos_mult);
    if(pos_mult <= 0.0)
        return false;

    if(!PassFailureReentryConfirm(direction, false, pos_mult, ENTRY_FAMILY_MTF))
        return false;

    double final_lot = CalcEntryLot(symbol, CfgRiskPercent(), risk_price, pos_mult);
    final_lot = ApplyLotCap(final_lot);
    final_lot = ApplyBalanceLotCap(final_lot);
    if(CfgRangeMaxLot() > 0.0 && final_lot > CfgRangeMaxLot())
        final_lot = CfgRangeMaxLot();
    if(!PassMinRisk(final_lot, risk_price, symbol))
        return false;

    double margin_required = 0.0;
    ENUM_ORDER_TYPE order_type = (direction == OB_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    if(!OrderCalcMargin(order_type, symbol, final_lot, entry, margin_required))
        return false;
    double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
    if(margin_required > free_margin)
    {
        if(free_margin <= 0.0)
            return false;
        final_lot = final_lot * (free_margin / margin_required) * 0.95;
        final_lot = ApplyLotCap(final_lot);
        final_lot = ApplyBalanceLotCap(final_lot);
        if(CfgRangeMaxLot() > 0.0 && final_lot > CfgRangeMaxLot())
            final_lot = CfgRangeMaxLot();
    }

    double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    double lot_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
    double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    if(lot_step <= 0.0)
        return false;
    final_lot = MathFloor(final_lot / lot_step) * lot_step;
    if(final_lot < lot_min) final_lot = lot_min;
    if(final_lot > lot_max) return false;

    TradeSignal sig;
    ZeroMemory(sig);
    sig.direction = direction;
    sig.entry = entry;
    sig.sl = sl;
    sig.tp = tp;
    sig.risk_price = risk_price;
    sig.lot = NormalizeDouble(final_lot, 2);
    sig.pos_mult = pos_mult;
    sig.ob_index = -1;
    sig.deep_entry = false;
    sig.touch_price = touch_price;
    sig.confirm_price = confirm_price;
    sig.bounce_seconds = 0;
    sig.bounce_ob_pct = reaction_atr;
    sig.confirm_ob_pos = (range.width_price > 0.0) ? (confirm_price - range.mid) / range.width_price : 0.0;
    sig.htf_target = true;
    sig.htf_partial_r = InpHTFPartialR;
    sig.htf_partial_pct = InpHTFPartialPct;
    sig.comment = "WT " + InpVersion + " " + (direction > 0 ? "B" : "S") +
                  " HTRG " + RangePositionToString(range_pos) +
                  " x" + DoubleToString(pos_mult, 1);

    if(ExecuteSignalFromZone(sig, g_zones, g_state.ob_count, false))
    {
        if(MathAbs(CfgRangeMaxWidthATR()) >= 60.0)
            MarkHTFRangeBoundaryUsedSMC(range, direction);
        s_last_range_entry = TimeCurrent();
        g_state.last_entry_bar = g_state.bar_count;
        g_state.pos_count++;
        return true;
    }
    return false;
}

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
            ZeroMemory(g_rev_sweep_zones);
            ZeroMemory(g_rev_sweep_monitors);
            g_rev_sweep_zone_count = 0;
            g_rev_sweep_monitor_count = 0;
            g_rev_sweep_cooldown = 0;
            ZeroMemory(g_range_reaction_zones);
            ZeroMemory(g_range_reaction_monitors);
            g_range_reaction_zone_count = 0;
            g_range_reaction_monitor_count = 0;
            g_range_reaction_cooldown = 0;
            g_htf_ob_react_last_level = 0.0;
            g_htf_ob_react_last_dir = 0;
            g_htf_ob_react_last_time = 0;
            ResetHTFRejectContext();
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
            if(!InpKeepZonesOnProfileSwitch)
            {
                ZeroMemory(g_zones);
                ZeroMemory(g_htf_zones);
                g_state.ob_count = 0;
                g_htf_zone_count = 0;
                g_monitor_count = 0;
                g_htf_monitor_count = 0;
            }
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
        DetectH4BOS(symbol);
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

        if(InpEnableMicroBOSRetest)
            DetectMicroBOSRetestZones(symbol, g_state.bar_count);
        UpdateHTFRejectContextFromRange(rates, copied, g_state.atr_value);
        UpdateStrongWickRejectContext(symbol);
        if(InpEnableSupplyDemandFlip)
            DetectSupplyDemandFlips(symbol, g_zones, g_state.ob_count, g_state.bar_count);
        if(InpEnableStrongSweepReversal)
            DetectStrongSweepReversalZones(symbol, g_state.bar_count);

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
    if(InpEnableMicroBOSRetest)
        UpdateOBStatus(g_micro_bos_zones, g_micro_bos_zone_count, bid, ask, g_state);
    if(InpEnableSupplyDemandFlip)
        UpdateSignalZoneTouches(g_sd_flip_zones, g_sd_flip_zone_count, bid, ask);
    if(InpEnableStrongSweepReversal)
        UpdateSignalZoneTouches(g_rev_sweep_zones, g_rev_sweep_zone_count, bid, ask);
    if(CfgRangeTPTarget() == 2)
        UpdateSignalZoneTouches(g_range_reaction_zones, g_range_reaction_zone_count, bid, ask);

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
        g_state.pos_count = CountActivePositionsForMainConcurrency();

    if(InpEnableEntryEngine)
    {
        if(g_osc_active)
            RegisterChannelMonitors(g_zones_osc, g_state_osc, g_monitors_osc, g_monitor_count_osc, new_active_bar, symbol);
        else
            RegisterChannelMonitors(g_zones, g_state, g_monitors, g_monitor_count, new_active_bar, symbol);

        if(!g_osc_active)
            RegisterMicroBOSMonitors(g_state, new_active_bar, symbol);
        if(!g_osc_active)
            RegisterSupplyDemandFlipMonitors(g_state, new_active_bar, symbol);
        if(!g_osc_active)
            RegisterStrongSweepReversalMonitors(g_state, new_active_bar, symbol);
        if(!g_osc_active)
            RegisterRangeReactionMonitors(g_state, new_active_bar, symbol);
        if(!g_osc_active && new_active_bar)
        {
            DetectRangeReactionZones(symbol, g_state.bar_count, bid, ask);
            if(CfgRangeTPTarget() == 2)
            {
                for(int rz = 0; rz < g_range_reaction_zone_count; rz++)
                {
                    if(g_state.pos_count >= CfgMaxConcurrent())
                        break;
                    if(TryExecuteRangeReactionZone(rz, symbol))
                    {
                        HTFRange used_range = GetHTFRange(symbol);
                        if(used_range.valid && CfgRangeTF() >= 1440 && !CfgRangeHTFOBReactionOnly())
                            MarkHTFRangeBoundaryUsedSMC(used_range, g_range_reaction_zones[rz].direction);
                        g_state.last_entry_bar = g_state.bar_count;
                        g_state.pos_count++;
                        g_range_reaction_executed++;
                        g_range_reaction_cooldown = (CfgRangeTF() >= 1440) ? 24 : 16;
                    }
                }
            }
        }

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

        if(!g_osc_active)
            ExecuteMicroBOSConfirmed(bid, ask, symbol);
        if(!g_osc_active)
            ExecuteSupplyDemandFlipConfirmed(bid, ask, symbol);
        if(!g_osc_active)
            ExecuteStrongSweepReversalConfirmed(bid, ask, symbol);
        if(!g_osc_active)
            ExecuteRangeReactionConfirmed(bid, ask, symbol);

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
                    int failure_reentry_family = EntryFamilyFromSignal(htf_confirmed[i], g_htf_zones[htf_confirmed[i].ob_index]);
                    if(!PassFailureReentryConfirm(htf_confirmed[i].direction, false,
                                                  htf_confirmed[i].pos_mult, failure_reentry_family)) continue;
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
                bool failure_reentry_is_sweep = false;
                if(g_signals[i].ob_index >= 0 && g_signals[i].ob_index < g_state_osc.ob_count)
                    failure_reentry_is_sweep = g_zones_osc[g_signals[i].ob_index].is_liquidity_sweep ||
                                               IsLooseSweepZone(g_zones_osc[g_signals[i].ob_index]);
                int failure_reentry_family = EntryFamilyFromSignalNoZone(g_signals[i]);
                if(g_signals[i].ob_index >= 0 && g_signals[i].ob_index < g_state_osc.ob_count)
                    failure_reentry_family = EntryFamilyFromSignal(g_signals[i], g_zones_osc[g_signals[i].ob_index]);
                if(g_signals[i].ob_index >= 0 && g_signals[i].ob_index < g_state_osc.ob_count &&
                   !PassPlainSweepDPGate(g_zones_osc[g_signals[i].ob_index], g_signals[i].direction))
                {
                    if(InpEnableEntryDebug) Print("FINAL_DIAG z=", g_signals[i].ob_index,
                       " dir=", g_signals[i].direction, " skip=plain_swp_dp_osc");
                    continue;
                }
                double failure_reentry_price = (g_signals[i].direction > 0) ? ask : bid;
                if(!PassFailureReentryConfirm(g_signals[i].direction, failure_reentry_is_sweep,
                                              g_signals[i].pos_mult, failure_reentry_family,
                                              failure_reentry_price)) continue;
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
                bool failure_reentry_is_sweep = false;
                if(g_signals[i].ob_index >= 0 && g_signals[i].ob_index < g_state.ob_count)
                    failure_reentry_is_sweep = g_zones[g_signals[i].ob_index].is_liquidity_sweep ||
                                               IsLooseSweepZone(g_zones[g_signals[i].ob_index]);
                int failure_reentry_family = EntryFamilyFromSignalNoZone(g_signals[i]);
                if(g_signals[i].ob_index >= 0 && g_signals[i].ob_index < g_state.ob_count)
                    failure_reentry_family = EntryFamilyFromSignal(g_signals[i], g_zones[g_signals[i].ob_index]);
                if(g_signals[i].ob_index >= 0 && g_signals[i].ob_index < g_state.ob_count &&
                   !PassPlainSweepDPGate(g_zones[g_signals[i].ob_index], g_signals[i].direction))
                {
                    if(InpEnableEntryDebug) Print("FINAL_DIAG z=", g_signals[i].ob_index,
                       " dir=", g_signals[i].direction, " skip=plain_swp_dp");
                    continue;
                }
                double failure_reentry_price = (g_signals[i].direction > 0) ? ask : bid;
                if(!PassFailureReentryConfirm(g_signals[i].direction, failure_reentry_is_sweep,
                                              g_signals[i].pos_mult, failure_reentry_family,
                                              failure_reentry_price)) continue;
                if(ExecuteSignal(g_signals[i])) { g_state.last_entry_bar = g_state.bar_count; g_state.pos_count++; }
            }
        }
    }

    // 6. 心跳
    {
    if(!g_osc_active)
        ExecuteHTFRangeBoundarySignalSMC(bid, ask, symbol);

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
    UpdateStructureHoldRelease(g_tracks, g_track_count);
    UpgradeHTFOBTouchHolds(g_tracks, g_track_count);
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
                    if(ShouldHoldStructureMomentum(g_tracks[t]))
                    {
                        if(InpStructureLogBOS)
                            Print("STRUCT_MOM_HOLD ticket=", g_tracks[t].ticket,
                                  " dir=", g_tracks[t].direction,
                                  " keepSL=", DoubleToString(g_tracks[t].sl_initial, _Digits),
                                  " newSL=", DoubleToString(structure_sl, _Digits));
                        continue;
                    }
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

int CountActivePositionsByFamily(int entry_family)
{
    int count = 0;
    for(int i = 0; i < g_track_count; i++)
    {
        if(g_tracks[i].ticket == 0) continue;
        if(g_tracks[i].entry_family != entry_family) continue;
        if(!PositionSelectByTicket(g_tracks[i].ticket)) continue;
        count++;
    }
    return count;
}

int CountActivePositionsForMainConcurrency()
{
    int count = CountActivePositions();
    if(!InpMicroBOSUseStructureHold)
        return count;
    int mbos_count = CountActivePositionsByFamily(ENTRY_FAMILY_MBOS);
    int main_count = count - mbos_count;
    return main_count > 0 ? main_count : 0;
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

    bool is_bos = (sig.ob_index >= 20000);
    string comment = is_bos
        ? StringFormat("WT %s BOS %s x%.1f", InpVersion, dir_str, sig.pos_mult)
        : StringFormat("WT %s MTF %s x%.1f", InpVersion, dir_str, sig.pos_mult);

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
                         false, 0, 0.0, sig.pos_mult, 0, 0, 0, false, false, g_tracks, g_track_count,
                         is_bos ? ENTRY_FAMILY_BOS : ENTRY_FAMILY_MTF);

        if(g_track_count > 0)
        {
            g_tracks[g_track_count - 1].open_bar = g_state.bar_count;
            g_tracks[g_track_count - 1].entry_market_state = g_state.market_state;
            if(sig.ob_index >= 20000 && PassStructureHoldQuality(sig.direction))
            {
                g_tracks[g_track_count - 1].use_structure_sl = true;
                g_tracks[g_track_count - 1].skip_mfe_exits = InpStructSkipMFEExits;
            }
        }

        if(!is_bos)
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
    int entry_family = EntryFamilyFromSignalNoZone(sig);
    if(sig.ob_index >= 0 && sig.ob_index < zone_count)
        entry_family = EntryFamilyFromSignal(sig, zones[sig.ob_index]);
    bool htf_reject_hold = ShouldUseHTFRejectHold(sig, entry_family);
    request.tp        = htf_reject_hold ? 0.0 : sig.tp;
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
                         sig.deep_entry, sig.bounce_seconds, sig.confirm_ob_pos, sig.pos_mult,
                         htf_reject_hold ? true : sig.htf_target,
                         sig.htf_partial_r, sig.htf_partial_pct,
                         sig.trend_release,
                         sig.failure_reverse,
                         g_tracks, g_track_count, entry_family);

        if(g_track_count > 0)
        {
            g_tracks[g_track_count - 1].open_bar = g_state.bar_count;
            g_tracks[g_track_count - 1].entry_market_state = g_state.market_state;
            if(htf_reject_hold)
            {
                g_tracks[g_track_count - 1].skip_mfe_exits = true;
                g_tracks[g_track_count - 1].htf_target = true;
            }
        }

        if(allow_layered && InpLayeredEntryCount >= 2)
            ExecuteLayeredOrders(sig, result.price);
        ExecuteMicroEntryOrders(sig);

        // BOS retest (ob_index >= 20000) vs MTF OB (>= 10000) vs M1 OB
        if(sig.ob_index >= 20000)
        {
            g_sb_signal.state = BOS_EXECUTED;
            if(g_sb_signal.from_h4)
                g_sb_signal.last_entry_age = g_sb_signal.age_bars;
            else
            {
                g_sb_signal.last_entry_age = 0;
                g_sb_signal.age_bars = 0;
            }
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
                         sig.deep_entry, sig.bounce_seconds, sig.confirm_ob_pos, sig.pos_mult,
                         sig.htf_target, sig.htf_partial_r, sig.htf_partial_pct,
                         sig.trend_release,
                         sig.failure_reverse,
                         g_tracks, g_track_count, EntryFamilyFromSignalNoZone(sig));
        if(g_track_count > 0)
        {
            g_tracks[g_track_count - 1].open_bar = g_state.bar_count;
            g_tracks[g_track_count - 1].entry_market_state = g_state.market_state;
        }
    }

    return placed;
}
