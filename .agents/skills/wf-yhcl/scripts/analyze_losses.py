#!/usr/bin/env python3
"""
订单级诊断：提取每笔交易的独立特征。
不按任何月份/时段分组，只输出每笔交易的:
  出口原因/持仓时长/趋势对齐度/OB评分/avgWvsavgL/盈利R倍数分布
"""
import re, sys
from pathlib import Path
from collections import Counter, defaultdict


def parse_trades(htm_path):
    """解析 MT5 HTML 报告，返回每笔交易的独立特征字典列表。"""
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    pending = []
    trades = []

    for row_html in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html)
        if len(cells) != 13:
            continue
        ctype = cells[3].strip()
        if ctype == 'balance':
            continue
        io = cells[4].strip()
        time_str = cells[0].strip()

        try:
            pnl = float(cells[10].strip().replace(' ', '').replace(',', ''))
        except ValueError:
            pnl = 0.0

        if io == 'in':
            pending.append({
                'time': time_str, 'direction': ctype,
                'price': float(cells[6].strip()) if cells[6].strip() else 0,
            })
        elif io == 'out' and pending:
            entry = pending.pop(0)
            hold = _hold_seconds(entry['time'], time_str)
            trades.append({
                'pnl': pnl,
                'hold_sec': hold,
                'direction': entry['direction'],
                'comment': cells[12].strip(),
                'entry_price': entry['price'],
                'exit_price': float(cells[6].strip()) if cells[6].strip() else 0,
                'exit_reason': classify_exit(cells[12].strip(), hold),
            })
    return trades


def _hold_seconds(entry_time, exit_time):
    """计算持仓秒数。"""
    from datetime import datetime
    def _parse(s):
        parts = s.split()
        d = parts[0].split('.')
        t = parts[1].split(':')
        return datetime(int(d[0]), int(d[1]), int(d[2]),
                        int(t[0]), int(t[1]), int(t[2]))

    try:
        et = _parse(entry_time)
        xt = _parse(exit_time)
        return int((xt - et).total_seconds())
    except Exception:
        return 0


def classify_exit(comment, hold_sec):
    """从comment字段解析出口原因（不依赖任何上下文）。"""
    c = (comment or '').lower()
    if 'be' in c:
        return 'BE'
    if 'dtp' in c:
        return 'DTP'
    if 'tp' in c:
        return 'TP'
    if 'sl' in c:
        if hold_sec < 10:
            return 'SL(<10s)'
        elif hold_sec < 60:
            return 'SL(<1m)'
        elif hold_sec < 300:
            return 'SL(<5m)'
        return 'SL(>5m)'
    if 'mfe' in c:
        return 'MFE_FAIL'
    if 'decay' in c or 'decay' in c:
        return 'DECAY'
    if 'timeout' in c or 'time' in c:
        return 'TIMEOUT'
    return 'OTHER'


# ===== 输出函数（始终不按月、不用时段）=====

def report_exit_reasons(trades):
    """出口原因分布。"""
    losses = [t for t in trades if t['pnl'] < 0]
    wins = [t for t in trades if t['pnl'] > 0]
    ec = Counter(t['exit_reason'] for t in losses)
    wec = Counter(t['exit_reason'] for t in wins)
    print(f"\n  亏损出口原因 (共{len(losses)}笔):")
    for reason, cnt in ec.most_common(6):
        print(f"    {reason:<12} {cnt:>4}T ({cnt/len(losses)*100:>5.1f}%)")
    print(f"  盈利出口原因 (共{len(wins)}笔):")
    for reason, cnt in wec.most_common(6):
        print(f"    {reason:<12} {cnt:>4}T ({cnt/len(wins)*100:>5.1f}%)")


def report_hold_time(trades):
    """持仓时长分布（不分月份）。"""
    losses = [t for t in trades if t['pnl'] < 0]
    buckets = {'<5s': 0, '5-10s': 0, '10-30s': 0,
               '30s-1m': 0, '1-5m': 0, '5-30m': 0, '>30m': 0}
    for t in losses:
        s = t['hold_sec']
        if s < 5:
            buckets['<5s'] += 1
        elif s < 10:
            buckets['5-10s'] += 1
        elif s < 30:
            buckets['10-30s'] += 1
        elif s < 60:
            buckets['30s-1m'] += 1
        elif s < 300:
            buckets['1-5m'] += 1
        elif s < 1800:
            buckets['5-30m'] += 1
        else:
            buckets['>30m'] += 1
    print(f"\n  亏损持仓时长 (共{len(losses)}笔):")
    for label, cnt in buckets.items():
        if cnt > 0:
            pct = cnt / len(losses) * 100
            bar = '█' * int(pct / 3)
            print(f"    {label:<10} {cnt:>4}T ({pct:>5.1f}%) {bar}")


def report_wl_ratio(trades):
    """盈亏强度比值——不受月份影响的独立诊断指标。"""
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]
    if not wins or not losses:
        return
    aw = sum(t['pnl'] for t in wins) / len(wins)
    al = abs(sum(t['pnl'] for t in losses) / len(losses))
    ratio = aw / al
    print(f"\n  盈亏强度:")
    print(f"    avg_win=${aw:.3f}  avg_loss=${al:.3f}  W/L={ratio:.2f}x")
    if ratio < 0.8:
        print("    ⚠️  W/L<0.8 → 亏损比盈利大，数学上负期望（除非胜率极高）")
    elif ratio < 1.2:
        print("    → 盈亏接近1:1，靠胜率赚钱")
    else:
        print("    → 盈利单覆盖亏损，胜率容忍度高")


def report_r_multiple_distribution(trades):
    """盈利R倍数分布——出口机制的核心诊断。"""
    wins = [t for t in trades if t['pnl'] > 0]
    if not wins:
        return
    losses = [t for t in trades if t['pnl'] < 0]
    avg_r = abs(sum(t['pnl'] for t in losses) / len(losses)) if losses else 1.0
    if avg_r <= 0:
        avg_r = 1.0

    buckets = Counter()
    for t in wins:
        r = t['pnl'] / avg_r
        if r < 0.5:
            buckets['<0.5R'] += 1
        elif r < 1.0:
            buckets['0.5-1R'] += 1
        elif r < 2.0:
            buckets['1-2R'] += 1
        elif r < 3.0:
            buckets['2-3R'] += 1
        elif r < 5.0:
            buckets['3-5R'] += 1
        else:
            buckets['>5R'] += 1

    print(f"\n  盈利R倍数分布 (avg_loss作为1R: ${avg_r:.2f}):")
    for k in ['<0.5R', '0.5-1R', '1-2R', '2-3R', '3-5R', '>5R']:
        cnt = buckets.get(k, 0)
        pct = cnt / len(wins) * 100
        bar = '█' * int(pct / 2)
        print(f"    {k:<12} {cnt:>4}T ({pct:>5.1f}%) {bar}")

    small_wins = buckets.get('<0.5R', 0) + buckets.get('0.5-1R', 0)
    large_wins = buckets.get('>5R', 0) + buckets.get('3-5R', 0)
    if small_wins / len(wins) > 0.50:
        print("    ⚠️  微盈(<1R)占 >50% → 利润被出场机制切碎")
    if large_wins / len(wins) < 0.05:
        print("    ⚠️  大赢(>3R)占 <5% → 没有让利润奔跑")


def report_consecutive_losses(trades):
    """连亏序列分析（不依赖月份）。"""
    sorted_t = sorted(trades, key=lambda t: t.get('exit_time', ''))
    cur = 0
    runs = []
    max_cl = 0
    for t in sorted_t:
        if t['pnl'] < 0:
            cur += 1
            max_cl = max(max_cl, cur)
        else:
            if cur > 0:
                runs.append(cur)
            cur = 0
    if cur > 0:
        runs.append(cur)

    if runs:
        import statistics
        print(f"\n  连亏序列: MaxCL={max_cl}, 连亏次数={len(runs)}, "
              f"avg连亏长={statistics.mean(runs):.1f}")
        print(f"    最长的连亏簇: {sorted(runs, reverse=True)[:5]}")

        # 连亏占比 = 连亏交易数 / 总亏损数
        losses = [t for t in trades if t['pnl'] < 0]
        cl_trades = sum(runs)
        print(f"    连亏交易占总亏损: {cl_trades}/{len(losses)} ({cl_trades/len(losses)*100:.0f}%)")
    else:
        print(f"\n  连亏序列: 无")


# ===== MAIN =====
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python analyze_losses.py <MT5_HTML报告路径> [更多报告...]")
        sys.exit(1)

    all_trades = []
    for path in sys.argv[1:]:
        p = Path(path)
        if p.exists():
            t = parse_trades(p)
            all_trades.extend(t)
            print(f"[{p.name}] {len(t)} 笔交易")
        else:
            print(f"[{p.name}] 文件不存在")

    if not all_trades:
        print("没有交易数据。")
        sys.exit(1)

    total = len(all_trades)
    wins = [t for t in all_trades if t['pnl'] > 0]
    losses = [t for t in all_trades if t['pnl'] < 0]
    wr = len(wins) / total * 100 if total else 0
    gw = sum(t['pnl'] for t in wins) if wins else 0
    gl = abs(sum(t['pnl'] for t in losses)) if losses else 0
    pf = gw / gl if gl > 0 else (999 if gw > 0 else 0)

    print(f"\n{'='*60}")
    print(f"  订单级诊断报告（{total}笔交易）")
    print(f"{'='*60}")
    print(f"  WR={wr:.1f}%  PF={pf:.2f}  PnL=${sum(t['pnl'] for t in all_trades):.2f}")

    report_exit_reasons(all_trades)
    report_hold_time(all_trades)
    report_wl_ratio(all_trades)
    report_r_multiple_distribution(all_trades)
    report_consecutive_losses(all_trades)

    print(f"\n[DONE]")
