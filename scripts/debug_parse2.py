import re
from pathlib import Path

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')

# Check both Phase 2 (7-day) and Phase 4 (full month) formats
for fname in ['phase2_mtf-off', 'p4_jan_off']:
    htm = DATA / f'{fname}.htm'
    raw = htm.read_bytes()
    html = raw.decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    print(f"\n=== {fname}: {len(rows)} rows ===")
    for i, r in enumerate(rows[:5]):
        cells = re.findall(r'<td[^>]*>([^<]*)</td>', r)
        print(f'Row{i} [{len(cells)}]: {cells}')
    # Find first row with profit != 0
    for i, r in enumerate(rows):
        cells = re.findall(r'<td[^>]*>([^<]*)</td>', r)
        if len(cells) >= 11:
            try:
                p = float(cells[10]) if len(cells) > 10 else 0
                if p != 0:
                    print(f'Non-zero profit row{i}: {cells}')
                    break
            except:
                pass
