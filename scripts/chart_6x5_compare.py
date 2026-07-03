#!/usr/bin/env python3
"""2025-2026 comparison: 6-strategy monthly balance line charts"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

DEPOSIT = 200
M = ['Jan', 'Feb', 'Mar', 'Apr', 'May']

d25 = {
    'Q2':       [240, 417, 535, 2184, 3197],
    'QS3':      [224, 435, 502, 5089, 7440],
    'QS4':      [211, 318, 367, 1424, 2091],
    'Q2+NOISE': [197, 177, 202,  522,  549],
    'QS3+NOISE':[194, 191, 199,  251,  301],
    'QS4+NOISE':[197, 196, 199,  220,  242],
}

d26 = {
    'Q2':       [227,  28, -145, -343, -541],
    'QS3':      [168,  11, -170, -312, -511],
    'QS4':      [206,  57, -103, -220, -389],
    'Q2+NOISE': [423, 480,  382,  375,  339],
    'QS3+NOISE':[250, 265,  214,  205,  205],
    'QS4+NOISE':[263, 280,  229,  220,  220],
}

C = {
    'Q2': '#2196F3', 'QS3': '#4CAF50', 'QS4': '#FF9800',
    'Q2+NOISE': '#64B5F6', 'QS3+NOISE': '#81C784', 'QS4+NOISE': '#FFB74D',
}

OUT = Path(__file__).resolve().parent.parent / 'results'
OUT.mkdir(parents=True, exist_ok=True)

# ========== 4-panel ==========
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 12))
x = list(range(len(M)))

panels = [
    (ax1, d25, ['Q2','QS3','QS4'], '2025 OFF (Q2 / QS3 / QS4)'),
    (ax2, d26, ['Q2','QS3','QS4'], '2026 OFF (Q2 / QS3 / QS4)'),
    (ax3, d25, ['Q2+NOISE','QS3+NOISE','QS4+NOISE'], '2025 NOISE Strategies'),
    (ax4, d26, ['Q2+NOISE','QS3+NOISE','QS4+NOISE'], '2026 NOISE Strategies'),
]

for ax, data, strs, title in panels:
    for s in strs:
        bal = [DEPOSIT] + data[s]
        xx = [0] + [i+1 for i in x]
        ax.plot(xx, bal, color=C[s], linewidth=2.5,
                marker='o' if 'NOISE' not in s else 's',
                markersize=8 if 'NOISE' not in s else 6,
                linestyle='--' if 'NOISE' in s else '-',
                label=s)
    ax.axhline(y=DEPOSIT, color='gray', linestyle=':', linewidth=1, alpha=0.5)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_ylabel('Balance ($)')
    if ax in (ax3, ax4):
        ax.set_xlabel('Month')
    ax.set_xticks([0] + [i+1 for i in x])
    ax.set_xticklabels(['Start'] + M)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'${v:,.0f}'))
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

plt.suptitle('6 Strategies x 5 Months: 2025 vs 2026 ($200 Start)',
             fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
p1 = OUT / 'bt_6x5_2025vs2026_balance.png'
plt.savefig(str(p1), dpi=150, bbox_inches='tight')
print(f'OK: {p1}')
plt.close()

# ========== Combined single chart ==========
fig2, ax = plt.subplots(figsize=(16, 7))
months_xtick = ['Start', '2025\nJan', 'Feb', 'Mar', 'Apr', 'May',
                '2026\nJan', 'Feb', 'Mar', 'Apr', 'May']

for s, d25s, d26s in [
    ('Q2', d25['Q2'], d26['Q2']),
    ('QS3', d25['QS3'], d26['QS3']),
    ('QS4', d25['QS4'], d26['QS4']),
    ('Q2+NOISE', d25['Q2+NOISE'], d26['Q2+NOISE']),
    ('QS3+NOISE', d25['QS3+NOISE'], d26['QS3+NOISE']),
    ('QS4+NOISE', d25['QS4+NOISE'], d26['QS4+NOISE']),
]:
    bal = [DEPOSIT] + d25s + d26s  # 1 + 5 + 5 = 11 points
    st = '--' if 'NOISE' in s else '-'
    lw = 1.8 if 'NOISE' in s else 2.5
    ax.plot(range(11), bal, color=C[s], linestyle=st, linewidth=lw,
            marker='o' if 'NOISE' not in s else 's',
            markersize=5 if 'NOISE' not in s else 4, label=s)

ax.axvline(x=5.5, color='black', linestyle='-', linewidth=1.5, alpha=0.3)
ax.axhline(y=DEPOSIT, color='gray', linestyle=':', linewidth=1, alpha=0.5)
ax.set_title('6 Strategies: 2025 vs 2026 Monthly Balance ($200 Start Each Year)',
             fontsize=14, fontweight='bold')
ax.set_ylabel('Balance ($)')
ax.set_xticks(range(11))
ax.set_xticklabels(months_xtick, fontsize=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'${v:,.0f}'))
ax.legend(fontsize=9, loc='upper left', ncol=2)
ax.grid(True, alpha=0.3)
plt.tight_layout()
p2 = OUT / 'bt_6x5_2025vs2026_combined.png'
plt.savefig(str(p2), dpi=150, bbox_inches='tight')
print(f'OK: {p2}')
plt.close()
