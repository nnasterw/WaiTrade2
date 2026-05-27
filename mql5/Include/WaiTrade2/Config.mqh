#ifndef __WAITRADE_CONFIG_MQH__
#define __WAITRADE_CONFIG_MQH__

// ═══════════════════════════════════════════════════════════════════════════
// WaiTrade2 EA — 输入参数定义 (V96b默认值)
// ═══════════════════════════════════════════════════════════════════════════

// ── OB检测 ──────────────────────────────────────────────────────────────────
input double InpBouncePct        = 0.30;     // OB确认反弹幅度(%)
input int    InpTimeoutMin       = 60;       // OB过期时间(分钟)
input double InpMaxEntryOffsetR  = 1.5;      // 最大入场偏移(R倍数)
input double InpEntryDepthPct    = 0.0;      // OB深入触及比例(0=边缘,0.5=中线,0.67=中下/中上)
input bool   InpEntryDepthFilter = true;     // true=必须深位触及才入场,false=深位仅作加仓标记
input double InpEntryDepthRelaxMinBalance = 0.0; // 余额达到该值后启用较浅EntryDepthPct(0=始终启用)
input double InpDeepEntryBoost   = 1.0;      // 深入OB后入场的仓位倍数(1=禁用加仓)
input int    InpEntryConfirmBars = 0;        // Bounce后需突破最近N根K线高/低(0=禁用)
input int    InpBounceCloseConfirmBars = 0;  // Bounce后需连续N根收在OB外侧(0=禁用)
input int    InpBounceCloseTF    = 1;        // Bounce收盘确认周期(分钟,0=工作周期)
input double InpBounceCloseBufferPct = 0.0;  // 收盘需越过OB边缘的OB高度比例
input bool   InpBounceCloseRequireBody = false; // 收盘确认K需同方向实体
input bool   InpEnableConfirmPullback = false; // Bounce确认后等待短回踩入场
input double InpConfirmPullbackPct = 0.50;   // 回踩比例: 触点到确认价区间
input int    InpConfirmPullbackWaitSec = 30; // 回踩等待秒数
input double InpConfirmPullbackMaxAdversePct = 0.20; // 反向跌破触点容忍OB高度比例
input bool   InpEnableEntryMomentumFilter = false; // 启用入场强弱转换过滤
input int    InpEntryMomentumTF = 1;         // 入场强弱过滤周期(分钟,0=工作周期)
input bool   InpEntryBlockCounterStrong = true; // 反向强势未转弱时禁止入场
input bool   InpEntryRequireCounterWeak = false; // 入场必须出现反向趋势转弱证据
input bool   InpRequireDoubleTch = true;     // 要求二次触碰
input int    InpDoubleTchWindowMin = 60;     // 二次触碰窗口(分钟)
input double InpMinOBSpreadMult  = 2.0;      // 最小OB宽度(点差倍数)
input double InpMinRiskSpreadRatio = 3.0;    // 最小风险/点差比
input double InpMinAbsRiskUSD    = 0.0;      // 最小绝对风险(USD)
input double InpMinOBBodyPct     = 50.0;     // OB蜡烛最小实体占比(%)
input double InpMinImpulseBodyPct = 0.0;     // 位移K线最小实体占比(%)
input double InpMinImpulseVolRatio = 0.0;    // 位移K线最小成交量倍率(0=禁用)
input int    InpStructureBreakBars = 0;      // 严格结构突破窗口(0=仅用旧Gap2)
input double InpStructureBreakATR = 0.0;     // 严格结构突破额外ATR阈值
input bool   InpRequireImpulseCandleDir = false; // 位移K必须同方向收盘
input bool   InpEnableRangeBreakout = false; // 启用震荡区间有效突破入场
input bool   InpRangeBreakoutOnly = false;   // 仅交易震荡区间突破，关闭常规OB
input int    InpRangeBreakoutBars = 10;      // 震荡区间观察bar数
input double InpRangeBreakoutMaxATR = 1.20;  // 区间最大高度/ATR
input double InpRangeBreakoutMinSpreadMult = 3.0; // 区间最小高度/spread
input double InpRangeBreakoutATR = 0.10;     // 有效突破额外ATR阈值
input double InpRangeBreakoutTPMult = 1.0;   // TP=区间高度倍数(0=不用固定TP)
input bool   InpRangeBreakoutBodyDir = true; // 突破K必须同方向实体
input bool   InpEnableLiquiditySweep = false; // 启用流动性扫损反转入场
input bool   InpLiquiditySweepOnly = false;   // 仅交易扫损反转，关闭常规OB
input int    InpSweepLookbackBars = 12;       // 扫损参考区间bar数
input double InpSweepMaxRangeATR = 2.50;      // 参考区间最大高度/ATR
input double InpSweepMinRangeSpreadMult = 4.0; // 参考区间最小高度/spread
input double InpSweepMinPenetrationATR = 0.05; // 扫破区间额外ATR阈值
input double InpSweepMinWickPct = 45.0;       // 扫损K最小影线占比
input double InpSweepTPMult = 1.0;            // TP=原区间高度倍数(0=DTP)
input bool   InpEnableLooseSweep = false;     // 启用第二条宽松Sweep补频腿
input int    InpLooseSweepLookbackBars = 6;   // 宽松Sweep参考区间bar数
input double InpLooseSweepMaxRangeATR = 4.0;  // 宽松Sweep参考区间最大高度/ATR
input double InpLooseSweepMinRangeSpreadMult = 2.5; // 宽松Sweep最小高度/spread
input double InpLooseSweepMinPenetrationATR = 0.01; // 宽松Sweep扫破ATR阈值
input double InpLooseSweepMinWickPct = 30.0;  // 宽松Sweep最小影线占比
input int    InpNoOBStartHour    = 23;       // 禁止建OB开始小时(服务器时间,-1=禁用)
input int    InpNoOBEndHour      = 6;        // 禁止建OB结束小时(服务器时间,-1=禁用)
input double InpMinOBStrength    = 0.5;      // 最低OB强度
input double InpMaxRiskATR       = 3.0;      // 最大risk/ATR
input double InpMaxCounterRiskATR = 1.5;     // 逆势最大risk/ATR
input bool   InpConsolidateOB    = true;     // 合并重叠OB
input double InpSpreadFloor      = 0.0;      // 最小spread下限(0=使用实时spread)

// ── Impulse参数 ──────────────────────────────────────────────────────────
input double InpImpulseATRMult   = 1.5;      // Impulse判定阈值(ATR倍数)
input int    InpImpulseLookback  = 3;        // Impulse观察窗口(bars)
input int    InpATRPeriod        = 14;       // ATR计算周期

// ── 止损 ──────────────────────────────────────────────────────────────────
input double InpSLBufferATR      = 0.10;     // SL额外ATR缓冲

// ── 保本 ──────────────────────────────────────────────────────────────────
input double InpBreakevenR       = 0.2;      // 保本触发(R倍数)
input double InpBreakevenLockR   = 0.05;     // 保本锁定利润(R倍数)
input double InpEarlyLossCutR    = 0.0;      // 入场后未保本前主动小亏退出R(0=禁用)
input double InpMFEFailMinR      = 0.0;      // 曾达到该浮盈后启用失败退出(0=禁用)
input double InpMFEFailExitR     = 0.0;      // 浮盈后回落至该R主动退出
input int    InpNoMFEExitBars    = 0;        // 持仓N根后仍无最小浮盈则退出(0=禁用)
input double InpNoMFEMinPeakR    = 0.0;      // 判断有浮盈的最小峰值R
input double InpNoMFEExitR       = 0.0;      // 无浮盈失败退出的当前R阈值
input bool   InpEnableFailureReverse = false; // 主动失败退出后反向开单
input bool   InpReverseOnEarlyLoss = false;  // early_loss后反手
input bool   InpReverseOnMFEFail   = false;  // mfe_fail后反手
input bool   InpReverseOnNoMFE     = false;  // no_mfe后反手
input double InpFailureReverseRiskMult = 1.0; // 反手单SL距离=原始risk倍数
input double InpFailureReverseLotMult  = 1.0; // 反手单仓位倍数
input double InpFailureReverseTPR      = 0.0; // 反手固定TP R(0=沿用DTP)
input bool   InpFailureReverseAllowChain = false; // 允许反手单继续反手

// ── 追踪止损 ──────────────────────────────────────────────────────────────
input double InpTrail1TriggerR   = 1.0;      // 追踪1触发(R)
input double InpTrail1LockR      = 0.2;      // 追踪1锁定(R)
input double InpTrail2TriggerR   = 2.5;      // 追踪2触发(R)
input double InpTrail2LockR      = 0.0;      // 追踪2锁定(R, 固定)
input double InpTrail2LockMult   = 0.65;     // 追踪2锁定(乘数)
input double InpTrail3TriggerR   = 0.0;      // 追踪3触发(R, 0=禁用)
input double InpTrail3LockR      = 0.0;      // 追踪3锁定(R)
input double InpTrail3LockMult   = 0.0;      // 追踪3锁定(乘数)

// ── DTP (动态止盈) ───────────────────────────────────────────────────────
input double InpDTPTriggerR      = 1.5;      // DTP激活阈值(R, 0=禁用)
input double InpDTPRetrace       = 0.30;     // DTP回撤关闭比例
input bool   InpAdaptiveDTP      = true;     // 自适应DTP
input double InpDTPStage2TriggerR = 0.0;     // DTP二阶触发峰值R(0=禁用)
input double InpDTPStage2Retrace = 0.0;      // DTP二阶回撤比例(0=禁用)
input double InpDTPStage3TriggerR = 0.0;     // DTP三阶触发峰值R(0=禁用)
input double InpDTPStage3Retrace = 0.0;      // DTP三阶回撤比例(0=禁用)
input int    InpDTPExitMode      = 0;        // DTP退出模式(0=全平,1=先部分平仓)
input int    InpDTPPartialPct    = 50;       // DTP部分平仓比例(%)
input double InpDTPPostPartialRetrace = 0.0; // DTP部分平仓后回撤比例(0=沿用)
input double InpDTPPostPartialLockR = 0.0;   // DTP部分平仓后剩余仓SL锁定R(0=禁用)
input bool   InpDTPResetPeakAfterPartial = false; // DTP部分平仓后重置余仓峰值
input double InpFixedTPR         = 0.0;      // 固定止盈(R, 0=DTP模式)
input double InpOBHeightTPMult   = 0.0;      // TP=OB高度倍数(0=禁用,2=量度移动)

// ── 分层入场(震荡网格) ──────────────────────────────────────────────────
input int    InpLayeredEntryCount = 0;       // 分层入场数(0=禁用,2-3=分层)
input double InpLayeredSpacingPct = 0.33;    // 分层间距(OB高度百分比)
input double InpLayeredLotMult    = 1.5;     // 深层仓位倍数(相对首层)
input double InpLayeredAvgTP_R    = 0.0;     // 从均价算TP(R,0=用其他TP)
input int    InpMicroEntryCount   = 0;       // 同信号微仓副单数(0=禁用)
input double InpMicroEntryLotMult = 0.05;    // 微仓副单手数倍数(相对主单)
input double InpMicroEntryMaxLotSize = 0.0;  // 微仓副单最大手数(0=不限制)

// ── 时间退出 ──────────────────────────────────────────────────────────────
input int    InpTimeExitBars     = 999;      // 超时退出(bars, 999=禁用)
input bool   InpTimeDecayTP      = false;    // 时间衰减TP

// ── 仓位管理 ──────────────────────────────────────────────────────────────
input double InpRiskPercent      = 2.0;      // 单笔风险(%余额)
input double InpFixedLotSize     = 0.0;      // 固定手数(>0时忽略风险%)
input bool   InpEnablePosMult    = true;     // 启用仓位乘数(false=固定1.0)
input double InpMaxPosMult       = 0.0;      // 最大仓位乘数(0=不限制)
input double InpMaxLotSize       = 0.0;      // 最大手数(0=不限制)
input double InpSweepPosMult     = 1.0;      // 扫损反转信号仓位倍数
input double InpRangeBreakoutPosMult = 1.0;  // 区间突破信号仓位倍数
input double InpHTFPullbackPosMult = 1.0;    // HTF回踩信号仓位倍数
input double InpSweepMaxLotSize  = 0.0;      // 扫损反转信号最大手数(0=不限制)
input double InpLooseSweepPosMult = 0.05;    // 宽松Sweep补频腿仓位倍数
input double InpLooseSweepMaxLotSize = 0.005; // 宽松Sweep补频腿最大手数(0=不限制)
input int    InpLooseSweepMaxActiveZones = 20; // max active loose sweep zones (0=unlimited)
input double InpRangeBreakoutMaxLotSize = 0.0; // 区间突破信号最大手数(0=不限制)
input double InpHTFPullbackMaxLotSize = 0.0; // HTF回踩信号最大手数(0=不限制)
input string InpHTFPullbackAllowHours = ""; // HTF回踩允许小时CSV(空=全部允许)
input string InpHTFPullbackNoHours = "";    // HTF回踩禁止小时CSV(空=禁用)
input double InpHTFPullbackRiskMin = 0.0;   // HTF回踩风险下限(0=禁用)
input double InpHTFPullbackRiskMax = 0.0;   // HTF回踩风险上限(<=min=禁用)
input double InpHTFPullbackConfirmMin = -999.0; // HTF回踩确认位置下限
input double InpHTFPullbackConfirmMax = 999.0;  // HTF回踩确认位置上限
input double InpHTFPullbackContextMult = 1.0;   // HTF回踩上下文仓位倍数(<=0=过滤)
input string InpSweepAllowHours  = "";       // Sweep允许小时CSV(空=全部允许)
input string InpSweepNoHours     = "";       // Sweep禁止小时CSV(空=禁用)
input string InpSweepContextMonths = "";     // Sweep上下文过滤月份CSV(空=全部月份)
input int    InpSweepContextMaxDay = 0;      // Sweep上下文过滤仅月内前N天启用(0=不限)
input double InpSweepContextMinMonthStartBalance = 0.0; // Sweep上下文过滤月初余额下限(0=不限)
input string InpSweepContextNoHours = "";   // Sweep上下文额外禁止小时CSV(空=禁用)
input double InpSweepBadRiskMin  = 0.0;      // Sweep弱风险区间下限
input double InpSweepBadRiskMax  = 0.0;      // Sweep弱风险区间上限
input double InpSweepBadRiskMult = 1.0;      // Sweep弱风险区间仓位倍数(<=0过滤)
input double InpSweepMinBalance  = 0.0;      // 余额低于该值时过滤Sweep(0=禁用)
input double InpSweepLowBalanceThreshold = 0.0; // 余额低于该值时Sweep降权(0=禁用)
input double InpSweepLowBalanceMult = 1.0;   // 低余额Sweep仓位倍数(<=0过滤)
input double InpSweepMonthlyNegativeMult = 1.0; // 月内余额低于月初时Sweep仓位倍数(<=0过滤)
input double InpSweepMonthlyProfitStartPct = 0.0; // 月内盈利达到月初该百分比后才允许Sweep(0=禁用)
input int    InpSweepEarlyBounceSecMin = 0; // Sweep early confirmation lower bound seconds (0=disabled)
input int    InpSweepEarlyBounceSecMax = 0; // Sweep early confirmation upper bound seconds (<=min=disabled)
input double InpSweepEarlyBounceMult = 1.0; // Sweep early confirmation position multiplier (<=0=filter)
input string InpSweepEarlyBounceHours = ""; // CSV hours where early confirmation multiplier applies (empty=all hours)
input int    InpSweepBadAgeMinBars = 0;     // Sweep zone age bad-cluster min bars (inclusive; 0=disabled)
input int    InpSweepBadAgeMaxBars = 0;     // Sweep zone age bad-cluster max bars (exclusive; <=min=disabled)
input double InpSweepBadAgeMult = 1.0;      // Sweep bad-age position multiplier (<=0=filter)
input double InpOBPosMult       = 1.0;      // regular OB position multiplier; does not affect sweep/range/HTFPB
input double InpOBPosMultMinBalance = 0.0;  // minimum balance before OB position multiplier is active
input string InpOBBadHours       = "";       // 普通OB弱小时CSV(不影响Sweep/区间突破)
input double InpOBBadHourMult    = 1.0;      // 普通OB弱小时仓位倍数(<=0过滤)
input string InpLowBalanceOBBadHours = "";  // 低余额普通OB弱小时CSV
input string InpLowBalanceOBBadMonths = ""; // 低余额普通OB弱月份CSV(空=全部月份)
input double InpLowBalanceOBBadMaxMonthStartBalance = 0.0; // 月初余额不高于该值时启用(0=禁用)
input double InpLowBalanceOBBadHourMult = 1.0; // 低余额普通OB弱小时仓位倍数(<=0过滤)
input double InpLowBalanceThreshold = 0.0;   // 余额低于该值启用启动期保护(0=禁用)
input double InpLowBalancePosMult = 1.0;     // 启动期仓位倍数
input double InpLowBalanceMaxLotSize = 0.0;  // 启动期最大手数(0=不限制)
input double InpMonthlyGuardMinBalance = 0.0; // 余额达到该值后才启用月内风控(0=始终启用)
input double InpMonthlyLossStopPct = 0.0;    // 月内余额回撤超过该百分比后停止新开仓(0=禁用)
input int    InpMonthlyLossStopMinTrades = 0; // 月亏停止前至少允许的月内开仓数(0=达到即停)
input int    InpMonthlyEarlyLossStopTrades = 0; // 月初第N笔后检查一次弱月熔断(0=禁用)
input double InpMonthlyEarlyLossStopPct = 0.0;  // 月初弱月熔断亏损百分比
input double InpMonthlyEarlyLossStopMinBalance = 0.0; // 月初弱月熔断启用余额(0=始终启用)
input double InpMonthlyNegativePosMult = 1.0; // 月内余额低于月初时仓位倍数
input bool   InpMonthlyEarlyLossStopContinuous = false; // true=第N笔后持续检查弱月熔断，false=只在第N笔检查
input double InpMonthlyWarmupProfitPct = 0.0; // month profit pct required before full size (0=disabled)
input double InpMonthlyWarmupPosMult = 1.0;   // position multiplier before monthly warmup profit is reached
input double InpMonthlyProfitLockMinBalance = 0.0; // 余额达到该值后启用月内盈利回吐锁(0=始终启用)
input double InpMonthlyProfitLockStartPct = 0.0; // 月内盈利达到月初余额百分比后启用回吐锁(0=禁用)
input double InpMonthlyProfitLockKeepPct = 0.0;  // 回吐到峰值盈利的该百分比以下停止新开仓
input double InpMonthlyProfitTargetStopPct = 0.0; // 月内达到盈利目标后停止新入场(%月初余额,0=禁用)
input double InpMonthlyProfitTargetStopMinBalance = 0.0; // 月初余额不低于该值时启用盈利目标停手(0=不限)
input double InpMonthlyProfitTargetStopMaxBalance = 0.0; // 月初余额不高于该值时启用盈利目标停手(0=不限)
input string InpMonthlyProfitTargetStopMonths = ""; // 月度盈利目标停手月份CSV(空=全部月份)
input double InpMonthlyProfitTargetStop2Pct = 0.0; // 第二组月内盈利目标停手(%月初余额,0=禁用)
input double InpMonthlyProfitTargetStop2MinBalance = 0.0; // 第二组月初余额下限(0=不限)
input double InpMonthlyProfitTargetStop2MaxBalance = 0.0; // 第二组月初余额上限(0=不限)
input string InpMonthlyProfitTargetStop2Months = ""; // 第二组月度盈利目标停手月份CSV(空=全部月份)
input bool   InpSharedMonthlyGuard = false; // 多图表共享月度风控状态(默认关闭)
input string InpSharedMonthlyGuardKey = ""; // 共享月度风控Key(同组合必须一致)
input bool   InpSharedMonthlyGuardDebug = false; // 打印共享月度风控诊断日志
input int    InpMaxConcurrent    = 5;        // 最大同时持仓数
input double InpFreeRunMinR      = 0.0;      // 浮盈≥此R不计并发(0=禁用)
input int    InpCooldownBars     = 0;        // 开仓冷却(bars)
input string InpEntryMonths      = "";       // 允许入场月份CSV, 如"3,11"(空=全部月份)
input string InpNoEntryHours     = "";       // 禁止入场小时CSV, 如"0,9,12"(空=禁用)
input string InpNoBuyHours       = "";       // 禁止做多小时CSV(空=禁用)
input string InpNoSellHours      = "";       // 禁止做空小时CSV(空=禁用)
input string InpLowRiskHours     = "";       // 低仓位小时CSV(空=禁用)
input double InpLowRiskHourMult  = 1.0;      // 低仓位小时仓位倍数
input string InpHighRiskHours    = "";       // 高仓位小时CSV(空=禁用)
input double InpHighRiskHourMult = 1.0;      // 高仓位小时仓位倍数
input string InpContextFilter1Months = "";   // Context filter1 months CSV(empty=all)
input string InpContextFilter1NoHours = "";  // Context filter1 blocked hours CSV
input string InpContextFilter1NoBuyHours = ""; // Context filter1 blocked buy hours CSV
input string InpContextFilter1NoSellHours = ""; // Context filter1 blocked sell hours CSV
input double InpContextFilter1MinMonthStartBalance = 0.0; // Context filter1 month-start min balance
input double InpContextFilter1MaxMonthStartBalance = 0.0; // Context filter1 month-start max balance
input double InpContextFilter1Mult = 1.0;     // Context filter1 position multiplier(<=0=filter)
input string InpContextFilter2Months = "";   // Context filter2 months CSV(empty=all)
input string InpContextFilter2NoHours = "";  // Context filter2 blocked hours CSV
input string InpContextFilter2NoBuyHours = ""; // Context filter2 blocked buy hours CSV
input string InpContextFilter2NoSellHours = ""; // Context filter2 blocked sell hours CSV
input double InpContextFilter2MinMonthStartBalance = 0.0; // Context filter2 month-start min balance
input double InpContextFilter2MaxMonthStartBalance = 0.0; // Context filter2 month-start max balance
input double InpContextFilter2Mult = 1.0;     // Context filter2 position multiplier(<=0=filter)
input string InpContextFilter3Months = "";   // Context filter3 months CSV(empty=all)
input string InpContextFilter3NoHours = "";  // Context filter3 blocked hours CSV
input string InpContextFilter3NoBuyHours = ""; // Context filter3 blocked buy hours CSV
input string InpContextFilter3NoSellHours = ""; // Context filter3 blocked sell hours CSV
input double InpContextFilter3MinMonthStartBalance = 0.0; // Context filter3 month-start min balance
input double InpContextFilter3MaxMonthStartBalance = 0.0; // Context filter3 month-start max balance
input double InpContextFilter3Mult = 1.0;     // Context filter3 position multiplier(<=0=filter)
input string InpContextFilter4Months = "";   // Context filter4 months CSV(empty=all)
input string InpContextFilter4NoHours = "";  // Context filter4 blocked hours CSV
input string InpContextFilter4NoBuyHours = ""; // Context filter4 blocked buy hours CSV
input string InpContextFilter4NoSellHours = ""; // Context filter4 blocked sell hours CSV
input double InpContextFilter4MinMonthStartBalance = 0.0; // Context filter4 month-start min balance
input double InpContextFilter4MaxMonthStartBalance = 0.0; // Context filter4 month-start max balance
input double InpContextFilter4Mult = 1.0;     // Context filter4 position multiplier(<=0=filter)
input string InpContextFilter5Months = "";   // Context filter5 months CSV(empty=all)
input string InpContextFilter5NoHours = "";  // Context filter5 blocked hours CSV
input string InpContextFilter5NoBuyHours = ""; // Context filter5 blocked buy hours CSV
input string InpContextFilter5NoSellHours = ""; // Context filter5 blocked sell hours CSV
input double InpContextFilter5MinMonthStartBalance = 0.0; // Context filter5 month-start min balance
input double InpContextFilter5MaxMonthStartBalance = 0.0; // Context filter5 month-start max balance
input double InpContextFilter5Mult = 1.0;     // Context filter5 position multiplier(<=0=filter)
input int    InpLateBounceSec    = 0;        // Bounce确认超过N秒后降权(0=禁用)
input double InpLateBounceMult   = 1.0;      // 晚确认仓位倍数
input double InpBounceSweetMinPct = 0.0;     // Bounce甜点下限(OB高度比例,0=禁用)
input double InpBounceSweetMaxPct = 0.0;     // Bounce甜点上限(OB高度比例,0=禁用)
input double InpOutsideBounceSweetMult = 1.0; // 非Bounce甜点仓位倍数
input double InpBadRiskMin       = 0.0;      // 弱风险区间下限(价格距离,0=禁用)
input double InpBadRiskMax       = 0.0;      // 弱风险区间上限(价格距离,0=禁用)
input double InpBadRiskMult      = 1.0;      // 弱风险区间仓位倍数
input double InpLargeRiskMin     = 0.0;      // 大风险结构下限(价格距离,0=禁用)
input double InpLargeRiskMult    = 1.0;      // 大风险结构仓位倍数
input double InpShallowConfirmPosMin = -999.0; // 确认位置过浅阈值(confirm_ob_pos,<=-999禁用)
input double InpShallowConfirmPosMult = 1.0; // 确认位置过浅仓位倍数(<=0过滤)
input double InpBadClusterMinBalance = 0.0;  // 余额达到该值后才启用组合坏簇降权(0=始终启用)
input bool   InpBadClusterOnlyMonthlyNegative = false; // 仅月内余额低于月初时启用组合坏簇降权
input string InpBadCluster1Hours = "";       // 组合坏簇1小时CSV(空=禁用)
input double InpBadCluster1RiskMin = 0.0;    // 组合坏簇1风险下限
input double InpBadCluster1RiskMax = 0.0;    // 组合坏簇1风险上限(<=min=禁用风险条件)
input double InpBadCluster1ConfirmMin = -999.0; // 组合坏簇1确认位置下限
input double InpBadCluster1ConfirmMax = 999.0;  // 组合坏簇1确认位置上限
input double InpBadCluster1Mult = 1.0;       // 组合坏簇1仓位倍数(<=0过滤)
input string InpBadCluster1Signal = "";      // 组合坏簇1信号类型(all/ob/sweep/range)
input string InpBadCluster2Hours = "";       // 组合坏簇2小时CSV(空=禁用)
input double InpBadCluster2RiskMin = 0.0;    // 组合坏簇2风险下限
input double InpBadCluster2RiskMax = 0.0;    // 组合坏簇2风险上限(<=min=禁用风险条件)
input double InpBadCluster2ConfirmMin = -999.0; // 组合坏簇2确认位置下限
input double InpBadCluster2ConfirmMax = 999.0;  // 组合坏簇2确认位置上限
input double InpBadCluster2Mult = 1.0;       // 组合坏簇2仓位倍数(<=0过滤)
input string InpBadCluster2Signal = "";      // 组合坏簇2信号类型(all/ob/sweep/range)
input string InpBadCluster3Hours = "";       // 组合坏簇3小时CSV(空=禁用)
input double InpBadCluster3RiskMin = 0.0;    // 组合坏簇3风险下限
input double InpBadCluster3RiskMax = 0.0;    // 组合坏簇3风险上限(<=min=禁用风险条件)
input double InpBadCluster3ConfirmMin = -999.0; // 组合坏簇3确认位置下限
input double InpBadCluster3ConfirmMax = 999.0;  // 组合坏簇3确认位置上限
input double InpBadCluster3Mult = 1.0;       // 组合坏簇3仓位倍数(<=0过滤)
input string InpBadCluster3Signal = "";      // 组合坏簇3信号类型(all/ob/sweep/range)
input string InpBadCluster4Hours = "";       // 组合坏簇4小时CSV(空=禁用)
input double InpBadCluster4RiskMin = 0.0;    // 组合坏簇4风险下限
input double InpBadCluster4RiskMax = 0.0;    // 组合坏簇4风险上限(<=min=禁用风险条件)
input double InpBadCluster4ConfirmMin = -999.0; // 组合坏簇4确认位置下限
input double InpBadCluster4ConfirmMax = 999.0;  // 组合坏簇4确认位置上限
input double InpBadCluster4Mult = 1.0;       // 组合坏簇4仓位倍数(<=0过滤)
input string InpBadCluster4Signal = "";      // 组合坏簇4信号类型(all/ob/sweep/range)
input string InpBadCluster5Hours = "";       // 组合坏簇5小时CSV(空=禁用)
input double InpBadCluster5RiskMin = 0.0;    // 组合坏簇5风险下限
input double InpBadCluster5RiskMax = 0.0;    // 组合坏簇5风险上限(<=min=禁用风险条件)
input double InpBadCluster5ConfirmMin = -999.0; // 组合坏簇5确认位置下限
input double InpBadCluster5ConfirmMax = 999.0;  // 组合坏簇5确认位置上限
input double InpBadCluster5Mult = 1.0;       // 组合坏簇5仓位倍数(<=0过滤)
input string InpBadCluster5Signal = "";      // 组合坏簇5信号类型(all/ob/sweep/range)
input string InpBadCluster6Hours = "";       // 组合坏簇6小时CSV(空=禁用)
input double InpBadCluster6RiskMin = 0.0;    // 组合坏簇6风险下限
input double InpBadCluster6RiskMax = 0.0;    // 组合坏簇6风险上限(<=min=禁用风险条件)
input double InpBadCluster6ConfirmMin = -999.0; // 组合坏簇6确认位置下限
input double InpBadCluster6ConfirmMax = 999.0;  // 组合坏簇6确认位置上限
input double InpBadCluster6Mult = 1.0;       // 组合坏簇6仓位倍数(<=0过滤)
input string InpBadCluster6Signal = "";      // 组合坏簇6信号类型(all/ob/sweep/range)
input bool   InpBadClusterFilteredMonthlyStop = false; // 坏簇过滤信号后锁住本月新入场
input double InpBadClusterFilteredStopMinBalance = 0.0; // 坏簇过滤停手启用余额/峰值(0=始终启用)
input double InpStartupBadClusterMaxMonthStartBalance = 0.0; // 启动期坏簇仅在月初余额<=该值时启用(0=禁用)
input string InpStartupBadCluster1Hours = "";       // 启动期坏簇1小时CSV(空=禁用)
input double InpStartupBadCluster1RiskMin = 0.0;    // 启动期坏簇1风险下限
input double InpStartupBadCluster1RiskMax = 0.0;    // 启动期坏簇1风险上限(<=min=禁用风险条件)
input double InpStartupBadCluster1ConfirmMin = -999.0; // 启动期坏簇1确认位置下限
input double InpStartupBadCluster1ConfirmMax = 999.0;  // 启动期坏簇1确认位置上限
input double InpStartupBadCluster1Mult = 1.0;       // 启动期坏簇1仓位倍数(<=0过滤)
input string InpStartupBadCluster1Signal = "";      // 启动期坏簇1信号类型(all/ob/sweep/range)
input string InpStartupBadCluster2Hours = "";       // 启动期坏簇2小时CSV(空=禁用)
input double InpStartupBadCluster2RiskMin = 0.0;    // 启动期坏簇2风险下限
input double InpStartupBadCluster2RiskMax = 0.0;    // 启动期坏簇2风险上限(<=min=禁用风险条件)
input double InpStartupBadCluster2ConfirmMin = -999.0; // 启动期坏簇2确认位置下限
input double InpStartupBadCluster2ConfirmMax = 999.0;  // 启动期坏簇2确认位置上限
input double InpStartupBadCluster2Mult = 1.0;       // 启动期坏簇2仓位倍数(<=0过滤)
input string InpStartupBadCluster2Signal = "";      // 启动期坏簇2信号类型(all/ob/sweep/range)
input string InpStartupBadCluster3Hours = "";       // 启动期坏簇3小时CSV(空=禁用)
input double InpStartupBadCluster3RiskMin = 0.0;    // 启动期坏簇3风险下限
input double InpStartupBadCluster3RiskMax = 0.0;    // 启动期坏簇3风险上限(<=min=禁用风险条件)
input double InpStartupBadCluster3ConfirmMin = -999.0; // 启动期坏簇3确认位置下限
input double InpStartupBadCluster3ConfirmMax = 999.0;  // 启动期坏簇3确认位置上限
input double InpStartupBadCluster3Mult = 1.0;       // 启动期坏簇3仓位倍数(<=0过滤)
input string InpStartupBadCluster3Signal = "";      // 启动期坏簇3信号类型(all/ob/sweep/range)
input string InpStartupBadCluster4Hours = "";       // 启动期坏簇4小时CSV(空=禁用)
input double InpStartupBadCluster4RiskMin = 0.0;    // 启动期坏簇4风险下限
input double InpStartupBadCluster4RiskMax = 0.0;    // 启动期坏簇4风险上限(<=min=禁用风险条件)
input double InpStartupBadCluster4ConfirmMin = -999.0; // 启动期坏簇4确认位置下限
input double InpStartupBadCluster4ConfirmMax = 999.0;  // 启动期坏簇4确认位置上限
input double InpStartupBadCluster4Mult = 1.0;       // 启动期坏簇4仓位倍数(<=0过滤)
input string InpStartupBadCluster4Signal = "";      // 启动期坏簇4信号类型(all/ob/sweep/range)
input bool   InpEnableHTFNetPushFilter = false; // 启用HTF净推进仓位过滤
input int    InpHTFNetPushTF     = 15;       // HTF净推进周期(分钟)
input int    InpHTFNetPushBars   = 4;        // HTF净推进观察闭合K数
input double InpHTFNetPushMinATR = 0.50;     // 净推进阈值(ATR倍数,<=0禁用)
input double InpHTFNetPushAlignedMult = 1.0; // HTF同向净推进仓位倍数
input double InpHTFNetPushNeutralMult = 1.0; // HTF无明显净推进仓位倍数
input double InpHTFNetPushCounterMult = 1.0; // HTF反向净推进仓位倍数(<=0过滤)
input bool   InpEnableHTFPullback = false; // 启用HTF净推进后的回踩区信号
input bool   InpHTFPullbackOnly = false;   // 仅交易HTF回踩区信号
input int    InpHTFPullbackTF = 15;        // HTF回踩信号周期(分钟)
input int    InpHTFPullbackBars = 3;       // HTF净推进观察闭合K数
input double InpHTFPullbackMinATR = 0.80;  // HTF净推进阈值(ATR倍数)
input double InpHTFPullbackZoneATR = 0.35; // 回踩区高度(ATR倍数)
input double InpHTFPullbackOffsetATR = 0.10; // 推进收盘价到回踩区近端偏移(ATR倍数)
input double InpHTFPullbackTPMult = 1.0;   // TP=HTF回踩区高度倍数(0=DTP)
input double InpBuyMinStrength   = 0.0;      // 做多最低OB强度覆盖(0=用主参数)
input double InpSellMinStrength  = 0.0;      // 做空最低OB强度覆盖(0=用主参数)
input double InpBuyPosMult       = 1.0;      // 做多仓位乘数覆盖
input double InpSellPosMult      = 1.0;      // 做空仓位乘数覆盖
input double InpBuyBE_R          = 0.0;      // 做多BE触发覆盖(0=用主参数)
input double InpBuyBE_Lock       = 0.0;      // 做多BE锁定覆盖(0=用主参数)
input double InpSellBE_R         = 0.0;      // 做空BE触发覆盖(0=用主参数)
input double InpSellBE_Lock      = 0.0;      // 做空BE锁定覆盖(0=用主参数)
input double InpBuyDTPTriggerR   = 0.0;      // 做多DTP触发覆盖(0=用主参数)
input double InpBuyDTPRetrace    = 0.0;      // 做多DTP回撤覆盖(0=用主参数)
input double InpSellDTPTriggerR  = 0.0;      // 做空DTP触发覆盖(0=用主参数)
input double InpSellDTPRetrace   = 0.0;      // 做空DTP回撤覆盖(0=用主参数)
input bool   InpEnableStrongAddOn = false;   // 启用强势延续加仓
input double InpStrongAddOnTriggerR = 1.0;   // 首次加仓触发浮盈R
input double InpStrongAddOnStepR  = 1.0;     // 后续每次加仓递增R
input int    InpStrongAddOnMaxCount = 0;     // 每个源持仓最多加仓次数
input double InpStrongAddOnLotMult = 0.5;    // 加仓手数=源持仓当前手数*倍数
input double InpStrongAddOnRiskMult = 0.5;   // 加仓SL距离=源持仓初始risk*倍数
input double InpStrongAddOnMinSpreadRatio = 5.0; // 加仓最小risk/spread
input int    InpCloseRetryCooldownSec = 0;   // 交易请求失败后重试冷却秒数(0=不限制)
input int    InpMaxEntriesPerOB  = 1;        // 每个OB最多入场次数(1=默认一次)
input int    InpOBReentryCooldownMin = 0;    // 同一OB再次入场冷却分钟(0=不限制)
input double InpReentryPosMult = 1.0;        // 同一OB再次入场仓位倍数(<=0=过滤)
input double InpContinuationPosMult = 1.0;   // 延续OB仓位倍数(<=0=过滤)
input int    InpFilterContAgeMinBars = 0;    // 过滤延续OB最小年龄bars(0=禁用)
input int    InpFilterContAgeMaxBars = 0;    // 过滤延续OB最大年龄bars(0=禁用)
input bool   InpFilterContNonDeepOnly = false; // 仅过滤未深触的延续OB
input double InpFilterBuyNoH1MinPosMult = 0.0; // 做多非H1降权最小仓位乘数(0=禁用)
input double InpFilterBuyNoH1MaxPosMult = 0.0; // 做多非H1降权最大仓位乘数(0=禁用)
input double InpFilterBuyNoH1PosMult = 1.0; // 做多非H1高仓位降权倍数(<=0=过滤)

// ── 增强 ──────────────────────────────────────────────────────────────────
input double InpBoostIn1HOB      = 3.0;      // 1H级别OB加仓倍数
input bool   InpDSWeight         = true;     // 启用供需权重
input double InpDTAddonBoost     = 0.0;      // 二次触碰额外加仓

// ── K线设置 ────────────────────────────────────────────────────────────────
input int    InpBarTF            = 1;        // 工作周期(分钟: 1=M1, 5=M5)
input int    InpBars             = 5000;     // 加载K线数
input int    InpOBScanDepth      = 200;      // OB扫描深度(bars, 0=全量)

// ── 标识 ──────────────────────────────────────────────────────────────────
input string InpVersion          = "V96b";   // 策略版本标识
input int    InpMagicNumber      = 202605;   // EA Magic Number

// ── v11 单策略品种Profile覆盖 ─────────────────────────────────────────────
input bool   InpEnableBTCProfile = false;    // 启用BTC专属参数覆盖(默认关闭)
input string InpBTCProfileSymbol = "BTC";    // 触发BTC profile的品种名片段
input double InpBTCBouncePct = 0.25;         // BTC bounce确认比例
input int    InpBTCTimeoutMin = 120;         // BTC OB过期分钟
input double InpBTCMaxEntryOffsetR = 0.5;    // BTC最大入场偏移
input int    InpBTCBarTF = 5;                // BTC工作周期
input bool   InpBTCEnableLiquiditySweep = true; // BTC启用Sweep
input bool   InpBTCLiquiditySweepOnly = false;  // BTC仅Sweep
input int    InpBTCNoOBStartHour = -1;      // BTC禁止建OB开始小时(-1=禁用)
input int    InpBTCNoOBEndHour = -1;        // BTC禁止建OB结束小时(-1=禁用)
input double InpBTCSLBufferATR = 1.5;       // BTC SL ATR buffer
input double InpBTCOBHeightTPMult = 1.5;    // BTC OB高度TP
input int    InpBTCTimeExitBars = 80;       // BTC超时退出
input int    InpBTCSweepLookbackBars = 12;   // BTC Sweep lookback
input double InpBTCSweepMaxRangeATR = 2.50;  // BTC Sweep range/ATR
input double InpBTCSweepMinRangeSpreadMult = 4.0; // BTC Sweep range/spread
input double InpBTCSweepMinPenetrationATR = 0.05; // BTC Sweep penetration
input double InpBTCSweepMinWickPct = 45.0;   // BTC Sweep wick
input double InpBTCSweepTPMult = 1.0;        // BTC Sweep TP mult
input double InpBTCBreakevenR = 1.0;         // BTC BE触发
input double InpBTCBreakevenLockR = 0.2;     // BTC BE锁定
input double InpBTCDTPTriggerR = 3.0;        // BTC DTP触发
input double InpBTCDTPRetrace = 0.25;        // BTC DTP回撤
input double InpBTCFixedTPR = 0.0;           // BTC固定TP
input double InpBTCRiskPercent = 5.4;        // BTC风险%
input double InpBTCMaxPosMult = 300.0;       // BTC最大仓位乘数
input double InpBTCMaxLotSize = 9.0;         // BTC最大手数
input int    InpBTCMaxConcurrent = 8;        // BTC最大并发
input double InpBTCMinRiskSpreadRatio = 5.0; // BTC最小risk/spread
input double InpBTCSweepPosMult = 0.1;       // BTC Sweep仓位倍数
input double InpBTCSweepMaxLotSize = 0.01;   // BTC Sweep最大手数
input double InpBTCLowBalanceThreshold = 1000.0; // BTC低余额阈值
input double InpBTCLowBalancePosMult = 0.39; // BTC低余额仓位倍数
input double InpBTCLowBalanceMaxLotSize = 0.39; // BTC低余额最大手数
input double InpBTCEntryDepthPct = 0.67;     // BTC入场深度
input bool   InpBTCEntryDepthFilter = true;  // BTC深度硬过滤
input bool   InpBTCRequireDoubleTch = false; // BTC二触要求
input int    InpBTCMaxEntriesPerOB = 4;      // BTC每OB入场数
input int    InpBTCOBReentryCooldownMin = 30; // BTC同OB冷却
input int    InpBTCCooldownBars = 1;         // BTC开仓冷却bars
input double InpBTCContinuationPosMult = 1.0; // BTC延续OB倍数
input int    InpBTCFilterContAgeMinBars = 0; // BTC延续OB过滤最小年龄
input int    InpBTCFilterContAgeMaxBars = 0; // BTC延续OB过滤最大年龄
input bool   InpBTCFilterContNonDeepOnly = false; // BTC延续OB仅过滤非深位
input double InpBTCBoostIn1HOB = 2.0;        // BTC 1H OB倍数
input int    InpBTCLateBounceSec = 30;       // BTC晚确认秒数
input double InpBTCLateBounceMult = 0.6;     // BTC晚确认倍数
input double InpBTCBounceSweetMinPct = 0.26; // BTC bounce甜点下限
input double InpBTCBounceSweetMaxPct = 0.34; // BTC bounce甜点上限
input double InpBTCOutsideBounceSweetMult = 0.7; // BTC非甜点倍数
input double InpBTCBadRiskMin = 150.0;       // BTC弱风险下限
input double InpBTCBadRiskMax = 200.0;       // BTC弱风险上限
input double InpBTCBadRiskMult = 0.6;        // BTC弱风险倍数
input double InpBTCLargeRiskMin = 300.0;     // BTC大风险下限
input double InpBTCLargeRiskMult = 4.05;     // BTC大风险倍数
input string InpBTCNoEntryHours = "0,7,22,23"; // BTC禁止入场小时
input string InpBTCNoBuyHours = "";         // BTC禁止做多小时
input string InpBTCNoSellHours = "17";      // BTC禁止做空小时
input string InpBTCLowRiskHours = "17";     // BTC低仓位小时
input double InpBTCLowRiskHourMult = 0.35;  // BTC低仓位倍数
input string InpBTCHighRiskHours = "12,13,20,23"; // BTC高仓位小时
input double InpBTCHighRiskHourMult = 8.0;  // BTC高仓位倍数

// ── v9.8 势位态动 ────────────────────────────────────────────────────────
// 势(M15趋势)
input int    InpTrendLookback     = 80;       // M15趋势回溯(bars)
input int    InpSwingStrength     = 3;        // Swing确认强度(左右bars)

// 态(趋势/震荡)
input bool   InpEnableStateFilter = false;    // 启用态感知过滤
input double InpRangeBE_R         = 0.0;      // 震荡态保本R(0=用主BE)
input int    InpRangeTimeExit     = 999;      // 震荡态超时bars(999=不超时)
input double InpTrendBE_R         = 0.0;      // 趋势态保本R(0=用主BE)
input double InpTrendBE_Lock      = 0.0;      // 趋势态保本锁定R(0=用主Lock)
input double InpTrendDTPRetrace   = 0.0;      // 趋势态DTP回撤%(0=用主Retrace)

// 位(评分系统)
input bool   InpEnableScoring     = false;    // 启用评分系统
input int    InpProximityFilter   = 0;        // 0=评分加权, 1=硬过滤
input double InpProximityATR      = 1.0;      // 接近度阈值(ATR倍数)
input int    InpMinScore          = 0;        // 最低入场评分(0=不过滤)

// 动(动能衰减)
input bool   InpEnableDecayExit   = false;    // 启用动能衰减退出
input double InpDecayMinR         = 1.0;      // 衰减检测启动阈值(R)
input int    InpDecayBars         = 3;        // 二推不破连续bar数
input int    InpEngulfBodyPct     = 50;       // 吞没追随实体占比(%)
input bool   InpEnableMomentumRegime = false; // 启用强弱转换持仓管理
input double InpWeakExitMinR      = 1.0;      // 动能转弱退出最小R
input double InpWeakBodyShrinkPct = 0.80;     // K1-K3实体递减倍率
input double InpWeakWickBodyRatio = 2.0;      // 长影线/实体阈值
input int    InpStrongMomentumBars = 4;       // 强势连续K线数
input double InpStrongMinBodyGrowth = 1.0;    // 强势末根/首根实体倍率
input double InpStrongWeakReverseBodyPct = 25.0; // 强势中允许的微弱反向实体%
input double InpStrongMaxPullbackPct = 35.0;  // 强势最大回撤/推进%
input double InpStrongDTPRetraceMult = 1.50;  // 强势时DTP回撤放宽倍数

// 部分平仓
input double InpPartialCloseR      = 0.0;      // 部分平仓触发R(0=禁用)
input int    InpPartialClosePct    = 50;       // 部分平仓比例(%)
input double InpPartialPostLockR   = 0.0;      // 部分平仓后剩余仓锁定R(0=不提损)
input bool   InpPartialOnlyDeep    = false;    // 仅深位OB入场单启用部分平仓

// 入场引擎
input bool   InpEnableEntryEngine  = false;    // 启用入场状态机(false=直接入场)

// HTF目标位
input bool   InpEnableHTFTarget    = false;    // 大小周期同向时使用大周期目标位TP
input int    InpHTFTargetTF        = 15;       // 大周期目标周期(分钟)
input int    InpHTFTargetLookback  = 96;       // 目标位回溯bars
input int    InpHTFSwingStrength   = 2;        // swing确认强度
input double InpHTFMinTargetR      = 2.0;      // 目标位最小R
input double InpHTFMaxTargetR      = 6.0;      // 目标位最大R(0=不限制)
input double InpHTFMeasuredMoveR   = 2.0;      // 无有效前高低时的量度目标R(0=禁用)
input bool   InpHTFRequireAligned  = true;     // 仅大小周期同向启用目标
input double InpHTFPartialR        = 1.0;      // HTF目标单分批止盈R(0=不用专属分批)
input int    InpHTFPartialPct      = 50;       // HTF目标单分批比例
input bool   InpHTFSkipDTP         = false;    // HTF目标单跳过普通DTP
input bool   InpHTFSkipTrail       = false;    // HTF目标单跳过普通Trail
input double InpHTFDTPTriggerR     = 0.0;      // HTF目标单专属DTP触发R(0=用普通DTP)
input double InpHTFDTPRetrace      = 0.0;      // HTF目标单专属DTP回撤(0=用普通DTP)
input double InpHTFDTPPostPartialRetrace = 0.0; // HTF目标单分批后DTP回撤(0=沿用)

// 诊断
input bool   InpEnableExitDebug    = false;    // 打印出场诊断日志
input bool   InpEnableEntryDebug   = false;    // 打印入场诊断日志

input string InpHighBalanceNoEntryMonths = ""; // high month-start balance no-entry months CSV
input double InpHighBalanceNoEntryMinMonthStartBalance = 0.0; // enable when month-start balance >= value

double GetEffectiveEntryDepthPct()
{
   double pct = CfgEntryDepthPct();
   if(InpEntryDepthRelaxMinBalance > 0.0 &&
      pct > 0.0 && pct < 0.67 &&
      AccountInfoDouble(ACCOUNT_BALANCE) < InpEntryDepthRelaxMinBalance)
   {
      pct = 0.67;
   }

   if(pct <= 0.0) return 0.0;
   if(pct >= 1.0) return 1.0;
   return pct;
}

bool UseBTCProfile()
{
   return (InpEnableBTCProfile &&
      StringLen(InpBTCProfileSymbol) > 0 &&
      StringFind(_Symbol, InpBTCProfileSymbol) >= 0);
}

double CfgBouncePct() { return UseBTCProfile() ? InpBTCBouncePct : InpBouncePct; }
int CfgTimeoutMin() { return UseBTCProfile() ? InpBTCTimeoutMin : InpTimeoutMin; }
double CfgMaxEntryOffsetR() { return UseBTCProfile() ? InpBTCMaxEntryOffsetR : InpMaxEntryOffsetR; }
int CfgBarTF() { return UseBTCProfile() ? InpBTCBarTF : InpBarTF; }
bool CfgEnableLiquiditySweep() { return UseBTCProfile() ? InpBTCEnableLiquiditySweep : InpEnableLiquiditySweep; }
bool CfgLiquiditySweepOnly() { return UseBTCProfile() ? InpBTCLiquiditySweepOnly : InpLiquiditySweepOnly; }
int CfgNoOBStartHour() { return UseBTCProfile() ? InpBTCNoOBStartHour : InpNoOBStartHour; }
int CfgNoOBEndHour() { return UseBTCProfile() ? InpBTCNoOBEndHour : InpNoOBEndHour; }
double CfgSLBufferATR() { return UseBTCProfile() ? InpBTCSLBufferATR : InpSLBufferATR; }
double CfgOBHeightTPMult() { return UseBTCProfile() ? InpBTCOBHeightTPMult : InpOBHeightTPMult; }
int CfgTimeExitBars() { return UseBTCProfile() ? InpBTCTimeExitBars : InpTimeExitBars; }
int CfgSweepLookbackBars() { return UseBTCProfile() ? InpBTCSweepLookbackBars : InpSweepLookbackBars; }
double CfgSweepMaxRangeATR() { return UseBTCProfile() ? InpBTCSweepMaxRangeATR : InpSweepMaxRangeATR; }
double CfgSweepMinRangeSpreadMult() { return UseBTCProfile() ? InpBTCSweepMinRangeSpreadMult : InpSweepMinRangeSpreadMult; }
double CfgSweepMinPenetrationATR() { return UseBTCProfile() ? InpBTCSweepMinPenetrationATR : InpSweepMinPenetrationATR; }
double CfgSweepMinWickPct() { return UseBTCProfile() ? InpBTCSweepMinWickPct : InpSweepMinWickPct; }
double CfgSweepTPMult() { return UseBTCProfile() ? InpBTCSweepTPMult : InpSweepTPMult; }
double CfgBreakevenR() { return UseBTCProfile() ? InpBTCBreakevenR : InpBreakevenR; }
double CfgBreakevenLockR() { return UseBTCProfile() ? InpBTCBreakevenLockR : InpBreakevenLockR; }
double CfgDTPTriggerR() { return UseBTCProfile() ? InpBTCDTPTriggerR : InpDTPTriggerR; }
double CfgDTPRetrace() { return UseBTCProfile() ? InpBTCDTPRetrace : InpDTPRetrace; }
double CfgFixedTPR() { return UseBTCProfile() ? InpBTCFixedTPR : InpFixedTPR; }
double CfgRiskPercent() { return UseBTCProfile() ? InpBTCRiskPercent : InpRiskPercent; }
double CfgMaxPosMult() { return UseBTCProfile() ? InpBTCMaxPosMult : InpMaxPosMult; }
double CfgMaxLotSize() { return UseBTCProfile() ? InpBTCMaxLotSize : InpMaxLotSize; }
int CfgMaxConcurrent() { return UseBTCProfile() ? InpBTCMaxConcurrent : InpMaxConcurrent; }
double CfgMinRiskSpreadRatio() { return UseBTCProfile() ? InpBTCMinRiskSpreadRatio : InpMinRiskSpreadRatio; }
double CfgSweepPosMult() { return UseBTCProfile() ? InpBTCSweepPosMult : InpSweepPosMult; }
double CfgSweepMaxLotSize() { return UseBTCProfile() ? InpBTCSweepMaxLotSize : InpSweepMaxLotSize; }
double CfgLowBalanceThreshold() { return UseBTCProfile() ? InpBTCLowBalanceThreshold : InpLowBalanceThreshold; }
double CfgLowBalancePosMult() { return UseBTCProfile() ? InpBTCLowBalancePosMult : InpLowBalancePosMult; }
double CfgLowBalanceMaxLotSize() { return UseBTCProfile() ? InpBTCLowBalanceMaxLotSize : InpLowBalanceMaxLotSize; }
double CfgEntryDepthPct() { return UseBTCProfile() ? InpBTCEntryDepthPct : InpEntryDepthPct; }
bool CfgEntryDepthFilter() { return UseBTCProfile() ? InpBTCEntryDepthFilter : InpEntryDepthFilter; }
bool CfgRequireDoubleTch() { return UseBTCProfile() ? InpBTCRequireDoubleTch : InpRequireDoubleTch; }
int CfgMaxEntriesPerOB() { return UseBTCProfile() ? InpBTCMaxEntriesPerOB : InpMaxEntriesPerOB; }
int CfgOBReentryCooldownMin() { return UseBTCProfile() ? InpBTCOBReentryCooldownMin : InpOBReentryCooldownMin; }
int CfgCooldownBars() { return UseBTCProfile() ? InpBTCCooldownBars : InpCooldownBars; }
double CfgContinuationPosMult() { return UseBTCProfile() ? InpBTCContinuationPosMult : InpContinuationPosMult; }
int CfgFilterContAgeMinBars() { return UseBTCProfile() ? InpBTCFilterContAgeMinBars : InpFilterContAgeMinBars; }
int CfgFilterContAgeMaxBars() { return UseBTCProfile() ? InpBTCFilterContAgeMaxBars : InpFilterContAgeMaxBars; }
bool CfgFilterContNonDeepOnly() { return UseBTCProfile() ? InpBTCFilterContNonDeepOnly : InpFilterContNonDeepOnly; }
double CfgBoostIn1HOB() { return UseBTCProfile() ? InpBTCBoostIn1HOB : InpBoostIn1HOB; }
int CfgLateBounceSec() { return UseBTCProfile() ? InpBTCLateBounceSec : InpLateBounceSec; }
double CfgLateBounceMult() { return UseBTCProfile() ? InpBTCLateBounceMult : InpLateBounceMult; }
double CfgBounceSweetMinPct() { return UseBTCProfile() ? InpBTCBounceSweetMinPct : InpBounceSweetMinPct; }
double CfgBounceSweetMaxPct() { return UseBTCProfile() ? InpBTCBounceSweetMaxPct : InpBounceSweetMaxPct; }
double CfgOutsideBounceSweetMult() { return UseBTCProfile() ? InpBTCOutsideBounceSweetMult : InpOutsideBounceSweetMult; }
double CfgBadRiskMin() { return UseBTCProfile() ? InpBTCBadRiskMin : InpBadRiskMin; }
double CfgBadRiskMax() { return UseBTCProfile() ? InpBTCBadRiskMax : InpBadRiskMax; }
double CfgBadRiskMult() { return UseBTCProfile() ? InpBTCBadRiskMult : InpBadRiskMult; }
double CfgLargeRiskMin() { return UseBTCProfile() ? InpBTCLargeRiskMin : InpLargeRiskMin; }
double CfgLargeRiskMult() { return UseBTCProfile() ? InpBTCLargeRiskMult : InpLargeRiskMult; }
string CfgNoEntryHours() { return UseBTCProfile() ? InpBTCNoEntryHours : InpNoEntryHours; }
string CfgNoBuyHours() { return UseBTCProfile() ? InpBTCNoBuyHours : InpNoBuyHours; }
string CfgNoSellHours() { return UseBTCProfile() ? InpBTCNoSellHours : InpNoSellHours; }
string CfgLowRiskHours() { return UseBTCProfile() ? InpBTCLowRiskHours : InpLowRiskHours; }
double CfgLowRiskHourMult() { return UseBTCProfile() ? InpBTCLowRiskHourMult : InpLowRiskHourMult; }
string CfgHighRiskHours() { return UseBTCProfile() ? InpBTCHighRiskHours : InpHighRiskHours; }
double CfgHighRiskHourMult() { return UseBTCProfile() ? InpBTCHighRiskHourMult : InpHighRiskHourMult; }

#endif
