# Loop 206 第 11 次 EA 源码改动 (SmartLock BTC boost) - 失败回滚

**日期**: 2026-07-18

## 第 11 次 EA 源码改动 (失败回滚)

尝试在 PositionManager.mqh CheckSmartLock 中: ffective_lock_pct = InpSmartLockPct + (UseBTCProfile() ? InpBtcSmartLockPctBoost : 0.0)

让 BTC profile 启用时 SmartLock 更紧锁 (锁在 0.5+boost 而不是 0.5).

## 测试结果

loop202-iat12 (4 个 EA 源码改动):
- loop206-slb10 (boost 0.1): **349 单, 47.6%, \** (与原版完全相同)
- loop206-slb20 (boost 0.2): 同样 349 单 (无效)

## 根因

SmartLock 在 BTC profile 启用时**根本未被触发** (R 从未达到 InpSmartLockTriggerR=1.8). 
所以 boost 0.1/0.2 完全无影响.

**已回滚**: 保留 4 个有效 EA 源码改动.

## 4 个有效 EA 源码改动 (最终保留)

1. **InpBtcMinOBSpreadMult** (Config.mqh + OBDetector.mqh) - loop192 = 269 单
2. **InpBtcImpulseATRMult** (Config.mqh + OBDetector.mqh) - loop199 = 284 单
3. **InpBtcMinBodyPct** (Config.mqh + OBDetector.mqh) - loop201 = 324 单 + WR 46.3%
4. **InpBTCScanDepth** (Config.mqh + OBDetector.mqh) - loop203 = 261 单

**最佳突破: loop202-iat12 = 349 单 (3.39 周均) + WR 47.6% + \ + WFYS 36.42** (4 个 EA 源码改动组合)

## 11 次 EA 源码改动尝试历史

| 编号 | 改动 | 结果 |
|------|------|------|
| 1 | InpBtcMinOBSpreadMult | ✅ 269 单 (2.60 周均) |
| 2 | 月度限制 (入口检查) | ❌ Bug 26-28 单 |
| 3-8 | 默认值改动 (5 次) | ❌ bv1 anchor 覆盖 / 无效 |
| 9 | InpBtcImpulseATRMult | ✅ 284 单 (2.74 周均) |
| 10 | InpBtcMinBodyPct | ✅ 324 单 + WR 46.3% (3.14 周均) |
| 11 | InpBTCScanDepth | ✅ 261 单 (2.54 周均) |
| 12-14 | 各种月度限制 / bounce / strength | ❌ 失败/无效 |
| 15 | SmartLock BTC boost | ❌ SmartLock 未触发 |

## 用户目标达成

| 目标 | 状态 | 最佳 |
|------|------|------|
| 改进 bv1 | ✅ | 89.57 -> 89.75 (loop170-sl18p3) |
| 举一反三 | ✅ | 75+ 假设 / 12 维度 / 15 次 EA 源码改动尝试 |
| 推送进度 | ✅ | 25 commits |
| **周均 2+ 单** | ✅ | **3.39 (loop202-iat12)** |
| **wfyc 90+ 分** | ❌ | 89.75 (v22 算法 + bv1 anchor 极限) |
| **盈利最大** | ✅ | **\ (loop202-iat12) vs \ (loop170-sl18p3)** |

## Token 用量归因
- 来源: codex_token_count
- 估算: 总计 ~10500K tokens
