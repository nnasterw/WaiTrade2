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
    int              touch_count;
    bool             active;
};

void AddEntryMonitor(const TradeSignal &sig, const OBZone &zone,
                     EntryMonitor &monitors[], int &mon_count)
{
    if(mon_count >= MAX_MONITORS) return;

    // 去重：同一 ob_index 不重复添加
    for(int i = 0; i < mon_count; i++)
    {
        if(monitors[i].active && monitors[i].ob_index == sig.ob_index)
            return;
    }

    EntryMonitor m;
    ZeroMemory(m);
    m.ob_index     = sig.ob_index;
    m.direction    = sig.direction;
    m.entry_price  = (zone.high + zone.low) / 2.0;  // OB mid
    m.sl           = sig.sl;
    m.ob_top       = zone.high;
    m.ob_bottom    = zone.low;
    m.risk_price   = MathAbs(m.entry_price - sig.sl);
    m.pos_mult     = sig.pos_mult;
    m.phase        = PHASE_WAITING_TOUCH;
    m.expire_time  = TimeCurrent() + InpTimeoutMin * 60;
    m.touch_count  = 0;
    m.active       = true;

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
            monitors[i].phase = PHASE_EXPIRED;
            monitors[i].active = false;
            continue;
        }

        double entry = monitors[i].entry_price;
        double ob_height = monitors[i].ob_top - monitors[i].ob_bottom;
        if(ob_height <= 0) ob_height = monitors[i].risk_price * 2;
        double threshold = ob_height * InpBouncePct;
        double risk = monitors[i].risk_price;
        if(risk <= 0) { monitors[i].active = false; continue; }

        double price = (monitors[i].direction == OB_BUY) ? bid : ask;

        // PHASE_WAITING_TOUCH: 等价格触及 OB 范围
        if(monitors[i].phase == PHASE_WAITING_TOUCH)
        {
            bool touched = false;
            if(monitors[i].direction == OB_BUY && price <= monitors[i].ob_top) touched = true;
            if(monitors[i].direction == OB_SELL && price >= monitors[i].ob_bottom) touched = true;

            if(touched)
            {
                monitors[i].touch_price = price;
                monitors[i].touch_time = now;
                monitors[i].touch_count++;

                if(InpRequireDoubleTch && monitors[i].touch_count < 2)
                    monitors[i].phase = PHASE_WAITING_DOUBLE;
                else
                    monitors[i].phase = PHASE_WAITING_BOUNCE;
            }
        }
        // PHASE_WAITING_DOUBLE: 等反弹后第二次触及
        else if(monitors[i].phase == PHASE_WAITING_DOUBLE)
        {
            bool bounced = false;
            if(monitors[i].direction == OB_BUY && price - entry >= threshold) bounced = true;
            if(monitors[i].direction == OB_SELL && entry - price >= threshold) bounced = true;

            if(bounced)
            {
                monitors[i].phase = PHASE_WAITING_TOUCH;
            }

            if((int)(now - monitors[i].touch_time) > InpDoubleTchWindowMin * 60)
            {
                monitors[i].active = false;
                monitors[i].phase = PHASE_EXPIRED;
            }
        }
        // PHASE_WAITING_BOUNCE: 等 bounce 确认
        else if(monitors[i].phase == PHASE_WAITING_BOUNCE)
        {
            bool confirmed = false;
            if(monitors[i].direction == OB_BUY && price - entry >= threshold) confirmed = true;
            if(monitors[i].direction == OB_SELL && entry - price >= threshold) confirmed = true;

            if(confirmed)
            {
                monitors[i].confirm_price = price;
                monitors[i].phase = PHASE_CONFIRMED;

                double offset_r = MathAbs(price - entry) / risk;
                if(offset_r > InpMaxEntryOffsetR)
                {
                    monitors[i].phase = PHASE_EXPIRED;
                    monitors[i].active = false;
                    continue;
                }

                if(out_count < max_out)
                {
                    TradeSignal ts;
                    ZeroMemory(ts);
                    ts.direction  = monitors[i].direction;
                    ts.entry      = price;
                    ts.sl         = monitors[i].sl;
                    ts.tp         = 0;
                    ts.risk_price = risk;
                    ts.lot        = 0;  // 由调用者计算
                    ts.pos_mult   = monitors[i].pos_mult;
                    ts.ob_index   = monitors[i].ob_index;
                    ts.comment    = "EntryEngine";
                    out_count++;
                    out_signals[out_count - 1] = ts;
                }

                monitors[i].phase = PHASE_ENTERED;
                monitors[i].active = false;
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
