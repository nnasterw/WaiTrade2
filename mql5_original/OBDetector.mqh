//+------------------------------------------------------------------+
//| OBDetector.mqh — OB识别模块 (V8.4逻辑)                             |
//| 只做位移K线检测+OB创建, 不做bar级touch检查                           |
//| touch→bounce确认由EntryEngine在tick级完成                           |
//+------------------------------------------------------------------+
#ifndef __WAITRADE_OBDETECTOR_MQH__
#define __WAITRADE_OBDETECTOR_MQH__

#include "Config.mqh"
#include "Utils.mqh"

#define MAX_ACTIVE_OBS 50
#define MAX_SIGNALS    20

struct OBBlock
{
   string direction;
   int    created_bar;
   double top;
   double bottom;
   double sl;
   double ds;
   double ob_size;
   int    ttl;
   bool   sent;       // 已发送给EntryEngine
   bool   next_same;
};

struct OBSignal
{
   int    bar;
   string direction;
   double entry;      // OB mid入场价
   double sl;
   double ob_top;
   double ob_bottom;
   double pos_mult;
   double ds;
   string tier;
   string entry_type;
   datetime signal_time;
};

class COBDetector
{
private:
   OBBlock  m_obs[MAX_ACTIVE_OBS];
   int      m_ob_count;
   OBSignal m_signals[MAX_SIGNALS];
   int      m_signal_count;

   void Classify(double vol_ratio, double body_pct, double risk_atr,
                 double disp_strength, bool is_ext, bool aligned, bool counter,
                 string &tier, double &mult)
   {
      tier = ""; mult = 0;
      if(is_ext)
      {
         if(vol_ratio >= 1.5 && body_pct >= 0.6 && risk_atr < 0.8 && aligned)
            { tier = "ext_L1"; mult = 3.0; return; }
         if(vol_ratio >= 1.2 && body_pct >= 0.5 && risk_atr < 1.0 && aligned)
            { tier = "ext_L2"; mult = 2.0; return; }
         return;
      }
      if(vol_ratio >= 2.0 && body_pct >= 0.7 && risk_atr < 0.6 && disp_strength >= 1.5 && aligned)
         { tier = "super_high"; mult = 5.0; return; }
      if(vol_ratio >= 1.5 && body_pct >= 0.6 && risk_atr < 0.8 && aligned)
         { tier = "high"; mult = 3.0; return; }
      if(vol_ratio >= 1.3 && body_pct >= 0.55 && risk_atr < 0.9 && aligned)
         { tier = "high_ext"; mult = 2.5; return; }
      if(vol_ratio >= 1.2 && body_pct >= 0.5 && aligned)
         { tier = "medium"; mult = 2.0; return; }
      if(vol_ratio >= 1.5 && body_pct >= 0.7 && counter)
         { tier = "medium_B"; mult = 2.0; return; }
      tier = "standard"; mult = 1.0;
   }

public:
   COBDetector() { m_ob_count = 0; m_signal_count = 0; }

   int GetSignalCount() { return m_signal_count; }
   OBSignal GetSignal(int idx) { return m_signals[idx]; }

   void Detect(const MqlRates &rates[], int count, double spread, int trend_1h, int abs_bar_count)
   {
      m_signal_count = 0;
      if(count < 61) return;

      double atr[];
      double high_arr[], low_arr[], close_arr[], open_arr[], vol_arr[];
      ArrayResize(high_arr, count);
      ArrayResize(low_arr, count);
      ArrayResize(close_arr, count);
      ArrayResize(open_arr, count);
      ArrayResize(vol_arr, count);

      for(int i = 0; i < count; i++)
      {
         high_arr[i]  = rates[i].high;
         low_arr[i]   = rates[i].low;
         close_arr[i] = rates[i].close;
         open_arr[i]  = rates[i].open;
         vol_arr[i]   = (double)rates[i].tick_volume;
      }
      CalcATRArray(high_arr, low_arr, close_arr, atr, count, 14);

      int bar = count - 2; // 上一根已完成bar
      if(bar < 60) return;

      double cur_atr = atr[bar];
      if(cur_atr <= 0) return;

      MqlDateTime dt;
      TimeToStruct(rates[bar].time, dt);
      int hour = dt.hour;
      bool is_core = IsCoreHour(hour);
      bool is_ext  = IsExtHour(hour);
      bool is_night = IsNightHour(hour);

      double bp = BodyPct(open_arr[bar], close_arr[bar], high_arr[bar], low_arr[bar]);
      double vr = VolRatio(vol_arr, bar);

      // === OB创建 ===
      bool can_build = false;
      if(is_core && bp > 0.55 && vr > 0.9) can_build = true;
      else if(is_ext && bp > 0.50 && vr > 0.8) can_build = true;

      // 诊断: 每1000 bars输出OB检测条件
      static int diag_count = 0;
      diag_count++;
      if(diag_count % 1000 == 1)
      {
         double prior_h = RollingMax(high_arr, bar-1, 3);
         double prior_l = RollingMin(low_arr, bar-1, 3);
         PrintFormat("[OB_DIAG] bar=%d h=%d can_build=%d bp=%.3f vr=%.3f atr=%.5f close=%.2f open=%.2f prior_h=%.2f prior_l=%.2f close>prior_h+0.1atr=%d bullish_candle=%d prev_bearish=%d obs=%d",
            bar, hour, can_build, bp, vr, cur_atr,
            close_arr[bar], open_arr[bar], prior_h, prior_l,
            close_arr[bar] > prior_h + 0.10 * cur_atr,
            close_arr[bar] > open_arr[bar],
            bar >= 1 ? close_arr[bar-1] < open_arr[bar-1] : 0,
            m_ob_count);
      }

      if(can_build)
      {
         // shift(1).rolling(3): max(high[bar-1], high[bar-2], high[bar-3])
         double prior_high = RollingMax(high_arr, bar-1, 3);
         double prior_low  = RollingMin(low_arr, bar-1, 3);

         // Bullish displacement
         if(close_arr[bar] > prior_high + 0.10 * cur_atr &&
            close_arr[bar] > open_arr[bar] &&
            bar >= 1 && close_arr[bar-1] < open_arr[bar-1])
         {
            if(m_ob_count < MAX_ACTIVE_OBS)
            {
               int ttl = (bp > 0.80 && vr > 1.5) ? 15 : (bp < 0.70 ? 8 : 12);
               double ob_top = open_arr[bar-1];
               double ob_bot = close_arr[bar-1];
               double sl_price = ob_bot - InpSLBufferATR * cur_atr;
               double ob_size = (ob_top - ob_bot) / cur_atr;
               bool next_same = (bar+1 < count) ? (close_arr[bar+1] > open_arr[bar+1]) : false;

               m_obs[m_ob_count].direction = "long";
               m_obs[m_ob_count].created_bar = abs_bar_count;
               m_obs[m_ob_count].top = ob_top;
               m_obs[m_ob_count].bottom = ob_bot;
               m_obs[m_ob_count].sl = sl_price;
               m_obs[m_ob_count].ds = bp * vr;
               m_obs[m_ob_count].ob_size = ob_size;
               m_obs[m_ob_count].ttl = ttl;
               m_obs[m_ob_count].sent = false;
               m_obs[m_ob_count].next_same = next_same;
               m_ob_count++;
            }
         }
         // Bearish displacement
         if(close_arr[bar] < prior_low - 0.10 * cur_atr &&
            close_arr[bar] < open_arr[bar] &&
            bar >= 1 && close_arr[bar-1] > open_arr[bar-1])
         {
            if(m_ob_count < MAX_ACTIVE_OBS)
            {
               int ttl = (bp > 0.80 && vr > 1.5) ? 15 : (bp < 0.70 ? 8 : 12);
               double ob_top = close_arr[bar-1];
               double ob_bot = open_arr[bar-1];
               double sl_price = ob_top + InpSLBufferATR * cur_atr + spread;
               double ob_size = (ob_top - ob_bot) / cur_atr;
               bool next_same = (bar+1 < count) ? (close_arr[bar+1] < open_arr[bar+1]) : false;

               m_obs[m_ob_count].direction = "short";
               m_obs[m_ob_count].created_bar = abs_bar_count;
               m_obs[m_ob_count].top = ob_top;
               m_obs[m_ob_count].bottom = ob_bot;
               m_obs[m_ob_count].sl = sl_price;
               m_obs[m_ob_count].ds = bp * vr;
               m_obs[m_ob_count].ob_size = ob_size;
               m_obs[m_ob_count].ttl = ttl;
               m_obs[m_ob_count].sent = false;
               m_obs[m_ob_count].next_same = next_same;
               m_ob_count++;
            }
         }
      }

      // === 清理过期OB ===
      for(int i = m_ob_count - 1; i >= 0; i--)
      {
         if(abs_bar_count - m_obs[i].created_bar > m_obs[i].ttl)
         {
            for(int j = i; j < m_ob_count - 1; j++)
               m_obs[j] = m_obs[j+1];
            m_ob_count--;
         }
      }

      // === 输出新OB为信号 (未发送过的) ===
      // 不做bar级touch检查! EntryEngine在tick级做touch→bounce
      for(int i = 0; i < m_ob_count && m_signal_count < MAX_SIGNALS; i++)
      {
         if(m_obs[i].sent) continue;

         string d = m_obs[i].direction;
         int age = abs_bar_count - m_obs[i].created_bar;

         // entry = OB中点 (和Python generate_ob_signals_v84一致)
         double ob_mid = (m_obs[i].top + m_obs[i].bottom) / 2.0;
         double entry_mid = ob_mid + ((d == "long") ? spread : 0);
         double risk_mid = (d == "long") ? entry_mid - m_obs[i].sl : m_obs[i].sl - entry_mid;
         if(risk_mid <= spread * 1.5 || risk_mid >= cur_atr * 3.0)
            { m_obs[i].sent = true; continue; }

         // OB大小过滤
         double ob_height = m_obs[i].top - m_obs[i].bottom;
         if(ob_height < spread * InpMinOBSpreadMult)
            { m_obs[i].sent = true; continue; }
         if(InpMinRiskSpreadRatio > 0 && spread > 0)
            if(risk_mid / spread < InpMinRiskSpreadRatio)
               { m_obs[i].sent = true; continue; }

         // 趋势过滤
         bool aligned = (d == "long" && trend_1h >= 0) || (d == "short" && trend_1h <= 0);
         bool counter = (d == "long" && trend_1h < 0) || (d == "short" && trend_1h > 0);
         double risk_atr = risk_mid / cur_atr;
         if(counter && risk_atr >= 1.5) { m_obs[i].sent = true; continue; }

         // 夜盘过滤
         if(is_night)
         {
            if(vr < 1.3 || bp < 0.50 || risk_atr >= 1.0)
               { m_obs[i].sent = true; continue; }
         }

         // 分类
         string tier; double base_mult;
         Classify(vr, bp, risk_atr, m_obs[i].ds, is_ext, aligned, counter, tier, base_mult);
         if(tier == "") { m_obs[i].sent = true; continue; }

         // Boosts
         double fresh_mult = (age <= 3) ? 1.5 : 1.0;
         double cont_mult  = m_obs[i].next_same ? 1.3 : 1.0;
         double combined_mult = base_mult * fresh_mult * cont_mult;

         m_obs[i].sent = true;

         // 输出信号: entry=OB mid, EntryEngine负责tick级touch+bounce
         AddSignal(bar, d, entry_mid, m_obs[i].sl,
                   m_obs[i].top, m_obs[i].bottom, combined_mult,
                   m_obs[i].ds, tier, "ob_mid", rates[bar].time);
      }
   }

private:
   void AddSignal(int bar, string dir, double entry, double sl,
                  double ob_top, double ob_bottom, double pos_mult,
                  double ds, string tier, string entry_type, datetime time)
   {
      if(m_signal_count >= MAX_SIGNALS) return;
      m_signals[m_signal_count].bar = bar;
      m_signals[m_signal_count].direction = dir;
      m_signals[m_signal_count].entry = entry;
      m_signals[m_signal_count].sl = sl;
      m_signals[m_signal_count].ob_top = ob_top;
      m_signals[m_signal_count].ob_bottom = ob_bottom;
      m_signals[m_signal_count].pos_mult = pos_mult;
      m_signals[m_signal_count].ds = ds;
      m_signals[m_signal_count].tier = tier;
      m_signals[m_signal_count].entry_type = entry_type;
      m_signals[m_signal_count].signal_time = time;
      m_signal_count++;
   }
};

#endif
