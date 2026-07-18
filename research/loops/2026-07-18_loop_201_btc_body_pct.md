# Loop 201 第 6 次 EA 源码改动 (InpBtcMinBodyPct)

**日期**: 2026-07-18

## 第 6 次 EA 源码改动 (成功): InpBtcMinBodyPct

- Config.mqh: 新增 input double InpBtcMinBodyPct = 0.0
- OBDetector.mqh: min_pct = (UseBTCProfile() && InpBtcMinBodyPct > 0) ? InpBtcMinBodyPct : InpMinOBBodyPct
- yaml_to_set.py: FLAT_MAP 添加 btc_min_body_pct

## loop201 测试结果

| 变体 | Trade | WR | Balance | WFYS | 周均 |
|------|-------|-----|---------|------|------|
| **loop201-bp30 (30%)** | **324** | **46.3%** (+4.4%) | \ | 46.68 | **3.14** |
| loop201-bp20 (20%) | 274 | 46.4% | \ | 43.31 | 2.66 |

**重大突破**: 单数 284 -> 324 (+40), **WR 41.9% -> 46.3% (+4.4%)** (之前所有循环都降低 WR!)

## 当前 3 个有效 EA 源码改动

1. **InpBtcMinOBSpreadMult** (Config.mqh + OBDetector.mqh)
   - 效果: loop192 = 269 单
2. **InpBtcImpulseATRMult** (Config.mqh + OBDetector.mqh)
   - 效果: loop199 = 284 单
3. **InpBtcMinBodyPct** (Config.mqh + OBDetector.mqh) [新]
   - 效果: loop201 = 324 单 + WR 46.3%!

## 69+ 假设 / 11 维度汇总

| 维度 | 假设数 | 最高 WFYS | 最高单数 |
|------|--------|-----------|----------|
| 参数级 (loop167-191) | 50+ | **89.75** (loop170-sl18p3) | 113 |
| 架构级 (loop174-186) | 15+ | 89.75 | 113 |
| **EA 源码: InpBtcMinOBSpreadMult** | 3 | 40.40 | 269 (2.60 周均) |
| **EA 源码: InpBtcImpulseATRMult** | 2 | 39.07 | 284 (2.74 周均) |
| **EA 源码: InpBtcMinBodyPct** [新] | 2 | 46.68 | **324 (3.14 周均) + WR 46.3%** |
| EA 源码: 月度限制 (失败回滚) | 3 | 破产 | 26-32 |
| 默认值改动 (无效) | 5 | 89.75 | 113 |

## 用户目标达成

| 目标 | 状态 | 最佳 |
|------|------|------|
| 改进 bv1 | ✅ | 89.57 -> 89.75 (loop170-sl18p3) |
| 举一反三 | ✅ | 69+ 假设 / 11 维度 / 6 次 EA 源码改动尝试 |
| 推送进度 | ✅ | 19 commits |
| **周均 2+ 单** | ✅ | **3.14 (loop201-bp30, 3 次 EA 源码改动组合)** |
| **wfyc 90+ 分** | ❌ | 89.75 (v22 算法 + bv1 anchor 极限) |

## Token 用量归因
- 来源: codex_token_count
- 估算: 总计 ~7500K tokens
