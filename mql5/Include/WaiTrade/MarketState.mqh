#ifndef __WAITRADE_MARKET_STATE_MQH__
#define __WAITRADE_MARKET_STATE_MQH__

#include "Config.mqh"
#include "Types.mqh"
#include "MathUtils.mqh"

enum MARKET_STATE { STATE_BULLISH=1, STATE_BEARISH=-1, STATE_RANGE=0 };

struct SwingPoint {
    double price;
    int    bar_index;
    int    type; // 1=high, -1=low
};

bool IsSwingHigh(const MqlRates &rates[], int idx, int strength, int total)
{
    if(idx - strength < 0 || idx + strength >= total)
        return false;
    double hi = rates[idx].high;
    for(int j = 1; j <= strength; j++)
    {
        if(rates[idx - j].high >= hi) return false;
        if(rates[idx + j].high >= hi) return false;
    }
    return true;
}

bool IsSwingLow(const MqlRates &rates[], int idx, int strength, int total)
{
    if(idx - strength < 0 || idx + strength >= total)
        return false;
    double lo = rates[idx].low;
    for(int j = 1; j <= strength; j++)
    {
        if(rates[idx - j].low <= lo) return false;
        if(rates[idx + j].low <= lo) return false;
    }
    return true;
}

MARKET_STATE DetectMarketState(string symbol, double &target_price)
{
    MqlRates rates[];
    int count = CopyRates(symbol, PERIOD_M15, 0, InpTrendLookback, rates);
    if(count < InpSwingStrength * 2 + 5)
        return STATE_RANGE;

    SwingPoint highs[];
    SwingPoint lows[];
    ArrayResize(highs, 0);
    ArrayResize(lows, 0);

    for(int i = InpSwingStrength; i < count - InpSwingStrength; i++)
    {
        if(IsSwingHigh(rates, i, InpSwingStrength, count))
        {
            int sz = ArraySize(highs);
            ArrayResize(highs, sz + 1);
            highs[sz].price     = rates[i].high;
            highs[sz].bar_index = i;
            highs[sz].type      = 1;
        }
        if(IsSwingLow(rates, i, InpSwingStrength, count))
        {
            int sz = ArraySize(lows);
            ArrayResize(lows, sz + 1);
            lows[sz].price     = rates[i].low;
            lows[sz].bar_index = i;
            lows[sz].type      = -1;
        }
    }

    int nh = ArraySize(highs);
    int nl = ArraySize(lows);
    if(nh < 2 || nl < 2)
    {
        target_price = 0;
        return STATE_RANGE;
    }

    double sh1 = highs[nh - 1].price;
    double sh2 = highs[nh - 2].price;
    double sl1 = lows[nl - 1].price;
    double sl2 = lows[nl - 2].price;

    bool hh = (sh1 > sh2);
    bool hl = (sl1 > sl2);
    bool lh = (sh1 < sh2);
    bool ll = (sl1 < sl2);

    MARKET_STATE state = STATE_RANGE;
    if(hh && hl) state = STATE_BULLISH;
    if(lh && ll) state = STATE_BEARISH;

    if(state == STATE_RANGE)
    {
        target_price = (sh1 > sl1) ? sh1 : sl1;
        double alt   = (sh1 > sl1) ? sl1 : sh1;
        if(MathAbs(target_price) < MathAbs(alt))
            target_price = alt;
    }
    else if(state == STATE_BULLISH)
    {
        target_price = sh1;
    }
    else
    {
        target_price = sl1;
    }

    return state;
}

#endif // __WAITRADE_MARKET_STATE_MQH__
