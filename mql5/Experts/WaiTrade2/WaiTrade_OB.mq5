#property copyright "WaiTrade2"
#property version   "98.01"
#property strict

#include <WaiTrade2/Config.mqh>
#include <WaiTrade2/Types.mqh>
#include <WaiTrade2/Utils.mqh>
#include <WaiTrade2/MarketState.mqh>
#include <WaiTrade2/ScoreEngine.mqh>
#include <WaiTrade2/DecayDetector.mqh>
#include <WaiTrade2/OBDetector.mqh>
#include <WaiTrade2/SignalEngine.mqh>
#include <WaiTrade2/EntryEngine.mqh>
#include <WaiTrade2/PositionManager.mqh>

OBZone      g_zones[MAX_OB_ZONES];
PosTrack    g_tracks[MAX_POSITIONS];
EAState     g_state;
TradeSignal g_signals[10];
int         g_track_count = 0;

// v9.8a EntryEngine
EntryMonitor g_monitors[MAX_MONITORS];
int          g_monitor_count = 0;
datetime     g_last_entry_attempt = 0;

int OnInit()
{
    ZeroMemory(g_state);
    ZeroMemory(g_zones);
    ZeroMemory(g_tracks);
    g_track_count = 0;
    g_monitor_count = 0;
    g_last_entry_attempt = 0;

    if(InpRiskPercent <= 0 || InpRiskPercent > 50)
    {
        Print("参数错误: InpRiskPercent=", InpRiskPercent);
        return INIT_PARAMETERS_INCORRECT;
    }

    Print("WaiTrade2 ", InpVersion, " 已加载 | ", _Symbol, " | Magic=", InpMagicNumber);
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    Print("WaiTrade2 ", InpVersion, " 已卸载 | 原因=", reason);
}

void OnTick()
{
    string symbol = _Symbol;
    ENUM_TIMEFRAMES tf = GetWorkTF();

    // 1. 加载K线数据
    MqlRates rates[];
    int copied = CopyRates(symbol, tf, 0, InpBars, rates);
    if(copied < 100) return;

    g_state.atr_value = CalcATR(rates, copied, InpATRPeriod);

    // 2. 新bar处理
    bool new_bar = IsNewBar(symbol, tf);
    if(new_bar)
    {
        g_state.bar_count++;

        DetectOrderBlocks(rates, copied, g_zones, g_state.ob_count, g_state);

        if(InpConsolidateOB)
            ConsolidateOBs(g_zones, g_state.ob_count);

        MqlRates rates_h1[];
        int h1_count = CopyRates(symbol, PERIOD_H1, 0, 100, rates_h1);
        if(h1_count > InpATRPeriod)
            g_state.atr_1h = CalcATR(rates_h1, h1_count, InpATRPeriod);

        int h1_dir = Detect1HOBDirection(symbol);
        Update1HAlignment(g_zones, g_state.ob_count, h1_dir);

        // v9.8: M15 市场状态检测
        if(InpEnableStateFilter || InpEnableScoring)
        {
            double target = 0;
            g_state.market_state = (int)DetectMarketState(symbol, target);
            g_state.target_price = target;

            MqlRates rates_m15[];
            int m15_count = CopyRates(symbol, PERIOD_M15, 0, InpTrendLookback, rates_m15);
            if(m15_count > 14)
                g_state.atr_m15 = CalcATR(rates_m15, m15_count, InpATRPeriod);
        }
    }

    // 3. 更新OB状态(每tick)
    double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
    UpdateOBStatus(g_zones, g_state.ob_count, bid, ask, g_state);

    // 4. 扫描入场信号
    g_state.pos_count = CountPositions();

    if(InpEnableEntryEngine)
    {
        // v9.8a: EntryEngine 状态机模式
        // 新 bar 时将活跃 OB 注册为 monitor（不做 touch 检查，由 EntryEngine 处理）
        if(new_bar)
        {
            double spread = GetSpread(symbol);
            for(int z = 0; z < g_state.ob_count; z++)
            {
                if(g_zones[z].expired || g_zones[z].used) continue;
                if(!PassOBReentryCooldown(g_zones[z])) continue;

                // 态过滤：趋势态禁止逆势
                if(InpEnableStateFilter && g_state.market_state != 0
                   && g_state.market_state != g_zones[z].direction)
                    continue;

                // 基本过滤：spread ratio
                double risk_dist = (g_zones[z].direction == OB_BUY)
                    ? ((g_zones[z].high + g_zones[z].low) / 2.0) - (g_zones[z].low - g_state.atr_value * InpSLBufferATR)
                    : (g_zones[z].high + g_state.atr_value * InpSLBufferATR) - ((g_zones[z].high + g_zones[z].low) / 2.0);
                if(spread > 0 && risk_dist / spread < InpMinRiskSpreadRatio)
                    continue;

                // 构造临时 signal 用于注册
                TradeSignal tmp;
                ZeroMemory(tmp);
                tmp.direction = g_zones[z].direction;
                tmp.sl = (g_zones[z].direction == OB_BUY)
                    ? g_zones[z].low - g_state.atr_value * InpSLBufferATR
                    : g_zones[z].high + g_state.atr_value * InpSLBufferATR;
                tmp.risk_price = MathAbs(((g_zones[z].high + g_zones[z].low) / 2.0) - tmp.sl);
                tmp.ob_index = z;
                tmp.pos_mult = 1.0;

                // 评分系统
                if(InpEnableScoring)
                {
                    double prox = (g_state.atr_m15 > 0) ? g_state.atr_m15 : g_state.atr_value * 5;
                    int score = CalcSignalScore(g_zones[z], g_state, g_state.market_state, prox, tmp.risk_price, 0);
                    if(score < InpMinScore) continue;
                    double mult = ScoreToMultiplier(score);
                    if(mult < 0) continue;
                    tmp.pos_mult = mult;
                }

                AddEntryMonitor(tmp, g_zones[z], g_monitors, g_monitor_count);
            }
        }

        // 每 tick 更新 monitors，获取确认的入场
        TradeSignal confirmed[10];
        int conf_count = UpdateEntryMonitors(bid, ask, TimeCurrent(), g_monitors, g_monitor_count, confirmed, 10);

        // 5. 执行确认的入场
        for(int i = 0; i < conf_count; i++)
        {
            if(g_state.pos_count >= InpMaxConcurrent) break;
            if(confirmed[i].ob_index < 0 || confirmed[i].ob_index >= g_state.ob_count)
                continue;
            if(!FinalizeEntryEngineSignal(symbol, g_zones[confirmed[i].ob_index], g_state, confirmed[i]))
                continue;

            if(ExecuteSignal(confirmed[i]))
            {
                g_state.last_entry_bar = g_state.bar_count;
                g_state.pos_count++;
            }
        }
    }
    else
    {
        // 原始模式: 直接入场
        int sig_count = ScanSignals(symbol, g_zones, g_state.ob_count, g_state, g_signals, 10);

        // 5. 执行入场
        for(int i = 0; i < sig_count; i++)
        {
            if(g_state.pos_count >= InpMaxConcurrent) break;
            if(ExecuteSignal(g_signals[i]))
            {
                g_state.last_entry_bar = g_state.bar_count;
                g_state.pos_count++;
            }
        }
    }

    // 6. 每小时存活日志
    {
        static datetime s_last_hb = 0;
        datetime now_t = TimeCurrent();
        if(now_t - s_last_hb >= 3600)
        {
            s_last_hb = now_t;
            double spread = (double)(SymbolInfoInteger(symbol, SYMBOL_SPREAD));
            Print("HEARTBEAT ", InpVersion, " | ", symbol, " ", EnumToString(tf),
                  " | bar=", g_state.bar_count,
                  " | ob=", g_state.ob_count,
                  " | pos=", g_state.pos_count,
                  " | atr=", DoubleToString(g_state.atr_value, _Digits),
                  " | spread=", spread,
                  " | state=", g_state.market_state);
        }
    }

    // 7. 持仓管理
    SyncPositions(g_tracks, g_track_count);
    ManagePositions(g_tracks, g_track_count, g_state);
}

bool ShouldSkipEntryAttempt()
{
    if(InpCloseRetryCooldownSec <= 0)
        return false;

    datetime now = TimeCurrent();
    return (g_last_entry_attempt > 0 &&
            now - g_last_entry_attempt < InpCloseRetryCooldownSec);
}

void MarkEntryAttemptFailed()
{
    if(InpCloseRetryCooldownSec <= 0)
        return;
    datetime now = TimeCurrent();
    g_last_entry_attempt = now;
}

bool ExecuteSignal(const TradeSignal &sig)
{
    if(ShouldSkipEntryAttempt())
        return false;

    MqlTradeRequest request = {};
    MqlTradeResult  result  = {};

    request.action    = TRADE_ACTION_DEAL;
    request.symbol    = _Symbol;
    request.volume    = sig.lot;
    request.type      = sig.direction > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    request.price     = sig.direction > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                          : SymbolInfoDouble(_Symbol, SYMBOL_BID);
    request.sl        = sig.sl;
    request.tp        = sig.tp;
    request.magic     = InpMagicNumber;
    request.comment   = sig.comment;
    request.deviation = 20;
    request.type_filling = ORDER_FILLING_IOC;
    request.type_time    = ORDER_TIME_GTC;

    if(!OrderSend(request, result))
    {
        // INVALID_STOPS(10016): SL距离不足, 标记OB已用避免反复重试
        if(result.retcode == 10016)
        {
            static int s_invalid_stops_count = 0;
            s_invalid_stops_count++;
            if(s_invalid_stops_count <= 10 || s_invalid_stops_count % 1000 == 0)
                Print("止损无效(已跳过", s_invalid_stops_count, "次): ", sig.comment);
            if(sig.ob_index >= 0 && sig.ob_index < g_state.ob_count)
                g_zones[sig.ob_index].used = true;
            return false;
        }

        if(result.retcode == TRADE_RETCODE_REQUOTE)
        {
            request.price = sig.direction > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                              : SymbolInfoDouble(_Symbol, SYMBOL_BID);
            if(!OrderSend(request, result))
            {
                Print("开仓失败(重试): ", result.comment, " retcode=", result.retcode);
                MarkEntryAttemptFailed();
                return false;
            }
        }
        else
        {
            static int s_fail_count = 0;
            s_fail_count++;
            if(s_fail_count <= 10 || s_fail_count % 500 == 0)
                Print("开仓失败(第", s_fail_count, "次): ", result.comment, " retcode=", result.retcode);
            MarkEntryAttemptFailed();
            return false;
        }
    }

    if(result.retcode == TRADE_RETCODE_DONE)
    {
        Print("开仓成功: ", sig.comment, " ticket=", result.order,
              " price=", result.price, " lot=", sig.lot,
              " bounce_sec=", sig.bounce_seconds,
              " bounce_ob=", DoubleToString(sig.bounce_ob_pct, 3),
              " confirm_pos=", DoubleToString(sig.confirm_ob_pos, 3),
              " touch=", DoubleToString(sig.touch_price, _Digits),
              " confirm=", DoubleToString(sig.confirm_price, _Digits));

        RegisterPosition(result.order, sig.direction, result.price, sig.sl, sig.risk_price,
                         sig.deep_entry,
                         sig.htf_target, sig.htf_partial_r, sig.htf_partial_pct,
                         sig.failure_reverse,
                         g_tracks, g_track_count);

        if(g_track_count > 0)
            g_tracks[g_track_count - 1].open_bar = g_state.bar_count;

        if(sig.ob_index >= 0 && sig.ob_index < g_state.ob_count)
            MarkZoneUsed(g_zones, sig.ob_index);

        return true;
    }

    return false;
}
