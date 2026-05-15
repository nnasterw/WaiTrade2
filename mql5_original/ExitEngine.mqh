//+------------------------------------------------------------------+
//| ExitEngine.mqh — 出场逻辑 (Trailing + DTP + 时间出场)               |
//+------------------------------------------------------------------+
#ifndef __WAITRADE_EXITENGINE_MQH__
#define __WAITRADE_EXITENGINE_MQH__

#include "Config.mqh"

enum ENUM_EXIT_REASON
{
   EXIT_NONE,
   EXIT_SL,
   EXIT_TRAILING_SL,
   EXIT_DTP,
   EXIT_TIME_TP,
   EXIT_TIMEOUT,
   EXIT_TIME_DECAY
};

struct ExitDecision
{
   bool             should_exit;
   ENUM_EXIT_REASON reason;
   double           new_sl;        // >0 表示只移SL不平仓
};

class CExitEngine
{
public:
   CExitEngine() {}

   // 核心: 每tick调用, 返回出场决策
   ExitDecision Update(double current_price, double entry_price, double initial_sl,
                       double current_sl, double initial_risk,
                       double &max_favorable_r, int elapsed_bars, string direction)
   {
      ExitDecision dec;
      dec.should_exit = false;
      dec.reason = EXIT_NONE;
      dec.new_sl = 0;

      if(initial_risk <= 0) { dec.should_exit = true; dec.reason = EXIT_SL; return dec; }

      // 当前R
      double current_r;
      if(direction == "long")
         current_r = (current_price - entry_price) / initial_risk;
      else
         current_r = (entry_price - current_price) / initial_risk;

      // 更新max_favorable_r
      if(current_r > max_favorable_r)
         max_favorable_r = current_r;

      // 1. SL检查
      if(direction == "long" && current_price <= current_sl)
      {
         double sl_r = (current_sl - entry_price) / initial_risk;
         dec.should_exit = true;
         dec.reason = (sl_r <= 0) ? EXIT_SL : EXIT_TRAILING_SL;
         return dec;
      }
      if(direction == "short" && current_price >= current_sl)
      {
         double sl_r = (entry_price - current_sl) / initial_risk;
         dec.should_exit = true;
         dec.reason = (sl_r <= 0) ? EXIT_SL : EXIT_TRAILING_SL;
         return dec;
      }

      // 2. 动态止盈 (DTP)
      if(InpDTPTriggerR < 900 && max_favorable_r >= InpDTPTriggerR)
      {
         double retrace = max_favorable_r - current_r;
         double retrace_pct = InpDTPRetrace;

         if(InpAdaptiveDTP)
         {
            if(max_favorable_r >= 6.0) retrace_pct = MathMin(retrace_pct, 0.20);
            else if(max_favorable_r >= 4.0) retrace_pct = MathMin(retrace_pct, 0.25);
            else if(max_favorable_r >= 3.0) retrace_pct = MathMin(retrace_pct, 0.30);
         }

         if(retrace >= max_favorable_r * retrace_pct)
         {
            dec.should_exit = true;
            dec.reason = EXIT_DTP;
            return dec;
         }
      }

      // 3. 时间出场
      if(elapsed_bars >= InpTimeExitBars)
      {
         if(current_r >= 0.5)
         {
            dec.should_exit = true;
            dec.reason = EXIT_TIME_TP;
         }
         else
         {
            dec.should_exit = true;
            dec.reason = EXIT_TIMEOUT;
         }
         return dec;
      }

      // 4. 时间衰减
      if(InpTimeDecayTP && InpTimeExitBars > 0)
      {
         double frac = (double)elapsed_bars / (double)InpTimeExitBars;
         if(frac >= 0.75 && current_r >= 0.5)
         {
            dec.should_exit = true;
            dec.reason = EXIT_TIME_DECAY;
            return dec;
         }
         if(frac >= 0.5 && max_favorable_r >= 1.5)
         {
            double decay_retrace = max_favorable_r - current_r;
            if(decay_retrace >= max_favorable_r * 0.25)
            {
               dec.should_exit = true;
               dec.reason = EXIT_TIME_DECAY;
               return dec;
            }
         }
      }

      // 5. Trailing SL 移动 (不平仓)
      double lock_r = CalcTrailingLock(max_favorable_r);
      if(lock_r >= -999) // 有效
      {
         double new_sl_price;
         if(direction == "long")
            new_sl_price = entry_price + lock_r * initial_risk;
         else
            new_sl_price = entry_price - lock_r * initial_risk;

         // 只能收紧
         if(direction == "long" && new_sl_price > current_sl)
         {
            dec.new_sl = new_sl_price;
            return dec;
         }
         if(direction == "short" && new_sl_price < current_sl)
         {
            dec.new_sl = new_sl_price;
            return dec;
         }
      }

      return dec;
   }

private:
   // 统一trailing计算 (从高到低检查levels)
   double CalcTrailingLock(double max_r)
   {
      // Level 3 (可选)
      if(InpTrail3TriggerR > 0 && max_r >= InpTrail3TriggerR)
      {
         if(InpTrail3LockMult > 0)
            return max_r * InpTrail3LockMult;
         return InpTrail3LockR;
      }

      // Level 2
      if(max_r >= InpTrail2TriggerR)
      {
         if(InpTrail2LockMult > 0)
            return max_r * InpTrail2LockMult;
         return InpTrail2LockR;  // Fix: 之前错误返回TriggerR
      }

      // Level 1
      if(max_r >= InpTrail1TriggerR)
         return InpTrail1LockR;

      // 保本
      if(max_r >= InpBreakevenR)
         return InpBreakevenLockR;

      return -9999; // 无操作
   }
};

#endif
