#ifndef __WAITRADE_CONFIG_MQH__
#define __WAITRADE_CONFIG_MQH__

// ═══════════════════════════════════════════════════════════════════════════
// WaiTrade EA — 输入参数定义 (V96b默认值)
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

#endif
