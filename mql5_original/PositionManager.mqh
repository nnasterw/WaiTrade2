//+------------------------------------------------------------------+
//| PositionManager.mqh — 仓位管理 (开单/平仓/并发控制/1H boost)        |
//+------------------------------------------------------------------+
#ifndef __WAITRADE_POSITIONMANAGER_MQH__
#define __WAITRADE_POSITIONMANAGER_MQH__

#include <Trade/Trade.mqh>
#include "Config.mqh"
#include "EntryEngine.mqh"

#define MAX_POSITIONS 20
#define MAGIC_NUMBER  20260512

struct PositionState
{
   ulong    ticket;
   string   direction;
   double   entry_price;
   double   initial_sl;
   double   current_sl;
   double   initial_risk;
   double   max_favorable_r;
   int      entry_bar;        // 入场时的bar计数
   double   pos_mult;
   bool     is_addon;         // 二推加仓单
   bool     active;
};

class CPositionManager
{
private:
   CTrade         m_trade;
   PositionState  m_positions[MAX_POSITIONS];
   int            m_pos_count;
   int            m_total_entries;
   datetime       m_last_exit_time;
   double         m_initial_deposit;  // 固定初始资金(不复利)

public:
   CPositionManager()
   {
      m_pos_count = 0;
      m_total_entries = 0;
      m_last_exit_time = 0;
      m_initial_deposit = 0;
      m_trade.SetExpertMagicNumber(MAGIC_NUMBER);
      m_trade.SetDeviationInPoints(20);
      m_trade.SetTypeFilling(ORDER_FILLING_IOC);
   }

   void SetInitialDeposit(double dep) { m_initial_deposit = dep; }
   int GetOpenCount()   { return m_pos_count; }
   int GetTotalEntries(){ return m_total_entries; }

   // 检查是否可以开新仓
   bool CanOpen(datetime now)
   {
      if(InpMaxConcurrent > 0 && m_pos_count >= InpMaxConcurrent)
         return false;
      if(InpCooldownBars > 0 && m_last_exit_time > 0)
      {
         int cooldown_sec = InpCooldownBars * PeriodSeconds(InpBarTF);
         if((int)(now - m_last_exit_time) < cooldown_sec)
            return false;
      }
      return true;
   }

   // 开仓 (和live对齐: 固定初始资金计算risk, 不复利)
   bool OpenPosition(const EntryDecision &dec, double account_balance, int current_bar = 0)
   {
      double risk = MathAbs(dec.entry_price - dec.sl);
      if(risk <= 0) return false;

      // OB大小过滤
      double ob_height = dec.ob_top - dec.ob_bottom;
      if(ob_height <= 0) ob_height = risk * 2;
      double spread = GetSpread();
      if(ob_height < spread * InpMinOBSpreadMult) return false;
      if(InpMinRiskSpreadRatio > 0 && spread > 0)
         if(risk / spread < InpMinRiskSpreadRatio) return false;
      if(InpMinAbsRiskUSD > 0 && risk < InpMinAbsRiskUSD) return false;

      // === 仓位计算 (和live完全对齐: 用当前余额, 自然复利) ===
      double risk_amount = account_balance * InpRiskPercent / 100.0;

      // 2. pos_mult: boost放大仓位 (和live一致)
      double pos_mult = dec.pos_mult;  // OB分类已含fresh/cont boost
      if(InpBoostIn1HOB > 1.0 && IsIn1HOB(dec.entry_price, dec.direction))
         pos_mult *= InpBoostIn1HOB;
      if(InpDSWeight)
         pos_mult *= MathMin(dec.ds * 1.5, 2.5);

      double volume = CalcVolume(risk_amount * pos_mult, risk, dec.entry_price);

      // 3. Margin检查: 防止超出可用保证金
      double margin_required = 0;
      if(OrderCalcMargin(dec.direction == "long" ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,
                         _Symbol, volume, dec.entry_price, margin_required))
      {
         double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
         if(margin_required > free_margin * 0.8)  // 最多用80%可用保证金
         {
            volume = CalcVolume(risk_amount, risk, dec.entry_price);  // 降级到1x
            if(volume <= 0) return false;
         }
      }
      if(volume <= 0) return false;

      // 下单
      bool ok = false;
      if(dec.direction == "long")
         ok = m_trade.Buy(volume, _Symbol, 0, dec.sl, 0, StringFormat("WT_%s", InpVersion));
      else
         ok = m_trade.Sell(volume, _Symbol, 0, dec.sl, 0, StringFormat("WT_%s", InpVersion));

      if(ok)
      {
         ulong ticket = m_trade.ResultOrder();
         if(ticket > 0 && m_pos_count < MAX_POSITIONS)
         {
            m_positions[m_pos_count].ticket = ticket;
            m_positions[m_pos_count].direction = dec.direction;
            m_positions[m_pos_count].entry_price = m_trade.ResultPrice();
            m_positions[m_pos_count].initial_sl = dec.sl;
            m_positions[m_pos_count].current_sl = dec.sl;
            m_positions[m_pos_count].initial_risk = risk;
            m_positions[m_pos_count].max_favorable_r = 0;
            m_positions[m_pos_count].entry_bar = current_bar;
            m_positions[m_pos_count].pos_mult = pos_mult;
            m_positions[m_pos_count].is_addon = false;
            m_positions[m_pos_count].active = true;
            m_pos_count++;
            m_total_entries++;
            return true;
         }
      }
      return false;
   }

   // 修改SL
   bool ModifySL(int idx, double new_sl)
   {
      if(idx < 0 || idx >= m_pos_count) return false;
      if(!m_positions[idx].active) return false;

      if(!PositionSelectByTicket(m_positions[idx].ticket)) return false;

      double current_sl = PositionGetDouble(POSITION_SL);
      string symbol = PositionGetString(POSITION_SYMBOL);
      int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      new_sl = NormalizeDouble(new_sl, digits);
      if(MathAbs(new_sl - current_sl) < SymbolInfoDouble(symbol, SYMBOL_POINT))
         return true;

      if(m_trade.PositionModify(m_positions[idx].ticket, new_sl, 0))
      {
         m_positions[idx].current_sl = new_sl;
         return true;
      }
      return false;
   }

   // 平仓
   bool ClosePosition(int idx, string comment="")
   {
      if(idx < 0 || idx >= m_pos_count) return false;
      if(!m_positions[idx].active) return false;

      if(m_trade.PositionClose(m_positions[idx].ticket))
      {
         m_positions[idx].active = false;
         m_last_exit_time = TimeCurrent();
         CleanUp();
         return true;
      }
      return false;
   }

   // 获取持仓状态 (直接访问内部数组)
   bool GetPosition(int idx, PositionState &out)
   {
      if(idx < 0 || idx >= m_pos_count) return false;
      out = m_positions[idx];
      return true;
   }

   // 更新持仓的max_favorable_r和current_sl
   void UpdatePosition(int idx, double max_r, double new_sl)
   {
      if(idx >= 0 && idx < m_pos_count)
      {
         m_positions[idx].max_favorable_r = max_r;
         m_positions[idx].current_sl = new_sl;
      }
   }

   // 同步MT5真实持仓 (防止不一致)
   void SyncPositions()
   {
      for(int i = m_pos_count - 1; i >= 0; i--)
      {
         if(!m_positions[i].active) continue;
         if(!PositionSelectByTicket(m_positions[i].ticket))
         {
            m_positions[i].active = false;
         }
      }
      CleanUp();
   }

private:
   double CalcVolume(double risk_usd, double risk_points, double price)
   {
      double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      double tick_size  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      double min_lot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double max_lot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
      double lot_step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

      if(tick_value <= 0 || tick_size <= 0 || risk_points <= 0) return 0;

      double ticks = risk_points / tick_size;
      double volume = risk_usd / (ticks * tick_value);

      // 规范化
      volume = MathMax(volume, min_lot);
      volume = MathMin(volume, max_lot);
      volume = MathFloor(volume / lot_step) * lot_step;

      return volume;
   }

   // 检查entry是否在1H OB区域内
   bool IsIn1HOB(double entry_price, string direction)
   {
      MqlRates rates_1h[];
      ArraySetAsSeries(rates_1h, true);
      int copied = CopyRates(_Symbol, PERIOD_H1, 0, 200, rates_1h);
      if(copied < 60) return false;

      // 简化版1H OB检测: 找最近的位移K线
      for(int i = 1; i < copied - 1 && i < 24; i++)
      {
         double body = MathAbs(rates_1h[i].close - rates_1h[i].open);
         double range = rates_1h[i].high - rates_1h[i].low;
         if(range <= 0) continue;
         double body_pct = body / range;
         if(body_pct < 0.6) continue;

         // Bullish 1H OB
         if(rates_1h[i].close > rates_1h[i].open && direction == "long")
         {
            double ob_top = rates_1h[i+1].open; // 前一根(bearish)的open
            double ob_bot = rates_1h[i+1].close;
            if(rates_1h[i+1].close < rates_1h[i+1].open) // 确认前一根是bearish
            {
               if(entry_price >= ob_bot && entry_price <= ob_top)
                  return true;
            }
         }
         // Bearish 1H OB
         if(rates_1h[i].close < rates_1h[i].open && direction == "short")
         {
            double ob_top = rates_1h[i+1].close;
            double ob_bot = rates_1h[i+1].open;
            if(rates_1h[i+1].close > rates_1h[i+1].open)
            {
               if(entry_price >= ob_bot && entry_price <= ob_top)
                  return true;
            }
         }
      }
      return false;
   }

   double GetSpread()
   {
      return SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
   }

   void CleanUp()
   {
      int new_count = 0;
      for(int i = 0; i < m_pos_count; i++)
      {
         if(m_positions[i].active)
         {
            if(i != new_count)
               m_positions[new_count] = m_positions[i];
            new_count++;
         }
      }
      m_pos_count = new_count;
   }
};

#endif
