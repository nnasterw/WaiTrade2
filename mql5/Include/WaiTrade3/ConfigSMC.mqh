// WaiTrade3 SMC 扩展参数 — 追加在 v2 Config.mqh 之上
// 所有新参数默认 false/0，确保 v2 .set 加载时行为一致
#ifndef __WAITRADE3_CONFIG_MQH__
#define __WAITRADE3_CONFIG_MQH__

// BV1 slim build: keep default v3 behavior without exceeding MT5 input budget.
#ifdef WAITRADE3_BV1_SLIM
#define WT3_INPUT const
#define WT3_PS1_INPUT input
#else
#define WT3_INPUT input
#define WT3_PS1_INPUT input
#endif

// ════════════════════════════════════════════════
// P0: 市场结构跟踪（Structure Tracker）
// ════════════════════════════════════════════════
WT3_INPUT bool   InpEnableStructureTracker    = false;  // 启用结构跟踪(BOS/CHOCH)
WT3_INPUT int    InpStructureLookbackBars     = 30;     // Swing pivot检测回溯bars
WT3_INPUT int    InpStructurePivotBars        = 5;      // Pivot检测左右bars数(5=11-bar模式)
WT3_INPUT int    InpStructureTrendTF          = 60;     // 趋势计算周期(分钟, 60=H1, 0=工作周期)
WT3_INPUT int    InpStructureTrendLookback    = 80;     // 趋势计算回溯bars
WT3_INPUT int    InpStructureTrendStableBars  = 2;      // 趋势稳定bars数(连续确认后才拦截, 防M15抖动)
WT3_INPUT int    InpStructureMinPivotStrength = 0;      // 最小pivot strength(0=不限制)
WT3_INPUT bool   InpStructureRequireClose     = true;   // 结构突破要求收盘价确认
WT3_INPUT bool   InpStructureLogBOS           = false;  // 打印BOS/CHOCH日志
WT3_INPUT bool   InpStructureBlockCounterTrend = false; // [DEPRECATED] 逆结构方向拦截入场(默认false=v2兼容)
WT3_INPUT double InpStructureBlockMinStrength  = 0.0;   // [DEPRECATED] 拦截强度(已被自适应出场替代)
// 趋势自适应出场: 弱趋势逆势=紧SL+SwingTP, 强趋势逆势=保留v2参数
WT3_INPUT bool   InpEnableTrendAdaptiveExit  = false;   // 启用趋势自适应出场
WT3_INPUT double InpTrendStrengthThreshold   = 4.0;     // 趋势强度阈值(stable_bars>=此值=强趋势,保留v2)
WT3_INPUT double InpCounterTrendSLMult       = 0.40;    // 弱趋势逆势SL倍数(0.4x正常SL=收紧60%)
WT3_INPUT int    InpCounterTrendTPMode       = 1;       // 弱趋势逆势TP: 0=正常DTP, 1=SwingTarget
// P0: OB多周期堆叠
WT3_INPUT bool   InpEnableOBStacking         = false;   // 启用OB多周期堆叠加仓

// ════════════════════════════════════════════════
// P1: H4 自适应重入控制（趋势市宽松 vs 震荡市限制）
// 配合v2宽SL (InpSLBufferATR=0.4)使用, v2重入参数设宽松(H4趋势时使用)
// H4震荡时自动收紧重入限制, 防止OB区域反复自毁
// 依赖: g_trend_state_h4 (由StructureTracker或独立H4检测填充)
// ════════════════════════════════════════════════
WT3_INPUT bool   InpEnableH4Adaptive         = false;   // H4自适应重入: 趋势宽松/震荡严格
WT3_INPUT int    InpH4TrendMaxEntriesPerOB    = 20;      // [趋势市] OB最大入场次数
WT3_INPUT int    InpH4TrendReentryCooldownMin = 0;       // [趋势市] OB重入冷却(分钟)
WT3_INPUT int    InpH4TrendCooldownBars       = 0;       // [趋势市] 全局冷却bars
WT3_INPUT int    InpH4ChopMaxEntriesPerOB     = 2;       // [震荡市] OB最大入场次数
WT3_INPUT int    InpH4ChopReentryCooldownMin  = 30;      // [震荡市] OB重入冷却(分钟)
WT3_INPUT int    InpH4ChopCooldownBars        = 3;       // [震荡市] 全局冷却bars

// ════════════════════════════════════════════════
// P0: SL 使用 H1 ATR (修复致命尺度错误: M1_ATR=$1.6 → SL=$0.65; H1_ATR≈$20 → SL=$6-8)
// ════════════════════════════════════════════════
WT3_INPUT bool   InpSLUseH1ATR               = false;   // SL距离用H1_ATR替代工作TF_ATR (XAU必须开!)

// ════════════════════════════════════════════════
// P0: 多周期OB加权入场 (HTF swing OB → 宽SL抓大波段)
// 原理: H4/H1 swing高低点 → OB zone → TF权重×该TF的ATR做SL
// H4 OB weight=4.0 SL=$15-25 | H1 weight=2.0 SL=$8-15 | M1 weight=1.0 SL=$1-3(scalper)
// 同价多周期共振 → confluence bonus叠加 → 最强信号
// ════════════════════════════════════════════════
WT3_INPUT bool   InpEnableMultiTFOB           = false;   // 启用多周期OB加权入场
WT3_INPUT double InpMTFH4Weight              = 4.0;     // H4 OB权重
WT3_INPUT double InpMTFH1Weight              = 2.0;     // H1 OB权重
WT3_INPUT double InpMTFM15Weight             = 1.5;     // M15 OB权重(预留)
WT3_INPUT double InpMTFM5Weight              = 1.2;     // M5 OB权重(预留)
WT3_INPUT double InpMTFM1Weight              = 1.0;     // M1 OB基准权重
WT3_INPUT double InpMTFOBSLBufferATR         = 0.5;     // MTF OB的SL缓冲(ATR倍数, 0.5×H4_ATR≈$12-20)
WT3_INPUT double InpMTFConfluenceBonus       = 1.5;     // 多周期共振加分(>1周期重叠×此倍率)
WT3_INPUT int    InpMTFOBMaxAgeBars          = 240;     // MTF OB最大存活bars(M1 bars, 240≈4小时)
WT3_INPUT int    InpMTFMaxOBPerTF            = 3;       // 每TF最多保留OB数
WT3_INPUT double InpMTFMaxWeight            = 2.0;     // MTF仓位权重上限 ($200账户不宜超过2.0)
WT3_INPUT bool   InpMTFBlockCounterTrend     = false;   // H4趋势强制对齐: BULL禁Sell/BEAR禁Buy(默认false=v2兼容)
WT3_INPUT bool   InpEdgeBounceOnly           = false;   // P0: 仅OB边缘入场(默认false=v2兼容)
WT3_INPUT bool   InpOBFreshnessFilter        = false;   // OB新鲜度过滤(默认false=v2兼容)
WT3_INPUT int    InpOBMaxMitigations         = 2;       // OB最大缓解次数(超过后不再交易该OB)
WT3_INPUT bool   InpBOSRetestEntry           = false;   // BOS突破回踩入场(结构突破→回踩→M1 OB确认)
WT3_INPUT bool   InpBOSLockBounceEntries     = true;    // BOS开启时同步用H4方向锁约束普通Bounce入场
WT3_INPUT bool   InpBOSRetestDirectEntry     = false;   // BOS回踩到位后直接入场(默认false保持EntryEngine确认)
WT3_INPUT bool   InpKeepZonesOnProfileSwitch = false;   // XAU趋势/震荡profile切换时保留zone, 默认false保持旧行为
WT3_INPUT double InpBOSRetestSLBuffer        = 0.5;     // BOS回踩SL缓冲(ATR倍数, 突破位外侧)
WT3_INPUT double InpBOSRetestTolerance       = 0.3;     // BOS回踩容差(ATR倍数, 价格接近突破位即触发)
WT3_INPUT int    InpBOSRetestMaxBars         = 480;     // BOS回踩最大等待bars(M1, 480=8小时)
WT3_INPUT double InpBOSRetestWeight          = 1.5;     // BOS回踩仓位加权(>1.0=比普通MTF信号更高的仓位)
WT3_INPUT bool   InpBOSStrictCloseBreak      = false;   // 大周期BOS用已收K收盘突破极限价, 过滤影线假突破
WT3_INPUT bool   InpBOSRequireContinuation   = false;   // BOS回踩成交前要求小周期同向延续
WT3_INPUT int    InpBOSContinuationTF        = 5;
WT3_INPUT int    InpBOSContinuationBars      = 2;
WT3_INPUT double InpBOSContinuationMinATR    = 0.20;

// ════════════════════════════════════════════════
// P0: 流动性池检测（Liquidity Pool）
// ════════════════════════════════════════════════
WT3_INPUT bool   InpEnableLiquidityPool       = false;  // 启用流动性池检测
WT3_INPUT int    InpLPPoolLookbackBars        = 20;     // 流动性池检测回溯bars
WT3_INPUT double InpLPSwingHighSimilarityPct  = 0.2;    // 双顶/双底价格相似度阈值(%)
WT3_INPUT int    InpLPMinSweepDistancePoints  = 10;     // 最小sweep距离(points)
WT3_INPUT double InpLPSweepEntryBoost         = 1.2;    // LP sweep后入场的仓位提升倍数
WT3_INPUT bool   InpLPSweepBoostOnly           = true;   // LP sweep仅提升仓位，不独立产生信号
WT3_INPUT double InpLPMinRangeATR             = 0.3;    // 流动性池最小范围(ATR倍数)
WT3_INPUT bool   InpLPLogDetection            = false;  // 打印流动性池检测日志

// ════════════════════════════════════════════════
// P1: HTF 折扣/溢价区（Discount/Premium Zone）
// ════════════════════════════════════════════════
WT3_INPUT bool   InpEnableDiscountPremium     = false;  // 启用折扣/溢价区过滤器
WT3_INPUT double InpDiscountMaxRatio          = 0.50;   // 多头最大折扣比(>此值为溢价，拦截)
WT3_INPUT double InpPremiumMinRatio           = 0.50;   // 空头最小溢价比(<此值为折扣，拦截)
WT3_INPUT int    InpDPHTFPeriod               = 60;     // HTF周期(分钟, 60=H1)
WT3_INPUT int    InpDPLookbackBars            = 48;     // 折扣区计算回溯bars
WT3_INPUT double InpDPEntryMult               = 1.0;    // 折扣区入场仓位乘数(<=0=过滤)

// ════════════════════════════════════════════════
// P1: OB 质量评分（OB Scorer）
// ════════════════════════════════════════════════
WT3_INPUT bool   InpEnableOBScoring           = false;  // 启用OB四维评分
WT3_INPUT int    InpOBScoreMinPass            = 60;     // OB最低通过分数(0-100)
WT3_INPUT double InpOBScoreTrendWeight        = 30.0;   // 趋势突破权重
WT3_INPUT double InpOBScoreDisplacementWeight = 25.0;   // 位移K线权重
WT3_INPUT double InpOBScoreLiquidityWeight    = 20.0;   // 流动性关联权重
WT3_INPUT double InpOBScoreMitigationWeight   = 15.0;   // 缓解率权重
WT3_INPUT double InpOBScoreDiscountWeight     = 10.0;   // 折扣区权重
WT3_INPUT bool   InpOBScoreLogLow             = false;  // 打印低分OB日志

// ════════════════════════════════════════════════
// P2: 结构轨迹止损（Structure Trail）
// ════════════════════════════════════════════════
WT3_INPUT bool   InpEnableStructureTrail      = false;  // 启用结构轨迹止损
WT3_INPUT double InpStructTrailTriggerR       = 1.0;    // 结构轨迹触发R(浮盈达此值启用)
WT3_INPUT double InpStructTrailBufferATR      = 0.2;    // 结构轨迹SL缓冲(ATR倍数)
WT3_INPUT int    InpStructTrailLookback       = 10;     // 结构pivot查找bars
WT3_INPUT bool   InpStructTrailOnlyDTPFree    = false;  // 仅DTP未触发时启用

// BD08: 小周期趋势/动能持有门控
WT3_INPUT int    InpStructMomLookbackBars       = 6;     // M5/M15动能观察bars
WT3_INPUT double InpStructMomMinNetATR          = 0.30;  // 顺势净实体推进阈值(ATR)
WT3_INPUT double InpStructMomStrongRevBodyATR   = 0.55;  // 强反弹K线实体阈值(ATR)
WT3_INPUT double InpStructMomBreakBufferATR     = 0.10;  // 反向突破确认缓冲(ATR)
WT3_INPUT bool   InpStructureHoldRequireQuality = false; // 仅质量合格订单允许结构长持仓
WT3_INPUT int    InpStructureHoldQualityTF      = 5;     // 长持仓质量判断周期
WT3_INPUT int    InpStructureHoldQualityBars    = 3;     // 长持仓质量判断K线数
WT3_INPUT double InpStructureHoldQualityMinATR  = 0.35;  // 长持仓顺向净推进阈值(ATR)
WT3_INPUT bool   InpStructureHoldQualityRequireStrongBreak = false; // 长持仓需强高低点突破
WT3_INPUT bool   InpStructureHoldDynamicRelease = false; // 小周期反转且顺向动能衰弱时恢复普通出场
WT3_INPUT double InpStructureHoldReleaseMinR    = 0.30;  // 动态解除结构持仓所需最小浮盈R
WT3_INPUT bool   InpStructureHoldReleaseRequireReverseContinuation = false; // 解除需反向动能延续

// BD08: micro structure break + retest entry, default off.
WT3_INPUT bool   InpEnableMicroBOSRetest       = false;
WT3_INPUT int    InpMicroBOSTF                 = 5;
WT3_INPUT int    InpMicroBOSLookbackBars       = 48;
WT3_INPUT int    InpMicroBOSPivotBars          = 2;
WT3_INPUT double InpMicroBOSBreakBufferATR     = 0.05;
WT3_INPUT double InpMicroBOSMinNetATR          = 0.25;
WT3_INPUT double InpMicroBOSExtensionATR       = 0.35;
WT3_INPUT double InpMicroBOSRetestToleranceATR = 0.20;
WT3_INPUT double InpMicroBOSZoneATR            = 0.30;
WT3_INPUT double InpMicroBOSSLATR              = 0.70;
WT3_INPUT double InpMicroBOSPosMult            = 1.0;
WT3_INPUT int    InpMicroBOSMaxBars            = 72;
WT3_INPUT int    InpMicroBOSCooldownBars       = 24;
WT3_INPUT int    InpMicroBOSMinBounceSec       = 0;
WT3_INPUT int    InpMicroBOSMaxBounceSec       = 0;
WT3_INPUT double InpMicroBOSMinFinalPosMult    = 0.0;
WT3_INPUT bool   InpMicroBOSRequireH4Aligned   = false;
WT3_INPUT bool   InpMicroBOSRequireContinuation = false;
WT3_INPUT int    InpMicroBOSContinuationTF     = 5;
WT3_INPUT int    InpMicroBOSContinuationBars   = 2;
WT3_INPUT double InpMicroBOSContinuationMinATR = 0.20;
WT3_INPUT bool   InpMicroBOSUseStructureHold   = false;
WT3_INPUT bool   InpMicroBOSRequireZoneConfluence = false;
WT3_INPUT bool   InpMicroBOSConfluenceAllowOB  = true;
WT3_INPUT bool   InpMicroBOSConfluenceAllowFVG = true;
WT3_INPUT double InpMicroBOSConfluenceToleranceATR = 0.25;

// BD08: supply/demand flip after an opposite OB is engulfed, default off.
WT3_INPUT bool   InpEnableSupplyDemandFlip      = false;
WT3_INPUT int    InpSDFlipTF                    = 5;
WT3_INPUT int    InpSDFlipLookbackBars          = 36;
WT3_INPUT bool   InpSDFlipRequireSourceOB       = true;
WT3_INPUT double InpSDFlipMinBodyATR            = 0.80;
WT3_INPUT double InpSDFlipBreakBufferATR        = 0.05;
WT3_INPUT double InpSDFlipRetestToleranceATR    = 0.20;
WT3_INPUT double InpSDFlipZoneATR               = 0.35;
WT3_INPUT double InpSDFlipSLATR                 = 0.80;
WT3_INPUT double InpSDFlipPosMult               = 1.0;
WT3_INPUT int    InpSDFlipMaxBars               = 120;
WT3_INPUT int    InpSDFlipCooldownBars          = 30;
WT3_INPUT bool   InpSDFlipRequireH4Aligned      = true;
WT3_INPUT bool   InpSDFlipRequireContinuation   = true;
WT3_INPUT int    InpSDFlipContinuationTF        = 1;
WT3_INPUT int    InpSDFlipContinuationBars      = 2;
WT3_INPUT double InpSDFlipContinuationMinATR    = 0.20;
WT3_INPUT bool   InpSDFlipUseStructureHold      = true;

// BD08: 强高低点扫损后的反向入场, default off.
WT3_INPUT bool   InpEnableStrongSweepReversal   = false;
WT3_INPUT int    InpStrongSweepTF               = 5;
WT3_INPUT int    InpStrongSweepLookbackBars     = 48;
WT3_INPUT int    InpStrongSweepPivotBars        = 2;
WT3_INPUT double InpStrongSweepPenetrationATR   = 0.05;
WT3_INPUT double InpStrongSweepCloseBackATR     = 0.02;
WT3_INPUT double InpStrongSweepWickPct          = 35.0;
WT3_INPUT bool   InpStrongSweepRequireDP        = true;
WT3_INPUT int    InpStrongSweepDPTF             = 60;
WT3_INPUT int    InpStrongSweepDPLookbackBars   = 48;
WT3_INPUT double InpStrongSweepDiscountMax      = 0.50;
WT3_INPUT double InpStrongSweepPremiumMin       = 0.50;
WT3_INPUT bool   InpStrongSweepRequireContinuation = true;
WT3_INPUT int    InpStrongSweepContinuationTF   = 1;
WT3_INPUT int    InpStrongSweepContinuationBars = 2;
WT3_INPUT double InpStrongSweepContinuationMinATR = 0.15;
WT3_INPUT double InpStrongSweepZoneATR          = 0.25;
WT3_INPUT double InpStrongSweepSLATR            = 0.70;
WT3_INPUT double InpStrongSweepPosMult          = 0.35;
WT3_INPUT double InpStrongSweepMaxLotSize       = 0.05;
WT3_INPUT int    InpStrongSweepMaxBars          = 72;
WT3_INPUT int    InpStrongSweepCooldownBars     = 12;
WT3_INPUT bool   InpStrongSweepUseStructureHold = false;

// BD08: lightweight regime position multiplier, default off.
WT3_INPUT bool   InpEnableLightRegimePosMult    = false;
WT3_INPUT int    InpLightRegimeTF               = 60;
WT3_INPUT int    InpLightRegimeBars             = 3;
WT3_INPUT double InpLightRegimeMinNetATR        = 0.45;
WT3_INPUT double InpLightRegimeTrendAlignedMult = 1.0;
WT3_INPUT double InpLightRegimeTrendCounterMult = 1.0;
WT3_INPUT double InpLightRegimeRangeMult        = 1.0;
WT3_INPUT bool   InpLightRegimeSweepOnly        = true;

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
bool CfgEnableStructureMomentumHold(){ return InpEnableStructureMomentumHold; }
bool CfgEnableMicroBOSRetest()       { return InpEnableMicroBOSRetest; }
bool CfgEnableSupplyDemandFlip()     { return InpEnableSupplyDemandFlip; }
bool CfgEnableH4Adaptive()           { return InpEnableH4Adaptive; }
bool CfgSLUseH1ATR()                 { return InpSLUseH1ATR; }
int  CfgH4TrendMaxEntriesPerOB()     { return InpH4TrendMaxEntriesPerOB; }
int  CfgH4TrendReentryCooldownMin()  { return InpH4TrendReentryCooldownMin; }
int  CfgH4TrendCooldownBars()        { return InpH4TrendCooldownBars; }
int  CfgH4ChopMaxEntriesPerOB()      { return InpH4ChopMaxEntriesPerOB; }
int  CfgH4ChopReentryCooldownMin()   { return InpH4ChopReentryCooldownMin; }
int  CfgH4ChopCooldownBars()         { return InpH4ChopCooldownBars; }


// ════════════════════════════════════════════════
// P1: PS1 - 由基线 OB/BOS 播种的趋势 campaign 重载
// 仅当 baseline 入口在同方向上已实现盈利/亏损后, 在新结构级别(M5 BOS/CHOCH)
// 形成独立再入, 禁止同 OB 重入和失败后的即时加仓
// ════════════════════════════════════════════════
WT3_PS1_INPUT bool   InpEnablePS1Campaign            = false;  // [PS1] 启用 baseline-seeded trend campaign 重载
WT3_PS1_INPUT int    InpPS1BaselineEntryWindowMin  = 240;    // baseline 入场后多少分钟内允许 PS1 重载 (默认 240=4h)
WT3_PS1_INPUT int    InpPS1MaxReloadPerWeek         = 1;       // PS1 重载频次上限 (每周最多 1 次, 防滥用)
WT3_PS1_INPUT double InpPS1MinCampaignR            = -0.3;    // baseline 出场 R 最小值 (>= 此值才认为方向有效; -0.3=允许小亏)
WT3_PS1_INPUT double InpPS1MaxCampaignR            = 8.0;     // baseline 出场 R 最大值 (<= 此值才允许 PS1, 避免已捕获极限趋势)
WT3_PS1_INPUT double InpPS1MinBossConfidence       = 0.5;     // M5 BOS/CHOCH 突破强度下限 (0.5 = 0.5 ATR)
WT3_PS1_INPUT double InpPS1MaxLotSize              = 0.05;    // PS1 重载最大手数 ($200 账户: 0.05 约 $5-10 风险)
WT3_PS1_INPUT int    InpPS1CooldownBars            = 12;      // PS1 重载后冷却 bars (M1 12 根 = 12min)
WT3_INPUT bool   InpPS1Log                     = true;    // 打印 PS1 状态机日志


#endif
