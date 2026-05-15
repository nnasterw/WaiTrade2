#ifndef __WAITRADE_UTILS_MQH__
#define __WAITRADE_UTILS_MQH__

#include "Config.mqh"
#include "Types.mqh"

double CalcATR(const MqlRates &rates[], int count, int period=14)
{
   if(count < period + 1) return 0.0;
   double sum = 0.0;
   for(int i = count - period; i < count; i++)
   {
      double tr = rates[i].high - rates[i].low;
      double tr2 = MathAbs(rates[i].high - rates[i-1].close);
      double tr3 = MathAbs(rates[i].low - rates[i-1].close);
      if(tr2 > tr) tr = tr2;
      if(tr3 > tr) tr = tr3;
      sum += tr;
   }
   return sum / period;
}

double CalcLotSize(string symbol, double risk_pct, double risk_price)
{
   if(risk_price <= 0) return SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double tick_value = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   double min_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);

   if(tick_value <= 0 || point <= 0) return min_lot;

   double risk_money = balance * risk_pct / 100.0;
   double risk_points = risk_price / point;
   double lot = risk_money / (risk_points * tick_value);

   lot = MathFloor(lot / lot_step) * lot_step;
   if(lot < min_lot) lot = min_lot;
   if(lot > max_lot) lot = max_lot;
   return NormalizeDouble(lot, 2);
}

double GetSpread(string symbol)
{
   return (double)SymbolInfoInteger(symbol, SYMBOL_SPREAD) * SymbolInfoDouble(symbol, SYMBOL_POINT);
}

ENUM_TIMEFRAMES GetWorkTF()
{
   switch(InpBarTF)
   {
      case 1:   return PERIOD_M1;
      case 5:   return PERIOD_M5;
      case 15:  return PERIOD_M15;
      case 30:  return PERIOD_M30;
      case 60:  return PERIOD_H1;
      case 240: return PERIOD_H4;
      default:  return PERIOD_M1;
   }
}

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

double PriceToR(double price, double entry, double risk_price, int direction)
{
   if(risk_price <= 0) return 0.0;
   return (price - entry) * direction / risk_price;
}

double RToPrice(double r_value, double entry, double risk_price, int direction)
{
   return entry + r_value * risk_price * direction;
}

bool ModifySL(ulong ticket, double new_sl)
{
   if(!PositionSelectByTicket(ticket)) return false;

   double tp = PositionGetDouble(POSITION_TP);
   string symbol = PositionGetString(POSITION_SYMBOL);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   new_sl = NormalizeDouble(new_sl, digits);

   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   request.action = TRADE_ACTION_SLTP;
   request.position = ticket;
   request.symbol = symbol;
   request.sl = new_sl;
   request.tp = tp;

   if(!OrderSend(request, result))
      return false;
   return (result.retcode == TRADE_RETCODE_DONE || result.retcode == TRADE_RETCODE_PLACED);
}

bool ClosePosition(ulong ticket)
{
   if(!PositionSelectByTicket(ticket)) return false;

   string symbol = PositionGetString(POSITION_SYMBOL);
   double volume = PositionGetDouble(POSITION_VOLUME);
   ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   request.action = TRADE_ACTION_DEAL;
   request.position = ticket;
   request.symbol = symbol;
   request.volume = volume;
   request.type = (pos_type == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.price = (pos_type == POSITION_TYPE_BUY) ?
                   SymbolInfoDouble(symbol, SYMBOL_BID) :
                   SymbolInfoDouble(symbol, SYMBOL_ASK);
   request.deviation = 20;

   if(!OrderSend(request, result))
      return false;
   return (result.retcode == TRADE_RETCODE_DONE);
}

int CountPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         count++;
   }
   return count;
}

#endif
