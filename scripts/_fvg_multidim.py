"""Multi-dimensional FVG trade analysis for experiment design."""
import re, sys
from pathlib import Path
from collections import defaultdict

PROJECT = Path('D:/Code/codexProject/WaiTrade2')
MT5 = PROJECT / 'temp' / 'mt5_portable_xau'

def parse_trades(htm_path):
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
            trade_type = clean[3].strip()
            size = float(clean[5].strip().replace(' ','').replace(',',''))
            price = float(clean[6].strip().replace(' ','').replace(',',''))
            pnl = float(clean[10].strip().replace(' ','').replace(',',''))
            comment = clean[12].strip() if len(clean) > 12 else ''
        except (ValueError, IndexError): continue
        if io == 'in':
            pending.append({'time': time_str, 'type': trade_type, 'size': size, 'price': price, 'comment': comment})
        elif io == 'out' and pending:
            entry = pending.pop(0)
            entry['pnl'] = pnl
            # 注释信息来自入场(entry['comment']), 而非退出(当前行的comment)
            mult_match = re.search(r'x([\d.]+)', entry.get('comment',''))
            entry['pos_mult'] = float(mult_match.group(1)) if mult_match else 0
            entry['is_fvg'] = 'FVG' in entry.get('comment','')
            entry['is_fade'] = 'Fade' in entry.get('comment','')
            trades.append(entry)
    return trades

# ── Collect all FVG trades across 5 months ──
MONTHS = ['2601','2602','2603','2604','2605']
all_trades = []
for mk in MONTHS:
    for config in ['base', 'fvg']:
        path = MT5 / f'fvg_{config}_{mk}.htm'
        trades = parse_trades(path)
        for t in trades:
            t['month'] = mk
            t['config'] = config
        all_trades.extend(trades)

fvg_trades = [t for t in all_trades if t['is_fvg']]
base_trades = [t for t in all_trades if t['config'] == 'base']
non_fvg = [t for t in all_trades if t['config'] == 'fvg' and not t['is_fvg']]

print('=' * 100)
print('  多维度 FVG 交易特征分析')
print('=' * 100)

# ── Dimension 1: Gap/Lot estimation from trade data ──
# We can't directly see gap size from trade data, but we can estimate from position sizing
print('\n【维度1: 仓位与盈亏关系】')
fvg_pnl_by_size = defaultdict(lambda: {'count':0, 'pnl':0.0, 'wins':0})
for t in fvg_trades:
    s = round(t['size'], 2)
    fvg_pnl_by_size[s]['count'] += 1
    fvg_pnl_by_size[s]['pnl'] += t['pnl']
    if t['pnl'] > 0: fvg_pnl_by_size[s]['wins'] += 1

print(f'  {"仓位":<10} {"笔数":>6} {"PnL":>10} {"WR":>7} {"均PnL":>8}')
for s in sorted(fvg_pnl_by_size.keys()):
    d = fvg_pnl_by_size[s]
    wr = d['wins']/d['count']*100 if d['count'] else 0
    print(f'  {s:<10.4f} {d["count"]:>6} ${d["pnl"]:>+9.2f} {wr:>6.1f}% ${d["pnl"]/d["count"]:>+7.2f}')

# ── Dimension 2: pos_mult vs PnL ──
print('\n【维度2: 仓位乘数与盈亏关系】')
mult_pnl = defaultdict(lambda: {'count':0, 'pnl':0.0, 'wins':0})
for t in fvg_trades:
    m = round(t['pos_mult'], 1)
    mult_pnl[m]['count'] += 1
    mult_pnl[m]['pnl'] += t['pnl']
    if t['pnl'] > 0: mult_pnl[m]['wins'] += 1

print(f'  {"pos_mult":<10} {"笔数":>6} {"PnL":>10} {"WR":>7}')
for m in sorted(mult_pnl.keys()):
    d = mult_pnl[m]
    wr = d['wins']/d['count']*100 if d['count'] else 0
    print(f'  {m:<10.1f} {d["count"]:>6} ${d["pnl"]:>+9.2f} {wr:>6.1f}%')

# ── Dimension 3: Direction × Month matrix ──
print('\n【维度3: 方向×月份 矩阵】')
print(f'  {"月份":<8} {"做多笔数":>8} {"做多PnL":>10} {"做多WR":>7} {"做空笔数":>8} {"做空PnL":>10} {"做空WR":>7} {"多空差":>10}')
for mk in MONTHS:
    mkt = [t for t in fvg_trades if t['month'] == mk]
    buy_t = [t for t in mkt if t['type'] == 'buy']
    sell_t = [t for t in mkt if t['type'] == 'sell']
    bwr = sum(1 for t in buy_t if t['pnl']>0)/len(buy_t)*100 if buy_t else 0
    swr = sum(1 for t in sell_t if t['pnl']>0)/len(sell_t)*100 if sell_t else 0
    bp = sum(t['pnl'] for t in buy_t)
    sp = sum(t['pnl'] for t in sell_t)
    print(f'  20{mk[:2]}.{mk[2:]} {len(buy_t):>8} ${bp:>+9.2f} {bwr:>6.1f}% {len(sell_t):>8} ${sp:>+9.2f} {swr:>6.1f}% ${bp-sp:>+9.2f}')

# ── Dimension 4: Hour × Direction matrix ──
print('\n【维度4: 时段×方向 盈利矩阵 (UTC)】')
hour_dir_pnl = defaultdict(lambda: defaultdict(float))
hour_dir_count = defaultdict(lambda: defaultdict(int))
for t in fvg_trades:
    try:
        h = int(t['time'].split(':')[0].split()[-1])
        d = 'long' if t['type'] == 'buy' else 'short'
        hour_dir_pnl[h][d] += t['pnl']
        hour_dir_count[h][d] += 1
    except: pass

print(f'  {"时段":<8} {"做多笔":>6} {"做多$":>10} {"做空笔":>6} {"做空$":>10} {"净差":>10}')
for h in sorted(hour_dir_pnl.keys()):
    lc = hour_dir_count[h]['long']; ls = hour_dir_pnl[h]['long']
    sc = hour_dir_count[h]['short']; ss = hour_dir_pnl[h]['short']
    print(f'  {h:02d}:00   {lc:>6} ${ls:>+9.2f} {sc:>6} ${ss:>+9.2f} ${ls-ss:>+9.2f}')

# ── Dimension 5: Fade vs Follow ──
print('\n【维度5: Fade(震荡反向) vs Follow(趋势顺向)】')
fade_t = [t for t in fvg_trades if t['is_fade']]
follow_t = [t for t in fvg_trades if not t['is_fade']]
fw = sum(1 for t in fade_t if t['pnl']>0)/len(fade_t)*100 if fade_t else 0
fl = sum(1 for t in follow_t if t['pnl']>0)/len(follow_t)*100 if follow_t else 0
print(f'  Fade:  {len(fade_t)}笔 ${sum(t["pnl"] for t in fade_t):+.2f} WR={fw:.1f}%')
print(f'  Follow:{len(follow_t)}笔 ${sum(t["pnl"] for t in follow_t):+.2f} WR={fl:.1f}%')

# ── Dimension 6: Consecutive loss streaks ──
print('\n【维度6: 连续亏损分析】')
# Sort all FVG trades by time
all_fvg_sorted = sorted(fvg_trades, key=lambda t: (t['month'], t['time']))
streaks = []
current = 0
current_month = None
monthly_streaks = defaultdict(list)
for t in all_fvg_sorted:
    if current_month != t['month']:
        if current != 0: streaks.append(current)
        current = 0
        current_month = t['month']
    if t['pnl'] > 0:
        if current < 0: streaks.append(current); monthly_streaks[current_month].append(current); current = 0
        current += 1
    else:
        if current > 0: streaks.append(current); monthly_streaks[current_month].append(current); current = 0
        current -= 1
if current != 0: streaks.append(current); monthly_streaks[current_month].append(current)

win_streaks = [s for s in streaks if s > 0]
loss_streaks = [s for s in streaks if s < 0]
print(f'  总赢连: {len(win_streaks)} 平均: {sum(win_streaks)/len(win_streaks):.1f} 最大: {max(win_streaks) if win_streaks else 0}')
print(f'  总亏连: {len(loss_streaks)} 平均: {sum(abs(s) for s in loss_streaks)/len(loss_streaks):.1f} 最大: {max(abs(s) for s in loss_streaks) if loss_streaks else 0}')

# Monthly max loss streak
for mk in MONTHS:
    ls = monthly_streaks.get(mk, [])
    neg = [abs(s) for s in ls if s < 0]
    if neg:
        print(f'  20{mk[:2]}.{mk[2:]}: 最大亏连={max(neg)} 次')

# ── Dimension 7: Base vs FVG configuration comparison for NON-FVG trades ──
print('\n【维度7: EntryEngine禁用影响 — 基准(无FVG) vs FVG运行中的非FVG交易】')
base_stats_by_month = {}
for mk in MONTHS:
    bt = [t for t in base_trades if t['month'] == mk]
    nt = [t for t in non_fvg if t['month'] == mk]
    bwr = sum(1 for t in bt if t['pnl']>0)/len(bt)*100 if bt else 0
    nwr = sum(1 for t in nt if t['pnl']>0)/len(nt)*100 if nt else 0
    bp = sum(t['pnl'] for t in bt)
    np = sum(t['pnl'] for t in nt)
    print(f'  20{mk[:2]}.{mk[2:]}: 基准 {len(bt)}笔 ${bp:+.2f} WR={bwr:.1f}% | FVG-非FVG {len(nt)}笔 ${np:+.2f} WR={nwr:.1f}%')

# ── Dimension 8: PnL distribution by config ──
print('\n【维度8: PnL分布 — 基准 vs FVG标记】')
for label, trades in [('基准', base_trades), ('FVG标记', fvg_trades)]:
    dist = defaultdict(int)
    for t in trades:
        p = t['pnl']
        if p < -50: dist['<-$50'] += 1
        elif p < -15: dist['-$50~-15'] += 1
        elif p < -5: dist['-$15~-5'] += 1
        elif p < -1: dist['-$5~-1'] += 1
        elif p < 0: dist['-$1~0'] += 1
        elif p < 1: dist['$0~1'] += 1
        elif p < 5: dist['$1~5'] += 1
        elif p < 15: dist['$5~15'] += 1
        elif p < 50: dist['$15~50'] += 1
        else: dist['>$50'] += 1
    print(f'  {label}: {dict(sorted(dist.items(), key=lambda x: float(x[0].replace("$","").replace("<","-").replace(">","").split("~")[0]) ))}')
