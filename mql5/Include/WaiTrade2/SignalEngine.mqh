#ifndef __WAITRADE_SIGNAL_ENGINE_MQH__
#define __WAITRADE_SIGNAL_ENGINE_MQH__

#include "Types.mqh"
#include "Config.mqh"
#include "MathUtils.mqh"
#include "TradeOps.mqh"
#include "MarketState.mqh"
#include "ScoreEngine.mqh"
#include "DecayDetector.mqh"
#include "RangeDetector.mqh"

// ═══════════════════════════════════════════════════════════════════════════
// FVG入场专用函数: 处理公允价值缺口的入场逻辑
//   震荡市(State=0): FVG回补=消解确认, 反向(fade)入场 — 核心用途
//   趋势市(State≠0): FVG回补=方向确认, 跟随入场 — 辅助用途
//
// FVG与普通OB的关键差异:
//   1. FVG间隙天然大于OB → 不适用MaxRiskATR限制
//   2. FVG回补后价格快速穿越 → 位置检查用宽缓冲(4x gap_half)
//   3. 小账户($200) FVG间隙大→计算lot<min → 强制min lot
// ═══════════════════════════════════════════════════════════════════════════
bool CheckFVGEntry(string symbol, const OBZone &zone, int zone_idx,
                   const EAState &state, TradeSignal &signal)
{
   if(!CfgFVGEnableFadeEntry())
      return false;
   if(!zone.is_fvg || !zone.fvg_filled)
      return false;
   if(zone.expired || zone.used)
      return false;

   // ── FVG专属时段过滤 ──────────────────────────────────
   if(StringLen(CfgFVGNoEntryHours()) > 0)
   {
      MqlDateTime dt_fvg;
      TimeToStruct(TimeCurrent(), dt_fvg);
      if(IsHourBlocked(CfgFVGNoEntryHours(), dt_fvg.hour))
         return false;
   }

   // ── 市场上下文 + H1趋势对齐 ──────────────────────────
   bool is_range = (CfgEnableStateFilter() && state.market_state == 0);
   if(CfgFVGRequireRangeBoundary() && !is_range)
      return false;

   int h1_dir = CfgFVGRequireH1Aligned() ? Detect1HOBDirection(symbol) : 0;

   int trade_dir;
   if(is_range)
   {
      // 震荡市: Fade入场(反向)
      trade_dir = -zone.direction;
      // H1强趋势时拒绝逆势fade(仅当InpFVGRequireH1Aligned=true)
      if(h1_dir != 0 && h1_dir != trade_dir)
         return false;
   }
   else
   {
      // 趋势市: Follow入场 — 必须与H1方向一致(仅当InpFVGRequireH1Aligned=true)
      if(h1_dir != 0 && h1_dir != zone.direction)
         return false;
      trade_dir = zone.direction;
   }

   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double spread = GetSpread(symbol);

   double gap_mid = zone.mid;
   double gap_half = (zone.high - zone.low) / 2.0;
   if(gap_half <= 0) return false;

   // 位置检查: 价格不得偏离FVG回补区域太远(4x gap_half缓冲, 适应快速穿越)
   if(trade_dir == OB_BUY)
   {
      if(ask > zone.high + gap_half * 4.0)
         return false;
   }
   else
   {
      if(bid < zone.low - gap_half * 4.0)
         return false;
   }

   // ── 确认蜡烛: 最近收盘K线必须与入场方向一致 ──────────
   if(CfgFVGRequireConfirmCandle())
   {
      MqlRates recent[2];
      if(CopyRates(symbol, PERIOD_CURRENT, 0, 2, recent) >= 2)
      {
         bool candle_ok = false;
         if(trade_dir == OB_BUY)
            candle_ok = (recent[1].close > recent[1].open);  // 阳线确认
         else
            candle_ok = (recent[1].close < recent[1].open);  // 阴线确认
         if(!candle_ok)
            return false;
      }
   }

   // ── SL: FVG对侧边界 + ATR缓冲 ─────────────────────────
   double sl;
   double entry = (trade_dir == OB_BUY) ? ask : bid;
   if(trade_dir == OB_BUY)
   {
      sl = zone.low - state.atr_value * CfgSLBufferATR();
      if(InpMinSLSpreadMult > 0 && spread > 0)
         sl = MathMin(sl, entry - spread * InpMinSLSpreadMult);
   }
   else
   {
      sl = zone.high + state.atr_value * CfgSLBufferATR();
      if(InpMinSLSpreadMult > 0 && spread > 0)
         sl = MathMax(sl, entry + spread * InpMinSLSpreadMult);
   }

   double risk_price = MathAbs(entry - sl);
   if(risk_price <= 0) return false;

   // ── 风险质量 ──────────────────────────────────────────
   if(!PassSpreadRatio(risk_price, spread))
      return false;
   if(CfgFVGFadeMinRiskSpreadRatio() > 0 && spread > 0 &&
      risk_price / spread < CfgFVGFadeMinRiskSpreadRatio())
      return false;
   // 跳过MaxRiskATR: FVG间隙天然大于普通OB

   // ── 偏移检查 ──────────────────────────────────────────
   double offset_r = MathAbs(entry - gap_mid) / risk_price;
   if(offset_r > CfgFVGFadeMaxEntryOffsetR())
      return false;

   // ── TP: 区间对侧swing点 或 gap高度R倍数 ────────────────
   double tp = 0.0;
   if(CfgFVGFadeTPMult() > 0)
   {
      if(is_range && state.target_price > 0)
         tp = state.target_price;
      else
         tp = entry + trade_dir * (zone.high - zone.low) * CfgFVGFadeTPMult();
   }

   // ── 仓位控制 ──────────────────────────────────────────
   double pos_mult = CfgFVGFadePosMult();
   if(zone.strength >= 3.0) pos_mult *= 1.3;
   else if(zone.strength < 1.5) pos_mult *= 0.7;

   pos_mult = ApplyDirectionPosMult(trade_dir, pos_mult);
   pos_mult = ApplyHourPositionMultiplier(pos_mult);
   pos_mult = ApplyBalancePositionMultiplier(pos_mult);
   pos_mult = ApplyMonthlyPositionMultiplier(pos_mult);
   pos_mult = ApplyRuntimePositionMultiplier(pos_mult);
   pos_mult = ApplyPositionMultiplierCap(pos_mult);
   if(pos_mult < 0) return false;

   double final_lot = CalcEntryLot(symbol, CfgRiskPercent(), risk_price, pos_mult);
   final_lot = ApplyLotCap(final_lot);
   if(CfgFVGFadeMaxLotSize() > 0 && final_lot > CfgFVGFadeMaxLotSize())
      final_lot = CfgFVGFadeMaxLotSize();
   if(!PassMinRisk(final_lot, risk_price, symbol))
      return false;

   // ── 保证金检查 ────────────────────────────────────────
   double margin_required = 0;
   ENUM_ORDER_TYPE order_type = (trade_dir == OB_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(!OrderCalcMargin(order_type, symbol, final_lot, entry, margin_required))
      return false;
   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(margin_required > free_margin)
   {
      if(free_margin <= 0) return false;
      final_lot = final_lot * (free_margin / margin_required) * 0.95;
      final_lot = ApplyLotCap(final_lot);
      if(CfgFVGFadeMaxLotSize() > 0 && final_lot > CfgFVGFadeMaxLotSize())
         final_lot = CfgFVGFadeMaxLotSize();
   }

   double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double lot_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(lot_step <= 0) return false;
   final_lot = MathFloor(final_lot / lot_step) * lot_step;
   // 小账户($200): FVG间隙大→risk_price大→计算lot常跌破min, 强制min lot
   if(final_lot < lot_min) final_lot = lot_min;
   if(final_lot > lot_max) return false;

   // ── 填充信号 ──────────────────────────────────────────
   signal.direction = trade_dir;
   signal.entry = entry;
   signal.sl = sl;
   signal.tp = tp;
   signal.risk_price = risk_price;
   signal.lot = final_lot;
   signal.pos_mult = pos_mult;
   signal.ob_index = zone_idx;
   signal.deep_entry = false;
   signal.touch_price = entry;
   signal.confirm_price = entry;
   signal.bounce_seconds = 0;
   signal.bounce_ob_pct = 0.0;
   signal.confirm_ob_pos = 0.0;
   signal.htf_target = false;
   signal.htf_partial_r = 0;
   signal.htf_partial_pct = 0;
   signal.comment = "WT " + InpVersion + " " + (trade_dir > 0 ? "B" : "S") +
                    " FVG" +
                    (is_range ? " Fade" : " Follow") +
                    " x" + DoubleToString(pos_mult, 1);

   return true;
}

double CalcOBHeightTP(const OBZone &zone, double entry)
{
   if(CfgOBHeightTPMult() <= 0 || zone.is_range_breakout || zone.is_htf_pullback) return 0.0;
   double ob_h = zone.high - zone.low;
   if(ob_h <= 0) return 0.0;
   return entry + zone.direction * ob_h * CfgOBHeightTPMult();
}

double CalcHTFPullbackTP(const OBZone &zone, double entry)
{
   if(!zone.is_htf_pullback || InpHTFPullbackTPMult <= 0 || zone.range_height <= 0)
      return 0.0;
   return entry + zone.direction * zone.range_height * InpHTFPullbackTPMult;
}

double CalcLiquiditySweepTP(const OBZone &zone, double entry)
{
   if(!zone.is_liquidity_sweep || CfgSweepTPMult() <= 0 || zone.range_height <= 0)
      return 0.0;
   if(zone.direction == OB_BUY)
      return zone.high + zone.range_height * CfgSweepTPMult();
   return zone.low - zone.range_height * CfgSweepTPMult();
}

bool IsZoneTouched(const OBZone &zone, double bid, double ask)
{
   if(zone.is_range_breakout)
   {
      if(zone.direction == OB_BUY)
         return (bid >= zone.high);
      return (ask <= zone.low);
   }

   if(zone.is_htf_pullback)
   {
      if(zone.direction == OB_BUY)
         return (bid <= zone.high);
      return (ask >= zone.low);
   }

   if(zone.direction == OB_BUY)
      return (bid <= zone.high);
   else
      return (ask >= zone.low);
}

bool PassDoubleTouchFilter(const OBZone &zone)
{
   if(CfgRequireDoubleTch())
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
   if(spread > 0 && risk_distance / spread < CfgMinRiskSpreadRatio())
      return false;
   return true;
}

// Tick噪音门控: 检查入场前tick方向一致性, 过滤高噪音环境
// 使用Cfg访问器 → 支持自适应切换(权益回撤时自动收紧)
bool PassTickNoiseGate(int direction, string symbol)
{
   if(!InpEnableTickNoiseGate)
      return true;

   double min_ratio  = CfgTickNoiseGateMinDirRatio();
   double max_range  = CfgTickNoiseGateMaxRangeATR();

   MqlTick ticks[];
   int count = CopyTicks(symbol, ticks, COPY_TICKS_ALL, 0, InpTickNoiseGateLookback);
   if(count < InpTickNoiseGateLookback / 2)
      return true;  // 数据不足,放行

   // 统计tick方向
   int up_ticks = 0, down_ticks = 0;
   double prev_mid = 0;
   double tick_high = 0, tick_low = DBL_MAX;
   bool   has_ref = false;

   for(int i = 0; i < count; i++)
   {
      double mid = (ticks[i].bid + ticks[i].ask) / 2.0;
      if(mid > tick_high) tick_high = mid;
      if(mid < tick_low)  tick_low  = mid;

      if(has_ref)
      {
         if(mid > prev_mid)      up_ticks++;
         else if(mid < prev_mid) down_ticks++;
      }
      prev_mid = mid;
      has_ref = true;
   }

   int total = up_ticks + down_ticks;
   if(total < 5)
      return true;  // 方向性tick不足,放行

   double dir_ratio = (direction > 0) ?
      (double)up_ticks   / (double)total :
      (double)down_ticks / (double)total;

   if(dir_ratio < min_ratio)
   {
      if(InpEnableEntryDebug)
         Print("TICK_NOISE z=skip dir_ratio=", DoubleToString(dir_ratio, 2),
               " min=", DoubleToString(min_ratio, 2),
               " total_ticks=", total);
      return false;
   }

   // 振幅检查: tick波动/ATR过大 → 噪音环境
   if(max_range > 0 && tick_low < DBL_MAX)
   {
      double atr_arr[1];
      double atr_val = 0;
      if(CopyBuffer(iATR(symbol, PERIOD_CURRENT, InpATRPeriod), 0, 0, 1, atr_arr) > 0)
         atr_val = atr_arr[0];
      if(atr_val > 0)
      {
         double range_ratio = (tick_high - tick_low) / atr_val;
         if(range_ratio > max_range)
         {
            if(InpEnableEntryDebug)
               Print("TICK_NOISE z=skip range_ratio=", DoubleToString(range_ratio, 3),
                     " max=", DoubleToString(max_range, 3));
            return false;
         }
      }
   }

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

bool IsCsvIntListed(string csv, int value)
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
      int listed = (int)StringToInteger(token);
      if(listed == value)
         return true;
   }

   return false;
}

bool IsHourBlocked(string csv, int hour)
{
   return IsCsvIntListed(csv, hour);
}

bool IsMonthAllowed(string csv, int month)
{
   return (StringLen(csv) == 0 || IsCsvIntListed(csv, month));
}

bool IsMonthlyDefensiveModeActive();

bool PassNoEntryHours(datetime now)
{
   MqlDateTime dt;
   TimeToStruct(now, dt);

   if(!IsMonthAllowed(InpEntryMonths, dt.mon))
      return false;
   if(IsHourBlocked(CfgNoEntryHours(), dt.hour))
      return false;
   if(IsMonthlyDefensiveModeActive() &&
      IsHourBlocked(InpMonthlyDefensiveNoEntryHours, dt.hour))
      return false;
   return true;
}

bool PassDirectionEntryHours(int direction, datetime now)
{
   MqlDateTime dt;
   TimeToStruct(now, dt);

   if(!IsMonthAllowed(InpEntryMonths, dt.mon))
      return false;
   if(IsHourBlocked(CfgNoEntryHours(), dt.hour))
      return false;
   if(direction == OB_BUY && IsHourBlocked(CfgNoBuyHours(), dt.hour))
      return false;
   if(direction == OB_SELL && IsHourBlocked(CfgNoSellHours(), dt.hour))
      return false;
   if(IsMonthlyDefensiveModeActive())
   {
      if(IsHourBlocked(InpMonthlyDefensiveNoEntryHours, dt.hour))
         return false;
      if(direction == OB_BUY && IsHourBlocked(InpMonthlyDefensiveNoBuyHours, dt.hour))
         return false;
      if(direction == OB_SELL && IsHourBlocked(InpMonthlyDefensiveNoSellHours, dt.hour))
         return false;
   }

   return true;
}

bool PassEntryMomentumFilter(int direction)
{
   if(!InpEnableEntryMomentumFilter)
      return true;

   int tf_min = (InpEntryMomentumTF > 0) ? InpEntryMomentumTF : CfgBarTF();
   ENUM_TIMEFRAMES tf = MinutesToTF(tf_min);
   int need = MathMax(MathMax(InpStrongMomentumBars, CfgDecayBars()) + 5, 8);

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
         " touch_count=", zone.touch_count,
         " entry_count=", zone.entry_count,
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
         " touch_price=", DoubleToString(signal.touch_price, _Digits),
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
   // 防守态全局仓位衰减(在所有乘数链末端, cap之前)
   // 解决信号强度评分在震荡市系统性高估: 2605 x1.4占19%交易/51%亏损
   if(IsAdaptiveNoiseGateDefensive() && InpAdaptiveNoiseDefBoostMult > 0.0)
      pos_mult *= InpAdaptiveNoiseDefBoostMult;

   // 双扫体制自适应: 震荡区间降低仓位(双重条件: 体制检测+防守态)
   // 仅在双扫确认震荡区间 AND 权益回撤>阈值时衰减, 趋势月双扫回调不受影响
   if(CfgDoubleSweepRegimePosMult() > 0.0 && CfgDoubleSweepRegimePosMult() < 1.0
      && IsDoubleSweepRegime() && IsAdaptiveNoiseGateDefensive())
   {
      pos_mult *= CfgDoubleSweepRegimePosMult();
   }

   double cap = CfgAdaptiveMaxPosMult();
   if(cap > 0 && pos_mult > cap)
      return cap;
   return pos_mult;
}

double ApplyLotCap(double lot)
{
   if(CfgMaxLotSize() > 0 && lot > CfgMaxLotSize())
      return CfgMaxLotSize();
   return lot;
}

bool IsLooseSweepZone(const OBZone &zone)
{
   return zone.is_liquidity_sweep && zone.is_loose_sweep;
}

double ApplySignalTypeLotCap(const OBZone &zone, double lot)
{
   if(IsLooseSweepZone(zone))
   {
      if(InpLooseSweepMaxLotSize > 0 && lot > InpLooseSweepMaxLotSize)
         return InpLooseSweepMaxLotSize;
      return lot;
   }
   if(zone.is_htf_pullback && InpHTFPullbackMaxLotSize > 0 && lot > InpHTFPullbackMaxLotSize)
      return InpHTFPullbackMaxLotSize;
   if(zone.is_liquidity_sweep && CfgSweepMaxLotSize() > 0 && lot > CfgSweepMaxLotSize())
      return CfgSweepMaxLotSize();
   if(zone.is_range_breakout && InpRangeBreakoutMaxLotSize > 0 && lot > InpRangeBreakoutMaxLotSize)
      return InpRangeBreakoutMaxLotSize;
   return lot;
}

double ApplyBalanceLotCap(double lot)
{
   if(CfgLowBalanceThreshold() <= 0 || CfgLowBalanceMaxLotSize() <= 0)
      return lot;
   if(AccountInfoDouble(ACCOUNT_BALANCE) < CfgLowBalanceThreshold() && lot > CfgLowBalanceMaxLotSize())
      return CfgLowBalanceMaxLotSize();
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
   double mult = 1.0;
   if(direction == OB_BUY)
      mult = InpBuyPosMult;
   else if(direction == OB_SELL)
      mult = InpSellPosMult;

   // 防守态方向仓位衰减: 解决某方向系统性亏损(如2603卖单WR=32%亏$115)
   if(IsAdaptiveNoiseGateDefensive())
   {
      if(direction == OB_BUY && InpAdaptiveNoiseDefBuyMult > 0.0 && InpAdaptiveNoiseDefBuyMult != 1.0)
         mult *= InpAdaptiveNoiseDefBuyMult;
      else if(direction == OB_SELL && InpAdaptiveNoiseDefSellMult > 0.0 && InpAdaptiveNoiseDefSellMult != 1.0)
         mult *= InpAdaptiveNoiseDefSellMult;
   }

   return pos_mult * mult;
}

double ApplyHourPositionMultiplier(double pos_mult)
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   if(CfgLowRiskHourMult() != 1.0 && IsHourBlocked(CfgLowRiskHours(), dt.hour))
      pos_mult *= CfgLowRiskHourMult();
   if(CfgHighRiskHourMult() != 1.0 && IsHourBlocked(CfgHighRiskHours(), dt.hour))
      pos_mult *= CfgHighRiskHourMult();

   return pos_mult;
}

double ApplyOneContextFilterPositionMultiplier(
   string months,
   string no_hours,
   string no_buy_hours,
   string no_sell_hours,
   double min_month_start_balance,
   double max_month_start_balance,
   double max_balance,
   double min_price,
   double max_price,
   double mult,
   int direction,
   double pos_mult
)
{
   if(mult == 1.0)
      return pos_mult;
   if(no_hours == "" && no_buy_hours == "" && no_sell_hours == "")
      return pos_mult;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(!IsMonthAllowed(months, dt.mon))
      return pos_mult;

   if(min_month_start_balance > 0 || max_month_start_balance > 0)
   {
      SyncMonthlyRiskState();
      if(g_monthly_start_balance <= 0)
         return pos_mult;
      if(min_month_start_balance > 0 && g_monthly_start_balance < min_month_start_balance)
         return pos_mult;
      if(max_month_start_balance > 0 && g_monthly_start_balance > max_month_start_balance)
         return pos_mult;
   }

   if(max_balance > 0 && AccountInfoDouble(ACCOUNT_BALANCE) > max_balance)
      return pos_mult;

   if(min_price > 0 || max_price > 0)
   {
      double ref_price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if(ref_price <= 0)
         ref_price = SymbolInfoDouble(_Symbol, SYMBOL_LAST);
      if(ref_price <= 0)
         return pos_mult;
      if(min_price > 0 && ref_price < min_price)
         return pos_mult;
      if(max_price > 0 && ref_price > max_price)
         return pos_mult;
   }

   bool matched = IsHourBlocked(no_hours, dt.hour);
   if(direction == OB_BUY && IsHourBlocked(no_buy_hours, dt.hour))
      matched = true;
   if(direction == OB_SELL && IsHourBlocked(no_sell_hours, dt.hour))
      matched = true;
   if(!matched)
      return pos_mult;

   if(mult <= 0)
      return -1.0;
   return pos_mult * mult;
}

double ApplyContextFilterPositionMultiplier(int direction, double pos_mult)
{
   if(UseBTCProfile())
      return pos_mult;

   pos_mult = ApplyOneContextFilterPositionMultiplier(
      CfgContextFilter1Months(), CfgContextFilter1NoHours(),
      CfgContextFilter1NoBuyHours(), CfgContextFilter1NoSellHours(),
      CfgContextFilter1MinMonthStartBalance(), CfgContextFilter1MaxMonthStartBalance(),
      CfgContextFilter1MaxBalance(),
      CfgContextFilter1MinPrice(), CfgContextFilter1MaxPrice(),
      CfgContextFilter1Mult(), direction, pos_mult);
   if(pos_mult < 0)
      return pos_mult;

   pos_mult = ApplyOneContextFilterPositionMultiplier(
      CfgContextFilter2Months(), CfgContextFilter2NoHours(),
      CfgContextFilter2NoBuyHours(), CfgContextFilter2NoSellHours(),
      CfgContextFilter2MinMonthStartBalance(), CfgContextFilter2MaxMonthStartBalance(),
      CfgContextFilter2MaxBalance(),
      CfgContextFilter2MinPrice(), CfgContextFilter2MaxPrice(),
      CfgContextFilter2Mult(), direction, pos_mult);
   if(pos_mult < 0)
      return pos_mult;

   pos_mult = ApplyOneContextFilterPositionMultiplier(
      CfgContextFilter3Months(), CfgContextFilter3NoHours(),
      CfgContextFilter3NoBuyHours(), CfgContextFilter3NoSellHours(),
      CfgContextFilter3MinMonthStartBalance(), CfgContextFilter3MaxMonthStartBalance(),
      CfgContextFilter3MaxBalance(),
      CfgContextFilter3MinPrice(), CfgContextFilter3MaxPrice(),
      CfgContextFilter3Mult(), direction, pos_mult);
   if(pos_mult < 0)
      return pos_mult;

   pos_mult = ApplyOneContextFilterPositionMultiplier(
      CfgContextFilter4Months(), CfgContextFilter4NoHours(),
      CfgContextFilter4NoBuyHours(), CfgContextFilter4NoSellHours(),
      CfgContextFilter4MinMonthStartBalance(), CfgContextFilter4MaxMonthStartBalance(),
      CfgContextFilter4MaxBalance(),
      CfgContextFilter4MinPrice(), CfgContextFilter4MaxPrice(),
      CfgContextFilter4Mult(), direction, pos_mult);
   if(pos_mult < 0)
      return pos_mult;

   return ApplyOneContextFilterPositionMultiplier(
      CfgContextFilter5Months(), CfgContextFilter5NoHours(),
      CfgContextFilter5NoBuyHours(), CfgContextFilter5NoSellHours(),
      CfgContextFilter5MinMonthStartBalance(), CfgContextFilter5MaxMonthStartBalance(),
      CfgContextFilter5MaxBalance(),
      CfgContextFilter5MinPrice(), CfgContextFilter5MaxPrice(),
      CfgContextFilter5Mult(), direction, pos_mult);
}

bool ShouldApplyContextReverse(int direction, double ref_price, double risk_price)
{
   if(UseBTCProfile())
      return false;
   if(InpContextReverseHours == "")
      return false;
   if(InpContextReverseDirections != "")
   {
      if(direction == OB_BUY && StringFind(InpContextReverseDirections, "buy") < 0)
         return false;
      if(direction == OB_SELL && StringFind(InpContextReverseDirections, "sell") < 0)
         return false;
   }
   if(InpContextReverseMaxRisk > 0 && risk_price > InpContextReverseMaxRisk)
      return false;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(!IsHourBlocked(InpContextReverseHours, dt.hour))
      return false;
   if(direction == OB_SELL &&
      (InpContextReverseSellEarlyDayMax > 0 || InpContextReverseSellLateDayMin > 0))
   {
      bool in_sell_day = false;
      if(InpContextReverseSellEarlyDayMax > 0 && dt.day <= InpContextReverseSellEarlyDayMax)
         in_sell_day = true;
      if(InpContextReverseSellLateDayMin > 0 && dt.day >= InpContextReverseSellLateDayMin)
         in_sell_day = true;
      if(!in_sell_day)
         return false;
   }

   if(InpContextReverseMaxMonthStartBalance > 0)
   {
      SyncMonthlyRiskState();
      if(g_monthly_start_balance <= 0 ||
         g_monthly_start_balance > InpContextReverseMaxMonthStartBalance)
         return false;
   }

   if(ref_price <= 0)
      ref_price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ref_price <= 0)
      ref_price = SymbolInfoDouble(_Symbol, SYMBOL_LAST);
   if(ref_price <= 0)
      return false;
   if(InpContextReverseMinPrice > 0 && ref_price < InpContextReverseMinPrice)
      return false;
   if(InpContextReverseMaxPrice > 0 && ref_price > InpContextReverseMaxPrice)
      return false;

   return true;
}

double ApplySignalTypePositionMultiplier(const OBZone &zone, double pos_mult)
{
   if(IsLooseSweepZone(zone))
      pos_mult *= InpLooseSweepPosMult;
   else if(zone.is_liquidity_sweep)
      pos_mult *= CfgSweepPosMult();
   if(zone.is_range_breakout)
      pos_mult *= InpRangeBreakoutPosMult;
   if(zone.is_htf_pullback)
      pos_mult *= InpHTFPullbackPosMult;
   return pos_mult;
}

double ApplyBalancePositionMultiplier(double pos_mult)
{
   if(CfgLowBalanceThreshold() <= 0 || CfgLowBalancePosMult() == 1.0)
      return pos_mult;
   if(AccountInfoDouble(ACCOUNT_BALANCE) < CfgLowBalanceThreshold())
      pos_mult *= CfgLowBalancePosMult();
   return pos_mult;
}

int g_monthly_risk_key = 0;
double g_monthly_start_balance = 0.0;
double g_monthly_peak_balance = 0.0;
int g_monthly_entry_count = 0;
bool g_monthly_entry_stopped = false;
bool g_monthly_loss_stopped = false;
bool g_monthly_profit_locked = false;

double g_runtime_start_balance = 0.0;
double g_runtime_peak_balance = 0.0;
int g_runtime_entry_count = 0;

bool UseSharedMonthlyGuard()
{
   return (InpSharedMonthlyGuard && StringLen(InpSharedMonthlyGuardKey) > 0);
}

void PrintSharedMonthlyDiag(string event_name)
{
   if(!InpSharedMonthlyGuardDebug || !UseSharedMonthlyGuard())
      return;

   Print("SHARED_GUARD event=", event_name,
         " key=", InpSharedMonthlyGuardKey,
         " version=", InpVersion,
         " symbol=", _Symbol,
         " month=", g_monthly_risk_key,
         " start=", DoubleToString(g_monthly_start_balance, 2),
         " peak=", DoubleToString(g_monthly_peak_balance, 2),
         " count=", g_monthly_entry_count,
         " entry_stopped=", g_monthly_entry_stopped ? 1 : 0,
         " loss_stopped=", g_monthly_loss_stopped ? 1 : 0,
         " profit_locked=", g_monthly_profit_locked ? 1 : 0);
}

string SharedMonthlyPrefix(int key)
{
   return "WT2_MONTH_" + InpSharedMonthlyGuardKey + "_" + IntegerToString(key);
}

void SaveSharedMonthlyState()
{
   if(!UseSharedMonthlyGuard() || g_monthly_risk_key <= 0)
      return;

   string prefix = SharedMonthlyPrefix(g_monthly_risk_key);
   GlobalVariableSet(prefix + "_start", g_monthly_start_balance);
   GlobalVariableSet(prefix + "_peak", g_monthly_peak_balance);
   GlobalVariableSet(prefix + "_count", g_monthly_entry_count);
   GlobalVariableSet(prefix + "_entry_stopped", g_monthly_entry_stopped ? 1.0 : 0.0);
   GlobalVariableSet(prefix + "_loss_stopped", g_monthly_loss_stopped ? 1.0 : 0.0);
   GlobalVariableSet(prefix + "_profit_locked", g_monthly_profit_locked ? 1.0 : 0.0);
}

void LoadSharedMonthlyState(int key)
{
   string prefix = SharedMonthlyPrefix(key);
   string start_key = prefix + "_start";

   if(!GlobalVariableCheck(start_key))
   {
      g_monthly_risk_key = key;
      g_monthly_start_balance = AccountInfoDouble(ACCOUNT_BALANCE);
      g_monthly_peak_balance = g_monthly_start_balance;
      g_monthly_entry_count = 0;
      g_monthly_entry_stopped = false;
      g_monthly_loss_stopped = false;
      g_monthly_profit_locked = false;
      SaveSharedMonthlyState();
      PrintSharedMonthlyDiag("init");
      return;
   }

   bool first_local_load = (key != g_monthly_risk_key);
   g_monthly_risk_key = key;
   g_monthly_start_balance = GlobalVariableGet(start_key);
   g_monthly_peak_balance = GlobalVariableGet(prefix + "_peak");
   g_monthly_entry_count = (int)GlobalVariableGet(prefix + "_count");
   g_monthly_entry_stopped = (GlobalVariableGet(prefix + "_entry_stopped") > 0.5);
   g_monthly_loss_stopped = (GlobalVariableGet(prefix + "_loss_stopped") > 0.5);
   g_monthly_profit_locked = (GlobalVariableGet(prefix + "_profit_locked") > 0.5);
   if(first_local_load)
      PrintSharedMonthlyDiag("load");
}

void SyncMonthlyRiskState()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int key = dt.year * 100 + dt.mon;
   if(UseSharedMonthlyGuard())
   {
      LoadSharedMonthlyState(key);
      return;
   }
   if(key != g_monthly_risk_key)
   {
      g_monthly_risk_key = key;
      g_monthly_start_balance = AccountInfoDouble(ACCOUNT_BALANCE);
      g_monthly_peak_balance = g_monthly_start_balance;
      g_monthly_entry_count = 0;
      g_monthly_entry_stopped = false;
      g_monthly_loss_stopped = false;
      g_monthly_profit_locked = false;
   }
}

void UpdateMonthlyPeakBalance(double balance)
{
   if(balance > g_monthly_peak_balance)
   {
      g_monthly_peak_balance = balance;
      SaveSharedMonthlyState();
   }
}

void RecordMonthlyEntry()
{
   SyncMonthlyRiskState();
   g_monthly_entry_count++;
   SaveSharedMonthlyState();
   PrintSharedMonthlyDiag("entry");
}

void SyncRuntimeRiskState()
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(g_runtime_start_balance <= 0.0)
   {
      g_runtime_start_balance = balance;
      g_runtime_peak_balance = balance;
   }
   if(balance > g_runtime_peak_balance)
      g_runtime_peak_balance = balance;
}

void RecordRuntimeEntry()
{
   SyncRuntimeRiskState();
   g_runtime_entry_count++;
}

bool IsRuntimeDefensiveModeActive()
{
   if(InpRuntimeDefensiveDrawdownPct <= 0.0)
      return false;

   SyncRuntimeRiskState();
   if(InpRuntimeDefensiveMinTrades > 0 &&
      g_runtime_entry_count < InpRuntimeDefensiveMinTrades)
      return false;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_balance = MathMin(balance, equity);
   if(InpRuntimeDefensiveMaxBalance > 0.0 &&
      risk_balance > InpRuntimeDefensiveMaxBalance)
      return false;
   if(g_runtime_peak_balance <= 0.0)
      return false;

   double stop_balance = g_runtime_peak_balance *
      (1.0 - InpRuntimeDefensiveDrawdownPct / 100.0);
   return (risk_balance <= stop_balance);
}

double ApplyRuntimePositionMultiplier(double pos_mult)
{
   if(InpRuntimeDefensivePosMult == 1.0 ||
      !IsRuntimeDefensiveModeActive())
      return pos_mult;
   if(InpRuntimeDefensivePosMult <= 0.0)
      return -1.0;
   return pos_mult * InpRuntimeDefensivePosMult;
}

// --- 自适应噪音门控: 权益回撤时自动切换到更严格的噪音参数 ---
bool IsAdaptiveNoiseGateDefensive()
{
   if(InpAdaptiveNoiseDrawdownPct <= 0.0)
      return false;
   if(!InpEnableTickNoiseGate)
      return false;

   SyncRuntimeRiskState();
   if(g_runtime_peak_balance <= 0.0)
      return false;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_balance = MathMin(balance, equity);

   // 回撤超过drawdownPct%触发防守; 恢复至recoveryPct%以内退出防守
   double enter_threshold = g_runtime_peak_balance *
      (1.0 - InpAdaptiveNoiseDrawdownPct / 100.0);
   double exit_threshold  = g_runtime_peak_balance *
      (1.0 - InpAdaptiveNoiseRecoveryPct / 100.0);

   // 无状态检查: 每tick独立判断, 回撤超过阈值立即防守, 恢复立即退出
   return (risk_balance <= enter_threshold);
}

double CfgTickNoiseGateMinDirRatio()
{
   if(IsAdaptiveNoiseGateDefensive() && InpAdaptiveNoiseDefMinDirRatio > 0.0)
      return InpAdaptiveNoiseDefMinDirRatio;
   return InpTickNoiseGateMinDirRatio;
}

double CfgTickNoiseGateMaxRangeATR()
{
   if(IsAdaptiveNoiseGateDefensive() && InpAdaptiveNoiseDefMaxRangeATR > 0.0)
      return InpAdaptiveNoiseDefMaxRangeATR;
   return InpTickNoiseGateMaxRangeATR;
}

// 自适应仓位乘数: 防守态衰减boost和MaxPosMult
double CfgAdaptiveBoostIn1HOB()
{
   double base = CfgBoostIn1HOB();
   if(IsAdaptiveNoiseGateDefensive() && InpAdaptiveNoiseDefBoostMult > 0.0 && base > 1.0)
      return 1.0 + (base - 1.0) * InpAdaptiveNoiseDefBoostMult;
   return base;
}
double CfgAdaptiveDeepEntryBoost()
{
   double base = InpDeepEntryBoost;
   if(IsAdaptiveNoiseGateDefensive() && InpAdaptiveNoiseDefBoostMult > 0.0 && base > 1.0)
      return 1.0 + (base - 1.0) * InpAdaptiveNoiseDefBoostMult;
   return base;
}
double CfgAdaptiveMaxPosMult()
{
   double base = CfgMaxPosMult();
   // 自适应噪音防守态衰减
   if(IsAdaptiveNoiseGateDefensive() && InpAdaptiveNoiseDefBoostMult > 0.0 && base > 1.0)
      base = 1.0 + (base - 1.0) * InpAdaptiveNoiseDefBoostMult;
   // ATR低波体制衰减(前向检测,不依赖交易结果)
   if(IsATRLowVolRegime() && InpATRRegimeLowMaxPosMult > 0.0 && InpATRRegimeLowMaxPosMult < base)
      base = InpATRRegimeLowMaxPosMult;
   return base;
}

// ATR体制检测: 基于市场微观结构的前向检测(不依赖交易结果)
// 比较当前ATR与历史平均ATR, 检测低波动体制
bool IsATRLowVolRegime()
{
   if(InpATRRegimePeriod <= 0)
      return false;

   int atr_handle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(atr_handle == INVALID_HANDLE)
      return false;

   // 当前ATR(最近1根bar)
   double atr_current[1];
   if(CopyBuffer(atr_handle, 0, 0, 1, atr_current) <= 0 || atr_current[0] <= 0)
      return false;

   // 历史平均ATR(过去InpATRRegimePeriod根bar的均值)
   double atr_hist[];
   int copied = CopyBuffer(atr_handle, 0, 1, InpATRRegimePeriod, atr_hist);
   if(copied < InpATRRegimePeriod / 2)  // 至少一半数据可用
      return false;

   double atr_sum = 0.0;
   for(int i = 0; i < copied; i++)
      atr_sum += atr_hist[i];
   double atr_avg = atr_sum / copied;
   if(atr_avg <= 0)
      return false;

   double ratio = atr_current[0] / atr_avg;
   return (ratio < InpATRRegimeLowThreshold);
}

// ATR自适应DTP触发: 低波体制降低DTP触发(更容易止盈)
double CfgATRDTPTriggerR()
{
   double base = CfgDTPTriggerR();
   if(IsATRLowVolRegime() && InpATRRegimeLowDTPTriggerR > 0.0)
      return InpATRRegimeLowDTPTriggerR;
   return base;
}

bool IsMonthlyDefensiveModeActive()
{
   if(InpMonthlyDefensiveLossPct <= 0 &&
      InpMonthlyDefensiveUntilProfitPct <= 0)
      return false;

   SyncMonthlyRiskState();
   if(g_monthly_start_balance <= 0)
      return false;
   if(InpMonthlyDefensiveMaxMonthStartBalance > 0 &&
      g_monthly_start_balance > InpMonthlyDefensiveMaxMonthStartBalance)
      return false;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_balance = MathMin(balance, equity);
   bool active = false;

   if(InpMonthlyDefensiveUntilProfitPct > 0)
   {
      double required_profit = g_monthly_start_balance *
         InpMonthlyDefensiveUntilProfitPct / 100.0;
      if(risk_balance - g_monthly_start_balance < required_profit)
         active = true;
   }

   if(!active && InpMonthlyDefensiveLossPct > 0)
   {
      if(InpMonthlyDefensiveMinTrades > 0 &&
         g_monthly_entry_count < InpMonthlyDefensiveMinTrades)
         return false;

      double defensive_balance = g_monthly_start_balance *
         (1.0 - InpMonthlyDefensiveLossPct / 100.0);
      active = (risk_balance <= defensive_balance);
   }

   double defensive_balance = g_monthly_start_balance *
      (1.0 - InpMonthlyDefensiveLossPct / 100.0);
   if(InpSharedMonthlyGuardDebug)
   {
      static datetime s_last_month_def_diag = 0;
      if(TimeCurrent() - s_last_month_def_diag >= 3600 &&
         g_monthly_entry_count >= InpMonthlyDefensiveMinTrades)
      {
         s_last_month_def_diag = TimeCurrent();
         Print("MONTH_DEF active=", active ? 1 : 0,
               " version=", InpVersion,
               " start=", DoubleToString(g_monthly_start_balance, 2),
               " risk_balance=", DoubleToString(risk_balance, 2),
               " threshold=", DoubleToString(defensive_balance, 2),
               " entries=", g_monthly_entry_count);
      }
   }
   return active;
}

bool CheckMonthlyLossStop(bool lock_stop)
{
   if(InpMonthlyLossStopPct <= 0)
      return false;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_balance = MathMin(balance, equity);

   SyncMonthlyRiskState();
   UpdateMonthlyPeakBalance(balance);

   bool loss_guard_enabled = (InpMonthlyGuardMinBalance <= 0 ||
      g_monthly_peak_balance >= InpMonthlyGuardMinBalance);
   if(!loss_guard_enabled || g_monthly_start_balance <= 0)
      return false;

   if(g_monthly_loss_stopped)
      return true;

   bool early_stop_check = (InpMonthlyEarlyLossStopTrades > 0 &&
      (g_monthly_entry_count == InpMonthlyEarlyLossStopTrades ||
       (InpMonthlyEarlyLossStopContinuous && g_monthly_entry_count >= InpMonthlyEarlyLossStopTrades)));
   if(early_stop_check)
   {
      bool early_guard_enabled = (InpMonthlyEarlyLossStopMinBalance <= 0 ||
         g_monthly_peak_balance >= InpMonthlyEarlyLossStopMinBalance);
      if(early_guard_enabled)
      {
         double early_stop_balance = g_monthly_start_balance * (1.0 - InpMonthlyEarlyLossStopPct / 100.0);
         if(risk_balance <= early_stop_balance)
         {
            if(lock_stop)
            {
               g_monthly_loss_stopped = true;
               g_monthly_entry_stopped = true;
               SaveSharedMonthlyState();
               PrintSharedMonthlyDiag("early_loss_stop");
            }
            return true;
         }
      }
   }

   double stop_balance = g_monthly_start_balance * (1.0 - InpMonthlyLossStopPct / 100.0);
   bool enough_trades = (InpMonthlyLossStopMinTrades <= 0 ||
      g_monthly_entry_count >= InpMonthlyLossStopMinTrades);
   if(enough_trades && risk_balance <= stop_balance)
   {
      if(lock_stop)
      {
         g_monthly_loss_stopped = true;
         g_monthly_entry_stopped = true;
         SaveSharedMonthlyState();
         PrintSharedMonthlyDiag("loss_stop");
      }
      return true;
   }

   return false;
}

bool IsMonthlyProfitLockEnabled()
{
   return (InpMonthlyProfitLockStartPct > 0 &&
      InpMonthlyProfitLockKeepPct > 0 &&
      (InpMonthlyProfitLockMinBalance <= 0 ||
         g_monthly_peak_balance >= InpMonthlyProfitLockMinBalance));
}

bool IsMonthlyProfitTargetStopSlotEnabled(
   double pct,
   double min_balance,
   double max_balance,
   string months
)
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return (pct > 0 &&
      IsMonthAllowed(months, dt.mon) &&
      (min_balance <= 0 || g_monthly_start_balance >= min_balance) &&
      (max_balance <= 0 || g_monthly_start_balance <= max_balance));
}

bool IsMonthlyProfitTargetStopEnabled()
{
   if(UseBTCProfile())
      return false;

   return (
      IsMonthlyProfitTargetStopSlotEnabled(
         InpMonthlyProfitTargetStopPct,
         InpMonthlyProfitTargetStopMinBalance,
         InpMonthlyProfitTargetStopMaxBalance,
         CfgMonthlyProfitTargetStopMonths()
      ) ||
      IsMonthlyProfitTargetStopSlotEnabled(
         InpMonthlyProfitTargetStop2Pct,
         InpMonthlyProfitTargetStop2MinBalance,
         InpMonthlyProfitTargetStop2MaxBalance,
         InpMonthlyProfitTargetStop2Months
      )
   );
}

double MonthlyProfitTargetStopPct()
{
   if(UseBTCProfile())
      return 0.0;

   if(IsMonthlyProfitTargetStopSlotEnabled(
      InpMonthlyProfitTargetStopPct,
      InpMonthlyProfitTargetStopMinBalance,
      InpMonthlyProfitTargetStopMaxBalance,
      CfgMonthlyProfitTargetStopMonths()
   ))
      return InpMonthlyProfitTargetStopPct;

   if(IsMonthlyProfitTargetStopSlotEnabled(
      InpMonthlyProfitTargetStop2Pct,
      InpMonthlyProfitTargetStop2MinBalance,
      InpMonthlyProfitTargetStop2MaxBalance,
      InpMonthlyProfitTargetStop2Months
   ))
      return InpMonthlyProfitTargetStop2Pct;

   return 0.0;
}

bool CheckMonthlyProfitTargetStop(bool lock_stop)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_balance = MathMin(balance, equity);

   SyncMonthlyRiskState();
   UpdateMonthlyPeakBalance(balance);

   double target_pct = MonthlyProfitTargetStopPct();
   if(target_pct <= 0 || g_monthly_start_balance <= 0)
      return false;

   double target_profit = g_monthly_start_balance * target_pct / 100.0;
   if(risk_balance - g_monthly_start_balance >= target_profit)
   {
      if(lock_stop)
      {
         g_monthly_profit_locked = true;
         g_monthly_entry_stopped = true;
         SaveSharedMonthlyState();
         PrintSharedMonthlyDiag("profit_target_stop");
      }
      return true;
   }

   return false;
}

bool CheckMonthlyProfitLockStop(bool lock_stop)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_balance = MathMin(balance, equity);

   SyncMonthlyRiskState();
   UpdateMonthlyPeakBalance(balance);

   if(!IsMonthlyProfitLockEnabled())
      return false;
   if(g_monthly_start_balance <= 0)
      return false;
   if(g_monthly_profit_locked)
      return true;

   double peak_profit = g_monthly_peak_balance - g_monthly_start_balance;
   double start_profit = g_monthly_start_balance * InpMonthlyProfitLockStartPct / 100.0;
   if(peak_profit < start_profit)
      return false;

   double current_profit = risk_balance - g_monthly_start_balance;
   double keep_profit = peak_profit * InpMonthlyProfitLockKeepPct / 100.0;
   if(current_profit < keep_profit)
   {
      if(lock_stop)
      {
         g_monthly_profit_locked = true;
         g_monthly_entry_stopped = true;
         SaveSharedMonthlyState();
         PrintSharedMonthlyDiag("profit_lock_stop");
      }
      return true;
   }

   return false;
}

bool PassMonthlyEntryGuard()
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   SyncMonthlyRiskState();
   UpdateMonthlyPeakBalance(balance);

   if(InpHighBalanceNoEntryMinMonthStartBalance > 0 &&
      g_monthly_start_balance >= InpHighBalanceNoEntryMinMonthStartBalance)
   {
      MqlDateTime dt;
      TimeToStruct(TimeCurrent(), dt);
      if(IsMonthAllowed(InpHighBalanceNoEntryMonths, dt.mon) &&
         StringLen(InpHighBalanceNoEntryMonths) > 0)
         return false;
   }

   bool profit_lock_enabled = IsMonthlyProfitLockEnabled();
   bool profit_target_enabled = IsMonthlyProfitTargetStopEnabled();

   if(InpMonthlyLossStopPct <= 0 && !profit_lock_enabled && !profit_target_enabled)
      return true;

   if(g_monthly_start_balance <= 0)
      return true;

   if(g_monthly_entry_stopped)
   {
      static datetime s_last_shared_block_diag = 0;
      if(TimeCurrent() - s_last_shared_block_diag >= 3600)
      {
         s_last_shared_block_diag = TimeCurrent();
         PrintSharedMonthlyDiag("entry_blocked");
      }
      return false;
   }

   if(CheckMonthlyLossStop(true))
      return false;

   if(CheckMonthlyProfitTargetStop(true))
      return false;

   if(CheckMonthlyProfitLockStop(true))
      return false;

   return true;
}

void LockMonthlyEntriesAfterFilteredBadCluster()
{
   if(!InpBadClusterFilteredMonthlyStop)
      return;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   SyncMonthlyRiskState();
   UpdateMonthlyPeakBalance(balance);

   if(InpBadClusterFilteredStopMinBalance > 0 &&
      g_monthly_peak_balance < InpBadClusterFilteredStopMinBalance)
      return;

   g_monthly_loss_stopped = true;
   g_monthly_entry_stopped = true;
   SaveSharedMonthlyState();
   PrintSharedMonthlyDiag("bad_cluster_stop");
}

double ApplyMonthlyPositionMultiplier(double pos_mult)
{
   if(InpMonthlyNegativePosMult == 1.0 &&
      (InpMonthlyWarmupProfitPct <= 0 || InpMonthlyWarmupPosMult == 1.0) &&
      ((InpMonthlyDefensiveLossPct <= 0 && InpMonthlyDefensiveUntilProfitPct <= 0) ||
       InpMonthlyDefensivePosMult == 1.0))
      return pos_mult;
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   SyncMonthlyRiskState();
   UpdateMonthlyPeakBalance(balance);
   if(InpMonthlyGuardMinBalance > 0 && g_monthly_peak_balance < InpMonthlyGuardMinBalance)
      return pos_mult;
   if(g_monthly_start_balance <= 0)
      return pos_mult;
   if(InpMonthlyWarmupProfitPct > 0 && InpMonthlyWarmupPosMult != 1.0)
   {
      double required_profit = g_monthly_start_balance * InpMonthlyWarmupProfitPct / 100.0;
      if(balance - g_monthly_start_balance < required_profit)
      {
         if(InpMonthlyWarmupPosMult <= 0)
            return -1.0;
         pos_mult *= InpMonthlyWarmupPosMult;
      }
   }
   if(balance < g_monthly_start_balance)
      pos_mult *= InpMonthlyNegativePosMult;
   if(IsMonthlyDefensiveModeActive())
   {
      if(InpMonthlyDefensivePosMult <= 0)
         return -1.0;
      pos_mult *= InpMonthlyDefensivePosMult;
   }
   return pos_mult;
}

double ApplyEntryQualityPositionMultiplier(const TradeSignal &signal, double risk_price, double pos_mult)
{
   if(CfgLateBounceSec() > 0 && CfgLateBounceMult() != 1.0 &&
      signal.bounce_seconds > CfgLateBounceSec())
      pos_mult *= CfgLateBounceMult();

   double bounce_sweet_min = CfgDefensiveBounceSweetMinPct();
   double bounce_sweet_max = CfgDefensiveBounceSweetMaxPct();
   double outside_bounce_sweet_mult = CfgDefensiveOutsideBounceSweetMult();
   if(bounce_sweet_min > 0 && bounce_sweet_max > bounce_sweet_min &&
      outside_bounce_sweet_mult != 1.0 && signal.bounce_ob_pct > 0)
   {
      if(signal.bounce_ob_pct < bounce_sweet_min ||
         signal.bounce_ob_pct > bounce_sweet_max)
      {
         if(outside_bounce_sweet_mult <= 0)
            return -1.0;
         pos_mult *= outside_bounce_sweet_mult;
      }
   }

   if(CfgBounceCloseWeakBodyPct() > 0 && CfgBounceCloseWeakBodyMult() != 1.0 &&
      signal.confirm_body_pct > 0 && signal.confirm_body_pct < CfgBounceCloseWeakBodyPct())
   {
      if(CfgBounceCloseWeakBodyMult() <= 0)
         return -1.0;
      pos_mult *= CfgBounceCloseWeakBodyMult();
   }

   if(CfgBadRiskMax() > CfgBadRiskMin() && CfgBadRiskMult() != 1.0 &&
      risk_price >= CfgBadRiskMin() && risk_price < CfgBadRiskMax())
      pos_mult *= CfgBadRiskMult();

   if(CfgLargeRiskMin() > 0 && CfgLargeRiskMult() != 1.0 &&
      risk_price >= CfgLargeRiskMin())
      pos_mult *= CfgLargeRiskMult();

   if(CfgShallowConfirmPosMin() > -999.0 && CfgShallowConfirmPosMult() != 1.0 &&
      signal.confirm_ob_pos > CfgShallowConfirmPosMin())
   {
      if(CfgShallowConfirmPosMult() <= 0)
         return -1.0;
      pos_mult *= CfgShallowConfirmPosMult();
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
   string signal_filter,
   const OBZone &zone,
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

   string filter = signal_filter;
   StringToLower(filter);
   if(filter != "" && filter != "all")
   {
      if(filter == "sweep" && !zone.is_liquidity_sweep)
         return pos_mult;
      if(filter == "range" && !zone.is_range_breakout)
         return pos_mult;
      if(filter == "htf_pullback" && !zone.is_htf_pullback)
         return pos_mult;
      if(filter == "htfpb" && !zone.is_htf_pullback)
         return pos_mult;
      if(filter == "ob" && (zone.is_liquidity_sweep || zone.is_range_breakout || zone.is_htf_pullback))
         return pos_mult;
   }

   if(mult <= 0)
      return -1.0;
   return pos_mult * mult;
}

double ApplyBadClusterPositionMultiplier(const OBZone &zone, const TradeSignal &signal, double risk_price, double pos_mult)
{
   if(InpBadClusterMinBalance > 0 || InpBadClusterOnlyMonthlyNegative)
   {
      double balance = AccountInfoDouble(ACCOUNT_BALANCE);
      if(InpBadClusterMinBalance > 0 && balance < InpBadClusterMinBalance)
         return pos_mult;

      if(InpBadClusterOnlyMonthlyNegative)
      {
         SyncMonthlyRiskState();
         if(g_monthly_start_balance <= 0 || balance >= g_monthly_start_balance)
            return pos_mult;
      }
   }

   pos_mult = ApplyOneBadClusterPositionMultiplier(
      InpBadCluster1Hours, InpBadCluster1RiskMin, InpBadCluster1RiskMax,
      InpBadCluster1ConfirmMin, InpBadCluster1ConfirmMax, InpBadCluster1Mult,
      InpBadCluster1Signal, zone,
      signal, risk_price, pos_mult);
   if(pos_mult < 0)
   {
      LockMonthlyEntriesAfterFilteredBadCluster();
      return pos_mult;
   }

   pos_mult = ApplyOneBadClusterPositionMultiplier(
      InpBadCluster2Hours, InpBadCluster2RiskMin, InpBadCluster2RiskMax,
      InpBadCluster2ConfirmMin, InpBadCluster2ConfirmMax, InpBadCluster2Mult,
      InpBadCluster2Signal, zone,
      signal, risk_price, pos_mult);
   if(pos_mult < 0)
   {
      LockMonthlyEntriesAfterFilteredBadCluster();
      return pos_mult;
   }

   pos_mult = ApplyOneBadClusterPositionMultiplier(
      InpBadCluster3Hours, InpBadCluster3RiskMin, InpBadCluster3RiskMax,
      InpBadCluster3ConfirmMin, InpBadCluster3ConfirmMax, InpBadCluster3Mult,
      InpBadCluster3Signal, zone,
      signal, risk_price, pos_mult);
   if(pos_mult < 0)
   {
      LockMonthlyEntriesAfterFilteredBadCluster();
      return pos_mult;
   }

   pos_mult = ApplyOneBadClusterPositionMultiplier(
      InpBadCluster4Hours, InpBadCluster4RiskMin, InpBadCluster4RiskMax,
      InpBadCluster4ConfirmMin, InpBadCluster4ConfirmMax, InpBadCluster4Mult,
      InpBadCluster4Signal, zone,
      signal, risk_price, pos_mult);
   if(pos_mult < 0)
   {
      LockMonthlyEntriesAfterFilteredBadCluster();
      return pos_mult;
   }

   pos_mult = ApplyOneBadClusterPositionMultiplier(
      InpBadCluster5Hours, InpBadCluster5RiskMin, InpBadCluster5RiskMax,
      InpBadCluster5ConfirmMin, InpBadCluster5ConfirmMax, InpBadCluster5Mult,
      InpBadCluster5Signal, zone,
      signal, risk_price, pos_mult);
   if(pos_mult < 0)
   {
      LockMonthlyEntriesAfterFilteredBadCluster();
      return pos_mult;
   }

   pos_mult = ApplyOneBadClusterPositionMultiplier(
      InpBadCluster6Hours, InpBadCluster6RiskMin, InpBadCluster6RiskMax,
      InpBadCluster6ConfirmMin, InpBadCluster6ConfirmMax, InpBadCluster6Mult,
      InpBadCluster6Signal, zone,
      signal, risk_price, pos_mult);
    if(pos_mult < 0)
       LockMonthlyEntriesAfterFilteredBadCluster();
    return pos_mult;
}

double ApplyStartupBadClusterPositionMultiplier(const OBZone &zone, const TradeSignal &signal, double risk_price, double pos_mult)
{
   if(InpStartupBadClusterMaxMonthStartBalance <= 0)
      return pos_mult;

   SyncMonthlyRiskState();
   if(g_monthly_start_balance <= 0 ||
      g_monthly_start_balance > InpStartupBadClusterMaxMonthStartBalance)
      return pos_mult;

   pos_mult = ApplyOneBadClusterPositionMultiplier(
      InpStartupBadCluster1Hours, InpStartupBadCluster1RiskMin, InpStartupBadCluster1RiskMax,
      InpStartupBadCluster1ConfirmMin, InpStartupBadCluster1ConfirmMax, InpStartupBadCluster1Mult,
      InpStartupBadCluster1Signal, zone,
      signal, risk_price, pos_mult);
   if(pos_mult < 0)
      return pos_mult;

   pos_mult = ApplyOneBadClusterPositionMultiplier(
      InpStartupBadCluster2Hours, InpStartupBadCluster2RiskMin, InpStartupBadCluster2RiskMax,
      InpStartupBadCluster2ConfirmMin, InpStartupBadCluster2ConfirmMax, InpStartupBadCluster2Mult,
      InpStartupBadCluster2Signal, zone,
      signal, risk_price, pos_mult);
   if(pos_mult < 0)
      return pos_mult;

   pos_mult = ApplyOneBadClusterPositionMultiplier(
      InpStartupBadCluster3Hours, InpStartupBadCluster3RiskMin, InpStartupBadCluster3RiskMax,
      InpStartupBadCluster3ConfirmMin, InpStartupBadCluster3ConfirmMax, InpStartupBadCluster3Mult,
      InpStartupBadCluster3Signal, zone,
      signal, risk_price, pos_mult);
   if(pos_mult < 0)
      return pos_mult;

   pos_mult = ApplyOneBadClusterPositionMultiplier(
      InpStartupBadCluster4Hours, InpStartupBadCluster4RiskMin, InpStartupBadCluster4RiskMax,
      InpStartupBadCluster4ConfirmMin, InpStartupBadCluster4ConfirmMax, InpStartupBadCluster4Mult,
      InpStartupBadCluster4Signal, zone,
      signal, risk_price, pos_mult);
   return pos_mult;
}

double ApplySweepContextPositionMultiplier(const OBZone &zone, const EAState &state,
                                           const TradeSignal &signal, double risk_price, double pos_mult)
{
   if(!zone.is_liquidity_sweep)
      return pos_mult;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   if(InpSweepAllowHours != "" && !IsHourBlocked(InpSweepAllowHours, dt.hour))
      return -1.0;
   if(IsHourBlocked(InpSweepNoHours, dt.hour))
      return -1.0;

   bool sweep_context_active = IsMonthAllowed(InpSweepContextMonths, dt.mon);
   if(sweep_context_active && InpSweepContextMaxDay > 0 && dt.day > InpSweepContextMaxDay)
      sweep_context_active = false;
   if(sweep_context_active && InpSweepContextMinMonthStartBalance > 0)
   {
      SyncMonthlyRiskState();
      if(g_monthly_start_balance < InpSweepContextMinMonthStartBalance)
         sweep_context_active = false;
   }

   if(sweep_context_active && IsHourBlocked(InpSweepContextNoHours, dt.hour))
      return -1.0;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(InpSweepMinBalance > 0 && balance < InpSweepMinBalance)
      return -1.0;
   if(InpSweepLowBalanceThreshold > 0 && balance < InpSweepLowBalanceThreshold &&
      InpSweepLowBalanceMult != 1.0)
   {
      if(InpSweepLowBalanceMult <= 0)
         return -1.0;
      pos_mult *= InpSweepLowBalanceMult;
   }
   if(InpSweepMonthlyNegativeMult != 1.0)
   {
      SyncMonthlyRiskState();
      if(g_monthly_start_balance > 0 && balance < g_monthly_start_balance)
      {
         if(InpSweepMonthlyNegativeMult <= 0)
            return -1.0;
         pos_mult *= InpSweepMonthlyNegativeMult;
      }
   }
   if(InpSweepMonthlyProfitStartPct > 0)
   {
      SyncMonthlyRiskState();
      if(g_monthly_start_balance > 0)
      {
         double required_profit = g_monthly_start_balance * InpSweepMonthlyProfitStartPct / 100.0;
         if(balance - g_monthly_start_balance < required_profit)
            return -1.0;
      }
   }

   if(InpSweepEarlyBounceSecMax > InpSweepEarlyBounceSecMin &&
      InpSweepEarlyBounceMult != 1.0 &&
      signal.bounce_seconds >= InpSweepEarlyBounceSecMin &&
      signal.bounce_seconds <= InpSweepEarlyBounceSecMax)
   {
      if(InpSweepEarlyBounceHours != "" && !IsHourBlocked(InpSweepEarlyBounceHours, dt.hour))
         return pos_mult;
      if(InpSweepEarlyBounceMult <= 0)
         return -1.0;
      pos_mult *= InpSweepEarlyBounceMult;
   }

   if(InpSweepBadRiskMax > InpSweepBadRiskMin &&
      risk_price >= InpSweepBadRiskMin && risk_price < InpSweepBadRiskMax &&
      InpSweepBadRiskMult != 1.0)
   {
      if(InpSweepBadRiskMult <= 0)
         return -1.0;
      pos_mult *= InpSweepBadRiskMult;
   }

   if(InpSweepBadAgeMaxBars > InpSweepBadAgeMinBars &&
      InpSweepBadAgeMult != 1.0)
   {
      int age = state.bar_count - zone.created_bar;
      if(age >= InpSweepBadAgeMinBars && age < InpSweepBadAgeMaxBars)
      {
         if(InpSweepBadAgeMult <= 0)
            return -1.0;
         pos_mult *= InpSweepBadAgeMult;
      }
   }

   return pos_mult;
}

double ApplyHTFPullbackContextPositionMultiplier(const OBZone &zone, const TradeSignal &signal,
                                                 double risk_price, double pos_mult)
{
   if(!zone.is_htf_pullback)
      return pos_mult;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   if(InpHTFPullbackAllowHours != "" && !IsHourBlocked(InpHTFPullbackAllowHours, dt.hour))
      return -1.0;
   if(IsHourBlocked(InpHTFPullbackNoHours, dt.hour))
      return -1.0;

   if(InpHTFPullbackRiskMax > InpHTFPullbackRiskMin &&
      (risk_price < InpHTFPullbackRiskMin || risk_price >= InpHTFPullbackRiskMax))
      return -1.0;

   if(signal.confirm_ob_pos < InpHTFPullbackConfirmMin ||
      signal.confirm_ob_pos >= InpHTFPullbackConfirmMax)
      return -1.0;

   if(InpHTFPullbackContextMult != 1.0)
   {
      if(InpHTFPullbackContextMult <= 0)
         return -1.0;
      pos_mult *= InpHTFPullbackContextMult;
   }

   return pos_mult;
}

double ApplyOBContextPositionMultiplier(const OBZone &zone, double pos_mult)
{
   if(zone.is_liquidity_sweep || zone.is_range_breakout || zone.is_htf_pullback)
      return pos_mult;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   if(InpOBPosMult != 1.0)
   {
      if(InpOBPosMultMinBalance > 0 && AccountInfoDouble(ACCOUNT_BALANCE) < InpOBPosMultMinBalance)
         return pos_mult;
      if(InpOBPosMult <= 0)
         return -1.0;
      pos_mult *= InpOBPosMult;
   }

   if(InpOBBadHours != "" && InpOBBadHourMult != 1.0 &&
      IsHourBlocked(InpOBBadHours, dt.hour))
   {
      if(InpOBBadHourMult <= 0)
         return -1.0;
      pos_mult *= InpOBBadHourMult;
   }

   if(InpLowBalanceOBBadHours == "" || InpLowBalanceOBBadHourMult == 1.0 ||
      InpLowBalanceOBBadMaxMonthStartBalance <= 0)
      return pos_mult;

   SyncMonthlyRiskState();
   if(g_monthly_start_balance <= 0 ||
      g_monthly_start_balance > InpLowBalanceOBBadMaxMonthStartBalance)
      return pos_mult;

   if(!IsMonthAllowed(InpLowBalanceOBBadMonths, dt.mon))
      return pos_mult;

   if(!IsHourBlocked(InpLowBalanceOBBadHours, dt.hour))
      return pos_mult;

   if(InpLowBalanceOBBadHourMult <= 0)
      return -1.0;
   return pos_mult * InpLowBalanceOBBadHourMult;
}

// ── HTF方向门控: 直接拦截强逆势入场(不经过仓位乘数链) ──────────
bool PassHTFDirectionGate(int direction)
{
   if(!CfgEnableHTFDirectionGate())
      return true;
   if(!CfgEnableHTFNetPushFilter() || CfgHTFNetPushMinATR() <= 0)
      return true;  // HTF过滤器未启用 → 放行

   int bars = MathMax(CfgHTFNetPushBars(), 1);
   int need = bars + InpATRPeriod + 1;
   ENUM_TIMEFRAMES tf = MinutesToTF(CfgHTFNetPushTF());

   MqlRates rates[];
   int count = CopyRates(_Symbol, tf, 1, need, rates);
   if(count < bars + 1)
      return true;

   double atr = CalcATR(rates, count, InpATRPeriod);
   if(atr <= 0)
      return true;

   int start = count - bars;
   double net_move = (rates[count - 1].close - rates[start].open) * direction;
   double net_atr = net_move / atr;

   // 强逆势(反向超过阈值) → 拦截
   if(net_atr <= -CfgHTFNetPushMinATR())
      return false;

   return true;
}

double ApplyHTFNetPushPositionMultiplier(int direction, double pos_mult)
{
   if(!CfgEnableHTFNetPushFilter() || CfgHTFNetPushMinATR() <= 0)
      return pos_mult;

   int bars = MathMax(CfgHTFNetPushBars(), 1);
   int need = bars + InpATRPeriod + 1;
   ENUM_TIMEFRAMES tf = MinutesToTF(CfgHTFNetPushTF());

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
   double mult = CfgHTFNetPushNeutralMult();

   if(net_atr >= CfgHTFNetPushMinATR())
      mult = CfgHTFNetPushAlignedMult();
   else if(net_atr <= -CfgHTFNetPushMinATR())
      mult = CfgHTFNetPushCounterMult();
   else
   {
      // 自适应防守: Neutral(无趋势震荡市)拦截。正常态保留(趋势市回调盈利)
      if(IsAdaptiveNoiseGateDefensive() && InpAdaptiveNoiseDefNeutralMult < 1.0)
         mult = InpAdaptiveNoiseDefNeutralMult;
   }

   if(mult <= 0)
      return -1.0;
   return pos_mult * mult;
}

// ── 双扫确认体制检测: 持久化状态供其他模块查询 ──────────────────────
// 双扫确认天然是市场体制检测器: 双方向LP被扫=震荡区间, 单方向=趋势
// 注意: 即使CfgDoubleSweepOnlyDefensive()=true, 体制检测仍运行(仅入场过滤受防守态限制)
static bool   g_double_sweep_regime_active = false;
static datetime g_double_sweep_regime_time = 0;

bool IsDoubleSweepRegime()
{
   if(!CfgEnableDoubleSweepConfirm())
      return false;
   // 体制状态在 CfgDoubleSweepWindowBars 内有效
   if(g_double_sweep_regime_time == 0)
      return false;
   int max_age_sec = CfgDoubleSweepWindowBars() * CfgBarTF() * 60;
   if((int)(TimeCurrent() - g_double_sweep_regime_time) > max_age_sec)
      return false;
   return g_double_sweep_regime_active;
}

// ── 双扫确认 (SMC路径B): 要求双方向LP都被扫荡后才允许入场 ──────────────
// 核心概念: 窄幅震荡市中, 价格需分别扫过区间上下限(双扫)后才形成真正的方向
// 只做双扫确认后的入场, 过滤区间中段的单向扫荡陷阱
// update_regime: false=跳过持久化体制状态更新(HTF路径不应覆盖主通道状态)
bool PassDoubleSweepConfirm(const OBZone &zones[], int zone_count, int bar_count, bool update_regime=true)
{
   if(!CfgEnableDoubleSweepConfirm())
   {
      if(update_regime) g_double_sweep_regime_active = false;
      return true;  // 功能未启用, 放行
   }

   // 防守态过滤: 仅在权益回撤时启用入场过滤(趋势月不受影响)
   // 但体制检测始终运行(IsDoubleSweepRegime不依赖防守态)
   bool only_defensive = CfgDoubleSweepOnlyDefensive() && !IsAdaptiveNoiseGateDefensive();

   int window_bars = CfgDoubleSweepWindowBars();
   if(window_bars <= 0)
   {
      if(update_regime) g_double_sweep_regime_active = false;
      return true;
   }

   int cutoff_bar = bar_count - window_bars;
   bool has_buy_sweep = false;   // 上方LP被扫(产生了sell方向的sweep OB)
   bool has_sell_sweep = false;  // 下方LP被扫(产生了buy方向的sweep OB)

   for(int i = 0; i < zone_count; i++)
   {
      if(!zones[i].is_liquidity_sweep) continue;
      if(zones[i].created_bar < cutoff_bar) continue;  // 过期
      if(zones[i].expired) continue;

      // sweep OB方向与扫荡方向相反: OB_BUY=下方LP被扫, OB_SELL=上方LP被扫
      if(zones[i].direction == OB_BUY)
         has_sell_sweep = true;   // buy方向sweep OB = 下方sell-stop被扫荡
      else
         has_buy_sweep = true;    // sell方向sweep OB = 上方buy-stop被扫荡
   }

   bool passed = (has_buy_sweep && has_sell_sweep);

   // 更新持久化体制状态(供IsDoubleSweepRegime查询)
   // HTF路径(update_regime=false)不应覆盖主通道状态
   if(update_regime)
   {
      g_double_sweep_regime_active = passed;
      g_double_sweep_regime_time = TimeCurrent();
   }

   // 入场过滤: 仅在非仅防守态或防守态激活时施加
   if(only_defensive)
      return true;  // 防守态要求但未触发 → 放行(趋势月)

   if(!passed && InpEnableEntryDebug)
      Print("DOUBLE_SWEEP skip: buy_sweep=", has_buy_sweep ? 1 : 0,
            " sell_sweep=", has_sell_sweep ? 1 : 0,
            " window=", window_bars, " bars");
   return passed;
}

// ── 双扫确认辅助: 当双扫+BlockSweepEntry启用时, 拒绝Sweep OB入场 ──────
// 逻辑: 双扫确认要求Sweep OB存在(探测双方向扫荡), 但Sweep OB信号质量低于普通OB
// 在震荡市中, 双扫完成后只允许普通OB入场, 过滤低质量Sweep信号
bool PassDoubleSweepSignalFilter(const OBZone &zone)
{
   if(!CfgEnableDoubleSweepConfirm() || !CfgDoubleSweepBlockSweepEntry())
      return true;  // 功能未启用, 放行

   // 仅在防守态时过滤(非防守态允许所有信号)
   if(CfgDoubleSweepOnlyDefensive() && !IsAdaptiveNoiseGateDefensive())
      return true;

   // 拦截Sweep OB入场(保留普通OB、Range Breakout、HTF Pullback)
   if(zone.is_liquidity_sweep)
   {
      if(InpEnableEntryDebug)
         Print("DOUBLE_SWEEP filter: block SWP entry ob=", zone.direction);
      return false;
   }

   return true;
}

bool PassOBReentryCooldown(const OBZone &zone)
{
   int max_entries = CfgMaxEntriesPerOB();
   if(max_entries < 1)
      max_entries = 1;
   if(zone.entry_count >= max_entries)
      return false;

   if(CfgOBReentryCooldownMin() <= 0 || zone.last_entry_time == 0)
      return true;
   return (TimeCurrent() - zone.last_entry_time >= CfgOBReentryCooldownMin() * 60);
}

double ApplyReentryPositionMultiplier(const OBZone &zone, double pos_mult)
{
   if(zone.entry_count <= 0 || InpReentryPosMult == 1.0)
      return pos_mult;
   if(InpReentryPosMult <= 0)
      return -1.0;
   return pos_mult * InpReentryPosMult;
}

double ApplyContinuationPositionMultiplier(const OBZone &zone, double pos_mult)
{
   if(!zone.is_continuation || CfgContinuationPosMult() == 1.0)
      return pos_mult;
   if(CfgContinuationPosMult() <= 0)
      return -1.0;
   return pos_mult * CfgContinuationPosMult();
}

bool PassContinuationAgeFilter(const OBZone &zone, const EAState &state, bool deep_entry)
{
   if(CfgFilterContAgeMaxBars() <= 0)
      return true;
   if(CfgFilterContAgeMaxBars() < CfgFilterContAgeMinBars())
      return true;
   if(!zone.is_continuation)
      return true;

   int age = state.bar_count - zone.created_bar;
   if(age < CfgFilterContAgeMinBars() || age > CfgFilterContAgeMaxBars())
      return true;
   if(CfgFilterContNonDeepOnly() && deep_entry)
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
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=expired/used");
      return false;
   }

   if(!PassOBReentryCooldown(zone))
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=cooldown");
      return false;
   }

   // FVG区通过EntryEngine确认后, 路由到FVG专属入场逻辑
   if(zone.is_fvg)
      return CheckFVGEntry(symbol, zone, signal.ob_index, state, signal);

   if(!PassDoubleSweepSignalFilter(zone))
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=double_sweep_signal_filter");
      return false;
   }

   if(!PassDirectionEntryHours(signal.direction, TimeCurrent()))
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=entry_hours");
      return false;
   }

   if(!PassMonthlyEntryGuard())
      return false;

   if(!PassEntryMomentumFilter(signal.direction))
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=momentum");
      return false;
   }

   // HTF方向门控: 强逆势直接拦截
   if(!PassHTFDirectionGate(signal.direction))
      return false;

   // ── HTF Range Fade: 大周期震荡高抛低吸 ──
   bool range_fade_active = false;
   ENUM_RANGE_POSITION range_pos = NO_RANGE;
   HTFRange active_range;

   if(CfgEnableRangeFade())
   {
      active_range = GetHTFRange(symbol);
      if(active_range.valid)
      {
         double current_price = (signal.direction == OB_BUY) ?
            SymbolInfoDouble(symbol, SYMBOL_ASK) : SymbolInfoDouble(symbol, SYMBOL_BID);
         range_pos = GetRangePosition(active_range, current_price);

         // 区间中部不交易(可选)
         if(CfgRangeNoMidTrades() && range_pos == RANGE_MIDDLE)
         {
            if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index,
               " dir=", signal.direction, " skip=range_mid");
            return false;
         }

         // 突破中观望
         if(range_pos == RANGE_BREAKING)
         {
            if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index,
               " dir=", signal.direction, " skip=range_breaking");
            return false;
         }

         // 方向反转: 上沿做空(高抛), 下沿做多(低吸)
         int faded = GetRangeFadeDirection(active_range, range_pos, signal.direction);
         if(faded != signal.direction)
         {
            if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index,
               " dir=", signal.direction, " range_fade_reverse to ", faded,
               " pos=", RangePositionToString(range_pos));
            signal.direction = faded;
            range_fade_active = true;
         }
      }
   }

   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double spread = GetSpread(symbol);

   double entry = (signal.direction == OB_BUY) ? ask : bid;
   double risk_price = MathAbs(entry - signal.sl);
   if(risk_price <= 0)
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=risk_price_zero");
      return false;
   }

   double confirm_entry = signal.entry;
   if(confirm_entry <= 0)
      confirm_entry = (signal.direction == OB_BUY) ? zone.high : zone.low;
   if(CfgMaxEntryOffsetR() > 0 && MathAbs(entry - confirm_entry) / risk_price > CfgMaxEntryOffsetR())
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=offset_r offset=", MathAbs(entry - confirm_entry) / risk_price, " max=", CfgMaxEntryOffsetR());
      return false;
   }

   if(!PassSpreadRatio(risk_price, spread))
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=spread_ratio risk=", risk_price, " spread=", spread);
      return false;
   }

   // Gap: Tick噪音门控 (使用Cfg访问器→自适应切换)
   if(!PassTickNoiseGate(signal.direction, symbol))
      return false;

   // EntryEngine确认后用真实可成交价重新过8-Gap，避免监控阶段和执行阶段口径漂移。
   double min_strength = GetDirectionMinStrength(signal.direction);
   if(min_strength > 0 && zone.strength < min_strength)
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=min_strength strength=", zone.strength, " min=", min_strength);
      return false;
   }

   if(InpMaxRiskATR > 0 && state.atr_value > 0 && risk_price > state.atr_value * InpMaxRiskATR)
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=max_risk_atr risk=", risk_price, " max=", state.atr_value * InpMaxRiskATR);
      return false;
   }

   if(InpMaxCounterRiskATR > 0 && state.atr_value > 0 &&
      zone.is_1h_aligned == false && risk_price > state.atr_value * InpMaxCounterRiskATR)
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=counter_risk_atr risk=", risk_price, " max=", state.atr_value * InpMaxCounterRiskATR);
      return false;
   }

   if(ShouldApplyContextReverse(signal.direction, entry, risk_price))
   {
      int rev_dir = (signal.direction == OB_BUY) ? OB_SELL : OB_BUY;
      double rev_entry = (rev_dir == OB_BUY) ? ask : bid;
      double rev_risk = risk_price * MathMax(InpContextReverseRiskMult, 0.1);
      signal.direction = rev_dir;
      signal.sl = (rev_dir == OB_BUY) ? rev_entry - rev_risk : rev_entry + rev_risk;
      signal.tp = (InpContextReverseTPR > 0) ?
         RToPrice(InpContextReverseTPR, rev_entry, rev_risk, rev_dir) : 0.0;
      entry = rev_entry;
      risk_price = rev_risk;
   }

   double pos_mult = signal.pos_mult;
   if(CfgEnableScoring())
   {
      double proximity_distance = MathAbs(bid - entry);
      double tp_est = CalcLiquiditySweepTP(zone, entry);
      if(tp_est == 0.0)
         tp_est = CalcHTFPullbackTP(zone, entry);
      if(tp_est == 0.0)
         tp_est = CalcOBHeightTP(zone, entry);
      if(tp_est == 0.0 && CfgDTPTriggerR() <= 0 && CfgFixedTPR() > 0)
         tp_est = RToPrice(CfgFixedTPR(), entry, risk_price, signal.direction);
      else if(tp_est == 0.0 && CfgEnableStateFilter() && state.market_state == 0 && state.target_price > 0)
         tp_est = state.target_price;
      else if(tp_est == 0.0)
         tp_est = RToPrice(2.0, entry, risk_price, signal.direction);
      double target_distance = MathAbs(tp_est - entry);
      int score = CalcSignalScore(zone, state, state.market_state,
                                  proximity_distance, risk_price, target_distance);
      if(CfgMinScore() > 0 && score < CfgMinScore())
      {
         if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=score score=", score, " min=", CfgMinScore());
         return false;
      }
      pos_mult = ScoreToMultiplier(score);
      if(pos_mult < 0)
      {
         if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=pos_mult_neg score=", score);
         return false;
      }
   }
   else
   {
      pos_mult = InpEnablePosMult ? CalcPositionMultiplier(zone) : 1.0;
   }
   double adaptive_deep_boost = CfgAdaptiveDeepEntryBoost();
   if(signal.deep_entry && adaptive_deep_boost > 1.0)
      pos_mult *= adaptive_deep_boost;
   pos_mult = ApplySignalTypePositionMultiplier(zone, pos_mult);
   pos_mult = ApplyDirectionPosMult(signal.direction, pos_mult);
   pos_mult = ApplyHourPositionMultiplier(pos_mult);
   pos_mult = ApplyContextFilterPositionMultiplier(signal.direction, pos_mult);
   pos_mult = ApplyEntryQualityPositionMultiplier(signal, risk_price, pos_mult);
   pos_mult = ApplyBadClusterPositionMultiplier(zone, signal, risk_price, pos_mult);
   pos_mult = ApplyStartupBadClusterPositionMultiplier(zone, signal, risk_price, pos_mult);
   pos_mult = ApplySweepContextPositionMultiplier(zone, state, signal, risk_price, pos_mult);
   pos_mult = ApplyHTFPullbackContextPositionMultiplier(zone, signal, risk_price, pos_mult);
   pos_mult = ApplyOBContextPositionMultiplier(zone, pos_mult);
   pos_mult = ApplyReentryPositionMultiplier(zone, pos_mult);
   pos_mult = ApplyContinuationPositionMultiplier(zone, pos_mult);
   if(pos_mult < 0)
      return false;
   pos_mult = ApplyHTFNetPushPositionMultiplier(signal.direction, pos_mult);
   pos_mult = ApplyBalancePositionMultiplier(pos_mult);
   pos_mult = ApplyMonthlyPositionMultiplier(pos_mult);
   pos_mult = ApplyRuntimePositionMultiplier(pos_mult);
   pos_mult = ApplyPositionMultiplierCap(pos_mult);
   if(!PassContinuationAgeFilter(zone, state, signal.deep_entry))
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=continuation_age");
      return false;
   }
   pos_mult = ApplyBuyNoH1PositionFilter(zone, signal.direction, pos_mult);
   if(pos_mult < 0)
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=buy_no_h1 pos_mult=", pos_mult);
      return false;
   }

   double final_lot = CalcEntryLot(symbol, CfgRiskPercent(), risk_price, pos_mult);
   final_lot = ApplyLotCap(final_lot);
   final_lot = ApplySignalTypeLotCap(zone, final_lot);
   final_lot = ApplyBalanceLotCap(final_lot);
   if(!PassMinRisk(final_lot, risk_price, symbol))
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=min_risk lot=", final_lot, " risk=", risk_price);
      return false;
   }

   double margin_required = 0;
   ENUM_ORDER_TYPE order_type = (signal.direction == OB_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(!OrderCalcMargin(order_type, symbol, final_lot, entry, margin_required))
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=margin_calc");
      return false;
   }

   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(margin_required > free_margin)
   {
      if(free_margin <= 0)
      {
         if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=free_margin_zero");
         return false;
      }
      final_lot = final_lot * (free_margin / margin_required) * 0.95;
      final_lot = ApplyLotCap(final_lot);
      final_lot = ApplySignalTypeLotCap(zone, final_lot);
      final_lot = ApplyBalanceLotCap(final_lot);
   }

   double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double lot_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(lot_step <= 0)
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=lot_step_zero");
      return false;
   }

   final_lot = MathFloor(final_lot / lot_step) * lot_step;
   if(final_lot < lot_min)
   {
      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " skip=lot_min final_lot=", final_lot, " min=", lot_min);
      return false;
   }
   if(final_lot > lot_max)
      final_lot = lot_max;

   // v11: 入场时按状态决定TP模式
   double tp = 0.0;
   if(zone.is_htf_pullback)
   {
      tp = CalcHTFPullbackTP(zone, entry);
      if(tp == 0.0 && CfgDTPTriggerR() <= 0 && CfgFixedTPR() > 0)
         tp = RToPrice(CfgFixedTPR(), entry, risk_price, signal.direction);
   }
   else if(zone.is_liquidity_sweep)
   {
      tp = CalcLiquiditySweepTP(zone, entry);
      // ★ Swing Capture: swing目标比sweep TP更远时优先用swing, 并跳过DTP
      if(CfgEnableStateFilter() && state.target_price > 0)
      {
         if((signal.direction == OB_BUY && state.target_price > entry) ||
            (signal.direction == OB_SELL && state.target_price < entry))
         {
            double swing_dist = MathAbs(state.target_price - entry);
            double sweep_dist = (tp > 0) ? MathAbs(tp - entry) : 0;
            if(swing_dist > sweep_dist)
            {
               tp = state.target_price;
               signal.htf_target = true;   // 跳过DTP截断
               signal.htf_partial_r = 0;   // 不部分平仓
            }
         }
      }
      if(tp == 0.0 && CfgDTPTriggerR() <= 0 && CfgFixedTPR() > 0)
         tp = RToPrice(CfgFixedTPR(), entry, risk_price, signal.direction);
   }
   else if(CfgEnableStateFilter() && state.market_state == 0)
   {
      // 震荡态: OBHeight TP优先，其次swing目标，最后固定TP
      tp = CalcOBHeightTP(zone, entry);
      if(tp == 0.0 && state.target_price > 0)
      {
         double swing_dist = MathAbs(state.target_price - entry);
         if(swing_dist > risk_price)
            tp = state.target_price;
      }
      if(tp == 0.0 && CfgFixedTPR() > 0)
         tp = RToPrice(CfgFixedTPR(), entry, risk_price, signal.direction);
   }
   else
   {
      // 趋势态: tp=0让DTP接管，除非没有DTP则用固定TP兜底
      if(CfgDTPTriggerR() <= 0 && CfgFixedTPR() > 0)
         tp = RToPrice(CfgFixedTPR(), entry, risk_price, signal.direction);
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

   // ── HTF Range Fade TP/SL覆盖 ──
   if(range_fade_active)
   {
      // 区间TP: 覆盖原TP（对侧边界或中轴）
      double range_tp = CalcRangeTP(active_range, range_pos, entry, signal.direction);
      if(range_tp > 0)
         signal.tp = range_tp;

      // 区间SL: 重新计算（边界外0.5ATR）
      double range_sl = CalcRangeSL(active_range, range_pos, signal.direction,
                                     state.atr_value);
      if(range_sl > 0)
      {
         signal.sl = range_sl;
         signal.risk_price = MathAbs(entry - range_sl);
      }

      // 区间仓位乘数
      if(CfgRangePosMult() > 0 && CfgRangePosMult() != 1.0)
      {
         signal.lot = NormalizeDouble(signal.lot * CfgRangePosMult(), 2);
         signal.pos_mult *= CfgRangePosMult();
      }

      // 区间最大手数限制
      if(CfgRangeMaxLot() > 0 && signal.lot > CfgRangeMaxLot())
         signal.lot = CfgRangeMaxLot();

      if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index,
         " range_tp=", signal.tp, " range_sl=", signal.sl,
         " pos=", RangePositionToString(range_pos),
         " confidence=", DoubleToString(active_range.confidence, 2));
   }

   PrintEntryDebug("entry_engine", zone, state, signal, entry, risk_price, spread, pos_mult,
                   CfgEnableScoring() ? CalcSignalScore(zone, state, state.market_state,
                                                      MathAbs(bid - entry), risk_price,
                                                      MathAbs(RToPrice(2.0, entry, risk_price, signal.direction) - entry))
                                    : -1);
   signal.comment = "WT " + InpVersion + " " + (signal.direction > 0 ? "B" : "S") +
                    (zone.is_range_breakout ? " RB" : "") +
                    (zone.is_htf_pullback ? " HTFPB" : "") +
                    (IsLooseSweepZone(zone) ? " LSWP" : "") +
                    (zone.is_liquidity_sweep ? " SWP" : "") +
                    (range_fade_active ? (" RG" + RangePositionToString(range_pos)) : "") +
                    " x" + DoubleToString(pos_mult, 1);

   if(InpEnableEntryDebug) Print("FINAL_DIAG z=", signal.ob_index, " dir=", signal.direction, " status=PASS lot=", final_lot, " entry=", entry, " sl=", signal.sl);
   return true;
}

int ScanSignals(string symbol, const OBZone &zones[], int zone_count,
                const EAState &state, TradeSignal &signals[], int max_signals)
{
   // 双扫确认门控: 要求在窗口内双方向LP都被扫荡
   if(!PassDoubleSweepConfirm(zones, zone_count, state.bar_count))
      return 0;

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

   if(CountPositions() >= CfgMaxConcurrent())
      return false;

   if(!PassOBReentryCooldown(zone))
      return false;

   if(!PassDoubleSweepSignalFilter(zone))
      return false;

   if(!PassDirectionEntryHours(zone.direction, TimeCurrent()))
      return false;

   if(!PassMonthlyEntryGuard())
      return false;

   if(!PassEntryMomentumFilter(zone.direction))
      return false;

   // HTF方向门控: 强逆势直接拦截
   if(!PassHTFDirectionGate(zone.direction))
      return false;

   // ── HTF Range Fade: 大周期震荡高抛低吸 ──
   bool range_fade_active2 = false;
   ENUM_RANGE_POSITION range_pos2 = NO_RANGE;
   int trade_direction = zone.direction;  // 默认用OB方向

   if(CfgEnableRangeFade())
   {
      HTFRange rng = GetHTFRange(symbol);
      if(rng.valid)
      {
         double cur_price = (zone.direction == OB_BUY) ?
            SymbolInfoDouble(symbol, SYMBOL_ASK) : SymbolInfoDouble(symbol, SYMBOL_BID);
         range_pos2 = GetRangePosition(rng, cur_price);

         // 区间中部不交易
         if(CfgRangeNoMidTrades() && range_pos2 == RANGE_MIDDLE)
            return false;

         // 突破中观望
         if(range_pos2 == RANGE_BREAKING)
            return false;

         // 方向反转
         int faded = GetRangeFadeDirection(rng, range_pos2, zone.direction);
         if(faded != zone.direction)
         {
            trade_direction = faded;
            range_fade_active2 = true;
         }
      }
   }

   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double spread = GetSpread(symbol);

   // FVG专属入场路径: 公允价值缺口回补后的交易逻辑
   if(zone.is_fvg)
      return CheckFVGEntry(symbol, zone, zone_idx, state, signal);

   if(!IsZoneTouched(zone, bid, ask))
      return false;

   if(!zone.is_range_breakout && !PassDoubleTouchFilter(zone))
      return false;

   // v9.8 态过滤: 趋势态硬过滤逆势
   if(CfgEnableStateFilter() && state.market_state != 0 && state.market_state != zone.direction)
      return false;

   double sl = 0;
   if(range_fade_active2)
   {
      // 区间fade: SL在区间边界外
      sl = CalcRangeSL(GetHTFRange(symbol), range_pos2, trade_direction, state.atr_value);
   }
   if(sl <= 0)
   {
      if(zone.direction == OB_BUY)
         sl = zone.low - state.atr_value * CfgSLBufferATR();
      else
         sl = zone.high + state.atr_value * CfgSLBufferATR();
   }

   double entry = (trade_direction == OB_BUY) ? ask : bid;
   double risk_price = MathAbs(entry - sl);

   if(risk_price <= 0)
      return false;

   if(!zone.is_range_breakout && !PassOffsetGuard(entry, risk_price, zone.direction, zone.mid, CfgMaxEntryOffsetR()))
      return false;

   if(!PassSpreadRatio(risk_price, spread))
      return false;

   // Gap: Tick噪音门控 (使用Cfg访问器→自适应切换)
   if(!PassTickNoiseGate(zone.direction, symbol))
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
   if(CfgEnableScoring())
   {
      double proximity_distance = MathAbs(bid - entry);
      double tp_est = CalcLiquiditySweepTP(zone, entry);
      if(tp_est == 0.0)
         tp_est = CalcHTFPullbackTP(zone, entry);
      if(tp_est == 0.0)
         tp_est = CalcOBHeightTP(zone, entry);
      if(tp_est == 0.0 && CfgDTPTriggerR() <= 0 && CfgFixedTPR() > 0)
         tp_est = RToPrice(CfgFixedTPR(), entry, risk_price, zone.direction);
      else if(tp_est == 0.0 && CfgEnableStateFilter() && state.market_state == 0 && state.target_price > 0)
         tp_est = state.target_price;
      else if(tp_est == 0.0)
         tp_est = RToPrice(2.0, entry, risk_price, zone.direction);
      double target_distance = MathAbs(tp_est - entry);
      score = CalcSignalScore(zone, state, state.market_state,
                              proximity_distance, risk_price, target_distance);
      if(CfgMinScore() > 0 && score < CfgMinScore())
         return false;
      pos_mult = ScoreToMultiplier(score);
      if(pos_mult < 0)
         return false;
   }
   else
   {
      pos_mult = InpEnablePosMult ? CalcPositionMultiplier(zone) : 1.0;
   }
   double entry_depth_pct = GetEffectiveEntryDepthPct();
   bool deep_entry = (entry_depth_pct > 0);
   if(entry_depth_pct > 0 && InpDeepEntryBoost > 1.0)
      pos_mult *= InpDeepEntryBoost;
   pos_mult = ApplySignalTypePositionMultiplier(zone, pos_mult);
   signal.bounce_seconds = 0;
   signal.bounce_ob_pct = 0.0;
   pos_mult = ApplyDirectionPosMult(zone.direction, pos_mult);
   pos_mult = ApplyHourPositionMultiplier(pos_mult);
   pos_mult = ApplyContextFilterPositionMultiplier(zone.direction, pos_mult);
   pos_mult = ApplyEntryQualityPositionMultiplier(signal, risk_price, pos_mult);
   pos_mult = ApplyBadClusterPositionMultiplier(zone, signal, risk_price, pos_mult);
   pos_mult = ApplyStartupBadClusterPositionMultiplier(zone, signal, risk_price, pos_mult);
   pos_mult = ApplySweepContextPositionMultiplier(zone, state, signal, risk_price, pos_mult);
   pos_mult = ApplyHTFPullbackContextPositionMultiplier(zone, signal, risk_price, pos_mult);
   pos_mult = ApplyOBContextPositionMultiplier(zone, pos_mult);
   pos_mult = ApplyReentryPositionMultiplier(zone, pos_mult);
   pos_mult = ApplyContinuationPositionMultiplier(zone, pos_mult);
   if(pos_mult < 0)
      return false;
   pos_mult = ApplyHTFNetPushPositionMultiplier(zone.direction, pos_mult);
   pos_mult = ApplyBalancePositionMultiplier(pos_mult);
   pos_mult = ApplyMonthlyPositionMultiplier(pos_mult);
   pos_mult = ApplyRuntimePositionMultiplier(pos_mult);
   pos_mult = ApplyPositionMultiplierCap(pos_mult);
   if(!PassContinuationAgeFilter(zone, state, deep_entry))
      return false;
   pos_mult = ApplyBuyNoH1PositionFilter(zone, zone.direction, pos_mult);
   if(pos_mult < 0)
      return false;
   double final_lot = CalcEntryLot(symbol, CfgRiskPercent(), risk_price, pos_mult);
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
   if(zone.is_htf_pullback && InpHTFPullbackTPMult > 0 && zone.range_height > 0)
      tp = CalcHTFPullbackTP(zone, entry);
   else if(zone.is_range_breakout && InpRangeBreakoutTPMult > 0 && zone.range_height > 0)
      tp = entry + zone.direction * zone.range_height * InpRangeBreakoutTPMult;
   else if(zone.is_liquidity_sweep)
   {
      tp = CalcLiquiditySweepTP(zone, entry);
      // ★ Swing Capture: swing目标比sweep TP更远时优先用swing, 并跳过DTP
      if(CfgEnableStateFilter() && state.target_price > 0)
      {
         if((signal.direction == OB_BUY && state.target_price > entry) ||
            (signal.direction == OB_SELL && state.target_price < entry))
         {
            double swing_dist = MathAbs(state.target_price - entry);
            double sweep_dist = (tp > 0) ? MathAbs(tp - entry) : 0;
            if(swing_dist > sweep_dist)
            {
               tp = state.target_price;
               signal.htf_target = true;
            }
         }
      }
      if(tp == 0.0 && CfgDTPTriggerR() <= 0 && CfgFixedTPR() > 0)
         tp = RToPrice(CfgFixedTPR(), entry, risk_price, zone.direction);
   }
   else if(CfgEnableStateFilter() && state.market_state == 0)
   {
      tp = CalcOBHeightTP(zone, entry);
      if(tp == 0.0 && state.target_price > 0)
      {
         double swing_dist = MathAbs(state.target_price - entry);
         if(swing_dist > risk_price)
            tp = state.target_price;
      }
      if(tp == 0.0 && CfgFixedTPR() > 0)
         tp = RToPrice(CfgFixedTPR(), entry, risk_price, zone.direction);
   }
   else
   {
      if(CfgDTPTriggerR() <= 0 && CfgFixedTPR() > 0)
         tp = RToPrice(CfgFixedTPR(), entry, risk_price, zone.direction);
   }

   signal.direction = trade_direction;
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

   // ── Range Fade TP/SL覆盖 (直接入场路径) ──
   if(range_fade_active2)
   {
      HTFRange rng2 = GetHTFRange(symbol);
      double range_tp = CalcRangeTP(rng2, range_pos2, entry, trade_direction);
      if(range_tp > 0) signal.tp = range_tp;
      if(CfgRangePosMult() > 0 && CfgRangePosMult() != 1.0)
      {
         signal.lot = NormalizeDouble(signal.lot * CfgRangePosMult(), 2);
         signal.pos_mult *= CfgRangePosMult();
      }
      if(CfgRangeMaxLot() > 0 && signal.lot > CfgRangeMaxLot())
         signal.lot = CfgRangeMaxLot();
   }

   PrintEntryDebug("direct", zone, state, signal, entry, risk_price, spread, pos_mult, score);
   signal.comment = "WT " + InpVersion + " " + (trade_direction > 0 ? "B" : "S") +
                    (zone.is_range_breakout ? " RB" : "") +
                    (zone.is_htf_pullback ? " HTFPB" : "") +
                    (IsLooseSweepZone(zone) ? " LSWP" : "") +
                    (zone.is_liquidity_sweep ? " SWP" : "") +
                    (range_fade_active2 ? (" RG" + RangePositionToString(range_pos2)) : "") +
                    " x" + DoubleToString(pos_mult, 1);

   return true;
}

double CalcPositionMultiplier(const OBZone &zone)
{
   double base = zone.strength;
   double fresh_mult = zone.is_fresh ? 1.5 : 1.0;
   double cont_mult = zone.is_continuation ? 1.3 : 1.0;
   double boost_1h = zone.is_1h_aligned ? CfgAdaptiveBoostIn1HOB() : 1.0;
   double ds = InpDSWeight ? zone.ds_weight : 1.0;

   return base * fresh_mult * cont_mult * boost_1h * ds;
}

bool IsInCooldown(const EAState &state)
{
   int bars = CfgCooldownBars();
   // 防守态: 若配置了防守冷卻且当前处于防守, 使用防守冷卻值
   if(bars <= 0 && InpAdaptiveNoiseDefCooldownBars > 0 && IsAdaptiveNoiseGateDefensive())
      bars = InpAdaptiveNoiseDefCooldownBars;

   if(bars <= 0)
      return false;
   return (state.bar_count - state.last_entry_bar) < bars;
}

#endif
