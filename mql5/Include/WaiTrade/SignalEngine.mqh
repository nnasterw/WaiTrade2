#ifndef __WAITRADE_SIGNAL_ENGINE_MQH__
#define __WAITRADE_SIGNAL_ENGINE_MQH__

#include "Types.mqh"
#include "Config.mqh"
#include "Utils.mqh"

int ScanSignals(string symbol, const OBZone &zones[], int zone_count,
                const EAState &state, TradeSignal &signals[], int max_signals)
{
   int count = 0;
   int best_idx = -1;
   double best_strength = 0;

   for(int i = 0; i < zone_count && count < max_signals; i++)
   {
      if(zones[i].expired || zones[i].used)
         continue;

      TradeSignal sig;
      if(CheckEntryConditions(symbol, zones[i], i, state, sig))
      {
         if(sig.pos_mult > best_strength)
         {
            best_strength = sig.pos_mult;
            best_idx = count;
         }
         signals[count] = sig;
         count++;
      }
   }

   if(count > 1 && best_idx > 0)
   {
      TradeSignal tmp = signals[0];
      signals[0] = signals[best_idx];
      signals[best_idx] = tmp;
   }

   return count;
}

bool CheckEntryConditions(string symbol, const OBZone &zone, int zone_idx,
                          const EAState &state, TradeSignal &signal)
{
   if(IsInCooldown(state))
      return false;

   if(CountPositions() >= InpMaxConcurrent)
      return false;

   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double spread = GetSpread(symbol);

   if(zone.direction == OB_BUY)
   {
      if(bid > zone.high)
         return false;
   }
   else
   {
      if(ask < zone.low)
         return false;
   }

   if(InpRequireDoubleTch)
   {
      if(zone.touch_count < 2)
         return false;
      if(zone.last_touch - zone.first_touch > InpDoubleTchWindowMin * 60)
         return false;
   }
   else
   {
      if(zone.touch_count < 1)
         return false;
   }

   double sl = 0;
   if(zone.direction == OB_BUY)
      sl = zone.low - state.atr_value * InpSLBufferATR;
   else
      sl = zone.high + state.atr_value * InpSLBufferATR;

   double entry = (zone.direction == OB_BUY) ? ask : bid;
   double risk_price = MathAbs(entry - sl);

   if(risk_price <= 0)
      return false;

   double offset = MathAbs(entry - zone.mid) / risk_price;
   if(offset > InpMaxEntryOffsetR)
      return false;

   if(spread > 0 && risk_price / spread < InpMinRiskSpreadRatio)
      return false;

   double pos_mult = InpEnablePosMult ? CalcPositionMultiplier(zone) : 1.0;
   double base_lot;
   if(InpFixedLotSize > 0)
      base_lot = InpFixedLotSize;
   else
      base_lot = CalcLotSize(symbol, InpRiskPercent, risk_price);
   double final_lot = base_lot * pos_mult;

   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double tick_value = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);

   if(point > 0 && tick_value > 0 && InpMinAbsRiskUSD > 0)
   {
      double risk_usd = final_lot * (risk_price / point) * tick_value;
      if(risk_usd < InpMinAbsRiskUSD)
         return false;
   }

   double margin_required = 0;
   ENUM_ORDER_TYPE order_type = (zone.direction == OB_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(!OrderCalcMargin(order_type, symbol, final_lot, entry, margin_required))
      return false;

   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(margin_required > free_margin)
   {
      if(free_margin <= 0)
         return false;
      final_lot = final_lot * (free_margin / margin_required) * 0.95;
      double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
      double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
      final_lot = MathFloor(final_lot / lot_step) * lot_step;
      if(final_lot < lot_min)
         return false;
   }

   double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double lot_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   final_lot = MathFloor(final_lot / lot_step) * lot_step;
   if(final_lot < lot_min) final_lot = lot_min;
   if(final_lot > lot_max) final_lot = lot_max;

   double tp = 0.0;
   if(InpDTPTriggerR <= 0 && InpFixedTPR > 0)
      tp = RToPrice(InpFixedTPR, entry, risk_price, zone.direction);

   signal.direction = zone.direction;
   signal.entry = entry;
   signal.sl = sl;
   signal.tp = tp;
   signal.risk_price = risk_price;
   signal.lot = final_lot;
   signal.pos_mult = pos_mult;
   signal.ob_index = zone_idx;
   signal.comment = "WT " + InpVersion + " " + (zone.direction > 0 ? "B" : "S") +
                    " x" + DoubleToString(pos_mult, 1);

   return true;
}

double CalcPositionMultiplier(const OBZone &zone)
{
   double base = zone.strength;
   double fresh_mult = zone.is_fresh ? 1.5 : 1.0;
   double cont_mult = zone.is_continuation ? 1.3 : 1.0;
   double boost_1h = zone.is_1h_aligned ? InpBoostIn1HOB : 1.0;
   double ds = InpDSWeight ? zone.ds_weight : 1.0;

   return base * fresh_mult * cont_mult * boost_1h * ds;
}

bool IsInCooldown(const EAState &state)
{
   if(InpCooldownBars <= 0)
      return false;
   return (state.bar_count - state.last_entry_bar) < InpCooldownBars;
}

#endif
