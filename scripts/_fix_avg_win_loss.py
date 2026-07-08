from pathlib import Path
p = Path(r"D:\Code\codexProject\WaiTrade2\scripts\wfys_score.py")
content = p.read_text(encoding="utf-8")
old = "        '720d盈亏比': r_metrics['avg_win_loss'] is not None and r_metrics['avg_win_loss'] >= HARD_GATES['avg_win_loss_v2_min'],"
new = "        '720d盈亏比': cont.get('avg_win_loss') is not None and cont['avg_win_loss'] >= HARD_GATES['avg_win_loss_v2_min'],"
if old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    print("Fixed avg_win_loss reference")
else:
    print("Not found")
