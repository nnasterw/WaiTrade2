// WaiTrade3 OBScorer — OB 四维质量评分系统
// 评分维度：趋势突破/位移K线/流动性关联/缓解率/折扣区位置
#ifndef __OB_SCORER_MQH__
#define __OB_SCORER_MQH__

#include <WaiTrade3/TypesSMC.mqh>
#include <WaiTrade3/ConfigSMC.mqh>
#include <WaiTrade3/StructureTracker.mqh>

// ── 检查OB是否伴随趋势突破 ──
bool HasTrendBreak(const OBZone &zone, TrendState trend)
{
    // 多头OB形成在bullish趋势中 = 顺趋势
    if(zone.direction == OB_BUY && trend == TREND_BULLISH) return true;
    // 空头OB形成在bearish趋势中 = 顺趋势
    if(zone.direction == OB_SELL && trend == TREND_BEARISH) return true;
    return false;
}

// ── 检查是否伴随位移K线 ──
bool HasDisplacement(const OBZone &zone, double atr, double min_impulse_pct)
{
    // zone.strength 字段（已在OBDetector中计算）反映位移强度
    if(min_impulse_pct <= 0) min_impulse_pct = 50.0;
    return zone.strength >= 2.0;  // strength >= 2 = 位移确认
}

// ── 计算缓解率 ──
double CalcMitigationPct(const OBZone &zone)
{
    double range = zone.high - zone.low;
    if(range <= 0) return 0.0;

    double mitigation = 0;

    // 基于touch_count估算（实际缓解需要price history，这里用touch_count近似）
    if(zone.touch_count > 0)
    {
        // 假设每次touch缓解约 20%
        mitigation = MathMin(zone.touch_count * 0.20, 1.0);
    }

    return mitigation;
}

// ── 四维评分主函数 ──
// 返回 0-100 分
int ScoreOBZone(const OBZone &zone, TrendState trend, double atr,
                bool liquidity_linked, double discount_ratio,
                bool in_discount_zone)
{
    if(!InpEnableOBScoring) return 100;  // 未启用时默认通过

    int score = 0;

    // 1. 趋势突破权重 (30)
    if(InpOBScoreTrendWeight > 0 && HasTrendBreak(zone, trend))
        score += (int)InpOBScoreTrendWeight;

    // 2. 位移K线权重 (25)
    if(InpOBScoreDisplacementWeight > 0 && HasDisplacement(zone, atr, InpMinImpulseBodyPct))
        score += (int)InpOBScoreDisplacementWeight;

    // 3. 流动性关联权重 (20)
    if(InpOBScoreLiquidityWeight > 0 && liquidity_linked)
        score += (int)InpOBScoreLiquidityWeight;

    // 4. 缓解率权重 (15) — 缓解越低越好
    if(InpOBScoreMitigationWeight > 0)
    {
        double mit = CalcMitigationPct(zone);
        double mit_score = (1.0 - mit) * InpOBScoreMitigationWeight;
        score += (int)mit_score;
    }

    // 5. 折扣区权重 (10) — 在正确位置的加成
    if(InpOBScoreDiscountWeight > 0 && in_discount_zone)
        score += (int)InpOBScoreDiscountWeight;

    return MathMin(score, 100);
}

// ── 批量评分所有zone ──
void ScoreAllZones(OBZone &zones[], int ob_count, EAState &state,
                   SMCZoneData &smc_data[], const MqlRates &rates[], int copied,
                   TrendState trend_state)
{
    if(!InpEnableOBScoring) return;

    int dp_lookback = (InpDPLookbackBars > 0) ? MathMin(InpDPLookbackBars, copied - 2) : 20;
    if(dp_lookback < 5) dp_lookback = 5;

    for(int z = 0; z < ob_count; z++)
    {
        if(zones[z].expired) continue;

        // 计算折扣区位置
        double dp_ratio = 0.5;
        bool in_dp = true;
        if(InpEnableDiscountPremium)
        {
            dp_ratio = CalcHTFPositionRatio(rates, copied, dp_lookback, InpDPHTFPeriod);
            in_dp = PassDiscountPremiumFilter(zones[z].direction, rates, copied,
                                             dp_lookback, InpDPHTFPeriod);
        }

        // 检查流动性关联（从全局g_lpools读取）
        // 注意：这里需要全局lpools引用，但函数签名不能引用全局
        // 所以从smc_data预先计算的字段获取
        bool liquidity_linked = smc_data[z].liquidity_linked;

        int score = ScoreOBZone(zones[z], trend_state, state.atr_value,
                               liquidity_linked, dp_ratio, in_dp);
        smc_data[z].quality_score = score;
        smc_data[z].discount_ratio = dp_ratio;
        smc_data[z].in_discount_zone = in_dp;

        if(InpOBScoreLogLow && score < InpOBScoreMinPass)
            Print("[SMC] OB评分低: z=", z, " dir=", zones[z].direction,
                  " score=", score, " / ", InpOBScoreMinPass);
    }
}

// ── 检查OB评分是否通过 ──
bool PassOBScoringGate(int zone_index, const SMCZoneData &smc_data[],
                       int ob_count)
{
    if(!InpEnableOBScoring) return true;
    if(zone_index < 0 || zone_index >= ob_count) return true;
    return smc_data[zone_index].quality_score >= InpOBScoreMinPass;
}

#endif
