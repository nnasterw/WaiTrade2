#ifndef __WAITRADE_POSITION_MANAGER_MQH__
#define __WAITRADE_POSITION_MANAGER_MQH__

#include "Types.mqh"
#include "Config.mqh"
#include "MathUtils.mqh"
#include "TradeOps.mqh"
#include "MarketState.mqh"
#include "DecayDetector.mqh"
#include "RangeDetector.mqh"

void RegisterPosition(ulong ticket, int direction, double entry, double sl, double risk_price,
                      bool deep_entry,
                      int bounce_seconds, double confirm_ob_pos, double entry_pos_mult,
                      bool htf_target, double htf_partial_r, int htf_partial_pct,
                      bool trend_release,
                      bool failure_reverse,
                      PosTrack &tracks[], int &track_count,
                      int entry_family = ENTRY_FAMILY_ANY);
bool IsPositionStrong(const PosTrack &track, const EAState &state);
bool PassMonthlyEntryGuard();
bool CheckMonthlyLossStop(bool lock_stop);
bool CheckMonthlyProfitLockStop(bool lock_stop);
void MarkCloseAttemptFailed(PosTrack &track);
bool ShouldHoldDTPContinuation(const PosTrack &track);
void RecordFailureReentryState(int direction, int entry_family = ENTRY_FAMILY_ANY, double entry_price = 0.0);
bool PassFailureReentryConfirm(int direction, bool is_sweep = false, double pos_mult = 0.0,
                               int entry_family = ENTRY_FAMILY_ANY, double entry_price = 0.0);
bool IsFailureClusterReadyForReverse(int direction);
bool HasDTPHoldReverseBreak(const MqlRates &rates[], int count, int direction, double atr);
bool HasDTPHoldStrongReverseCandle(const MqlRates &rates[], int count, int direction,
                                   int lookback, double atr);
bool PassDTPHoldSignalQuality(const PosTrack &track);
bool ShouldApplyConditionalTrendRelease(const PosTrack &track);
bool IsDTPStrictHTFAligned(const PosTrack &track);
bool IsDTPStrictRangeQuality(const PosTrack &track, bool range_optional);

int g_failure_reentry_dir = 0;
int g_failure_reentry_count = 0;
datetime g_failure_reentry_time = 0;
int g_failure_reentry_family = ENTRY_FAMILY_ANY;
double g_failure_reentry_price = 0.0;
datetime g_post_win_cooldown_time = 0;
int g_post_win_cooldown_dir = 0;
int g_post_win_cooldown_family = ENTRY_FAMILY_ANY;
double g_post_win_cooldown_profit = 0.0;

string EntryFamilyName(int family)
{
    if(family == ENTRY_FAMILY_OB) return "OB";
    if(family == ENTRY_FAMILY_SWP) return "SWP";
    if(family == ENTRY_FAMILY_BOS) return "BOS";
    if(family == ENTRY_FAMILY_MBOS) return "MBOS";
    if(family == ENTRY_FAMILY_SDFLIP) return "SDFLIP";
    if(family == ENTRY_FAMILY_HTFPB) return "HTFPB";
    if(family == ENTRY_FAMILY_FVG) return "FVG";
    if(family == ENTRY_FAMILY_MTF) return "MTF";
    if(family == ENTRY_FAMILY_REV) return "REV";
    if(family == ENTRY_FAMILY_REVSWP) return "REVSWP";
    return "ANY";
}

bool IsFailureReentryFamilyFiltered()
{
    return StringLen(InpFailureReentryFamilyFilter) > 0;
}

bool IsFailureReentryFamilyAllowed(int family)
{
    if(!IsFailureReentryFamilyFiltered())
        return true;
    string filter = InpFailureReentryFamilyFilter;
    StringReplace(filter, " ", "");
    string needle = "," + EntryFamilyName(family) + ",";
    string haystack = "," + filter + ",";
    return (StringFind(haystack, needle) >= 0);
}

bool IsPostWinCooldownFamilySelected(int family)
{
    if(StringLen(InpPostWinCooldownFamilies) <= 0)
        return true;
    string filter = InpPostWinCooldownFamilies;
    StringReplace(filter, " ", "");
    string needle = "," + EntryFamilyName(family) + ",";
    string haystack = "," + filter + ",";
    return (StringFind(haystack, needle) >= 0);
}

bool IsConditionalTrendReleaseFamilySelected(int family)
{
    if(StringLen(InpConditionalOBTrendReleaseFamilies) <= 0)
        return true;
    string filter = InpConditionalOBTrendReleaseFamilies;
    StringReplace(filter, " ", "");
    string needle = "," + EntryFamilyName(family) + ",";
    string haystack = "," + filter + ",";
    return (StringFind(haystack, needle) >= 0);
}

bool HasPostWinCooldownStrongReverseCandle(const MqlRates &rates[], int count, int direction,
                                           int lookback, double atr)
{
    if(atr <= 0 || count < lookback + 2)
        return false;
    int used = MathMin(lookback, count - 1);
    for(int i = 1; i <= used; i++)
    {
        double reverse_body = (rates[i].open - rates[i].close) * direction;
        if(reverse_body >= atr * InpPostWinCooldownContinuationReverseBodyATR)
            return true;
    }
    return false;
}

bool HasPostWinCooldownStructureBreak(const MqlRates &rates[], int count, int direction, double atr)
{
    if(atr <= 0 || count < 8)
        return false;

    double buffer = atr * MathMax(InpPostWinCooldownContinuationBreakBufferATR, 0.0);
    double last_close = rates[1].close;
    double swing_high = 0.0;
    double swing_low = 999999.0;
    int limit = MathMin(count - 2, 18);

    for(int i = 2; i < limit; i++)
    {
        if(swing_high <= 0.0 && IsSwingHigh(rates, i, 1, count))
            swing_high = rates[i].high;
        if(swing_low >= 999999.0 && IsSwingLow(rates, i, 1, count))
            swing_low = rates[i].low;
    }
    if(swing_high <= 0.0)
    {
        for(int i = 2; i < MathMin(count, 12); i++)
            swing_high = MathMax(swing_high, rates[i].high);
    }
    if(swing_low >= 999999.0)
    {
        for(int i = 2; i < MathMin(count, 12); i++)
            swing_low = MathMin(swing_low, rates[i].low);
    }

    if(direction == OB_BUY)
        return (swing_high > 0.0 && last_close > swing_high + buffer);
    return (swing_low < 999999.0 && last_close < swing_low - buffer);
}

bool HasPostWinCooldownContinuation(int direction)
{
    int lookback = MathMax(1, InpPostWinCooldownContinuationBars);
    ENUM_TIMEFRAMES tf = MinutesToTF(InpPostWinCooldownContinuationTF > 0 ?
                                     InpPostWinCooldownContinuationTF : CfgBarTF());
    int need = MathMin(MathMax(lookback + 18, 28), 64);

    MqlRates rates[64];
    int count = CopyRates(_Symbol, tf, 0, need, rates);
    if(count < lookback + 8)
        return false;

    double atr = CalcATR(rates, count, 14);
    if(atr <= 0)
        return false;

    if(HasPostWinCooldownStrongReverseCandle(rates, count, direction, lookback, atr))
        return false;
    if(InpPostWinCooldownContinuationRequireBreak &&
       !HasPostWinCooldownStructureBreak(rates, count, direction, atr))
        return false;

    double net = DirectionalNetBodyATR_PM(rates, count, direction, lookback, atr);
    return (net >= InpPostWinCooldownContinuationMinNetATR ||
            CheckStrongMomentum(_Symbol, direction, rates, count));
}

void RecordPostWinCooldownIfNeeded(const PosTrack &track)
{
    if(InpPostWinCooldownMinProfit <= 0.0 || InpPostWinCooldownMin <= 0)
        return;
    if(!IsPostWinCooldownFamilySelected(track.entry_family))
        return;
    if(track.entry_balance <= 0.0)
        return;

    double profit = AccountInfoDouble(ACCOUNT_BALANCE) - track.entry_balance;
    if(profit < InpPostWinCooldownMinProfit)
        return;

    g_post_win_cooldown_time = TimeCurrent();
    g_post_win_cooldown_dir = track.direction;
    g_post_win_cooldown_family = track.entry_family;
    g_post_win_cooldown_profit = profit;
    if(InpEnableEntryDebug)
        Print("POST_WIN_COOLDOWN record family=", EntryFamilyName(track.entry_family),
              " dir=", track.direction,
              " profit=", DoubleToString(profit, 2),
              " min=", InpPostWinCooldownMin);
}

bool PassPostWinCooldown(int direction, int entry_family)
{
    if(InpPostWinCooldownMinProfit <= 0.0 || InpPostWinCooldownMin <= 0)
        return true;
    if(g_post_win_cooldown_time <= 0)
        return true;
    if(TimeCurrent() - g_post_win_cooldown_time > InpPostWinCooldownMin * 60)
        return true;
    if(!InpPostWinCooldownCrossFamily && g_post_win_cooldown_family != entry_family)
        return true;
    if(InpPostWinCooldownCrossFamily && !IsPostWinCooldownFamilySelected(entry_family))
        return true;
    if(InpPostWinCooldownSameDirection && g_post_win_cooldown_dir != direction)
        return true;
    if(InpPostWinCooldownRequireContinuation && HasPostWinCooldownContinuation(direction))
    {
        if(InpEnableEntryDebug)
            Print("POST_WIN_COOLDOWN continuation pass family=", EntryFamilyName(entry_family),
                  " dir=", direction,
                  " last_profit=", DoubleToString(g_post_win_cooldown_profit, 2));
        return true;
    }
    if(InpEnableEntryDebug)
        Print("POST_WIN_COOLDOWN block family=", EntryFamilyName(entry_family),
              " dir=", direction,
              " last_profit=", DoubleToString(g_post_win_cooldown_profit, 2));
    return false;
}

bool IsPostWinCooldownActiveForEntry(int direction, int entry_family)
{
    if(InpPostWinCooldownMinProfit <= 0.0 || InpPostWinCooldownMin <= 0)
        return false;
    if(g_post_win_cooldown_time <= 0)
        return false;
    if(TimeCurrent() - g_post_win_cooldown_time > InpPostWinCooldownMin * 60)
        return false;
    if(!InpPostWinCooldownCrossFamily && g_post_win_cooldown_family != entry_family)
        return false;
    if(InpPostWinCooldownCrossFamily && !IsPostWinCooldownFamilySelected(entry_family))
        return false;
    if(InpPostWinCooldownSameDirection && g_post_win_cooldown_dir != direction)
        return false;
    if(InpPostWinCooldownRequireContinuation && HasPostWinCooldownContinuation(direction))
        return false;
    return true;
}

// 余额阶梯仓位上限 (opt-in, 默认关闭)
// 在低余额阶段压低仓位, 避免低余额阶段产生 2+ 手单笔产生大亏月
double ApplyBalanceTierLotCap(double lot, int signal_type)
  {
      if(!InpEnableBalanceTierLotCap)
          return lot;
      double balance = AccountInfoDouble(ACCOUNT_BALANCE);
      if(balance >= InpBalanceTier1Threshold)
          return lot;
      double cap = InpBalanceTier1MaxLotSize;
      if(signal_type == 0) cap = InpBalanceTier1OBSignalMaxLotSize; // OB
      else if(signal_type == 1) cap = InpBalanceTier1SWPMaxLotSize;  // SWP
      else if(signal_type == 2) cap = InpBalanceTier1BOSMaxLotSize;  // BOS
      else cap = InpBalanceTier1OtherMaxLotSize;                    // Other
      if(lot > cap)
          return cap;
      return lot;
  }

double ApplyPostWinCooldownLotCap(double lot, int direction, int entry_family)
{
    if(InpPostWinCooldownMaxLotSize <= 0.0)
        return lot;
    if(!IsPostWinCooldownActiveForEntry(direction, entry_family))
        return lot;
    if(lot > InpPostWinCooldownMaxLotSize)
        return InpPostWinCooldownMaxLotSize;
    return lot;
}

bool IsDTPStrictExitFamily(int family)
{
    if(StringLen(InpDTPStrictExitFamilies) <= 0)
        return true;
    string filter = InpDTPStrictExitFamilies;
    StringReplace(filter, " ", "");
    string needle = "," + EntryFamilyName(family) + ",";
    string haystack = "," + filter + ",";
    return (StringFind(haystack, needle) >= 0);
}

bool IsWeakExitFamilySelected(int family)
{
    if(StringLen(InpWeakExitFamilyFilter) <= 0)
        return true;
    string filter = InpWeakExitFamilyFilter;
    StringReplace(filter, " ", "");
    string needle = "," + EntryFamilyName(family) + ",";
    string haystack = "," + filter + ",";
    return (StringFind(haystack, needle) >= 0);
}

bool IsStructureHoldFamilySelected(int family)
{
    if(StringLen(InpStructureHoldFamilies) <= 0)
        return true;
    string filter = InpStructureHoldFamilies;
    StringReplace(filter, " ", "");
    string needle = "," + EntryFamilyName(family) + ",";
    string haystack = "," + filter + ",";
    return (StringFind(haystack, needle) >= 0);
}

bool IsWeakExitFamilyOverride(int family)
{
    if(StringLen(InpWeakExitFamilyFilter) <= 0 || InpWeakExitFamilyMinR <= 0.0)
        return false;
    return IsWeakExitFamilySelected(family);
}

void RecordFailureReentryState(int direction, int entry_family = ENTRY_FAMILY_ANY, double entry_price = 0.0)
{
    if(!InpEnableFailureReentryConfirm)
        return;
    if(direction == 0)
        return;
    if(!IsFailureReentryFamilyAllowed(entry_family))
        return;

    bool same_bucket = (g_failure_reentry_dir == direction);
    if(IsFailureReentryFamilyFiltered())
        same_bucket = same_bucket && (g_failure_reentry_family == entry_family);

    if(same_bucket)
        g_failure_reentry_count++;
    else
    {
        g_failure_reentry_dir = direction;
        g_failure_reentry_family = entry_family;
        g_failure_reentry_count = 1;
    }
    if(entry_price > 0.0)
        g_failure_reentry_price = entry_price;
    g_failure_reentry_time = TimeCurrent();
}

void ClearFailureReentryState(int direction)
{
    if(direction == 0 || g_failure_reentry_dir == direction)
    {
        g_failure_reentry_dir = 0;
        g_failure_reentry_count = 0;
        g_failure_reentry_time = 0;
        g_failure_reentry_family = ENTRY_FAMILY_ANY;
        g_failure_reentry_price = 0.0;
    }
}

void ClearFailureReentryStateOnWin(int direction, double current_r)
{
    if(InpFailureReentryClearWinR < 0.0)
        return;
    if(current_r >= InpFailureReentryClearWinR)
        ClearFailureReentryState(direction);
}

bool HasFailureReentryStrongReverseCandle(const MqlRates &rates[], int count, int direction,
                                          int lookback, double atr)
{
    if(atr <= 0 || count < lookback + 2)
        return false;
    int used = MathMin(lookback, count - 1);
    for(int i = 1; i <= used; i++)
    {
        double reverse_body = (rates[i].open - rates[i].close) * direction;
        if(reverse_body >= atr * InpFailureReentryReverseBodyATR)
            return true;
    }
    return false;
}

bool HasFailureReentryStructureBreak(const MqlRates &rates[], int count, int direction, double atr)
{
    if(atr <= 0 || count < 8)
        return false;

    double buffer = atr * MathMax(InpFailureReentryBreakBufferATR, 0.0);
    double last_close = rates[1].close;
    double swing_high = 0.0;
    double swing_low = 999999.0;
    int pivot = MathMax(1, MathMin(InpFailureReentryStructurePivotBars, 4));
    int limit = MathMin(count - pivot, MathMax(pivot + 2, InpFailureReentryStructureLookbackBars));

    for(int i = pivot + 1; i < limit; i++)
    {
        if(swing_high <= 0.0 && IsSwingHigh(rates, i, pivot, count))
            swing_high = rates[i].high;
        if(swing_low >= 999999.0 && IsSwingLow(rates, i, pivot, count))
            swing_low = rates[i].low;
        if(swing_high > 0.0 && swing_low < 999999.0)
            break;
    }

    if(swing_high <= 0.0)
    {
        for(int i = 2; i < MathMin(count, 12); i++)
            swing_high = MathMax(swing_high, rates[i].high);
    }
    if(swing_low >= 999999.0)
    {
        for(int i = 2; i < MathMin(count, 12); i++)
            swing_low = MathMin(swing_low, rates[i].low);
    }

    if(direction == OB_BUY)
        return (swing_high > 0.0 && last_close > swing_high + buffer);
    return (swing_low < 999999.0 && last_close < swing_low - buffer);
}

bool HasFailureReentryContinuation(int direction)
{
    int lookback = MathMax(1, InpFailureReentryConfirmBars);
    ENUM_TIMEFRAMES tf = MinutesToTF(InpFailureReentryConfirmTF);
    int need = MathMin(MathMax(MathMax(lookback + 16, InpFailureReentryStructureLookbackBars + 8), 24), 64);

    MqlRates rates[64];
    int count = CopyRates(_Symbol, tf, 0, need, rates);
    if(count < lookback + 2)
        return false;

    double atr = CalcATR(rates, count, 14);
    if(atr <= 0)
        return false;

    double net = 0.0;
    for(int i = 1; i <= lookback; i++)
        net += (rates[i].close - rates[i].open) * direction;
    if(net / atr < InpFailureReentryConfirmMinATR)
        return false;

    if(InpFailureReentryBlockStrongReverse &&
       HasFailureReentryStrongReverseCandle(rates, count, direction, lookback, atr))
        return false;
    if(InpFailureReentryBlockReverseBreak &&
       HasFailureReentryStructureBreak(rates, count, -direction, atr))
        return false;
    if(InpFailureReentryRequireStructureBreak &&
       !HasFailureReentryStructureBreak(rates, count, direction, atr))
        return false;
    return true;
}

bool PassFailureReentryConfirm(int direction, bool is_sweep = false, double pos_mult = 0.0,
                               int entry_family = ENTRY_FAMILY_ANY, double entry_price = 0.0)
{
    if(!InpEnableFailureReentryConfirm)
        return true;
    if(direction == 0)
        return true;
    if(!IsFailureReentryFamilyAllowed(entry_family))
        return true;
    if(g_failure_reentry_dir != direction)
        return true;
    if(IsFailureReentryFamilyFiltered() && g_failure_reentry_family != entry_family)
        return true;
    if(g_failure_reentry_count < MathMax(1, InpFailureReentryConfirmLosses))
        return true;
    if(InpFailureReentryBlockOBOnly && is_sweep)
        return true;
    if(InpFailureReentryBlockMinPosMult > 0.0 && pos_mult < InpFailureReentryBlockMinPosMult)
        return true;
    if(InpFailureReentryConfirmMaxAgeMin > 0 &&
       g_failure_reentry_time > 0 &&
       TimeCurrent() - g_failure_reentry_time > InpFailureReentryConfirmMaxAgeMin * 60.0)
    {
        ClearFailureReentryState(direction);
        return true;
    }
    if(InpFailureReentryBlockMin > 0)
    {
        if(g_failure_reentry_time > 0 &&
           TimeCurrent() - g_failure_reentry_time < InpFailureReentryBlockMin * 60.0)
            return false;
        ClearFailureReentryState(direction);
        return true;
    }
    return HasFailureReentryContinuation(direction);
}

bool IsFailureClusterReadyForReverse(int direction)
{
    if(!InpEnableFailureReentryConfirm)
        return false;
    if(direction == 0)
        return false;
    if(g_failure_reentry_dir != -direction)
        return false;
    if(g_failure_reentry_count < MathMax(1, InpFailureReentryConfirmLosses))
        return false;
    if(InpFailureReentryConfirmMaxAgeMin > 0 &&
       g_failure_reentry_time > 0 &&
       TimeCurrent() - g_failure_reentry_time > InpFailureReentryConfirmMaxAgeMin * 60.0)
    {
        ClearFailureReentryState(g_failure_reentry_dir);
        return false;
    }
    return HasFailureReentryContinuation(direction);
}

bool CloseAllForMonthlyReason(PosTrack &tracks[], int &track_count, const string reason)
{
    bool closed_any = false;
    for(int i = track_count - 1; i >= 0; i--)
    {
        if(tracks[i].ticket == 0) continue;
        if(!PositionSelectByTicket(tracks[i].ticket))
            continue;

        if(ClosePosition(tracks[i].ticket, reason))
            closed_any = true;
        else
            MarkCloseAttemptFailed(tracks[i]);
    }
    return closed_any;
}

bool CloseAllForMonthlyStop(PosTrack &tracks[], int &track_count)
{
    return CloseAllForMonthlyReason(tracks, track_count, "monthly_stop");
}

string StrongAddOnFamilyName(int family)
{
    if(family == ENTRY_FAMILY_BOS) return "BOS";
    if(family == ENTRY_FAMILY_HTFPB) return "HTFPB";
    if(family == ENTRY_FAMILY_SWP) return "SWP";
    if(family == ENTRY_FAMILY_OB) return "OB";
    if(family == ENTRY_FAMILY_REV) return "REV";
    if(family == ENTRY_FAMILY_REVSWP) return "REVSWP";
    if(family == ENTRY_FAMILY_FVG) return "FVG";
    if(family == ENTRY_FAMILY_MTF) return "MTF";
    return "ANY";
}

bool IsStrongAddOnFamilyAllowed(int family)
{
    if(StringLen(InpStrongAddOnFamilies) <= 0)
        return true;
    string csv = "," + InpStrongAddOnFamilies + ",";
    StringToUpper(csv);
    string name = "," + StrongAddOnFamilyName(family) + ",";
    return StringFind(csv, name) >= 0;
}

bool IsStrongAddOnDirectionAllowed(int direction)
{
    if(StringLen(InpStrongAddOnDirections) <= 0)
        return true;
    string csv = "," + InpStrongAddOnDirections + ",";
    StringToUpper(csv);
    string name = (direction > 0) ? ",BUY," : ",SELL,";
    return StringFind(csv, name) >= 0;
}

bool OpenStrongAddOn(PosTrack &track, const EAState &state,
                     PosTrack &tracks[], int &track_count)
{
    if(!InpEnableStrongAddOn) return false;
    if(!PassMonthlyEntryGuard()) return false;
    if(InpStrongAddOnMaxCount <= 0) return false;
    if(track.failure_reverse || track.strong_addon) return false;
    if(track.addon_count >= InpStrongAddOnMaxCount) return false;
    if(!IsStrongAddOnFamilyAllowed(track.entry_family)) return false;
    if(!IsStrongAddOnDirectionAllowed(track.direction)) return false;
    if(track_count >= MAX_POSITIONS) return false;
    if(CountPositions() >= CfgMaxConcurrent()) return false;
    if(!PositionSelectByTicket(track.ticket)) return false;
    if(!IsPositionStrong(track, state)) return false;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    double trigger_r = InpStrongAddOnTriggerR + track.addon_count * InpStrongAddOnStepR;
    if(current_r < trigger_r)
        return false;

    string symbol = _Symbol;
    double spread = GetSpread(symbol);
    double risk = track.risk_price * MathMax(InpStrongAddOnRiskMult, 0.1);
    if(risk <= 0)
        return false;
    if(spread > 0 && risk / spread < InpStrongAddOnMinSpreadRatio)
        return false;

    double source_volume = PositionGetDouble(POSITION_VOLUME);
    double lot = source_volume * MathMax(InpStrongAddOnLotMult, 0.1);
    if(InpStrongAddOnUseRiskLot)
    {
        double risk_pct = (InpStrongAddOnRiskPercent > 0.0) ? InpStrongAddOnRiskPercent : CfgRiskPercent();
        double pos_mult = MathMax(InpStrongAddOnLotMult, 0.1);
        lot = CalcEntryLot(symbol, risk_pct, risk, pos_mult);
    }
    double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    double lot_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
    if(lot_step <= 0)
        return false;
    lot = MathFloor(lot / lot_step) * lot_step;
    if(lot < lot_min)
        return false;
    if(InpStrongAddOnMaxLotSize > 0 && lot > InpStrongAddOnMaxLotSize)
        lot = InpStrongAddOnMaxLotSize;
    if(CfgMaxLotSize() > 0 && lot > CfgMaxLotSize())
        lot = CfgMaxLotSize();
    lot = ApplyBalanceTierLotCap(lot, track.entry_family);
    if(lot > lot_max)
        lot = lot_max;

    double order_price = (track.direction > 0) ? SymbolInfoDouble(symbol, SYMBOL_ASK)
                                               : SymbolInfoDouble(symbol, SYMBOL_BID);
    double sl = (track.direction > 0) ? order_price - risk : order_price + risk;
    double current_sl = PositionGetDouble(POSITION_SL);
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    if(current_sl > 0)
    {
        if(track.direction > 0 && current_sl > sl && current_sl < order_price - point)
            sl = current_sl;
        else if(track.direction < 0 && current_sl < sl && current_sl > order_price + point)
            sl = current_sl;
    }
    risk = MathAbs(order_price - sl);
    if(risk <= 0)
        return false;

    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    request.action = TRADE_ACTION_DEAL;
    request.symbol = symbol;
    request.volume = lot;
    request.type = (track.direction > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    request.price = order_price;
    request.sl = BrokerStopFromVirtualSL(sl, order_price, risk, track.direction);
    request.tp = 0.0;
    request.magic = InpMagicNumber;
    request.comment = "WT " + InpVersion + " ADD";
    request.deviation = 20;
    request.type_filling = ORDER_FILLING_IOC;
    request.type_time = ORDER_TIME_GTC;

    if(!OrderSend(request, result))
        return false;
    if(result.retcode != TRADE_RETCODE_DONE)
        return false;

    double fill_price = result.price > 0 ? result.price : order_price;
    RegisterPosition(result.order, track.direction, fill_price, sl, risk,
                     track.deep_entry, track.bounce_seconds, track.confirm_ob_pos, track.entry_pos_mult,
                     track.htf_target, track.htf_partial_r, track.htf_partial_pct,
                     track.trend_release, false, tracks, track_count, track.entry_family);
    if(track_count > 0)
    {
        tracks[track_count - 1].open_bar = state.bar_count;
        tracks[track_count - 1].strong_addon = true;
    }
    track.addon_count++;
    Print("强势延续加仓: source=", track.ticket,
          " addon=", result.order,
          " r=", DoubleToString(current_r, 2),
          " lot=", DoubleToString(lot, 2));
    return true;
}

bool OpenFailureReverse(const PosTrack &track, const string reason,
                        double source_volume, int open_bar,
                        PosTrack &tracks[], int &track_count)
{
    if(!InpEnableFailureReverse) return false;
    if(!PassMonthlyEntryGuard()) return false;
    if(track.failure_reverse && !InpFailureReverseAllowChain) return false;
    if(reason == "early_loss" && !InpReverseOnEarlyLoss) return false;
    if(reason == "mfe_fail" && !InpReverseOnMFEFail) return false;
    if(reason == "no_mfe" && !InpReverseOnNoMFE) return false;
    if(track_count >= MAX_POSITIONS) return false;
    if(CountPositions() >= CfgMaxConcurrent()) return false;

    string symbol = _Symbol;
    int rev_dir = -track.direction;
    double risk = track.risk_price * MathMax(InpFailureReverseRiskMult, 0.1);
    if(risk <= 0) return false;

    double lot = source_volume * MathMax(InpFailureReverseLotMult, 0.1);
    double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    double lot_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
    if(lot_step <= 0) return false;
    lot = MathFloor(lot / lot_step) * lot_step;
    if(lot < lot_min) return false;
    if(CfgMaxLotSize() > 0 && lot > CfgMaxLotSize())
        lot = CfgMaxLotSize();
    lot = ApplyBalanceTierLotCap(lot, track.entry_family);
    if(lot > lot_max) lot = lot_max;

    double order_price = (rev_dir > 0) ? SymbolInfoDouble(symbol, SYMBOL_ASK)
                                      : SymbolInfoDouble(symbol, SYMBOL_BID);
    double sl = (rev_dir > 0) ? order_price - risk : order_price + risk;
    double tp = 0.0;
    if(InpFailureReverseTPR > 0)
        tp = RToPrice(InpFailureReverseTPR, order_price, risk, rev_dir);
    else if(CfgDTPTriggerR() <= 0 && CfgFixedTPR() > 0)
        tp = RToPrice(CfgFixedTPR(), order_price, risk, rev_dir);

    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    request.action = TRADE_ACTION_DEAL;
    request.symbol = symbol;
    request.volume = lot;
    request.type = (rev_dir > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    request.price = order_price;
    request.sl = BrokerStopFromVirtualSL(sl, order_price, risk, rev_dir);
    request.tp = tp;
    request.magic = InpMagicNumber;
    request.comment = "WT " + InpVersion + " REV " + reason;
    request.deviation = 20;
    request.type_filling = ORDER_FILLING_IOC;
    request.type_time = ORDER_TIME_GTC;

    if(!OrderSend(request, result))
        return false;
    if(result.retcode != TRADE_RETCODE_DONE)
        return false;

    double fill_price = result.price > 0 ? result.price : order_price;
    RegisterPosition(result.order, rev_dir, fill_price, sl, risk,
                     false, 0, 0.0, 1.0, false, 0, 0, false, true, tracks, track_count, ENTRY_FAMILY_REV);
    if(track_count > 0)
        tracks[track_count - 1].open_bar = open_bar;
    return true;
}

double CurrentR(const PosTrack &track)
{
    if(!PositionSelectByTicket(track.ticket)) return 0;
    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    return PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
}

void PrintExitDebug(string reason, const PosTrack &track, double current_r, const EAState &state)
{
    if(!InpEnableExitDebug) return;
    double peak_r = MathMax(track.peak_profit_r, track.dtp_peak_r);
    double giveback_r = peak_r - current_r;
    Print("EXIT_DIAG reason=", reason,
          " ticket=", track.ticket,
          " dir=", track.direction,
          " entry=", DoubleToString(track.entry_price, _Digits),
          " current_r=", DoubleToString(current_r, 2),
          " peak_r=", DoubleToString(peak_r, 2),
          " dtp_peak_r=", DoubleToString(track.dtp_peak_r, 2),
          " giveback_r=", DoubleToString(giveback_r, 2),
          " bars_held=", state.bar_count - track.open_bar,
          " last_sl=", track.last_sl_reason);
}

void PrintSLDebug(string reason, const PosTrack &track, double current_r, double new_sl)
{
    if(!InpEnableExitDebug) return;
    Print("SL_DIAG reason=", reason,
          " ticket=", track.ticket,
          " current_r=", DoubleToString(current_r, 2),
          " peak_r=", DoubleToString(track.peak_profit_r, 2),
          " new_sl=", DoubleToString(new_sl, _Digits));
}

void PrintPositionGoneDebug(const PosTrack &track)
{
    if(!InpEnableExitDebug) return;
    double peak_r = MathMax(track.peak_profit_r, track.dtp_peak_r);
    Print("POSITION_GONE_DIAG",
          " ticket=", track.ticket,
          " dir=", track.direction,
          " entry=", DoubleToString(track.entry_price, _Digits),
          " sl_initial=", DoubleToString(track.sl_initial, _Digits),
          " peak_r=", DoubleToString(peak_r, 2),
          " raw_peak_r=", DoubleToString(track.peak_profit_r, 2),
          " dtp_peak_r=", DoubleToString(track.dtp_peak_r, 2),
          " open_bar=", track.open_bar,
          " last_sl=", track.last_sl_reason,
          " be=", track.be_applied,
          " trail=", track.trail_level,
          " partial=", track.partial_closed,
          " dtp_partial=", track.dtp_partial_closed,
          " deep=", track.deep_entry,
          " htf=", track.htf_target,
          " rev=", track.failure_reverse,
          " addon=", track.strong_addon);
}

void RecordPassiveGoneForReentry(const PosTrack &track)
{
    if(!InpEnableFailureReentryConfirm || !InpFailureReentryRecordPassiveLoss)
        return;
    double peak_r = MathMax(track.peak_profit_r, track.dtp_peak_r);
    if(peak_r > InpFailureReentryPassiveLossMaxPeakR)
        return;
    if(track.be_applied || track.partial_closed || track.dtp_partial_closed ||
       track.trail_level > 0 || track.dtp_active)
        return;
    RecordFailureReentryState(track.direction, track.entry_family, track.entry_price);
}

bool ShouldSkipCloseAttempt(PosTrack &track)
{
    if(CfgCloseRetryCooldownSec() <= 0)
        return false;

    datetime now = TimeCurrent();
    return (track.last_close_attempt > 0 &&
            now - track.last_close_attempt < CfgCloseRetryCooldownSec());
}

void MarkCloseAttemptFailed(PosTrack &track)
{
    if(CfgCloseRetryCooldownSec() <= 0)
        return;
    datetime now = TimeCurrent();
    track.last_close_attempt = now;
}

bool IsSLImprovement(const PosTrack &track, double new_sl)
{
    double base_sl = track.virtual_sl > 0 ? track.virtual_sl : track.sl_initial;
    if(base_sl <= 0)
        return true;
    return (track.direction > 0) ? (new_sl > base_sl) : (new_sl < base_sl);
}

bool ApplyProtectiveSL(PosTrack &track, double new_sl, const string reason, double current_r)
{
    if(!PositionSelectByTicket(track.ticket)) return false;
    if(!IsSLImprovement(track, new_sl)) return true;

    if(UseVirtualSLMode())
    {
        double broker_sl = BrokerStopFromVirtualSL(new_sl, track.entry_price, track.risk_price, track.direction);
        if(!ModifySL(track.ticket, broker_sl))
            return false;
        track.virtual_sl = new_sl;
        track.virtual_sl_reason = reason;
        track.last_sl_reason = reason + "_virtual";
        PrintSLDebug(track.last_sl_reason, track, current_r, new_sl);
        return true;
    }

    if(!ModifySL(track.ticket, new_sl))
        return false;
    track.last_sl_reason = reason;
    PrintSLDebug(reason, track, current_r, new_sl);
    return true;
}

bool ActivateConditionalTrendRelease(PosTrack &track, double current_r, const EAState &state)
{
    if(!InpConditionalOBTrendRelease)
        return false;
    if(track.trend_release)
        return true;
    if(!IsConditionalTrendReleaseFamilySelected(track.entry_family))
        return false;
    if(!PassDTPHoldSignalQuality(track))
        return false;
    if(!ShouldApplyConditionalTrendRelease(track))
        return false;

    track.trend_release = true;
    bool modified = true;
    if(InpConditionalOBTrendReleaseDropTP)
        modified = ClearTP(track.ticket);

    if(InpEnableExitDebug)
        PrintExitDebug(modified ? "trend_release" : "trend_release_tp_fail",
                       track, current_r, state);
    return true;
}

bool ApplyConditionalBETrendRelease(PosTrack &track, double current_r,
                                    const EAState &state, double &be_lock_r)
{
    if(!InpConditionalOBTrendRelease || InpConditionalOBTrendReleaseBELockR <= -0.9)
        return false;
    if(!IsConditionalTrendReleaseFamilySelected(track.entry_family))
        return false;
    if(!PassDTPHoldSignalQuality(track))
        return false;
    if(!ShouldApplyConditionalTrendRelease(track))
        return false;

    be_lock_r = InpConditionalOBTrendReleaseBELockR;
    track.trend_release = true;
    if(InpEnableExitDebug)
        PrintExitDebug("be_trend_release", track, current_r, state);
    return true;
}

bool CheckVirtualSLBreach(PosTrack &track, const EAState &state)
{
    int breach_sec = CfgVirtualSLBreachSec();
    if(breach_sec <= 0) return false;
    if(track.virtual_sl <= 0) return false;
    if(!PositionSelectByTicket(track.ticket)) return false;

    double price = (track.direction > 0)
        ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
        : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    bool breached = (track.direction > 0) ? (price <= track.virtual_sl)
                                          : (price >= track.virtual_sl);

    if(!breached)
    {
        // Price recovered: breach was a wick → mark as VSL survivor
        if(track.virtual_sl_breach_start > 0)
            track.survived_vsl_breach = true;
        track.virtual_sl_breach_start = 0;
        return false;
    }

    datetime now = TimeCurrent();
    if(track.virtual_sl_breach_start == 0)
        track.virtual_sl_breach_start = now;

    if(now - track.virtual_sl_breach_start < breach_sec)
        return false;

    if(ShouldSkipCloseAttempt(track))
        return true;
    double current_r = CurrentR(track);
    string reason = "vsl_breach";
    PrintExitDebug(reason, track, current_r, state);
    if(!ClosePosition(track.ticket, reason))
        MarkCloseAttemptFailed(track);
    return true;
}

bool CheckVirtualSL(PosTrack &track, const EAState &state)
{
    if(!UseVirtualSLMode()) return false;
    if(track.virtual_sl <= 0) return false;
    if(state.bar_count <= track.open_bar) return false;
    if(!PositionSelectByTicket(track.ticket)) return false;

    int bars_needed = CfgVirtualSLConfirmBars();
    int tf_min = CfgVirtualSLConfirmTF() > 0 ? CfgVirtualSLConfirmTF() : CfgBarTF();
    ENUM_TIMEFRAMES tf = MinutesToTF(tf_min);
    MqlRates rates[];
    int count = CopyRates(_Symbol, tf, 1, bars_needed, rates);
    if(count < bars_needed)
        return false;

    double buffer = state.atr_value * CfgVirtualSLCloseBufferATR();
    for(int i = 0; i < bars_needed; i++)
    {
        if(track.direction > 0)
        {
            if(rates[i].close > track.virtual_sl - buffer)
                return false;
        }
        else
        {
            if(rates[i].close < track.virtual_sl + buffer)
                return false;
        }
    }

    if(ShouldSkipCloseAttempt(track))
        return true;

    double current_r = CurrentR(track);
    string reason = "vsl";
    if(track.virtual_sl_reason != "")
        reason = "vsl_" + track.virtual_sl_reason;
    PrintExitDebug(reason, track, current_r, state);
    if(!ClosePosition(track.ticket, reason))
        MarkCloseAttemptFailed(track);
    return true;
}

void ManagePositions(PosTrack &tracks[], int &track_count, const EAState &state)
{
    if(CheckMonthlyLossStop(true))
    {
        CloseAllForMonthlyStop(tracks, track_count);
        return;
    }
    // 盈利回吐锁只停止新入场，不强平已有趋势单。
    // 已有持仓继续交给 DTP/Trail/动能衰弱等结构化出场处理。
    CheckMonthlyProfitLockStop(true);

    for(int i = track_count - 1; i >= 0; i--)
    {
        if(tracks[i].ticket == 0) continue;

        if(!PositionSelectByTicket(tracks[i].ticket))
        {
            PrintPositionGoneDebug(tracks[i]);
            RecordPostWinCooldownIfNeeded(tracks[i]);
            for(int j = i; j < track_count - 1; j++)
                tracks[j] = tracks[j + 1];
            track_count--;
            continue;
        }

        if(CheckVirtualSLBreach(tracks[i], state))
            continue;
        if(CheckVirtualSL(tracks[i], state))
            continue;

        CheckEarlyLossCut(tracks[i], state, tracks, track_count);
        CheckMFEFailExit(tracks[i], state, tracks, track_count);
        CheckFastSL(tracks[i], state, tracks, track_count);
         CheckNoMFEExit(tracks[i], state, tracks, track_count);
        CheckPartialClose(tracks[i], state);
        CheckBreakeven(tracks[i], state);
        CheckStructureProfitLock(tracks[i], state);
        OpenStrongAddOn(tracks[i], state, tracks, track_count);
        // BD08: 结构止损持仓→跳过DTP/Trail, 由EA层M15结构管理
        if(tracks[i].use_structure_sl) continue;
        if(!(tracks[i].htf_target && InpHTFSkipTrail))
            CheckTrailing(tracks[i]);
        if(!(tracks[i].htf_target && InpHTFSkipDTP))
            CheckDTP(tracks[i], state);
        CheckTimeExit(tracks[i], state);
        CheckDecay(tracks[i], state);
    }
}

void SyncPositions(PosTrack &tracks[], int &track_count)
{
    for(int i = track_count - 1; i >= 0; i--)
    {
        bool found = false;
        for(int p = PositionsTotal() - 1; p >= 0; p--)
        {
            ulong ticket = PositionGetTicket(p);
            if(ticket == tracks[i].ticket)
            {
                found = true;
                break;
            }
        }
        if(!found)
        {
            PrintPositionGoneDebug(tracks[i]);
            RecordPostWinCooldownIfNeeded(tracks[i]);
            RecordPassiveGoneForReentry(tracks[i]);
            for(int j = i; j < track_count - 1; j++)
                tracks[j] = tracks[j + 1];
            track_count--;
        }
    }
}

void CheckMFEFailExit(PosTrack &track, const EAState &state,
                      PosTrack &tracks[], int &track_count)
{
    if(CfgMFEFailMinR() <= 0) return;
    if(track.skip_mfe_exits && (track.use_structure_sl || (CfgRangeHTFRejectContextEnabled() && track.htf_target))) return;
    if(track.be_applied || track.trail_level > 0 || track.dtp_active || track.partial_closed || track.dtp_partial_closed)
        return;
    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    track.peak_profit_r = MathMax(track.peak_profit_r, current_r);

    if(track.peak_profit_r < CfgMFEFailMinR())
        return;
    if(current_r > CfgMFEFailExitR())
        return;
    if(ShouldSkipCloseAttempt(track))
        return;

    double source_volume = PositionGetDouble(POSITION_VOLUME);
    PrintExitDebug("mfe_fail", track, current_r, state);
    if(ClosePosition(track.ticket, "mfe_fail"))
    {
        RecordFailureReentryState(track.direction, track.entry_family, track.entry_price);
        OpenFailureReverse(track, "mfe_fail", source_volume, state.bar_count, tracks, track_count);
    }
    else
        MarkCloseAttemptFailed(track);
}

void CheckEarlyLossCut(PosTrack &track, const EAState &state,
                       PosTrack &tracks[], int &track_count)
{
    if(InpEarlyLossCutR <= 0) return;
    if(track.be_applied || track.trail_level > 0 || track.dtp_active || track.partial_closed || track.dtp_partial_closed)
        return;
    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r > -InpEarlyLossCutR)
        return;
    if(ShouldSkipCloseAttempt(track))
        return;

    double source_volume = PositionGetDouble(POSITION_VOLUME);
    if(ClosePosition(track.ticket, "early_loss"))
    {
        RecordFailureReentryState(track.direction, track.entry_family, track.entry_price);
        OpenFailureReverse(track, "early_loss", source_volume, state.bar_count, tracks, track_count);
    }
    else
        MarkCloseAttemptFailed(track);
}

void CheckNoMFEExit(PosTrack &track, const EAState &state,
                    PosTrack &tracks[], int &track_count)
{
    if(CfgNoMFEExitBars() <= 0) return;
    if(track.skip_mfe_exits && (track.use_structure_sl || (CfgRangeHTFRejectContextEnabled() && track.htf_target))) return;
    if(track.be_applied || track.trail_level > 0 || track.dtp_active || track.partial_closed || track.dtp_partial_closed)
        return;
    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    track.peak_profit_r = MathMax(track.peak_profit_r, current_r);

    int bars_held = state.bar_count - track.open_bar;
    if(bars_held < CfgNoMFEExitBars())
        return;
    if(track.peak_profit_r >= CfgNoMFEMinPeakR())
        return;
    if(current_r > CfgNoMFEExitR())
        return;
    if(ShouldSkipCloseAttempt(track))
        return;

    double source_volume = PositionGetDouble(POSITION_VOLUME);
    PrintExitDebug("no_mfe", track, current_r, state);
    if(ClosePosition(track.ticket, "no_mfe"))
    {
        RecordFailureReentryState(track.direction, track.entry_family, track.entry_price);
        OpenFailureReverse(track, "no_mfe", source_volume, state.bar_count, tracks, track_count);
    }
    else
        MarkCloseAttemptFailed(track);
}

// BTC 快速SL防护 - 不受BE/Trail/DTP skip条件限制
void CheckFastSL(PosTrack &track, const EAState &state,
                PosTrack &tracks[], int &track_count)
{
    double min_peak = UseBTCProfile() ? InpBTCFastSLPeakR : 0.0;
    int bars = UseBTCProfile() ? InpBTCFastSLBars : 0;
    double exit_r = UseBTCProfile() ? InpBTCFastSLExitR : 0.0;
    if(min_peak <= 0 || bars <= 0) return;
    if(!PositionSelectByTicket(track.ticket)) return;
    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    track.peak_profit_r = MathMax(track.peak_profit_r, current_r);
    int bars_held = state.bar_count - track.open_bar;
    if(bars_held < bars) return;
    if(track.peak_profit_r >= min_peak) return;
    if(current_r > exit_r) return;
    if(ShouldSkipCloseAttempt(track)) return;
    double source_volume = PositionGetDouble(POSITION_VOLUME);
    if(ClosePosition(track.ticket, "fast_sl"))
    {
        PrintExitDebug("fast_sl", track, current_r, state);
        RecordFailureReentryState(track.direction, track.entry_family, track.entry_price);
    }
    else
        MarkCloseAttemptFailed(track);
}

void CheckPartialClose(PosTrack &track, const EAState &state)
{
    double partial_r = InpPartialCloseR;
    int partial_pct = InpPartialClosePct;
    if(track.htf_target && track.htf_partial_r > 0)
    {
        partial_r = track.htf_partial_r;
        partial_pct = track.htf_partial_pct;
    }

    if(partial_r <= 0) return;
    if(track.partial_closed) return;
    if(InpPartialOnlyDeep && !track.deep_entry) return;

    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);

    if(current_r >= partial_r)
    {
        if(ShouldSkipCloseAttempt(track))
            return;

        if(PartialClose(track.ticket, partial_pct))
        {
            track.partial_closed = true;
            if(InpPartialPostLockR > 0)
            {
                double new_sl = RToPrice(InpPartialPostLockR, track.entry_price, track.risk_price, track.direction);
                ApplyProtectiveSL(track, new_sl, "partial_lock", current_r);
            }
            PrintSLDebug("partial", track, current_r, 0);
        }
        else
            MarkCloseAttemptFailed(track);
    }
}

void CheckBreakeven(PosTrack &track, const EAState &state)
{
    if(track.be_applied) return;

    double be_r = CfgBreakevenR();
    double be_lock_r = CfgBreakevenLockR();
    if(track.trend_release && InpConditionalOBTrendReleaseBELockR >= 0.0)
        be_lock_r = InpConditionalOBTrendReleaseBELockR;

    if(track.direction > 0)
    {
        if(InpBuyBE_R > 0) be_r = InpBuyBE_R;
        if(InpBuyBE_Lock > 0) be_lock_r = InpBuyBE_Lock;
    }
    else if(track.direction < 0)
    {
        if(InpSellBE_R > 0) be_r = InpSellBE_R;
        if(InpSellBE_Lock > 0) be_lock_r = InpSellBE_Lock;
    }

    // v11: 用入场时锁定的市场状态
    if(CfgEnableStateFilter())
    {
        if(track.entry_market_state == 0 && CfgRangeBE_R() > 0)
            be_r = CfgRangeBE_R();
        else if(track.entry_market_state != 0)
        {
            if(CfgTrendBE_R() > 0) be_r = CfgTrendBE_R();
            if(CfgTrendBE_Lock() > 0) be_lock_r = CfgTrendBE_Lock();
        }
    }

    if(!UseBTCProfile() && InpContextBER > 0 && InpContextBEMinPrice > 0)
    {
        bool context_be = (track.entry_price >= InpContextBEMinPrice);
        if(context_be && InpContextBEMaxPrice > 0 && track.entry_price > InpContextBEMaxPrice)
            context_be = false;
        if(context_be && InpContextBEMaxMonthStartBalance > 0)
        {
            SyncMonthlyRiskState();
            if(g_monthly_start_balance <= 0 ||
               g_monthly_start_balance > InpContextBEMaxMonthStartBalance)
                context_be = false;
        }
        if(context_be)
        {
            be_r = InpContextBER;
            be_lock_r = InpContextBELockR;
        }
    }

    // VSL active: 5s timer is the protection, delay BE to let winners run
    if(CfgVirtualSLBreachSec() > 0)
    {
        be_r = 1.0;
        be_lock_r = 0.6;
    }

    if(be_r <= 0) return;

    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);

    if(current_r >= be_r)
    {
        ApplyConditionalBETrendRelease(track, current_r, state, be_lock_r);
        double new_sl = RToPrice(be_lock_r, track.entry_price, track.risk_price, track.direction);
        if(ShouldSkipCloseAttempt(track))
            return;

        if(ApplyProtectiveSL(track, new_sl, "be", current_r))
        {
            track.be_applied = true;
        }
        else
            MarkCloseAttemptFailed(track);
    }
}

void CheckStructureProfitLock(PosTrack &track, const EAState &state)
{
    if(!track.use_structure_sl) return;
    if(InpStructProfitLockTriggerR <= 0 && InpStructProfitTrailTriggerR <= 0) return;
    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    track.peak_profit_r = MathMax(track.peak_profit_r, current_r);

    if(InpStructProfitLockRequireReverseSignal)
    {
        int lookback = MathMax(2, InpDTPHoldLookbackBars);
        MqlRates m1[40], m5[40];
        int m1_count = CopyRates(_Symbol, PERIOD_M1, 0, 40, m1);
        int m5_count = CopyRates(_Symbol, PERIOD_M5, 0, 40, m5);
        double atr_m1 = CalcATR(m1, m1_count, 14);
        double atr_m5 = CalcATR(m5, m5_count, 14);
        bool m1_reverse = m1_count >= lookback + 2 && atr_m1 > 0 &&
                          (HasDTPHoldReverseBreak(m1, m1_count, track.direction, atr_m1) ||
                           HasDTPHoldStrongReverseCandle(m1, m1_count, track.direction, lookback, atr_m1));
        bool m5_reverse = m5_count >= lookback + 2 && atr_m5 > 0 &&
                          (HasDTPHoldReverseBreak(m5, m5_count, track.direction, atr_m5) ||
                           HasDTPHoldStrongReverseCandle(m5, m5_count, track.direction, lookback, atr_m5));
        if(!m1_reverse && !m5_reverse)
            return;
    }

    double lock_r = -999999.0;
    string reason = "";
    if(InpStructProfitTrailTriggerR > 0 &&
       InpStructProfitTrailLockMult > 0 &&
       track.peak_profit_r >= InpStructProfitTrailTriggerR)
    {
        lock_r = track.peak_profit_r * InpStructProfitTrailLockMult;
        reason = "struct_trail";
    }
    else if(InpStructProfitLockTriggerR > 0 &&
            current_r >= InpStructProfitLockTriggerR)
    {
        lock_r = InpStructProfitLockR;
        reason = "struct_lock";
    }

    if(lock_r <= -999998.0) return;

    double new_sl = RToPrice(lock_r, track.entry_price, track.risk_price, track.direction);
    if(ShouldSkipCloseAttempt(track))
        return;

    if(ApplyProtectiveSL(track, new_sl, reason, current_r))
    {
    }
    else
        MarkCloseAttemptFailed(track);
}

void CheckTrailing(PosTrack &track)
{
    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_sl    = PositionGetDouble(POSITION_SL);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);

    track.peak_profit_r = MathMax(track.peak_profit_r, current_r);

    // 从最高级别向下检查，避免同一tick多次ModifySL
    // Level 3 升级
    if(InpTrail3TriggerR > 0 && current_r >= InpTrail3TriggerR && track.trail_level < 3)
    {
        double lock_r = InpTrail3LockR > 0 ? InpTrail3LockR : track.peak_profit_r * InpTrail3LockMult;
        double new_sl = RToPrice(lock_r, track.entry_price, track.risk_price, track.direction);
        if(ShouldSkipCloseAttempt(track))
            return;

        if(ApplyProtectiveSL(track, new_sl, "trail3", current_r))
        {
            track.trail_level = 3;
        }
        else
            MarkCloseAttemptFailed(track);
        return;
    }
    // Level 2 升级
    else if(InpTrail2TriggerR > 0 && current_r >= InpTrail2TriggerR && track.trail_level < 2)
    {
        double lock_r = InpTrail2LockR > 0 ? InpTrail2LockR : track.peak_profit_r * InpTrail2LockMult;
        double new_sl = RToPrice(lock_r, track.entry_price, track.risk_price, track.direction);
        if(ShouldSkipCloseAttempt(track))
            return;

        if(ApplyProtectiveSL(track, new_sl, "trail2", current_r))
        {
            track.trail_level = 2;
        }
        else
            MarkCloseAttemptFailed(track);
        return;
    }
    // Level 1 升级
    else if(InpTrail1TriggerR > 0 && current_r >= InpTrail1TriggerR && track.trail_level < 1)
    {
        double new_sl = RToPrice(InpTrail1LockR, track.entry_price, track.risk_price, track.direction);
        if(ShouldSkipCloseAttempt(track))
            return;

        if(ApplyProtectiveSL(track, new_sl, "trail1", current_r))
        {
            track.trail_level = 1;
        }
        else
            MarkCloseAttemptFailed(track);
        return;
    }

    // 动态推进: 当前级别的LockMult > 0时，随peak增长持续推进SL
    double lock_mult = 0;
    if(track.trail_level == 3 && InpTrail3LockMult > 0)
        lock_mult = InpTrail3LockMult;
    else if(track.trail_level == 2 && InpTrail2LockMult > 0)
        lock_mult = InpTrail2LockMult;

    if(lock_mult > 0)
    {
        double lock_r = track.peak_profit_r * lock_mult;
        double new_sl = RToPrice(lock_r, track.entry_price, track.risk_price, track.direction);
        if((track.direction > 0 && new_sl > current_sl) ||
           (track.direction < 0 && new_sl < current_sl))
        {
            if(ShouldSkipCloseAttempt(track))
                return;

            if(ApplyProtectiveSL(track, new_sl, "trail_dyn", current_r))
            {
            }
            else
                MarkCloseAttemptFailed(track);
        }
    }
}

double GetDTPRetrace(const PosTrack &track, const EAState &state)
{
    double dtp_retrace = CfgDTPRetrace();
    if(track.direction > 0 && InpBuyDTPRetrace > 0)
        dtp_retrace = InpBuyDTPRetrace;
    else if(track.direction < 0 && InpSellDTPRetrace > 0)
        dtp_retrace = InpSellDTPRetrace;
    if(track.htf_target && InpHTFDTPRetrace > 0)
        dtp_retrace = InpHTFDTPRetrace;
    if(CfgEnableStateFilter() && track.entry_market_state != 0 && CfgTrendDTPRetrace() > 0)
        dtp_retrace = CfgTrendDTPRetrace() / 100.0;
    if(InpDTPStage2TriggerR > 0 && InpDTPStage2Retrace > 0 && track.dtp_peak_r >= InpDTPStage2TriggerR)
        dtp_retrace = InpDTPStage2Retrace;
    if(InpDTPStage3TriggerR > 0 && InpDTPStage3Retrace > 0 && track.dtp_peak_r >= InpDTPStage3TriggerR)
        dtp_retrace = InpDTPStage3Retrace;
    if(track.dtp_partial_closed && CfgDTPPostPartialRetrace() > 0)
        dtp_retrace = CfgDTPPostPartialRetrace();
    if(track.htf_target && track.dtp_partial_closed && InpHTFDTPPostPartialRetrace > 0)
        dtp_retrace = InpHTFDTPPostPartialRetrace;
    if(InpEnableMomentumRegime && InpStrongDTPRetraceMult > 0 &&
       PassDTPHoldSignalQuality(track) && IsPositionStrong(track, state))
        dtp_retrace *= InpStrongDTPRetraceMult;
    return dtp_retrace;
}

void ApplyDTPPostPartialLock(PosTrack &track, double current_r)
{
    if(CfgDTPPostPartialLockR() <= 0) return;
    if(current_r <= CfgDTPPostPartialLockR()) return;
    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_sl = PositionGetDouble(POSITION_SL);
    double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
    double new_sl = RToPrice(CfgDTPPostPartialLockR(), track.entry_price, track.risk_price, track.direction);

    if(track.direction > 0)
    {
        if(new_sl <= current_sl || new_sl >= current_price - point)
            return;
    }
    else
    {
        if(new_sl >= current_sl || new_sl <= current_price + point)
            return;
    }

    if(ShouldSkipCloseAttempt(track))
        return;

    if(!ApplyProtectiveSL(track, new_sl, "dtp_part_lock", current_r))
        MarkCloseAttemptFailed(track);
}

double DirectionalNetBodyATR_PM(const MqlRates &rates[], int count, int direction, int lookback, double atr)
{
    if(atr <= 0 || count < lookback + 2)
        return 0.0;
    double net = 0.0;
    int used = MathMin(lookback, count - 1);
    for(int i = 1; i <= used; i++)
        net += (rates[i].close - rates[i].open) * direction;
    return net / atr;
}

bool HasDTPHoldReverseBreak(const MqlRates &rates[], int count, int direction, double atr)
{
    if(atr <= 0 || count < 8)
        return false;
    double buffer = atr * InpDTPHoldBreakBufferATR;
    double last_close = rates[1].close;
    double swing_high = 0.0;
    double swing_low = 999999.0;
    int limit = MathMin(count - 2, 18);

    for(int i = 2; i < limit; i++)
    {
        if(swing_high <= 0 && IsSwingHigh(rates, i, 1, count))
            swing_high = rates[i].high;
        if(swing_low >= 999999.0 && IsSwingLow(rates, i, 1, count))
            swing_low = rates[i].low;
    }
    if(swing_high <= 0)
    {
        for(int i = 2; i < MathMin(count, 12); i++)
            swing_high = MathMax(swing_high, rates[i].high);
    }
    if(swing_low >= 999999.0)
    {
        for(int i = 2; i < MathMin(count, 12); i++)
            swing_low = MathMin(swing_low, rates[i].low);
    }

    if(direction == OB_BUY)
        return (swing_low < 999999.0 && last_close < swing_low - buffer);
    return (swing_high > 0 && last_close > swing_high + buffer);
}

bool HasDTPHoldStrongReverseCandle(const MqlRates &rates[], int count, int direction,
                                   int lookback, double atr)
{
    if(atr <= 0 || count < lookback + 2)
        return false;
    int used = MathMin(lookback, count - 1);
    for(int i = 1; i <= used; i++)
    {
        double reverse_body = (rates[i].open - rates[i].close) * direction;
        if(reverse_body >= atr * InpDTPHoldReverseBodyATR)
            return true;
    }
    return false;
}

bool IsDTPContinuationOnTF(const PosTrack &track, ENUM_TIMEFRAMES tf, int lookback)
{
    MqlRates rates[40];
    int count = CopyRates(_Symbol, tf, 0, 40, rates);
    if(count < lookback + 2)
        return false;

    double atr = CalcATR(rates, count, 14);
    if(atr <= 0)
        return false;

    if(HasDTPHoldReverseBreak(rates, count, track.direction, atr))
        return false;
    if(HasDTPHoldStrongReverseCandle(rates, count, track.direction, lookback, atr))
        return false;
    if(CheckMomentumWeakness(_Symbol, track.direction, rates, count))
        return false;

    double net = DirectionalNetBodyATR_PM(rates, count, track.direction, lookback, atr);
    return (net >= InpDTPHoldMinNetATR || CheckStrongMomentum(_Symbol, track.direction, rates, count));
}

bool PassDTPHoldSignalQuality(const PosTrack &track)
{
    bool apply_min_bounce = true;
    if(StringLen(InpDTPHoldMinBounceDirections) > 0)
    {
        string filter = InpDTPHoldMinBounceDirections;
        StringToLower(filter);
        if(track.direction == OB_BUY)
            apply_min_bounce = (StringFind(filter, "buy") >= 0);
        else if(track.direction == OB_SELL)
            apply_min_bounce = (StringFind(filter, "sell") >= 0);
    }
    if(apply_min_bounce &&
       InpDTPHoldMinBounceSec > 0 &&
       track.bounce_seconds < InpDTPHoldMinBounceSec)
        return false;
    bool apply_confirm_pos = true;
    if(StringLen(InpDTPHoldConfirmPosDirections) > 0)
    {
        string filter = InpDTPHoldConfirmPosDirections;
        StringToLower(filter);
        if(track.direction == OB_BUY)
            apply_confirm_pos = (StringFind(filter, "buy") >= 0);
        else if(track.direction == OB_SELL)
            apply_confirm_pos = (StringFind(filter, "sell") >= 0);
    }
    if(apply_confirm_pos &&
       InpDTPHoldMaxConfirmPos < 900.0 &&
       track.confirm_ob_pos > InpDTPHoldMaxConfirmPos)
        return false;
    bool apply_min_pos_mult = true;
    if(StringLen(InpDTPHoldMinEntryPosMultDirections) > 0)
    {
        string filter = InpDTPHoldMinEntryPosMultDirections;
        StringToLower(filter);
        if(track.direction == OB_BUY)
            apply_min_pos_mult = (StringFind(filter, "buy") >= 0);
        else if(track.direction == OB_SELL)
            apply_min_pos_mult = (StringFind(filter, "sell") >= 0);
    }
    if(apply_min_pos_mult &&
       InpDTPHoldMinEntryPosMult > 0.0 &&
       track.entry_pos_mult < InpDTPHoldMinEntryPosMult)
        return false;
    return true;
}

bool ShouldHoldDTPContinuation(const PosTrack &track)
{
    if(!InpDTPHoldOnContinuation)
        return false;
    if(!PositionSelectByTicket(track.ticket))
        return false;
    if(!PassDTPHoldSignalQuality(track))
        return false;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r <= 0.0)
        return false;
    if(InpDTPHoldRequireHTFAligned && !IsDTPStrictHTFAligned(track))
        return false;

    int lookback = MathMax(2, InpDTPHoldLookbackBars);
    bool tf1_hold = IsDTPContinuationOnTF(track, MinutesToTF(InpDTPHoldTF1), lookback);
    bool tf2_hold = false;
    if(InpDTPHoldTF2 > 0)
        tf2_hold = IsDTPContinuationOnTF(track, MinutesToTF(InpDTPHoldTF2), lookback);

    return (tf1_hold || tf2_hold);
}

bool HasConditionalTrendReleaseReverseBreak(const MqlRates &rates[], int count,
                                            int direction, double atr)
{
    if(atr <= 0 || count < 8)
        return false;
    double buffer = atr * MathMax(InpConditionalOBTrendReleaseBreakBufferATR, 0.0);
    double last_close = rates[1].close;
    double swing_high = 0.0;
    double swing_low = 999999.0;
    int limit = MathMin(count - 2, 18);

    for(int i = 2; i < limit; i++)
    {
        if(swing_high <= 0 && IsSwingHigh(rates, i, 1, count))
            swing_high = rates[i].high;
        if(swing_low >= 999999.0 && IsSwingLow(rates, i, 1, count))
            swing_low = rates[i].low;
    }
    if(swing_high <= 0)
    {
        for(int i = 2; i < MathMin(count, 12); i++)
            swing_high = MathMax(swing_high, rates[i].high);
    }
    if(swing_low >= 999999.0)
    {
        for(int i = 2; i < MathMin(count, 12); i++)
            swing_low = MathMin(swing_low, rates[i].low);
    }

    if(direction == OB_BUY)
        return (swing_low < 999999.0 && last_close < swing_low - buffer);
    return (swing_high > 0 && last_close > swing_high + buffer);
}

bool HasConditionalTrendReleaseStrongReverseCandle(const MqlRates &rates[],
                                                  int count, int direction,
                                                  int lookback, double atr)
{
    if(atr <= 0 || count < lookback + 2)
        return false;
    int used = MathMin(lookback, count - 1);
    for(int i = 1; i <= used; i++)
    {
        double reverse_body = (rates[i].open - rates[i].close) * direction;
        if(reverse_body >= atr * MathMax(InpConditionalOBTrendReleaseReverseBodyATR, 0.0))
            return true;
    }
    return false;
}

bool IsConditionalTrendReleaseOnTF(const PosTrack &track, ENUM_TIMEFRAMES tf,
                                  int lookback)
{
    MqlRates rates[40];
    int count = CopyRates(_Symbol, tf, 0, 40, rates);
    if(count < lookback + 2)
        return false;

    double atr = CalcATR(rates, count, 14);
    if(atr <= 0)
        return false;

    if(HasConditionalTrendReleaseReverseBreak(rates, count, track.direction, atr))
        return false;
    if(HasConditionalTrendReleaseStrongReverseCandle(rates, count, track.direction,
                                                     lookback, atr))
        return false;
    if(CheckMomentumWeakness(_Symbol, track.direction, rates, count))
        return false;

    double net = DirectionalNetBodyATR_PM(rates, count, track.direction, lookback, atr);
    return (net >= MathMax(InpConditionalOBTrendReleaseMinNetATR, 0.0) ||
            CheckStrongMomentum(_Symbol, track.direction, rates, count));
}

bool ShouldApplyConditionalTrendRelease(const PosTrack &track)
{
    if(!InpConditionalOBTrendRelease)
        return false;
    if(!PositionSelectByTicket(track.ticket))
        return false;
    if(!PassDTPHoldSignalQuality(track))
        return false;
    bool apply_min_pos_mult = true;
    if(StringLen(InpConditionalOBTrendReleasePosMultDirections) > 0)
    {
        string filter = InpConditionalOBTrendReleasePosMultDirections;
        StringToLower(filter);
        if(track.direction == OB_BUY)
            apply_min_pos_mult = (StringFind(filter, "buy") >= 0);
        else if(track.direction == OB_SELL)
            apply_min_pos_mult = (StringFind(filter, "sell") >= 0);
    }
    if(apply_min_pos_mult &&
       InpConditionalOBTrendReleaseMinEntryPosMult > 0.0 &&
       track.entry_pos_mult < InpConditionalOBTrendReleaseMinEntryPosMult)
        return false;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r <= 0.0)
        return false;

    int lookback = MathMax(2, InpConditionalOBTrendReleaseLookbackBars);
    int tf1_min = InpConditionalOBTrendReleaseTF1 > 0
        ? InpConditionalOBTrendReleaseTF1
        : CfgBarTF();
    bool tf1_hold = IsConditionalTrendReleaseOnTF(
        track, MinutesToTF(tf1_min), lookback);
    bool tf2_hold = false;
    if(InpConditionalOBTrendReleaseTF2 > 0)
        tf2_hold = IsConditionalTrendReleaseOnTF(
            track, MinutesToTF(InpConditionalOBTrendReleaseTF2), lookback);

    return (tf1_hold || tf2_hold);
}

bool HasDTPReverseContinuationOnTF(const PosTrack &track, ENUM_TIMEFRAMES tf, int lookback)
{
    MqlRates rates[40];
    int count = CopyRates(_Symbol, tf, 0, 40, rates);
    if(count < lookback + 2)
        return false;

    double atr = CalcATR(rates, count, 14);
    if(atr <= 0)
        return false;

    int reverse_dir = -track.direction;
    if(!HasDTPHoldReverseBreak(rates, count, track.direction, atr))
        return false;
    if(!HasDTPHoldStrongReverseCandle(rates, count, track.direction, lookback, atr))
        return false;

    double reverse_net = DirectionalNetBodyATR_PM(rates, count, reverse_dir, lookback, atr);
    return (reverse_net >= InpDTPHoldMinNetATR || CheckStrongMomentum(_Symbol, reverse_dir, rates, count));
}

bool HasDTPReverseContinuation(const PosTrack &track)
{
    if(!InpDTPExitRequireReverseContinuation)
        return true;
    if(!PositionSelectByTicket(track.ticket))
        return false;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r <= 0.0)
        return true;

    int lookback = MathMax(2, InpDTPHoldLookbackBars);
    if(HasDTPReverseContinuationOnTF(track, MinutesToTF(InpDTPHoldTF1), lookback))
        return true;
    if(InpDTPHoldTF2 > 0 && HasDTPReverseContinuationOnTF(track, MinutesToTF(InpDTPHoldTF2), lookback))
        return true;
    return false;
}

bool HasExitReverseContinuation(const PosTrack &track)
{
    if(!PositionSelectByTicket(track.ticket))
        return false;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r <= 0.0)
        return true;

    int lookback = MathMax(2, InpDTPHoldLookbackBars);
    if(HasDTPReverseContinuationOnTF(track, MinutesToTF(InpDTPHoldTF1), lookback))
        return true;
    if(InpDTPHoldTF2 > 0 && HasDTPReverseContinuationOnTF(track, MinutesToTF(InpDTPHoldTF2), lookback))
        return true;
    return false;
}

bool HasDTPMomentumWeaknessOnTF(const PosTrack &track, ENUM_TIMEFRAMES tf)
{
    MqlRates rates[40];
    int count = CopyRates(_Symbol, tf, 0, 40, rates);
    if(count < 4)
        return false;
    return CheckMomentumWeakness(_Symbol, track.direction, rates, count);
}

bool HasDTPMomentumWeakness(const PosTrack &track)
{
    if(!InpDTPExitRequireMomentumWeakness)
        return true;
    if(!PositionSelectByTicket(track.ticket))
        return false;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r <= 0.0)
        return true;

    if(HasDTPMomentumWeaknessOnTF(track, MinutesToTF(InpDTPHoldTF1)))
        return true;
    if(InpDTPHoldTF2 > 0 && HasDTPMomentumWeaknessOnTF(track, MinutesToTF(InpDTPHoldTF2)))
        return true;
    return false;
}

bool IsDTPStrictHTFAligned(const PosTrack &track)
{
    if(!InpDTPStrictRequireHTFAligned)
        return true;
    if(track.direction == 0)
        return false;

    int bars = MathMax(InpDTPStrictHTFBars, 1);
    int need = MathMin(MathMax(bars + InpATRPeriod + 4, 24), 80);
    ENUM_TIMEFRAMES tf = MinutesToTF(InpDTPStrictHTFTF);

    MqlRates rates[80];
    int count = CopyRates(_Symbol, tf, 0, need, rates);
    if(count < bars + 2)
        return false;

    double atr = CalcATR(rates, count, InpATRPeriod);
    if(atr <= 0.0)
        return false;

    double net = 0.0;
    for(int i = 1; i <= bars && i < count; i++)
        net += (rates[i].close - rates[i].open) * track.direction;

    return (net / atr >= InpDTPStrictHTFMinATR);
}

bool IsDTPStrictRangeQuality(const PosTrack &track, bool range_optional)
{
    if(!CfgRangeDTPStrictQualityOnly())
        return true;
    if(range_optional)
        return true;
    if(!CfgEnableRangeFade() || track.direction == 0 || track.entry_price <= 0.0)
        return false;

    HTFRange range = GetHTFRange(_Symbol);
    if(!range.valid)
        return false;

    ENUM_RANGE_POSITION pos = GetRangePosition(range, track.entry_price);
    if(track.direction == OB_BUY)
        return pos == RANGE_NEAR_BOTTOM;
    if(track.direction == OB_SELL)
        return pos == RANGE_NEAR_TOP;
    return false;
}

bool IsDirectionHTFNetAligned(int direction, int tf_min, int bars_input, double min_atr)
{
    if(direction == 0)
        return false;

    int bars = MathMax(bars_input, 1);
    int need = MathMin(MathMax(bars + InpATRPeriod + 4, 24), 80);
    ENUM_TIMEFRAMES tf = MinutesToTF(tf_min);

    MqlRates rates[80];
    int count = CopyRates(_Symbol, tf, 0, need, rates);
    if(count < bars + 2)
        return false;

    double atr = CalcATR(rates, count, InpATRPeriod);
    if(atr <= 0.0)
        return false;

    double net = 0.0;
    for(int i = 1; i <= bars && i < count; i++)
        net += (rates[i].close - rates[i].open) * direction;

    return (net / atr >= min_atr);
}

bool HasRecentStrongStructureBreakOnTF(int direction, int tf_min)
{
    if(direction == 0)
        return false;

    ENUM_TIMEFRAMES tf = MinutesToTF(tf_min);
    int pivot = MathMax(1, MathMin(InpStructureSLStrongBreakPivot, 6));
    int lookback = MathMax(InpStructureSLStrongBreakLookback, pivot * 4 + 12);
    int max_age = MathMax(1, InpStructureSLStrongBreakMaxAge);
    int need = MathMin(MathMax(lookback + max_age + InpATRPeriod + pivot + 8, 80), 360);

    MqlRates rates[360];
    int count = CopyRates(_Symbol, tf, 0, need, rates);
    if(count < pivot * 2 + 12)
        return false;

    double atr = CalcATR(rates, count, InpATRPeriod);
    if(atr <= 0.0)
        return false;

    double buffer = atr * MathMax(InpStructureSLStrongBreakBufferATR, 0.0);
    int age_limit = MathMin(max_age, count - pivot - 2);
    int swing_limit = MathMin(count - pivot, lookback + max_age);

    for(int break_bar = 1; break_bar <= age_limit; break_bar++)
    {
        int swing_start = break_bar + pivot + 1;
        if(swing_start >= swing_limit)
            continue;

        for(int swing_bar = swing_start; swing_bar < swing_limit; swing_bar++)
        {
            if(direction == OB_BUY)
            {
                if(!IsSwingHigh(rates, swing_bar, pivot, count))
                    continue;
                bool prev_not_broken = (rates[break_bar + 1].close <= rates[swing_bar].high + buffer);
                bool close_broken = (rates[break_bar].close > rates[swing_bar].high + buffer);
                if(prev_not_broken && close_broken)
                    return true;
            }
            else
            {
                if(!IsSwingLow(rates, swing_bar, pivot, count))
                    continue;
                bool prev_not_broken = (rates[break_bar + 1].close >= rates[swing_bar].low - buffer);
                bool close_broken = (rates[break_bar].close < rates[swing_bar].low - buffer);
                if(prev_not_broken && close_broken)
                    return true;
            }
        }
    }
    return false;
}

bool HasRecentStrongStructureBreak(int direction)
{
    if(!InpStructureSLRequireStrongBreak)
        return true;
    if(HasRecentStrongStructureBreakOnTF(direction, InpStructureSLStrongBreakTF1))
        return true;
    if(InpStructureSLStrongBreakTF2 > 0 &&
       HasRecentStrongStructureBreakOnTF(direction, InpStructureSLStrongBreakTF2))
        return true;
    return false;
}

bool IsStructureSLHTFAligned(int direction)
{
    if(!HasRecentStrongStructureBreak(direction))
        return false;
    if(!InpStructureSLRequireHTFAligned)
        return true;
    return IsDirectionHTFNetAligned(direction, InpStructureSLHTFTF,
                                    InpStructureSLHTFBars, InpStructureSLHTFMinATR);
}

void CheckDTP(PosTrack &track, const EAState &state)
{
    double dtp_trigger_r = CfgDTPTriggerR();
    if(track.direction > 0 && InpBuyDTPTriggerR > 0)
        dtp_trigger_r = InpBuyDTPTriggerR;
    else if(track.direction < 0 && InpSellDTPTriggerR > 0)
        dtp_trigger_r = InpSellDTPTriggerR;
    if(track.htf_target && InpHTFDTPTriggerR > 0)
        dtp_trigger_r = InpHTFDTPTriggerR;
    // ATR低波体制: 降低DTP触发(更容易止盈, 解决2605跑不到1.5R的问题)
    if(InpATRRegimeLowDTPTriggerR > 0.0 && IsATRLowVolRegime())
        dtp_trigger_r = InpATRRegimeLowDTPTriggerR;
    // 双扫体制自适应: 震荡区间降低DTP触发(双重条件: 体制检测+防守态)
    if(CfgDoubleSweepDTPTriggerR() > 0.0 && IsDoubleSweepRegime()
       && IsAdaptiveNoiseGateDefensive())
        dtp_trigger_r = CfgDoubleSweepDTPTriggerR();
    if(dtp_trigger_r <= 0) return;
    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);

    if(!track.dtp_active && current_r >= dtp_trigger_r)
    {
        track.dtp_active = true;
        track.dtp_peak_r = current_r;
        ActivateConditionalTrendRelease(track, current_r, state);
    }

    if(track.dtp_active)
    {
        track.dtp_peak_r = MathMax(track.dtp_peak_r, current_r);
        double dtp_retrace = GetDTPRetrace(track, state);
        double retrace = track.dtp_peak_r - current_r;
        double threshold = InpAdaptiveDTP ? track.dtp_peak_r * dtp_retrace
                                          : dtp_trigger_r * dtp_retrace;
        if(retrace >= threshold)
        {
            bool strict_exit = IsDTPStrictExitFamily(track.entry_family);
            if(CfgRangeHTFRejectContextEnabled() && track.htf_target)
                strict_exit = true;
            if(strict_exit && !IsDTPStrictHTFAligned(track))
                strict_exit = false;
            bool range_optional = (track.entry_family == ENTRY_FAMILY_REVSWP);
            if(strict_exit && !IsDTPStrictRangeQuality(track, range_optional))
                strict_exit = false;
            if(strict_exit && !HasDTPReverseContinuation(track))
            {
                PrintExitDebug("dtp_wait_rev", track, current_r, state);
                return;
            }
            if(strict_exit && !HasDTPMomentumWeakness(track))
            {
                PrintExitDebug("dtp_wait_weak", track, current_r, state);
                return;
            }
            if(ShouldHoldDTPContinuation(track))
            {
                PrintExitDebug("dtp_hold", track, current_r, state);
                return;
            }
            if(ShouldSkipCloseAttempt(track))
                return;

            if(InpDTPExitMode == 1 && !track.dtp_partial_closed)
            {
                if(PartialClose(track.ticket, InpDTPPartialPct))
                {
                    track.dtp_partial_closed = true;
                    ApplyDTPPostPartialLock(track, current_r);
                    PrintExitDebug("dtp_partial", track, current_r, state);
                    if(CfgDTPResetPeakAfterPartial())
                        track.dtp_peak_r = current_r;
                    return;
                }
            }
            PrintExitDebug(track.dtp_partial_closed ? "dtp2" : "dtp", track, current_r, state);
            if(ClosePosition(track.ticket, track.dtp_partial_closed ? "dtp2" : "dtp"))
                ClearFailureReentryStateOnWin(track.direction, current_r);
            else
                MarkCloseAttemptFailed(track);
        }
    }
}

bool IsPositionStrong(const PosTrack &track, const EAState &state)
{
    if(!InpEnableMomentumRegime && !InpEnableStrongAddOn)
        return false;

    MqlRates rates[];
    int need = MathMax(InpStrongMomentumBars, 4) + 2;
    int count = CopyRates(_Symbol, GetWorkTF(), 0, need, rates);
    if(count < need)
        return false;

    return CheckStrongMomentum(_Symbol, track.direction, rates, count);
}

void CheckDecay(PosTrack &track, const EAState &state)
{
    if(!CfgEnableDecayExit() && !InpEnableMomentumRegime) return;

    // DTP激活后禁用衰减检测，让大赢单自由跑
    if(track.dtp_active) return;

    // 缓存 M1 rates：同一 bar 内只 CopyRates 一次（bar级模式，tick级检查无意义）
    static int    s_decay_bar = 0;
    static MqlRates s_m1_rates[];
    static int    s_m1_count = 0;

    if(state.bar_count != s_decay_bar)
    {
        s_decay_bar = state.bar_count;
        s_m1_count = CopyRates(_Symbol, PERIOD_M1, 0, CfgDecayBars() + 5, s_m1_rates);
    }
    if(s_m1_count < CfgDecayBars() + 2) return;

    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);

    // 震荡态入场单衰减门槛更低(0.5R)，趋势态用主参数
    double effective_decay_min = CfgDecayMinR();
    if(track.entry_market_state == 0 && CfgDecayMinR() > 0.5)
        effective_decay_min = 0.5;

    double effective_weak_min = InpWeakExitMinR;
    if(IsWeakExitFamilyOverride(track.entry_family))
        effective_weak_min = InpWeakExitFamilyMinR;

    bool decay = CfgEnableDecayExit() && current_r >= effective_decay_min &&
                 CheckMomentumDecay(_Symbol, track.direction, s_m1_rates, s_m1_count);
    bool weak = InpEnableMomentumRegime && current_r >= effective_weak_min &&
                CheckMomentumWeakness(_Symbol, track.direction, s_m1_rates, s_m1_count);
    if(decay || weak)
    {
        if(weak && InpWeakExitRequireReverseContinuation &&
           IsWeakExitFamilySelected(track.entry_family) &&
           !HasExitReverseContinuation(track))
        {
            bool low_balance_weak_guard =
                (InpWeakExitLowBalanceThreshold > 0.0 &&
                 AccountInfoDouble(ACCOUNT_BALANCE) <= InpWeakExitLowBalanceThreshold);
            if(low_balance_weak_guard &&
               InpWeakExitLowBalanceForceExitR > 0.0 &&
               current_r >= InpWeakExitLowBalanceForceExitR)
            {
                if(ShouldSkipCloseAttempt(track))
                    return;

                PrintExitDebug("weak_low_balance_force", track, current_r, state);
                if(ClosePosition(track.ticket, "weak_low_balance_force"))
                    ClearFailureReentryStateOnWin(track.direction, current_r);
                else
                    MarkCloseAttemptFailed(track);
                return;
            }

            double weak_lock_r = InpWeakExitHoldLockR;
            if(low_balance_weak_guard && InpWeakExitLowBalanceHoldLockR > weak_lock_r)
                weak_lock_r = InpWeakExitLowBalanceHoldLockR;

            if(weak_lock_r > 0.0 && current_r > weak_lock_r &&
               !ShouldSkipCloseAttempt(track))
            {
                double lock_sl = RToPrice(weak_lock_r, track.entry_price,
                                          track.risk_price, track.direction);
                if(!ApplyProtectiveSL(track, lock_sl, "weak_hold_lock", current_r))
                    MarkCloseAttemptFailed(track);
            }
            PrintExitDebug("weak_wait_rev", track, current_r, state);
            return;
        }
        if(ShouldSkipCloseAttempt(track))
            return;

        string reason = weak ? "momentum_weak" : "decay";
        PrintExitDebug(reason, track, current_r, state);
        if(ClosePosition(track.ticket, reason))
            ClearFailureReentryStateOnWin(track.direction, current_r);
        else
            MarkCloseAttemptFailed(track);
    }
}

void CheckTimeExit(PosTrack &track, const EAState &state)
{
    int time_exit_bars = CfgTimeExitBars();

    // v11: 用入场时锁定的市场状态判断超时
    if(CfgEnableStateFilter() && track.entry_market_state == 0 && CfgRangeTimeExit() < 999)
        time_exit_bars = CfgRangeTimeExit();

    if(time_exit_bars >= 999) return;

    int bars_held = state.bar_count - track.open_bar;
    if(bars_held >= time_exit_bars)
    {
        bool time_hold_family_ok = (StringLen(InpDTPStrictExitFamilies) <= 0 ||
                                    IsDTPStrictExitFamily(track.entry_family));
        if(time_hold_family_ok && InpDTPHoldOnContinuation && ShouldHoldDTPContinuation(track))
        {
            double hold_r = CurrentR(track);
            PrintExitDebug("time_hold", track, hold_r, state);
            return;
        }

        if(ShouldSkipCloseAttempt(track))
            return;

        double current_r = CurrentR(track);
        PrintExitDebug("time", track, current_r, state);
        if(ClosePosition(track.ticket, "time"))
        {
            if(current_r >= 0.0)
                ClearFailureReentryStateOnWin(track.direction, current_r);
            else
                RecordFailureReentryState(track.direction, track.entry_family, track.entry_price);
        }
        else
            MarkCloseAttemptFailed(track);
    }
}

void RegisterPosition(ulong ticket, int direction, double entry, double sl, double risk_price,
                      bool deep_entry, int bounce_seconds, double confirm_ob_pos, double entry_pos_mult,
                      bool htf_target, double htf_partial_r, int htf_partial_pct,
                      bool trend_release,
                      bool failure_reverse,
                      PosTrack &tracks[], int &track_count,
                      int entry_family = ENTRY_FAMILY_ANY)
{
    if(track_count >= MAX_POSITIONS)
    {
        Print("跟踪数组已满, 无法注册 ticket=", ticket);
        return;
    }

    PosTrack t;
    ZeroMemory(t);
    t.ticket       = ticket;
    t.direction    = direction;
    t.entry_price  = entry;
    t.sl_initial   = sl;
    t.risk_price   = risk_price;
    t.peak_profit_r = 0;
    t.open_bar     = 0;  // 由调用者在注册后设置,或直接用state.bar_count
    t.be_applied   = false;
    t.trail_level  = 0;
    t.dtp_active   = false;
    t.dtp_peak_r   = 0;
    t.partial_closed = false;
    t.dtp_partial_closed = false;
    t.deep_entry = deep_entry;
    t.bounce_seconds = bounce_seconds;
    t.confirm_ob_pos = confirm_ob_pos;
    t.entry_pos_mult = entry_pos_mult;
    t.htf_target = htf_target;
    t.htf_partial_r = htf_partial_r;
    t.htf_partial_pct = htf_partial_pct;
    t.trend_release = trend_release;
    t.failure_reverse = failure_reverse;
    t.addon_count = 0;
    t.strong_addon = false;
    t.last_close_attempt = 0;
    t.last_sl_reason = "";
    t.entry_market_state = 0;
    t.virtual_sl = sl;
    t.virtual_sl_breach_start = 0;
    t.survived_vsl_breach = false;
    t.entry_family = entry_family;
    t.entry_balance = AccountInfoDouble(ACCOUNT_BALANCE);
    t.virtual_sl_reason = "init";
    t.use_structure_sl = (InpEnableStructureMomentumHold &&
                          IsStructureHoldFamilySelected(entry_family));
    t.skip_mfe_exits = (t.use_structure_sl && InpStructSkipMFEExits);

    tracks[track_count] = t;
    track_count++;
}

#endif
