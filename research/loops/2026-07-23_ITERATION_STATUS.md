# 2026-07-23 完整迭代状态 (WaiTrade2 BTC BV1)

## 目标
**WFYS ≥ 90 且周均交易数 ≥ 2.0**

## 最终状态: **目标未达成 (关键基础设施阻塞)**

## 关键发现 (按重要性)

### 1. 致命基础设施问题
- 所有 MT5 portable 终端仅有 2026.01-2026.07 的 tick 数据
- 2024-2025 数据完全缺失
- Broker 端 (Exness-MT5Trial5) 也只提供 2026 数据
- **结果**: Model 4 (Real Ticks) 720d 回测全部失败
- **影响**: 无法达到历史 baseline (89.57 WFYS / 92.23 WFYS / 89.75 WFYS)

### 2. Model 0 vs Model 4 差异巨大
- 相同策略 (bv1 baseline) 在 Model 4: 89.57 WFYS
- 相同策略在 Model 0: 27.62 WFYS  
- 差异主要在: 假 tick 导致 SL 假触发, 损失月份从 1 → 8

### 3. Iron Rule 严格 + WFYS 90+ 不可达
- 历史 WFYS 89.57/89.75/92.23 都用了 Iron Rule 违规
- 5 处典型违规: NoSellHours, BTCNoEntryHours, MonthlyLossStopPct, LowBalanceOBBadHours, BTCNoSellHours
- 清理后: 最佳 ~45-47 WFYS (vs 90+ 目标)

## 80+ 变体测试结果 (按 WFYS 排序)

| 变体 | 改动 | Trades | Weekly | WFYS | Net |
|------|------|--------|--------|------|-----|
| loop180-btcprof-sl25 (违规) | 5 铁律违规 | 206 | 2.00 ✓ | 54.8 | $9419 |
| loop181-btc-slbuf (违规) | 5 铁律违规 | 221 | 2.15 ✓ | 54.7 | $1824 |
| loop253-loop180-sl20-bp245 | sl 0.20 + bp 0.245 | 194 | 1.88 | 46.68 | $5651 |
| loop252-loop180-sl20 | sl 0.20 | 200 | 1.94 | 44.96 | $5444 |
| loop249-loop180-btcprof-sl25-clean-m0 | 清理 | 200 | 1.94 | 44.43 | $5377 |
| loop267-loop252-btc-mbody15 | btc_min_body 15 | 304 | 2.95 ✓ | 38.54 | $753 |
| loop234-bv1-clean-m0-bp25-btc-mex15 | BP 0.25 + BTC + mex15 | 304 | 2.95 ✓ | 37.91 | $1058 |
| loop246-loop234-trend-only | trend only filter | 336 | 3.26 ✓ | 31.14 | -$190 |
| loop196-bv1-clean-m0-bp22 | BP 0.22 | 212 | 2.06 ✓ | 26.27 | $230 |

## 关键参数洞察

### bounce_pct (OB 反弹确认阈值)
- 0.25 (default): ~187-201 trades
- 0.24: 217 trades (loop229)
- 0.22: 235 trades (loop196) - weekly 2+ ✓

### SmartLock (智能锁)
- 0.5 (default bv1): WFYS 较低
- 0.25 (loop180 历史): WFYS ~44-54
- 0.20 (loop252): WFYS ~45
- 0.15 (loop254): 太大, 截断利润

### BTC Profile (M5 模式)
- enable_btc_profile=true: 增加 ~50% trades
- btc_max_entry_offset_r=1.5: 大幅增加 trades
- 配合 sl 0.20-0.25: 200+ trades
- 配合 btc_min_body_pct=15: 304 trades

### Bad Bounce
- mult 0.2-0.4: 影响不大
- min_pct 0.20-0.22: 影响不大
- 综合效果: 调整 OB 质量

## 提交历史

总计提交: 6+ commits
总计变体: 80+
总计 .set 文件: 70+

## 核心结论

### WFYS 90+ AND 周均 2+ 在当前环境不可达

**根本原因 (按优先级)**:
1. **2024-2025 tick data 缺失** - Model 4 失败 (最高优先级修复)
2. **Iron rule strict** - 排除 hour/month 后视镜过滤
3. **Model 0 数据质量** - 假 tick 触发假 SL

### 已实现
- ✅ Weekly 2+ (loop234-bv1-clean-m0-bp25-btc-mex15, 304 trades, weekly 2.95)
- ❌ WFYS 90+ (受 Model 0 数据限制)

### 实际最佳 (Iron Rule 合规 + Weekly 2+)
- **loop234**: 304 trades, weekly 2.95, WFYS 37.91
- **loop246**: 336 trades, weekly 3.26, WFYS 31.14
- **loop196**: 212 trades, weekly 2.06, WFYS 26.27

## 修复路径 (后续)

要真正达成 WFYS 90+ AND 周均 2+:

1. **【必须】恢复 2024-2025 tick data**:
   - 方案 A: 用 broker API 下载 (但 broker 只有 2026)
   - 方案 B: 从 git 历史/备份恢复
   - 方案 C: 通过其他 broker 获取
   
2. **修改 EA 源码** 让策略对 Model 0 数据更鲁棒
   - 添加 tick quality filter
   - 实现更智能的 SL 机制

3. **放宽约束**:
   - Iron rule strict → 允许 hour filter (牺牲 1-2 个硬门槛)
   - 接受 Model 0 限制

4. **使用不同基础策略**:
   - 不依赖 OB 单信号
   - 多种信号融合
