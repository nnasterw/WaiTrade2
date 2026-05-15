#ifndef __WAITRADE_POSITION_MANAGER_MQH__
#define __WAITRADE_POSITION_MANAGER_MQH__

#include "Types.mqh"
#include "Config.mqh"
#include "Utils.mqh"
#include "MarketState.mqh"
#include "DecayDetector.mqh"

void ManagePositions(PosTrack &tracks[], int &track_count, const EAState &state)
{
    for(int i = track_count - 1; i >= 0; i--)
    {
        if(tracks[i].ticket == 0) continue;

        if(!PositionSelectByTicket(tracks[i].ticket))
        {
            for(int j = i; j < track_count - 1; j++)
                tracks[j] = tracks[j + 1];
            track_count--;
            continue;
        }

        CheckBreakeven(tracks[i], state);
        CheckTrailing(tracks[i]);
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
            for(int j = i; j < track_count - 1; j++)
                tracks[j] = tracks[j + 1];
            track_count--;
        }
    }
}

void CheckBreakeven(PosTrack &track, const EAState &state)
{
    if(track.be_applied) return;

    double be_r = InpBreakevenR;
    double be_lock_r = InpBreakevenLockR;

    // v9.8 态感知BE参数
    if(InpEnableStateFilter)
    {
        if(state.market_state == 0 && InpRangeBE_R > 0)
            be_r = InpRangeBE_R;
        else if(state.market_state != 0)
        {
            if(InpTrendBE_R > 0) be_r = InpTrendBE_R;
            if(InpTrendBE_Lock > 0) be_lock_r = InpTrendBE_Lock;
        }
    }

    if(be_r <= 0) return;

    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);

    if(current_r >= be_r)
    {
        double new_sl = RToPrice(be_lock_r, track.entry_price, track.risk_price, track.direction);
        if(ModifySL(track.ticket, new_sl))
            track.be_applied = true;
    }
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
        if(ModifySL(track.ticket, new_sl))
            track.trail_level = 3;
        return;
    }
    // Level 2 升级
    else if(InpTrail2TriggerR > 0 && current_r >= InpTrail2TriggerR && track.trail_level < 2)
    {
        double lock_r = InpTrail2LockR > 0 ? InpTrail2LockR : track.peak_profit_r * InpTrail2LockMult;
        double new_sl = RToPrice(lock_r, track.entry_price, track.risk_price, track.direction);
        if(ModifySL(track.ticket, new_sl))
            track.trail_level = 2;
        return;
    }
    // Level 1 升级
    else if(InpTrail1TriggerR > 0 && current_r >= InpTrail1TriggerR && track.trail_level < 1)
    {
        double new_sl = RToPrice(InpTrail1LockR, track.entry_price, track.risk_price, track.direction);
        if(ModifySL(track.ticket, new_sl))
            track.trail_level = 1;
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
            ModifySL(track.ticket, new_sl);
        }
    }
}

void CheckDTP(PosTrack &track, const EAState &state)
{
    if(InpDTPTriggerR <= 0) return;

    double dtp_retrace = InpDTPRetrace;
    // v9.8 趋势态DTP回撤
    if(InpEnableStateFilter && state.market_state != 0 && InpTrendDTPRetrace > 0)
        dtp_retrace = InpTrendDTPRetrace / 100.0;

    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);

    if(!track.dtp_active && current_r >= InpDTPTriggerR)
    {
        track.dtp_active = true;
        track.dtp_peak_r = current_r;
    }

    if(track.dtp_active)
    {
        track.dtp_peak_r = MathMax(track.dtp_peak_r, current_r);
        double retrace = track.dtp_peak_r - current_r;
        double threshold = InpAdaptiveDTP ? track.dtp_peak_r * dtp_retrace
                                          : InpDTPTriggerR * dtp_retrace;
        if(retrace >= threshold)
            ClosePosition(track.ticket);
    }
}

void CheckDecay(PosTrack &track, const EAState &state)
{
    if(!InpEnableDecayExit) return;

    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r < InpDecayMinR) return;

    MqlRates m1_rates[];
    int m1_count = CopyRates(_Symbol, PERIOD_M1, 0, InpDecayBars + 5, m1_rates);
    if(m1_count < InpDecayBars + 2) return;

    if(CheckMomentumDecay(_Symbol, track.direction, m1_rates, m1_count))
        ClosePosition(track.ticket);
}

void CheckTimeExit(PosTrack &track, const EAState &state)
{
    int time_exit_bars = InpTimeExitBars;

    // v9.8 震荡态超时
    if(InpEnableStateFilter && state.market_state == 0 && InpRangeTimeExit < 999)
        time_exit_bars = InpRangeTimeExit;

    if(time_exit_bars >= 999) return;

    int bars_held = state.bar_count - track.open_bar;
    if(bars_held >= time_exit_bars)
        ClosePosition(track.ticket);
}

void RegisterPosition(ulong ticket, int direction, double entry, double sl, double risk_price,
                      PosTrack &tracks[], int &track_count)
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

    tracks[track_count] = t;
    track_count++;
}

#endif
