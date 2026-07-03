import re, os
from pathlib import Path

MT5D = Path(os.path.expandvars(r'%APPDATA%')) / 'MetaQuotes' / 'Terminal' / 'D0E8209F77C8CF37AD8BF550E51FF075'
# Find largest D7D htm file (720d report is ~9MB)
files = [(p.stat().st_size, p) for p in MT5D.glob('v11xau-qs3-d7d*.htm')]
files.sort(reverse=True)
f = files[0][1]
print(f"Using: {f.name} ({f.stat().st_size} bytes)")
raw = f.read_bytes()
text = raw.decode('utf-16-le')
lines = text.split('\n')

trades = 0
wins = 0
losses = 0
for line in lines:
    if 'XAUUSDm' not in line or 'out' not in line:
        continue
    if not re.search(r'<\s*td[^>]*>\s*out\s*<\s*/td\s*>', line, re.IGNORECASE):
        continue
    trades += 1
    clean = re.sub(r'<[^>]+>', ' | ', line).strip()
    parts = [p.strip() for p in clean.split('|')]
    non_empty = [p for p in parts if p]
    try:
        sym_idx = non_empty.index('XAUUSDm')
    except ValueError:
        continue
    if sym_idx + 2 >= len(non_empty) or non_empty[sym_idx + 2] != 'out':
        continue
    if len(non_empty) >= 3:
        try:
            profit_val = float(non_empty[-3].replace(' ', ''))
            if profit_val > 0.01:
                wins += 1
            elif profit_val < -0.01:
                losses += 1
        except:
            pass

wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0

balance = None
for i in range(max(0, len(lines)-50), len(lines)):
    clean = re.sub(r'<[^>]+>', ' | ', lines[i]).strip()
    m = re.match(r'^\|\s*\|\s*(-?[\d\s]+[\d.]*\d)\s*\|\s*\|$', clean)
    if m:
        val_str = m.group(1).replace(' ', '').replace('\xa0', '')
        try:
            balance = float(val_str)
        except:
            pass

print(f'D7D 720d: {trades}t {wins}W/{losses}L {wr:.1f}% WR, Balance=${balance:,.2f}' if balance else 'NO BALANCE')
