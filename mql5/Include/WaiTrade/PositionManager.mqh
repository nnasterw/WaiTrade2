#ifndef __WAITRADE_POSITION_MANAGER_MQH__
#define __WAITRADE_POSITION_MANAGER_MQH__

#include "Types.mqh"
#include "Config.mqh"
#include "Utils.mqh"

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

        CheckBreakeven(tracks[i]);
        CheckTrailing(tracks[i]);
        CheckDTP(tracks[i], state);
        CheckTimeExit(tracks[i], state);
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

void CheckBreakeven(PosTrack &track)
{
    if(track.be_applied) return;
    if(InpBreakevenR <= 0) return;

    if(!PositionSelectByTicket(track.ticket)) return;

    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);

    if(current_r >= InpBreakevenR)
    {
        double new_sl = RToPrice(InpBreakevenLockR, track.entry_price, track.risk_price, track.direction);
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
        double threshold = InpAdaptiveDTP ? track.dtp_peak_r * InpDTPRetrace
                                          : InpDTPTriggerR * InpDTPRetrace;
        if(retrace >= threshold)
            ClosePosition(track.ticket);
    }
}

void CheckTimeExit(PosTrack &track, const EAState &state)
{
    if(InpTimeExitBars >= 999) return;

    int bars_held = state.bar_count - track.open_bar;
    if(bars_held >= InpTimeExitBars)
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
