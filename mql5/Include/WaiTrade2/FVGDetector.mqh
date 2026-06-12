#ifndef __WAITRADE_FVG_DETECTOR_MQH__
#define __WAITRADE_FVG_DETECTOR_MQH__

#include "Types.mqh"
#include "Config.mqh"
#include "MathUtils.mqh"
#include "TradeOps.mqh"

// ═══════════════════════════════════════════════════════════════════════════
// FVG (公允价值缺口) 检测模块 — SMC三要素第三原语
//
// FVG定义: 3根连续K线中, 第1根和第3根的价格区间不重叠
//   Bullish FVG: low[newest] > high[oldest] → 价格跳空上涨, 留下下方失衡
//   Bearish FVG: high[newest] < low[oldest] → 价格跳空下跌, 留下上方失衡
//
// SMC中的角色:
//   趋势市: FVG回补后继续原方向 (follow)
//   震荡市: FVG+区间边界Sweep后反向入场 (fade)
// ═══════════════════════════════════════════════════════════════════════════

// 检测单根K线是否为强位移(displacement)蜡烛
// 强位移 = 实体占比高 + 相对ATR足够大 + 收盘方向一致
bool IsDisplacementCandle(const MqlRates &bar, double atr, int direction)
{
   if(atr <= 0) return false;

   double body = MathAbs(bar.open - bar.close);
   double range = bar.high - bar.low;
   if(range <= 0) return false;

   // 实体占比至少40% (排除纯影线假突破)
   if(body / range < 0.40) return false;

   // 位移幅度至少0.3 ATR
   if(body < atr * 0.3) return false;

   // 收盘方向检查
   if(direction == OB_BUY && bar.close <= bar.open) return false;
   if(direction == OB_SELL && bar.close >= bar.open) return false;

   return true;
}

// 检测FVG是否与已存在的FVG重叠(去重)
bool IsFVGDuplicate(const OBZone &zones[], int zone_count, double gap_top, double gap_bottom,
                    int direction, double atr)
{
   for(int z = 0; z < zone_count; z++)
   {
      if(zones[z].expired || !zones[z].is_fvg) continue;
      if(zones[z].direction != direction) continue;
      // 重叠容差: 0.15 ATR
      double tol = atr * 0.15;
      if(MathAbs(zones[z].high - gap_top) < tol &&
         MathAbs(zones[z].low - gap_bottom) < tol)
         return true;
   }
   return false;
}

// 主FVG检测函数: 扫描3-bar失衡并在震荡市边界标记高价值FVG
void DetectFVGs(const MqlRates &rates[], int count, OBZone &zones[], int &zone_count,
                const EAState &state, double atr, double spread)
{
   if(!InpEnableFVG)
      return;
   if(zone_count >= MAX_OB_ZONES)
      return;
   if(atr <= 0)
      return;

   static int s_fvg_total_created = 0;

   int lookback = InpFVGLookbackBars;
   if(lookback < 3) lookback = 3;
   if(lookback > 200) lookback = 200;

   // 从count-3开始扫描(需要oldest/middle/newest三根完整K线)
   int scan_start = count - 3;
   int scan_end = MathMax(1, count - lookback);
   if(scan_start < scan_end) return;

   double min_gap = atr * InpFVGMinGapATR;

   for(int oldest = scan_start; oldest >= scan_end; oldest--)
   {
      if(zone_count >= MAX_OB_ZONES) break;

      int middle = oldest + 1;
      int newest = oldest + 2;

      // ── Bullish FVG: 价格跳空上涨 ──────────────────────────
      // low[newest] > high[oldest] → 第3根完全在第1根上方
      if(rates[newest].low > rates[oldest].high)
      {
         double gap_top = rates[newest].low;
         double gap_bottom = rates[oldest].high;
         double gap_size = gap_top - gap_bottom;

         // 最小缺口过滤
         if(gap_size < min_gap) continue;
         // 最大缺口过滤(异常大缺口非正常FVG)
         if(InpFVGMaxGapATR > 0 && gap_size > atr * InpFVGMaxGapATR) continue;

         // 位移蜡烛质量: middle bar必须是强bullish impulse
         if(!IsDisplacementCandle(rates[middle], atr, OB_BUY)) continue;

         // 去重
         if(IsFVGDuplicate(zones, zone_count, gap_top, gap_bottom, OB_BUY, atr)) continue;

         // 时段过滤
         MqlDateTime dt;
         TimeToStruct(rates[newest].time, dt);
         if(IsInNoOBWindow(dt.hour)) continue;  // 复用OB的禁止时段

         OBZone zone = {};
         zone.high = gap_top;
         zone.low = gap_bottom;
         zone.mid = (zone.high + zone.low) / 2.0;
         zone.ob_top = zone.high;
         zone.ob_bottom = zone.low;
         zone.direction = OB_BUY;  // Bullish FVG = 看涨失衡
         zone.created = rates[newest].time;
         zone.created_bar = state.bar_count - (count - 1 - newest);
         zone.touch_count = 0;
         zone.first_touch = 0;
         zone.last_touch = 0;
         // FVG强度: 基于缺口大小和位移质量
         double disp_quality = MathAbs(rates[middle].close - rates[middle].open) / atr;
         zone.strength = MathMin(5.0, 1.0 + (gap_size / atr) * 1.5 + disp_quality * 0.5);
         zone.is_fresh = true;
         zone.is_continuation = false;
         zone.is_1h_aligned = false;
         zone.ds_weight = 1.0;
         zone.entry_count = 0;
         zone.last_entry_time = 0;
         zone.used = false;
         zone.expired = false;
         zone.is_range_breakout = false;
         zone.is_liquidity_sweep = false;
         zone.is_loose_sweep = false;
         zone.is_htf_pullback = false;
         zone.range_height = gap_size;
         // FVG专属字段
         zone.is_fvg = true;
         zone.fvg_filled = false;
         zone.fvg_formed_time = rates[newest].time;
         zone.fvg_mitigation_price = zone.mid;  // 50%回补位

         zones[zone_count] = zone;
         zone_count++;
      }

      // ── Bearish FVG: 价格跳空下跌 ──────────────────────────
      if(rates[newest].high < rates[oldest].low)
      {
         double gap_top = rates[oldest].low;
         double gap_bottom = rates[newest].high;
         double gap_size = gap_top - gap_bottom;

         if(gap_size < min_gap) continue;
         if(InpFVGMaxGapATR > 0 && gap_size > atr * InpFVGMaxGapATR) continue;

         // 位移蜡烛: middle bar必须是强bearish impulse
         if(!IsDisplacementCandle(rates[middle], atr, OB_SELL)) continue;

         if(IsFVGDuplicate(zones, zone_count, gap_top, gap_bottom, OB_SELL, atr)) continue;

         MqlDateTime dt;
         TimeToStruct(rates[newest].time, dt);
         if(IsInNoOBWindow(dt.hour)) continue;

         OBZone zone = {};
         zone.high = gap_top;
         zone.low = gap_bottom;
         zone.mid = (zone.high + zone.low) / 2.0;
         zone.ob_top = zone.high;
         zone.ob_bottom = zone.low;
         zone.direction = OB_SELL;  // Bearish FVG = 看跌失衡
         zone.created = rates[newest].time;
         zone.created_bar = state.bar_count - (count - 1 - newest);
         zone.touch_count = 0;
         zone.first_touch = 0;
         zone.last_touch = 0;
         double disp_quality = MathAbs(rates[middle].close - rates[middle].open) / atr;
         zone.strength = MathMin(5.0, 1.0 + (gap_size / atr) * 1.5 + disp_quality * 0.5);
         zone.is_fresh = true;
         zone.is_continuation = false;
         zone.is_1h_aligned = false;
         zone.ds_weight = 1.0;
         zone.entry_count = 0;
         zone.last_entry_time = 0;
         zone.used = false;
         zone.expired = false;
         zone.is_range_breakout = false;
         zone.is_liquidity_sweep = false;
         zone.is_loose_sweep = false;
         zone.is_htf_pullback = false;
         zone.range_height = gap_size;
         zone.is_fvg = true;
         zone.fvg_filled = false;
         zone.fvg_formed_time = rates[newest].time;
         zone.fvg_mitigation_price = zone.mid;

         zones[zone_count] = zone;
         zone_count++;
         s_fvg_total_created++;
      }
   }
}

// 更新FVG状态: 检测价格是否已回补缺口
// 震荡市: 回补=入场机会(消解确认)
// 趋势市: 回补=方向确认(继续原趋势)
void UpdateFVGStatus(OBZone &zones[], int &zone_count, double bid, double ask, const EAState &state)
{
   for(int i = zone_count - 1; i >= 0; i--)
   {
      if(!zones[i].is_fvg || zones[i].expired || zones[i].used)
         continue;

      // FVG过期: 超过最大存活bars
      int bars_alive = state.bar_count - zones[i].created_bar;
      if(InpFVGMaxAgeBars > 0 && bars_alive > InpFVGMaxAgeBars)
      {
         zones[i].expired = true;
         continue;
      }

      // 常规过期(全局bars配置)
      if(bars_alive > InpBars)
      {
         zones[i].expired = true;
         continue;
      }

      // FVG时间过期
      if(InpFVGTimeoutMin > 0)
      {
         long minutes_alive = (long)(TimeCurrent() - zones[i].created) / 60;
         if(minutes_alive > InpFVGTimeoutMin)
         {
            zones[i].expired = true;
            continue;
         }
      }

      // 检测价格是否进入FVG区域(回补)
      bool in_gap = false;
      if(zones[i].direction == OB_BUY)
      {
         // Bullish FVG: 价格下跌回补缺口
         if(bid <= zones[i].high && bid >= zones[i].low)
            in_gap = true;
      }
      else
      {
         // Bearish FVG: 价格上涨回补缺口
         if(ask >= zones[i].low && ask <= zones[i].high)
            in_gap = true;
      }

      if(in_gap && !zones[i].fvg_filled)
      {
         zones[i].fvg_filled = true;
         zones[i].is_fresh = false;
         zones[i].first_touch = TimeCurrent();
         zones[i].last_touch = TimeCurrent();
         zones[i].touch_count = 1;
      }
      else if(in_gap)
      {
         zones[i].last_touch = TimeCurrent();
         zones[i].touch_count++;
      }
   }
}

// 检查FVG是否在当前震荡区间边界附近(高价值fade信号)
// 仅当FVG靠近区间边界时才认为是有意义的fade信号
bool IsFVGAtRangeBoundary(const OBZone &fvg, double range_high, double range_low, double atr)
{
   if(range_high <= range_low || atr <= 0) return false;

   double tolerance = atr * 0.3;  // 30% ATR容差

   if(fvg.direction == OB_BUY)
   {
      // Bullish FVG在区间上沿附近 → 假突破fade信号(做空)
      return (MathAbs(fvg.mid - range_high) < tolerance);
   }
   else
   {
      // Bearish FVG在区间下沿附近 → 假突破fade信号(做多)
      return (MathAbs(fvg.mid - range_low) < tolerance);
   }
}

// 获取FVG对侧目标价(区间fade模式)
// Bullish FVG在区间上沿 → 目标=区间下沿
// Bearish FVG在区间下沿 → 目标=区间上沿
double GetFVGFadeTarget(const OBZone &fvg, double range_high, double range_low)
{
   if(range_high <= range_low) return 0.0;

   if(fvg.direction == OB_BUY)
      return range_low;   // 做空目标=区间下沿
   else
      return range_high;  // 做多目标=区间上沿
}

#endif
