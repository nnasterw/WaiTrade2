#ifndef __WAITRADE_SIGNAL_ENGINE_MQH__
#define __WAITRADE_SIGNAL_ENGINE_MQH__

#include "Types.mqh"
#include "Config.mqh"
#include "Utils.mqh"
#include "MarketState.mqh"
#include "ScoreEngine.mqh"
#include "DecayDetector.mqh"

double CalcOBHeightTP(const OBZone &zone, double entry)
{
   if(InpOBHeightTPMult <= 0 || zone.is_range_breakout) return 0.0;
   double ob_h = zone.high - zone.low;
   if(ob_h <= 0) return 0.0;
   return entry + zone.direction * ob_h * InpOBHeightTPMult;
}

double CalcLiquiditySweepTP(const OBZone &zone, double entry)
{
   if(!zone.is_liquidity_sweep || InpSweepTPMult <= 0 || zone.range_height <= 0)
      return 0.0;
   if(zone.direction == OB_BUY)
      return zone.high + zone.range_height * InpSweepTPMult;
   return zone.low - zone.range_height * InpSweepTPMult;
}

bool IsZoneTouched(const OBZone &zone, double bid, double ask)
{
   if(zone.is_range_breakout)
   {
      if(zone.direction == OB_BUY)
         return (bid >= zone.high);
      return (ask <= zone.low);
   }

   if(zone.direction == OB_BUY)
      return (bid <= zone.high);
   else
      return (ask >= zone.low);
}

bool PassDoubleTouchFilter(const OBZone &zone)
{
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
   return true;
}

bool PassOffsetGuard(double entry_price, double risk_price, int direction, double zone_mid, double max_offset_r)
{
   double offset = MathAbs(entry_price - zone_mid) / risk_price;
   return (offset <= max_offset_r);
}

bool PassSpreadRatio(double risk_distance, double spread)
{
   if(spread > 0 && risk_distance / spread < InpMinRiskSpreadRatio)
      return false;
   return true;
}

bool PassMinRisk(double final_lot, double risk_price, string symbol)
{
   if(InpMinAbsRiskUSD <= 0)
      return true;

   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double tick_value = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);

   if(point <= 0 || tick_value <= 0)
      return true;

   double risk_usd = final_lot * (risk_price / point) * tick_value;
   return (risk_usd >= InpMinAbsRiskUSD);
}

bool IsHourBlocked(string csv, int hour)
{
   if(StringLen(csv) == 0)
      return false;

   string parts[];
   ushort sep = StringGetCharacter(",", 0);
   int count = StringSplit(csv, sep, parts);
   for(int i = 0; i < count; i++)
   {
      string token = parts[i];
      StringTrimLeft(token);
      StringTrimRight(token);
      if(StringLen(token) == 0)
         continue;
      int blocked_hour = (int)StringToInteger(token);
      if(blocked_hour == hour)
         return true;
   }

   return false;
}

bool PassNoEntryHours(datetime now)
{
   MqlDateTime dt;
   TimeToStruct(now, dt);

   return !IsHourBlocked(InpNoEntryHours, dt.hour);
}

bool PassDirectionEntryHours(int direction, datetime now)
{
   MqlDateTime dt;
   TimeToStruct(now, dt);

   if(IsHourBlocked(InpNoEntryHours, dt.hour))
      return false;
   if(direction == OB_BUY && IsHourBlocked(InpNoBuyHours, dt.hour))
      return false;
   if(direction == OB_SELL && IsHourBlocked(InpNoSellHours, dt.hour))
      return false;

   return true;
}

bool PassEntryMomentumFilter(int direction)
{
   if(!InpEnableEntryMomentumFilter)
      return true;

   int tf_min = (InpEntryMomentumTF > 0) ? InpEntryMomentumTF : InpBarTF;
   ENUM_TIMEFRAMES tf = MinutesToTF(tf_min);
   int need = MathMax(MathMax(InpStrongMomentumBars, InpDecayBars) + 5, 8);

   MqlRates rates[];
   int count = CopyRates(_Symbol, tf, 0, need, rates);
   if(count < need)
      return true;

   bool counter_strong = CheckStrongMomentum(_Symbol, -direction, rates, count);
   bool counter_weak = CheckMomentumWeakness(_Symbol, -direction, rates, count);

   if(InpEntryBlockCounterStrong && counter_strong && !counter_weak)
      return false;
   if(InpEntryRequireCounterWeak && !counter_weak)
      return false;

   return true;
}

void ApplyHTFTarget(string symbol, double entry, double risk_price, TradeSignal &signal)
{
   if(!InpEnableHTFTarget)
      return;

   double htf_tp = 0;
   if(!CalcHTFTargetPrice(symbol, signal.direction, entry, risk_price, htf_tp))
      return;

   signal.tp = htf_tp;
   signal.htf_target = true;
   signal.htf_partial_r = InpHTFPartialR;
   signal.htf_partial_pct = InpHTFPartialPct;
}

void PrintEntryDebug(const string stage, const OBZone &zone, const EAState &state,
                     const TradeSignal &signal, double entry, double risk_price,
                     double spread, double pos_mult, int score)
{
   if(!InpEnableEntryDebug)
      return;

   int hour = 0;
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   hour = dt.hour;

   double risk_atr = (state.atr_value > 0) ? risk_price / state.atr_value : 0.0;
   double spread_risk = (risk_price > 0) ? spread / risk_price : 0.0;
   int age = state.bar_count - zone.created_bar;

   Print("ENTRY_DIAG stage=", stage,
         " ticket=0",
         " dir=", signal.direction,
         " hour=", hour,
         " ob_age=", age,
         " touch=", zone.touch_count,
         " strength=", DoubleToString(zone.strength, 2),
         " ds=", DoubleToString(zone.ds_weight, 2),
         " fresh=", zone.is_fresh ? 1 : 0,
         " cont=", zone.is_continuation ? 1 : 0,
         " h1=", zone.is_1h_aligned ? 1 : 0,
         " deep=", signal.deep_entry ? 1 : 0,
         " htf=", signal.htf_target ? 1 : 0,
         " bounce_sec=", signal.bounce_seconds,
         " bounce_ob=", DoubleToString(signal.bounce_ob_pct, 3),
         " confirm_pos=", DoubleToString(signal.confirm_ob_pos, 3),
         " touch=", DoubleToString(signal.touch_price, _Digits),
         " confirm=", DoubleToString(signal.confirm_price, _Digits),
         " risk_atr=", DoubleToString(risk_atr, 2),
         " spread_risk=", DoubleToString(spread_risk, 3),
         " pos_mult=", DoubleToString(pos_mult, 2),
         " score=", score,
         " entry=", DoubleToString(entry, _Digits),
         " sl=", DoubleToString(signal.sl, _Digits));
}

double ApplyPositionMultiplierCap(double pos_mult)
{
   if(InpMaxPosMult > 0 && pos_mult > InpMaxPosMult)
      return InpMaxPosMult;
   return pos_mult;
}

double ApplyLotCap(double lot)
{
   if(InpMaxLotSize > 0 && lot > InpMaxLotSize)
      return InpMaxLotSize;
   return lot;
}

double ApplySignalTypeLotCap(const OBZone &zone, double lot)
{
   if(zone.is_liquidity_sweep && InpSweepMaxLotSize > 0 && lot > InpSweepMaxLotSize)
      return InpSweepMaxLotSize;
   if(zone.is_range_breakout && InpRangeBreakoutMaxLotSize > 0 && lot > InpRangeBreakoutMaxLotSize)
      return InpRangeBreakoutMaxLotSize;
   return lot;
}

double ApplyBalanceLotCap(double lot)
{
   if(InpLowBalanceThreshold <= 0 || InpLowBalanceMaxLotSize <= 0)
      return lot;
   if(AccountInfoDouble(ACCOUNT_BALANCE) < InpLowBalanceThreshold && lot > InpLowBalanceMaxLotSize)
      return InpLowBalanceMaxLotSize;
   return lot;
}

double GetDirectionMinStrength(int direction)
{
   if(direction == OB_BUY && InpBuyMinStrength > 0)
      return InpBuyMinStrength;
   if(direction == OB_SELL && InpSellMinStrength > 0)
      return InpSellMinStrength;
   return InpMinOBStrength;
}

double ApplyDirectionPosMult(int direction, double pos_mult)
{
   if(direction == OB_BUY)
      return pos_mult * InpBuyPosMult;
   if(direction == OB_SELL)
      return pos_mult * InpSellPosMult;
   return pos_mult;
}

double ApplyHourPositionMultiplier(double pos_mult)
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   if(InpLowRiskHourMult != 1.0 && IsHourBlocked(InpLowRiskHours, dt.hour))
      pos_mult *= InpLowRiskHourMult;
   if(InpHighRiskHourMult != 1.0 && IsHourBlocked(InpHighRiskHours, dt.hour))
      pos_mult *= InpHighRiskHourMult;

   return pos_mult;
}

double ApplySignalTypePositionMultiplier(const OBZone &zone, double pos_mult)
{
   if(zone.is_liquidity_sweep)
      pos_mult *= InpSweepPosMult;
   if(zone.is_range_breakout)
      pos_mult *= InpRangeBreakoutPosMult;
   return pos_mult;
}

double ApplyBalancePositionMultiplier(double pos_mult)
{
   if(InpLowBalanceThreshold <= 0 || InpLowBalancePosMult == 1.0)
      return pos_mult;
   if(AccountInfoDouble(ACCOUNT_BALANCE) < InpLowBalanceThreshold)
      pos_mult *= InpLowBalancePosMult;
   return pos_mult;
}

int g_monthly_risk_key = 0;
double g_monthly_start_balance = 0.0;
double g_monthly_peak_balance = 0.0;
int g_monthly_entry_count = 0;

void SyncMonthlyRiskState()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int key = dt.year * 100 + dt.mon;
   if(key != g_monthly_risk_key)
   {
      g_monthly_risk_key = key;
      g_monthly_start_balance = AccountInfoDouble(ACCOUNT_BALANCE);
      g_monthly_peak_balance = g_monthly_start_balance;
      g_monthly_entry_count = 0;
   }
}

void UpdateMonthlyPeakBalance(double balance)
{
   if(balance > g_monthly_peak_balance)
      g_monthly_peak_balance = balance;
}

void RecordMonthlyEntry()
{
   SyncMonthlyRiskState();
   g_monthly_entry_count++;
}

bool PassMonthlyEntryGuard()
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   bool loss_guard_enabled = (InpMonthlyLossStopPct > 0 &&
      (InpMonthlyGuardMinBalance <= 0 || balance >= InpMonthlyGuardMinBalance));
   bool profit_lock_enabled = (InpMonthlyProfitLockStartPct > 0 &&
      InpMonthlyProfitLockKeepPct > 0 &&
      (InpMonthlyProfitLockMinBalance <= 0 || balance >= InpMonthlyProfitLockMinBalance));

   if(!loss_guard_enabled && !profit_lock_enabled)
      return true;

   SyncMonthlyRiskState();
   UpdateMonthlyPeakBalance(balance);
   if(g_monthly_start_balance <= 0)
      return true;

   if(loss_guard_enabled)
   {
      double stop_balance = g_monthly_start_balance * (1.0 - InpMonthlyLossStopPct / 100.0);
      bool enough_trades = (InpMonthlyLossStopMinTrades <= 0 ||
         g_monthly_entry_count >= InpMonthlyLossStopMinTrades);
      if(enough_trades && balance <= stop_balance)
         return false;
   }

   if(profit_lock_enabled)
   {
      double peak_profit = g_monthly_peak_balance - g_monthly_start_balance;
      double current_profit = balance - g_monthly_start_balance;
      double start_profit = g_monthly_start_balance * InpMonthlyProfitLockStartPct / 100.0;
      if(peak_profit >= start_profit)
      {
         double keep_profit = peak_profit * InpMonthlyProfitLockKeepPct / 100.0;
         if(current_profit < keep_profit)
            return false;
      }
   }

   return true;
}

double ApplyMonthlyPositionMultiplier(double pos_mult)
{
   if(InpMonthlyNegativePosMult == 1.0)
      return pos_mult;
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(InpMonthlyGuardMinBalance > 0 && balance < InpMonthlyGuardMinBalance)
      return pos_mult;
   SyncMonthlyRiskState();
   if(g_monthly_start_balance <= 0)
      return pos_mult;
   if(balance < g_monthly_start_balance)
      pos_mult *= InpMonthlyNegativePosMult;
   return pos_mult;
}

double ApplyEntryQualityPositionMultiplier(const TradeSignal &signal, double risk_price, double pos_mult)
{
   if(InpLateBounceSec > 0 && InpLateBounceMult != 1.0 &&
      signal.bounce_seconds > InpLateBounceSec)
      pos_mult *= InpLateBounceMult;

   if(InpBounceSweetMinPct > 0 && InpBounceSweetMaxPct > InpBounceSweetMinPct &&
      InpOutsideBounceSweetMult != 1.0 && signal.bounce_ob_pct > 0)
   {
      if(signal.bounce_ob_pct < InpBounceSweetMinPct ||
         signal.bounce_ob_pct > InpBounceSweetMaxPct)
         pos_mult *= InpOutsideBounceSweetMult;
   }

   if(InpBadRiskMax > InpBadRiskMin && InpBadRiskMult != 1.0 &&
      risk_price >= InpBadRiskMin && risk_price < InpBadRiskMax)
      pos_mult *= InpBadRiskMult;

   if(InpLargeRiskMin > 0 && InpLargeRiskMult != 1.0 &&
      risk_price >= InpLargeRiskMin)
      pos_mult *= InpLargeRiskMult;

   if(InpShallowConfirmPosMin > -999.0 && InpShallowConfirmPosMult != 1.0 &&
      signal.confirm_ob_pos > InpShallowConfirmPosMin)
   {
      if(InpShallowConfirmPosMult <= 0)
         return -1.0;
      pos_mult *= InpShallowConfirmPosMult;
   }

   return pos_mult;
}

double ApplyOneBadClusterPositionMultiplier(
   string hours,
   double risk_min,
   double risk_max,
   double confirm_min,
   double confirm_max,
   double mult,
   const TradeSignal &signal,
   double risk_price,
   double pos_mult
)
{
   if(hours == "" || mult == 1.0)
      return pos_mult;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(!IsHourBlocked(hours, dt.hour))
      return pos_mult;

   if(risk_max > risk_min && (risk_price < risk_min || risk_price >= risk_max))
      return pos_mult;

   if(signal.confirm_ob_pos < confirm_min || signal.confirm_ob_pos >= confirm_max)
      return pos_mult;

   if(mult <= 0)
      return -1.0;
   return pos_mult * mult;
}

double ApplyBadClusterPositionMultiplier(const TradeSignal &signal, double risk_price, double pos_mult)
{
   pos_mult = ApplyOneBadClusterPositionMultiplier(
      InpBadCluster1Hours, InpBadCluster1RiskMin, InpBadCluster1RiskMax,
      InpBadCluster1ConfirmMin, InpBadCluster1ConfirmMax, InpBadCluster1Mult,
      signal, risk_price, pos_mult);
   if(pos_mult < 0)
      return pos_mult;

   pos_mult = ApplyOneBadClusterPositionMultiplier(
      InpBadCluster2Hours, InpBadCluster2RiskMin, InpBadCluster2RiskMax,
      InpBadCluster2ConfirmMin, InpBadCluster2ConfirmMax, InpBadCluster2Mult,
      signal, risk_price, pos_mult);
   if(pos_mult < 0)
      return pos_mult;

   return ApplyOneBadClusterPositionMultiplier(
      InpBadCluster3Hours, InpBadCluster3RiskMin, InpBadCluster3RiskMax,
      InpBadCluster3ConfirmMin, InpBadCluster3ConfirmMax, InpBadCluster3Mult,
      signal, risk_price, pos_mult);
}

double ApplyHTFNetPushPositionMultiplier(int direction, double pos_mult)
{
   if(!InpEnableHTFNetPushFilter || InpHTFNetPushMinATR <= 0)
      return pos_mult;

   int bars = MathMax(InpHTFNetPushBars, 1);
   int need = bars + InpATRPeriod + 1;
   ENUM_TIMEFRAMES tf = MinutesToTF(InpHTFNetPushTF);

   MqlRates rates[];
   int count = CopyRates(_Symbol, tf, 1, need, rates);
   if(count < bars + 1)
      return pos_mult;

   double atr = CalcATR(rates, count, InpATRPeriod);
   if(atr <= 0)
      return pos_mult;

   int start = count - bars;
   double net_move = (rates[count - 1].close - rates[start].open) * direction;
   double net_atr = net_move / atr;
   double mult = InpHTFNetPushNeutralMult;

   if(net_atr >= InpHTFNetPushMinATR)
      mult = InpHTFNetPushAlignedMult;
   else if(net_atr <= -InpHTFNetPushMinATR)
      mult = InpHTFNetPushCounterMult;

   if(mult <= 0)
      return -1.0;
   return pos_mult * mult;
}

bool PassOBReentryCooldown(const OBZone &zone)
{
   if(InpOBReentryCooldownMin <= 0 || zone.last_entry_time == 0)
      return true;
   return (TimeCurrent() - zone.last_entry_time >= InpOBReentryCooldownMin * 60);
}

bool PassContinuationAgeFilter(const OBZone &zone, const EAState &state, bool deep_entry)
{
   if(InpFilterContAgeMaxBars <= 0)
      return true;
   if(InpFilterContAgeMaxBars < InpFilterContAgeMinBars)
      return true;
   if(!zone.is_continuation)
      return true;

   int age = state.bar_count - zone.created_bar;
   if(age < InpFilterContAgeMinBars || age > InpFilterContAgeMaxBars)
      return true;
   if(InpFilterContNonDeepOnly && deep_entry)
      return true;

   return false;
}

double ApplyBuyNoH1PositionFilter(const OBZone &zone, int direction, double pos_mult)
{
   if(InpFilterBuyNoH1MaxPosMult <= 0 || InpFilterBuyNoH1PosMult == 1.0)
      return pos_mult;
   if(direction != OB_BUY || zone.is_1h_aligned)
      return pos_mult;

   double min_mult = MathMax(0.0, InpFilterBuyNoH1MinPosMult);
   if(pos_mult < min_mult || pos_mult > InpFilterBuyNoH1MaxPosMult)
      return pos_mult;
   if(InpFilterBuyNoH1PosMult <= 0)
      return -1.0;

   return pos_mult * InpFilterBuyNoH1PosMult;
}

double CalcEntryLot(string symbol, double risk_pct, double risk_price, double pos_mult)
{
   double base_lot;
   if(InpFixedLotSize > 0)
      base_lot = InpFixedLotSize;
   else
      base_lot = CalcLotSize(symbol, risk_pct, risk_price);
   return base_lot * pos_mult;
}

bool FinalizeEntryEngineSignal(string symbol, const OBZone &zone, const EAState &state,
                               TradeSignal &signal)
{
   if(zone.expired || zone.used)
      return false;

   if(!PassOBReentryCooldown(zone))
      return false;

   if(!PassDirectionEntryHours(signal.direction, TimeCurrent()))
      return false;

   if(!PassMonthlyEntryGuard())
      return false;

   if(!PassEntryMomentumFilter(signal.direction))
      return false;

   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double spread = GetSpread(symbol);

   double entry = (signal.direction == OB_BUY) ? ask : bid;
   double risk_price = MathAbs(entry - signal.sl);
   if(risk_price <= 0)
      return false;

   double confirm_entry = signal.entry;
   if(confirm_entry <= 0)
      confirm_entry = (signal.direction == OB_BUY) ? zone.high : zone.low;
   if(InpMaxEntryOffsetR > 0 && MathAbs(entry - confirm_entry) / risk_price > InpMaxEntryOffsetR)
      return false;

   if(!PassSpreadRatio(risk_price, spread))
      return false;

   // EntryEngine确认后用真实可成交价重新过8-Gap，避免监控阶段和执行阶段口径漂移。
   double min_strength = GetDirectionMinStrength(signal.direction);
   if(min_strength > 0 && zone.strength < min_strength)
      return false;

   if(InpMaxRiskATR > 0 && state.atr_value > 0 && risk_price > state.atr_value * InpMaxRiskATR)
      return false;

   if(InpMaxCounterRiskATR > 0 && state.atr_value > 0 &&
      zone.is_1h_aligned == false && risk_price > state.atr_value * InpMaxCounterRiskATR)
      return false;

   double pos_mult = signal.pos_mult;
   if(InpEnableScoring)
   {
      double proximity_distance = MathAbs(bid - entry);
      double tp_est = CalcLiquiditySweepTP(zone, entry);
      if(tp_est == 0.0)
         tp_est = CalcOBHeightTP(zone, entry);
      if(tp_est == 0.0 && InpDTPTriggerR <= 0 && InpFixedTPR > 0)
         tp_est = RToPrice(InpFixedTPR, entry, risk_price, signal.direction);
      else if(tp_est == 0.0 && InpEnableStateFilter && state.market_state == 0 && state.target_price > 0)
         tp_est = state.target_price;
      else if(tp_est == 0.0)
         tp_est = RToPrice(2.0, entry, risk_price, signal.direction);
      double target_distance = MathAbs(tp_est - entry);
      int score = CalcSignalScore(zone, state, state.market_state,
                                  proximity_distance, risk_price, target_distance);
      if(InpMinScore > 0 && score < InpMinScore)
         return false;
      pos_mult = ScoreToMultiplier(score);
      if(pos_mult < 0)
         return false;
   }
   else
   {
      pos_mult = InpEnablePosMult ? CalcPositionMultiplier(zone) : 1.0;
   }
   if(signal.deep_entry && InpDeepEntryBoost > 1.0)
      pos_mult *= InpDeepEntryBoost;
   pos_mult = ApplySignalTypePositionMultiplier(zone, pos_mult);
   pos_mult = ApplyDirectionPosMult(signal.direction, pos_mult);
   pos_mult = ApplyHourPositionMultiplier(pos_mult);
   pos_mult = ApplyEntryQualityPositionMultiplier(signal, risk_price, pos_mult);
   pos_mult = ApplyBadClusterPositionMultiplier(signal, risk_price, pos_mult);
   if(pos_mult < 0)
      return false;
   pos_mult = ApplyHTFNetPushPositionMultiplier(signal.direction, pos_mult);
   pos_mult = ApplyBalancePositionMultiplier(pos_mult);
   pos_mult = ApplyMonthlyPositionMultiplier(pos_mult);
   pos_mult = ApplyPositionMultiplierCap(pos_mult);
   if(!PassContinuationAgeFilter(zone, state, signal.deep_entry))
      return false;
   pos_mult = ApplyBuyNoH1PositionFilter(zone, signal.direction, pos_mult);
   if(pos_mult < 0)
      return false;

   double final_lot = CalcEntryLot(symbol, InpRiskPercent, risk_price, pos_mult);
   final_lot = ApplyLotCap(final_lot);
   final_lot = ApplySignalTypeLotCap(zone, final_lot);
   final_lot = ApplyBalanceLotCap(final_lot);
   if(!PassMinRisk(final_lot, risk_price, symbol))
      return false;

   double margin_required = 0;
   ENUM_ORDER_TYPE order_type = (signal.direction == OB_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(!OrderCalcMargin(order_type, symbol, final_lot, entry, margin_required))
      return false;

   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(margin_required > free_margin)
   {
      if(free_margin <= 0)
         return false;
      final_lot = final_lot * (free_margin / margin_required) * 0.95;
      final_lot = ApplyLotCap(final_lot);
      final_lot = ApplySignalTypeLotCap(zone, final_lot);
      final_lot = ApplyBalanceLotCap(final_lot);
   }

   double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double lot_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(lot_step <= 0)
      return false;

   final_lot = MathFloor(final_lot / lot_step) * lot_step;
   if(final_lot < lot_min)
      return false;
   if(final_lot > lot_max)
      final_lot = lot_max;

   // v11: 入场时按状态决定TP模式
   double tp = 0.0;
   if(zone.is_liquidity_sweep)
   {
      tp = CalcLiquiditySweepTP(zone, entry);
      if(tp == 0.0 && InpDTPTriggerR <= 0 && InpFixedTPR > 0)
         tp = RToPrice(InpFixedTPR, entry, risk_price, signal.direction);
   }
   else if(InpEnableStateFilter && state.market_state == 0)
   {
      // 震荡态: OBHeight TP优先，其次swing目标，最后固定TP
      tp = CalcOBHeightTP(zone, entry);
      if(tp == 0.0 && state.target_price > 0)
      {
         double swing_dist = MathAbs(state.target_price - entry);
         if(swing_dist > risk_price)
            tp = state.target_price;
      }
      if(tp == 0.0 && InpFixedTPR > 0)
         tp = RToPrice(InpFixedTPR, entry, risk_price, signal.direction);
   }
   else
   {
      // 趋势态: tp=0让DTP接管，除非没有DTP则用固定TP兜底
      if(InpDTPTriggerR <= 0 && InpFixedTPR > 0)
         tp = RToPrice(InpFixedTPR, entry, risk_price, signal.direction);
   }

   signal.entry = entry;
   signal.risk_price = risk_price;
   signal.lot = NormalizeDouble(final_lot, 2);
   signal.pos_mult = pos_mult;
   signal.tp = tp;
   signal.htf_target = false;
   signal.htf_partial_r = 0;
   signal.htf_partial_pct = 0;
   ApplyHTFTarget(symbol, entry, risk_price, signal);
   PrintEntryDebug("entry_engine", zone, state, signal, entry, risk_price, spread, pos_mult,
                   InpEnableScoring ? CalcSignalScore(zone, state, state.market_state,
                                                      MathAbs(bid - entry), risk_price,
                                                      MathAbs(RToPrice(2.0, entry, risk_price, signal.direction) - entry))
                                    : -1);
   signal.comment = "WT " + InpVersion + " " + (signal.direction > 0 ? "B" : "S") +
                    (zone.is_range_breakout ? " RB" : "") +
                    (zone.is_liquidity_sweep ? " SWP" : "") +
                    " x" + DoubleToString(pos_mult, 1);

   return true;
}

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

   if(!PassOBReentryCooldown(zone))
      return false;

   if(!PassDirectionEntryHours(zone.direction, TimeCurrent()))
      return false;

   if(!PassMonthlyEntryGuard())
      return false;

   if(!PassEntryMomentumFilter(zone.direction))
      return false;

   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double spread = GetSpread(symbol);

   if(!IsZoneTouched(zone, bid, ask))
      return false;

   if(!zone.is_range_breakout && !PassDoubleTouchFilter(zone))
      return false;

   // v9.8 态过滤: 趋势态硬过滤逆势
   if(InpEnableStateFilter && state.market_state != 0 && state.market_state != zone.direction)
      return false;

   double sl = 0;
   if(zone.direction == OB_BUY)
      sl = zone.low - state.atr_value * InpSLBufferATR;
   else
      sl = zone.high + state.atr_value * InpSLBufferATR;

   double entry = (zone.direction == OB_BUY) ? ask : bid;
   double risk_price = MathAbs(entry - sl);

   if(risk_price <= 0)
      return false;

   if(!zone.is_range_breakout && !PassOffsetGuard(entry, risk_price, zone.direction, zone.mid, InpMaxEntryOffsetR))
      return false;

   if(!PassSpreadRatio(risk_price, spread))
      return false;

   // Gap5: 信号质量门槛
   double min_strength = GetDirectionMinStrength(zone.direction);
   if(min_strength > 0 && zone.strength < min_strength)
      return false;

   // Gap7: risk不能太大
   if(InpMaxRiskATR > 0 && state.atr_value > 0 && risk_price > state.atr_value * InpMaxRiskATR)
      return false;

   // Gap8: 逆势 + risk大 → 丢弃
   if(InpMaxCounterRiskATR > 0 && state.atr_value > 0 &&
      zone.is_1h_aligned == false && risk_price > state.atr_value * InpMaxCounterRiskATR)
      return false;

   // v9.8 评分系统
   double pos_mult = 1.0;
   int score = -1;
   if(InpEnableScoring)
   {
      double proximity_distance = MathAbs(bid - entry);
      double tp_est = CalcLiquiditySweepTP(zone, entry);
      if(tp_est == 0.0)
         tp_est = CalcOBHeightTP(zone, entry);
      if(tp_est == 0.0 && InpDTPTriggerR <= 0 && InpFixedTPR > 0)
         tp_est = RToPrice(InpFixedTPR, entry, risk_price, zone.direction);
      else if(tp_est == 0.0 && InpEnableStateFilter && state.market_state == 0 && state.target_price > 0)
         tp_est = state.target_price;
      else if(tp_est == 0.0)
         tp_est = RToPrice(2.0, entry, risk_price, zone.direction);
      double target_distance = MathAbs(tp_est - entry);
      score = CalcSignalScore(zone, state, state.market_state,
                              proximity_distance, risk_price, target_distance);
      if(InpMinScore > 0 && score < InpMinScore)
         return false;
      pos_mult = ScoreToMultiplier(score);
      if(pos_mult < 0)
         return false;
   }
   else
   {
      pos_mult = InpEnablePosMult ? CalcPositionMultiplier(zone) : 1.0;
   }
   bool deep_entry = (InpEntryDepthPct > 0);
   if(InpEntryDepthPct > 0 && InpDeepEntryBoost > 1.0)
      pos_mult *= InpDeepEntryBoost;
   pos_mult = ApplySignalTypePositionMultiplier(zone, pos_mult);
   signal.bounce_seconds = 0;
   signal.bounce_ob_pct = 0.0;
   pos_mult = ApplyDirectionPosMult(zone.direction, pos_mult);
   pos_mult = ApplyHourPositionMultiplier(pos_mult);
   pos_mult = ApplyEntryQualityPositionMultiplier(signal, risk_price, pos_mult);
   pos_mult = ApplyBadClusterPositionMultiplier(signal, risk_price, pos_mult);
   if(pos_mult < 0)
      return false;
   pos_mult = ApplyHTFNetPushPositionMultiplier(zone.direction, pos_mult);
   pos_mult = ApplyBalancePositionMultiplier(pos_mult);
   pos_mult = ApplyMonthlyPositionMultiplier(pos_mult);
   pos_mult = ApplyPositionMultiplierCap(pos_mult);
   if(!PassContinuationAgeFilter(zone, state, deep_entry))
      return false;
   pos_mult = ApplyBuyNoH1PositionFilter(zone, zone.direction, pos_mult);
   if(pos_mult < 0)
      return false;
   double final_lot = CalcEntryLot(symbol, InpRiskPercent, risk_price, pos_mult);
   final_lot = ApplyLotCap(final_lot);
   final_lot = ApplySignalTypeLotCap(zone, final_lot);
   final_lot = ApplyBalanceLotCap(final_lot);

   if(!PassMinRisk(final_lot, risk_price, symbol))
      return false;

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
      final_lot = ApplyLotCap(final_lot);
      final_lot = ApplySignalTypeLotCap(zone, final_lot);
      final_lot = ApplyBalanceLotCap(final_lot);
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

   // v11: 入场时按状态决定TP模式（直接入场路径）
   double tp = 0.0;
   if(zone.is_range_breakout && InpRangeBreakoutTPMult > 0 && zone.range_height > 0)
      tp = entry + zone.direction * zone.range_height * InpRangeBreakoutTPMult;
   else if(zone.is_liquidity_sweep)
   {
      tp = CalcLiquiditySweepTP(zone, entry);
      if(tp == 0.0 && InpDTPTriggerR <= 0 && InpFixedTPR > 0)
         tp = RToPrice(InpFixedTPR, entry, risk_price, zone.direction);
   }
   else if(InpEnableStateFilter && state.market_state == 0)
   {
      tp = CalcOBHeightTP(zone, entry);
      if(tp == 0.0 && state.target_price > 0)
      {
         double swing_dist = MathAbs(state.target_price - entry);
         if(swing_dist > risk_price)
            tp = state.target_price;
      }
      if(tp == 0.0 && InpFixedTPR > 0)
         tp = RToPrice(InpFixedTPR, entry, risk_price, zone.direction);
   }
   else
   {
      if(InpDTPTriggerR <= 0 && InpFixedTPR > 0)
         tp = RToPrice(InpFixedTPR, entry, risk_price, zone.direction);
   }

   signal.direction = zone.direction;
   signal.entry = entry;
   signal.sl = sl;
   signal.tp = tp;
   signal.risk_price = risk_price;
   signal.lot = final_lot;
   signal.pos_mult = pos_mult;
   signal.ob_index = zone_idx;
   signal.deep_entry = deep_entry;
   signal.touch_price = entry;
   signal.confirm_price = entry;
   signal.bounce_seconds = 0;
   signal.bounce_ob_pct = 0.0;
   signal.confirm_ob_pos = 0.0;
   signal.htf_target = false;
   signal.htf_partial_r = 0;
   signal.htf_partial_pct = 0;
   ApplyHTFTarget(symbol, entry, risk_price, signal);
   PrintEntryDebug("direct", zone, state, signal, entry, risk_price, spread, pos_mult, score);
   signal.comment = "WT " + InpVersion + " " + (zone.direction > 0 ? "B" : "S") +
                    (zone.is_range_breakout ? " RB" : "") +
                    (zone.is_liquidity_sweep ? " SWP" : "") +
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
