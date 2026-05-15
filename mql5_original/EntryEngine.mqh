//+------------------------------------------------------------------+
//| EntryEngine.mqh — 入场状态机 (Bounce确认 + 二推不破)                |
//+------------------------------------------------------------------+
#ifndef __WAITRADE_ENTRYENGINE_MQH__
#define __WAITRADE_ENTRYENGINE_MQH__

#include "Config.mqh"
#include "OBDetector.mqh"

#define MAX_MONITORS 20

enum ENUM_ENTRY_PHASE
{
   PHASE_WAITING_TOUCH,    // 等待价格触及OB
   PHASE_WAITING_BOUNCE,   // 已触及, 等反弹
   PHASE_WAITING_DOUBLE,   // 等第二次触及(二推不破)
   PHASE_CONFIRMED,        // bounce已确认
   PHASE_EXPIRED,          // 过期
   PHASE_ENTERED           // 已入场
};

struct EntryMonitor
{
   OBSignal       signal;
   ENUM_ENTRY_PHASE phase;
   datetime       expire_time;     // 超时时间
   double         touch_price;     // 触及价格
   datetime       touch_time;      // 触及时间
   double         confirm_price;   // 确认价格
   datetime       confirm_time;    // 确认时间
   int            touch_count;     // 触及次数(二推不破用)
   bool           active;
};

struct EntryDecision
{
   bool     should_enter;
   string   direction;
   double   entry_price;
   double   sl;
   double   pos_mult;
   double   ob_top;
   double   ob_bottom;
   double   ds;
   string   tier;
};

class CEntryEngine
{
private:
   EntryMonitor m_monitors[MAX_MONITORS];
   int          m_count;

public:
   CEntryEngine() { m_count = 0; }

   // 注册新信号进行监控
   void AddSignal(const OBSignal &sig)
   {
      if(m_count >= MAX_MONITORS) return;

      m_monitors[m_count].signal = sig;
      m_monitors[m_count].phase = PHASE_WAITING_TOUCH;
      m_monitors[m_count].expire_time = TimeCurrent() + InpTimeoutMin * 60;
      m_monitors[m_count].touch_price = 0;
      m_monitors[m_count].touch_time = 0;
      m_monitors[m_count].confirm_price = 0;
      m_monitors[m_count].confirm_time = 0;
      m_monitors[m_count].touch_count = 0;
      m_monitors[m_count].active = true;
      m_count++;
   }

   // 每tick更新, 返回可入场的决策数
   int Update(double bid, double ask, datetime now, EntryDecision &decisions[], int max_decisions)
   {
      int dec_count = 0;

      for(int i = 0; i < m_count; i++)
      {
         if(!m_monitors[i].active) continue;
         if(now > m_monitors[i].expire_time)
         {
            m_monitors[i].phase = PHASE_EXPIRED;
            m_monitors[i].active = false;
            continue;
         }

         OBSignal sig = m_monitors[i].signal;
         double entry_price = sig.entry;
         double ob_height = sig.ob_top - sig.ob_bottom;
         if(ob_height <= 0) ob_height = MathAbs(entry_price - sig.sl) * 2;
         double threshold = ob_height * InpBouncePct;
         double risk = MathAbs(entry_price - sig.sl);
         if(risk <= 0) { m_monitors[i].active = false; continue; }

         double price = (sig.direction == "long") ? bid : ask;

         // Phase: 等待触及
         if(m_monitors[i].phase == PHASE_WAITING_TOUCH)
         {
            bool touched = false;
            if(sig.direction == "long" && price <= entry_price) touched = true;
            if(sig.direction == "short" && price >= entry_price) touched = true;

            if(touched)
            {
               m_monitors[i].touch_price = price;
               m_monitors[i].touch_time = now;
               m_monitors[i].touch_count++;

               if(InpRequireDoubleTch && m_monitors[i].touch_count < 2)
                  m_monitors[i].phase = PHASE_WAITING_DOUBLE;
               else
                  m_monitors[i].phase = PHASE_WAITING_BOUNCE;
            }
         }
         // Phase: 等二推 (第一次触及后等反弹再回来)
         else if(m_monitors[i].phase == PHASE_WAITING_DOUBLE)
         {
            // 检查是否先反弹了
            bool bounced = false;
            if(sig.direction == "long" && price - entry_price >= threshold) bounced = true;
            if(sig.direction == "short" && entry_price - price >= threshold) bounced = true;

            if(bounced)
            {
               // 反弹后等第二次触及
               m_monitors[i].phase = PHASE_WAITING_TOUCH;
               // touch_count已经是1, 下次触及就变2
            }
            // 二推窗口超时
            if((int)(now - m_monitors[i].touch_time) > InpDoubleTchWindowMin * 60)
            {
               m_monitors[i].active = false;
               m_monitors[i].phase = PHASE_EXPIRED;
            }
         }
         // Phase: 等待bounce确认
         else if(m_monitors[i].phase == PHASE_WAITING_BOUNCE)
         {
            bool confirmed = false;
            if(sig.direction == "long" && price - entry_price >= threshold) confirmed = true;
            if(sig.direction == "short" && entry_price - price >= threshold) confirmed = true;

            if(confirmed)
            {
               m_monitors[i].confirm_price = price;
               m_monitors[i].confirm_time = now;
               m_monitors[i].phase = PHASE_CONFIRMED;

               // offset检查
               double offset_r = MathAbs(price - entry_price) / risk;
               if(offset_r > InpMaxEntryOffsetR)
               {
                  m_monitors[i].phase = PHASE_EXPIRED;
                  m_monitors[i].active = false;
                  continue;
               }

               // 生成入场决策
               if(dec_count < max_decisions)
               {
                  decisions[dec_count].should_enter = true;
                  decisions[dec_count].direction = sig.direction;
                  decisions[dec_count].entry_price = price;
                  decisions[dec_count].sl = sig.sl;
                  decisions[dec_count].pos_mult = sig.pos_mult;
                  decisions[dec_count].ob_top = sig.ob_top;
                  decisions[dec_count].ob_bottom = sig.ob_bottom;
                  decisions[dec_count].ds = sig.ds;
                  decisions[dec_count].tier = sig.tier;
                  dec_count++;
               }
               m_monitors[i].phase = PHASE_ENTERED;
               m_monitors[i].active = false;
            }
         }
      }

      // 清理不活跃的monitors
      CleanUp();
      return dec_count;
   }

   int GetActiveCount()
   {
      int c = 0;
      for(int i = 0; i < m_count; i++)
         if(m_monitors[i].active) c++;
      return c;
   }

   void Clear() { m_count = 0; }

private:
   void CleanUp()
   {
      int new_count = 0;
      for(int i = 0; i < m_count; i++)
      {
         if(m_monitors[i].active)
         {
            if(i != new_count)
               m_monitors[new_count] = m_monitors[i];
            new_count++;
         }
      }
      m_count = new_count;
   }
};

#endif
