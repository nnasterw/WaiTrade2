"""V96b Live 交易深度分析 — 胜率低原因诊断"""
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRADE_LOG = ROOT / "results" / "live" / "mt5_v5_trades.csv"

rows = []
with open(TRADE_LOG, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

print(f"总记录: {len(rows)}")

# CSV 列: 时间,品种,策略周期,方向,手数,结果,评分,详情
# 筛选 v96b
v96b = []
for r in rows:
    profile = r.get('策略周期', r.get('profile', ''))
    if 'v96b' in profile:
        v96b.append(r)
print(f"v96b 记录: {len(v96b)}")

# === 提取盈亏数据 ===
all_pnls = []
for r in v96b:
    detail = r.get('详情', r.get('detail', r.get('comment', '')))
    pnl_match = re.search(r'pnl=([-\d.]+)', detail)
    if not pnl_match:
        continue
    pnl = float(pnl_match.group(1))
    if abs(pnl) < 0.0001:
        continue

    timestamp = r.get('时间', r.get('timestamp', ''))
    symbol = r.get('品种', r.get('symbol', ''))
    direction = r.get('方向', r.get('direction', ''))
    result = r.get('结果', r.get('result', ''))
    score = r.get('评分', r.get('score', ''))

    # 提取止损信息
    sl_match = re.search(r'comment=\[sl ([-\d.]+)\]', detail)
    sl_price = float(sl_match.group(1)) if sl_match else None

    # 出场原因分析
    exit_reason = 'unknown'
    if re.search(r'close_external|MT5 history close', detail):
        if re.search(r'\[sl [-\d.]+\]', detail):
            exit_reason = 'SL止损'
        elif re.search(r'\[tp [-\d.]+\]', detail):
            exit_reason = 'TP止盈'
        else:
            exit_reason = '外部关闭'
    elif 'WaiTrade_time_tp' in detail:
        exit_reason = '时间TP'
    elif 'WaiTrade_trail' in detail:
        exit_reason = 'Trailing止损'
    elif 'WaiTrade_dyn_tp' in detail:
        exit_reason = '动态TP'
    elif 'time_decay' in detail:
        exit_reason = '时间衰减'
    elif 'breakeven' in detail:
        exit_reason = '保本止损'

    # 提取开仓细节
    entry_match = re.search(r'市价=([-\d.]+)', detail)
    entry_price = float(entry_match.group(1)) if entry_match else None

    # 提取止损价格
    stop_match = re.search(r'止损=([-\d.]+)', detail)
    stop_price = float(stop_match.group(1)) if stop_match else None

    all_pnls.append({
        'symbol': symbol,
        'pnl': pnl,
        'direction': direction,
        'result': result,
        'exit_reason': exit_reason,
        'detail': detail[:500],
        'timestamp': timestamp,
        'entry_price': entry_price,
        'stop_price': stop_price,
        'sl_price': sl_price,
        'score': score,
    })

print(f"有效盈亏记录: {len(all_pnls)}")

if not all_pnls:
    print("没有找到 v96b 的盈亏数据，检查是否有其他策略或数据格式问题")
    exit()

# === 胜率统计 ===
total_trades = len(all_pnls)
wins = [t for t in all_pnls if t['pnl'] > 0]
losses = [t for t in all_pnls if t['pnl'] < 0]
win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0

print(f"\n{'='*60}")
print(f"V96b Live 交易胜率分析")
print(f"{'='*60}")
print(f"总交易: {total_trades}")
print(f"盈利: {len(wins)} ({win_rate:.1f}%)")
print(f"亏损: {len(losses)} ({100-win_rate:.1f}%)")
print(f"总盈亏: ${sum(t['pnl'] for t in all_pnls):.2f}")
if wins:
    print(f"平均盈利: ${sum(t['pnl'] for t in wins)/len(wins):.2f}")
if losses:
    print(f"平均亏损: ${sum(t['pnl'] for t in losses)/len(losses):.2f}")
    # 最大亏损
    max_loss = min(t['pnl'] for t in losses)
    print(f"最大亏损: ${max_loss:.2f}")
if wins:
    max_win = max(t['pnl'] for t in wins)
    print(f"最大盈利: ${max_win:.2f}")

# === 出场原因分布 ===
print(f"\n{'='*60}")
print(f"出场原因分析")
print(f"{'='*60}")
exit_cnt = Counter(t['exit_reason'] for t in all_pnls)
for reason, cnt in exit_cnt.most_common():
    by_reason = [t for t in all_pnls if t['exit_reason'] == reason]
    reason_wins = len([t for t in by_reason if t['pnl'] > 0])
    reason_pnl = sum(t['pnl'] for t in by_reason)
    print(f"  {reason}: {cnt}笔 (胜{reason_wins}/{cnt}={reason_wins/cnt*100:.0f}%) 盈亏=${reason_pnl:.2f}")

# === 品种分析 ===
print(f"\n{'='*60}")
print(f"品种分布")
print(f"{'='*60}")
sym_cnt = Counter(t['symbol'] for t in all_pnls)
for sym, cnt in sym_cnt.most_common():
    by_sym = [t for t in all_pnls if t['symbol'] == sym]
    sym_wins = len([t for t in by_sym if t['pnl'] > 0])
    sym_pnl = sum(t['pnl'] for t in by_sym)
    sym_rate = sym_wins/cnt*100 if cnt > 0 else 0
    print(f"  {sym:<14} {cnt:>4}笔  胜率 {sym_rate:5.1f}%  盈亏 ${sym_pnl:>8.2f}")

# === 止损距离分析 ===
print(f"\n{'='*60}")
print(f"止损触发深度分析")
print(f"{'='*60}")
sl_trades = [t for t in all_pnls if t['exit_reason'] == 'SL止损']
if sl_trades:
    sl_rate = len(sl_trades) / total_trades * 100
    sl_pnl = sum(t['pnl'] for t in sl_trades)
    sl_wins = len([t for t in sl_trades if t['pnl'] > 0])
    print(f"止损关闭: {len(sl_trades)}笔 ({sl_rate:.0f}% of total)")
    print(f"  胜率: {sl_wins}/{len(sl_trades)}={sl_wins/len(sl_trades)*100:.0f}%")
    print(f"  盈亏: ${sl_pnl:.2f}")

    # 分析止损距离是否合理
    risks = []
    for t in sl_trades:
        if t['entry_price'] and t['stop_price']:
            risk = abs(t['entry_price'] - t['stop_price'])
            risks.append((t['symbol'], risk, t['pnl']))
    if risks:
        print(f"  止损距离样本 (前10):")
        for sym, risk, pnl in risks[:10]:
            print(f"    {sym}: risk={risk:.5f} pnl=${pnl:.2f}")

# === 时间分析 ===
print(f"\n{'='*60}")
print(f"最近20笔交易时间线")
print(f"{'='*60}")
for t in all_pnls[-20:]:
    emoji = "+" if t['pnl'] > 0 else "-"
    print(f"  {emoji} {t['timestamp'][:19]} {t['symbol']:<12} {t['direction']:<4} PnL=${t['pnl']:>7.2f} {t['exit_reason']}")

# === 回测对比 ===
print(f"\n{'='*60}")
print(f"与回测对比")
print(f"{'='*60}")
print(f"回测结果 (30天, 999/false, M1, XAUUSDm):")
print(f"  总交易: 112, 胜率: 73.2%, 盈利因子: 1.32")
print(f"")
print(f"Live 结果 (12品种, V96b, 999/false):")
print(f"  总交易: {total_trades}, 胜率: {win_rate:.1f}%")
if win_rate < 50:
    print(f"")
    print(f"⚠ 胜率差距: 回测73.2% vs Live {win_rate:.1f}% = 差距{73.2-win_rate:.0f}个百分点")
    print(f"")
    print(f"可能原因分析:")
    print(f"  1. Live交易在行情快速波动时入场偏移过大 → SL被触发")
    print(f"  2. 点差成本 (live真实的bid/ask) 比回测假设高")
    print(f"  3. MT5 EA也管理持仓 → 和Python脚本冲突 → SL被过早移动")
    print(f"  4. 12品种的某些品种 (USDCHF/NZDUSD等) 流动性差 → 滑点大")
    print(f"  5. 当前市场行情不适合M1二推策略 (低波动/区间震荡)")

# === 按小时段分析胜率 ===
print(f"\n{'='*60}")
print(f"按小时段胜率分析")
print(f"{'='*60}")
for hour in range(24):
    hour_label = f"T-{hour:02d}"
    hour_trades = [t for t in all_pnls if t['timestamp'][11:13] == f'{hour:02d}']
    if hour_trades:
        h_wins = len([t for t in hour_trades if t['pnl'] > 0])
        h_pnl = sum(t['pnl'] for t in hour_trades)
        print(f"  {hour:02d}:00: {len(hour_trades)}笔 胜率{h_wins/len(hour_trades)*100:.0f}% 盈亏${h_pnl:.2f}")
