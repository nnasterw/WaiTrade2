#ifndef __WAITRADE_OB_DETECTOR_MQH__
#define __WAITRADE_OB_DETECTOR_MQH__

#include "Types.mqh"
#include "Config.mqh"
#include "Utils.mqh"

bool IsImpulse(const MqlRates &rates[], int count, int start_idx, int direction, double atr)
{
   if(atr <= 0) return false;
   int look = InpImpulseLookback;
   if(look < 1) look = 3;
   double move = 0.0;

   if(direction == OB_BUY)
   {
      double high_max = rates[start_idx].high;
      for(int i = start_idx + 1; i < start_idx + look && i < count; i++)
         if(rates[i].high > high_max) high_max = rates[i].high;
      move = high_max - rates[start_idx].low;
   }
   else
   {
      double low_min = rates[start_idx].low;
      for(int i = start_idx + 1; i < start_idx + look && i < count; i++)
         if(rates[i].low < low_min) low_min = rates[i].low;
      move = rates[start_idx].high - low_min;
   }

   double threshold = InpImpulseATRMult > 0 ? InpImpulseATRMult : 1.5;
   return (move > atr * threshold);
}

bool IsInNoOBWindow(int hour)
{
   if(InpNoOBStartHour < 0 || InpNoOBEndHour < 0)
      return false;

   int start_hour = InpNoOBStartHour % 24;
   int end_hour = InpNoOBEndHour % 24;

   if(start_hour == end_hour)
      return true;

   if(start_hour < end_hour)
      return (hour >= start_hour && hour < end_hour);

   return (hour >= start_hour || hour < end_hour);
}

bool PassOBBodyPct(const MqlRates &bar)
{
   if(InpMinOBBodyPct <= 0)
      return true;

   double body = MathAbs(bar.open - bar.close);
   double range = bar.high - bar.low;
   if(range <= 0)
      return false;

   return (body / range * 100.0 >= InpMinOBBodyPct);
}

double CalcOBStrength(const MqlRates &rates[], int ob_idx, int impulse_end, double atr, int direction)
{
   if(atr <= 0) return 1.0;

   double impulse_size = 0.0;
   if(direction == OB_BUY)
   {
      double high_max = rates[ob_idx + 1].high;
      for(int i = ob_idx + 1; i <= impulse_end; i++)
         if(rates[i].high > high_max) high_max = rates[i].high;
      impulse_size = high_max - rates[ob_idx].low;
   }
   else
   {
      double low_min = rates[ob_idx + 1].low;
      for(int i = ob_idx + 1; i <= impulse_end; i++)
         if(rates[i].low < low_min) low_min = rates[i].low;
      impulse_size = rates[ob_idx].high - low_min;
   }

   double ratio = impulse_size / atr;
   double score_impulse = MathMin(ratio - 1.0, 2.0);
   if(score_impulse < 0) score_impulse = 0;

   double ob_range = rates[ob_idx].high - rates[ob_idx].low;
   double score_width = 0.0;
   if(ob_range > 0 && ob_range < atr * 0.5)
      score_width = 1.0;
   else if(ob_range <= atr)
      score_width = 0.5;

   double score_fresh = 1.0;

   double score_position = 0.0;
   double body = MathAbs(rates[ob_idx].close - rates[ob_idx].open);
   if(ob_range > 0 && body / ob_range > 0.6)
      score_position = 1.0;
   else if(ob_range > 0 && body / ob_range > 0.4)
      score_position = 0.5;

   double total = 1.0 + score_impulse + score_width + score_fresh + score_position;
   if(total > 5.0) total = 5.0;
   if(total < 1.0) total = 1.0;
   return total;
}

double CalcDSWeight(const MqlRates &rates[], int count, int ob_idx)
{
   int look_back = 10;
   int start = ob_idx - look_back;
   if(start < 0) start = 0;

   double bull_power = 0.0;
   double bear_power = 0.0;

   for(int i = start; i < ob_idx; i++)
   {
      double body = rates[i].close - rates[i].open;
      double range = rates[i].high - rates[i].low;
      if(range <= 0) continue;

      if(body > 0)
         bull_power += body / range * (rates[i].high - rates[i].low);
      else
         bear_power += MathAbs(body) / range * (rates[i].high - rates[i].low);
   }

   double total = bull_power + bear_power;
   if(total <= 0) return 1.0;

   double imbalance = MathAbs(bull_power - bear_power) / total;
   double weight = 0.5 + imbalance * 2.0;
   if(weight > 2.5) weight = 2.5;
   if(weight < 0.5) weight = 0.5;
   return weight;
}

void UpdateOBStatus(OBZone &zones[], int &zone_count, double bid, double ask, const EAState &state)
{
   datetime now = TimeCurrent();

   for(int i = zone_count - 1; i >= 0; i--)
   {
      if(zones[i].expired) continue;

      if(zones[i].used)
      {
         zones[i].expired = true;
         continue;
      }

      int bars_alive = state.bar_count - zones[i].created_bar;
      if(bars_alive > InpBars)
      {
         zones[i].expired = true;
         continue;
      }

      long minutes_alive = (long)(now - zones[i].created) / 60;
      // Gap6: 动态TTL — 高strength OB活更久, 低strength快过期
      int ttl_minutes = InpTimeoutMin;
      if(zones[i].strength >= 2.0) ttl_minutes = (int)(InpTimeoutMin * 1.5);
      else if(zones[i].strength < 1.0) ttl_minutes = (int)(InpTimeoutMin * 0.5);
      if(minutes_alive > ttl_minutes)
      {
         zones[i].expired = true;
         continue;
      }

      bool touched = false;
      if(zones[i].direction == OB_BUY && bid <= zones[i].high)
         touched = true;
      else if(zones[i].direction == OB_SELL && ask >= zones[i].low)
         touched = true;

      if(touched)
      {
         zones[i].touch_count++;
         zones[i].last_touch = now;
         if(zones[i].first_touch == 0)
            zones[i].first_touch = now;
         zones[i].is_fresh = false;
      }
   }
}

void ConsolidateOBs(OBZone &zones[], int &zone_count)
{
   for(int i = 0; i < zone_count - 1; i++)
   {
      if(zones[i].expired) continue;

      for(int j = i + 1; j < zone_count; j++)
      {
         if(zones[j].expired) continue;
         if(zones[i].direction != zones[j].direction) continue;

         bool overlap = (zones[i].low <= zones[j].high && zones[i].high >= zones[j].low);
         if(!overlap) continue;

         zones[i].high = MathMax(zones[i].high, zones[j].high);
         zones[i].low = MathMin(zones[i].low, zones[j].low);
         zones[i].mid = (zones[i].high + zones[i].low) / 2.0;
         if(zones[j].strength > zones[i].strength)
            zones[i].strength = zones[j].strength;
         if(zones[j].ds_weight > zones[i].ds_weight)
            zones[i].ds_weight = zones[j].ds_weight;

         zones[j].expired = true;
      }
   }
}

int Detect1HOBDirection(string symbol)
{
   MqlRates rates_1h[];
   int copied = CopyRates(symbol, PERIOD_H1, 0, 50, rates_1h);
   if(copied < 20) return 0;

   double atr_1h = CalcATR(rates_1h, copied, InpATRPeriod);
   if(atr_1h <= 0) return 0;

   int look = InpImpulseLookback > 0 ? InpImpulseLookback : 3;
   for(int i = copied - (look + 1); i >= 1; i--)
   {
      if(rates_1h[i].close < rates_1h[i].open)
      {
         if(IsImpulse(rates_1h, copied, i + 1, OB_BUY, atr_1h))
            return OB_BUY;
      }

      if(rates_1h[i].close > rates_1h[i].open)
      {
         if(IsImpulse(rates_1h, copied, i + 1, OB_SELL, atr_1h))
            return OB_SELL;
      }
   }
   return 0;
}

void MarkZoneUsed(OBZone &zones[], int index)
{
    if(index >= 0 && index < MAX_OB_ZONES)
    {
        int max_entries = InpMaxEntriesPerOB;
        if(max_entries < 1)
            max_entries = 1;

        zones[index].entry_count++;
        zones[index].last_entry_time = TimeCurrent();
        if(zones[index].entry_count >= max_entries)
            zones[index].used = true;
    }
}

void Update1HAlignment(OBZone &zones[], int zone_count, int h1_direction)
{
    for(int i = 0; i < zone_count; i++)
    {
        if(!zones[i].expired && !zones[i].used)
            zones[i].is_1h_aligned = (zones[i].direction == h1_direction);
    }
}

void CompactZones(OBZone &zones[], int &zone_count)
{
   int write = 0;
   for(int read = 0; read < zone_count; read++)
   {
      if(!zones[read].expired)
      {
         if(write != read)
            zones[write] = zones[read];
         write++;
      }
   }
   zone_count = write;
}

bool DetectContinuation(const MqlRates &rates[], int count, int ob_idx, int direction)
{
   int ma_period = 20;
   if(ob_idx < ma_period) return false;

   double sum = 0;
   for(int i = ob_idx - ma_period; i < ob_idx; i++)
      sum += rates[i].close;
   double ma = sum / ma_period;

   if(direction == OB_BUY)
      return (rates[ob_idx].close > ma);
   else
      return (rates[ob_idx].close < ma);
}

void DetectOrderBlocks(const MqlRates &rates[], int count, OBZone &zones[], int &zone_count, const EAState &state)
{
   CompactZones(zones, zone_count);

   double atr = state.atr_value;
   if(atr <= 0) atr = CalcATR(rates, count, InpATRPeriod);
   if(atr <= 0) return;

   string symbol = Symbol();
   double spread = GetSpread(symbol);
   if(InpSpreadFloor > 0 && spread < InpSpreadFloor)
      spread = InpSpreadFloor;
   double min_ob_range = spread * InpMinOBSpreadMult;

   int scan_start = count - (InpImpulseLookback + 1);
   int scan_end = 1;
   if(InpOBScanDepth > 0 && count > InpOBScanDepth + 4)
      scan_end = count - 4 - InpOBScanDepth;

   for(int i = scan_start; i >= scan_end; i--)
   {
      if(zone_count >= MAX_OB_ZONES) break;

      // Bullish OB: bearish candle followed by up impulse
      if(rates[i].close < rates[i].open)
      {
         if(i + InpImpulseLookback < count && IsImpulse(rates, count, i + 1, OB_BUY, atr))
         {
            double ob_range = MathAbs(rates[i].open - rates[i].close);  // Gap1: 实体大小
            if(ob_range < min_ob_range) continue;

            double impulse_high = rates[i + 1].high;
            for(int k = i + 1; k <= i + InpImpulseLookback && k < count; k++)
               if(rates[k].high > impulse_high) impulse_high = rates[k].high;

            double bounce = (impulse_high - rates[i].high) / ob_range;
            if(bounce < InpBouncePct) continue;

            bool duplicate = false;
            for(int z = 0; z < zone_count; z++)
            {
               if(zones[z].expired) continue;
               if(zones[z].direction == OB_BUY &&
                  MathAbs(zones[z].high - rates[i].open) < atr * 0.1 &&
                  MathAbs(zones[z].low - rates[i].close) < atr * 0.1)
               {
                  duplicate = true;
                  break;
               }
            }
            if(duplicate) continue;

            // Gap2: Displacement确认 — impulse bar close必须突破前3根最高点
            double prior_high = rates[i].high;
            for(int p = MathMax(0, i-3); p < i; p++)
               if(rates[p].high > prior_high) prior_high = rates[p].high;
            if(rates[i+1].close <= prior_high)
               continue;

            // Gap3: K线质量 — 实体占比达标
            if(!PassOBBodyPct(rates[i]))
               continue;

            // Gap4: 高噪音时段过滤
            MqlDateTime dt_bull;
            TimeToStruct(rates[i].time, dt_bull);
            if(IsInNoOBWindow(dt_bull.hour))
               continue;

            OBZone zone = {};
            zone.high = rates[i].open;   // Gap1: bearish candle的open是实体高点
            zone.low = rates[i].close;   // Gap1: bearish candle的close是实体低点
            zone.mid = (zone.high + zone.low) / 2.0;
            zone.direction = OB_BUY;
            zone.created = rates[i].time;
            zone.created_bar = state.bar_count - (count - 1 - i);
            zone.touch_count = 0;
            zone.first_touch = 0;
            zone.last_touch = 0;
            zone.strength = CalcOBStrength(rates, i, MathMin(i + InpImpulseLookback, count - 1), atr, OB_BUY);
            zone.is_fresh = true;
            zone.is_continuation = DetectContinuation(rates, count, i, zone.direction);
            zone.is_1h_aligned = false;
            zone.ds_weight = InpDSWeight ? CalcDSWeight(rates, count, i) : 1.0;
            zone.entry_count = 0;
            zone.last_entry_time = 0;
            zone.used = false;
            zone.expired = false;

            zones[zone_count] = zone;
            zone_count++;
         }
      }

      // Bearish OB: bullish candle followed by down impulse
      if(rates[i].close > rates[i].open)
      {
         if(i + InpImpulseLookback < count && IsImpulse(rates, count, i + 1, OB_SELL, atr))
         {
            double ob_range = MathAbs(rates[i].open - rates[i].close);  // Gap1: 实体大小
            if(ob_range < min_ob_range) continue;

            double impulse_low = rates[i + 1].low;
            for(int k = i + 1; k <= i + InpImpulseLookback && k < count; k++)
               if(rates[k].low < impulse_low) impulse_low = rates[k].low;

            double bounce = (rates[i].low - impulse_low) / ob_range;
            if(bounce < InpBouncePct) continue;

            bool duplicate = false;
            for(int z = 0; z < zone_count; z++)
            {
               if(zones[z].expired) continue;
               if(zones[z].direction == OB_SELL &&
                  MathAbs(zones[z].high - rates[i].close) < atr * 0.1 &&
                  MathAbs(zones[z].low - rates[i].open) < atr * 0.1)
               {
                  duplicate = true;
                  break;
               }
            }
            if(duplicate) continue;

            // Gap2: Displacement确认 — impulse bar close必须突破前3根最低点
            double prior_low = rates[i].low;
            for(int p = MathMax(0, i-3); p < i; p++)
               if(rates[p].low < prior_low) prior_low = rates[p].low;
            if(rates[i+1].close >= prior_low)
               continue;

            // Gap3: K线质量 — 实体占比达标
            if(!PassOBBodyPct(rates[i]))
               continue;

            // Gap4: 高噪音时段过滤
            MqlDateTime dt_bear;
            TimeToStruct(rates[i].time, dt_bear);
            if(IsInNoOBWindow(dt_bear.hour))
               continue;

            OBZone zone = {};
            zone.high = rates[i].close;  // Gap1: bullish candle的close是实体高点
            zone.low = rates[i].open;    // Gap1: bullish candle的open是实体低点
            zone.mid = (zone.high + zone.low) / 2.0;
            zone.direction = OB_SELL;
            zone.created = rates[i].time;
            zone.created_bar = state.bar_count - (count - 1 - i);
            zone.touch_count = 0;
            zone.first_touch = 0;
            zone.last_touch = 0;
            zone.strength = CalcOBStrength(rates, i, MathMin(i + InpImpulseLookback, count - 1), atr, OB_SELL);
            zone.is_fresh = true;
            zone.is_continuation = DetectContinuation(rates, count, i, zone.direction);
            zone.is_1h_aligned = false;
            zone.ds_weight = InpDSWeight ? CalcDSWeight(rates, count, i) : 1.0;
            zone.entry_count = 0;
            zone.last_entry_time = 0;
            zone.used = false;
            zone.expired = false;

            zones[zone_count] = zone;
            zone_count++;
         }
      }
   }

}

#endif
