#ifndef __WAITRADE_TYPES_MQH__
#define __WAITRADE_TYPES_MQH__

// ═══════════════════════════════════════════════════════════════════════════
// WaiTrade2 EA — 核心数据结构
// ═══════════════════════════════════════════════════════════════════════════

#define MAX_OB_ZONES   100
#define MAX_POSITIONS  20
#define OB_BUY         1
#define OB_SELL       -1

struct OBZone
{
    double   high;           // OB区域上沿
    double   low;            // OB区域下沿
    double   mid;            // 入场价 (区域中点)
    int      direction;      // OB_BUY=看涨(做多), OB_SELL=看跌(做空)
    datetime created;        // 创建时间
    int      created_bar;    // 创建时的全局bar计数
    int      touch_count;    // 价格触碰OB区域次数
    datetime first_touch;    // 首次触碰时间
    datetime last_touch;     // 最近触碰时间
    double   strength;       // OB强度评分 (1.0-5.0)
    bool     is_fresh;       // 是否未被触碰过
    bool     is_continuation;// 是否顺势OB
    bool     is_1h_aligned;  // 是否与1H OB方向一致
    double   ds_weight;      // 供需权重 (0.5-2.5)
    int      entry_count;    // 已基于该OB入场次数
    datetime last_entry_time;// 最近一次基于该OB入场时间
    bool     used;           // 是否已入场
    bool     expired;        // 是否已过期
    bool     is_range_breakout; // 是否为震荡区间突破信号
    bool     is_liquidity_sweep; // 是否为流动性扫损反转信号
    bool     is_loose_sweep; // loose sweep supplemental signal
    bool     is_htf_pullback; // higher-timeframe net-push pullback signal
    double   range_height;    // 震荡区间高度，用于量度目标
    double   ob_top;          // OB检测原始顶部(实体边界)
    double   ob_bottom;       // OB检测原始底部(实体边界)
};

struct TradeSignal
{
    int      direction;      // 1=做多, -1=做空
    double   entry;          // 入场价 (OB mid)
    double   sl;             // 止损价
    double   tp;             // 止盈价 (0=DTP模式)
    double   risk_price;     // 风险距离 (|entry - sl|)
    double   lot;            // 计算手数
    double   pos_mult;       // 仓位乘数
    int      ob_index;       // 对应OB数组索引
    bool     deep_entry;      // 是否深入OB后入场
    double   touch_price;     // EntryEngine真实触点/最深触点
    double   confirm_price;   // EntryEngine确认价
    int      bounce_seconds;  // 从触点到确认耗时
    double   bounce_ob_pct;   // 确认反弹幅度/OB高度
    double   confirm_ob_pos;  // 确认价相对OB区间位置(买:高于上沿为正,卖:低于下沿为正)
    bool     htf_target;      // 是否使用大周期目标位
    double   htf_partial_r;   // 大周期目标单分批R
    int      htf_partial_pct; // 大周期目标单分批比例
    bool     failure_reverse; // 是否失败反手单
    string   comment;        // 订单备注
};

struct PosTrack
{
    ulong    ticket;         // 持仓ticket
    int      direction;      // 1=多, -1=空
    double   entry_price;    // 入场价
    double   sl_initial;     // 初始止损
    double   risk_price;     // 初始风险距离
    double   peak_profit_r;  // 历史最高浮盈(R倍数)
    int      open_bar;       // 开仓时的全局bar计数
    bool     be_applied;     // 是否已执行保本
    int      trail_level;    // 当前追踪级别 (0=无, 1-3)
    bool     dtp_active;     // DTP是否已激活
    double   dtp_peak_r;     // DTP激活后的峰值R
    bool     partial_closed; // 是否已执行部分平仓
    bool     dtp_partial_closed; // DTP是否已执行部分平仓
    bool     deep_entry;      // 是否深入OB后入场
    bool     htf_target;      // 是否使用大周期目标位
    double   htf_partial_r;   // 大周期目标单分批R
    int      htf_partial_pct; // 大周期目标单分批比例
    bool     failure_reverse; // 是否失败反手单
    int      addon_count;     // 已触发强势延续加仓次数
    bool     strong_addon;    // 是否强势延续加仓单
    datetime last_close_attempt; // 最近一次主动市价平仓尝试时间
    string   last_sl_reason; // 最近一次SL修改来源
    int      entry_market_state; // 入场时市场状态(1=bull,-1=bear,0=range)
};

struct EAState
{
    int      bar_count;      // 全局bar计数器 (从EA启动开始累加)
    int      last_entry_bar; // 上次入场的bar计数 (用于cooldown)
    int      ob_count;       // 当前有效OB数量
    int      pos_count;      // 当前跟踪的持仓数量
    double   atr_value;      // 当前ATR值
    double   atr_1h;         // 1H ATR值
    // v9.8
    int      market_state;   // MARKET_STATE enum value (1=bull, -1=bear, 0=range)
    double   target_price;   // 震荡态对面swing点价格
    double   atr_m15;        // M15 ATR
};

#endif
