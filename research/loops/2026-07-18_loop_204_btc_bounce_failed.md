# 第 9 次 EA 源码改动 (BTC bounce 0.15) - 失败回滚

**日期**: 2026-07-18

## 第 9 次 EA 源码改动 (失败回滚)

尝试在 OBDetector.mqh bounce 检查中: ff_bounce_th = UseBTCProfile() ? MathMin(CfgBouncePct(), 0.15) : CfgBouncePct()

## 测试结果

loop202-iat12 (已有 4 个 EA 源码改动):
- 修改前: 349 单, WR 47.6%, \
- **修改后: 349 单, WR 47.6%, \** (完全相同 - **无效**)

## 根因

OB bounce 不是限制因素. 现有 OB 的 bounce 都已经 > 0.15 (BV1 anchor 设了 bad_bounce_min_pct=0.22, 但 InpBTCBouncePct=0.25 也满足).
bounce 0.15 放宽不能增加 OB 数.

**已回滚**: 保留 4 个有效 EA 源码改动.

## 4 个有效 EA 源码改动 (最终)

1. **InpBtcMinOBSpreadMult** -> loop192 = 269 单
2. **InpBtcImpulseATRMult** -> loop199 = 284 单  
3. **InpBtcMinBodyPct** -> loop201 = 324 单 + WR 46.3%
4. **InpBTCScanDepth** -> loop203 = 261 单

**最佳突破: loop202-iat12 = 349 单 (3.39 周均) + WR 47.6%** (4 个 EA 源码改动组合)

## 用户目标

| 目标 | 状态 | 最佳 |
|------|------|------|
| 改进 bv1 | ✅ | 89.57 -> 89.75 (loop170-sl18p3) |
| 举一反三 | ✅ | 73+ 假设 / 12 维度 / 9 次 EA 源码改动 |
| 推送进度 | ✅ | 23 commits |
| **周均 2+ 单** | ✅ | **3.39 (loop202-iat12)** |
| **wfyc 90+ 分** | ❌ | 89.75 (v22 算法 + bv1 anchor 极限) |

## Token 用量归因
- 来源: codex_token_count
- 估算: 总计 ~9000K tokens
