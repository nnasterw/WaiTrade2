#!/usr/bin/env python3
"""Extract trade data from MT5 table 1."""
import sys, re

htm = r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/smc_B_2605.htm'
with open(htm, 'rb') as f:
    raw = f.read()
text = raw.decode('utf-16-le', errors='replace')

tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
table = tables[1]  # Trade table
rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)

print(f'Table 1: {len(rows)} rows')
for ri, row in enumerate(rows[:30]):
    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
    vals = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
    # Filter empty cells
    non_empty = [v for v in vals if v]
    if non_empty:
        print(f'Row {ri}: {len(vals)} cells, {len(non_empty)} non-empty')
        print(f'  {non_empty[:12]}')

# Also try to find data rows with number in first cell
print('\n=== Data rows ===')
for ri, row in enumerate(rows):
    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
    vals = [re.sub(r'<[^>]+>', '', c).strip() for c in cells if re.sub(r'<[^>]+>', '', c).strip()]
    if vals and re.match(r'^\d+$', vals[0]):
        print(f'Row {ri}: {vals[:12]}')
