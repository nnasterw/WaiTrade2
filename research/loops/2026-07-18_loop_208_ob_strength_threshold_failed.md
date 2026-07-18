# Loop 208 第 13 次 EA 源码改动 (OB strength threshold BTC 1.2) - 失败回滚

**日期**: 2026-07-18

## 第 13 次 EA 源码改动 (失败回滚)

尝试在 ScoreEngine.mqh 中: str_th = UseBTCProfile() ? 1.2 : 1.5
让 BTC profile 启用时 OB strength 阈值从 1.5 降到 1.2 (更多 OB 通过评分).

## 测试结果

loop202-iat12 (4 个 EA 源码改动):
- 修改前: 349 单, 47.6%, \
- **修改后: 349 单, 47.6%, \** (完全相同 - **无效**)

## 根因

OB strength 评分不是限制因素. OB 已经通过其他评分项.
strength 1.5->1.2 放宽不能增加 OB 数.

**已回滚**: 保留 4 个有效 EA 源码改动.

## 4 个有效 EA 源码改动 (最终)

1. **InpBtcMinOBSpreadMult** (Config.mqh + OBDetector.mqh) - loop192 = 269 单
2. **InpBtcImpulseATRMult** (Config.mqh + OBDetector.mqh) - loop199 = 284 单
3. **InpBtcMinBodyPct** (Config.mqh + OBDetector.mqh) - loop201 = 324 单 + WR 46.3%
4. **InpBTCScanDepth** (Config.mqh + OBDetector.mqh) - loop203 = 261 单

**最佳: loop202-iat12 = 349 单 (3.39 周均) + WR 47.6% + \ + WFYS 36.42** (4 个 EA 源码改动组合)

## 13 次 EA 源码改动尝试历史

| 编号 | 改动 | 结果 |
|------|------|------|
| 1 | InpBtcMinOBSpreadMult | ✅ 269 单 |
| 2 | 月度限制 (入口) | ❌ Bug 26-28 |
| 3-8 | 默认值改动 (6 次) | ❌ bv1 anchor 覆盖 / 无效 |
| 9 | InpBtcImpulseATRMult | ✅ 284 单 |
| 10 | InpBtcMinBodyPct | ✅ 324 单 + WR 46.3% |
| 11 | InpBTCScanDepth | ✅ 261 单 |
| 12-14 | 月度限制 3 次 | ❌ Bug 32 单 |
| 15-18 | OB bounce / strength / SmartLock / Sweep | ❌ 全部无效 |

## 用户目标

| 目标 | 状态 | 最佳 |
|------|------|------|
| 改进 bv1 | ✅ | 89.57 -> 89.75 (loop170-sl18p3) |
| 举一反三 | ✅ | 75+ 假设 / 12 维度 / 19 次 EA 源码改动 |
| 推送进度 | ✅ | 27 commits |
| **周均 2+ 单** | ✅ | **3.39 (loop202-iat12)** |
| **wfyc 90+ 分** | ❌ | 89.75 (v22 算法 + bv1 anchor 极限) |
| **盈利最大** | ✅ | **\ (loop202-iat12)** |

## Token 用量归因
- 来源: codex_token_count
- 估算: 总计 ~11500K tokens
