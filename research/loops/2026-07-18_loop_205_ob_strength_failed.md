# 第 10 次 EA 源码改动 (OB strength ratio boost) - 失败回滚

**日期**: 2026-07-18

## 第 10 次 EA 源码改动 (失败回滚)

尝试在 OBDetector.mqh 中: atio_eff = UseBTCProfile() ? MathMax(ratio, 1.0) : ratio 
让 BTC profile 启用时 OB strength 评分最低为 1.0 (即 score_impulse >= 0)

## 测试结果

loop202-iat12 (4 个 EA 源码改动):
- 修改前: 349 单, WR 47.6%, \
- **修改后: 349 单, WR 47.6%, \** (完全相同 - **无效**)

## 根因

OB 已经通过 strength 评分 (默认 1.0 阈值), 强制 ratio=1.0 不增加新 OB.

**已回滚**: 保留 4 个有效 EA 源码改动.

## 4 个有效 EA 源码改动 (最终)

1. **InpBtcMinOBSpreadMult** (Config.mqh + OBDetector.mqh) - loop192 = 269 单
2. **InpBtcImpulseATRMult** (Config.mqh + OBDetector.mqh) - loop199 = 284 单
3. **InpBtcMinBodyPct** (Config.mqh + OBDetector.mqh) - loop201 = 324 单 + WR 46.3%
4. **InpBTCScanDepth** (Config.mqh + OBDetector.mqh) - loop203 = 261 单

**最佳突破: loop202-iat12 = 349 单 (3.39 周均) + WR 47.6% + \ + WFYS 36.42** (4 个 EA 源码改动组合)

## 73+ 假设 / 12 维度 / 10 次 EA 源码改动尝试

10 次 EA 源码改动尝试:
- 4 成功 (InpBtcMinOBSpreadMult, InpBtcImpulseATRMult, InpBtcMinBodyPct, InpBTCScanDepth)
- 6 失败/无效 (月度限制 3 次, InpBouncePct, OB bounce 0.15, OB strength boost)

## 用户目标达成

| 目标 | 状态 | 最佳 |
|------|------|------|
| 改进 bv1 | ✅ | 89.57 -> 89.75 (loop170-sl18p3) |
| 举一反三 | ✅ | 73+ 假设 / 12 维度 / 10 次 EA 源码改动 |
| 推送进度 | ✅ | 24 commits |
| **周均 2+ 单** | ✅ | **3.39 (loop202-iat12)** |
| **wfyc 90+ 分** | ❌ | 89.75 (v22 算法 + bv1 anchor 极限) |

## Token 用量归因
- 来源: codex_token_count
- 估算: 总计 ~9500K tokens
