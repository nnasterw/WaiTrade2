"""Deep FVG trade analysis — compare base vs FVG, isolate FVG-labeled trades."""
import re, json
from pathlib import Path
from collections import defaultdict, Counter

PROJECT = Path('D:/Code/codexProject/WaiTrade2')
MT5 = PROJECT / 'temp' / 'mt5_portable_xau'

def parse_trades(htm_path):
    """Parse MT5 HTML report — returns list of {time, type, size, price, pnl, comment}"""
    if not htm_path.exists():
        return []
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    trades = []
    pending = []
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
        except (ValueError, IndexError):
            continue
        if io == 'in':
            pending.append({'time': time_str, 'type': trade_type, 'size': size, 'price': price, 'comment': comment})
        elif io == 'out' and pending:
            entry = pending.pop(0)
            entry['pnl'] = pnl
            entry['close_time'] = time_str
            entry['close_price'] = price
            # Preserve the ENTRY comment (not the exit comment)
            trades.append(entry)
    return trades

def analyze(trades, label):
    if not trades: return {'count': 0, 'label': label, 'total_pnl': 0, 'wr': 0, 'pf': 0, 'avg_win': 0, 'avg_loss': 0}
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]
    return {
        'label': label, 'count': len(trades),
        'wins': len(wins), 'losses': len(losses),
        'wr': len(wins)/len(trades)*100,
        'total_pnl': sum(t['pnl'] for t in trades),
        'avg_win': sum(t['pnl'] for t in wins)/len(wins) if wins else 0,
        'avg_loss': sum(t['pnl'] for t in losses)/len(losses) if losses else 0,
        'pf': sum(t['pnl'] for t in wins)/abs(sum(t['pnl'] for t in losses)) if losses else (999 if wins else 0),
        'best': max(t['pnl'] for t in trades) if trades else 0,
        'worst': min(t['pnl'] for t in trades) if trades else 0,
        'avg_size': sum(t['size'] for t in trades)/len(trades),
        'buy_count': sum(1 for t in trades if t['type'] == 'buy'),
        'sell_count': sum(1 for t in trades if t['type'] == 'sell'),
    }

MONTHS = ['2601','2602','2603','2604','2605']

print('=' * 100)
print('  FVG vs 基准 — 逐月交易特征深度对比')
print('=' * 100)

for mk in MONTHS:
    base_t = parse_trades(MT5 / f'fvg_base_{mk}.htm')
    fvg_t = parse_trades(MT5 / f'fvg_fvg_{mk}.htm')

    # Separate FVG-labeled vs non-FVG in the FVG run
    fvg_only = [t for t in fvg_t if 'FVG' in t.get('comment','')]
    non_fvg = [t for t in fvg_t if 'FVG' not in t.get('comment','')]

    bs = analyze(base_t, 'base')
    fs = analyze(fvg_t, 'fvg')
    fo = analyze(fvg_only, 'fvg_only')
    nf = analyze(non_fvg, 'non_fvg')

    print(f'\n{"="*100}')
    print(f'  {mk} — 基准 vs FVG启用')
    print(f'{"="*100}')
    print(f'  {"":<16} {"笔数":>6} {"PnL":>10} {"WR":>7} {"PF":>6} {"均赢":>8} {"均亏":>8}')
    print(f'  {"-"*70}')
    print(f'  {"基准":<16} {bs["count"]:>6} ${bs["total_pnl"]:>+9.2f} {bs["wr"]:>6.1f}% {bs["pf"]:>5.2f} ${bs["avg_win"]:>+7.2f} ${bs["avg_loss"]:>+7.2f}')
    print(f'  {"FVG整体":<16} {fs["count"]:>6} ${fs["total_pnl"]:>+9.2f} {fs["wr"]:>6.1f}% {fs["pf"]:>5.2f} ${fs["avg_win"]:>+7.2f} ${fs["avg_loss"]:>+7.2f}')
    print(f'  {"  └ FVG标记":<16} {fo["count"]:>6} ${fo["total_pnl"]:>+9.2f} {fo["wr"]:>6.1f}% {fo["pf"]:>5.2f} ${fo["avg_win"]:>+7.2f} ${fo["avg_loss"]:>+7.2f}')
    print(f'  {"  └ 非FVG":<16} {nf["count"]:>6} ${nf["total_pnl"]:>+9.2f} {nf["wr"]:>6.1f}% {nf["pf"]:>5.2f} ${nf["avg_win"]:>+7.2f} ${nf["avg_loss"]:>+7.2f}')

    if fo['count'] > 0:
        # FVG trade analysis
        fvg_wins = [t for t in fvg_only if t['pnl'] > 0]
        fvg_losses = [t for t in fvg_only if t['pnl'] < 0]

        # Buy vs Sell
        fvg_buy = [t for t in fvg_only if t['type'] == 'buy']
        fvg_sell = [t for t in fvg_only if t['type'] == 'sell']
        ba = analyze(fvg_buy, 'fvg_buy')
        sa = analyze(fvg_sell, 'fvg_sell')
        print(f'  {"  FVG做多":<16} {ba["count"]:>6} ${ba["total_pnl"]:>+9.2f} {ba["wr"]:>6.1f}% {ba["pf"]:>5.2f}')
        print(f'  {"  FVG做空":<16} {sa["count"]:>6} ${sa["total_pnl"]:>+9.2f} {sa["wr"]:>6.1f}% {sa["pf"]:>5.2f}')

        # PnL distribution
        sizes = Counter()
        for t in fvg_only:
            p = t['pnl']
            if p < -15: sizes['<-$15'] += 1
            elif p < -5: sizes['-$15~-5'] += 1
            elif p < -1: sizes['-$5~-1'] += 1
            elif p < 0: sizes['-$1~0'] += 1
            elif p < 1: sizes['$0~1'] += 1
            elif p < 5: sizes['$1~5'] += 1
            elif p < 15: sizes['$5~15'] += 1
            else: sizes['>$15'] += 1
        print(f'  FVG盈亏分布: {dict(sizes)}')

# ── Cross-month FVG summary ──
print(f'\n\n{"="*100}')
print('  FVG标记交易 — 跨月汇总')
print(f'{"="*100}')
print(f'{"月份":<8} {"FVG笔数":>8} {"FVG_PnL":>10} {"FVG_WR":>7} {"FVG_PF":>7} {"非FVG笔数":>10} {"非FVG_PnL":>10} {"FVG做多":>8} {"FVG做空":>8}')
print('-' * 90)

for mk in MONTHS:
    fvg_t = parse_trades(MT5 / f'fvg_fvg_{mk}.htm')
    fvg_only = [t for t in fvg_t if 'FVG' in t.get('comment','')]
    non_fvg = [t for t in fvg_t if 'FVG' not in t.get('comment','')]
    fo = analyze(fvg_only, 'fvg')
    fn = analyze(non_fvg, 'non_fvg')
    buy_c = sum(1 for t in fvg_only if t['type'] == 'buy')
    sell_c = sum(1 for t in fvg_only if t['type'] == 'sell')
    print(f'20{mk[:2]}.{mk[2:]} {fo["count"]:>8} ${fo["total_pnl"]:>+9.2f} {fo["wr"]:>6.1f}% {fo["pf"]:>6.2f} {fn["count"]:>10} ${fn["total_pnl"]:>+9.2f} {buy_c:>8} {sell_c:>8}')

# Grand total
all_fvg = []
all_nonfvg = []
for mk in MONTHS:
    fvg_t = parse_trades(MT5 / f'fvg_fvg_{mk}.htm')
    all_fvg.extend([t for t in fvg_t if 'FVG' in t.get('comment','')])
    all_nonfvg.extend([t for t in fvg_t if 'FVG' not in t.get('comment','')])

fa = analyze(all_fvg, 'all_fvg')
na = analyze(all_nonfvg, 'all_nonfvg')
print('-' * 90)
print(f'{"合计":<8} {fa["count"]:>8} ${fa["total_pnl"]:>+9.2f} {fa["wr"]:>6.1f}% {fa["pf"]:>6.2f} {na["count"]:>10} ${na["total_pnl"]:>+9.2f}')

if all_fvg:
    # Buy vs Sell breakdown
    fvg_buy_all = [t for t in all_fvg if t['type'] == 'buy']
    fvg_sell_all = [t for t in all_fvg if t['type'] == 'sell']
    ba = analyze(fvg_buy_all, 'all_buy')
    sa = analyze(fvg_sell_all, 'all_sell')
    print(f'\nFVG方向分析:')
    print(f'  做多: {ba["count"]}笔 ${ba["total_pnl"]:+.2f} WR={ba["wr"]:.1f}% PF={ba["pf"]:.2f}')
    print(f'  做空: {sa["count"]}笔 ${sa["total_pnl"]:+.2f} WR={sa["wr"]:.1f}% PF={sa["pf"]:.2f}')

    # Time distribution
    hours = Counter()
    hour_pnl = defaultdict(float)
    for t in all_fvg:
        try:
            h = int(t['time'].split(':')[0].split()[-1]) if ':' in t['time'] else 0
            hours[h] += 1
            hour_pnl[h] += t['pnl']
        except: pass
    print(f'\nFVG时段分布 (UTC):')
    for h in sorted(hours.keys()):
        bar = '█' * (hours[h] // 5)
        print(f'  {h:02d}:00 {hours[h]:>5d}笔 ${hour_pnl[h]:>+8.2f} {bar}')
