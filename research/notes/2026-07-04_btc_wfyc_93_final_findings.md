# BTC WFYS 93 攻关 - 最终发现 (2026-07-04 15:30)

## 目标
通过代码级结构改造将 BTC 策略 WFYS 评分从 87.34 提升到 93+

## 最终结果
**87.34 → 87.34** (无提升)
- 添加 2 个代码改造 (CheckFastSL, CheckLossCut) 但均未能生效
- BE 参数调整导致策略 0 笔交易 (BE 1.0R 太早触发)

## 关键代码改造

### 1. CheckFastSL (Peak R 防护)
- 添加 InpBTCFastSLPeakR/Bars/ExitR 输入
- 新增 CheckFastSL 函数 (绕过 BE/Trail/DTP skip 条件)
- 在 OnTick 中调用
- **问题**: BTC SL 交易 peak R 2-3R+, FastSL 阈值无法在不杀中等赢单的情况下生效

### 2. CheckLossCut (无 peak 检查, 直接切损)
- 添加 InpBTCLossCutBars/R 输入
- 新增 CheckLossCut 函数 (无 peak 检查)
- 在 OnTick 中调用
- **问题**: 同样未生效. SL 交易价差太快 (8-23 min 跌 -1R), LossCut 阈值不切

### 3. BE 强化 (失败)
- btc_breakeven_r=1.0, btc_breakeven_lock_r=0.5
- **结果**: 0 笔交易 (BE 在 1.0R 触发, HTF 目标 3.2R 无法到达)

## 根本原因分析

BTC 策略 + HTF 目标系统的结构性限制:

1. **SL 交易 peak R 过高** (>= 2.0R)
   - 价格先上行到 2-3R, 然后回落到 -1R 触发 SL
   - FastSL 阈值需要 >= 3.0R 才能 catch, 但这会同时杀 2-3R 中等赢单

2. **BE 锁利时机敏感**
   - BE=1.3R 是 sweet spot (HTF 目标 3.2R)
   - BE=1.0R 触发太早, 杀交易
   - BE=2.0R 触发太晚, 保护不了

3. **OB 策略天然 big_win 比例 ~21-25%**
   - 大赢单 (3R+) 难以推到 50%
   - 中等赢单 (2-3R) 难以扩展到 3R+
   - 这是结构限制, 不是参数问题

## 完整统计
- 100+ 策略变体测试
- 2 个代码级改造 (CheckFastSL, CheckLossCut)
- 2 个 BE 尝试 (失败)
- 最佳: v11-btc1-trend111/112 (87.34)
- 距 93+ 仍差 5.66 分

## 93+ 所需根本性改变

1. **不同入场逻辑**: OB 策略 + 严格过滤 (volatility, HTF context, time)
2. **不同出场逻辑**: Wider SL, 智能 trailing, 分批止盈
3. **不同策略**: 完全重新设计 (非 OB-based)
4. **不同时间周期**: H1/H4 instead of M5
5. **不同品种**: 其他品种 (XAU, ETH) 可能更适合

## 当前代码状态
- mql5/Include/WaiTrade2/Config.mqh: 添加 InpBTCFastSL* 和 InpBTCLossCut* 输入
- mql5/Include/WaiTrade2/PositionManager.mqh: 添加 CheckFastSL 和 CheckLossCut 函数
- mql5/Experts/WaiTrade2/WaiTrade_OB.ex5: 编译 (509840 字节, 2026-07-04 15:13)

## 建议
- 87.34 是 BTC OB 策略 + HTF 目标的结构上限
- 93+ 需要策略方向调整, 非参数/单点代码优化
- 建议重新设计入场/出场逻辑, 或尝试其他策略基线
