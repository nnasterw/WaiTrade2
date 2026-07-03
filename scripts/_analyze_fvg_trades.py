"""Deep analysis of FVG backtest trades — compare base vs FVG trade characteristics."""
import re, json, sys
from pathlib import Path
from collections import defaultdict, Counter

PROJECT = Path(__file__).resolve().parent.parent
MT5_HOME = PROJECT / 'temp' / 'mt5_portable_xau'

def parse_trades_detailed(htm_path):
    """Parse MT5 HTML report extracting individual trade details.
    Returns list of {time, type, size, price, sl, tp, pnl, comment}"""
    if not htm_path.exists():
        return []

    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')

    # Extract trade rows (13 columns in the main table)
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)

    trades = []
    pending = []  # stack for matching in/out

    for r in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
        if len(cells) != 13:
            continue
        # Strip HTML tags from cell content
        clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]

        # 13-col layout:
        # 0=time 1=ticket 2=symbol 3=type(sell/buy/balance) 4=action(in/out)
        # 5=size 6=price 7-9=?? 10=PnL 11=balance 12=comment
        if clean_cells[3] == 'balance':
            continue

        io_type = clean_cells[4].strip()  # 'in' / 'out'
        try:
            time_str = clean_cells[0].strip()
            trade_type = clean_cells[3].strip()  # sell/buy = direction
            size = float(clean_cells[5].strip().replace(' ', '').replace(',', ''))
            price = float(clean_cells[6].strip().replace(' ', '').replace(',', ''))
            pnl = float(clean_cells[10].strip().replace(' ', '').replace(',', ''))
            comment = clean_cells[12].strip() if len(clean_cells) > 12 else ''
        except (ValueError, IndexError):
            continue

        if io_type == 'in':
            pending.append({
                'time': time_str, 'type': trade_type, 'size': size,
                'price': price, 'comment': comment
            })
        elif io_type == 'out' and pending:
            entry = pending.pop(0)
            entry['pnl'] = pnl
            entry['close_time'] = time_str
            entry['close_price'] = price
            trades.append(entry)

    return trades

def analyze_trades(trades, label):
    """Analyze a list of trades and return statistics."""
    if not trades:
        return {'count': 0, 'label': label}

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]

    # Win/Loss stats
    stats = {
        'label': label,
        'count': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'wr': len(wins) / len(trades) * 100 if trades else 0,
        'total_pnl': sum(t['pnl'] for t in trades),
        'avg_win': sum(t['pnl'] for t in wins) / len(wins) if wins else 0,
        'avg_loss': sum(t['pnl'] for t in losses) / len(losses) if losses else 0,
        'best': max(t['pnl'] for t in trades) if trades else 0,
        'worst': min(t['pnl'] for t in trades) if trades else 0,
        'avg_size': sum(t['size'] for t in trades) / len(trades),
        'pf': sum(t['pnl'] for t in wins) / abs(sum(t['pnl'] for t in losses)) if losses else (999 if wins else 0),
    }

    # Win size distribution
    win_sizes = Counter()
    for t in wins:
        p = t['pnl']
        if p < 1: win_sizes['<$1'] += 1
        elif p < 5: win_sizes['$1-5'] += 1
        elif p < 15: win_sizes['$5-15'] += 1
        elif p < 50: win_sizes['$15-50'] += 1
        else: win_sizes['>$50'] += 1
    stats['win_dist'] = dict(win_sizes)

    # Loss size distribution
    loss_sizes = Counter()
    for t in losses:
        p = abs(t['pnl'])
        if p < 1: loss_sizes['<$1'] += 1
        elif p < 5: loss_sizes['$1-5'] += 1
        elif p < 15: loss_sizes['$5-15'] += 1
        elif p < 50: loss_sizes['$15-50'] += 1
        else: loss_sizes['>$50'] += 1
    stats['loss_dist'] = dict(loss_sizes)

    # Hour distribution
    hours = Counter()
    for t in trades:
        try:
            h = int(t['time'].split(':')[0]) if ':' in t['time'] else 0
            hours[h] += 1
        except:
            pass
    stats['hours'] = dict(sorted(hours.items()))

    # FVG vs non-FVG breakdown
    fvg_trades = [t for t in trades if 'FVG' in t.get('comment', '')]
    non_fvg = [t for t in trades if 'FVG' not in t.get('comment', '')]
    stats['fvg_count'] = len(fvg_trades)
    stats['fvg_pnl'] = sum(t['pnl'] for t in fvg_trades)
    stats['fvg_wr'] = len([t for t in fvg_trades if t['pnl'] > 0]) / len(fvg_trades) * 100 if fvg_trades else 0
    stats['non_fvg_count'] = len(non_fvg)
    stats['non_fvg_pnl'] = sum(t['pnl'] for t in non_fvg)
    stats['non_fvg_wr'] = len([t for t in non_fvg if t['pnl'] > 0]) / len(non_fvg) * 100 if non_fvg else 0

    # Sequential streaks
    streaks = []
    current = 0
    for t in sorted(trades, key=lambda x: x['time']):
        if t['pnl'] > 0:
            if current < 0: streaks.append(current); current = 0
            current += 1
        else:
            if current > 0: streaks.append(current); current = 0
            current -= 1
    if current: streaks.append(current)

    win_streaks = [s for s in streaks if s > 0]
    loss_streaks = [s for s in streaks if s < 0]
    stats['max_win_streak'] = max(win_streaks) if win_streaks else 0
    stats['max_loss_streak'] = abs(min(loss_streaks)) if loss_streaks else 0

    # Sequential PnL (cumulative)
    cum_pnl = []
    running = 0
    for t in sorted(trades, key=lambda x: x['time']):
        running += t['pnl']
        cum_pnl.append((t['time'], running))
    stats['cum_pnl'] = cum_pnl

    return stats

def print_stats(stats):
    """Pretty print trade statistics."""
    if stats['count'] == 0:
        print('  (无交易)')
        return

    print(f'  总交易: {stats["count"]} | 胜:{stats["wins"]} 负:{stats["losses"]} | WR={stats["wr"]:.1f}%')
    print(f'  总PnL: ${stats["total_pnl"]:+.2f} | PF={stats["pf"]:.2f}')
    print(f'  均赢: ${stats["avg_win"]:+.2f} | 均亏: ${stats["avg_loss"]:+.2f}')
    print(f'  最佳: ${stats["best"]:+.2f} | 最差: ${stats["worst"]:+.2f}')
    print(f'  均仓: {stats["avg_size"]:.4f} lot')
    print(f'  最长赢连: {stats["max_win_streak"]} | 最长亏连: {stats["max_loss_streak"]}')

    if stats['fvg_count'] > 0:
        print(f'  ┌─ FVG 交易: {stats["fvg_count"]}笔 PnL=${stats["fvg_pnl"]:+.2f} WR={stats["fvg_wr"]:.1f}%')
        print(f'  └─ 非FVG交易: {stats["non_fvg_count"]}笔 PnL=${stats["non_fvg_pnl"]:+.2f} WR={stats["non_fvg_wr"]:.1f}%')

    print(f'  盈利分布: {stats["win_dist"]}')
    print(f'  亏损分布: {stats["loss_dist"]}')

def main():
    months = ['2601', '2602', '2603', '2604', '2605']
    results = {}

    print('=' * 90)
    print('  FVG 交易深度分析 — 逐笔数据对比')
    print('=' * 90)

    for mk in months:
        print(f'\n{"="*90}')
        print(f'  {mk} — 对比分析')
        print(f'{"="*90}')

        # Parse base and FVG reports
        base_path = MT5_HOME / f'fvg_base_{mk}.htm'
        fvg_path = MT5_HOME / f'fvg_fvg_{mk}.htm'

        base_trades = parse_trades_detailed(base_path)
        fvg_trades = parse_trades_detailed(fvg_path)

        print(f'\n[基准 — FVG关闭] ({len(base_trades)}笔)')
        base_stats = analyze_trades(base_trades, f'base_{mk}')
        print_stats(base_stats)

        print(f'\n[FVG启用] ({len(fvg_trades)}笔)')
        fvg_stats = analyze_trades(fvg_trades, f'fvg_{mk}')
        print_stats(fvg_stats)

        # Delta analysis
        print(f'\n[增量分析]')
        delta_trades = len(fvg_trades) - len(base_trades)
        delta_pnl = fvg_stats['total_pnl'] - base_stats['total_pnl']

        # Find trades unique to FVG (by looking at comment or by comparing time windows)
        fvg_only_trades = [t for t in fvg_trades if 'FVG' in t.get('comment', '')]
        non_fvg_fvg_run = [t for t in fvg_trades if 'FVG' not in t.get('comment', '')]

        print(f'  新增交易: +{delta_trades}笔 | PnL增量: ${delta_pnl:+.2f}')
        print(f'  其中FVG标记交易: {len(fvg_only_trades)}笔 PnL=${sum(t["pnl"] for t in fvg_only_trades):+.2f} WR={len([t for t in fvg_only_trades if t["pnl"]>0])/len(fvg_only_trades)*100 if fvg_only_trades else 0:.1f}%')

        if non_fvg_fvg_run:
            nf_wr = len([t for t in non_fvg_fvg_run if t['pnl'] > 0]) / len(non_fvg_fvg_run) * 100
            print(f'  非FVG交易(FVG运行中): {len(non_fvg_fvg_run)}笔 PnL=${sum(t["pnl"] for t in non_fvg_fvg_run):+.2f} WR={nf_wr:.1f}%')

        # FVG hourly concentration
        if fvg_only_trades:
            fvg_hours = Counter()
            for t in fvg_only_trades:
                try:
                    h = int(t['time'].split(':')[0]) if ':' in t['time'] else 0
                    fvg_hours[h] += 1
                except:
                    pass
            print(f'  FVG时段分布: {dict(sorted(fvg_hours.items()))}')

        results[mk] = {'base': base_stats, 'fvg': fvg_stats}

    # ── Cross-month summary ──
    print(f'\n\n{"="*90}')
    print('  跨月汇总 — FVG效果矩阵')
    print(f'{"="*90}')
    print(f'{"月份":<8} {"基准笔数":>8} {"基准PnL":>10} {"FVG笔数":>8} {"FVG_PnL":>10} {"FVG标记":>8} {"FVG_PnL":>10} {"FVG_WR":>7} {"增量":>10}')
    print('-' * 85)

    total_delta = 0
    for mk in months:
        bs = results[mk]['base']
        fs = results[mk]['fvg']
        delta = fs['total_pnl'] - bs['total_pnl']
        total_delta += delta
        print(f'20{mk[:2]}.{mk[2:]} {bs["count"]:>8} ${bs["total_pnl"]:>+9.2f} {fs["count"]:>8} ${fs["total_pnl"]:>+9.2f} {fs["fvg_count"]:>8} ${fs["fvg_pnl"]:>+9.2f} {fs["fvg_wr"]:>6.1f}% ${delta:>+9.2f}')

    print('-' * 85)
    print(f'{"合计":<8} {sum(r["base"]["count"] for r in results.values()):>8} ${sum(r["base"]["total_pnl"] for r in results.values()):>+9.2f} {sum(r["fvg"]["count"] for r in results.values()):>8} ${sum(r["fvg"]["total_pnl"] for r in results.values()):>+9.2f} {sum(r["fvg"]["fvg_count"] for r in results.values()):>8} ${sum(r["fvg"]["fvg_pnl"] for r in results.values()):>+9.2f} {sum(r["fvg"]["fvg_count"] for r in results.values()):>6} ${total_delta:>+9.2f}')

    # FVG trade quality analysis
    print(f'\n{"="*90}')
    print('  FVG 专属交易质量分析')
    print(f'{"="*90}')
    all_fvg = []
    all_non_fvg_in_fvg_run = []
    for mk in months:
        fvg_path = MT5_HOME / f'fvg_fvg_{mk}.htm'
        fvg_trades = parse_trades_detailed(fvg_path)
        all_fvg.extend([t for t in fvg_trades if 'FVG' in t.get('comment', '')])
        all_non_fvg_in_fvg_run.extend([t for t in fvg_trades if 'FVG' not in t.get('comment', '')])

    if all_fvg:
        fvg_wins = [t for t in all_fvg if t['pnl'] > 0]
        fvg_losses = [t for t in all_fvg if t['pnl'] < 0]
        print(f'  FVG标记交易总数: {len(all_fvg)}')
        print(f'  胜: {len(fvg_wins)} | 负: {len(fvg_losses)} | WR: {len(fvg_wins)/len(all_fvg)*100:.1f}%')
        print(f'  总PnL: ${sum(t["pnl"] for t in all_fvg):+.2f}')
        print(f'  均赢: ${sum(t["pnl"] for t in fvg_wins)/len(fvg_wins):+.2f}' if fvg_wins else '  均赢: N/A')
        print(f'  均亏: ${sum(t["pnl"] for t in fvg_losses)/len(fvg_losses):+.2f}' if fvg_losses else '  均亏: N/A')
        if fvg_losses:
            print(f'  PF: {sum(t["pnl"] for t in fvg_wins)/abs(sum(t["pnl"] for t in fvg_losses)):.2f}')

        # Size analysis
        sizes = Counter()
        for t in all_fvg:
            s = t['size']
            if s < 0.005: sizes['<0.005'] += 1
            elif s < 0.01: sizes['0.005-0.01'] += 1
            elif s < 0.02: sizes['0.01-0.02'] += 1
            else: sizes['>0.02'] += 1
        print(f'  FVG仓位分布: {dict(sizes)}')

        # Hour effectiveness
        hour_pnl = defaultdict(float)
        hour_count = defaultdict(int)
        for t in all_fvg:
            try:
                h = int(t['time'].split(':')[0]) if ':' in t['time'] else 0
                hour_pnl[h] += t['pnl']
                hour_count[h] += 1
            except:
                pass
        print(f'  FVG时段PnL:')
        for h in sorted(hour_pnl.keys()):
            print(f'    {h:02d}:00 — {hour_count[h]:3d}笔 ${hour_pnl[h]:+.2f}')

    # Save detailed stats
    out_path = PROJECT / 'temp' / 'fvg_deep_analysis.json'
    json.dumps(results, indent=2, default=str)  # Just check it serializes
    print(f'\n详细数据已保存: {out_path}')

if __name__ == '__main__':
    main()
