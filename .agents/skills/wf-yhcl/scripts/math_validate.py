#!/usr/bin/env python3
"""
数学验证工具：用期望值公式模拟过滤器的独立效果。
不依赖任何历史月份标记——只用可观测的交易级特征。

用法:
  python math_validate.py --hypothesis noise_gate --trades 1289 --sl_pct 0.82 --avg_loss -1.80 --avg_win 1.66 --block_rate 0.85 --false_rate 0.46
  python math_validate.py --hypothesis trend_alignment --trades 1289 --aligned_wr 0.55 --counter_wr 0.40 --aligned_pct 0.60
  python math_validate.py --hypothesis ob_quality --trades 1289 --low_q_wr 0.38 --high_q_wr 0.56 --low_q_pct 0.40
  python math_validate.py --hypothesis sl_buffer --trades 1289 --tight_pct 0.30 --tight_avg_loss 2.50 --tight_wr 0.35
"""
import argparse


def validate_noise_gate(trades, sl_pct, avg_loss, avg_win, block_rate, false_rate):
    """Tick噪音门控独立验证。
    不依赖"这个月好不好"——只看门控本身对期望值的影响。
    """
    n = trades
    wr = 1 - sl_pct
    avg_L = abs(avg_loss)
    avg_W = avg_win

    pnl_old = n * (wr * avg_W - sl_pct * avg_L)
    blocked = n * block_rate
    noise_killed = blocked * (1 - false_rate)
    false_killed = blocked * false_rate
    pnl_new = pnl_old + noise_killed * avg_L - false_killed * avg_W
    improvement = pnl_new - pnl_old

    trades_new = n - blocked

    print(f"\n{'='*60}")
    print(f"  Tick噪音门控验证")
    print(f"{'='*60}")
    print(f"  原始: {n}笔, WR={wr*100:.1f}%, PnL=${pnl_old:.0f}")
    print(f"  拦截率: {block_rate*100:.0f}% ({blocked:.0f}笔)")
    print(f"    拦截噪音损失: {noise_killed:.0f}笔 → 省下 ${noise_killed*avg_L:.0f}")
    print(f"    误杀盈利单: {false_killed:.0f}笔 → 损失 ${false_killed*avg_W:.0f}")
    print(f"  过滤后: {trades_new:.0f}笔, WR={noise_killed/blocked*100:.0f}%→{wr*100:.0f}%, PnL=${pnl_new:.0f}")
    print(f"  净改善: ${improvement:+.0f}")

    # 敏感度扫描
    print(f"\n  ── 误杀率敏感度 ──")
    for fr in [0.20, 0.30, 0.40, 0.50, 0.60]:
        nk = blocked * (1 - fr)
        fk = blocked * fr
        imp = nk * avg_L - fk * avg_W
        pnl = pnl_old + imp
        verdict = "PASS" if imp > 0 else "FAIL"
        print(f"    false_rate={fr*100:.0f}% → 净改善=${imp:+.0f} (PnL=${pnl:.0f}) {verdict}")

    # 盈亏平衡误杀率
    be = avg_L / (avg_W + avg_L)
    print(f"\n  盈亏平衡误杀率: {be*100:.1f}%")
    print(f"  (误杀率超过此值 → 过滤器净效应为负)")
    return improvement > 0


def validate_trend_alignment(trades, aligned_wr, counter_wr, aligned_pct,
                              avg_win=1.66, avg_loss=1.80):
    """趋势对齐验证：检查同方向的入场WR是否显著优于逆势入场。
    不分析"哪个时间段"，只分析"入场方向与趋势方向的关系"。
    """
    n = trades
    aligned_trades = n * aligned_pct
    counter_trades = n * (1 - aligned_pct)

    pnl_old = (aligned_trades * aligned_wr + counter_trades * counter_wr) * avg_win \
            - (aligned_trades * (1-aligned_wr) + counter_trades * (1-counter_wr)) * avg_loss

    # 拦截所有逆势入场
    pnl_new = aligned_trades * aligned_wr * avg_win - aligned_trades * (1-aligned_wr) * avg_loss
    improvement = pnl_new - pnl_old
    wr_diff = aligned_wr - counter_wr

    print(f"\n{'='*60}")
    print(f"  趋势对齐验证")
    print(f"{'='*60}")
    print(f"  对齐入场: {aligned_trades:.0f}笔 ({aligned_pct*100:.0f}%), WR={aligned_wr*100:.1f}%")
    print(f"  逆势入场: {counter_trades:.0f}笔 ({(1-aligned_pct)*100:.0f}%), WR={counter_wr*100:.1f}%")
    print(f"  WR差: {wr_diff*100:+.1f}%")
    print(f"  原PnL=${pnl_old:.0f}")
    print(f"  拦截逆势后PnL=${pnl_new:.0f}")
    print(f"  净改善=${improvement:+.0f}")

    if wr_diff > 0.10:
        verdict = "[PASS] 趋势对齐显著有效"
    elif wr_diff > 0.05:
        verdict = "[WARN] 微弱有效，需避免过度拦截"
    else:
        verdict = "[FAIL] WR差异不足，趋势对齐过滤无效"
    print(f"  判定: {verdict}")

    # 最优阈值扫描
    print(f"\n  ── 逆势拦截比例扫描 ──")
    for intercept_pct in [0.25, 0.50, 0.75, 1.0]:
        blocked = counter_trades * intercept_pct
        saved_losses = blocked * (1 - counter_wr) * avg_loss
        missed_wins = blocked * counter_wr * avg_win
        net = saved_losses - missed_wins
        print(f"    拦截{intercept_pct*100:.0f}%逆势 → 净改善=${net:+.0f}")

    return wr_diff > 0.05


def validate_sl_buffer(trades, tight_pct, tight_avg_loss, tight_wr, avg_win=1.66):
    """SL缓冲验证：检查过紧止损是否可以通过放宽缓冲来改善。
    不依赖哪个月——只看"SL距离太窄导致被噪音秒杀"的定量影响。
    """
    n = trades
    tight_trades = n * tight_pct

    tight_pnl = tight_trades * (tight_wr * avg_win - (1-tight_wr) * tight_avg_loss)
    improvement = -tight_pnl  # 过滤掉它们=省下损失-丢掉盈利

    print(f"\n{'='*60}")
    print(f"  SL缓冲验证")
    print(f"{'='*60}")
    print(f"  SL过紧交易: {tight_trades:.0f}笔 ({tight_pct*100:.0f}%)")
    print(f"    avg_loss=${tight_avg_loss:.2f}, WR={tight_wr*100:.1f}%")
    print(f"    这批交易净盈亏=${tight_pnl:.0f}")
    print(f"  放宽SL缓冲后预期净改善=${improvement:+.0f}")

    if tight_pnl < 0 and tight_pct > 0.1:
        print(f"  [PASS] SL缓冲放宽有效")
    elif tight_pnl < 0:
        print(f"  [WARN] 有效但影响范围小")
    else:
        print(f"  [FAIL] SL过紧交易本身盈利，放宽会退化")

    return tight_pnl < 0


def validate_ob_quality(trades, low_q_wr, high_q_wr, low_q_pct,
                         avg_win=1.66, avg_loss=1.80):
    """OB质量验证：不同质量OB的入场WR差异→是否可以用质量过滤。
    只关注OB可观测维度（大小/年龄/反弹深度），不涉及时段。
    """
    n = trades
    low_q_trades = n * low_q_pct
    high_q_trades = n * (1 - low_q_pct)
    wr_diff = high_q_wr - low_q_wr

    pnl_old = (low_q_trades * low_q_wr + high_q_trades * high_q_wr) * avg_win \
            - (low_q_trades * (1-low_q_wr) + high_q_trades * (1-high_q_wr)) * avg_loss
    pnl_new = high_q_trades * high_q_wr * avg_win - high_q_trades * (1-high_q_wr) * avg_loss
    improvement = pnl_new - pnl_old

    print(f"\n{'='*60}")
    print(f"  OB质量验证")
    print(f"{'='*60}")
    print(f"  低质量OB: {low_q_trades:.0f}笔 ({low_q_pct*100:.0f}%), WR={low_q_wr*100:.1f}%")
    print(f"  高质量OB: {high_q_trades:.0f}笔, WR={high_q_wr*100:.1f}%")
    print(f"  WR差: {wr_diff*100:+.1f}%")
    print(f"  原PnL=${pnl_old:.0f}")
    print(f"  过滤低质量OB后PnL=${pnl_new:.0f}")
    print(f"  净改善=${improvement:+.0f}")
    print(f"  [PASS] OB质量过滤有效" if wr_diff > 0.10 and improvement > 0
          else f"  [FAIL] OB质量差异不足以支撑过滤")
    return wr_diff > 0.10


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='数学验证工具 — 可复用交易特征')
    parser.add_argument('--hypothesis', choices=['noise_gate','trend_alignment','sl_buffer','ob_quality'],
                        default='noise_gate', help='验证的假设类型')
    parser.add_argument('--trades', type=int, default=1289, help='总回测交易数（非模拟）')
    parser.add_argument('--avg_win', type=float, default=1.66)
    parser.add_argument('--avg_loss', type=float, default=1.80)
    # 噪音门控
    parser.add_argument('--sl_pct', type=float, default=0.82)
    parser.add_argument('--block_rate', type=float, default=0.85)
    parser.add_argument('--false_rate', type=float, default=0.46)
    # 趋势对齐
    parser.add_argument('--aligned_wr', type=float, default=0.55)
    parser.add_argument('--counter_wr', type=float, default=0.40)
    parser.add_argument('--aligned_pct', type=float, default=0.60)
    # SL缓冲
    parser.add_argument('--tight_pct', type=float, default=0.30)
    parser.add_argument('--tight_avg', type=float, default=2.50)
    parser.add_argument('--tight_wr', type=float, default=0.35)
    # OB质量
    parser.add_argument('--low_q_wr', type=float, default=0.38)
    parser.add_argument('--high_q_wr', type=float, default=0.56)
    parser.add_argument('--low_q_pct', type=float, default=0.40)

    args = parser.parse_args()

    if args.hypothesis == 'noise_gate':
        validate_noise_gate(args.trades, args.sl_pct, -args.avg_loss,
                           args.avg_win, args.block_rate, args.false_rate)
    elif args.hypothesis == 'trend_alignment':
        validate_trend_alignment(args.trades, args.aligned_wr, args.counter_wr,
                                args.aligned_pct, args.avg_win, args.avg_loss)
    elif args.hypothesis == 'sl_buffer':
        validate_sl_buffer(args.trades, args.tight_pct, args.tight_avg,
                          args.tight_wr, args.avg_win)
    elif args.hypothesis == 'ob_quality':
        validate_ob_quality(args.trades, args.low_q_wr, args.high_q_wr,
                           args.low_q_pct, args.avg_win, args.avg_loss)
