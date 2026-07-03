#!/usr/bin/env python3
"""
Deep loss analysis for 2026 Jan-May: OFF vs ALL.
Parses 13-cell DEAL rows from MT5 HTML reports.
"""
from pathlib import Path
import re
from collections import Counter
from datetime import datetime

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
MONTHS = ['jan','feb','mar','apr','may']


def parse_trades(htm_path):
    """Parse MT5 HTML report using 13-cell DEAL rows.
    Deal format: time,ticket,symbol,type,in/out,lots,price,order#,comm,swap,profit,balance,comment
    """
    raw = htm_path.read_bytes()
    html = raw.decode('utf-16-le', errors='replace')
    all_rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)

    ins = {}   # order_num -> {time, direction, price}
    outs = []

    for row_html in all_rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html)
        if len(cells) != 13:
            continue
        if cells[3].strip() == 'balance':
            continue

        time_str = cells[0].strip()
        direction = cells[3].strip()
        in_out = cells[4].strip()
        order_num = cells[7].strip()
        profit = cells[10].strip()
        comment = cells[12].strip()

        try:
            dt = datetime.strptime(time_str, '%Y.%m.%d %H:%M:%S')
        except:
            continue

        if in_out == 'in':
            ins[order_num] = {'time': dt, 'direction': direction}
        elif in_out == 'out':
            try:
                profit_val = float(profit)
            except:
                profit_val = 0.0

            entry = ins.get(order_num, {'time': dt, 'direction': direction})
            holding_sec = (dt - entry['time']).total_seconds()

            comment_lower = comment.lower()
            if 'sl ' in comment_lower:
                exit_reason = 'SL'
            elif 'be ' in comment_lower or 'be-' in comment_lower:
                exit_reason = 'BE'
            elif 'tp ' in comment_lower:
                exit_reason = 'TP'
            elif 'dtp ' in comment_lower:
                exit_reason = 'DTP'
            elif 'timeout' in comment_lower:
                exit_reason = 'TIMEOUT'
            elif 'trail' in comment_lower:
                exit_reason = 'TRAIL'
            else:
                exit_reason = 'OTHER'

            outs.append({
                'time': entry['time'],
                'exit_time': dt,
                'direction': direction,
                'profit': profit_val,
                'holding_sec': holding_sec,
                'exit_reason': exit_reason,
                'comment': comment,
            })

    return outs


def analyze(trades, label):
    """Analyze a trade list."""
    losing = [t for t in trades if t['profit'] < 0]
    winning = [t for t in trades if t['profit'] > 0]
    flat_t = [t for t in trades if t['profit'] == 0]

    total = len(trades)
    n_loss = len(losing)
    n_win = len(winning)
    n_flat = len(flat_t)

    if total == 0:
        return {'label': label, 'total': 0, 'n_loss': 0, 'n_win': 0}

    wr = n_win / total * 100 if total > 0 else 0
    total_pnl = sum(t['profit'] for t in trades)
    avg_win = sum(t['profit'] for t in winning) / n_win if n_win > 0 else 0
    avg_loss = sum(t['profit'] for t in losing) / n_loss if n_loss > 0 else 0

    exit_dist = Counter(t['exit_reason'] for t in losing)

    hold_secs = [t['holding_sec'] for t in losing]
    avg_hold = sum(hold_secs) / len(hold_secs) if hold_secs else 0

    buckets = {'<10s':0,'10-30s':0,'30-60s':0,'1-5min':0,'5-15min':0,'15-60min':0,'>60min':0}
    for hs in hold_secs:
        if hs < 10: buckets['<10s'] += 1
        elif hs < 30: buckets['10-30s'] += 1
        elif hs < 60: buckets['30-60s'] += 1
        elif hs < 300: buckets['1-5min'] += 1
        elif hs < 900: buckets['5-15min'] += 1
        elif hs < 3600: buckets['15-60min'] += 1
        else: buckets['>60min'] += 1

    buy_losing = [t for t in losing if t['direction'] == 'buy']
    sell_losing = [t for t in losing if t['direction'] == 'sell']
    n_buy_loss = len(buy_losing)
    n_sell_loss = len(sell_losing)
    avg_buy_l = sum(abs(t['profit']) for t in buy_losing) / n_buy_loss if n_buy_loss > 0 else 0
    avg_sell_l = sum(abs(t['profit']) for t in sell_losing) / n_sell_loss if n_sell_loss > 0 else 0

    # Consecutive losses
    max_cl = cur = 0
    cl_streaks = []
    for t in sorted(trades, key=lambda x: x['time']):
        if t['profit'] < 0:
            cur += 1
        else:
            if cur > 0:
                cl_streaks.append(cur)
            cur = 0
    if cur > 0:
        cl_streaks.append(cur)
    max_cl = max(cl_streaks) if cl_streaks else 0
    streak_dist = Counter(cl_streaks)

    hour_dist = Counter(t['time'].hour for t in losing)

    return {
        'label': label, 'total': total,
        'n_win': n_win, 'n_loss': n_loss, 'n_flat': n_flat,
        'wr': wr, 'total_pnl': total_pnl,
        'avg_win': avg_win, 'avg_loss': avg_loss,
        'exit_dist': exit_dist, 'avg_hold_sec': avg_hold,
        'hold_buckets': buckets,
        'n_buy_loss': n_buy_loss, 'n_sell_loss': n_sell_loss,
        'avg_buy_l': avg_buy_l, 'avg_sell_l': avg_sell_l,
        'max_cl': max_cl, 'streak_dist': streak_dist,
        'hour_dist': hour_dist,
    }


def print_analysis(r):
    """Pretty-print one analysis result."""
    label = r['label']
    nl = r.get('n_loss', 0)
    total = r.get('total', 0)
    if total == 0:
        print(f"\n  {label}: NO TRADES")
        return

    print(f"\n{'='*65}")
    print(f"  {label}: {total}T | {r['n_win']}W/{nl}L/{r['n_flat']}F | WR={r['wr']:.1f}% | PnL=${r['total_pnl']:.2f}")
    print(f"  AvgWin=${r['avg_win']:.2f}  AvgLoss=${r['avg_loss']:.2f}")

    if nl == 0:
        return

    # Exit reasons
    parts = [f"{reason}={count}({count/nl*100:.0f}%)" for reason, count in r['exit_dist'].most_common(4)]
    print(f"  [Exit] " + ' | '.join(parts))

    # Holding time
    parts2 = [f"{bk}={cnt}({cnt/nl*100:.0f}%)" for bk, cnt in r['hold_buckets'].items() if cnt > 0]
    print(f"  [Hold] avg={r['avg_hold_sec']:.0f}s | " + ' '.join(parts2))

    # Direction
    buy_pct = r['n_buy_loss']/nl*100
    print(f"  [Dir] BuyLoss={r['n_buy_loss']}({buy_pct:.0f}%,${r['avg_buy_l']:.2f}) "
          f"SellLoss={r['n_sell_loss']}({100-buy_pct:.0f}%,${r['avg_sell_l']:.2f})")

    # Streaks
    parts3 = [f"{sl}连x{cnt}" for sl, cnt in sorted(r['streak_dist'].items())]
    print(f"  [Streak] MaxCL={r['max_cl']} | " + ' '.join(parts3))

    # Top hours
    top_hrs = r['hour_dist'].most_common(4)
    parts4 = [f"{hr:02d}h={cnt}({cnt/nl*100:.0f}%)" for hr, cnt in top_hrs]
    print(f"  [Hours] " + ' '.join(parts4))


def main():
    # === Part 1: Monthly loss analysis ===
    for month in MONTHS:
        print(f"\n{'#'*65}")
        print(f"#  {month.upper()} 2026")
        print(f"{'#'*65}")
        for cfg in ['off', 'all']:
            htm = DATA / f'p4_{month}_{cfg}.htm'
            if not htm.exists():
                continue
            trades = parse_trades(htm)
            r = analyze(trades, f'{month.upper()}-{cfg.upper()}')
            print_analysis(r)

    # === Part 2: January anomaly ===
    print(f"\n\n{'█'*75}")
    print(f"{'█'*5}  JANUARY ANOMALY: OFF vs ALL comparison")
    print(f"{'█'*75}")

    jan_off = parse_trades(DATA / 'p4_jan_off.htm')
    jan_all = parse_trades(DATA / 'p4_jan_all.htm')

    off_winning = [t for t in jan_off if t['profit'] > 0]
    all_winning = [t for t in jan_all if t['profit'] > 0]
    off_losing = [t for t in jan_off if t['profit'] < 0]
    all_losing = [t for t in jan_all if t['profit'] < 0]

    off_pnl = sum(t['profit'] for t in jan_off)
    all_pnl = sum(t['profit'] for t in jan_all)
    blocked_pnl = off_pnl - all_pnl
    blocked_wins = len(off_winning) - len(all_winning)
    blocked_losses = len(off_losing) - len(all_losing)

    print(f"\n  OFF: {len(jan_off)}T, PnL=${off_pnl:.2f}")
    print(f"  ALL: {len(jan_all)}T, PnL=${all_pnl:.2f}")
    print(f"  BLOCKED: {len(jan_off)-len(jan_all)}T (Wins={blocked_wins}, Losses={blocked_losses}), PnL=${blocked_pnl:+.2f}")

    off_exit = Counter(t['exit_reason'] for t in off_losing)
    all_exit = Counter(t['exit_reason'] for t in all_losing)
    print(f"\n  [Loss exit reasons]")
    for reason in ['SL', 'BE', 'TP', 'DTP', 'TIMEOUT', 'TRAIL', 'OTHER']:
        o = off_exit.get(reason, 0)
        a = all_exit.get(reason, 0)
        print(f"    {reason:<8}: OFF={o:>4}  ALL={a:>4}  blocked={o-a:>+4}")

    # Hourly trade reduction
    off_hr = Counter(t['time'].hour for t in jan_off)
    all_hr = Counter(t['time'].hour for t in jan_all)
    print(f"\n  [Hourly trade cut %]")
    for hr in sorted(set(list(off_hr.keys()) + list(all_hr.keys()))):
        o = off_hr.get(hr, 0)
        a = all_hr.get(hr, 0)
        if o > 0:
            red_pct = (1 - a/o) * 100
            print(f"    {hr:02d}h: {o:>4} -> {a:>4} ({red_pct:>5.0f}% cut)")

    # === Part 3: Cross-month summary ===
    print(f"\n\n{'█'*95}")
    print(f"{'█'*5}  CROSS-MONTH SUMMARY")
    print(f"{'█'*95}")

    hdr = (f"{'Month':<8}{'Cfg':<5}{'Trades':>7}{'Loss':>6}{'SL%':>6}{'BE%':>6}"
           f"{'Hold':>8}{'BuyL%':>7}{'MaxCL':>6}{'AvgL$':>7}{'TopHr':>6}")
    print(hdr)
    print("-" * 70)
    for month in MONTHS:
        for cfg in ['off', 'all']:
            htm = DATA / f'p4_{month}_{cfg}.htm'
            if not htm.exists():
                continue
            trades = parse_trades(htm)
            r = analyze(trades, '')
            nl = r['n_loss']
            if nl == 0:
                continue
            sl_pct = r['exit_dist'].get('SL', 0) / nl * 100
            be_pct = r['exit_dist'].get('BE', 0) / nl * 100
            buy_pct = r['n_buy_loss'] / nl * 100
            top_hr = r['hour_dist'].most_common(1)
            top_h = f"{top_hr[0][0]:02d}h" if top_hr else '-'
            print(f"{month.upper():<8}{cfg:<5}{r['total']:>7}{nl:>6}{sl_pct:>5.0f}%{be_pct:>5.0f}%"
                  f"{r['avg_hold_sec']:>7.0f}s{buy_pct:>6.0f}%{r['max_cl']:>6}${abs(r['avg_loss']):>6.2f}{top_h:>6}")

    # === Part 4: Direction asymmetry ===
    print(f"\n\n[Direction WR asymmetry]")
    print(f"{'Month':<8}{'Cfg':<5}{'BuyWR':>8}{'SellWR':>8}{'Delta':>8}{'BuyT':>6}{'SellT':>6}")
    print("-" * 45)
    for month in MONTHS:
        for cfg in ['off', 'all']:
            htm = DATA / f'p4_{month}_{cfg}.htm'
            if not htm.exists():
                continue
            trades = parse_trades(htm)
            buys = [t for t in trades if t['direction'] == 'buy']
            sells = [t for t in trades if t['direction'] == 'sell']
            buy_wr = len([t for t in buys if t['profit'] > 0]) / len(buys) * 100 if buys else 0
            sell_wr = len([t for t in sells if t['profit'] > 0]) / len(sells) * 100 if sells else 0
            print(f"{month.upper():<8}{cfg:<5}{buy_wr:>7.1f}%{sell_wr:>7.1f}%{buy_wr-sell_wr:>+7.1f}%{len(buys):>6}{len(sells):>6}")

    print(f"\n[DONE]")


if __name__ == '__main__':
    main()
