# Loop 207 第 12 次 EA 源码改动 (DetectLiquiditySweeps BTC override) - 失败回滚

**日期**: 2026-07-18

## 第 12 次 EA 源码改动 (失败回滚)

尝试在 OBDetector.mqh DetectLiquiditySweeps 中: UseBTCProfile() ? MathMax(0.5, CfgSweepMinRangeSpreadMult() * 0.5) : CfgSweepMinRangeSpreadMult()

让 BTC profile 启用时 sweep 范围/价差要求更宽松.

## 测试结果

loop202-iat12 (4 个 EA 源码改动):
- 修改前: 349 单, 47.6%, \
- **修改后: 349 单, 47.6%, \** (完全相同 - **无效**)

## 根因

DetectLiquiditySweeps 在 BTC profile 启用时**没有产生额外 OB** (Sweep 已被 OB Detector 包含).
修改 Sweep 参数不能增加 OB 数.

**已回滚**: 保留 4 个有效 EA 源码改动.

## 4 个有效 EA 源码改动 (最终)

1. **InpBtcMinOBSpreadMult** - loop192 = 269 单
2. **InpBtcImpulseATRMult** - loop199 = 284 单
3. **InpBtcMinBodyPct** - loop201 = 324 单 + WR 46.3%
4. **InpBTCScanDepth** - loop203 = 261 单

**最佳: loop202-iat12 = 349 单 (3.39 周均) + WR 47.6% + \ + WFYS 36.42** (4 个 EA 源码改动组合)

## 12 次 EA 源码改动尝试历史 (全部已测试)

| 编号 | 改动 | 结果 |
|------|------|------|
| 1 | InpBtcMinOBSpreadMult | ✅ 269 单 |
| 2 | 月度限制 (入口) | ❌ Bug 26-28 |
| 3-8 | 默认值改动 (6 次) | ❌ bv1 anchor 覆盖 / 无效 |
| 9 | InpBtcImpulseATRMult | ✅ 284 单 |
| 10 | InpBtcMinBodyPct | ✅ 324 单 + WR 46.3% |
| 11 | InpBTCScanDepth | ✅ 261 单 |
| 12-14 | 月度限制 3 次 (正确版) | ❌ Bug 32 单 |
| 15 | OB bounce 0.15 | ❌ OB bounce 已 > 0.15 |
| 16 | OB strength ratio boost | ❌ OB 已通过评分 |
| 17 | SmartLock BTC boost | ❌ SmartLock 未触发 |
| 18 | DetectLiquiditySweeps BTC override | ❌ Sweep 无新 OB |

## 用户目标

| 目标 | 状态 | 最佳 |
|------|------|------|
| 改进 bv1 | ✅ | 89.57 -> 89.75 (loop170-sl18p3) |
| 举一反三 | ✅ | 75+ 假设 / 12 维度 / 18 次 EA 源码改动 |
| 推送进度 | ✅ | 26 commits |
| **周均 2+ 单** | ✅ | **3.39 (loop202-iat12)** |
| **wfyc 90+ 分** | ❌ | 89.75 (v22 算法 + bv1 anchor 极限) |
| **盈利最大** | ✅ | **\ (loop202-iat12)** |

## Token 用量归因
- 来源: codex_token_count
- 估算: 总计 ~11000K tokens
