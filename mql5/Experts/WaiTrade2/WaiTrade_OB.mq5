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
OBZone      g_htf_zones[MAX_OB_ZONES];
PosTrack    g_tracks[MAX_POSITIONS];
EAState     g_state;
TradeSignal g_signals[10];
int         g_track_count = 0;
int         g_htf_zone_count = 0;

// v9.8a EntryEngine
EntryMonitor g_monitors[MAX_MONITORS];
EntryMonitor g_htf_monitors[MAX_MONITORS];
int          g_monitor_count = 0;
int          g_htf_monitor_count = 0;
datetime     g_last_entry_attempt = 0;

// 双zone通道：M3振荡腿独立zone缓存（始终维护，不受趋势模式切换影响）
OBZone      g_zones_osc[MAX_OB_ZONES];
EAState     g_state_osc;
EntryMonitor g_monitors_osc[MAX_MONITORS];
int          g_monitor_count_osc = 0;
bool         g_osc_active = false; // 当前tick是否使用振荡通道

// ── 双通道辅助函数：注册活跃OB为监视器 ──────────────────────────────
void RegisterChannelMonitors(OBZone& zones[], EAState& state,
                              EntryMonitor& mons[], int& mon_count,
                              bool new_active_bar, string symbol)
{
    if(!new_active_bar) return;
    double spread = GetSpread(symbol);
    for(int z = 0; z < state.ob_count; z++)
    {
        if(zones[z].expired || zones[z].used) continue;
        if(!PassOBReentryCooldown(zones[z])) continue;
        if(CfgEnableStateFilter() && state.market_state != 0
           && state.market_state != zones[z].direction) continue;

        double risk_dist = (zones[z].direction == OB_BUY)
            ? ((zones[z].high + zones[z].low) / 2.0) - (zones[z].low - state.atr_value * CfgSLBufferATR())
            : (zones[z].high + state.atr_value * CfgSLBufferATR()) - ((zones[z].high + zones[z].low) / 2.0);
        if(spread > 0 && risk_dist / spread < CfgMinRiskSpreadRatio()) continue;

        TradeSignal tmp;
        ZeroMemory(tmp);
        tmp.direction  = zones[z].direction;
        tmp.sl         = (zones[z].direction == OB_BUY)
            ? zones[z].low  - state.atr_value * CfgSLBufferATR()
            : zones[z].high + state.atr_value * CfgSLBufferATR();
        tmp.risk_price = MathAbs(((zones[z].high + zones[z].low) / 2.0) - tmp.sl);
        tmp.ob_index   = z;
        tmp.pos_mult   = 1.0;

        if(CfgEnableScoring())
        {
            double prox = (state.atr_m15 > 0) ? state.atr_m15 : state.atr_value * 5;
            int score   = CalcSignalScore(zones[z], state, state.market_state, prox, tmp.risk_price, 0);
            if(score < CfgMinScore()) continue;
            double mult = ScoreToMultiplier(score);
            if(mult < 0) continue;
            tmp.pos_mult = mult;
        }
        AddEntryMonitor(tmp, zones[z], mons, mon_count);
    }
}

// ── 双通道辅助函数：执行已确认的入场 ────────────────────────────────
void ExecuteChannelConfirmed(OBZone& zones[], EAState& state,
                              EntryMonitor& mons[], int& mon_count,
                              double bid, double ask, string symbol)
{
    TradeSignal confirmed[10];
    int conf_count = UpdateEntryMonitors(bid, ask, TimeCurrent(), mons, mon_count, confirmed, 10);
    for(int i = 0; i < conf_count; i++)
    {
        if(state.pos_count >= CfgMaxConcurrent()) break;
        if(confirmed[i].ob_index < 0 || confirmed[i].ob_index >= state.ob_count) continue;
        if(!FinalizeEntryEngineSignal(symbol, zones[confirmed[i].ob_index], state, confirmed[i])) continue;
        if(ExecuteSignal(confirmed[i]))
        {
            state.last_entry_bar = state.bar_count;
            state.pos_count++;
        }
    }
}

int OnInit()
{
    ZeroMemory(g_state);
    ZeroMemory(g_zones);
    ZeroMemory(g_htf_zones);
    ZeroMemory(g_tracks);
    g_track_count = 0;
    g_htf_zone_count = 0;
    g_monitor_count = 0;
    g_htf_monitor_count = 0;
    ZeroMemory(g_state_osc);
    ZeroMemory(g_zones_osc);
    ZeroMemory(g_monitors_osc);
    g_monitor_count_osc = 0;
    g_last_entry_attempt = 0;

    if(CfgRiskPercent() <= 0 || CfgRiskPercent() > 50)
    {
        Print("参数错误: RiskPercent=", CfgRiskPercent());
        return INIT_PARAMETERS_INCORRECT;
    }

    SymbolSelect(_Symbol, true);
    SyncMonthlyRiskState();
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

    // 月初OB zone重置（消除多月状态延续对信号质量的影响）
    if(InpMonthlyZoneReset)
    {
        static int s_prev_month = 0;
        MqlDateTime dt;
        TimeToStruct(TimeCurrent(), dt);
        int cur_month = dt.year * 100 + dt.mon;
        if(s_prev_month != 0 && cur_month != s_prev_month)
        {
            ZeroMemory(g_zones);
            ZeroMemory(g_htf_zones);
            g_state.ob_count = 0;
            g_htf_zone_count = 0;
            g_monitor_count = 0;
            g_htf_monitor_count = 0;
            g_state.last_entry_bar = 0;
            // 同步清除振荡通道
            ZeroMemory(g_zones_osc);
            g_state_osc.ob_count = 0;
            g_monitor_count_osc = 0;
            g_state_osc.last_entry_bar = 0;
            Print("月初Zone重置 ", dt.year, ".", StringFormat("%02d", dt.mon));
        }
        s_prev_month = cur_month;
    }

    // 双通道模式：M3振荡通道独立维护，无切换清除
    // 单通道模式（兜底）：切换时清除，防止TF不同的OB相互污染
    bool s_dual = InpEnableDualZoneChannel && InpEnableXAUTrendProfile;
    if(InpEnableXAUTrendProfile && !s_dual)
    {
        static bool s_last_trend_profile = false;
        bool cur_trend = UseXAUTrendProfile();
        if(cur_trend != s_last_trend_profile)
        {
            ZeroMemory(g_zones);
            ZeroMemory(g_htf_zones);
            g_state.ob_count = 0;
            g_htf_zone_count = 0;
            g_monitor_count = 0;
            g_htf_monitor_count = 0;
            s_last_trend_profile = cur_trend;
            Print("Profile切换zone清除(单通道): ", cur_trend ? "→Trend" : "→FAGE");
        }
    }

    // 1. 加载K线数据
    // 双通道模式：主通道固定用M1（趋势通道）；另有M3振荡通道独立更新
    ENUM_TIMEFRAMES act_tf = s_dual ? (ENUM_TIMEFRAMES)CfgMinutesToTF(InpXAUTrendBarTF) : tf;
    MqlRates rates[];
    int copied = CopyRates(symbol, act_tf, 0, InpBars, rates);
    if(copied < 100) {
        static datetime s_last_copy_fail = 0;
        if(TimeCurrent() - s_last_copy_fail >= 300) {
            s_last_copy_fail = TimeCurrent();
            Print("CopyRates失败: symbol=", symbol, " tf=", act_tf, " copied=", copied);
        }
        return;
    }

    g_state.atr_value = CalcATR(rates, copied, InpATRPeriod);

    // 2. 新bar处理（趋势通道 / 单通道主通道）
    bool new_bar = IsNewBar(symbol, act_tf);
    if(new_bar)
    {
        g_state.bar_count++;

        DetectOrderBlocks(rates, copied, g_zones, g_state.ob_count, g_state);
        if(InpConsolidateOB)
            ConsolidateOBs(g_zones, g_state.ob_count);
        if(InpEnableHTFPullback && !InpHTFPullbackOnly)
        {
            CompactZones(g_htf_zones, g_htf_zone_count);
            DetectHTFPullbacks(g_htf_zones, g_htf_zone_count, g_state, GetSpread(symbol));
        }

        MqlRates rates_h1[];
        int h1_count = CopyRates(symbol, PERIOD_H1, 0, 100, rates_h1);
        if(h1_count > InpATRPeriod)
            g_state.atr_1h = CalcATR(rates_h1, h1_count, InpATRPeriod);

        int h1_dir = Detect1HOBDirection(symbol);
        Update1HAlignment(g_zones, g_state.ob_count, h1_dir);
        if(InpEnableHTFPullback && !InpHTFPullbackOnly)
            Update1HAlignment(g_htf_zones, g_htf_zone_count, h1_dir);

        if(CfgEnableStateFilter() || CfgEnableScoring())
        {
            double target = 0;
            g_state.market_state = (int)DetectMarketState(symbol, target);
            g_state.target_price = target;

            MqlRates rates_m15[];
            int m15_count = CopyRates(symbol, PERIOD_M15, 0, CfgTrendLookback(), rates_m15);
            if(m15_count > 14)
                g_state.atr_m15 = CalcATR(rates_m15, m15_count, InpATRPeriod);
        }
    }

    // 双通道：M3振荡通道始终独立更新（new_osc_bar_tick 提升作用域供信号扫描使用）
    bool new_osc_bar_tick = false;
    if(s_dual)
    {
        ENUM_TIMEFRAMES osc_tf = (ENUM_TIMEFRAMES)CfgMinutesToTF(InpBarTF);
        MqlRates osc_rates[];
        int osc_copied = CopyRates(symbol, osc_tf, 0, InpBars, osc_rates);
        if(osc_copied >= 100)
        {
            g_state_osc.atr_value = CalcATR(osc_rates, osc_copied, InpATRPeriod);
            bool new_osc = IsNewBar(symbol, osc_tf);
            new_osc_bar_tick = new_osc;
            if(new_osc)
            {
                g_state_osc.bar_count++;
                DetectOrderBlocks(osc_rates, osc_copied, g_zones_osc, g_state_osc.ob_count, g_state_osc);
                if(InpConsolidateOB) ConsolidateOBs(g_zones_osc, g_state_osc.ob_count);

                MqlRates osc_h1[];
                int osc_h1c = CopyRates(symbol, PERIOD_H1, 0, 100, osc_h1);
                if(osc_h1c > InpATRPeriod)
                    g_state_osc.atr_1h = CalcATR(osc_h1, osc_h1c, InpATRPeriod);
                int osc_h1dir = Detect1HOBDirection(symbol);
                Update1HAlignment(g_zones_osc, g_state_osc.ob_count, osc_h1dir);

                if(CfgEnableStateFilter() || CfgEnableScoring())
                {
                    double osc_target = 0;
                    g_state_osc.market_state = (int)DetectMarketState(symbol, osc_target);
                    g_state_osc.target_price = osc_target;
                    MqlRates osc_m15[];
                    int osc_m15c = CopyRates(symbol, PERIOD_M15, 0, CfgTrendLookback(), osc_m15);
                    if(osc_m15c > 14)
                        g_state_osc.atr_m15 = CalcATR(osc_m15, osc_m15c, InpATRPeriod);
                }
            }
        }
    }

    // 3. 更新OB状态(每tick) + 选择活跃通道
    g_osc_active = s_dual && !UseXAUTrendProfile();
    double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
    UpdateOBStatus(g_zones, g_state.ob_count, bid, ask, g_state);
    if(s_dual)
        UpdateOBStatus(g_zones_osc, g_state_osc.ob_count, bid, ask, g_state_osc);
    else if(InpEnableHTFPullback && !InpHTFPullbackOnly)
        UpdateOBStatus(g_htf_zones, g_htf_zone_count, bid, ask, g_state);
    // 4. 扫描入场信号（双通道：振荡用M3 osc通道，趋势用M1主通道）
    bool new_active_bar = g_osc_active ? new_osc_bar_tick : new_bar;

    if(g_osc_active)
        g_state_osc.pos_count = CountActivePositions();
    else
        g_state.pos_count = CountActivePositions();

    if(InpEnableEntryEngine)
    {
        // 注册活跃通道的OB监视器
        if(g_osc_active)
            RegisterChannelMonitors(g_zones_osc, g_state_osc, g_monitors_osc, g_monitor_count_osc, new_active_bar, symbol);
        else
            RegisterChannelMonitors(g_zones, g_state, g_monitors, g_monitor_count, new_active_bar, symbol);

        // HTF pullback（仅单通道或趋势通道模式）
        if(!g_osc_active && new_bar && InpEnableHTFPullback && !InpHTFPullbackOnly)
        {
            for(int z = 0; z < g_htf_zone_count; z++)
            {
                if(g_htf_zones[z].expired || g_htf_zones[z].used) continue;
                if(!PassOBReentryCooldown(g_htf_zones[z])) continue;
                if(CfgEnableStateFilter() && g_state.market_state != 0 &&
                   g_state.market_state != g_htf_zones[z].direction) continue;

                TradeSignal tmp;
                ZeroMemory(tmp);
                tmp.direction  = g_htf_zones[z].direction;
                tmp.sl         = (g_htf_zones[z].direction == OB_BUY)
                    ? g_htf_zones[z].low  - g_state.atr_value * CfgSLBufferATR()
                    : g_htf_zones[z].high + g_state.atr_value * CfgSLBufferATR();
                tmp.risk_price = MathAbs(((g_htf_zones[z].high + g_htf_zones[z].low) / 2.0) - tmp.sl);
                tmp.ob_index   = z;
                tmp.pos_mult   = 1.0;
                AddEntryMonitor(tmp, g_htf_zones[z], g_htf_monitors, g_htf_monitor_count);
            }
        }

        // 5. 执行确认的入场
        if(g_osc_active)
            ExecuteChannelConfirmed(g_zones_osc, g_state_osc, g_monitors_osc, g_monitor_count_osc, bid, ask, symbol);
        else
            ExecuteChannelConfirmed(g_zones, g_state, g_monitors, g_monitor_count, bid, ask, symbol);

        if(!g_osc_active && InpEnableHTFPullback && !InpHTFPullbackOnly)
        {
            TradeSignal htf_confirmed[10];
            int htf_conf_count = UpdateEntryMonitors(bid, ask, TimeCurrent(), g_htf_monitors, g_htf_monitor_count, htf_confirmed, 10);
            for(int i = 0; i < htf_conf_count; i++)
            {
                if(g_state.pos_count >= CfgMaxConcurrent()) break;
                if(htf_confirmed[i].ob_index < 0 || htf_confirmed[i].ob_index >= g_htf_zone_count) continue;
                if(!FinalizeEntryEngineSignal(symbol, g_htf_zones[htf_confirmed[i].ob_index], g_state, htf_confirmed[i])) continue;
                if(ExecuteSignalFromZone(htf_confirmed[i], g_htf_zones, g_htf_zone_count, false))
                {
                    g_state.last_entry_bar = g_state.bar_count;
                    g_state.pos_count++;
                }
            }
        }
    }
    else
    {
        // 原始模式: 直接入场（使用活跃通道）
        int sig_count;
        if(g_osc_active)
        {
            sig_count = ScanSignals(symbol, g_zones_osc, g_state_osc.ob_count, g_state_osc, g_signals, 10);
            for(int i = 0; i < sig_count; i++)
            {
                if(g_state_osc.pos_count >= CfgMaxConcurrent()) break;
                if(ExecuteSignal(g_signals[i])) { g_state_osc.last_entry_bar = g_state_osc.bar_count; g_state_osc.pos_count++; }
            }
        }
        else
        {
            sig_count = ScanSignals(symbol, g_zones, g_state.ob_count, g_state, g_signals, 10);
            for(int i = 0; i < sig_count; i++)
            {
                if(g_state.pos_count >= CfgMaxConcurrent()) break;
                if(ExecuteSignal(g_signals[i])) { g_state.last_entry_bar = g_state.bar_count; g_state.pos_count++; }
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

int CountActivePositions()
{
    if(CfgFreeRunMinR() <= 0)
        return CountPositions();
    int count = 0;
    for(int i = 0; i < g_track_count; i++)
    {
        if(g_tracks[i].ticket == 0) continue;
        if(g_tracks[i].peak_profit_r >= CfgFreeRunMinR())
            continue;
        count++;
    }
    return count;
}

bool ShouldSkipEntryAttempt()
{
    if(CfgCloseRetryCooldownSec() <= 0)
        return false;

    datetime now = TimeCurrent();
    return (g_last_entry_attempt > 0 &&
            now - g_last_entry_attempt < CfgCloseRetryCooldownSec());
}

void MarkEntryAttemptFailed()
{
    if(CfgCloseRetryCooldownSec() <= 0)
        return;
    datetime now = TimeCurrent();
    g_last_entry_attempt = now;
}

bool ExecuteLayeredOrders(const TradeSignal &sig, double base_price)
{
    if(InpLayeredEntryCount < 2) return false;
    if(sig.ob_index < 0 || sig.ob_index >= g_state.ob_count) return false;

    double ob_h = g_zones[sig.ob_index].high - g_zones[sig.ob_index].low;
    if(ob_h <= 0) return false;

    double spacing = ob_h * InpLayeredSpacingPct;
    int layers = MathMin(InpLayeredEntryCount - 1, 3);

    for(int i = 1; i <= layers; i++)
    {
        double offset = spacing * i;
        double limit_price = (sig.direction > 0) ? base_price - offset : base_price + offset;

        double lot_mult = 1.0 + (InpLayeredLotMult - 1.0) * i / layers;
        double layer_lot = NormalizeDouble(sig.lot * lot_mult, 2);
        double lot_min = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
        if(layer_lot < lot_min) layer_lot = lot_min;

        MqlTradeRequest req = {};
        MqlTradeResult  res = {};
        req.action = TRADE_ACTION_PENDING;
        req.symbol = _Symbol;
        req.volume = layer_lot;
        req.type   = (sig.direction > 0) ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
        req.price  = NormalizeDouble(limit_price, _Digits);
        req.sl     = sig.sl;
        req.tp     = sig.tp;
        req.magic  = InpMagicNumber;
        req.comment = sig.comment + "_L" + IntegerToString(i+1);
        req.deviation = 20;
        req.type_filling = ORDER_FILLING_RETURN;
        req.type_time = ORDER_TIME_GTC;

        if(OrderSend(req, res))
        {
            if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
                Print("分层挂单L", i+1, ": price=", req.price, " lot=", layer_lot);
        }
    }
    return true;
}

bool ExecuteMicroEntryOrders(const TradeSignal &sig)
{
    if(InpMicroEntryCount <= 0 || InpMicroEntryLotMult <= 0)
        return false;

    int count = MathMin(InpMicroEntryCount, 5);
    double lot_min = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    if(InpMicroEntryMaxLotSize > 0 && InpMicroEntryMaxLotSize < lot_min)
        return false;

    double micro_lot = sig.lot * InpMicroEntryLotMult;
    if(InpMicroEntryMaxLotSize > 0 && micro_lot > InpMicroEntryMaxLotSize)
        micro_lot = InpMicroEntryMaxLotSize;
    micro_lot = NormalizeDouble(micro_lot, 2);
    if(micro_lot < lot_min)
        micro_lot = lot_min;

    bool placed = false;
    for(int i = 1; i <= count; i++)
    {
        MqlTradeRequest req = {};
        MqlTradeResult  res = {};
        req.action    = TRADE_ACTION_DEAL;
        req.symbol    = _Symbol;
        req.volume    = micro_lot;
        req.type      = sig.direction > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
        req.price     = sig.direction > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                          : SymbolInfoDouble(_Symbol, SYMBOL_BID);
        req.sl        = sig.sl;
        req.tp        = sig.tp;
        req.magic     = InpMagicNumber;
        req.comment   = sig.comment + "_M" + IntegerToString(i);
        req.deviation = 20;
        req.type_filling = ORDER_FILLING_IOC;
        req.type_time    = ORDER_TIME_GTC;

        if(!OrderSend(req, res) || res.retcode != TRADE_RETCODE_DONE)
            continue;

        placed = true;
        Print("微仓副单成功 ", req.comment, " ticket=", res.order,
              " price=", res.price, " lot=", micro_lot);
        RecordMonthlyEntry();
        RegisterPosition(res.order, sig.direction, res.price, sig.sl, sig.risk_price,
                         sig.deep_entry,
                         sig.htf_target, sig.htf_partial_r, sig.htf_partial_pct,
                         sig.failure_reverse,
                         g_tracks, g_track_count);
        if(g_track_count > 0)
        {
            g_tracks[g_track_count - 1].open_bar = g_state.bar_count;
            g_tracks[g_track_count - 1].entry_market_state = g_state.market_state;
        }
    }

    return placed;
}

bool ExecuteSignal(const TradeSignal &sig)
{
    return ExecuteSignalFromZone(sig, g_zones, g_state.ob_count, true);
}

bool ExecuteSignalFromZone(const TradeSignal &sig, OBZone &zones[], int zone_count, bool allow_layered)
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
            if(sig.ob_index >= 0 && sig.ob_index < zone_count)
                zones[sig.ob_index].used = true;
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

        RecordMonthlyEntry();
        RegisterPosition(result.order, sig.direction, result.price, sig.sl, sig.risk_price,
                         sig.deep_entry,
                         sig.htf_target, sig.htf_partial_r, sig.htf_partial_pct,
                         sig.failure_reverse,
                         g_tracks, g_track_count);

        if(g_track_count > 0)
        {
            g_tracks[g_track_count - 1].open_bar = g_state.bar_count;
            g_tracks[g_track_count - 1].entry_market_state = g_state.market_state;
        }

        if(allow_layered && InpLayeredEntryCount >= 2)
            ExecuteLayeredOrders(sig, result.price);
        ExecuteMicroEntryOrders(sig);

        if(sig.ob_index >= 0 && sig.ob_index < zone_count)
            MarkZoneUsed(zones, sig.ob_index);

        return true;
    }

    return false;
}
