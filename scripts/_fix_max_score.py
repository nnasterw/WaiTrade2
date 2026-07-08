from pathlib import Path
p = Path(r"D:\Code\codexProject\WaiTrade2\scripts\wfys_score.py")
content = p.read_text(encoding="utf-8")
old = "                max_score = {'720d回撤': 8.0, 'Recovery Factor': 7.0, 'Profit Factor': 5.0, 'Sharpe/Sortino/Calmar': 5.0}[part_name]"
new = "                max_score = {'720d回撤': 8.0, 'Recovery Factor': 7.0, 'Profit Factor': 5.0, '720d周均单数': 2.0, '720d胜率': 2.0, '720d盈亏比': 1.0}[part_name]"
if old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    print("Fixed max_score dict")
else:
    print("Not found")
