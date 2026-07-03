import re
from pathlib import Path
htm = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\p18_qs3_check.htm')
raw = htm.read_bytes()
html = raw.decode('utf-16-le', errors='replace')
rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
trades = []
for r in rows:
    cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
    if len(cells) == 13 and cells[3] != 'balance' and cells[4].strip() == 'out':
        try:
            p = float(cells[10].strip().replace(' ','').replace(',',''))
            trades.append(p)
        except:
            pass
wins = [t for t in trades if t > 0]
losses = [t for t in trades if t < 0]
gw = sum(wins) if wins else 0
gl = abs(sum(losses)) if losses else 0
pf = gw/gl if gl > 0 else 0
wr = len(wins)/len(trades)*100 if trades else 0
print(f'QS3 720d: {len(trades)}T, WR={wr:.1f}%, PF={pf:.2f}, PnL=${sum(trades):.2f}, Bal=${300+sum(trades):.2f}')
print(f'Commit said: QS3 = $313K (likely at $200 deposit)')
print(f'Our QS4 at $300: $253,882')
