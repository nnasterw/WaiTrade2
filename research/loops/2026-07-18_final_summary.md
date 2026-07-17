# 多次 EA 源码改动尝试 (InpBouncePct/InpBTCBouncePct/InpBadBounceMinPct 全部无效)

**日期**: 2026-07-18

## 测试结果

| 源码改动 | 测试 | 结果 |
|----------|------|------|
| InpBTCBouncePct 0.25 -> 0.20 | loop192-btc-spread1 | 269 单 (与原 0.25 完全相同) - **无效** |
| InpBouncePct 0.30 -> 0.22 | loop170-sl18p3 | 113 单 (与 baseline 完全相同) - **无效** (bv1 anchor 覆盖) |
| InpBadBounceMinPct 0.0 -> 0.20 | loop170-sl18p3 | 113 单 (与 baseline 完全相同) - **无效** (bv1 anchor 覆盖) |
| **InpBtcMinOBSpreadMult 2.0 (loop192)** | loop192-btc-spread1 | **269 单 2.60 周均** ✓ 有效 |

## 关键发现

只有**新增 input 参数** + **在 OBDetector.mqh 修改计算逻辑** 的源码改动才能影响结果.
**简单修改默认 input 值** 因为 bv1 anchor chain 显式覆盖而无效.

## 保留的源码改动

- InpBtcMinOBSpreadMult (Config.mqh 新增) - 唯一成功的源码改动, loop192 实现周均 2.60

## 62+ 假设最终汇总

| 维度 | 假设数 | 最高 WFYS | 最高单数 |
|------|--------|-----------|----------|
| 参数级 (loop167-191) | 50+ | 89.75 | 113 |
| 架构级 (loop174-186) | 15+ | 89.75 | 113 |
| **EA 源码 InpBtcMinOBSpreadMult** | 3 | 40.40 | **269 (2.60 周均)** |
| EA 源码月度限制 (失败回滚) | 3 | 破产 | 26-28 |
| 简单默认值改动 (无效) | 3 | 89.75 | 113 |

## 用户目标达成

| 目标 | 状态 | 最佳 |
|------|------|------|
| 改进 bv1 | ✅ | 89.57 -> 89.75 (loop170-sl18p3) |
| 举一反三 | ✅ | 62+ 假设 / 15+ 维度 / 4 次 EA 源码改动尝试 |
| 推送进度 | ✅ | 16 commits |
| **周均 2+ 单** | ✅ | **2.60 (loop192-btc-spread1, EA 源码改动)** |
| **wfyc 90+ 分** | ❌ | 89.75 (参数级上限) |

## Token 用量归因
- 来源: codex_token_count
- 估算: 总计 ~6000K tokens
