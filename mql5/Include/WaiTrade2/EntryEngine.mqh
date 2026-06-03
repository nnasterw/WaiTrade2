#ifndef __WAITRADE_ENTRY_ENGINE_MQH__
#define __WAITRADE_ENTRY_ENGINE_MQH__

#include "Config.mqh"
#include "Types.mqh"
#include "MathUtils.mqh"
#include "TradeOps.mqh"
#include "ScoreEngine.mqh"

#define MAX_MONITORS 20

enum ENUM_ENTRY_PHASE
{
    PHASE_WAITING_TOUCH,
    PHASE_WAITING_BOUNCE,
    PHASE_WAITING_PULLBACK,
    PHASE_WAITING_DOUBLE,
    PHASE_CONFIRMED,
    PHASE_EXPIRED,
    PHASE_ENTERED
};

struct EntryMonitor
{
    int              ob_index;
    int              direction;       // OB_BUY or OB_SELL
    double           entry_price;     // OB mid
    double           sl;
    double           ob_top;
    double           ob_bottom;
    double           risk_price;      // |entry - sl|
    double           pos_mult;
    ENUM_ENTRY_PHASE phase;
    datetime         expire_time;
    datetime         touch_time;
    double           touch_price;
    double           confirm_price;
    datetime         confirm_time;
    double           confirm_body_pct;
    double           pullback_entry_price;
    int              touch_count;
    bool             deep_entry;
    bool             active;
    bool             is_loose_sweep;
    bool             is_htf_pullback;
};

double ClampEntryDepthPct()
{
    return GetEffectiveEntryDepthPct();
}

double CalcDepthTouchLevel(const EntryMonitor &monitor)
{
    double depth = ClampEntryDepthPct();
    if(depth <= 0)
        return (monitor.direction == OB_BUY) ? monitor.ob_top : monitor.ob_bottom;

    double height = monitor.ob_top - monitor.ob_bottom;
    if(height <= 0)
        return (monitor.direction == OB_BUY) ? monitor.ob_top : monitor.ob_bottom;

    if(monitor.direction == OB_BUY)
        return monitor.ob_top - height * depth;
    return monitor.ob_bottom + height * depth;
}

bool IsDeepTouched(const EntryMonitor &monitor, double price)
{
    if(ClampEntryDepthPct() <= 0)
        return false;

    double level = CalcDepthTouchLevel(monitor);
    if(monitor.direction == OB_BUY)
        return price <= level;
    return price >= level;
}

bool PassEntryStructureConfirm(int direction, double price)
{
    if(InpEntryConfirmBars <= 0)
        return true;

    MqlRates rates[];
    int need = InpEntryConfirmBars + 2;
    int copied = CopyRates(_Symbol, GetWorkTF(), 0, need, rates);
    if(copied < need)
        return false;

    double level = (direction == OB_BUY) ? rates[copied - 2].high : rates[copied - 2].low;
    for(int i = copied - 3; i >= 0 && i >= copied - 1 - InpEntryConfirmBars; i--)
    {
        if(direction == OB_BUY)
            level = MathMax(level, rates[i].high);
        else
            level = MathMin(level, rates[i].low);
    }

    if(direction == OB_BUY)
        return price > level;
    return price < level;
}

bool PassBounceCloseConfirm(EntryMonitor &monitor)
{
    int bars_needed = CfgBounceCloseConfirmBars();
    if(bars_needed <= 0)
        return true;

    int tf_min = (InpBounceCloseTF > 0) ? InpBounceCloseTF : CfgBarTF();
    ENUM_TIMEFRAMES tf = MinutesToTF(tf_min);

    MqlRates rates[];
    int copied = CopyRates(_Symbol, tf, 1, bars_needed + 10, rates);
    if(copied < bars_needed)
        return false;

    double ob_height = monitor.ob_top - monitor.ob_bottom;
    if(ob_height <= 0)
        ob_height = monitor.risk_price;
    double buffer = ob_height * CfgBounceCloseBufferPct();

    int confirmed = 0;
    for(int i = copied - 1; i >= 0 && confirmed < bars_needed; i--)
    {
        datetime close_time = rates[i].time + PeriodSeconds(tf);
        if(close_time <= monitor.touch_time)
            break;

        bool pass = false;
        if(monitor.direction == OB_BUY)
        {
            pass = (rates[i].close > monitor.ob_top + buffer);
            if(pass && CfgBounceCloseRequireBody())
                pass = (rates[i].close > rates[i].open);
            double range = rates[i].high - rates[i].low;
            double body_pct = (range > 0) ? MathAbs(rates[i].close - rates[i].open) / range * 100.0 : 0.0;
            if(pass && CfgBounceCloseMinBodyPct() > 0)
            {
                pass = (body_pct >= CfgBounceCloseMinBodyPct());
            }
            if(pass)
                monitor.confirm_body_pct = body_pct;
        }
        else
        {
            pass = (rates[i].close < monitor.ob_bottom - buffer);
            if(pass && CfgBounceCloseRequireBody())
                pass = (rates[i].close < rates[i].open);
            double range = rates[i].high - rates[i].low;
            double body_pct = (range > 0) ? MathAbs(rates[i].close - rates[i].open) / range * 100.0 : 0.0;
            if(pass && CfgBounceCloseMinBodyPct() > 0)
            {
                pass = (body_pct >= CfgBounceCloseMinBodyPct());
            }
            if(pass)
                monitor.confirm_body_pct = body_pct;
        }

        if(!pass)
            return false;

        confirmed++;
    }

    return confirmed >= bars_needed;
}

double CalcConfirmPullbackEntryPrice(const EntryMonitor &monitor)
{
    double pct = InpConfirmPullbackPct;
    if(pct < 0.0) pct = 0.0;
    if(pct > 1.0) pct = 1.0;

    if(monitor.direction == OB_BUY)
        return monitor.confirm_price - (monitor.confirm_price - monitor.touch_price) * pct;
    return monitor.confirm_price + (monitor.touch_price - monitor.confirm_price) * pct;
}

bool IsConfirmPullbackAdverseBreak(const EntryMonitor &monitor, double price, double ob_height)
{
    if(InpConfirmPullbackMaxAdversePct <= 0)
        return false;

    double buffer = ob_height * InpConfirmPullbackMaxAdversePct;
    if(monitor.direction == OB_BUY)
        return price < monitor.touch_price - buffer;
    return price > monitor.touch_price + buffer;
}

void BuildEntrySignalFromMonitor(const EntryMonitor &monitor, double price,
                                 TradeSignal &out_signal)
{
    ZeroMemory(out_signal);
    out_signal.direction  = monitor.direction;
    out_signal.entry      = price;
    out_signal.sl         = monitor.sl;
    out_signal.tp         = 0;
    out_signal.risk_price = MathAbs(price - monitor.sl);
    out_signal.lot        = 0;
    out_signal.pos_mult   = monitor.pos_mult;
    out_signal.ob_index   = monitor.ob_index;
    out_signal.deep_entry = monitor.deep_entry;
    out_signal.touch_price = monitor.touch_price;
    out_signal.confirm_price = monitor.confirm_price;
    out_signal.bounce_seconds = (int)(monitor.confirm_time - monitor.touch_time);
    out_signal.confirm_body_pct = monitor.confirm_body_pct;

    double ob_height = monitor.ob_top - monitor.ob_bottom;
    if(ob_height > 0)
    {
        out_signal.bounce_ob_pct = MathAbs(monitor.confirm_price - monitor.touch_price) / ob_height;
        if(monitor.direction == OB_BUY)
            out_signal.confirm_ob_pos = (monitor.confirm_price - monitor.ob_top) / ob_height;
        else
            out_signal.confirm_ob_pos = (monitor.ob_bottom - monitor.confirm_price) / ob_height;
    }
    out_signal.comment    = "EntryEngine";
}

void AddEntryMonitor(const TradeSignal &sig, const OBZone &zone,
                     EntryMonitor &monitors[], int &mon_count)
{
    // 去重：同一 ob_index 不重复添加
    for(int i = 0; i < mon_count; i++)
    {
        if(monitors[i].active && monitors[i].ob_index == sig.ob_index)
            return;
    }
    if(mon_count >= MAX_MONITORS)
    {
        if(zone.is_loose_sweep || zone.is_htf_pullback)
            return;

        int remove_idx = -1;
        for(int i = 0; i < mon_count; i++)
        {
            if(monitors[i].active && (monitors[i].is_loose_sweep || monitors[i].is_htf_pullback))
            {
                remove_idx = i;
                break;
            }
        }
        if(remove_idx < 0)
            return;

        for(int i = remove_idx; i < mon_count - 1; i++)
            monitors[i] = monitors[i + 1];
        mon_count--;
    }

    EntryMonitor m;
    ZeroMemory(m);
    m.ob_index     = sig.ob_index;
    m.direction    = sig.direction;
    // 入场参考用OB边缘（触及位），不用mid
    m.entry_price  = (sig.direction == OB_BUY) ? zone.high : zone.low;
    m.sl           = sig.sl;
    m.ob_top       = zone.high;
    m.ob_bottom    = zone.low;
    m.risk_price   = MathAbs(m.entry_price - sig.sl);
    m.pos_mult     = sig.pos_mult;
    m.phase        = PHASE_WAITING_TOUCH;
    m.expire_time  = TimeCurrent() + CfgTimeoutMin() * 60;
    m.touch_count  = 0;
    m.deep_entry   = false;
    m.active       = true;
    m.is_loose_sweep = zone.is_loose_sweep;
    m.is_htf_pullback = zone.is_htf_pullback;

    monitors[mon_count] = m;
    mon_count++;
}

int UpdateEntryMonitors(double bid, double ask, datetime now,
                        EntryMonitor &monitors[], int &mon_count,
                        TradeSignal &out_signals[], int max_out)
{
    int out_count = 0;

    for(int i = 0; i < mon_count; i++)
    {
        if(!monitors[i].active) continue;

        if(now > monitors[i].expire_time)
        {
            if(InpEnableEntryDebug) Print("MON_DIAG ob=", monitors[i].ob_index, " dir=", monitors[i].direction, " phase=", monitors[i].phase, " status=EXPIRED timeout");
            monitors[i].phase = PHASE_EXPIRED;
            monitors[i].active = false;
            continue;
        }

        double entry = monitors[i].entry_price;
        double ob_height = monitors[i].ob_top - monitors[i].ob_bottom;
        if(ob_height <= 0) ob_height = monitors[i].risk_price * 2;
        double threshold = ob_height * CfgBouncePct();
        double risk = monitors[i].risk_price;
        if(risk <= 0) { monitors[i].active = false; continue; }

        double price = (monitors[i].direction == OB_BUY) ? bid : ask;
        double depth_level = CalcDepthTouchLevel(monitors[i]);
        if(IsDeepTouched(monitors[i], price))
            monitors[i].deep_entry = true;

        // PHASE_WAITING_TOUCH: 等价格触及OB深度阈值 → 记录touch → 进入bounce等待
        if(monitors[i].phase == PHASE_WAITING_TOUCH)
        {
            bool touched = false;
            double touch_level = CfgEntryDepthFilter() ? depth_level :
                                 ((monitors[i].direction == OB_BUY) ? monitors[i].ob_top : monitors[i].ob_bottom);
            if(monitors[i].direction == OB_BUY && price <= touch_level) touched = true;
            if(monitors[i].direction == OB_SELL && price >= touch_level) touched = true;

            if(touched)
            {
                monitors[i].touch_price = price;
                monitors[i].touch_time = now;
                monitors[i].touch_count++;
                if(InpEnableEntryDebug) Print("MON_DIAG ob=", monitors[i].ob_index, " dir=", monitors[i].direction, " phase=", monitors[i].phase, " status=TOUCHED count=", monitors[i].touch_count, " price=", price);

                // 二推不破: 需要第二次触及才进入bounce确认
                if(CfgRequireDoubleTch() && monitors[i].touch_count < 2)
                {
                    monitors[i].phase = PHASE_WAITING_DOUBLE;
                    continue;
                }

                // 触及确认，进入bounce等待阶段
                monitors[i].phase = PHASE_WAITING_BOUNCE;
            }
        }
        // PHASE_WAITING_BOUNCE: tick级bounce确认 — 价格从OB反弹达到阈值才入场
        else if(monitors[i].phase == PHASE_WAITING_BOUNCE)
        {
            if(monitors[i].direction == OB_BUY && price < monitors[i].touch_price)
                monitors[i].touch_price = price;
            if(monitors[i].direction == OB_SELL && price > monitors[i].touch_price)
                monitors[i].touch_price = price;

            bool confirmed = false;
            // buy: 价格从真实最深触点向上弹出 ob_height × InpBouncePct
            if(monitors[i].direction == OB_BUY && price - monitors[i].touch_price >= threshold)
                confirmed = true;
            // sell: 价格从真实最深触点向下弹出 ob_height × InpBouncePct
            if(monitors[i].direction == OB_SELL && monitors[i].touch_price - price >= threshold)
                confirmed = true;

            if(confirmed)
            {
                if(InpEnableEntryDebug) Print("MON_DIAG ob=", monitors[i].ob_index, " dir=", monitors[i].direction, " status=BOUNCE_CONFIRMED price=", price, " touch=", monitors[i].touch_price, " threshold=", threshold);

                if(!PassEntryStructureConfirm(monitors[i].direction, price))
                {
                    if(InpEnableEntryDebug) Print("MON_DIAG ob=", monitors[i].ob_index, " dir=", monitors[i].direction, " status=BLOCKED struct_confirm price=", price);
                    continue;
                }

                if(!PassBounceCloseConfirm(monitors[i]))
                {
                    if(InpEnableEntryDebug) Print("MON_DIAG ob=", monitors[i].ob_index, " dir=", monitors[i].direction, " status=BLOCKED bounce_close_confirm");
                    continue;
                }

                // offset guard: 确认价偏离entry过远则放弃
                double offset_r = MathAbs(price - entry) / risk;
                if(offset_r > CfgMaxEntryOffsetR())
                {
                    if(InpEnableEntryDebug) Print("MON_DIAG ob=", monitors[i].ob_index, " dir=", monitors[i].direction, " status=BLOCKED offset_r=", offset_r, " max=", CfgMaxEntryOffsetR());
                    monitors[i].phase = PHASE_EXPIRED;
                    monitors[i].active = false;
                    continue;
                }

                monitors[i].confirm_price = price;
                monitors[i].confirm_time = now;

                if(InpEnableConfirmPullback && InpConfirmPullbackWaitSec > 0 &&
                   InpConfirmPullbackPct > 0)
                {
                    monitors[i].pullback_entry_price = CalcConfirmPullbackEntryPrice(monitors[i]);
                    monitors[i].phase = PHASE_WAITING_PULLBACK;
                    if(InpEnableEntryDebug) Print("MON_DIAG ob=", monitors[i].ob_index, " dir=", monitors[i].direction, " status=PULLBACK_WAIT entry=", monitors[i].pullback_entry_price);
                    continue;
                }

                monitors[i].phase = PHASE_ENTERED;
                monitors[i].active = false;
                if(InpEnableEntryDebug) Print("MON_DIAG ob=", monitors[i].ob_index, " dir=", monitors[i].direction, " status=ENTERED price=", price, " bounce_r=", offset_r);

                if(out_count < max_out)
                {
                    BuildEntrySignalFromMonitor(monitors[i], price, out_signals[out_count]);
                    out_count++;
                }
            }

            // bounce超时: 30 bars未确认则过期
            if((int)(now - monitors[i].touch_time) > 30 * CfgBarTF() * 60)
            {
                monitors[i].phase = PHASE_EXPIRED;
                monitors[i].active = false;
            }
        }
        // PHASE_WAITING_PULLBACK: bounce确认后等短回踩到折返价，未回踩则放弃
        else if(monitors[i].phase == PHASE_WAITING_PULLBACK)
        {
            bool entered = false;
            if(monitors[i].direction == OB_BUY && price <= monitors[i].pullback_entry_price)
                entered = true;
            if(monitors[i].direction == OB_SELL && price >= monitors[i].pullback_entry_price)
                entered = true;

            if(entered)
            {
                monitors[i].phase = PHASE_ENTERED;
                monitors[i].active = false;
                if(out_count < max_out)
                {
                    BuildEntrySignalFromMonitor(monitors[i],
                                                monitors[i].pullback_entry_price,
                                                out_signals[out_count]);
                    out_count++;
                }
                continue;
            }

            if(IsConfirmPullbackAdverseBreak(monitors[i], price, ob_height) ||
               (int)(now - monitors[i].confirm_time) > InpConfirmPullbackWaitSec)
            {
                monitors[i].phase = PHASE_EXPIRED;
                monitors[i].active = false;
            }
        }
        // PHASE_WAITING_DOUBLE: 等第二次触及(二推不破)
        else if(monitors[i].phase == PHASE_WAITING_DOUBLE)
        {
            // 检查第二次触及
            bool touched2 = false;
            double touch2_level = CfgEntryDepthFilter() ? depth_level :
                                  ((monitors[i].direction == OB_BUY) ? monitors[i].ob_top : monitors[i].ob_bottom);
            if(monitors[i].direction == OB_BUY && price <= touch2_level) touched2 = true;
            if(monitors[i].direction == OB_SELL && price >= touch2_level) touched2 = true;

            if(touched2)
            {
                monitors[i].touch_count++;
                if(monitors[i].touch_count >= 2)
                {
                    // 第二次触及确认，进入bounce等待
                    monitors[i].touch_price = price;
                    monitors[i].touch_time = now;
                    monitors[i].phase = PHASE_WAITING_BOUNCE;
                }
            }

            // 二推窗口超时
            if((int)(now - monitors[i].touch_time) > InpDoubleTchWindowMin * 60)
            {
                monitors[i].active = false;
                monitors[i].phase = PHASE_EXPIRED;
            }
        }
    }

    // 压缩：清理非活跃 monitors
    int write = 0;
    for(int i = 0; i < mon_count; i++)
    {
        if(monitors[i].active)
        {
            if(write != i)
                monitors[write] = monitors[i];
            write++;
        }
    }
    mon_count = write;

    return out_count;
}

#endif
