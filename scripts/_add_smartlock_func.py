from pathlib import Path
pm_path = Path(r"D:\Code\codexProject\WaiTrade2\mql5\Include\WaiTrade2\PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")

# Insert CheckSmartLock before CheckBigWinProtection
needle = "void CheckBigWinProtection(PosTrack &track, const EAState &state)"
new_func = """// SmartLock: dynamic big-win protection
// When R >= InpSmartLockTriggerR, lock SL at InpSmartLockPct * peak_r (R-based)
// Designed to protect winners from reversal
void CheckSmartLock(PosTrack &track, const EAState &state)
{
    if(!InpSmartLockEnable) return;
    if(track.smart_locked) return;
    if(!PositionSelectByTicket(track.ticket)) return;
    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r < InpSmartLockTriggerR) return;
    // Calculate target lock R based on current peak R
    double target_lock_r = current_r * InpSmartLockPct;
    if(target_lock_r < 0.5) return;  // minimum lock at 0.5R
    // Calculate new SL price
    double new_sl = RToPrice(target_lock_r, track.entry_price, track.risk_price, track.direction);
    // Force set SL
    if(!ModifySL(track.ticket, new_sl)) return;
    track.virtual_sl = new_sl;
    track.virtual_sl_reason = "smart_lock";
    track.last_sl_reason = "smart_lock";
    track.smart_locked = true;
    if(InpEnableExitDebug) PrintExitDebug("smart_lock", track, current_r, state);
}

void CheckBigWinProtection(PosTrack &track, const EAState &state)"""
if needle in content:
    content = content.replace(needle, new_func, 1)
    pm_path.write_text(content, encoding="utf-8")
    print("Added CheckSmartLock function")
else:
    print("Not found")

