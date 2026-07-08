from pathlib import Path
p = Path(r"D:\Code\codexProject\WaiTrade2\scripts\wfys_score.py")
content = p.read_text(encoding="utf-8")
# Update key fields
old1 = "'profitable_months_min': 21,"
new1 = "'profitable_months_min': 22,  # v2.0: 21->22"
old2 = "'loss_months_max': 3,"
new2 = "'loss_months_max': 2,  # v2.0: 3->2"
old3 = "'micro_win_ratio_max': 0.55,\n}"
new3 = "'micro_win_ratio_max': 0.55,\n    # WFYS v2.0: 3 new 720d hard gates\n    'weekly_trades_min': 2.0,    # v2.0: week avg >= 2 trades\n    'win_rate_min': 0.35,           # v2.0: win rate >= 35%\n    'avg_win_loss_v2_min': 3.0,    # v2.0: avg_W/|avg_L| >= 3.0\n}"
for old, new in [(old1, new1), (old2, new2), (old3, new3)]:
    if old in content:
        content = content.replace(old, new, 1)
        print("Replaced:", old[:50])
    else:
        print("Not found:", old[:50])
p.write_text(content, encoding="utf-8")
print("Saved")
