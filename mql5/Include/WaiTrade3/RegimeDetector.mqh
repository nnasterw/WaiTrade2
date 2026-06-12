// WaiTrade3 RegimeDetector — 震荡/趋势双轨制检测
// 整合: H4方向 + BOS活跃度 + OB触碰密度 + OB数量
#ifndef __REGIME_DETECTOR_MQH__
#define __REGIME_DETECTOR_MQH__

#include <WaiTrade2/Types.mqh>
#include <WaiTrade3/TypesSMC.mqh>
#include <WaiTrade3/StructureTracker.mqh>

// ════════════════════════════════════════════════
// 市场体制枚举
// ════════════════════════════════════════════════
enum ENUM_MARKET_REGIME {
    REGIME_UNKNOWN = 0,
    REGIME_TRENDING,    // 趋势市: Bounce scalping全火力
    REGIME_CHOP         // 震荡市: BOS优先 + OB反转
};

// ════════════════════════════════════════════════
// 体制检测器状态
// ════════════════════════════════════════════════
struct RegimeState {
    ENUM_MARKET_REGIME current;      // 当前体制
    ENUM_MARKET_REGIME previous;     // 上一体制(防抖动)

    int    stable_bars;             // 当前体制已稳定bars数
    int    h4_trend;                // H4趋势方向(TREND_BULLISH/BEARISH/CHOP)
    int    bos_signals_recent;      // 最近480bar内的BOS信号数
    int    max_ob_touches;          // 全局最高OB触碰数
    int    active_ob_count;         // 当前活跃OB数量
    int    trend_score;             // 趋势评分(0-7)

    datetime last_update;           // 最后更新时间
    int    chop_entry_block_count;  // 震荡市拦截的Bounce入场数
    int    reverse_entry_count;     // 震荡市反转入场数
};

RegimeState g_regime;

// ════════════════════════════════════════════════
// 初始化
// ════════════════════════════════════════════════
void InitRegimeDetector()
{
    ZeroMemory(g_regime);
    g_regime.current = REGIME_UNKNOWN;
    g_regime.previous = REGIME_UNKNOWN;
    g_regime.stable_bars = 0;
}

// ════════════════════════════════════════════════
// 更新体制检测 (每个新bar调用一次)
// ════════════════════════════════════════════════
void UpdateRegime(string symbol, int bar_count)
{
    // 1. H4趋势信号 (来自StructureTracker或独立检测)
    //    TREND_BULLISH/TREND_BEARISH = 趋势, TREND_CHOP/UNKNOWN = 震荡
    bool h4_trending = (g_regime.h4_trend == TREND_BULLISH || g_regime.h4_trend == TREND_BEARISH);

    // 2. BOS活跃度: 最近480bar内有BOS执行=趋势(信号来自外部设置)
    //    g_regime.bos_signals_recent 由EA在BOS执行/过期时更新

    // 3. OB触碰密度: 全局最高OB触碰数≥8=价格反复回同一区域=震荡
    bool ob_over_touched = (g_regime.max_ob_touches >= 8);

    // 4. OB数量: 活跃OB>15=多空分歧大=偏震荡
    bool too_many_obs = (g_regime.active_ob_count > 15);

    // ══ 综合评分 ══
    int score = 0;
    if(h4_trending)               score += 3;  // H4有方向=强趋势信号
    if(g_regime.bos_signals_recent >= 1) score += 2;  // BOS活跃=价格突破结构
    if(!ob_over_touched)          score += 1;  // OB未被反复摩擦
    if(!too_many_obs)             score += 1;  // OB数量适中

    g_regime.trend_score = score;

    // ══ 体制判定 (带滞后) ══
    ENUM_MARKET_REGIME new_regime;
    if(score >= 4)       new_regime = REGIME_TRENDING;   // 5→4: 更容易趋势
    else if(score <= 2)  new_regime = REGIME_CHOP;
    else                 new_regime = REGIME_UNKNOWN;  // 中间态→持留

    // 滞后: 需要连续N bar确认才切换
    if(new_regime != g_regime.current)
    {
        if(new_regime == REGIME_UNKNOWN)
        {
            // UNKNOWN→不切换,保持当前
            g_regime.stable_bars++;
        }
        else if(g_regime.stable_bars >= 5)  // 需要5bar确认(防抖动)
        {
            // 切换体制
            g_regime.previous = g_regime.current;
            g_regime.current = new_regime;
            g_regime.stable_bars = 0;
            if(InpStructureLogBOS)
                Print("[REGIME] 切换→", (new_regime == REGIME_TRENDING ? "TREND" : "CHOP"),
                      " score=", score, " H4=", g_regime.h4_trend,
                      " BOS=", g_regime.bos_signals_recent,
                      " OBtouch=", g_regime.max_ob_touches,
                      " OBs=", g_regime.active_ob_count);
        }
        else
        {
            g_regime.stable_bars++;
        }
    }
    else
    {
        g_regime.stable_bars++;
    }

    g_regime.last_update = TimeCurrent();
}

// ════════════════════════════════════════════════
// 查询: 是否趋势市
// ════════════════════════════════════════════════
bool IsTrending() { return g_regime.current == REGIME_TRENDING; }

// ════════════════════════════════════════════════
// 查询: 是否震荡市
// ════════════════════════════════════════════════
bool IsChopping() { return g_regime.current == REGIME_CHOP; }

// ════════════════════════════════════════════════
// 路径B: 纯BOS模式(返回true=当前只应使用BOS入场)
// ════════════════════════════════════════════════
bool IsBOSOnlyMode(bool enable_path_b)
{
    if(!enable_path_b) return false;
    // 路径B: 始终使用BOS, 不用Bounce
    return true;
}

// ════════════════════════════════════════════════
// 诊断输出
// ════════════════════════════════════════════════
void PrintRegimeDiag()
{
    Print("[REGIME] current=", (g_regime.current == REGIME_TRENDING ? "TREND" :
           (g_regime.current == REGIME_CHOP ? "CHOP" : "UNKNOWN")),
          " score=", g_regime.trend_score,
          " stable=", g_regime.stable_bars,
          " H4=", g_regime.h4_trend,
          " BOS=", g_regime.bos_signals_recent,
          " OBt=", g_regime.max_ob_touches,
          " OBs=", g_regime.active_ob_count,
          " blocked=", g_regime.chop_entry_block_count,
          " reversed=", g_regime.reverse_entry_count);
}

#endif
