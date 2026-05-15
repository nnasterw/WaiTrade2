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
    // 入场参考用OB边缘（触及位），不用mid
    m.entry_price  = (sig.direction == OB_BUY) ? zone.high : zone.low;
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

        // PHASE_WAITING_TOUCH: 等价格触及 OB 范围 → 直接确认（OBDetector已验证有效性）
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

                // 二推不破: 需要第二次触及
                if(InpRequireDoubleTch && monitors[i].touch_count < 2)
                {
                    monitors[i].phase = PHASE_WAITING_DOUBLE;
                    continue;
                }

                // OBDetector 的 impulse+bounce 已证明 OB 有效
                // 触及即确认，只做 offset guard
                double offset_r = MathAbs(price - entry) / risk;
                if(offset_r > InpMaxEntryOffsetR)
                {
                    monitors[i].phase = PHASE_EXPIRED;
                    monitors[i].active = false;
                    continue;
                }

                monitors[i].confirm_price = price;
                monitors[i].phase = PHASE_ENTERED;
                monitors[i].active = false;

                if(out_count < max_out)
                {
                    TradeSignal ts;
                    ZeroMemory(ts);
                    ts.direction  = monitors[i].direction;
                    ts.entry      = price;
                    ts.sl         = monitors[i].sl;
                    ts.tp         = 0;
                    ts.risk_price = risk;
                    ts.lot        = 0;
                    ts.pos_mult   = monitors[i].pos_mult;
                    ts.ob_index   = monitors[i].ob_index;
                    ts.comment    = "EntryEngine";
                    out_signals[out_count] = ts;
                    out_count++;
                }
            }
        }
        // PHASE_WAITING_DOUBLE: 等第二次触及
        else if(monitors[i].phase == PHASE_WAITING_DOUBLE)
        {
            // 检查第二次触及
            bool touched2 = false;
            if(monitors[i].direction == OB_BUY && price <= monitors[i].ob_top) touched2 = true;
            if(monitors[i].direction == OB_SELL && price >= monitors[i].ob_bottom) touched2 = true;

            if(touched2)
            {
                monitors[i].touch_count++;
                if(monitors[i].touch_count >= 2)
                {
                    double offset_r = MathAbs(price - entry) / risk;
                    if(offset_r > InpMaxEntryOffsetR)
                    {
                        monitors[i].phase = PHASE_EXPIRED;
                        monitors[i].active = false;
                        continue;
                    }

                    monitors[i].confirm_price = price;
                    monitors[i].phase = PHASE_ENTERED;
                    monitors[i].active = false;

                    if(out_count < max_out)
                    {
                        TradeSignal ts;
                        ZeroMemory(ts);
                        ts.direction  = monitors[i].direction;
                        ts.entry      = price;
                        ts.sl         = monitors[i].sl;
                        ts.tp         = 0;
                        ts.risk_price = risk;
                        ts.lot        = 0;
                        ts.pos_mult   = monitors[i].pos_mult;
                        ts.ob_index   = monitors[i].ob_index;
                        ts.comment    = "EntryEngine-DT";
                        out_signals[out_count] = ts;
                        out_count++;
                    }
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
