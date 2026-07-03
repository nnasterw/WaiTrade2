import re
from pathlib import Path
DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
htm = DATA / 'p4_jan_off.htm'
raw = htm.read_bytes()
html = raw.decode('utf-16-le', errors='replace')
rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
print(f'Found {len(rows)} trade rows')
for i, r in enumerate(rows[:3]):
    cells = re.findall(r'<td[^>]*>([^<]*)</td>', r)
    print(f'Row {i}: {len(cells)} cells: {cells[:8]}')
# Count in/out
ins = sum(1 for r in rows if '<td>in</td>' in r)
outs = sum(1 for r in rows if '<td>out</td>' in r)
print(f'in={ins} out={outs}')
