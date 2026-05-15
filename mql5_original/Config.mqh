//+------------------------------------------------------------------+
//| Config.mqh — 策略参数定义 (所有版本共用)                            |
//+------------------------------------------------------------------+
#ifndef __WAITRADE_CONFIG_MQH__
#define __WAITRADE_CONFIG_MQH__

// === 入场参数 ===
input group "=== 入场 ==="
input double InpBouncePct        = 0.30;  // Bounce确认阈值 (OB高度的%)
input int    InpTimeoutMin        = 90;    // Bounce等待超时(分钟)
input double InpMaxEntryOffsetR   = 1.0;   // 最大入场偏移(R)
input bool   InpRequireDoubleTch  = false; // 需要二推不破
input int    InpDoubleTchWindowMin= 90;    // 二推时间窗口(分钟)

// === OB过滤 ===
input group "=== OB过滤 ==="
input double InpMinOBSpreadMult   = 3.0;   // 最小OB高度(spread倍数)
input double InpMinRiskSpreadRatio= 5.0;   // 最小risk/spread比
input double InpMinAbsRiskUSD     = 0.30;  // 最小绝对risk(USD)
input bool   InpConsolidateOB     = true;  // 合并同一OB多级信号

// === 止损 ===
input group "=== 止损 ==="
input double InpSLBufferATR       = 0.10;  // SL = OB底部 - N×ATR

// === Trailing ===
input group "=== Trailing ==="
input double InpBreakevenR        = 0.5;   // 保本触发R
input double InpBreakevenLockR    = 0.1;   // 保本锁定R
input double InpTrail1TriggerR    = 1.5;   // Trailing Level 1 触发
input double InpTrail1LockR       = 0.3;   // Trailing Level 1 锁定
input double InpTrail2TriggerR    = 3.0;   // Trailing Level 2 触发
input double InpTrail2LockMult    = 0.65;  // Trailing Level 2 锁定(peak×, 0=用LockR)
input double InpTrail2LockR       = 0.0;   // Trailing Level 2 固定锁定R(LockMult=0时生效)
input double InpTrail3TriggerR    = 0.0;   // Trailing Level 3 触发(0=禁用)
input double InpTrail3LockR       = 0.0;   // Trailing Level 3 固定锁定R
input double InpTrail3LockMult    = 0.0;   // Trailing Level 3 锁定(peak×, 0=用LockR)

// === 动态止盈 ===
input group "=== 动态止盈 ==="
input double InpDTPTriggerR       = 2.0;   // DTP触发R (999=禁用)
input double InpDTPRetrace        = 0.35;  // DTP回撤比例
input bool   InpAdaptiveDTP       = true;  // 高R时缩小回撤比例

// === 时间出场 ===
input group "=== 时间出场 ==="
input int    InpTimeExitBars      = 12;    // 最大持仓(bars)
input bool   InpTimeDecayTP       = true;  // 时间衰减止盈

// === 仓位管理 ===
input group "=== 仓位管理 ==="
input double InpRiskPercent       = 2.0;   // 每笔风险(%)
input int    InpMaxConcurrent     = 5;     // 最大并发持仓
input int    InpCooldownBars      = 0;     // 冷却期(bars)
input double InpBoostIn1HOB       = 3.0;   // 1H OB区域仓位倍数
input bool   InpDSWeight          = true;  // ds动能加权
input double InpDTAddonBoost      = 2.0;   // 二推加仓倍数(0=禁用)

// === 数据 ===
input group "=== 数据 ==="
input ENUM_TIMEFRAMES InpBarTF    = PERIOD_M1; // 信号K线周期
input int    InpBars              = 5000;  // 回看K线数

// === 版本标记 ===
input group "=== 版本 ==="
input string InpVersion           = "v95c"; // 版本标签(仅显示用)

#endif
