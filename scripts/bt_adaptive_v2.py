#!/usr/bin/env python3
"""自适应噪音门控验证: 从扫描中确定的最佳正常/防守参数组合.
固定lookback=15, 正常ratio=0.25/range=0.22, 防守ratio=0.30/range=可变.
扫描回撤触发阈值和防守range."""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

# ==== 固定噪音底座 ====
NOISE_BASE = {
    'InpEnableTickNoiseGate': 'true',
    'InpEnableDynamicSpread': 'true',
    'InpMinSLSpreadMult': '5.0',
    'InpOBTouchConfirmTicks': '5',
    'InpEnableMTF': 'false',
}

# ==== 正常态参数 (优化2505盈利) ====
NORMAL = {
    **NOISE_BASE,
    'InpSLBufferATR': '0.5',
    'InpMaxPosMult': '2.0',
    'InpTickNoiseGateLookback': '15',
    'InpTickNoiseGateMinDirRatio': '0.25',
    'InpTickNoiseGateMaxRangeATR': '0.22',
    # 自适应: 回撤>dd%触发防守
    'InpAdaptiveNoiseRecoveryPct': '1.0',
}

# 防守态: 收紧ratio和range (lookback不变, EA代码不支持动态切换)
DEF_RATIO = '0.30'  # 防守tick方向一致率

VARIANTS = [
    # 参考: 最佳静态 (从扫描结果)
    ('REF', 'REF-B2(lb20/r25/a18)静态', {
        **NOISE_BASE,
        'InpSLBufferATR': '0.5',
        'InpMaxPosMult': '2.0',
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.25',
        'InpTickNoiseGateMaxRangeATR': '0.18',
    }),

    # 自适应: 变化回撤触发阈值
    ('AD_dd3', 'AD-dd3% a22->a14', {
        **NORMAL,
        'InpAdaptiveNoiseDrawdownPct': '3.0',
        'InpAdaptiveNoiseDefMinDirRatio': DEF_RATIO,
        'InpAdaptiveNoiseDefMaxRangeATR': '0.14',
    }),
    ('AD_dd2', 'AD-dd2% a22->a14', {
        **NORMAL,
        'InpAdaptiveNoiseDrawdownPct': '2.0',
        'InpAdaptiveNoiseDefMinDirRatio': DEF_RATIO,
        'InpAdaptiveNoiseDefMaxRangeATR': '0.14',
    }),
    ('AD_dd5', 'AD-dd5% a22->a14', {
        **NORMAL,
        'InpAdaptiveNoiseDrawdownPct': '5.0',
        'InpAdaptiveNoiseDefMinDirRatio': DEF_RATIO,
        'InpAdaptiveNoiseDefMaxRangeATR': '0.14',
    }),

    # 自适应: 变化防守range严格度
    ('AD_a12', 'AD-dd3% a22->a12', {
        **NORMAL,
        'InpAdaptiveNoiseDrawdownPct': '3.0',
        'InpAdaptiveNoiseDefMinDirRatio': DEF_RATIO,
        'InpAdaptiveNoiseDefMaxRangeATR': '0.12',
    }),
    ('AD_a16', 'AD-dd3% a22->a16', {
        **NORMAL,
        'InpAdaptiveNoiseDrawdownPct': '3.0',
        'InpAdaptiveNoiseDefMinDirRatio': DEF_RATIO,
        'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
    }),
]

MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]
total = len(VARIANTS) * 2
print(f"\n{'='*70}")
print(f"  Adaptive Noise Gate: {len(VARIANTS)}v x 2m = {total} BTs")
print(f"  Normal: lb15/r25/a22 | Defensive: lb15/r30/a[12-16]")
print(f"{'='*70}")

set_files = {}
for key, label, ov in VARIANTS:
    set_files[key] = make_set(f'ad_{key}', ov, base='v11xau-qs3.set')

results = {}
done = 0
for vkey, vlabel, ov in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1
        key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<42} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'ad_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=$ {r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:
            print('FAILED')

# ===== 汇总 =====
ref_off_25 = results.get('REF_2505', {}).get('pnl', 0)
ref_off_26 = results.get('REF_2605', {}).get('pnl', 0)

print(f"\n{'='*120}")
print(f"  ADAPTIVE NOISE GATE RESULTS")
print(f"  REF static B2: 2505=${ref_off_25:,.0f}, 2605=${ref_off_26:,.2f}")
print(f"{'='*120}")
print(f"\n{'Variant':<42} {'2505 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'dREF25':>9} {'dREF26':>9}")
print('-' * 120)

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        d25 = r25['pnl'] - ref_off_25
        d26 = r26['pnl'] - ref_off_26
        mark = ''
        if r26['pnl'] > 0:
            mark += ' [2605+]'
        if r25['pnl'] >= ref_off_25 * 0.90:
            mark += ' [2505=]'
        print(f"{vlabel:<42} {r25['count']:>5} {r25['daily']:>4.1f} {r25['pf']:>5.2f} "
              f"${r25['pnl']:>+9.2f} | {r26['count']:>5} {r26['daily']:>4.1f} {r26['pf']:>5.2f} "
              f"${r26['pnl']:>+9.2f} | ${d25:>+8.0f} ${d26:>+8.2f}{mark}")

# 双月净合计
print(f"\n--- Dual-Month Net Ranking ---")
for vkey, vlabel, _ in sorted(VARIANTS, key=lambda v: results.get(f'{v[0]}_2505', {}).get('pnl', -99999) + results.get(f'{v[0]}_2605', {}).get('pnl', -99999), reverse=True):
    r25 = results.get(f'{vkey}_2505', {}).get('pnl', -99999)
    r26 = results.get(f'{vkey}_2605', {}).get('pnl', -99999)
    net = r25 + r26
    print(f"  {vlabel:<42} Net=${net:>+9,.2f}  2505=${r25:>+,.0f}  2605=${r26:>+,.2f}")

print(f"\n[DONE]")
