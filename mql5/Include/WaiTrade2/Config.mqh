#ifndef __WAITRADE_CONFIG_MQH__
#define __WAITRADE_CONFIG_MQH__

// ═══════════════════════════════════════════════════════════════════════════
// WaiTrade2 EA — 输入参数定义 (V96b默认值)
// ═══════════════════════════════════════════════════════════════════════════

// ── OB检测 ──────────────────────────────────────────────────────────────────
input double InpBouncePct        = 0.30;     // OB确认反弹幅度(%)
input int    InpTimeoutMin       = 60;       // OB过期时间(分钟)
input double InpMaxEntryOffsetR  = 1.5;      // 最大入场偏移(R倍数)
input bool   InpRequireDoubleTch = true;     // 要求二次触碰
input int    InpDoubleTchWindowMin = 60;     // 二次触碰窗口(分钟)
input double InpMinOBSpreadMult  = 2.0;      // 最小OB宽度(点差倍数)
input double InpMinRiskSpreadRatio = 3.0;    // 最小风险/点差比
input double InpMinAbsRiskUSD    = 0.0;      // 最小绝对风险(USD)
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
input double InpFixedTPR         = 0.0;      // 固定止盈(R, 0=DTP模式)

// ── 时间退出 ──────────────────────────────────────────────────────────────
input int    InpTimeExitBars     = 999;      // 超时退出(bars, 999=禁用)
input bool   InpTimeDecayTP      = false;    // 时间衰减TP

// ── 仓位管理 ──────────────────────────────────────────────────────────────
input double InpRiskPercent      = 2.0;      // 单笔风险(%余额)
input double InpFixedLotSize     = 0.0;      // 固定手数(>0时忽略风险%)
input bool   InpEnablePosMult    = true;     // 启用仓位乘数(false=固定1.0)
input int    InpMaxConcurrent    = 5;        // 最大同时持仓数
input int    InpCooldownBars     = 0;        // 开仓冷却(bars)

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

// 部分平仓
input double InpPartialCloseR      = 0.0;      // 部分平仓触发R(0=禁用)
input int    InpPartialClosePct    = 50;       // 部分平仓比例(%)

// 入场引擎
input bool   InpEnableEntryEngine  = false;    // 启用入场状态机(false=直接入场)

// 诊断
input bool   InpEnableExitDebug    = false;    // 打印出场诊断日志

#endif
