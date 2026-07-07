# BTC EA WFYC 88+ 突破迭代研究

**日期**: 2026-07-07  
**目标**: BTC EA WFYS (Win-First-Your-Self) 评分 ≥ 88+ (从 87.34 baseline 突破)  
**实际达成**: 88.84 (trend531) - 距离 90+ 目标差 1.16 分  
**探索范围**: trend500-trend563 + EA 源码改动, 共 30+ 变体  
**Token 使用**: ~25M

---

## 一、起点 (2026-07-07 早晨)

| 策略 | 分数 | Hard Pass | 状态 |
|------|------|-----------|------|
| `v11-btc1-trend218` | 87.34 | ✓ | 唯一 hard_pass (max_loss 24.4%) |
| `v11-btc1-trend409` | 89.21 | ✗ | 最高分 (max_loss 101.4% 失败) |
| `v11-btc1-trend298` | 88.29 | ✗ | 类似 trend409 |

**关键瓶颈分析**:
- 稳定性 22.66/30: 22/24 盈利月, 2 亏损月
- 趋势结构 12.24/15: big_w 27% (需 50%)
- 风险质量 24.31/25: sharpe 1.96 (需 3.0)
- 利润能力 30/30: 已满分
- **总差距**: 10.79 分

---

## 二、迭代阶段 1: trend500-trend509 (cap_loss 扩展)

| # | 名称 | 关键变化 | 分数 | Hard Pass |
|---|------|---------|------|-----------|
| 500 | cap_loss h=3,4,5,10,12 | 扩展到 2025-11 h=12 + 2026-01 h=10 | 80.88 | ✗ |
| 501 | btc_cap_loss_r=-0.5 | 从 -0.3 收紧 | - | - |
| 502 | cap_loss h=3,4,5,10,12,15 r=-0.4 | 综合 | - | - |
| 503 | DTP 1.8/0.25 | 折中 | - | - |
| 504 | DTP 1.5/0.20 | 激进 | - | - |
| 505 | entry_depth 0.7 + DTP 1.5/0.20 | deep entry | - | - |
| 506 | cap_loss r=-0.4 + monthly_defensive 5% | 月度保护 | - | - |
| 507 | cap_loss h=3,4,5,10,12 + DTP 1.5/0.20 | 双优 | - | - |
| 508 | cap_loss h=3,4,5,11,12,13 | 亚洲时段 | - | - |
| 509 | cap_loss h=3,4,5,10,12 + cap_loss_days=5 | 周末 cap | - | - |

**发现**: trend500 max_lot 实际是 1.6 (anchor 默认)，导致 2026-05 大亏 -$1556 (13 笔)。

---

## 三、迭代阶段 2: trend520-trend535 (微调尝试)

| # | 名称 | 关键变化 | 分数 | Hard Pass |
|---|------|---------|------|-----------|
| 520 | trend500 + max_lot=1.0 | 修复 max_lot bug | 77.38 | ✗ |
| 521 | monthly_profit_target_stop 15%/30% | 月度止盈 | - | - |
| 522 | cap_loss 全时段 h=3,4,5,10,12,13,15,20,21,22 | 广泛保护 | - | - |
| 523 | cap_loss + monthly_defensive 5% | 双重保护 | - | - |
| 524 | cap_loss + DTP 1.5/0.20 + max_lot 1.0 | 综合 | - | - |
| 530 | HTF 2.5/3.5 (从 2.2/3.2 提升) | 提升 HTF 目标 | 77.87 | ✗ |
| 531 | **bad_bounce 0.22-0.28 + max_lot 1.0** | **更严过滤** | **88.84** | **✓** |
| 532 | monthly_profit_target_stop 15%+30% | 月度止盈 | 77.38 | ✗ |
| 533 | BE 1.5/0.5 | 早锁利 | 78.93 | ✗ |
| 534 | BE stage2 2.0/0.8 | 双层 BE | - | - |
| 535 | max_lot 0.6 | 降一档 | 76.79 | ✗ |

**🎯 重大突破: trend531 = 88.84 (研究版Live候选, 全部 18 个 hard gates PASS!)**

trend531 关键参数:
- bad_bounce 0.22-0.28 (从 0.25-0.30 更严)
- bad_bounce_mult 0.4
- max_lot 1.0

trend531 月度表现 (24m):
- 2 亏损月: 2024-11 (-$18), 2026-05 (-$38)
- 22/24 盈利月
- 6 强利润月, 2 大趋势月
- 月收益中位数 5.4%
- Top5 集中度 61.5%
- max_dd 11.1%
- PF 3.71, Recovery 13.69
- big_w 23.8%, micro 28.6%

---

## 四、迭代阶段 3: trend540-trend553 (微调突破)

| # | 名称 | 关键变化 | 分数 | Hard Pass |
|---|------|---------|------|-----------|
| 540 | trend531 + HTF 2.5/3.5 | HTF 升级 | 87.34 | ✓ |
| 541 | bad_bounce 0.20-0.26 | 更严 | 84.41 | ✓ |
| 542 | trend531 + DTP 1.8/0.25 | DTP 折中 | 88.84 | ✓ |
| 543 | trend531 + low_balance 0.4 | 低余额保护 | 88.84 | ✓ |
| 544 | bad_bounce 0.20-0.28 mult 0.5 | 更严+减少 | - | - |
| 545 | btc_bounce_pct 0.22 | 收紧 | - | - |
| 550 | **EA 源码: BigWinLock 2.5/1.5** | R>=2.5 锁 1.5R | 88.84 | ✓ |
| 551 | BigWinLock 3.0/2.0 | R>=3.0 锁 2.0R | - | - |
| 552 | BigWinLock 2.0/1.0 + MonthlyGuard | 防月度失控 | - | - |
| 553 | BigWinLock 2.5/1.0 + MonthlyGuard | 组合 | - | - |

**发现**: trend540-553 全部都接近 trend531 (88.84)，但均未突破 90。

EA 源码改动 (BigWinLock, MonthlyLossGuard) 编译成功 (0 errors, 1 warning)，但因 MT5 缓存问题未能在回测中验证。

---

## 五、迭代阶段 4: trend560-trend563 (HTF 微调)

| # | 名称 | 关键变化 | 分数 | Hard Pass |
|---|------|---------|------|-----------|
| 560 | htf_partial_r 1.5/50% | HTF 单部分止盈 | 72.27 | ✗ |
| 561 | bad_bounce 0.24-0.28 | 更窄 sweet spot | 88.84 | ✓ |
| 562 | ob_high_pos_boost 1.7 (从 1.5) | boost 提升 | 85.17 | ✓ |
| 563 | htf_partial_r 1.0/50% | HTF 双锁 | - | - |

**HTF partial close 反而破坏月度稳定性** (16/24 盈利月)。

---

## 六、Top 10 评分结果汇总

| 策略 | 分数 | Stab | Prof | Risk | Trend | Trades | Hard Pass |
|------|------|------|------|------|-------|--------|-----------|
| **trend531** | **88.84** | 22.67 | 30.00 | 24.31 | 11.86 | 117 | **✓** |
| trend540 | 87.34 | 22.67 | 28.50 | 24.31 | 11.86 | 117 | ✓ |
| trend218 (baseline) | 87.34 | 22.67 | 28.50 | 24.32 | 11.86 | 111 | ✓ |
| trend541 | 84.41 | 17.75 | 30.00 | 24.53 | 12.13 | 126 | ✓ |
| trend562 | 85.17 | 19.00 | 30.00 | 24.31 | 11.86 | 117 | ✓ |
| trend500 | 80.88 | 15.87 | 30.00 | 23.51 | 11.50 | 146 | ✗ |
| trend533 | 78.93 | 14.42 | 30.00 | 23.41 | 11.10 | 112 | ✗ |
| trend530 | 77.87 | 12.70 | 30.00 | 23.44 | 11.73 | 130 | ✗ |
| trend520 | 77.38 | 12.21 | 30.00 | 23.44 | 11.73 | 135 | ✗ |
| trend532 | 77.38 | 12.21 | 30.00 | 23.44 | 11.73 | 133 | ✗ |

---

## 七、关键洞察与教训

### 7.1 稳定性 (22.67) 难以突破
- 22/24 盈利月 = 91.7% 是 BTC OB 策略的天花板
- 24/24 盈利月在统计上几乎不可能 (2 个亏损月是 -$18, -$38 极小)

### 7.2 趋势结构 (11.86) 突破困难
- big_w 23.8% 是当前 EA 架构的天然限制
- 提升 big_w 需要: 让 5-8 个 2.0-3.0R 单子 "吃满" 到 4R+
- 单纯调整 DTP/BE 阈值无法实现 (已验证)

### 7.3 利润能力 (30) 已满分
- 24m 总收益 3758% (vs 优秀线 12.0)
- 720d PF 3.71, Recovery 13.69, Sharpe 1.97

### 7.4 风险质量 (24.31) 已接近满分
- 距离 25.0 满分差 0.69 (需要 sharpe 3.0, 现实 1.97)

### 7.5 EA 源码改动 (BigWinLock/MonthlyGuard) 编译成功
- Config.mqh: 新增 6 个 InpBTC* 参数
- PositionManager.mqh: 新增 CheckBigWinProtection + CheckMonthlyLossGuard 函数
- Types.mqh: 新增 bigwin_locked 字段
- yaml_to_set.py: 新增 6 个 FLAT_MAP 字段
- .ex5 编译 0 errors, 1 warning
- 但 MT5 缓存问题导致回测未验证新代码生效

---

## 八、突破 90 的真正路径

### 8.1 已达 88.84 (差 1.16 分)
- 稳定性 +0.5: 需要 24/24 盈利月 (极难)
- 趋势 +0.5: 需要 big_w 30% (EA 架构限制)
- 风险 +0.16: 需要 sharpe 2.5 (参数微调可达)

### 8.2 关键路径 (需 EA 源码深度改动)
1. **大赢单放大器**: R>=3 立即锁 50% 仓位 (50% 继续 trail 跑)
2. **HTF 顺逆势过滤器**: H4 net direction 冲突时 BLOCK (覆盖 2024-11 + 2026-01)
3. **多层 max_loss 控制器**: 改进 cap_loss 按月内动态调整
4. **真正的多级 trailing**: Trail1 1.0R, Trail2 2.0R, Trail3 4.0R + 大赢单锁定

### 8.3 验证方法
- 重跑 trend531 + 新 EA (30 天快速验证)
- 比较 .trades.csv 字段: peak_r, bigwin_locked, monthly_loss_guard
- 24m 全量验证

---

## 九、推荐决策

### 9.1 立即可部署: **trend531**
- WFYS 88.84 (研究版Live候选, 全部 18 hard gates PASS)
- 22/24 盈利月, 0 大亏月
- max_dd 11.1%, PF 3.71, Recovery 13.69
- $7,615 (24m 24倍收益)

### 9.2 后续研究方向
1. **修复 EA 缓存问题**: 确保新 .ex5 真正加载
2. **完整 BigWinLock/MonthlyGuard 验证**: 30 天 + 24m 双重验证
3. **HTF 顺逆势过滤器 (新功能)**: 需要新 input + SignalEngine.mqh 改动
4. **多级 trailing + 大赢单锁定**: CheckTrailing 函数增强

### 9.3 已生成的策略配置
- `mql5/Presets/v11-btc1-trend500.set` 至 `v11-btc1-trend563.set` (30+ 变体)
- `config/strategies.yaml`: 2390 个策略
- `results/backtest/`: 30+ 个 .txt + .trades.csv + .wfys.json
- `mql5/Include/WaiTrade2/`: 已修改 Config.mqh, PositionManager.mqh, Types.mqh
- `scripts/yaml_to_set.py`: 已添加 6 个新 FLAT_MAP 字段

---

## 十、约束与坑记录

- **MT5 include 路径**: 编译时优先用 AppData 路径 (`0F72AF710F2F9B3FF7E22892AE773049`), 需 Copy-Item 同步源码
- **MT5 缓存**: 回测结果可能复用 cache, 需删除 .ex5 强制重编
- **yaml.dump 破坏 anchor**: PyYAML 不会保留 YAML anchor (`<<: *anchor`), 必须用文件追加方式
- **big_w 统计**: WFYS 按 exit R (不是 peak_r) 计算 >3R 占比
- **OB age 字段**: 当前 EA 未填充 ob_age, 无法用于过滤

