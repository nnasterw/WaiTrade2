import csv
from collections import defaultdict
from pathlib import Path

csv_path = Path(r"D:\Code\codexProject\WaiTrade2\results\backtest\v11-btc1-loop43_20240601_20260531_20260708.trades.csv")
with csv_path.open(encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print("=" * 60)
print("V11-BTC1-LOOP43 关键指标详细分析")
print("=" * 60)
print("总交易数:", len(rows))
print("回测周期: 2024.06.01 - 2026.05.31 (729天)")
print()

wins = [r for r in rows if r.get("pnl_proxy", "") and float(r.get("pnl_proxy", 0) or 0) > 0]
losses = [r for r in rows if r.get("pnl_proxy", "") and float(r.get("pnl_proxy", 0) or 0) < 0]
breakeven = [r for r in rows if r.get("pnl_proxy", "") and float(r.get("pnl_proxy", 0) or 0) == 0]
print("--- 胜率/败率 ---")
print("盈利单:", len(wins), "(", round(100*len(wins)/len(rows),1), "%)")
print("亏损单:", len(losses), "(", round(100*len(losses)/len(rows),1), "%)")
print("持平:", len(breakeven))
print()

if wins:
    win_total = sum(float(r.get("pnl_proxy", 0) or 0) for r in wins)
    win_avg = win_total / len(wins)
    print("--- 盈利统计 ---")
    print("总盈利: $", round(win_total, 2))
    print("平均盈利: $", round(win_avg, 2), "/单")
    print("最大单笔盈利: $", round(max(float(r.get("pnl_proxy", 0) or 0) for r in wins), 2))
if losses:
    loss_total = sum(float(r.get("pnl_proxy", 0) or 0) for r in losses)
    loss_avg = loss_total / len(losses)
    print("--- 亏损统计 ---")
    print("总亏损: $", round(loss_total, 2))
    print("平均亏损: $", round(loss_avg, 2), "/单")
    print("最大单笔亏损: $", round(min(float(r.get("pnl_proxy", 0) or 0) for r in losses), 2))

print()
print("--- 盈亏比 (Win/Loss Ratio) ---")
if wins and losses:
    avg_w = sum(float(r.get("pnl_proxy", 0) or 0) for r in wins) / len(wins)
    avg_l = abs(sum(float(r.get("pnl_proxy", 0) or 0) for r in losses) / len(losses))
    print("平均盈利/平均亏损:", round(avg_w/avg_l, 2))
    print("总盈利/总亏损:", round(abs(win_total/loss_total), 2))

print()
print("--- 日均交易 ---")
print("日均单数:", round(len(rows)/729, 3), "笔/天")
print("周均单数:", round(len(rows)/729*7, 2), "笔/周")
print("月均单数:", round(len(rows)/24, 2), "笔/月")

print()
print("--- 月度表现 ---")
month_data = defaultdict(lambda: {"trades": 0, "pnl": 0.0, "wins": 0, "losses": 0})
for r in rows:
    close_time = r.get("close_time", "")
    if close_time:
        month = close_time[:7]
        pnl = float(r.get("pnl_proxy", 0) or 0)
        month_data[month]["trades"] += 1
        month_data[month]["pnl"] += pnl
        if pnl > 0:
            month_data[month]["wins"] += 1
        elif pnl < 0:
            month_data[month]["losses"] += 1
for month in sorted(month_data.keys()):
    d = month_data[month]
    wr = round(100 * d["wins"] / d["trades"], 1) if d["trades"] > 0 else 0
    sign = "+" if d["pnl"] >= 0 else ""
    print("  " + month + ": 单数=" + str(d["trades"]).rjust(3) + " 胜率=" + str(wr).rjust(5) + "% 净利=" + sign + "$" + str(round(d["pnl"], 2)))

print()
print("--- R 倍数分布 ---")
r_values = [float(r.get("r", 0) or 0) for r in rows if r.get("r", "")]
big_w = [r for r in r_values if r > 3.0]
micro = [r for r in r_values if 0 < r < 0.5]
mid = [r for r in r_values if 0.5 <= r <= 3.0]
losses_r = [r for r in r_values if r < 0]
print(">3R (大赢):", len(big_w), "笔 (", round(100*len(big_w)/len(r_values),1), "%)")
print("0.5R-3R (中等):", len(mid), "笔")
print("<0.5R (微利):", len(micro), "笔 (", round(100*len(micro)/len(r_values),1), "%)")
print("<0R (亏损):", len(losses_r), "笔")
print("平均R:", round(sum(r_values)/len(r_values), 3))
print("最大R:", round(max(r_values), 2))
print("最小R:", round(min(r_values), 2))

print()
print("--- 持仓时长 ---")
durations = [float(r.get("duration_min", 0) or 0) for r in rows if r.get("duration_min", "")]
if durations:
    durations.sort()
    print("平均持仓:", round(sum(durations)/len(durations), 1), "分钟 (", round(sum(durations)/len(durations)/60, 1), "小时)")
    print("中位数持仓:", durations[len(durations)//2], "分钟")
    print("最短持仓:", min(durations), "分钟")
    print("最长持仓:", max(durations), "分钟 (", round(max(durations)/60, 1), "小时)")
    short = [d for d in durations if d < 10]
    medium = [d for d in durations if 10 <= d < 60]
    long_d = [d for d in durations if d >= 60]
    print("  <10min (极短):", len(short), "笔 (", round(100*len(short)/len(durations),1), "%)")
    print("  10-60min (短):", len(medium), "笔 (", round(100*len(medium)/len(durations),1), "%)")
    print("  >=60min (长):", len(long_d), "笔 (", round(100*len(long_d)/len(durations),1), "%)")

print()
print("--- 出仓原因 ---")
reasons = defaultdict(int)
for r in rows:
    reasons[r.get("reason", "")] += 1
for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
    print("  " + reason + ": " + str(count) + " 笔 (" + str(round(100*count/len(rows),1)) + "%)")

print()
print("--- 方向偏差 ---")
buy_pnl = sum(float(r.get("pnl_proxy", 0) or 0) for r in rows if r.get("dir") == "buy")
sell_pnl = sum(float(r.get("pnl_proxy", 0) or 0) for r in rows if r.get("dir") == "sell")
buy_count = sum(1 for r in rows if r.get("dir") == "buy")
sell_count = sum(1 for r in rows if r.get("dir") == "sell")
print("Buy 方向:", buy_count, "笔, 净利 $", round(buy_pnl, 2), ", 平均 $", round(buy_pnl/buy_count, 2) if buy_count else 0, "/单")
print("Sell 方向:", sell_count, "笔, 净利 $", round(sell_pnl, 2), ", 平均 $", round(sell_pnl/sell_count, 2) if sell_count else 0, "/单")

