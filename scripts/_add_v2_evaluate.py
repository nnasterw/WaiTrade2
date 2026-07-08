from pathlib import Path
p = Path(r"D:\Code\codexProject\WaiTrade2\scripts\wfys_score.py")
content = p.read_text(encoding="utf-8")

# Add new hard gates to evaluate_hard_gates
# 1. Add 720d 周均单数, 胜率, 盈亏比 gates to evaluate_hard_gates
old1 = "        '<0.5R微利单占比': r_metrics['micro_win_ratio'] is not None and r_metrics['micro_win_ratio'] <= HARD_GATES['micro_win_ratio_max'],"
new1 = "        '<0.5R微利单占比': r_metrics['micro_win_ratio'] is not None and r_metrics['micro_win_ratio'] <= HARD_GATES['micro_win_ratio_max'],\n        # WFYS v2.0: 3 new 720d gates (from continuous_report)\n        '720d周均单数': cont['trade_count'] is not None and (cont['trade_count'] / 103.0) >= HARD_GATES['weekly_trades_min'],\n        '720d胜率': cont['trade_count'] is not None and cont['trade_count'] > 0 and (sum(1 for t in metrics.get('trades', []) if t.get('pnl', 0) > 0) / cont['trade_count']) >= HARD_GATES['win_rate_min'] if False else False,  # placeholder\n        '720d盈亏比': r_metrics['avg_win_loss'] is not None and r_metrics['avg_win_loss'] >= HARD_GATES['avg_win_loss_v2_min'],"

if old1 in content:
    content = content.replace(old1, new1, 1)
    p.write_text(content, encoding="utf-8")
    print("Added 3 v2.0 gates (placeholder for win_rate)")
else:
    print("evaluate_hard_gates anchor not found")
