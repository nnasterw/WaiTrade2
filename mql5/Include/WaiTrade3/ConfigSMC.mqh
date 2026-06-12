// WaiTrade3 SMC 扩展参数 — 追加在 v2 Config.mqh 之上
// 所有新参数默认 false/0，确保 v2 .set 加载时行为一致
#ifndef __WAITRADE3_CONFIG_MQH__
#define __WAITRADE3_CONFIG_MQH__

// ════════════════════════════════════════════════
// P0: 市场结构跟踪（Structure Tracker）
// ════════════════════════════════════════════════
input bool   InpEnableStructureTracker    = false;  // 启用结构跟踪(BOS/CHOCH)
input int    InpStructureLookbackBars     = 30;     // Swing pivot检测回溯bars
input int    InpStructurePivotBars        = 5;      // Pivot检测左右bars数(5=11-bar模式)
input int    InpStructureTrendTF          = 60;     // 趋势计算周期(分钟, 60=H1, 0=工作周期)
input int    InpStructureTrendLookback    = 80;     // 趋势计算回溯bars
input int    InpStructureTrendStableBars  = 2;      // 趋势稳定bars数(连续确认后才拦截, 防M15抖动)
input int    InpStructureMinPivotStrength = 0;      // 最小pivot strength(0=不限制)
input bool   InpStructureRequireClose     = true;   // 结构突破要求收盘价确认
input bool   InpStructureLogBOS           = false;  // 打印BOS/CHOCH日志
input bool   InpStructureBlockCounterTrend = false; // [DEPRECATED] 逆结构方向拦截入场(默认false=v2兼容)
input double InpStructureBlockMinStrength  = 0.0;   // [DEPRECATED] 拦截强度(已被自适应出场替代)
// 趋势自适应出场: 弱趋势逆势=紧SL+SwingTP, 强趋势逆势=保留v2参数
input bool   InpEnableTrendAdaptiveExit  = false;   // 启用趋势自适应出场
input double InpTrendStrengthThreshold   = 4.0;     // 趋势强度阈值(stable_bars>=此值=强趋势,保留v2)
input double InpCounterTrendSLMult       = 0.40;    // 弱趋势逆势SL倍数(0.4x正常SL=收紧60%)
input int    InpCounterTrendTPMode       = 1;       // 弱趋势逆势TP: 0=正常DTP, 1=SwingTarget
// P0: OB多周期堆叠
input bool   InpEnableOBStacking         = false;   // 启用OB多周期堆叠加仓

// ════════════════════════════════════════════════
// P1: H4 自适应重入控制（趋势市宽松 vs 震荡市限制）
// 配合v2宽SL (InpSLBufferATR=0.4)使用, v2重入参数设宽松(H4趋势时使用)
// H4震荡时自动收紧重入限制, 防止OB区域反复自毁
// 依赖: g_trend_state_h4 (由StructureTracker或独立H4检测填充)
// ════════════════════════════════════════════════
input bool   InpEnableH4Adaptive         = false;   // H4自适应重入: 趋势宽松/震荡严格
input int    InpH4TrendMaxEntriesPerOB    = 20;      // [趋势市] OB最大入场次数
input int    InpH4TrendReentryCooldownMin = 0;       // [趋势市] OB重入冷却(分钟)
input int    InpH4TrendCooldownBars       = 0;       // [趋势市] 全局冷却bars
input int    InpH4ChopMaxEntriesPerOB     = 2;       // [震荡市] OB最大入场次数
input int    InpH4ChopReentryCooldownMin  = 30;      // [震荡市] OB重入冷却(分钟)
input int    InpH4ChopCooldownBars        = 3;       // [震荡市] 全局冷却bars

// ════════════════════════════════════════════════
// P0: SL 使用 H1 ATR (修复致命尺度错误: M1_ATR=$1.6 → SL=$0.65; H1_ATR≈$20 → SL=$6-8)
// ════════════════════════════════════════════════
input bool   InpSLUseH1ATR               = false;   // SL距离用H1_ATR替代工作TF_ATR (XAU必须开!)

// ════════════════════════════════════════════════
// P0: 多周期OB加权入场 (HTF swing OB → 宽SL抓大波段)
// 原理: H4/H1 swing高低点 → OB zone → TF权重×该TF的ATR做SL
// H4 OB weight=4.0 SL=$15-25 | H1 weight=2.0 SL=$8-15 | M1 weight=1.0 SL=$1-3(scalper)
// 同价多周期共振 → confluence bonus叠加 → 最强信号
// ════════════════════════════════════════════════
input bool   InpEnableMultiTFOB           = false;   // 启用多周期OB加权入场
input double InpMTFH4Weight              = 4.0;     // H4 OB权重
input double InpMTFH1Weight              = 2.0;     // H1 OB权重
input double InpMTFM15Weight             = 1.5;     // M15 OB权重(预留)
input double InpMTFM5Weight              = 1.2;     // M5 OB权重(预留)
input double InpMTFM1Weight              = 1.0;     // M1 OB基准权重
input double InpMTFOBSLBufferATR         = 0.5;     // MTF OB的SL缓冲(ATR倍数, 0.5×H4_ATR≈$12-20)
input double InpMTFConfluenceBonus       = 1.5;     // 多周期共振加分(>1周期重叠×此倍率)
input int    InpMTFOBMaxAgeBars          = 240;     // MTF OB最大存活bars(M1 bars, 240≈4小时)
input int    InpMTFMaxOBPerTF            = 3;       // 每TF最多保留OB数
input double InpMTFMaxWeight            = 2.0;     // MTF仓位权重上限 ($200账户不宜超过2.0)
input bool   InpMTFBlockCounterTrend     = false;   // H4趋势强制对齐: BULL禁Sell/BEAR禁Buy(默认false=v2兼容)
input bool   InpEdgeBounceOnly           = false;   // P0: 仅OB边缘入场(默认false=v2兼容)
input bool   InpOBFreshnessFilter        = false;   // OB新鲜度过滤(默认false=v2兼容)
input int    InpOBMaxMitigations         = 2;       // OB最大缓解次数(超过后不再交易该OB)
input bool   InpBOSRetestEntry           = false;   // BOS突破回踩入场(结构突破→回踩→M1 OB确认)
input double InpBOSRetestSLBuffer        = 0.5;     // BOS回踩SL缓冲(ATR倍数, 突破位外侧)
input double InpBOSRetestTolerance       = 0.3;     // BOS回踩容差(ATR倍数, 价格接近突破位即触发)
input int    InpBOSRetestMaxBars         = 480;     // BOS回踩最大等待bars(M1, 480=8小时)
input double InpBOSRetestWeight          = 1.5;     // BOS回踩仓位加权(>1.0=比普通MTF信号更高的仓位)

// ════════════════════════════════════════════════
// P0: 流动性池检测（Liquidity Pool）
// ════════════════════════════════════════════════
input bool   InpEnableLiquidityPool       = false;  // 启用流动性池检测
input int    InpLPPoolLookbackBars        = 20;     // 流动性池检测回溯bars
input double InpLPSwingHighSimilarityPct  = 0.2;    // 双顶/双底价格相似度阈值(%)
input int    InpLPMinSweepDistancePoints  = 10;     // 最小sweep距离(points)
input double InpLPSweepEntryBoost         = 1.2;    // LP sweep后入场的仓位提升倍数
input bool   InpLPSweepBoostOnly           = true;   // LP sweep仅提升仓位，不独立产生信号
input double InpLPMinRangeATR             = 0.3;    // 流动性池最小范围(ATR倍数)
input bool   InpLPLogDetection            = false;  // 打印流动性池检测日志

// ════════════════════════════════════════════════
// P1: HTF 折扣/溢价区（Discount/Premium Zone）
// ════════════════════════════════════════════════
input bool   InpEnableDiscountPremium     = false;  // 启用折扣/溢价区过滤器
input double InpDiscountMaxRatio          = 0.50;   // 多头最大折扣比(>此值为溢价，拦截)
input double InpPremiumMinRatio           = 0.50;   // 空头最小溢价比(<此值为折扣，拦截)
input int    InpDPHTFPeriod               = 60;     // HTF周期(分钟, 60=H1)
input int    InpDPLookbackBars            = 48;     // 折扣区计算回溯bars
input double InpDPEntryMult               = 1.0;    // 折扣区入场仓位乘数(<=0=过滤)

// ════════════════════════════════════════════════
// P1: OB 质量评分（OB Scorer）
// ════════════════════════════════════════════════
input bool   InpEnableOBScoring           = false;  // 启用OB四维评分
input int    InpOBScoreMinPass            = 60;     // OB最低通过分数(0-100)
input double InpOBScoreTrendWeight        = 30.0;   // 趋势突破权重
input double InpOBScoreDisplacementWeight = 25.0;   // 位移K线权重
input double InpOBScoreLiquidityWeight    = 20.0;   // 流动性关联权重
input double InpOBScoreMitigationWeight   = 15.0;   // 缓解率权重
input double InpOBScoreDiscountWeight     = 10.0;   // 折扣区权重
input bool   InpOBScoreLogLow             = false;  // 打印低分OB日志

// ════════════════════════════════════════════════
// P2: 结构轨迹止损（Structure Trail）
// ════════════════════════════════════════════════
input bool   InpEnableStructureTrail      = false;  // 启用结构轨迹止损
input double InpStructTrailTriggerR       = 1.0;    // 结构轨迹触发R(浮盈达此值启用)
input double InpStructTrailBufferATR      = 0.2;    // 结构轨迹SL缓冲(ATR倍数)
input int    InpStructTrailLookback       = 10;     // 结构pivot查找bars
input bool   InpStructTrailOnlyDTPFree    = false;  // 仅DTP未触发时启用

// ════════════════════════════════════════════════
// 工具函数
// ════════════════════════════════════════════════
int  CfgStructureTrendTF() { return InpStructureTrendTF; }
int CfgStructureTrendLookback() { return InpStructureTrendLookback; }
int CfgStructureTrendStableBars() { return InpStructureTrendStableBars; }

bool CfgEnableStructureTracker()     { return InpEnableStructureTracker; }
bool CfgEnableTrendAdaptiveExit()    { return InpEnableTrendAdaptiveExit; }
double CfgTrendStrengthThreshold()   { return InpTrendStrengthThreshold; }
double CfgCounterTrendSLMult()       { return InpCounterTrendSLMult; }
int CfgCounterTrendTPMode()          { return InpCounterTrendTPMode; }
bool CfgEnableLiquidityPool()        { return InpEnableLiquidityPool; }
bool CfgEnableDiscountPremium()      { return InpEnableDiscountPremium; }
bool CfgEnableOBScoring()            { return InpEnableOBScoring; }
bool CfgEnableStructureTrail()       { return InpEnableStructureTrail; }
bool CfgEnableH4Adaptive()           { return InpEnableH4Adaptive; }
bool CfgSLUseH1ATR()                 { return InpSLUseH1ATR; }
int  CfgH4TrendMaxEntriesPerOB()     { return InpH4TrendMaxEntriesPerOB; }
int  CfgH4TrendReentryCooldownMin()  { return InpH4TrendReentryCooldownMin; }
int  CfgH4TrendCooldownBars()        { return InpH4TrendCooldownBars; }
int  CfgH4ChopMaxEntriesPerOB()      { return InpH4ChopMaxEntriesPerOB; }
int  CfgH4ChopReentryCooldownMin()   { return InpH4ChopReentryCooldownMin; }
int  CfgH4ChopCooldownBars()         { return InpH4ChopCooldownBars; }

#endif
