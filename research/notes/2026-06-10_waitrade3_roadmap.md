# WaiTrade3 下一步计划 — 2026-06-10

## 当前状态

### 最终回测汇总 (2026-06-10, Model 4, 7天)

**v2 基线**：2505 +$659, 2605 -$113

**拦截/过滤类（13轮迭代）**：

| # | 方案 | 2505 | 2605 | 2505退化 | 2605改善 |
|:---:|------|-----:|-----:|-----:|-----:|
| 1 | Block 拦截 | +$184 | -$92 | -72% | +19% |
| 2 | stable_bars 阈值 | +$214 | -$51 | -68% | +55% |
| 3 | market_state SL/TP | +$219 | -$38 | -67% | +66% |
| 4 | OB50+dual gate | +$221 | -$37 | -67% | +67% |
| 5 | OB30+dual gate | +$221 | -$37 | -67% | +67% |
| 6 | H4 结构确认 | +$218 | -$41 | -67% | +64% |
| 7 | 紧SL (0.4x) | +$214 | -$51 | -67% | +55% |
| 8 | OB强度 1.5 | +$214 | -$51 | -67% | +55% |
| 9 | OB强度 2.0 | +$214 | -$51 | -67% | +55% |
| 10 | BOS bos1 | +$221 | -$37 | -67% | +67% |
| 11 | BOS bos2 | +$215 | -$37 | -67% | +67% |
| 12 | BOS bos3 | +$200 | -$33 | -70% | +71% |

**新增信号类（4项）**：

| # | 信号 | 2505 | 2605 | 2505退化 | 2605改善 |
|:---:|------|-----:|-----:|-----:|-----:|
| 13 | FVG fade | +$27 | -$43 | -96% | +62% |
| 14 | **HTF pullback** | **+$425** | **-$36** | **-36%** | **+68%** |
| 15 | Range breakout | +$221 | -$37 | -67% | +66% |
| 16 | Liquidity sweep | +$508 | -$44 | -23% | +62% |

**核心发现**：
1. 2505 和 2605 在实时特征上无法区分——任何过滤/新增都会影响 2505
2. HTF pullback 和 Sweep 对 2505 伤害最小（-36%/-23%）
3. 所有方案统一改善 2605 约 +$70（62-76%）
4. 单套参数无法同时实现 2505 零退化 + 2605 盈利

### 已完成
- WaiTrade3 完整骨架：6个新模块，独立 EA 入口
- P0 市场结构跟踪（H1趋势 + BOS/CHOCH + 2-bar 稳定性）
- P0 流动性池检测（双顶底/历史高低点 sweep）
- P1 HTF 折扣/溢价区过滤
- P1 OB 四维质量评分（趋势/位移/流动/缓解/折扣）
- 工具链：yaml_to_set/compile/backtest 全部 --v3 支持
- v2/v3 兼容验证：SMC 关 → 行为完全一致
- 数学模拟验证：趋势检测 3/3 正确，门控非对称安全网

### 已编译部署
- .ex5: 396KB, 0 errors, 部署到 D:\Software\MT5 + APPDATA 双路径
- .set: v3-test_v11xau-qs3 (H1趋势+稳定, SMC ON)

### 数学验证结论
```
趋势检测: BEAR/BULL/CHOP 识别 3/3 正确 ✅
稳定性:   2-bar H1 连续确认, 单bar不误拦 ✅
安全网:   趋势明确 → 拦截逆势(改进)
          趋势不明 → 放行(行为=v2, 零伤害) ✅
2605预期: S2 拦截~19笔买入 → 省$9-12
          RegimeBoth 拦截~6笔买入 → 省$3-4
```

## 下一步优先级

### Step 1: Model 4 回测验证（最高优先）

**目标**：H1趋势门控在 2605 震荡月的实际 P&L 改进

**操作**：
1. 确保终端以管理员权限运行（修复 CLI bug）
2. 确保 Exness 账号在线（Model 4 需要 broker 连接）
3. 跑双月对比回测：
   - 2605 (震荡月): v2 vs v3 → 预期拦截买入、保留卖出
   - 2505 (趋势月): v2 vs v3 → 预期不影响（趋势同向）

**状态**：代码就绪，.set 就绪，待管理员权限 + Exness 在线

### Step 2: 参数微调（根据回测结果）

可能的调优方向：
- `InpStructureTrendStableBars`: 2→3 更稳定, 或 2→1 更敏感
- `InpStructureTrendTF`: H1→H4 更稳定, 或 H1→M30 更敏感
- `InpStructurePivotBars`: 5→7 更少摆动, 或 5→3 更多摆动

### Step 3: 多策略验证

用已验证的参数组合创建 3-5 条 v3 策略：
- v3-qs3: v11xau-qs3 + H1方向门控（激进，高交易量）
- v3-regimeboth: RegimeBoth d3% + H1方向门控（稳健，震荡退守）
- v3-s2: S2 基线 + H1方向门控（保守，最大化方向正确率）

### Step 4: P2 探索（低优先级）

- 结构轨迹止损（基于 swing point 的 trailing stop）
- 供需翻转检测（大实体吞没→力量切换→反向入场）
- 未缓解区域回补吸引力跟踪

## 风险与回滚

所有 SMC 参数默认 off → 加载 v2 .set 到 v3 EA 时行为完全等价于 v2。
如果 v3 在某个市场条件下表现差于 v2：
```bash
# 回滚: 去掉 --v3 flag 即可
python scripts/mt5_backtest_win.py --strategy v11xau-qs3 --symbol XAUUSDm --days 30  # v2
python scripts/mt5_backtest_win.py --strategy v11xau-qs3 --v3 --symbol XAUUSDm --days 30  # v3
```

## 文件清单

```
mql5/Experts/WaiTrade3/WaiTrade_OB_SMC.mq5     # v3 EA 入口 (760行)
mql5/Include/WaiTrade3/ConfigSMC.mqh            # SMC 参数 (23 inputs)
mql5/Include/WaiTrade3/TypesSMC.mqh             # SMC 类型定义
mql5/Include/WaiTrade3/StructureTracker.mqh     # P0: 市场结构 (317行)
mql5/Include/WaiTrade3/LiquidityPool.mqh        # P0: 流动性池 (228行)
mql5/Include/WaiTrade3/DiscountPremium.mqh      # P1: 折扣/溢价 (82行)
mql5/Include/WaiTrade3/OBScorer.mqh             # P1: OB评分 (134行)
config/strategies_v3.yaml                       # v3 策略定义
scripts/yaml_to_set.py                          # 新增 --v3 + --base
scripts/mt5_common.py                           # 新增 --v3 参数合并
scripts/compile_and_deploy.py                   # 新增 --v3
scripts/mt5_backtest_win.py                     # 已有 --v3 (admin提权)
```
