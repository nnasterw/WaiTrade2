#!/usr/bin/env python3
"""Deep analysis of QS4+NOISE and Q2+NOISE losing trades."""
import re
from pathlib import Path
from collections import Counter

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')

def parse_all(htm_path):
    raw = htm_path.read_bytes()
    html = raw.decode('utf-16-le', errors='replace')
    all_rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)

    ins = {}
    trades = []
    for row_html in all_rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html)
        if len(cells) != 13 or cells[3]=='balance': continue
        dt_str = cells[0].strip()
        direction = cells[3].strip()
        in_out = cells[4].strip()
        order_num = cells[7].strip()
        profit = cells[10].strip()
        comment = cells[12].strip()

        if in_out == 'in':
            ins[order_num] = {'time': dt_str, 'direction': direction}
        elif in_out == 'out':
            try: p = float(profit)
            except: p = 0.0
            entry_info = ins.get(order_num, {'time': dt_str, 'direction': direction})
            reason = 'OTHER'
            cl = comment.lower()
            if 'sl ' in cl: reason = 'SL'
            elif 'be ' in cl: reason = 'BE'
            elif 'tp ' in cl: reason = 'TP'
            elif 'dtp ' in cl: reason = 'DTP'
            elif 'timeout' in cl: reason = 'TIMEOUT'

            trades.append({
                'time': dt_str, 'direction': direction,
                'profit': p, 'exit_reason': reason, 'comment': comment,
            })
    return trades


for label, prefix in [('QS4+NOISE', 'qs4'), ('Q2+NOISE', 'p10')]:
    months_map = {'qs4': {'jan':'jan','feb':'feb','mar':'mar','apr':'apr','may':'may'},
                  'p10': {'jan':'jan','feb':'feb','mar':'mar','apr':'apr','may':'may'}}
    print(f"\n{'='*70}")
    print(f"  {label} — 损失单分析")
    print(f"{'='*70}")

    all_losses = []
    for m in ['jan','feb','mar','apr','may']:
        key = months_map[prefix][m]
        htm = DATA / f'{prefix}_{key}.htm'
        if not htm.exists(): continue
        trades = parse_all(htm)
        losses = [t for t in trades if t['profit'] < 0]
        wins = [t for t in trades if t['profit'] > 0]
        total_pnl = sum(t['profit'] for t in trades)

        if losses:
            avg_l = sum(t['profit'] for t in losses) / len(losses)
            reasons = Counter(t['exit_reason'] for t in losses)
            print(f"\n  {m.upper()}: {len(losses)}L/{len(wins)}W, PnL=${total_pnl:.0f}, avgLoss=${avg_l:.0f}")
            print(f"    Exit: " + ' '.join(f"{r}={c}" for r,c in reasons.most_common()))
            for t in losses:
                all_losses.append(t)
                print(f"    {t['time']} {t['direction']:>4} ${t['profit']:>8.2f} [{t['exit_reason']}] {t['comment'][:60]}")

    if all_losses:
        avg_all = sum(t['profit'] for t in all_losses) / len(all_losses)
        reasons_all = Counter(t['exit_reason'] for t in all_losses)
        print(f"\n  汇总: {len(all_losses)} losses, avg=${avg_all:.0f}")
        print(f"  出口: " + ' '.join(f"{r}={c}" for r,c in reasons_all.most_common()))

print("\n[DONE]")
