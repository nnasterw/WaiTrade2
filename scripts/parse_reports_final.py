#!/usr/bin/env python3
"""Final: parse all 5 MT5 reports properly by looking at the correct table structure."""
from pathlib import Path
import re

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')

def parse_one(htm_path):
    raw = htm_path.read_bytes()
    html = raw.decode('utf-16-le', errors='replace')

    # MT5 report structure:
    # Table 1: Test settings (symbol, period, model, etc.)
    # Table 2: Input parameters (long list)
    # Table 3: Summary results (what we want!)
    # Table 4: Charts
    # Table 5: Trade list
    #
    # The summary table (Table 3) has structure:
    # <tr><td>Label</td><td>Value</td><td>Label</td><td>Value</td>...</tr>

    # Find all <table> tags
    tables = list(re.finditer(r'<table[^>]*>', html, re.I))
    print(f"  Found {len(tables)} tables")

    # Look for the summary table: after input params, before trade list
    # It contains unique labels
    summary_markers = ['Bars in test', 'Ticks modelled', 'Modelling quality',
                       'Initial deposit', 'Total net profit', 'Gross profit',
                       'Gross loss', 'Profit factor', 'Expected payoff',
                       'Absolute drawdown', 'Maximal drawdown',
                       'Total trades', 'Short positions', 'Long positions',
                       'Profit trades', 'Loss trades', 'Largest profit trade',
                       'Largest loss trade', 'Average profit trade',
                       'Average loss trade', 'Maximum consecutive wins',
                       'Maximum consecutive losses', 'Sharpe ratio',
                       'Z-Score', 'AHPR', 'GHPR']

    found = {}
    for marker in summary_markers:
        # Search case-insensitive
        pattern = re.compile(r'(' + re.escape(marker) + r')', re.I)
        m = pattern.search(html)
        if m:
            # Get the value after this label
            # MT5 format: <tr><td>Label</td><td>Value</td>...</tr>
            # Find next <td> after the label
            label_end = m.end()
            # Skip to next <td> with content
            next_td = re.search(r'<td[^>]*>(.*?)</td>', html[label_end:label_end+200], re.I | re.DOTALL)
            if next_td:
                val = re.sub(r'<[^>]+>', '', next_td.group(1)).strip()
                found[marker] = val

    return found

# Parse all reports
reports = {}
for test in ['phase2_mtf-off', 'phase2_mtf-all', 'phase2_mtf-r5', 'phase2_mtf-r4', 'phase2_mtf-r1b']:
    htm = DATA / f'{test}.htm'
    if htm.exists():
        print(f"\nParsing: {test}")
        reports[test] = parse_one(htm)

# Print combined table
print("\n" + "="*120)
header = f"{'Metric':<28}"
for test in reports:
    header += f" {test.replace('phase2_mtf-',''):>12}"
print(header)
print("-"*120)

metrics = ['Total trades', 'Total net profit', 'Gross profit', 'Gross loss',
           'Profit factor', 'Expected payoff', 'Maximal drawdown',
           'Profit trades', 'Loss trades', 'Largest profit trade',
           'Largest loss trade', 'Average profit trade', 'Average loss trade',
           'Maximum consecutive wins', 'Maximum consecutive losses']

for metric in metrics:
    row = f"{metric:<28}"
    for test in reports:
        val = reports[test].get(metric, '-')
        row += f" {val:>12}"
    print(row)
