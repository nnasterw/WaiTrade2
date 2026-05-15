//+------------------------------------------------------------------+
//| WaiTrade_OB.mq5 — 统一OB回踩策略EA (V8.4-V9.5c)                   |
//|                                                                  |
//| 模块化架构:                                                       |
//|   Config.mqh       — 所有参数 (input变量)                          |
//|   Utils.mqh        — 工具函数 (ATR/时段/特征)                      |
//|   OBDetector.mqh   — OB识别 + 信号生成                             |
//|   EntryEngine.mqh  — 入场状态机 (Bounce确认/二推不破)               |
//|   ExitEngine.mqh   — 出场逻辑 (Trailing/DTP/时间)                  |
//|   PositionManager.mqh — 仓位管理 (开单/平仓/boost)                 |
//|                                                                  |
//| 用法:                                                            |
//|   1. 编译此EA → WaiTrade_OB.ex5                                   |
//|   2. Strategy Tester → 选择此EA                                   |
//|   3. 加载.set预设文件切换版本 (V8.4/V9.3/V9.5c等)                  |
//|   4. 模式选"Every tick based on real ticks"                       |
//|   5. 运行                                                        |
//+------------------------------------------------------------------+
#property copyright "WaiTrade"
#property version   "1.00"
#property strict

#include <WaiTrade/Config.mqh>
#include <WaiTrade/Utils.mqh>
#include <WaiTrade/OBDetector.mqh>
#include <WaiTrade/EntryEngine.mqh>
#include <WaiTrade/ExitEngine.mqh>
#include <WaiTrade/PositionManager.mqh>

// === 全局对象 ===
COBDetector      g_detector;
CEntryEngine     g_entry;
CExitEngine      g_exit;
CPositionManager g_positions;

// === 状态 ===
datetime g_last_bar_time = 0;   // 上次信号扫描的bar时间
int      g_bar_count = 0;       // 持仓bar计数器
int      g_trend_1h = 0;        // 当前1H趋势

// EMA handles for 1H trend
int      g_ema20_handle = INVALID_HANDLE;
int      g_ema60_handle = INVALID_HANDLE;

//+------------------------------------------------------------------+
int OnInit()
{
   // 创建1H EMA指标 (用于趋势判断)
   g_ema20_handle = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   g_ema60_handle = iMA(_Symbol, PERIOD_H1, 60, 0, MODE_EMA, PRICE_CLOSE);

   if(g_ema20_handle == INVALID_HANDLE || g_ema60_handle == INVALID_HANDLE)
   {
      Print("[WaiTrade] 无法创建EMA指标");
      return(INIT_FAILED);
   }

   Print(StringFormat("[WaiTrade] 初始化 %s | 版本:%s | Bounce:%.0f%% | Timeout:%dmin | MaxPos:%d",
         _Symbol, InpVersion, InpBouncePct*100, InpTimeoutMin, InpMaxConcurrent));
   Print(StringFormat("[WaiTrade] Trailing: BE=%.1fR→%.1fR | L1=%.1fR→%.1fR | L2=%.1fR→×%.2f",
         InpBreakevenR, InpBreakevenLockR, InpTrail1TriggerR, InpTrail1LockR,
         InpTrail2TriggerR, InpTrail2LockMult));
   Print(StringFormat("[WaiTrade] DTP=%.1fR@%.0f%% | TimeExit=%dbars | 1HBoost=%.1fx | DS=%s",
         InpDTPTriggerR, InpDTPRetrace*100, InpTimeExitBars,
         InpBoostIn1HOB, InpDSWeight ? "ON" : "OFF"));

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_ema20_handle != INVALID_HANDLE) IndicatorRelease(g_ema20_handle);
   if(g_ema60_handle != INVALID_HANDLE) IndicatorRelease(g_ema60_handle);

   Print(StringFormat("[WaiTrade] 结束 | 总入场: %d", g_positions.GetTotalEntries()));
}

//+------------------------------------------------------------------+
void OnTick()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick)) return;

   datetime now = tick.time;
   double bid = tick.bid;
   double ask = tick.ask;
   double spread = ask - bid;

   // 诊断计数器
   static int tick_count_diag = 0;
   tick_count_diag++;

   // ============================================
   // 模块1: 定期扫描K线 → 识别OB → 生成待确认信号
   // ============================================
   datetime current_bar_time = iTime(_Symbol, InpBarTF, 0);
   if(current_bar_time != g_last_bar_time)
   {
      g_last_bar_time = current_bar_time;
      g_bar_count++;

      // 更新1H趋势 (shift=1防前瞻)
      UpdateTrend1H();

      // 获取K线数据
      MqlRates rates[];
      ArraySetAsSeries(rates, false); // 时间正序(oldest=0)
      int copied = CopyRates(_Symbol, InpBarTF, 0, InpBars, rates);
      if(copied > 60)
      {
         // OB识别
         g_detector.Detect(rates, copied, spread, g_trend_1h, g_bar_count);

         // 将新信号注册到入场引擎
         for(int i = 0; i < g_detector.GetSignalCount(); i++)
         {
            OBSignal sig = g_detector.GetSignal(i);
            g_entry.AddSignal(sig);
         }
      }
      else if(g_bar_count <= 3 || g_bar_count % 1000 == 0)
      {
         Print(StringFormat("[WaiTrade] bar#%d CopyRates=%d (<60, skip)", g_bar_count, copied));
      }

      // 诊断: 每200 bar输出状态
      if(g_bar_count % 200 == 0 || g_bar_count == 1)
      {
         Print(StringFormat("[WaiTrade] bar#%d | ticks=%d | 1H_trend=%d | spread=%.5f | CopyRates=%d | signals=%d",
               g_bar_count, tick_count_diag, g_trend_1h, spread, copied,
               g_detector.GetSignalCount()));
      }
   }

   // ============================================
   // 模块2: 入场检查 (每tick)
   // ============================================
   if(g_positions.CanOpen(now))
   {
      EntryDecision decisions[];
      ArrayResize(decisions, 5);
      int dec_count = g_entry.Update(bid, ask, now, decisions, 5);

      for(int i = 0; i < dec_count; i++)
      {
         if(!decisions[i].should_enter) continue;
         if(!g_positions.CanOpen(now)) break;

         double balance = AccountInfoDouble(ACCOUNT_BALANCE);
         g_positions.OpenPosition(decisions[i], balance, g_bar_count);
      }
   }

   // ============================================
   // 模块3: 出场检查 (每tick, 和live一致)
   // ============================================
   for(int i = g_positions.GetOpenCount() - 1; i >= 0; i--)
   {
      PositionState pos;
      if(!g_positions.GetPosition(i, pos)) continue;
      if(!pos.active) continue;

      double check_price = (pos.direction == "long") ? bid : ask;
      int elapsed_bars = g_bar_count - pos.entry_bar;

      ExitDecision exit_dec = g_exit.Update(
         check_price, pos.entry_price, pos.initial_sl,
         pos.current_sl, pos.initial_risk,
         pos.max_favorable_r, elapsed_bars, pos.direction
      );

      // Fix: 每tick写回max_favorable_r(不只是trailing触发时)
      g_positions.UpdatePosition(i, pos.max_favorable_r,
         (exit_dec.new_sl > 0) ? exit_dec.new_sl : pos.current_sl);

      if(exit_dec.should_exit)
      {
         string reason_str;
         switch(exit_dec.reason)
         {
            case EXIT_SL:          reason_str = "SL"; break;
            case EXIT_TRAILING_SL: reason_str = "Trail"; break;
            case EXIT_DTP:         reason_str = "DTP"; break;
            case EXIT_TIME_TP:     reason_str = "TimeTP"; break;
            case EXIT_TIMEOUT:     reason_str = "Timeout"; break;
            case EXIT_TIME_DECAY:  reason_str = "Decay"; break;
            default:               reason_str = "Unknown";
         }
         g_positions.ClosePosition(i, reason_str);
      }
      else if(exit_dec.new_sl > 0)
      {
         g_positions.ModifySL(i, exit_dec.new_sl);
      }
   }

   // ============================================
   // 模块4: 同步持仓状态 (每100个tick检查一次)
   // ============================================
   static int tick_count = 0;
   tick_count++;
   if(tick_count % 100 == 0)
      g_positions.SyncPositions();
}

//+------------------------------------------------------------------+
void UpdateTrend1H()
{
   double ema20[], ema60[];
   ArraySetAsSeries(ema20, true);
   ArraySetAsSeries(ema60, true);

   // shift=1: 用前一根完成的1H bar (防前瞻)
   if(CopyBuffer(g_ema20_handle, 0, 1, 1, ema20) <= 0) return;
   if(CopyBuffer(g_ema60_handle, 0, 1, 1, ema60) <= 0) return;

   if(ema20[0] > ema60[0]) g_trend_1h = 1;
   else if(ema20[0] < ema60[0]) g_trend_1h = -1;
   else g_trend_1h = 0;
}
//+------------------------------------------------------------------+
