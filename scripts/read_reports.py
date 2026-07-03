import re, glob
for f in sorted(glob.glob('results/backtest/v11xau-qs3-h[78]_*.txt')):
    text = open(f, encoding='utf-8').read()
    m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', text)
    if m:
        name = f.split('\\')[-1].replace('.txt','')
        print(f"{name}: {m.group(1)}t WR{m.group(2)}% Bal${m.group(3)}")
