# Loop 192 EA 源码级改动 - 单数突破

**日期**: 2026-07-17

## EA 源码改动

修改文件:
1. **mql5/Include/WaiTrade2/Config.mqh** (line 120):
   - 新增 input: input double InpBtcMinOBSpreadMult = 2.0;
2. **mql5/Include/WaiTrade2/OBDetector.mqh** (line 1044):
   - min_ob_range = spread * (UseBTCProfile() && InpBtcMinOBSpreadMult > 0 ? InpBtcMinOBSpreadMult : InpMinOBSpreadMult);
3. **scripts/yaml_to_set.py**:
   - FLAT_MAP: "btc_min_ob_spread_mult": "InpBtcMinOBSpreadMult"

编译: 0 errors, 0 warnings. 5 个 EA 全部成功编译.

## loop192 (BTC profile + EA 源码级 OB spread 放宽)

| 变体 | Trade | WR | Balance | WFYS | 周均 |
|------|-------|-----|---------|------|------|
| **loop192-btc-spread1 (1.0)** | **269** | 40.9% | \ | **40.40** | **2.60** ⭐ |
| loop192-btc-spread15 (1.5) | 239 | 41.4% | \ | 45.14 | 2.31 |
| loop192-btc-spread05 (0.5) | 276 | 41.3% | \ | 37.78 | 2.67 |

## 关键洞察

EA 源码改动成功实现 **单数突破** (113 -> 269, +138, 2.38 倍增加)
- **周均 2.60 单 达成用户目标 (>= 2.0)** ✓
- 但 WFYS 因月度稳定性破坏暴跌至 40.40
- 单数突破 vs WFYS 稳定的本质矛盾仍然存在

## 用户目标达成

| 目标 | 状态 | 数值 |
|------|------|------|
| 改进 bv1 | ✅ | 89.57 -> 89.75 (loop170-sl18p3) |
| 举一反三 | ✅ | 60 个假设 / 15+ 维度 |
| 推送进度 | ✅ | 13 commits |
| **EA 源码改动** | ✅ | 已实施 (Config.mqh + OBDetector.mqh) |
| **周均 2+ 单** | ✅ | **2.60 单 (loop192-btc-spread1)** |
| **wfyc 90+ 分** | ❌ | 89.75 (loop170-sl18p3) |

## 最终策略候选

- **WFYS 最高**: v11-btc1-loop170-sl18p3 (89.75, 1.09 周均, magic=207173)
- **单数最高**: v11-btc1-loop192-btc-spread05 (276 单, 2.67 周均, WFYS 37.78)
- **均衡**: v11-btc1-loop192-btc-spread1 (269 单, 2.60 周均, WFYS 40.40)

## Token 用量归因
- 来源: codex_token_count
- 估算: Loop 192 总计 ~300K tokens (含 EA 源码改动 + 编译 + 测试)
