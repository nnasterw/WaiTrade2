from pathlib import Path
p = Path(r"D:\Code\codexProject\WaiTrade2\scripts\wfys_score.py")
content = p.read_text(encoding="utf-8")
# Update risk quality to v2.0 (5 -> 5 with new 3 sub-items)
old = """    risk_ratio_score += _linear_score(cont['sharpe'], 0.0, 3.0, 2.0)
    risk_ratio_score += _linear_score(cont['sortino'], 0.0, 4.0, 1.5)
    risk_ratio_score += _linear_score(cont['calmar'], 0.0, 3.0, 1.5)
    risk_parts = {
        '720d回撤': _reverse_linear_score(cont['max_drawdown_pct'], 0.40, 0.18, 8.0),
        'Recovery Factor': _linear_score(cont['recovery_factor'], 0.0, 5.0, 7.0),
        'Profit Factor': _linear_score(cont['profit_factor'], 0.0, 2.10, 5.0),
        'Sharpe/Sortino/Calmar': min(5.0, risk_ratio_score),
    }"""
new = """    risk_ratio_score += _linear_score(cont['sharpe'], 0.0, 3.0, 1.0)
    risk_ratio_score += _linear_score(cont['sortino'], 0.0, 4.0, 1.0)
    risk_ratio_score += _linear_score(cont['calmar'], 0.0, 3.0, 1.0)
    risk_parts = {
        '720d回撤': _reverse_linear_score(cont['max_drawdown_pct'], 0.40, 0.18, 8.0),
        'Recovery Factor': _linear_score(cont['recovery_factor'], 0.0, 5.0, 7.0),
        'Profit Factor': _linear_score(cont['profit_factor'], 0.0, 2.10, 5.0),
        # v2.0: 3 new sub-items
        '720d周均单数': _linear_score(cont['trade_count'] / 103.0 if cont['trade_count'] else 0.0, 0.0, 2.5, 2.0),
        '720d胜率': _linear_score(r_metrics.get('win_rate', 0.0), 0.20, 0.50, 2.0),
        '720d盈亏比': _linear_score(cont['avg_win_loss'], 0.0, 6.0, 1.0),
    }"""
if old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    print("Updated risk_parts with v2.0 (3 new sub-items)")
else:
    print("Anchor not found")
