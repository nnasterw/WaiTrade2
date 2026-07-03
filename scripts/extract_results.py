#!/usr/bin/env python3
"""Extract results from MT5 HTML reports by parsing trade list."""
from pathlib import Path
import re

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')

def max_consecutive(values, condition):
    max_c = cur = 0
    for v in values:
        if condition(v):
            cur += 1
            max_c = max(max_c, cur)
        else:
            cur = 0
    return max_c

def extract(htm_path):
    raw = htm_path.read_bytes()
    html = raw.decode('utf-16-le', errors='replace')
    result = {}

    # Trade totals row (last bold values before </table>)
    bold_nums = re.findall(r'<td[^>]*><b>([^<]+)</b></td>', html)
    if len(bold_nums) >= 4:
        result['commission'] = bold_nums[-4].strip()
        result['swap'] = bold_nums[-3].strip()
        result['net_profit'] = bold_nums[-2].strip()
        result['balance'] = bold_nums[-1].strip()

    # Parse all trade rows to extract profits
    all_rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    trade_profits = []
    for row_html in all_rows:
        cells = re.findall(r'<td[^>]*>([^<]*)</td>', row_html)
        if len(cells) >= 11 and cells[4].strip() == 'out':
            try:
                p = float(cells[10].strip())
                trade_profits.append(p)
            except:
                pass

    result['total_out_trades'] = str(len(trade_profits))
    wins = [p for p in trade_profits if p > 0]
    losses = [p for p in trade_profits if p < 0]
    result['wins'] = str(len(wins))
    result['losses'] = str(len(losses))
    if wins: result['avg_win'] = f'{sum(wins)/len(wins):.2f}'
    if losses: result['avg_loss'] = f'{sum(losses)/len(losses):.2f}'
    if trade_profits: result['total_pnl'] = f'{sum(trade_profits):.2f}'
    result['max_consecutive_losses'] = str(max_consecutive(trade_profits, lambda x: x < 0))
    result['gross_profit'] = f'{sum(wins):.2f}' if wins else '0.00'
    result['gross_loss'] = f'{sum(abs(l) for l in losses):.2f}' if losses else '0.00'
    if trade_profits: result['win_rate'] = f'{len(wins)/len(trade_profits)*100:.1f}%'
    if losses and sum(abs(l) for l in losses) > 0:
        result['pf'] = f'{sum(wins)/sum(abs(l) for l in losses):.2f}'
    elif wins: result['pf'] = 'inf'
    else: result['pf'] = '0.00'

    return result

# Parse all tests
all_tests = {
    'Phase2 (Bad: 2026.05.22-30)': [
        'phase2_mtf-off', 'phase2_mtf-all', 'phase2_mtf-r5', 'phase2_mtf-r4', 'phase2_mtf-r1b'
    ],
    'Phase3 (Good: 2025.10.01-07)': [
        'phase3_mtf-off', 'phase3_mtf-all'
    ],
}

for section, tests in all_tests.items():
    results = {}
    for test in tests:
        htm = DATA / f'{test}.htm'
        if htm.exists():
            results[test] = extract(htm)

    print(f"\n=== {section} ===")
    print(f"{'Test':<22} {'Trades':>6} {'W':>4} {'L':>4} {'WR%':>7} {'Net$':>8} {'Balance':>10} {'PF':>6} {'Gross+':>8} {'Gross-':>8} {'AvgW':>7} {'AvgL':>7} {'MaxCL':>6}")
    print("-"*120)
    for test in tests:
        r = results.get(test, {})
        label = test.replace('phase2_mtf-', '').replace('phase3_mtf-', '')
        print(f'{label:<22} {r.get("total_out_trades","?"):>6} {r.get("wins","?"):>4} {r.get("losses","?"):>4} '
              f'{r.get("win_rate","?"):>7} {r.get("total_pnl","?"):>8} {r.get("balance","?"):>10} '
              f'{r.get("pf","?"):>6} {r.get("gross_profit","?"):>8} {r.get("gross_loss","?"):>8} '
              f'{r.get("avg_win","?"):>7} {r.get("avg_loss","?"):>7} {r.get("max_consecutive_losses","?"):>6}')
