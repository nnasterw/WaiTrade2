#!/usr/bin/env python3
"""分析 zd2 月度回测数据，找出亏损规律"""
import sys, math

months = [
    ('2024-06', 44, 47.7, 121.83, -39.1),
    ('2024-07', 17, 47.1, 331.79, 65.9),
    ('2024-08', 37, 48.6, 218.29, 9.1),
    ('2024-09', 39, 56.4, 194.22, -2.9),
    ('2024-10', 30, 70.0, 301.53, 50.8),
    ('2024-11', 54, 55.6, 141.74, -29.1),
    ('2024-12', 41, 48.8, 136.37, -31.8),
    ('2025-01', 34, 64.7, 326.18, 63.1),
    ('2025-02', 37, 45.9, 192.72, -3.6),
    ('2025-03', 33, 63.6, 224.14, 12.1),
    ('2025-04', 42, 57.1, 221.52, 10.8),
    ('2025-05', 79, 43.0, 129.49, -35.3),
    ('2025-06', 52, 59.6, 212.20, 6.1),
    ('2025-07', 57, 61.4, 213.07, 6.5),
    ('2025-08', 38, 50.0, 159.12, -20.4),
    ('2025-09', 39, 48.7, 167.84, -16.1),
    ('2025-10', 29, 62.1, 255.82, 27.9),
    ('2025-11', 34, 58.8, 298.89, 49.4),
    ('2025-12', 25, 64.0, 310.04, 55.0),
    ('2026-01', 10, 60.0, 302.26, 51.1),
    ('2026-02', 8, 87.5, 306.15, 53.1),
    ('2026-03', 27, 59.3, 321.00, 60.5),
    ('2026-04', 17, 52.9, 317.76, 58.9),
    ('2026-05', 12, 66.7, 325.37, 62.7),
]

winners = [m for m in months if m[4] > 0]
losers = [m for m in months if m[4] < 0]
n = len(months)

print("=" * 70)
print("ZD2 月度回测统计分析")
print("=" * 70)

print(f"\n=== 盈亏统计 ===")
print(f"盈利月: {len(winners)}/{n} ({len(winners)/n*100:.1f}%)")
print(f"  平均交易: {sum(m[1] for m in winners)/len(winners):.1f}笔")
print(f"  平均胜率: {sum(m[2] for m in winners)/len(winners):.1f}%")
print(f"  平均收益: {sum(m[4] for m in winners)/len(winners):.1f}%")
print(f"亏损月: {len(losers)}/{n} ({len(losers)/n*100:.1f}%)")
print(f"  平均交易: {sum(m[1] for m in losers)/len(losers):.1f}笔")
print(f"  平均胜率: {sum(m[2] for m in losers)/len(losers):.1f}%")
print(f"  平均亏损: {sum(m[4] for m in losers)/len(losers):.1f}%")

# Correlation analysis
trades_list = [m[1] for m in months]
returns = [m[4] for m in months]
wr_list = [m[2] for m in months]
mean_t = sum(trades_list)/n
mean_r = sum(returns)/n
mean_wr = sum(wr_list)/n

def corr(x, y, mx, my):
    cov = sum((x[i]-mx)*(y[i]-my) for i in range(n))
    sx = math.sqrt(sum((v-mx)**2 for v in x))
    sy = math.sqrt(sum((v-my)**2 for v in y))
    return cov/(sx*sy) if sx*sy > 0 else 0

print(f"\n=== 相关性 ===")
print(f"交易数 vs 收益: {corr(trades_list, returns, mean_t, mean_r):.3f}")
print(f"胜率 vs 收益: {corr(wr_list, returns, mean_wr, mean_r):.3f}")

# High vs low frequency
print(f"\n=== 高频月(>=45笔) vs 低频月(<45笔) ===")
high = [m for m in months if m[1] >= 45]
low = [m for m in months if m[1] < 45]
print(f"高频({len(high)}个月): 均收益{sum(m[4] for m in high)/len(high):.1f}%, 盈利{sum(1 for m in high if m[4]>0)}/{len(high)}")
for m in high:
    print(f"  {m[0]}: {m[1]}笔 WR{m[2]:.1f}% {m[4]:+.1f}%")
print(f"低频({len(low)}个月): 均收益{sum(m[4] for m in low)/len(low):.1f}%, 盈利{sum(1 for m in low if m[4]>0)}/{len(low)}")

# By quarter
print(f"\n=== 季度分组 ===")
quarters = {}
for m in months:
    yr, mo = m[0].split('-')
    q = f'{yr}-Q{(int(mo)-1)//3+1}'
    quarters.setdefault(q, []).append(m)
for q in sorted(quarters.keys()):
    qm = quarters[q]
    print(f"{q}: {sum(1 for m in qm if m[4]>0)}/{len(qm)}盈利, 均{sum(m[1] for m in qm)/len(qm):.0f}笔/月, 均收益{sum(m[4] for m in qm)/len(qm):+.1f}%")

# Half year
print(f"\n=== 半年度分组 ===")
h1_2024 = [m for m in months if m[0] < '2024-07']
h2_2024 = [m for m in months if '2024-07' <= m[0] <= '2024-12']
h1_2025 = [m for m in months if '2025-01' <= m[0] <= '2025-06']
h2_2025 = [m for m in months if '2025-07' <= m[0] <= '2025-12']
h1_2026 = [m for m in months if m[0] >= '2026-01']
for label, half in [('2024-H2', h2_2024), ('2025-H1', h1_2025), ('2025-H2', h2_2025), ('2026-H1', h1_2026)]:
    if half:
        print(f"{label}: {sum(1 for m in half if m[4]>0)}/{len(half)}盈利, 均{sum(m[1] for m in half)/len(half):.0f}笔/月, 均收益{sum(m[4] for m in half)/len(half):+.1f}%")
