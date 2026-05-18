#ifndef __WAITRADE_BAR_TRACKER_MQH__
#define __WAITRADE_BAR_TRACKER_MQH__

bool IsNewBar(string symbol, ENUM_TIMEFRAMES tf)
{
   static datetime last_time_m1  = 0;
   static datetime last_time_m5  = 0;
   static datetime last_time_m15 = 0;
   static datetime last_time_h1  = 0;

   datetime cur_time = iTime(symbol, tf, 0);
   bool is_new = false;

   if(tf == PERIOD_M1)
   { if(cur_time != last_time_m1) { last_time_m1 = cur_time; is_new = true; } }
   else if(tf == PERIOD_M5)
   { if(cur_time != last_time_m5) { last_time_m5 = cur_time; is_new = true; } }
   else if(tf == PERIOD_M15)
   { if(cur_time != last_time_m15) { last_time_m15 = cur_time; is_new = true; } }
   else if(tf == PERIOD_H1)
   { if(cur_time != last_time_h1) { last_time_h1 = cur_time; is_new = true; } }
   else
   { if(cur_time != last_time_m1) { last_time_m1 = cur_time; is_new = true; } }

   return is_new;
}

#endif
