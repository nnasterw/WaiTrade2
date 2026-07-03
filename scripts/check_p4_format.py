import re
from pathlib import Path

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
for month in ['jan','feb','mar','apr','may']:
    for cfg in ['off','all']:
        htm = DATA / f'p4_{month}_{cfg}.htm'
        if not htm.exists():
            continue
        raw = htm.read_bytes()
        html = raw.decode('utf-16-le', errors='replace')
        all_rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
        c11 = sum(1 for r in all_rows if len(re.findall(r'<td[^>]*>(.*?)</td>', r)) == 11)
        c13 = sum(1 for r in all_rows if len(re.findall(r'<td[^>]*>(.*?)</td>', r)) == 13)
        # Count deals (13-cell with profit != 0 and type != 'balance')
        deals = 0
        for r in all_rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
            if len(cells) == 13 and cells[3] != 'balance':
                deals += 1
        print(f"{month}-{cfg}: {len(all_rows)} rows, 11c={c11}, 13c={c13}, deals={deals}")
