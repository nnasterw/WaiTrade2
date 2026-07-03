"""Phase 1: RegimeBoth 2605 订单级诊断 — 遵循 wf-analyze-cl 工作流
提取: 持仓时长/出口原因/趋势对齐/仓位/盈亏强度 — 全部是实时可观测特征
"""
import re, sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta

MT5 = Path('D:/Code/codexProject/WaiTrade2/temp/mt5_portable_xau')

def parse_trades_detail(htm_path):
    """解析MT5报告 — 返回完整trade列表"""
    if not htm_path.exists(): return []
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    trades, pending = [], []
    for r in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
        if len(cells) != 13: continue
        clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        if clean[3] == 'balance': continue
        io = clean[4].strip()
        try:
            time_str = clean[0].strip()
            trade_type = clean[3].strip()  # buy/sell
            size = float(clean[5].strip().replace(' ','').replace(',',''))
            price = float(clean[6].strip().replace(' ','').replace(',',''))
            pnl = float(clean[10].strip().replace(' ','').replace(',',''))
            comment = clean[12].strip() if len(clean) > 12 else ''
        except (ValueError, IndexError): continue
        if io == 'in':
            pending.append({
                'time': time_str, 'type': trade_type, 'size': size,
                'price': price, 'comment': comment
            })
        elif io == 'out' and pending:
            entry = pending.pop(0)
            entry['pnl'] = pnl
            entry['close_time'] = time_str
            entry['close_price'] = price
            # 出口原因从退出comment推断
            exit_comment = comment
            entry['exit_reason'] = classify_exit(exit_comment)
            # 持仓时长
            try:
                t_in = datetime.strptime(entry['time'], '%Y.%m.%d %H:%M:%S')
                t_out = datetime.strptime(entry['close_time'], '%Y.%m.%d %H:%M:%S')
                entry['hold_sec'] = (t_out - t_in).total_seconds()
            except: entry['hold_sec'] = 0
            # pos_mult
            mult_match = re.search(r'x([\d.]+)', entry.get('comment',''))
            entry['pos_mult'] = float(mult_match.group(1)) if mult_match else 1.0
            # 信号类型
            if 'SWP' in entry.get('comment',''): entry['sig_type'] = 'sweep'
            elif 'RB' in entry.get('comment',''): entry['sig_type'] = 'range'
            elif 'HTFPB' in entry.get('comment',''): entry['sig_type'] = 'htf_pullback'
            else: entry['sig_type'] = 'ob'
            trades.append(entry)
    return trades

def classify_exit(comment):
    """从退出注释推断出口原因"""
    c = comment.lower()
    if 'sl' in c and 'sl ' in c: return 'sl'
    if 'be' in c or 'breakeven' in c: return 'be'
    if 'tp' in c: return 'tp'
    if 'dtp' in c: return 'dtp'
    if 'mfe_fail' in c: return 'mfe_fail'
    if 'decay' in c: return 'decay'
    if 'time' in c and 'exit' in c: return 'timeout'
    if 'reverse' in c: return 'reverse'
    return 'unknown'

# ── Phase 1.1: 基础数据 ──
path = MT5 / 'top5_2m_REG3_2605.htm'
trades = parse_trades_detail(path)
print(f'总交易: {len(trades)}')
if not trades:
    # Try alternate path
    for alt in MT5.glob('*.htm'):
        if 'REG3' in alt.name and '2605' in alt.name:
            trades = parse_trades_detail(alt)
            print(f'找到: {alt.name}, {len(trades)}笔')
            break

if not trades:
    print('未找到RegimeBoth 2605报告! 检查文件...')
    for f in sorted(MT5.glob('*.htm')):
        print(f'  {f.name}')
    sys.exit(1)

wins = [t for t in trades if t['pnl'] > 0]
losses = [t for t in trades if t['pnl'] <= 0]
total_pnl = sum(t['pnl'] for t in trades)
avg_w = sum(t['pnl'] for t in wins)/len(wins) if wins else 0
avg_l = sum(t['pnl'] for t in losses)/len(losses) if losses else 0

print(f'\n{"="*80}')
print(f'  Phase 1.1: 基础统计')
print(f'{"="*80}')
print(f'  交易: {len(trades)} | 胜: {len(wins)} | 负: {len(losses)} | WR: {len(wins)/len(trades)*100:.1f}%')
print(f'  总PnL: ${total_pnl:+.2f}')
print(f'  均赢: ${avg_w:+.2f} | 均亏: ${avg_l:+.2f}')
print(f'  W/L比值: {avg_w/abs(avg_l):.2f}' if avg_l != 0 else '  W/L比值: INF')

# ── Phase 1.2: 持仓时长与出口原因 ──
print(f'\n{"="*80}')
print(f'  Phase 1.2: 持仓时长分解 (不按月分组, 纯物理特征)')
print(f'{"="*80}')

hold_buckets = {'<10s': (0,10), '10-60s': (10,60), '1-5min': (60,300),
                '5-30min': (300,1800), '>30min': (1800, 999999)}
print(f'  {"区间":<12} {"笔数":>6} {"占比":>7} {"PnL":>10} {"WR":>7} {"主要出口":>12}')
for name, (lo, hi) in hold_buckets.items():
    subset = [t for t in trades if lo <= t['hold_sec'] < hi]
    if not subset: continue
    swr = sum(1 for t in subset if t['pnl']>0)/len(subset)*100
    spnl = sum(t['pnl'] for t in subset)
    reasons = Counter(t['exit_reason'] for t in subset)
    top_reason = reasons.most_common(1)[0][0] if reasons else '?'
    print(f'  {name:<12} {len(subset):>6} {len(subset)/len(trades)*100:>6.1f}% ${spnl:>+9.2f} {swr:>6.1f}% {top_reason:>12}')

# ── Phase 1.3: 出口原因 × PnL ──
print(f'\n{"="*80}')
print(f'  Phase 1.3: 出口原因分析')
print(f'{"="*80}')
exit_stats = defaultdict(lambda: {'count':0, 'pnl':0.0, 'wins':0, 'hold_sum':0.0})
for t in trades:
    er = t['exit_reason']
    exit_stats[er]['count'] += 1
    exit_stats[er]['pnl'] += t['pnl']
    exit_stats[er]['hold_sum'] += t['hold_sec']
    if t['pnl'] > 0: exit_stats[er]['wins'] += 1

print(f'  {"原因":<12} {"笔数":>6} {"占比":>7} {"PnL":>10} {"WR":>7} {"均持":>8}')
for er in sorted(exit_stats.keys(), key=lambda x: exit_stats[x]['count'], reverse=True):
    es = exit_stats[er]
    wr = es['wins']/es['count']*100 if es['count'] else 0
    avg_hold = es['hold_sum']/es['count'] if es['count'] else 0
    print(f'  {er:<12} {es["count"]:>6} {es["count"]/len(trades)*100:>6.1f}% ${es["pnl"]:>+9.2f} {wr:>6.1f}% {avg_hold:>7.0f}s')

# ── Phase 1.4: 信号类型 × PnL ──
print(f'\n{"="*80}')
print(f'  Phase 1.4: 信号类型分析')
print(f'{"="*80}')
sig_stats = defaultdict(lambda: {'count':0, 'pnl':0.0, 'wins':0})
for t in trades:
    st = t['sig_type']
    sig_stats[st]['count'] += 1
    sig_stats[st]['pnl'] += t['pnl']
    if t['pnl'] > 0: sig_stats[st]['wins'] += 1

print(f'  {"类型":<16} {"笔数":>6} {"PnL":>10} {"WR":>7}')
for st in sorted(sig_stats.keys(), key=lambda x: sig_stats[x]['count'], reverse=True):
    ss = sig_stats[st]
    wr = ss['wins']/ss['count']*100 if ss['count'] else 0
    print(f'  {st:<16} {ss["count"]:>6} ${ss["pnl"]:>+9.2f} {wr:>6.1f}%')

# ── Phase 1.5: 盈亏强度比值 ──
print(f'\n{"="*80}')
print(f'  Phase 1.5: 盈亏强度比值 (W/L ratio)')
print(f'{"="*80}')
print(f'  avg_W = ${avg_w:+.2f}')
print(f'  |avg_L| = ${abs(avg_l):.2f}')
wl_ratio = avg_w/abs(avg_l) if avg_l != 0 else float('inf')
print(f'  W/L = {wl_ratio:.2f}')
if wl_ratio < 0.8:
    print(f'  诊断: W/L < 0.8 → 亏损比盈利大 → 数学上负期望（除非胜率极高）')
    print(f'  当前WR={len(wins)/len(trades)*100:.0f}%, 需要的盈亏平衡WR={1/(1+wl_ratio)*100:.0f}%')
elif wl_ratio > 1.5:
    print(f'  诊断: W/L > 1.5 → 盈利单足以覆盖亏损单 → 胜率容忍度高')
else:
    print(f'  诊断: W/L ≈ 1 → 盈亏接近 1:1 → 靠胜率赚钱')

# ── Phase 1.6: 盈利单R倍数分布 ──
print(f'\n{"="*80}')
print(f'  Phase 1.6: 盈利单盈亏幅度分布')
print(f'{"="*80}')
if wins:
    win_pnls = [t['pnl'] for t in wins]
    loss_pnls = [abs(t['pnl']) for t in losses]
    avg_risk = (sum(win_pnls) + sum(loss_pnls)) / len(trades) if trades else 1
    r_buckets = {'微盈(<0.5R)': 0, '小盈(0.5-1R)': 0, '中盈(1-2R)': 0, '大盈(>2R)': 0}
    for p in win_pnls:
        r = p / avg_risk if avg_risk > 0 else 0
        if r < 0.5: r_buckets['微盈(<0.5R)'] += 1
        elif r < 1: r_buckets['小盈(0.5-1R)'] += 1
        elif r < 2: r_buckets['中盈(1-2R)'] += 1
        else: r_buckets['大盈(>2R)'] += 1
    for name, cnt in r_buckets.items():
        print(f'  {name}: {cnt} ({cnt/len(wins)*100:.0f}% of wins)')

    # 微盈占比诊断
    micro_pct = r_buckets['微盈(<0.5R)'] / len(wins) * 100
    if micro_pct > 50:
        print(f'  ⚠ 微盈占比 {micro_pct:.0f}% > 50% → 利润被出场机制切碎!')

# ── Phase 1.7: 方向分析 ──
print(f'\n{"="*80}')
print(f'  Phase 1.7: 买卖方向分析')
print(f'{"="*80}')
for d in ['buy', 'sell']:
    subset = [t for t in trades if t['type'] == d]
    if not subset: continue
    swr = sum(1 for t in subset if t['pnl']>0)/len(subset)*100
    spnl = sum(t['pnl'] for t in subset)
    print(f'  {d}: {len(subset)}笔 ${spnl:+.2f} WR={swr:.1f}%')

# ── 交易明细逐笔 ──
print(f'\n{"="*80}')
print(f'  逐笔交易明细 (按时间排序)')
print(f'{"="*80}')
print(f'  {"#":>3} {"入场":<20} {"出场":<20} {"持秒":>6} {"方向":>5} {"PnL":>8} {"原因":>10} {"信号":>12} {"乘数":>5}')
for i, t in enumerate(sorted(trades, key=lambda x: x['time'])):
    print(f'  {i+1:>3} {t["time"]:<20} {t["close_time"]:<20} {t["hold_sec"]:>6.0f} {t["type"]:>5} ${t["pnl"]:>+7.2f} {t["exit_reason"]:>10} {t["sig_type"]:>12} x{t["pos_mult"]:.1f}')
