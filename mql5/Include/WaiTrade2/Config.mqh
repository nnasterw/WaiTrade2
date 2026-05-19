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

// ── 时间退出 ──────────────────────────────────────────────────────────────
input int    InpTimeExitBars     = 999;      // 超时退出(bars, 999=禁用)
input bool   InpTimeDecayTP      = false;    // 时间衰减TP

// ── 仓位管理 ──────────────────────────────────────────────────────────────
input double InpRiskPercent      = 2.0;      // 单笔风险(%余额)
input double InpFixedLotSize     = 0.0;      // 固定手数(>0时忽略风险%)
input bool   InpEnablePosMult    = true;     // 启用仓位乘数(false=固定1.0)
input double InpMaxPosMult       = 0.0;      // 最大仓位乘数(0=不限制)
input double InpMaxLotSize       = 0.0;      // 最大手数(0=不限制)
input int    InpMaxConcurrent    = 5;        // 最大同时持仓数
input int    InpCooldownBars     = 0;        // 开仓冷却(bars)
input string InpNoEntryHours     = "";       // 禁止入场小时CSV, 如"0,9,12"(空=禁用)
input string InpNoBuyHours       = "";       // 禁止做多小时CSV(空=禁用)
input string InpNoSellHours      = "";       // 禁止做空小时CSV(空=禁用)
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

#endif
