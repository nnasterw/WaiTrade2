#!/usr/bin/env python3
"""Deeper HTML inspection for trade table."""
import sys, re

htm = r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/smc_B_2605.htm'
with open(htm, 'rb') as f:
    raw = f.read()
text = raw.decode('utf-16-le', errors='replace')

# Find all table sections
tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
print(f'Total tables: {len(tables)}')

for ti, table in enumerate(tables):
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
    # Check if this looks like a trades table
    row_text = ' '.join(rows[:3]) if rows else ''
    print(f'\nTable {ti}: {len(rows)} rows')
    for ri, row in enumerate(rows[:3]):
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        vals = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        print(f'  Row {ri}: {len(cells)} cells -> {vals[:8]}')

# Also check using the known MT5 trade report pattern
# MT5 trade rows typically have: #, Time, Type, Order, Size, Price, S/L, T/P, Time, Price, Commission, Swap, Profit
trade_rows = []
for table in tables:
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        vals = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        if len(vals) >= 10:
            # Check if last value looks like profit/loss
            try:
                last = vals[-1].replace(' ','').replace('&nbsp;','')
                if re.match(r'^-?\d+\.?\d*$', last) and float(last) != 0:
                    # Check first value looks like a datetime
                    if re.match(r'\d{4}\.\d{2}\.\d{2}', vals[0]):
                        trade_rows.append(vals)
            except:
                pass

print(f'\n\n=== TRADE ROWS ({len(trade_rows)} found) ===')
for tr in trade_rows[:5]:
    print(f'  {tr}')
if trade_rows:
    print(f'  ...')
    for tr in trade_rows[-3:]:
        print(f'  {tr}')
