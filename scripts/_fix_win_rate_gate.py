from pathlib import Path
p = Path(r"D:\Code\codexProject\WaiTrade2\scripts\wfys_score.py")
content = p.read_text(encoding="utf-8")
old = "        '720d胜率': cont['trade_count'] is not None and cont['trade_count'] > 0 and (sum(1 for t in metrics.get('trades', []) if t.get('pnl', 0) > 0) / cont['trade_count']) >= HARD_GATES['win_rate_min'] if False else False,  # placeholder"
new = "        '720d胜率': r_metrics.get('win_rate') is not None and r_metrics['win_rate'] >= HARD_GATES['win_rate_min'],"
if old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    print("Fixed win_rate gate")
else:
    print("Placeholder not found")
