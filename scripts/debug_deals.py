import re
from pathlib import Path

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
htm = DATA / 'phase2_mtf-off.htm'
raw = htm.read_bytes()
html = raw.decode('utf-16-le', errors='replace')

# Find the "Results" or "Deals" section header
for tag in ['Deals', 'Results', 'Trades', 'Orders']:
    idx = html.find(tag)
    if idx > 0:
        print(f"Found '{tag}' at pos {idx}")
        # Show surrounding HTML
        print(html[max(0,idx-200):idx+500])
        print("---")

# Find all unique row structures by counting cells
all_rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
cell_counts = {}
for r in all_rows:
    cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
    n = len(cells)
    cell_counts[n] = cell_counts.get(n, 0) + 1
print(f"\nCell count distribution: {sorted(cell_counts.items())}")

# Show samples of each cell count
for n in sorted(cell_counts.keys()):
    for r in all_rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
        if len(cells) == n:
            print(f"\n{cells}")
            break
