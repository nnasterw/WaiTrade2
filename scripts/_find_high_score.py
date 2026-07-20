import json, os
from pathlib import Path
results = []
for f in Path(r'results/backtest').glob('*_wfys_*.json'):
    try:
        j = json.loads(f.read_text(encoding='utf-8'))
        if j.get('score', {}).get('total_score', 0) >= 85:
            results.append((j['score']['total_score'], f.name, j.get('metrics', {}).get('continuous', {}).get('trade_count', 0), j.get('metrics', {}).get('r_metrics', {}).get('win_rate', 0)))
    except: pass
for s, n, t, w in sorted(results, reverse=True)[:30]:
    print(f'{round(s,2):.2f} {t} {round(w*100,1)}% {n}')
