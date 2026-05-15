//+------------------------------------------------------------------+
//| Utils.mqh — 工具函数 (ATR/特征计算/时段判断)                        |
//+------------------------------------------------------------------+
#ifndef __WAITRADE_UTILS_MQH__
#define __WAITRADE_UTILS_MQH__

// ATR计算 (EMA方式，和Python atr_values一致)
double CalcATR(const double &high[], const double &low[], const double &close[], int idx, int period=14)
{
   if(idx < period) return high[idx] - low[idx];
   double alpha = 2.0 / (period + 1.0);
   double atr = high[0] - low[0];
   for(int i = 1; i <= idx && i < ArraySize(high); i++)
   {
      double tr = MathMax(high[i] - low[i],
                  MathMax(MathAbs(high[i] - close[i-1]),
                          MathAbs(low[i] - close[i-1])));
      atr = alpha * tr + (1.0 - alpha) * atr;
   }
   return atr;
}

// 批量计算ATR到数组
void CalcATRArray(const double &high[], const double &low[], const double &close[],
                  double &atr_out[], int count, int period=14)
{
   ArrayResize(atr_out, count);
   if(count == 0) return;
   atr_out[0] = high[0] - low[0];
   double alpha = 2.0 / (period + 1.0);
   for(int i = 1; i < count; i++)
   {
      double tr = MathMax(high[i] - low[i],
                  MathMax(MathAbs(high[i] - close[i-1]),
                          MathAbs(low[i] - close[i-1])));
      atr_out[i] = alpha * tr + (1.0 - alpha) * atr_out[i-1];
   }
}

// 是否核心时段 (7-21 UTC)
bool IsCoreHour(int hour)
{
   return (hour >= 7 && hour <= 21);
}

// 是否扩展时段 (22-6 UTC)
bool IsExtHour(int hour)
{
   return (hour >= 22 || hour <= 6);
}

// 是否夜盘 (19-21 UTC)
bool IsNightHour(int hour)
{
   return (hour >= 19 && hour <= 21);
}

// rolling max (往回lookback根)
double RollingMax(const double &arr[], int idx, int lookback)
{
   double mx = -DBL_MAX;
   int start = MathMax(0, idx - lookback + 1);
   for(int i = start; i <= idx; i++)
      if(arr[i] > mx) mx = arr[i];
   return mx;
}

// rolling min
double RollingMin(const double &arr[], int idx, int lookback)
{
   double mn = DBL_MAX;
   int start = MathMax(0, idx - lookback + 1);
   for(int i = start; i <= idx; i++)
      if(arr[i] < mn) mn = arr[i];
   return mn;
}

// rolling mean
double RollingMean(const double &arr[], int idx, int lookback)
{
   int start = MathMax(0, idx - lookback + 1);
   double sum = 0;
   int cnt = 0;
   for(int i = start; i <= idx; i++) { sum += arr[i]; cnt++; }
   return cnt > 0 ? sum / cnt : 0;
}

// body占比
double BodyPct(double open, double close, double high, double low)
{
   double range = MathMax(high - low, 1e-9);
   return MathAbs(close - open) / range;
}

// volume ratio (当前bar vs 30bar均值)
double VolRatio(const double &volume[], int idx)
{
   double avg = RollingMean(volume, MathMax(0, idx-1), 30);
   if(avg < 1.0) avg = 1.0;
   return volume[idx] / avg;
}

// 获取品种spread (从Symbol Info)
double GetSpread()
{
   return SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
}

// 1H趋势方向 (EMA20 vs EMA60, shift(1)防前瞻)
int GetTrend1H(int shift=1)
{
   double ema20 = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   double ema60 = iMA(_Symbol, PERIOD_H1, 60, 0, MODE_EMA, PRICE_CLOSE);
   // 获取shift后的值
   double buf20[], buf60[];
   ArraySetAsSeries(buf20, true);
   ArraySetAsSeries(buf60, true);
   CopyBuffer(ema20, 0, shift, 1, buf20);
   CopyBuffer(ema60, 0, shift, 1, buf60);
   if(ArraySize(buf20) == 0 || ArraySize(buf60) == 0) return 0;
   if(buf20[0] > buf60[0]) return 1;
   if(buf20[0] < buf60[0]) return -1;
   return 0;
}

#endif
