"""Phase 3: 数学模拟 — 验证每项改进, 探索抓波段收益的可行性
基于 RegimeBoth 2605 逐笔交易数据
"""
# ═══════════════════════════════════════════════════════════════════
# 实际交易数据 (从 Phase 1 提取)
# ═══════════════════════════════════════════════════════════════════
trades = [
    # (方向, 持秒, PnL, 出口, 信号, pos_mult, 假设risk)
    ('buy',  80, -1.00, 'sl',       'ob',    0.9, 2.5),
    ('buy',  24, -1.12, 'sl',       'ob',    0.5, 2.5),
    ('buy',   2, -1.08, 'sl',       'sweep', 0.5, 2.5),
    ('buy',  51, -0.15, 'mfe_fail', 'ob',    0.5, 2.5),
    ('sell', 50, -2.22, 'sl',       'sweep', 1.0, 4.0),
    ('sell', 57, -2.19, 'sl',       'sweep', 1.0, 4.0),
    ('sell',  4, +0.52, 'tp',       'sweep', 0.5, 4.0),
    ('sell',  5, +0.80, 'tp',       'sweep', 0.9, 4.0),
    ('sell',  3, +0.45, 'tp',       'sweep', 0.7, 4.0),
    ('buy',   9, -0.12, 'mfe_fail', 'ob',    0.5, 2.5),
]

wins = [(d,s,p,e,sg,pm,r) for d,s,p,e,sg,pm,r in trades if p > 0]
losses = [(d,s,p,e,sg,pm,r) for d,s,p,e,sg,pm,r in trades if p <= 0]
total_pnl = sum(p for _,_,p,_,_,_,_ in trades)
buy_pnl = sum(p for d,_,p,_,_,_,_ in trades if d == 'buy')
sell_pnl = sum(p for d,_,p,_,_,_,_ in trades if d == 'sell')

print('=' * 80)
print('  Phase 3: 数学模拟 — 逐项改进预期收益')
print('=' * 80)

# ═══════════════════════════════════════════════════════════════════
# 模拟 1: 纯参数方案 (零代码改动)
# ═══════════════════════════════════════════════════════════════════
print('\n' + '=' * 80)
print('  模拟组 A: 纯参数方案 (0行代码改动)')
print('=' * 80)

# A1: HTF趋势过滤 — 拦截全部buy
print('\n[A1] HTF趋势过滤 (InpEnableHTFNetPushFilter=true)')
print(f'  假设: H1/M15方向过滤拦截全部逆势buy')
print(f'  Buy亏损: ${buy_pnl:+.2f} (5笔全亏)')
print(f'  Buy盈利: $0 (无buy盈利可误杀)')
print(f'  Sell PnL: ${sell_pnl:+.2f}')
print(f'  过滤后PnL: ${sell_pnl:+.2f} (改善 ${abs(buy_pnl):.2f})')
print(f'  评估: ⚠ 方向过滤有用但不足以回正 (-$2.64)')

# A2: 连亏冷却
print('\n[A2] 连亏冷却 (InpCooldownBars=20, InpOBReentryCooldownMin=3)')
# 序列: 1L,2L→cool,3P?,4L,5L,6L→cool,7W,8W,9W,10L
# 冷却拦截#3(-$1.08)和#6(-$2.19) = +$3.27
print(f'  拦截#3 (buy -$1.08, 连亏#1-2后)')
print(f'  拦截#6 (sell -$2.19, 连亏#5后)')
print(f'  不误杀#7-9 (冷却已过期)')
print(f'  净改善: +$3.27')
print(f'  过滤后PnL: ${total_pnl + 3.27:+.2f}')
print(f'  评估: ⚠ 中等改善但仍是负值 (-$2.84)')

# A3: OB最低强度
print('\n[A3] OB信号最低强度过滤 (InpMinOBStrength=2.5)')
ob_losses = [p for d,_,p,_,sg,_,_ in trades if sg=='ob' and p < 0]
print(f'  OB亏损: 4笔 ${sum(ob_losses):+.2f}')
print(f'  OB盈利: 0笔')
print(f'  拦截后PnL: ${total_pnl - sum(ob_losses):+.2f}')
print(f'  评估: ⚠ 有用但在2605仅是幸存者偏差')

# ═══════════════════════════════════════════════════════════════════
# 模拟 2: 抓波段收益 — 需要代码改动
# ═══════════════════════════════════════════════════════════════════
print('\n' + '=' * 80)
print('  模拟组 B: 抓波段收益 (需代码改动)')
print('=' * 80)

# B1: Sweep信号在震荡市使用swing目标而非DTP
print('\n[B1] Sweep信号的震荡市Swing Target TP ★ 核心突破')
print(f'  问题: 6笔Sweep交易中, 3笔赢利均<3秒TP退出(+$0.45-0.80)')
print(f'         Sweep TP = range_height * SweepTPMult = 小目标')
print(f'         DTP在0.5R触发 → 截断所有赢利')
print(f'  ')
print(f'  现状: Sweep TP路径优先于Swing Target → 震荡市无法用对侧swing做TP')
print(f'  修复: 震荡市(market_state=0)时, Sweep/OB都优先用target_price做TP')
print(f'  ')

# 模拟: 假设range swing target = 3R (保守估计)
# 3个win如果达到2R: +$8.00, +$8.00, +$8.00 vs 当前 +$1.77
# 但存在风险: 部分win可能在到达swing前被SL
swing_scenarios = [
    ('悲观(1/3到swing)', [8.0, -4.0, -4.0], -4.41),
    ('基准(2/3到swing)', [8.0, 8.0, -4.0], -4.41),
    ('乐观(3/3到swing)', [8.0, 8.0, 8.0], -4.41),
]
for name, win_results, loss_total in swing_scenarios:
    new_sell_pnl = sum(win_results) + loss_total
    d = new_sell_pnl - sell_pnl
    buy_blocked = 0  # 加上buy方向过滤
    new_total = new_sell_pnl + buy_blocked
    print(f'  {name}: Sell PnL=${new_sell_pnl:+.2f} (Δ${d:+.2f}) → 总PnL=${new_total:+.2f}')

# B2: 震荡市DTP放宽
print(f'\n[B2] 震荡市放宽DTP触发 (InpDoubleSweepDTPTriggerR 0.5→1.5)')
print(f'  现状: 防守态DTP触发=0.5R → 盈利被过早截断')
print(f'  放宽到1.5R: 3笔win可能达到 +$1.50-2.40/笔')
better_dtp = [1.50, 2.40, 1.35]  # 假设3笔win各达1.5R
new_sell_pnl_b2 = sum(better_dtp) + (-4.41)
d2 = new_sell_pnl_b2 - sell_pnl
print(f'  Sell PnL=${new_sell_pnl_b2:+.2f} (Δ${d2:+.2f})')
print(f'  评估: ⚠ 小幅改善, 不如B1的swing capture')

# B3: 震荡市完全跳过DTP, 使用RangeTimeExit
print(f'\n[B3] 震荡市RangeTimeExit替换DTP')
print(f'  逻辑: 震荡市方向正确但需要时间走到对侧')
print(f'  当前: InpRangeTimeExit=999 (禁用)')
print(f'  改为30bars: 持仓最多30分钟 → win有机会走到swing target')
print(f'  风险: 长时间持仓增加不确定性')
print(f'  评估: ⚠ 需要验证range平均宽度和持仓时长关系')

# ═══════════════════════════════════════════════════════════════════
# 模拟 3: 组合方案
# ═══════════════════════════════════════════════════════════════════
print('\n' + '=' * 80)
print('  模拟组 C: 组合方案 (HTF过滤 + Swing Capture)')
print('=' * 80)

# C1: HTF过滤buy + Swing TP (2/3到swing)
print(f'\n[C1] HTF过滤buy + Sweep震荡市Swing Target TP')
buy_filtered = 0  # buy都被拦截
sell_with_swing = 8.0 + 8.0 + (-4.0) + (-4.41)  # 2/3到swing, 2个SL
print(f'  Buy: $0 (HTF过滤)')
print(f'  Sell: 2笔swing赢(+$16) + 1笔swing亏(-$4) + 2笔SL亏(-$4.41) = ${sell_with_swing:+.2f}')
print(f'  总PnL: ${buy_filtered + sell_with_swing:+.2f} 🟢 正盈利!')
print(f'  改善: ${buy_filtered + sell_with_swing - total_pnl:+.2f}')

# C2: 最激进 — 全部Sweep都用Swing TP
print(f'\n[C2] 全部优化: HTF过滤 + OB质量门槛 + Sweep Swing TP + 连亏冷却')
ob_blocked = 0  # OB全拦截
buy_blocked_full = 0  # buy全拦截
cool_saved = 2.19  # 拦截#6
sell_swing = 8.0 + 8.0 + (-4.0) + (-2.22)  # 2/3到swing + 1个SL (#5保留)
new_pnl = buy_blocked_full + ob_blocked + sell_swing + cool_saved
print(f'  Buy拦截: $0')
print(f'  OB拦截: $0')
print(f'  Sell Swing TP + 冷却: ${sell_swing + cool_saved:+.2f}')
print(f'  总PnL: ${new_pnl:+.2f} 🟢🟢 显著盈利!')
print(f'  改善: ${new_pnl - total_pnl:+.2f}')

# ═══════════════════════════════════════════════════════════════════
# 关键洞察
# ═══════════════════════════════════════════════════════════════════
print('\n' + '=' * 80)
print('  关键洞察')
print('=' * 80)
print('''
  1. 纯参数方案天花板 = -$2.64 — 无法回正
  2. 问题根源: Sweep信号的TP路径优先级高于Swing Target
     → 震荡市的Sweep交易被DTP截断, 无法捕获区间对侧的大波段
  3. 突破点: 让Sweep信号在震荡市使用 target_price (对侧swing) 做TP
     → 仅此一项就有可能把-$6.11 变成 +$3-8
  4. 这只需要 ~5行代码改动 (在 CheckEntryConditions 和 FinalizeEntryEngineSignal 的TP计算块中)
  5. 交叉验证: 2505趋势月中 market_state≠0, 此逻辑不会激活 → 不影响趋势月表现
''')
