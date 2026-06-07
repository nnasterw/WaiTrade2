#!/usr/bin/env python3
"""Phase 2: Falsifiable hypotheses with mathematical verification for PathB 2605."""
from collections import defaultdict

# ── PathB 2605 已知数据 ──
# From Phase 1 analysis: 16 trades, -$14.11 total PnL
# Exit reasons: SL=11, DTP=3, MFE_FAIL=2
# Hold times: <10s=2, 10-60s=11, 1-5min=3
# Signal types: SWP=13, OB=3

# From backtest: total PnL = -$14.11
# Estimated per-trade metrics (from similar S2 2605 data):
# S2 2605: 37T, WR=24.3%, PF=0.35, avg per trade = -$0.616

# For PathB 2605, 16T, -$14.11 → avg = -$0.882 per trade
# If we assume DTP wins are ~$1.50 each and SL losses are ~-$2.00 each:
# 3 * $1.50 - 11 * $2.00 - 2 * $0.50 = $4.50 - $22.00 - $1.00 = -$18.50 (rough)
# Let's use the actual PnL = -$14.11

# From S2 2605: WR=24.3%, avg_W ≈ $1.59, avg_L ≈ -$1.28 (from prior analyses)
# PathB 2605: similar per-trade characteristics but fewer trades

print("=" * 70)
print("  Phase 2: 可证伪假说 & 数学验证")
print("=" * 70)

# ── H1: 防守态衰减Sweep信号仓位 ──
print("""
H1: Sweep OB在震荡市信号质量低于普通OB → 防守态衰减SWP仓位
  当前状态: Sweep OB和普通OB使用相同仓位乘数
  观测: PathB 2605中81%(13/16)交易来自SWP信号, S2中0%SWP
        S2(纯OB)亏损-$22.81/37T=-$0.616/T, PathB(SWP为主)亏损-$14.11/16T=-$0.882/T
        PathB平均每笔亏损更大 → SWP信号单笔质量可能更差
  若真: 防守态衰减SWP仓位(衰减50%) → 13笔SWP亏损减半 → 预期改善 +$5至+$10
  若伪: SWP仓位衰减不影响PnL(风险本位lot计算抵消)
  证伪方法: 对比 PathB+Sweep衰减 vs PathB 在2605的回测
""")

# Math check: does risk-based lot sizing neutralize this?
# lot = balance * risk% / (SL * point_value) * pos_mult
# Reducing pos_mult (via SweepDecay=0.5) directly reduces lot size
# So this SHOULD work at the end of chain (after cap)
print("  验证: 仓位乘数衰减在链末端(ApplyPositionMultiplierCap之后)生效, 不受风险本位抵消")
print("  预期: 2605 PnL从-$14改善至约-$9")

# ── H2: 防守态禁用Sweep OB入场 ──
print("""
H2: 双扫确认后, 只允许普通OB入场(禁用SWP OB入场)
  当前状态: 双扫确认放行后, 所有OB类型均可入场(含SWP)
  观测: S2(纯OB)在2605表现更好(-$22.81/37T vs PathB -$14.11/16T)
        实际上PathB per-trade更差(-$0.882 vs -$0.616)
        SWP信号可能是双扫确认后仍亏损的来源
  若真: 禁用SWP入场, 仅保留普通OB → 交易更少但质量更高
  若伪: 禁用SWP后无足够交易, 或普通OB在双扫后质量也无提升
  证伪方法: 新增InpDoubleSweepBlockSweepEntry参数, 测试2605

  验证: 如果PathB的13笔SWP中, WR与S2的OB WR相似(24%),
        则约3笔盈利/10笔亏损, 去掉这13笔节省约$7亏损
        加上OB的3笔不变, 预期: 3笔OB维持现状 + 省下SWP亏损 → PnL约-$7
""")

# ── H3: 防守态仓位全局衰减 ──
print("""
H3: 防守态全局仓位衰减叠加双扫确认
  当前状态: 双扫确认过滤入场数量, 但不改变入场后的仓位大小
  观测: PathB+decay0.5在2605(PathABD): 8T, -$10.31
        比PathB(16T, -$14.11)少亏$3.80但交易数减半
        衰减过滤了MORE交易(因lot<0.01被拒绝)
  若真: 适度衰减(0.7而非0.5)可保留交易数同时降低亏损
  若伪: 任何衰减都会过度减少交易数
  证伪方法: 测试PathB+decay=0.7在2605

  验证: decay=0.7保留约12T(16*0.75), 每笔亏损从-$0.88降至-$0.62
        预期: 12T * -$0.62 = -$7.44
""")

# ── H4: 双扫窗口微调 ──
print("""
H4: 双扫窗口从20 bars缩小至15 bars, 提高时效性
  当前状态: 窗口20 bars, 包含的Sweep OB可能过时
  观测: 2605窄幅震荡周期约30-60分钟(M1), 20 bars=20分钟窗口适当
        缩小到15 bars可能排除过期Sweep, 提高双扫确认的新鲜度
  若真: 15 bars窗口 → 更严格的时效性 → WR提升
  若伪: 15 bars和20 bars无差异, 或过滤更少(15 bars更宽松)
  证伪方法: 测试PathB+window15在2605和2505

  验证: 预计微小差异, 2605可能改善$1-3
""")

# ── H5: 防守态DTP触发降低 ──
print("""
H5: 防守态DTP触发从1.0R降至0.5R, 捕捉窄幅微利
  当前状态: DTP=1.0R, 在2605窄幅中很少触发(2605 DTP率仅5.8%)
  观测: PathB 2605仅3/16 DTP退出, 若DTP=0.5R可增加DTP退出比例
        窄幅区间位移约0.5-1.0R, 0.5R更容易到达
  若真: 降低DTP触发 → 更多小赢 → 总PnL改善
  若伪: 0.5R触发过早, 切碎利润 → avg_W下降 → 净效应为负
  证伪方法: 测试PathB+DTP=0.5R在2605和2505

  验证: 若原来3笔DTP变5笔, 新增2笔各盈利$0.75(0.5R时的avg_W)
        = +$1.50 - 这2笔原本可能是SL(-$2.00 each)
        改善 = $1.50 - (-$4.00) = +$5.50
        但2505趋势月DTP=0.5R会大幅减少大赢, 退化严重
""")

# Summary
print("\n" + "=" * 70)
print("  Phase 2 假说优先级排序")
print("=" * 70)
print("""
  P0  H2: 双扫后禁用SWP入场        ~5行代码  预期2605: -$7    风险: 低
  P0  H3: 防守态decay=0.7叠加       ~0行(已有) 预期2605: -$7    风险: 中(2505退化)
  P1  H1: 防守态SWP仓位衰减         ~10行代码 预期2605: -$9    风险: 低
  P2  H4: 双扫窗口15bars            ~0行(参数) 预期2605: -$12   风险: 低
  P3  H5: 防守态DTP=0.5R            ~5行代码  预期2605: -$8    风险: 高(2505大退化)
""")

print("\n[DONE]")
