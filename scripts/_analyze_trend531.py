import csv
from collections import defaultdict
from pathlib import Path

csv_path = Path(r"D:\Code\codexProject\WaiTrade2\results\backtest\v11-btc1-trend531_20240601_20260531_20260707.trades.csv")
with csv_path.open(encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print("Total trades:", len(rows))

month_trades = defaultdict(list)
for r in rows:
    close_time = r.get("close_time", "")
    if close_time:
        month = close_time[:7]
        month_trades[month].append(r)

print()
print("=== Loss Months ===")
for month in sorted(month_trades.keys()):
    net = sum(float(r.get("pnl_proxy", 0) or 0) for r in month_trades[month])
    if net < 0:
        print("  " + month + ": net=" + str(round(net, 2)) + ", trades=" + str(len(month_trades[month])))
        for r in month_trades[month]:
            ct = r.get("close_time", "")[:16]
            d = r.get("dir", "")
            p = float(r.get("pnl_proxy", 0) or 0)
            rv = r.get("r", "")
            rea = r.get("reason", "")
            dur = r.get("duration_min", "")
            bo = r.get("bounce_ob", "")
            cf = r.get("confirm", "")
            htf = r.get("htf", "")
            print("    " + ct + " dir=" + d + " pnl=" + str(round(p, 2)) + " r=" + rv + " reason=" + rea + " duration=" + dur + " htf=" + htf + " bo=" + bo + " cf=" + cf)

print()
print("=== Exit Reasons ===")
exit_counts = defaultdict(int)
exit_pnl = defaultdict(float)
for r in rows:
    reason = r.get("reason", "")
    exit_counts[reason] += 1
    exit_pnl[reason] += float(r.get("pnl_proxy", 0) or 0)
for reason, count in sorted(exit_counts.items(), key=lambda x: -x[1]):
    print("  " + reason + ": " + str(count) + " trades, net=" + str(round(exit_pnl[reason], 2)))

print()
print("=== Loss Trades (>-10) ===")
loss_trades = [r for r in rows if float(r.get("pnl_proxy", 0) or 0) < -10]
print("Total: " + str(len(loss_trades)))
short = [r for r in loss_trades if float(r.get("duration_min", 0) or 0) < 30]
medium = [r for r in loss_trades if 30 <= float(r.get("duration_min", 0) or 0) < 180]
long = [r for r in loss_trades if float(r.get("duration_min", 0) or 0) >= 180]
print("  Short (<30min): " + str(len(short)))
print("  Medium (30-180min): " + str(len(medium)))
print("  Long (>=180min): " + str(len(long)))

print()
print("=== Big Winners (R >= 2.5) ===")
big = [r for r in rows if float(r.get("r", 0) or 0) >= 2.5]
print("Total: " + str(len(big)))
for r in sorted(big, key=lambda x: float(x.get("r", 0) or 0), reverse=True)[:5]:
    print("  R=" + r.get("r", "") + " reason=" + r.get("reason", "") + " duration=" + r.get("duration_min", "") + " htf=" + r.get("htf", ""))

print()
print("=== Direction Bias ===")
buy_pnl = sum(float(r.get("pnl_proxy", 0) or 0) for r in rows if r.get("dir") == "buy")
sell_pnl = sum(float(r.get("pnl_proxy", 0) or 0) for r in rows if r.get("dir") == "sell")
print("Buy PnL: " + str(round(buy_pnl, 2)) + " (" + str(sum(1 for r in rows if r.get("dir")=="buy")) + " trades)")
print("Sell PnL: " + str(round(sell_pnl, 2)) + " (" + str(sum(1 for r in rows if r.get("dir")=="sell")) + " trades)")

