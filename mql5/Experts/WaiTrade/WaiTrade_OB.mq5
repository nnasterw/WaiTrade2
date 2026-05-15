#property copyright "WaiTrade"
#property version   "96.02"
#property strict

#include <WaiTrade/Config.mqh>
#include <WaiTrade/Types.mqh>
#include <WaiTrade/Utils.mqh>
#include <WaiTrade/OBDetector.mqh>
#include <WaiTrade/SignalEngine.mqh>
#include <WaiTrade/PositionManager.mqh>

OBZone      g_zones[MAX_OB_ZONES];
PosTrack    g_tracks[MAX_POSITIONS];
EAState     g_state;
TradeSignal g_signals[10];
int         g_track_count = 0;

int OnInit()
{
    ZeroMemory(g_state);
    ZeroMemory(g_zones);
    ZeroMemory(g_tracks);
    g_track_count = 0;

    if(InpRiskPercent <= 0 || InpRiskPercent > 50)
    {
        Print("参数错误: InpRiskPercent=", InpRiskPercent);
        return INIT_PARAMETERS_INCORRECT;
    }

    Print("WaiTrade ", InpVersion, " 已加载 | ", _Symbol, " | Magic=", InpMagicNumber);
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    Print("WaiTrade ", InpVersion, " 已卸载 | 原因=", reason);
}

void OnTick()
{
    string symbol = _Symbol;
    ENUM_TIMEFRAMES tf = GetWorkTF();

    // 1. 加载K线数据并更新ATR
    MqlRates rates[];
    int copied = CopyRates(symbol, tf, 0, InpBars, rates);
    if(copied < 100) return;

    g_state.atr_value = CalcATR(rates, copied, InpATRPeriod);

    // 2. 新bar处理
    if(IsNewBar(symbol, tf))
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
        for(int i = 0; i < g_state.ob_count; i++)
        {
            if(!g_zones[i].expired && !g_zones[i].used)
                g_zones[i].is_1h_aligned = (g_zones[i].direction == h1_dir);
        }
    }

    // 3. 更新OB状态(每tick)
    double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
    UpdateOBStatus(g_zones, g_state.ob_count, bid, ask, g_state);

    // 4. 扫描入场信号
    g_state.pos_count = CountPositions();
    int sig_count = ScanSignals(symbol, g_zones, g_state.ob_count, g_state, g_signals, 10);

    // 5. 执行入场
    for(int i = 0; i < sig_count; i++)
    {
        if(g_state.pos_count >= InpMaxConcurrent) break;
        ExecuteSignal(g_signals[i]);
        g_state.last_entry_bar = g_state.bar_count;
        g_state.pos_count++;
    }

    // 6. 持仓管理
    SyncPositions(g_tracks, g_track_count);
    ManagePositions(g_tracks, g_track_count, g_state);
}

void ExecuteSignal(const TradeSignal &sig)
{
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
        Print("开仓失败: ", result.comment, " retcode=", result.retcode);
        return;
    }

    if(result.retcode == TRADE_RETCODE_DONE)
    {
        Print("开仓成功: ", sig.comment, " ticket=", result.order,
              " price=", result.price, " lot=", sig.lot);

        RegisterPosition(result.order, sig.direction, result.price, sig.sl, sig.risk_price,
                         g_tracks, g_track_count);

        if(g_track_count > 0)
            g_tracks[g_track_count - 1].open_bar = g_state.bar_count;

        if(sig.ob_index >= 0 && sig.ob_index < g_state.ob_count)
            g_zones[sig.ob_index].used = true;
    }
}
