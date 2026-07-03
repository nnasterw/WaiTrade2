# WaiTrade3 开发状态 — 2026.06.10

## 一、项目背景

WaiTrade3 是基于 WaiTrade2 的 SMC/ICT 增强版，新增三大原语的第三环（方向识别/流动性池/折扣区）。

**设计原则**：WaiTrade3 = WaiTrade2 超集。所有 SMC 功能默认关闭，加载 v2 .set 时行为完全一致。

## 二、架构设计

### 物理隔离

```
mql5/
├── Experts/WaiTrade2/          ← v2 原版，一字节不改
├── Experts/WaiTrade3/          ← v3 EA 入口
├── Include/WaiTrade2/          ← v2 .mqh 16个（改动1个: RangeDetector.mqh 修复）
└── Include/WaiTrade3/          ← v3 新增 7个 .mqh
    ├── ConfigSMC.mqh           — 22个 SMC 输入参数（全部默认 false/0）
    ├── TypesSMC.mqh            — SMCSwingPoint / LiquidityPool / SMCZoneData
    ├── StructureTracker.mqh    — BOS/CHOCH 趋势状态机 + HTF 趋势计算
    ├── LiquidityPool.mqh       — 双顶/双底/历史高低点 sweep
    ├── DiscountPremium.mqh     — HTF 折扣/溢价区
    └── OBScorer.mqh            — 四维评分（趋势/位移/流动/缓解/折扣）
```

### 无复制共享

OBDetector.mqh / SignalEngine.mqh / PositionManager.mqh / EntryEngine.mqh 等大模块直接 `#include <WaiTrade2/xxx.mqh>`，v3 不需要复制这 ~3000 行代码。

## 三、完成清单

### ✅ 编译部署

| 项目 | 状态 | 详情 |
|------|------|------|
| 编译 | ✅ 0 errors | v2+v3+PortfolioSetup+ClearGuard 全部通过 |
| .ex5 部署 | ✅ | 项目目录 + MT5 数据目录 |
| 回测 CLI 修复 | ✅ | 移除了误加的 `/portable` flag |

### ✅ 工具链扩展

| 脚本 | 改动 | 用法 |
|------|------|------|
| `mt5_common.py` | 合并加载 v2+v3 yaml；`--v3` 策略继承 _base | `--v3` 时策略参数自动继承 v2+d |
| `yaml_to_set.py` | 已有 `--v3 --base` | `--v3 strategy --base v2_strategy → Presets/v3/` |
| `compile_and_deploy.py` | 新增 `--v3` | `--v3` 编译并部署 v3 EA |

### ✅ SMC 模块（P0）

| 模块 | 功能 | 验证 |
|------|------|------|
| StructureTracker | 3~5-bar pivot → HH/HL/LH/LL → BOS/CHOCH → 趋势状态机 | ✅ 日志输出趋势变化 |
| StructureTracker HTF | 支持配置 M15/H1 独立趋势计算 | ✅ `InpStructureTrendTF=15/60` |
| LiquidityPool | 双顶/底 + 历史高低点 sweep | ✅ 模块已集成 |
| 方向门控 | `PassSMCDirectionGate()` 拦截逆势入场 | ✅ 验证正确拦截 |

### ✅ SMC 模块（P1）

| 模块 | 功能 | 验证 |
|------|------|------|
| DiscountPremium | HTF 折扣/溢价区位置过滤 | ✅ 乘数计算 |
| OBScorer | 四维评分 0-100 | ✅ 评分函数 |

### ✅ 兼容性验证

| 场景 | v2 | v3 (SMC 全关) | v3 (门控开) |
|------|----|--------------|------------|
| 回测 30天 | 62笔, +$74.16 | **62笔, +$74.16** ✅ 完全一致 | 0笔（全逆势拦截） |

## 四、方向门控分析

### 工作原理

```
OnTick → RegisterChannelMonitors（EntryEngine路径）
  → OB 状态过滤器
  → market_state 过滤器
  → SMC 方向门控（新增）
      → trend=CHOP/UNKNOWN → 允许
      → trend=BULLISH + direction=BUY → 允许
      → trend=BULLISH + direction=SELL → 拦截
      → trend=BEARISH + direction=BUY → 拦截
      → trend=BEARISH + direction=SELL → 允许
  → spread/risk 过滤器
  → score 过滤器
  → AddEntryMonitor → UpdateEntryMonitors → ExecuteSignal
```

### 验证结果

2026.04 月份（30 天回测）：
- v2 产生 62 笔交易，其中 **全部为买入逆势交易**
- v3 门控拦截了全部 62 笔（因为该月为空头趋势主导）
- 门控逻辑正确，但该月无符合方向的卖出 OB

### 已知局限

| 问题 | 影响 | 状态 |
|------|------|------|
| M15 趋势每 15-30 分钟翻转 | 门控不稳定 | 🔧 需加大 TF |
| H1 趋势尚未系统测试 | 可能更稳定 | 🔧 待测 |
| 无趋势强度阈值 | 微弱趋势也拦截 | 🔧 待实现 |

## 五、待完成

### P0（高优）

| 任务 | 工作量 | 说明 |
|------|--------|------|
| 方向门控调优 | 1h | 加大 trend_tf 到 H1 + 趋势强度阈值 (`InpStructureBlockMinStrength`) |
| 双月回测验证 | 2h | v3 vs v2 对比 2505（趋势月）和 2605（震荡月） |
| 改进效果量化 | 1h | 验证方向门控对买/卖方向的改进（原分析卖出 100% 正确） |

### P1（中优）

| 任务 | 工作量 | 说明 |
|------|--------|------|
| v3 策略模板 | 1h | 定义 3~5 条 v3 策略（不同市场模式的 SMC 配置） |
| liquidity_pool 激活验证 | 1h | 流动性池加持后交易质量 |
| OBScorer 入场过滤 | 1h | 评分 <60 的 OB 拦截效果 |

### P2（低优）

| 任务 | 工作量 | 说明 |
|------|--------|------|
| 结构轨迹止损 | 2h | swing point 级别 trail |
| check_strategy_consistency --v3 | 0.5h | 扩展工具链 |

## 六、技术债务

1. **RangeDetector.mqh 已修复**：`CalcATR(symbol, tf, 14, rates, count)` → `CalcATR(rates, count, 14)`（v2 已有 bug，阻塞 v3 编译）
2. **`/portable` 已移除**：`mt5_backtest_win.py` 中移除，D:盘终端安装版不需要

## 七、建议迭代顺序

```
Step 1: 方向门控调优（~2h）
  ├ 加大 trend_tf → H1 (60min)
  ├ 添加趋势强度阈值 (InpStructureBlockMinStrength)
  └ 验证 2505 + 2605

Step 2: 双月对比回测（~1h）
  ├ v2 基线：2505 / 2605
  ├ v3 门控开：2505 / 2605
  └ 量化方向改进效果

Step 3: 定义 v3 策略集（~1h）
  ├ v3_struct_ctrend — M3 + 方向门控（主要）
  ├ v3_struct_osc — M3 + 门控 + 流动池（震荡配置）
  └ v3_full — 全功能
```
