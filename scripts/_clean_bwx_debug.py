"""Clean up BigWinLock debug prints and simplify"""
from pathlib import Path
pm_path = Path("D:/Code/codexProject/WaiTrade2/mql5/Include/WaiTrade2/PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")

# Remove all debug prints
old_bwx = """void CheckBigWinProtection(PosTrack &track, const EAState &state)
{
    static int s_call_count = 0;
    s_call_count++;
    if(s_call_count % 5 == 1) { double cr = PriceToR(PositionGetDouble(POSITION_PRICE_CURRENT), track.entry_price, track.risk_price, track.direction); Print("BWX ", s_call_count, " trig=", InpBTCBigWinTriggerR, " htf=", track.htf_target, " r=", cr, " risk_price=", track.risk_price, " entry=", track.entry_price); }
    if(!UseBTCProfile()) return;
    double trigger_r = InpBTCBigWinTriggerR;
    double lock_to_r = InpBTCBigWinLockToR;
    if(trigger_r <= 0.0 || lock_to_r <= 0.0) return;
    if(InpBTCBigWinOnlyHTFTarget && !track.htf_target) return;
    if(track.bigwin_locked) return;
    if(!PositionSelectByTicket(track.ticket)) return;
    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r < trigger_r) { if(current_r > trigger_r - 0.3) Print("BWX near r=", current_r, " trig=", trigger_r); return; }
    Print("BWX TRIGGER r=", current_r, ">= trig=", trigger_r);
    // 将 SL 移到 lock_to_r 位置 (锁利)
    double new_sl = RToPrice(lock_to_r, track.entry_price, track.risk_price, track.direction);
    if(!track.bigwin_locked)
    {
        if(ShouldSkipCloseAttempt(track)) return;
        if(ApplyProtectiveSL(track, new_sl, "bigwin_lock", current_r))
        {
            track.bigwin_locked = true;
            PrintExitDebug("bigwin_lock", track, current_r, state);
        }
        else
            MarkCloseAttemptFailed(track);
    }
}"""

new_bwx = """void CheckBigWinProtection(PosTrack &track, const EAState &state)
{
    if(!UseBTCProfile()) return;
    double trigger_r = InpBTCBigWinTriggerR;
    double lock_to_r = InpBTCBigWinLockToR;
    if(trigger_r <= 0.0 || lock_to_r <= 0.0) return;
    if(InpBTCBigWinOnlyHTFTarget && !track.htf_target) return;
    if(track.bigwin_locked) return;
    if(!PositionSelectByTicket(track.ticket)) return;
    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r < trigger_r) return;
    // 将 SL 移到 lock_to_r 位置 (锁利) - 强制执行, 跳过 IsSLImprovement 检查
    double new_sl = RToPrice(lock_to_r, track.entry_price, track.risk_price, track.direction);
    if(!PositionSelectByTicket(track.ticket)) return;
    if(!ModifySL(track.ticket, new_sl)) return;
    track.virtual_sl = new_sl;
    track.virtual_sl_reason = "bigwin_lock";
    track.last_sl_reason = "bigwin_lock";
    track.bigwin_locked = true;
    if(InpEnableExitDebug) PrintExitDebug("bigwin_lock", track, current_r, state);
}"""

if old_bwx in content:
    content = content.replace(old_bwx, new_bwx, 1)
    pm_path.write_text(content, encoding="utf-8")
    print("Cleaned CheckBigWinProtection")
else:
    print("Not found")

