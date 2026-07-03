"""Debug HTML report cell contents."""
import re
from collections import Counter
html = open(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/nkss_REF_OFF_2505.htm', 'rb').read().decode('utf-16-le', errors='replace')
rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
print(f"Found {len(rows)} data rows")
cell_counts = Counter()
for r in rows:
    cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
    cell_counts[len(cells)] += 1
print(f"Cell count distribution: {dict(cell_counts)}")

# Print sample of 11-cell rows (Orders)
print("\n=== 11-cell rows (Orders) ===")
for r in rows:
    cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
    if len(cells) == 11:
        print(f"  [0]={cells[0].strip()[:40]}  [1]={cells[1].strip()[:40]}  [3]={cells[3].strip()[:40]}  [4]={cells[4].strip()[:40]}  [5]={cells[5].strip()[:40]}")
        break

# Print sample of 13-cell rows (Deals/Trades)
print("\n=== 13-cell rows (Deals) ===")
count = 0
for r in rows:
    cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
    if len(cells) == 13:
        print(f"Row {count}:")
        for j in range(13):
            print(f"  [{j}] = {cells[j].strip()[:60]}")
        count += 1
        if count >= 3: break

