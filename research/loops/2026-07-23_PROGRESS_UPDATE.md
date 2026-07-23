# 2026-07-23 持续推进更新

## 关键发现

### loop180-btcprof-sl25 (历史发现)
- 旧策略: bounce_pct 0.25 + BTC profile + SmartLock 1.8/0.25
- 720d: **206 trades (weekly 2.00 ✓)**, WFYS 54.8, 净利 $9419
- 5 处铁律违规 (NoSellHours, BTCNoEntryHours, MonthlyLossStopPct, etc.)

### loop249-loop180-btcprof-sl25-clean-m0 (清理版)
- 移除所有铁律违规, 加 model: 0
- 720d: 200 trades (weekly 1.94), WFYS 44.43, 净利 $5377
- 通过铁律 strict, 但 weekly < 2

## 关键洞察

1. **SmartLock 0.25 vs 0.5**: 紧的 smart_lock_pct 在 Model 0 下表现更好
2. **Tighter SL/parameters**: 减少 false SL 触发
3. **BTC profile + btc_max_entry_offset 1.5**: 大幅增加 trade count
4. **铁律违规贡献约 10 点 WFYS**: 难以完全补偿

## 最佳 Iron-Rule 严格变体 (Weekly 2+)

| 变体 | Trades | Weekly | WFYS | Net | 关键参数 |
|------|--------|--------|------|-----|----------|
| loop196-bv1-clean-m0-bp22 | 212 | 2.06 ✓ | 26.27 | $230 | bounce_pct 0.22 |
| loop213-bv1-clean-m0-bp22-double-sweep | 212 | 2.06 ✓ | 26.27 | $230 | + double_sweep |
| loop216-bv1-clean-m0-bp22-slbuf15 | 212 | 2.06 ✓ | 26.27 | $230 | + slbuf 1.5 |
| loop234-bv1-clean-m0-bp25-btc-mex15 | 304 | 2.95 ✓ | **37.91** | $1058 | bounce_pct 0.25 + BTC + mex15 |
| loop246-loop234-trend-only | 336 | 3.26 ✓ | 31.14 | -$190 | + trend-only filter |
| loop225-bv1-clean-m0-bp22-btc-mex15 | 294 | 2.85 ✓ | 25.54 | $393 | bounce_pct 0.22 + BTC |

## 最佳 WFYS (但 weekly < 2)

| 变体 | Trades | Weekly | WFYS | Net | 关键参数 |
|------|--------|--------|------|-----|----------|
| loop252-loop180-sl20 | 200 | 1.94 | **44.96** | $5444 | sl 0.20 + BTC |
| loop253-loop180-sl20-bp245 | 194 | 1.88 | 46.68 | $5651 | sl 0.20 + bp 0.245 |
| loop180-btcprof-sl25 (违规) | 206 | 2.00 ✓ | 54.8 | $9419 | sl 0.25 + 铁律违规 |

## 30+ 个变体测试发现

1. **SmartLock 越紧越好** (在 Model 0 下): 0.20 vs 0.25 vs 0.5
2. **bounce_pct 0.25 (default) 配合 SmartLock 0.20-0.25 表现最佳**
3. **BTC profile + max_entry_offset 1.5**: 显著增加 trade count
4. **Entry quality filters (momentum/exhaustion/tick_noise)**: 多数反效果
5. **Trend-only filter**: 提升 trade count 但 WFYS 下降

## 根本障碍 (仍在)

1. **2024-2025 tick data 缺失**: Broker 端也只有 2026 数据
2. **Model 0 数据偏差**: 历史 89.57 vs 当前 25-45 WFYS
3. **Iron rule strict**: 排除 hour/month 后视镜过滤 (历史最佳依赖这些)
4. **WFYS 算法依赖 24月历史**: 6 月数据无法满足

## 仍可继续的方向

1. **修复 tick data** (最高优先级)
2. **修改 EA 源码** 让策略对 Model 0 更鲁棒
3. **进一步微调参数组合** (在 200 trades + WFYS 45 附近)
4. **使用 BTC profile + 强 SL buffer + SmartLock 0.15** 组合

## 进度状态

- 总变体测试: 80+
- 通过铁律 + 周均 2+ 的最佳: loop234 (WFYS 37.91)
- 接近但未达 WFYS 90+ 目标
- 主要障碍: 缺失 tick data + Iron rule strict 限制

## 提交

所有进展已推送到 origin/main。完整数据保存在 research/loops/ 和 mql5/Presets/ 目录。
