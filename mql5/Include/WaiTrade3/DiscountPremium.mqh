// WaiTrade3 DiscountPremium — HTF 折扣/溢价区过滤器
// 多头只能在折扣区入场，空头只能在溢价区入场
#ifndef __DISCOUNT_PREMIUM_MQH__
#define __DISCOUNT_PREMIUM_MQH__

#include <WaiTrade3/TypesSMC.mqh>
#include <WaiTrade3/ConfigSMC.mqh>

// ── 计算当前价格在 HTF 区间中的位置 ──
// 返回 0.0~1.0: 0=区间底部, 1=区间顶部
double CalcHTFPositionRatio(const MqlRates &rates[], int copied,
                            int lookback, int htf_period_min)
{
    if(copied < lookback) return 0.5;

    double htf_high = rates[0].high;
    double htf_low  = rates[0].low;

    for(int i = 1; i < lookback && i < copied; i++)
    {
        if(rates[i].high > htf_high) htf_high = rates[i].high;
        if(rates[i].low  < htf_low)  htf_low  = rates[i].low;
    }

    double range = htf_high - htf_low;
    if(range <= 0) return 0.5;

    return (rates[copied - 1].close - htf_low) / range;
}

// ── 检查是否为折扣/溢价区 ──
// 返回 true 如果方向与其 HTF 位置匹配
// 对于买入: 需要在折扣区 (ratio < InpDiscountMaxRatio)
// 对于卖出: 需要在溢价区 (ratio > InpPremiumMinRatio)
bool PassDiscountPremiumFilter(int direction, const MqlRates &rates[],
                               int copied, int lookback, int htf_period_min)
{
    if(!InpEnableDiscountPremium) return true;
    if(lookback < 5) return true;

    double ratio = CalcHTFPositionRatio(rates, copied, lookback, htf_period_min);

    if(direction == OB_BUY)
        return ratio <= InpDiscountMaxRatio;
    else // OB_SELL
        return ratio >= InpPremiumMinRatio;
}

// ── 获取折扣/溢价乘数 ──
// 在折扣区 = 正常乘数; 溢价区(逆势) = 降权
double GetDiscountPremiumMult(int direction, const MqlRates &rates[],
                              int copied, int lookback, int htf_period_min)
{
    if(!InpEnableDiscountPremium || !InpDPEntryMult) return 1.0;
    if(lookback < 5) return 1.0;

    double ratio = CalcHTFPositionRatio(rates, copied, lookback, htf_period_min);

    if(direction == OB_BUY && ratio <= InpDiscountMaxRatio)
        return InpDPEntryMult;
    if(direction == OB_SELL && ratio >= InpPremiumMinRatio)
        return InpDPEntryMult;

    // 溢价区做多 或 折扣区做空 → 逆势
    if(InpDPEntryMult > 0)
        return InpDPEntryMult;  // 降权
    return 0.0;  // 过滤
}

// ── 更新Zone的折扣/溢价比（供OB评分使用） ──
void UpdateZoneDiscountRatio(SMCZoneData &smc, int zone_direction,
                             const MqlRates &rates[], int copied,
                             int lookback, int htf_period_min)
{
    if(!InpEnableDiscountPremium) return;
    smc.discount_ratio = CalcHTFPositionRatio(rates, copied, lookback, htf_period_min);
    smc.in_discount_zone = PassDiscountPremiumFilter(zone_direction, rates,
                                                     copied, lookback, htf_period_min);
}

#endif
