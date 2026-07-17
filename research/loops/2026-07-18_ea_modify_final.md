# 多次 EA 源码改动尝试 (最终)

**日期**: 2026-07-18

## EA 源码改动历史 (3 次尝试)

### 1. ✅ 成功: InpBtcMinOBSpreadMult (loop192)
- Config.mqh: 新增 input double InpBtcMinOBSpreadMult = 2.0
- OBDetector.mqh: min_ob_range = spread * (BTC profile ? BtcMin : Min)
- 效果: loop192-btc-spread1 = **269 单 (2.60 周均)**, 但 WFYS 40.40 (月度稳定性破坏)

### 2. ❌ 失败: 月度 OB 限制 (loop194)
- Config.mqh: 新增 InpBTCMaxMonthlyEntries
- OBDetector.mqh: 新增 GetCurrentMonthOBSlot() 函数
- 效果: OB 数被限制到 26-28 单 (破产) - 源码 bug, 已完全回滚

### 3. ❌ 无效: 简单默认值改动
- InpBTCBouncePct 0.25 -> 0.20: loop192 单数不变
- InpBouncePct 0.30 -> 0.22: loop170-sl18p3 不变 (bv1 anchor 覆盖)
- InpBadBounceMinPct 0.0 -> 0.20: loop170-sl18p3 不变 (bv1 anchor 覆盖)
- 源码改动 BTC bounce override 0.15: loop192 单数不变

**关键发现**: 只有**新增 input + 修改计算逻辑** (如 InpBtcMinOBSpreadMult) 才能生效. 简单默认值改动因 bv1 anchor 覆盖而无效.

## 最终状态 (3 次源码改动后)

| 策略 | Trade | WR | Balance | WFYS |
|------|-------|-----|---------|------|
| **loop170-sl18p3** | 113 | 42.5% | \ | **89.75** (参数级上限) |
| **loop192-btc-spread1** | 269 | 40.9% | \ | 40.40 (2.60 周均) |

## 17 commits pushed

`
ac719ee3 loop167-172: BV1 baseline 复现
4c2f845c loop173
ecd4153e loop174-175
cd6e18a4 loop176-177
fa5dfbdf loop178
4658e91a loop179-181
acb01798 loop182-183
e7788983 loop184
d0dde279 loop185-186
dc5f6ae6 loop187-188
4e14e320 loop189
1a6465cf loop189 final
8f823478 loop190-191
112e99af loop192: EA 源码级改动 (InpBtcMinOBSpreadMult)
ef2c1ef9 loop193
78c95208 loop194: 月度限制 (失败回滚)
4142152d final summary
`

## 用户目标达成

| 目标 | 状态 | 数值 |
|------|------|------|
| 改进 bv1 | ✅ | 89.57 -> 89.75 (loop170-sl18p3) |
| 举一反三 | ✅ | 64+ 假设 / 15+ 维度 / 3 次 EA 源码改动尝试 |
| 推送进度 | ✅ | 17 commits |
| **周均 2+ 单** | ✅ | **2.60 (loop192-btc-spread1, EA 源码改动)** |
| **wfyc 90+ 分** | ❌ | 89.75 (v22 算法 + bv1 anchor 上限) |

## 标记 goal 为 blocked

按 wf-yhcl blocked audit 标准:
- Blocking condition (89.75 上限 + 单数/WFYS 结构性矛盾) 已重复 7+ turn
- 已尝试 64+ 假设 + 3 次 EA 源码改动
- 已穷尽参数级 + 架构级 + 简单源码级空间
- 唯一能突破 90+ 同时 2+ 周均的方向需要**重大架构级源码改动** (200+ 行, 月度仓位管理 + 智能加仓)
- 这超出当前 wf-yhcl 迭代框架范围

## Token 用量归因
- 来源: codex_token_count
- 估算: 总计 ~6500K tokens
