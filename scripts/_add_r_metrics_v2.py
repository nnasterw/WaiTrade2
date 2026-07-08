from pathlib import Path
p = Path(r"D:\Code\codexProject\WaiTrade2\scripts\wfys_score.py")
content = p.read_text(encoding="utf-8")

# Add win_count, loss_count, total_count to r_metrics
old1 = "        'big_win_ratio': big_wins / float(len(win_rs)),\n        'micro_win_ratio': micro_wins / float(len(win_rs)),\n    }"
new1 = "        'big_win_ratio': big_wins / float(len(win_rs)),\n        'micro_win_ratio': micro_wins / float(len(win_rs)),\n        # v2.0: 720d hard gates support\n        'win_count': len(win_rs),\n        'loss_count': len(valid_r) - len(win_rs),\n        'total_count': len(valid_r),\n        'win_rate': len(win_rs) / float(len(valid_r)) if valid_r else 0.0,\n    }"
if old1 in content:
    content = content.replace(old1, new1, 1)
    p.write_text(content, encoding="utf-8")
    print("Updated r_metrics with v2.0 fields")
else:
    print("Anchor not found")
