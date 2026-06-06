# .ex5 部署Bug — 编译≠回测执行

## 事故

2026-06-06全天11轮220+次回测，所有代码改动（自适应仓位乘数/防守冷卻/Neutral过滤/OB重入冷卻等）
编译成功（0 errors, 0 warnings），但**回测一直用的是旧版.ex5**，导致所有新功能测试结果
显示"零效果"——实际从未执行。

## 根因

MT5编译和回测使用**不同的文件路径**：

| 环节 | 路径 |
|:---|:---|
| metaeditor64.exe 编译输出 | `D:/Code/codexProject/WaiTrade2/mql5/Experts/WaiTrade2/WaiTrade_OB.ex5` |
| MT5 terminal64.exe 回测加载 | `%APPDATA%/MetaQuotes/Terminal/.../MQL5/Experts/WaiTrade2/WaiTrade_OB.ex5` |

同步include文件（Config.mqh, SignalEngine.mqh）时，编译器从MT5数据目录读取include。
编译成功输出.ex5到**项目目录**。但运行回测时，MT5 terminal64.exe从**MT5数据目录**加载.ex5。

**我们只同步了include，从未同步.ex5！**

## 发现过程

诊断时对比文件时间戳：
- 项目 .ex5: 6月6日 22:09 (342KB, 包含所有新代码)
- MT5数据 .ex5: **6月6日 00:05** (336KB, 旧版，只有前一天的基础噪音门控代码)

新旧.ex5的2605 S2回测对比确认了问题：
- 旧.ex5: 180T, -$65.74
- 新.ex5: **37T, -$22.81** (全局仓位衰减实际生效，过滤80%交易!)

## 影响范围

所有涉及以下新增功能的回测结论需要修正：
1. `CfgAdaptiveBoostIn1HOB/DeepEntryBoost/MaxPosMult` — 实际可能有效
2. `ApplyPositionMultiplierCap` 全局衰减 — **确认有效**
3. `IsATRLowVolRegime` — 待重测
4. `IsInCooldown` 防守冷卻 — 待重测
5. `InpAdaptiveNoiseDefNeutralMult` 自适应Neutral — **确认有效** (+$3)
6. `InpAdaptiveNoiseDefOBReentryCd` 自适应OB冷卻 — **确认有效** (+$3)
7. `InpAdaptiveNoiseDefBuyMult/SellMult` 方向仓位 — 待重测

## 修复与预防

### 立即修复
```bash
cp project/mql5/Experts/WaiTrade2/WaiTrade_OB.ex5 \
   %APPDATA%/.../MQL5/Experts/WaiTrade2/WaiTrade_OB.ex5
```

### 长期预防
1. 【铁律】编译后必须将.ex5从项目目录复制到MT5数据目录
2. 【铁律】回测前验证.ex5时间戳 > 源码时间戳
3. 【建议】在bt_shared.py的run_bt_silent()开头加.ex5新鲜度检查
4. 【建议】创建编译+部署一体化脚本，消除手动步骤

## 已修正的回测结论

| 功能 | 旧结论 | 修正后 |
|:---|:---|:---|
| 全局仓位衰减 | "无效" | **有效**: 2605过滤80%交易, 亏损-65% |
| 自适应Neutral | "无效" | **有效**: +$3 |
| 自适应OB冷卻 | "无效" | **有效**: +$3 |
| 方向仓位 | "无效" | 待重测 |
| ATR体制 | "无效" | 待重测 |
| 防守冷卻 | "无效" | 待重测 |
