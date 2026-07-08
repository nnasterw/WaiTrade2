"""为 PositionManager.mqh 添加 CheckBigWinProtection 和 CheckMonthlyLossGuard 函数"""
from pathlib import Path
import re

pm_path = Path("D:/Code/codexProject/WaiTrade2/mql5/Include/WaiTrade2/PositionManager.mqh")
content = pm_path.read_text(encoding="utf-8")

# 找到 CheckMaxLossCap 函数末尾
needle = "void CheckPartialClose(PosTrack &track, const EAState &state)"
if needle not in content:
    print("Anchor not found:", needle)
    exit(1)

new_funcs = """// BTC 大赢单保护器: 当 R 达到 InpBTCBigWinTriggerR 时, 主动锁定到 InpBTCBigWinLockToR
// 目的: 让 >3R 单子数量增加 (锁住大赢单防回吐)
void CheckBigWinProtection(PosTrack &track, const EAState &state)
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
}

// BTC 月度最大单笔损失保护: 防止单笔损失超过 R 阈值 (月度风控)
void CheckMonthlyLossGuard(PosTrack &track, const EAState &state,
                           PosTrack &tracks[], int &track_count)
{
    if(!UseBTCProfile()) return;
    if(!InpBTCEnableMonthlyLossGuard) return;
    double guard_r = InpBTCMonthlyLossGuardR;
    if(guard_r >= 0.0) return;
    if(InpBTCMonthlyLossGuardOnlyHTFTarget && !track.htf_target) return;
    if(!PositionSelectByTicket(track.ticket)) return;
    // 至少持有 5 bars 避免入场即被 guard
    int bars_held = state.bar_count - track.open_bar;
    if(bars_held < 5) return;
    double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
    double current_r = PriceToR(current_price, track.entry_price, track.risk_price, track.direction);
    if(current_r > guard_r) return;
    if(ShouldSkipCloseAttempt(track)) return;
    if(ClosePosition(track.ticket, "monthly_loss_guard"))
    {
        PrintExitDebug("monthly_loss_guard", track, current_r, state);
        RecordFailureReentryState(track.direction, track.entry_family, track.entry_price);
    }
    else
        MarkCloseAttemptFailed(track);
}

void CheckPartialClose(PosTrack &track, const EAState &state)"""

# 替换
content_new = content.replace(needle, new_funcs, 1)
pm_path.write_text(content_new, encoding="utf-8")
print("Inserted CheckBigWinProtection and CheckMonthlyLossGuard functions")
print("File size:", pm_path.stat().st_size)

