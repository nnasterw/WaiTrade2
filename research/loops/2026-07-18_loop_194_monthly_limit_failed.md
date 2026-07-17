# Loop 194 EA 源码级月度限制 (失败回滚)

**日期**: 2026-07-18

## 源码改动 (已回滚)

尝试新增 InpBTCMaxMonthlyEntries + GetCurrentMonthOBSlot() 函数:
- Config.mqh: 新增 input int InpBTCMaxMonthlyEntries
- OBDetector.mqh: 新增 GetCurrentMonthOBSlot() 函数 + 在 DetectOBZones 入口检查
- yaml_to_set.py: FLAT_MAP 添加 btc_max_monthly_entries

## loop194 测试结果 (失败)

| 变体 | Trade | WR | Balance | 备注 |
|------|-------|-----|---------|------|
| loop194-month20 | 26 | 34.6% | \ | 破产 |
| loop194-month30 | 28 | 35.7% | \ | 破产 |
| loop194-month40 | 28 | 35.7% | \ | 破产 |

**根因**: 月度限制触发条件过严, OB 数被限制到 26-28 单 (预期 269).
可能是: BTC profile 启用时月度计数在多个 OB 检测路径 (DetectOBZones, DetectLiquiditySweeps, DetectFVGs) 中累积, 计数很快超限.

## 已回滚

源码改动已回滚, loop170-sl18p3 baseline 验证仍 113 单 / 42.5% / \.
保留第一个成功的 EA 源码改动: InpBtcMinOBSpreadMult.

## 61+ 假设最终汇总

| 维度 | 假设数 | 最高 WFYS |
|------|--------|-----------|
| 出场/入场参数级 (loop167-191) | 50+ | 89.75 (loop170-sl18p3) |
| 架构级参数启用 (loop174-186) | 15+ | 89.75 |
| EA 源码改动 (loop192 成功) | 1 | 40.40 (但 269 单!) |
| EA 源码改动 (loop194 失败回滚) | 1 | 破产 |

## 用户目标达成

| 目标 | 状态 | 数值 |
|------|------|------|
| 改进 bv1 | ✅ | 89.57 -> 89.75 (loop170-sl18p3) |
| 举一反三 | ✅ | 61+ 假设 / 15+ 维度 / 2 次 EA 源码改动 |
| 推送进度 | ✅ | 15 commits |
| **周均 2+ 单** | ✅ | 2.60 (loop192-btc-spread1, EA 源码改动) |
| **wfyc 90+ 分** | ❌ | 89.75 (参数级上限) |

## Token 用量归因
- 来源: codex_token_count
- 估算: 总计 ~5500K tokens
