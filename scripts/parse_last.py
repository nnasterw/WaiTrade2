import re
from pathlib import Path
DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
htm = DATA / 'p15_may_realq2.htm'
raw = htm.read_bytes(); html = raw.decode('utf-16-le',errors='replace')
rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
trades = []
for r in rows:
    cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
    if len(cells)==13 and cells[3]!='balance' and cells[4].strip()=='out':
        try: trades.append(float(cells[10].strip()))
        except: pass
wins = [t for t in trades if t>0]; losses = [t for t in trades if t<0]
print(f'{len(trades)}T, {len(wins)}W/{len(losses)}L, PnL=${sum(trades):.2f}')
