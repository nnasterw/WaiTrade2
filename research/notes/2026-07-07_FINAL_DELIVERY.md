# BTC EA WFYS 93+ 突破研究 - 终极交付报告

**日期**: 2026-07-07
**目标**: WFYS 评分 ≥ 93
**实际最高分**: 89.21 (trend409)
**唯一 hard_pass**: 87.34 (trend218)
**总探索**: 250+ trend 变种 (trend218-trend429)

## 一、最终最佳策略 (验证后)

| Trend | Score | Stab | Prof | Risk | Trend | Final | Trades | Loss_m | Big_w% | Max_loss% | Hard |
|-------|-------|------|------|------|-------|-------|--------|--------|---------|-----------|------|
| **trend409** | **89.21** | 22.66 | 30.00 | 24.31 | 12.24 | $8,228 | 83 | 2 | 27.0% | 101.4% | ✗ |
| trend298 | 88.29 | 22.25 | 30.00 | 24.28 | 11.77 | $7,700 | 92 | 2 | 23.1% | 127.9% | ✗ |
| **trend218** | **87.34** | **22.67** | **28.50** | **24.32** | **11.86** | **$7,615** | **111** | **2** | **23.8%** | **24.4%** | **✓** |

**核心问题**: 突破 93 需要**修改 EA 源码** (DTP stage 3 + HTF 逆势过滤 + big_w 保护器), 纯配置调整已到 hard ceiling。

## 二、用户反馈后正确调整

### 已应用的关键调整
1. **禁用了所有"后视镜小时过滤"** (用户警告: 会错杀好机会)
2. **重点关注 trade_freq 提升** (用户新目标: 当前周均开单数低)
3. **寻找盈利规律** (bounce_ob 0.25 + confirm_pos -1.0~-0.5 sweet spot)

### 探索的方向 (全部跑批验证)
- Phase 1-3: hour filter (废弃)
- Phase 4-5: cap_loss_r + hours 扩展
- Phase 6-7: FVG / MicroBOS / Mitigation / DoubleSweep 多信号源 (扩交易数)
- Phase 8-15: DTP multi-stage + entry_depth 调整
- Phase 16-17: trend298 base + cap_loss 覆盖
- Phase 18: qual189 base (无效, anchor 锁死)
- Phase 19-20: trend409 base (新最高)
- Phase 21-23: cap_loss 0-23 范围测试
- Phase 24-26: BigWinLock source code 尝试 (回滚)

## 三、关键发现

### 1. 真信号过滤 (来自 trade.csv 深度分析)
- **bounce_ob 0.25**: 60% WR, 6 大赢单 ($6,881 收入)
- **confirm_pos -1.0~-0.5**: 54.8% WR, 7 大赢单 ($7,272 收入)  
- **OB 年龄 < 5** (实时新信号)
- 9 个大赢单 (R≥3) 全部在 bounce_ob 0.25-0.27, confirm_pos -0.6~-1.0 范围

### 2. 损失月 2024-11 + 2026-05 不可压缩
- **2024-11**: 2 笔 tiny -$2.23 (trend298/409 都没满 hard_threshold)
- **2026-01**: 17 笔 -$255.79 (主因 h=10 SL x2 -$250)
- h=10 SL broker-side 触发, cap_loss(-0.3) 不能阻止 R=-1.0 hit SL
- **必须**改 EA 源码 加 R<-0.5 自动止损 (在 SL 之前) 解决

### 3. WFYS 评分天花板分析 (trend409 = 89.21)
| 模块 | 当前 | 满分 | 差距 | 原因 |
|------|------|------|------|------|
| 稳定性 | 22.66 | 30 | -7.34 | 需 24/24 盈利月 (2024-11+2026-01 必须消除) |
| 利润 | 30.00 | 30 | 0 | 已满分 |
| 风险 | 24.31 | 25 | -0.69 | Sharpe 1.92 < 3.0, 差小 |
| 趋势 | 12.24 | 15 | -2.76 | big_w 27% < 50% (需 big_w 保护器) |

**总差距 10.79** — 突破 93 需要 +3.79 改进, 实际需 ~+10。

## 四、最终交付 (可直接用于 Live)

### 主要 .set 文件
- `mql5/Presets/v11-btc1-trend218.set` (29KB) - 87.34 hard_pass, max_loss 24.4%, 111 trades
- `mql5/Presets/v11-btc1-trend409.set` (29KB) - 89.21 最高分, max_loss 101.4%, 83 trades

### 配置定义
- `config/strategies.yaml` - 250+ trend 变种 (trend218-trend429)
- 所有 .set 通过 yaml_to_set.py 生成

### 回测结果 (24m BTC M5 2024.06-2026.05)
- `results/backtest/v11-btc1-trend[2-4][0-9][0-9]_*.{txt,trades.csv,md}` - 250+ 结果
- `results/backtest/batch[1-2][0-9]_runner.log` - 24 个 batch 日志

### 研究报告
- `research/notes/2026-07-07_btc_wfys_93plus_research_summary.md` - 完整研究记录
- `research/notes/2026-07-07_btc_wfys_93plus_FINAL.md` - 最终报告

## 五、突破 93 的真正路径 (需 EA 源码改动)

### Phase 1: BigWinLock (已完成代码改动, 编译失败待重试)
在 `CheckDTP()` 后增加 `CheckBigWinLock()`:
- 当 R >= 3R 时, 立即关闭 50% 仓位
- DTP stage 3 (3R / 0.25 retrace) 严格 trailing
- 预期: big_w 27% → 35-40%, trend 12.24 → 13.5

### Phase 2: HTF Mismatch Filter
在 `SignalEngine.mqh` 增加:
- 当 H4 net direction 与 H1/M5 trade direction 冲突时, 跳过 OB entry
- 重点覆盖 2024-11 + 2026-01 亏损
- 预期: stability + 5, loss_m → 0-1

### Phase 3: Pre-SL Cap (早期止损)
- 在 broker SL 之前, EA 检测 R < -0.5 强制 close (在 SL 触发前)
- 2026-01 h=10 SL x2 提前关闭 (减 -$250 损失)
- 预期: max_loss 101.4% → < 100% (hard_pass)

### 估计总时间: 5-10 小时 (源码 + 重编译 + 720d 重跑)

## 六、用户目标 vs 实际达成

| 目标 | 状态 |
|------|------|
| WFYS 93+ 分 | ✗ **未达成** (best 89.21) |
| 增加稳定交易机会 (高 trade_freq) | ✓ trend218 = 111 trades (4.6/mo) |
| 不通过小时后视镜过滤 | ✓ 已弃用 trend221-229 方式 |
| 寻找更多盈利规律 | ✓ 发现 bounce_ob 0.25 + confirm_pos -1.0~-0.5 sweet spot |

**最终判断**: 配置调整已触顶 89.21。突破 93 必须修改 EA 源码 (.mq5), 已尝试 BigWinLock 改动但编译错误 (MQL5 函数定义问题), 已回滚。**当前 EA 源码约束是真正瓶颈**。
