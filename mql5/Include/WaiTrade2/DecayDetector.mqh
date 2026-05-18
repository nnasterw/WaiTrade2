#ifndef __WAITRADE_DECAY_DETECTOR_MQH__
#define __WAITRADE_DECAY_DETECTOR_MQH__

#include "Config.mqh"
#include "Types.mqh"
#include "MathUtils.mqh"

bool CheckMomentumDecay(string symbol, int direction, const MqlRates &rates[], int count)
{
    int need = InpDecayBars + 2;
    if(count < need)
        return false;

    // 条件1: 二推不破
    bool cond1 = false;
    {
        int start = count - InpDecayBars;
        if(direction > 0)
        {
            double ref_high = rates[start - 1].high;
            bool no_new_high = true;
            for(int i = start; i < count; i++)
            {
                if(rates[i].high > ref_high)
                { no_new_high = false; break; }
            }
            if(no_new_high && InpDecayBars >= 3)
            {
                int a = count - 3, b = count - 2, c = count - 1;
                if(rates[c].high < rates[b].high && rates[b].high < rates[a].high &&
                   rates[c].low  < rates[b].low  && rates[b].low  < rates[a].low)
                    cond1 = true;
            }
        }
        else
        {
            double ref_low = rates[start - 1].low;
            bool no_new_low = true;
            for(int i = start; i < count; i++)
            {
                if(rates[i].low < ref_low)
                { no_new_low = false; break; }
            }
            if(no_new_low && InpDecayBars >= 3)
            {
                int a = count - 3, b = count - 2, c = count - 1;
                if(rates[c].high > rates[b].high && rates[b].high > rates[a].high &&
                   rates[c].low  > rates[b].low  && rates[b].low  > rates[a].low)
                    cond1 = true;
            }
        }
    }

    // 条件2: 吞没 + 追随
    bool cond2 = false;
    if(count >= 3)
    {
        int e = count - 2; // 吞没bar
        int f = count - 1; // 追随bar
        int p = count - 3; // 吞没前一根

        if(direction > 0)
        {
            bool engulf = (rates[e].close < rates[p].open);
            double f_body = MathAbs(rates[f].close - rates[f].open);
            double f_range = rates[f].high - rates[f].low;
            bool follow = (rates[f].close < rates[f].open) &&
                          (f_range > 0 && f_body / f_range * 100.0 >= InpEngulfBodyPct);
            if(engulf && follow)
                cond2 = true;
        }
        else
        {
            bool engulf = (rates[e].close > rates[p].open);
            double f_body = MathAbs(rates[f].close - rates[f].open);
            double f_range = rates[f].high - rates[f].low;
            bool follow = (rates[f].close > rates[f].open) &&
                          (f_range > 0 && f_body / f_range * 100.0 >= InpEngulfBodyPct);
            if(engulf && follow)
                cond2 = true;
        }
    }

    return (cond1 || cond2);
}

#endif // __WAITRADE_DECAY_DETECTOR_MQH__
