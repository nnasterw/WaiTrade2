"""V96b Live 深度分析 — 区分原始SL vs Trailing SL 出场"""
import csv, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRADE_LOG = ROOT / "results" / "live" / "mt5_v5_trades.csv"

rows = []
with open(TRADE_LOG, 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if 'v96b' in r.get('策略周期', ''):
            rows.append(r)

print(f"V96b 记录: {len(rows)}")

trades = []
for r in rows:
    detail = r.get('详情', '')
    pnl_match = re.search(r'pnl=([-\d.]+)', detail)
    if not pnl_match:
        continue
    pnl = float(pnl_match.group(1))
    if abs(pnl) < 0.0001:
        continue

    entry_match = re.search(r'市价=([-\d.]+)', detail)
    stop_match = re.search(r'止损=([-\d.]+)', detail)
    sl_close_match = re.search(r'comment=\[sl ([-\d.]+)\]', detail)

    entry_price = float(entry_match.group(1)) if entry_match else None
    init_sl = float(stop_match.group(1)) if stop_match else None
    final_sl = float(sl_close_match.group(1)) if sl_close_match else None

    direction = r.get('方向', '')
    symbol = r.get('品种', '')
    timestamp = r.get('时间', '')

    if not entry_price or not init_sl:
        continue

    init_risk = abs(entry_price - init_sl)

    # 判断 SL 是否被修改过（trailing生效）
    sl_modified = False
    if final_sl and init_sl:
        if abs(final_sl - init_sl) > init_risk * 0.001:
            sl_modified = True

    # 判断出场类型
    if sl_modified and final_sl:
        if direction == '买入':
            sl_r = (final_sl - entry_price) / init_risk if init_risk > 0 else 0
        else:  # 卖出
            sl_r = (entry_price - final_sl) / init_risk if init_risk > 0 else 0

        if sl_r >= 0.01:
            exit_type = f'Trailing锁利 (SL_at_{sl_r:.2f}R)'
        elif sl_r >= -0.01:
            exit_type = '保本/微盈'
        else:
            exit_type = f'Trailing收紧 (SL_at_{sl_r:.2f}R)'
    else:
        exit_type = '原始SL止损'

    # 计算R倍数
    r_multiple = pnl / (init_risk * 0.01) if init_risk > 0 else 0  # 粗略估计（不知道手数）

    trades.append({
        'timestamp': timestamp,
        'symbol': symbol,
        'direction': direction,
        'pnl': pnl,
        'entry': entry_price,
        'init_sl': init_sl,
        'final_sl': final_sl,
        'init_risk': init_risk,
        'sl_modified': sl_modified,
        'exit_type': exit_type,
        'r_multiple': r_multiple,
    })

print(f"有效交易: {len(trades)}")
print()

# === 按出场类型分类 ===
from collections import Counter
exit_types = Counter(t['exit_type'] for t in trades)
print("出场类型分布:")
for et, cnt in exit_types.most_common():
    by_type = [t for t in trades if t['exit_type'] == et]
    type_wins = len([t for t in by_type if t['pnl'] > 0])
    type_pnl = sum(t['pnl'] for t in by_type)
    print(f"  {et}: {cnt}笔 (胜{type_wins}/{cnt}={type_wins/cnt*100:.0f}%) 盈亏=${type_pnl:.2f}")

# === SL修改 vs 未修改 ===
print()
modified = [t for t in trades if t['sl_modified']]
unmodified = [t for t in trades if not t['sl_modified']]
print(f"SL被修改 (trailing生效): {len(modified)}笔")
if modified:
    m_wins = len([t for t in modified if t['pnl'] > 0])
    m_pnl = sum(t['pnl'] for t in modified)
    print(f"  胜率: {m_wins/len(modified)*100:.0f}%, 盈亏=${m_pnl:.2f}, 平均${m_pnl/len(modified):.2f}")
print(f"SL未被修改 (原始止损): {len(unmodified)}笔")
if unmodified:
    u_wins = len([t for t in unmodified if t['pnl'] > 0])
    u_pnl = sum(t['pnl'] for t in unmodified)
    print(f"  胜率: {u_wins/len(unmodified)*100:.0f}%, 盈亏=${u_pnl:.2f}, 平均${u_pnl/len(unmodified):.2f}")

# === 详细列出每笔交易 ===
print()
print(f"{'='*90}")
print(f"{'时间':<22} {'品种':<12} {'方向':<4} {'入场':>10} {'初始SL':>10} {'最终SL':>10} {'盈亏':>8} {'出场类型'}")
print(f"{'='*90}")
for t in trades:
    entry_s = f"{t['entry']:.3f}" if t['entry'] else 'N/A'
    init_s = f"{t['init_sl']:.3f}" if t['init_sl'] else 'N/A'
    final_s = f"{t['final_sl']:.3f}" if t['final_sl'] else 'N/A'
    print(f"{t['timestamp']:<22} {t['symbol']:<12} {t['direction']:<4} {entry_s:>10} {init_s:>10} {final_s:>10} ${t['pnl']:>7.2f} {t['exit_type']}")

# === 关键发现 ===
print()
print("="*60)
print("关键发现")
print("="*60)
total = len(trades)
wins = len([t for t in trades if t['pnl'] > 0])
losses = len([t for t in trades if t['pnl'] < 0])

# SL修改后仍亏损的（SL追得太紧）
modified_losses = [t for t in modified if t['pnl'] < 0]
print(f"1. SL被修改但最终亏损: {len(modified_losses)}笔 → SL追得太紧/被行情扫到")

# 持仓时间极短
print(f"2. 所有出场都是SL方式 → Python脚本的time_tp/dyn_tp/decay_tp均未触发")
print(f"   原因: 行情未达到这些出场条件之前就被SL触发了")

# 盈亏比失衡
if wins > 0 and losses > 0:
    avg_win = sum(t['pnl'] for t in trades if t['pnl'] > 0) / wins
    avg_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0)) / losses
    print(f"3. 盈亏比: 平均盈利${avg_win:.2f} vs 平均亏损${avg_loss:.2f} = 1:{avg_loss/avg_win:.1f}")
    print(f"   即使胜率50%也需要盈亏比>1才能盈利")

# 大部分是BTC
btc_trades = [t for t in trades if 'BTC' in t['symbol']]
print(f"4. BTCUSDm占比: {len(btc_trades)}/{total}={len(btc_trades)/total*100:.0f}%")
print(f"   BTC盈亏: ${sum(t['pnl'] for t in btc_trades):.2f}")
