// WaiTrade3 SMC 扩展类型定义 — 平行数组，不修改 v2 原有 struct
#ifndef __WAITRADE3_TYPES_MQH__
#define __WAITRADE3_TYPES_MQH__

#define MAX_SWING_POINTS      50
#define MAX_LIQUIDITY_POOLS   20

// ── Swing Point 类型 ──
enum SMCSwingPointType {
    SWING_HIGH,   // 局部高点
    SWING_LOW     // 局部低点
};

// ── Swing Point 强度 ──
enum SMCSwingStrength {
    SWING_WEAK,     // 已被突破
    SWING_STRONG,   // 尚未被突破（支撑/阻力）
    SWING_BROKEN    // 刚被突破（状态转换中）
};

// ── 趋势状态 ──
enum TrendState {
    TREND_UNKNOWN = 0,
    TREND_BULLISH,   // HH + HL（高点+低点上移）
    TREND_BEARISH,   // LH + LL（高点+低点下移）
    TREND_CHOP       // 无明显结构
};

// ── Swing Point ──
struct SMCSwingPoint {
    double   price;          // 价格
    datetime time;           // 时间
    SMCSwingPointType type;     // HIGH 或 LOW
    SMCSwingStrength strength;  // 强度
    int      bar_index;      // 全局bar索引
    bool     broken;         // 是否已被突破
    double   break_price;    // 突破价格
    datetime break_time;     // 突破时间
};

// ── 流动性池类型 ──
enum LiquidityPoolType {
    LP_SWING_HIGH_LOW,       // 历史高低点
    LP_DOUBLE_TOP_BOTTOM,    // 双顶/双底
    LP_TRENDLINE_BREAK       // 趋势线突破（预留）
};

// ── 流动性池 ──
struct LiquidityPool {
    LiquidityPoolType type;
    double   level;           // 关键价格水平
    double   range_high;      // 区间上沿
    double   range_low;       // 区间下沿
    double   similarity_pct;  // 双顶相似度（仅DOUBLE_TOP_BOTTOM）
    datetime formed_time;     // 形成时间
    bool     swept;           // 是否已被扫
    datetime sweep_time;      // 扫损时间
    double   sweep_distance;  // 扫损距离(points)
    int      sweep_bar;       // 扫损bar索引
    bool     active;          // 是否活跃（未过期）
    int      age_bars;        // 存活bars
};

// ── OB 平行数据（通过 zone index 关联，不修改 OBZone struct） ──
struct SMCZoneData {
    bool     bos_break;        // OB形成伴随BOS
    bool     choch_signal;     // OB伴随CHOCH
    int      quality_score;    // OB质量评分(0-100)
    double   discount_ratio;   // 折扣/溢价比(0-1)
    bool     in_discount_zone; // 是否在折扣区
    double   mitigation_pct;   // 缓解百分比(0=未缓解, 1=完全缓解)
    bool     liquidity_linked; // 是否关联流动性池扫损
    double   htf_net_push;     // HTF净方向(正=多头, 负=空头)
};

// ── 结构突破信号 ──
enum StructureSignal {
    SIG_NONE = 0,
    SIG_BOS_BULL,       // 多头结构突破(低点更高的低点被破)
    SIG_BOS_BEAR,       // 空头结构突破(高点更低的高点被破)
    SIG_CHOCH_BULL,     // 空转多
    SIG_CHOCH_BEAR      // 多转空
};

#endif
