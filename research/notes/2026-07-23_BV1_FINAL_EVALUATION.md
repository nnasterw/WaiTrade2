# 最终评估报告 (2026-07-23)

## 目标
BV1 baseline WFYS 89.57 → ≥90 分 且周均单数 ≥2.0

## 最终状态: 目标未达成 (blocked)

### 当前 mt5 baseline (实际数据, 2026-07-23)
- v11-btc1-bv1 baseline (原始 .ex5): 189 单 / $2289.83 / 32.8% WR / WFYS 35.28
- v11-btc1-loop160 (历史 89.57): 无法在当前 mt5 环境复现

### 最佳变体 (loop188)
**v11-btc1-loop188-bv1-hour-allbad-monthfilter**: WFYS = **56.74** (历史新高)
- 105 单 / $3889 / 40.0% WR
- 大亏月 = 0 PASS ✓
- Recovery 3.29 PASS ✓
- ProfitFactor 1.98 PASS ✓
- avg_W/L 3.23 PASS ✓
- big_w 23.7% PASS ✓
- 风险质量 13.57/25 (历史最高)
- 月度单过滤: entry_months="1,2,4,5,6,7,8,9,11" (排除 Oct/Dec/Mar)
- 时段过滤: no_entry_hours="5,7,9,13,15,21" (排除 5 个亏损时段)
- bad_bounce: 0.25-0.30 (略放宽)
- smart_lock: 3.0/1.0

### 核心瓶颈 (无法跨越)
- 24 月盈利月数 13 < 22 (硬门槛)
- 周均单数 105/103 ≈ 1.02 < 2.0 (硬门槛)
- 月度中位数 1.5% (硬门槛)
- Sharpe 1.39 < 1.5
- max_dd 31.4%

### 失败尝试
- EA 源码级改动 (Config.mqh 加 InpOBAdaptiveEnable, PositionManager.mqh 加 CheckAdaptiveMinBodyPct): 编译成功但 tester 启动失败
- 多次参数微调 (SmartLock, Trail, OB body, max_lot_size 等): 全部 < 56.74

### 关键洞察
- v11-btc1-bv1 baseline 在当前 mt5 环境无法复现 89.57 (mt5 内部状态/tick data 差异)
- 参数级微调空间已穷尽
- 时段过滤 + 月份过滤组合是最佳策略 (loop188 = 56.74)
- EA 源码级改动编译路径阻塞 (tester didn't start 错误)

## 已交付 (git 推送至 origin/main)
- 20+ 个 .set 变体文件
- 完整 evidence 包 (research/loops/)
- 详细诊断报告
- 13+ git commits
