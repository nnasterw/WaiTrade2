#!/usr/bin/env python3
"""Parse Phase 2 HTML backtest reports (UTF-16LE encoded)."""
import re
from pathlib import Path

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
TESTS = ['phase2_mtf-off', 'phase2_mtf-all', 'phase2_mtf-r5', 'phase2_mtf-r4', 'phase2_mtf-r1b']

def read_htm(path):
    """Read UTF-16LE encoded HTML report."""
    raw = path.read_bytes()
    # MT5 reports are UTF-16LE
    try:
        return raw.decode('utf-16-le')
    except:
        return raw.decode('utf-8', errors='replace')

def parse_mt5_report(html):
    """Extract metrics from MT5 HTML report using text-based patterns."""
    result = {}

    # Key patterns (MT5 reports have labels followed by values)
    patterns = {
        'balance': r'Final balance[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'net_profit': r'Total net profit[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'gross_profit': r'Gross profit[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'gross_loss': r'Gross loss[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'pf': r'Profit[-\s]factor[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'dd': r'Maximal drawdown[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'dd_abs': r'Balance drawdown absolute[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'sharpe': r'Sharpe ratio[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'payoff': r'Expected payoff[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'trades': r'Total trades[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'win_rate': r'Profit trades[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'loss_trades': r'Loss trades[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'short_pct': r'Short positions[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'long_pct': r'Long positions[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'consecutive_loss': r'consecutive losses[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'largest_loss': r'Largest[-\s]loss[-\s]trade[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'largest_win': r'Largest[-\s]profit[-\s]trade[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'avg_win': r'Average profit trade[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'avg_loss': r'Average loss trade[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
        'model': r'Model[:\s]*<[^>]*>\s*<[^>]*>\s*<[^>]*>\s*<[^>]*>([^<]+)',
    }

    for key, pat in patterns.items():
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # Clean HTML entities
            val = val.replace('&nbsp;', ' ').strip()
            result[key] = val
        else:
            result[key] = '-'

    return result

def main():
    # Print summary table
    print(f"{'Test':<20} {'Trades':>6} {'NetProfit':>12} {'Balance':>10} {'PF':>6} {'DD%':>8} {'WR%':>7} {'Payoff':>10} {'MaxConLoss':>10}")
    print('-' * 90)

    for test in TESTS:
        htm = DATA / f'{test}.htm'
        if not htm.exists():
            print(f'{test:<20} NO REPORT')
            continue

        html = read_htm(htm)
        r = parse_mt5_report(html)

        label = test.replace('phase2_', '')
        print(f'{label:<20} {r["trades"]:>6} {r["net_profit"]:>12} {r["balance"]:>10} '
              f'{r["pf"]:>6} {r["dd"]:>8} {r["win_rate"]:>7} {r["payoff"]:>10} {r["consecutive_loss"]:>10}')

    # Second table: gross detail
    print(f'\n{"Test":<20} {"GrossProfit":>12} {"GrossLoss":>12} {"AvgWin":>10} {"AvgLoss":>10} {"LrgWin":>10} {"LrgLoss":>10}')
    print('-' * 85)
    for test in TESTS:
        htm = DATA / f'{test}.htm'
        if not htm.exists():
            continue
        html = read_htm(htm)
        r = parse_mt5_report(html)
        label = test.replace('phase2_', '')
        print(f'{label:<20} {r["gross_profit"]:>12} {r["gross_loss"]:>12} '
              f'{r["avg_win"]:>10} {r["avg_loss"]:>10} {r["largest_win"]:>10} {r["largest_loss"]:>10}')

if __name__ == '__main__':
    main()
