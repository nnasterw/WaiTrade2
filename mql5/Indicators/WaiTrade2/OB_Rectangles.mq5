#property copyright "WaiTrade2"
#property version   "1.00"
#property indicator_chart_window
#property indicator_plots 0

// ── OB区域虚线框绘制指标 ──────────────────────────────────────────
// 独立指标: 在图表上绘制虚线矩形框选OB区域, 24小时后自动删除
// 不影响EA编译, 可与任何策略版本配合使用

#define OB_RECT_PREFIX "OBR_"

input bool   InpDrawOBRectangles   = true;     // 启用OB虚线框绘制
input int    InpOBRectBarWidth     = 5;        // OB矩形宽度(bar数)
input int    InpOBRectMaxAgeHours  = 24;       // 最大保留时间(小时)
input color  InpBuyOBColor         = clrDodgerBlue;  // 买入OB颜色
input color  InpSellOBColor        = clrTomato;      // 卖出OB颜色
input int    InpOBRectLineWidth    = 2;        // 线宽
input double InpMinOBHeightPips    = 5.0;      // 最小OB高度(pips, 过滤微小区间)

// 全局OB检测数据结构
#define MAX_OBS 50
struct SimpleOB {
   double high, low;
   int direction; // 1=buy, -1=sell
   datetime bar_time;
   bool drawn;
};
SimpleOB g_obs[MAX_OBS];
int g_ob_count = 0;

// 简单摆动点检测
bool IsSwingHigh(const double &high[], int idx, int strength, int total)
{
   if(idx - strength < 0 || idx + strength >= total) return false;
   for(int j = 1; j <= strength; j++)
   {
      if(high[idx - j] >= high[idx]) return false;
      if(high[idx + j] >= high[idx]) return false;
   }
   return true;
}

bool IsSwingLow(const double &low[], int idx, int strength, int total)
{
   if(idx - strength < 0 || idx + strength >= total) return false;
   for(int j = 1; j <= strength; j++)
   {
      if(low[idx - j] <= low[idx]) return false;
      if(low[idx + j] <= low[idx]) return false;
   }
   return true;
}

// 绘制单个OB矩形
void DrawOBRect(const SimpleOB &ob, int idx)
{
   string name = OB_RECT_PREFIX + IntegerToString(idx) + "_" +
                 IntegerToString((int)ob.bar_time);

   if(ObjectFind(0, name) >= 0) return;

   datetime t1 = ob.bar_time;
   datetime t2 = t1 + PeriodSeconds(_Period) * InpOBRectBarWidth;

   color clr = (ob.direction > 0) ? InpBuyOBColor : InpSellOBColor;

   ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, ob.high, t2, ob.low);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, InpOBRectLineWidth);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_FILL, true);
}

// 清理超时矩形
void CleanOldRects()
{
   static datetime s_last_clean = 0;
   if(TimeCurrent() - s_last_clean < 60) return;
   s_last_clean = TimeCurrent();

   datetime cutoff = TimeCurrent() - InpOBRectMaxAgeHours * 3600;

   for(int i = ObjectsTotal(0) - 1; i >= 0; i--)
   {
      string name = ObjectName(0, i);
      if(StringFind(name, OB_RECT_PREFIX) != 0) continue;

      string parts[];
      int cnt = StringSplit(name, '_', parts);
      if(cnt >= 3)
      {
         datetime created = (datetime)StringToInteger(parts[2]);
         if(created > 0 && created < cutoff)
            ObjectDelete(0, name);
      }
   }
}

// 检测新OB
void DetectOBs()
{
   static datetime s_last_bar = 0;
   if(Time[0] == s_last_bar) return;
   s_last_bar = Time[0];

   int bars = Bars(_Symbol, _Period);
   if(bars < 20) return;

   double highs[], lows[], closes[];
   ArraySetAsSeries(highs, true);
   ArraySetAsSeries(lows, true);
   ArraySetAsSeries(closes, true);
   CopyHigh(_Symbol, _Period, 0, bars, highs);
   CopyLow(_Symbol, _Period, 0, bars, lows);
   CopyClose(_Symbol, _Period, 0, bars, closes);

   int strength = 2; // 摆动点强度
   int lookback = 50;
   if(bars < lookback) lookback = bars;

   // 查找最近的摆动高低点作为OB
   int last_swing_high = -1, last_swing_low = -1;
   double last_sh_price = 0, last_sl_price = 0;

   for(int i = strength + 1; i < lookback - strength; i++)
   {
      if(IsSwingHigh(highs, i, strength, lookback))
      {
         last_swing_high = i;
         last_sh_price = highs[i];
      }
      if(IsSwingLow(lows, i, strength, lookback))
      {
         last_swing_low = i;
         last_sl_price = lows[i];
      }
   }

   // 生成简单OB: 最近摆动高低点之间的区间
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double min_height = InpMinOBHeightPips * point * 10;

   // 用最近几根bar的区间作为OB
   for(int i = 3; i < MathMin(48, lookback - 3); i += 2)
   {
      double ob_high = highs[i];
      double ob_low = lows[i];
      double range = ob_high - ob_low;

      if(range < min_height) continue;

      // 判断方向: 实体方向
      int dir = (closes[i] > closes[i+1]) ? 1 : -1;

      // 避免重复
      bool exists = false;
      for(int j = 0; j < g_ob_count; j++)
      {
         if(MathAbs(g_obs[j].high - ob_high) < point && MathAbs(g_obs[j].low - ob_low) < point)
         { exists = true; break; }
      }
      if(exists) continue;

      if(g_ob_count < MAX_OBS)
      {
         g_obs[g_ob_count].high = ob_high;
         g_obs[g_ob_count].low = ob_low;
         g_obs[g_ob_count].direction = dir;
         g_obs[g_ob_count].bar_time = Time[i];
         g_obs[g_ob_count].drawn = false;
         g_ob_count++;
      }
   }

   // 绘制所有未绘制的OB
   for(int j = 0; j < g_ob_count; j++)
   {
      if(!g_obs[j].drawn)
      {
         DrawOBRect(g_obs[j], j);
         g_obs[j].drawn = true;
      }
   }
}

int OnInit()
{
   if(!InpDrawOBRectangles)
   {
      Print("OB_Rectangles: 已禁用 (InpDrawOBRectangles=false)");
      return INIT_SUCCEEDED;
   }
   Print("OB_Rectangles: 已加载 | OB最大保留", InpOBRectMaxAgeHours, "h | 线宽", InpOBRectLineWidth);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   ObjectsDeleteAll(0, OB_RECT_PREFIX);
}

int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[], const double &low[],
                const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
{
   if(!InpDrawOBRectangles) return rates_total;

   CleanOldRects();
   DetectOBs();

   return rates_total;
}
