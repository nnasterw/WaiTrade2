import re
from pathlib import Path

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
htm = DATA / 'phase2_mtf-off.htm'
raw = htm.read_bytes()
html = raw.decode('utf-16-le', errors='replace')

all_rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)

# Show first 5 rows with 13 cells (deals)
count = 0
for r in all_rows:
    cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
    if len(cells) == 13:
        print(f"13-cell: {cells}")
        count += 1
        if count >= 5:
            break

# Show first 5 rows with 11 cells (orders)
print("\n---")
count = 0
for r in all_rows:
    cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
    if len(cells) == 11:
        print(f"11-cell: {cells}")
        count += 1
        if count >= 5:
            break
