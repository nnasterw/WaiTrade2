#!/usr/bin/env python3
"""自适应v3: 正常态用REF_LOOSE级宽松参数(lb10/r20/a25), 回撤时收紧.
目标: 2505保持REF_LOOSE级盈利(~$6K), 2605触发防守后盈利."""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE_BASE = {
    'InpEnableTickNoiseGate': 'true',
    'InpEnableDynamicSpread': 'true',
    'InpMinSLSpreadMult': '5.0',
    'InpOBTouchConfirmTicks': '5',
    'InpEnableMTF': 'false',
}

# ==== 宽松正常态 (REF_LOOSE风格: lb10/r20/a25, 2505曾+$6,691) ====
LOOSE_NORMAL = {
    **NOISE_BASE,
    'InpSLBufferATR': '0.5',
    'InpMaxPosMult': '2.0',
    'InpTickNoiseGateLookback': '10',
    'InpTickNoiseGateMinDirRatio': '0.20',
    'InpTickNoiseGateMaxRangeATR': '0.25',
    'InpAdaptiveNoiseRecoveryPct': '1.0',
}

VARIANTS = [
    # 参考基线
    ('REF_LOOSE', 'REF-LOOSE(lb10/r20/a25)静态', {
        **NOISE_BASE,
        'InpSLBufferATR': '0.5',
        'InpMaxPosMult': '2.0',
        'InpTickNoiseGateLookback': '10',
        'InpTickNoiseGateMinDirRatio': '0.20',
        'InpTickNoiseGateMaxRangeATR': '0.25',
    }),
    ('REF_BEST',  'REF-BEST-AD(dd3 a22->a16)', {
        **NOISE_BASE,
        'InpSLBufferATR': '0.5',
        'InpMaxPosMult': '2.0',
        'InpTickNoiseGateLookback': '15',
        'InpTickNoiseGateMinDirRatio': '0.25',
        'InpTickNoiseGateMaxRangeATR': '0.22',
        'InpAdaptiveNoiseDrawdownPct': '3.0',
        'InpAdaptiveNoiseDefMinDirRatio': '0.30',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
        'InpAdaptiveNoiseRecoveryPct': '1.0',
    }),

    # 自适应: 宽松正常态 → 收紧防守
    ('AD_L3', 'AD-LOOSE dd3% a25->a16', {
        **LOOSE_NORMAL,
        'InpAdaptiveNoiseDrawdownPct': '3.0',
        'InpAdaptiveNoiseDefMinDirRatio': '0.30',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
    }),
    ('AD_L2', 'AD-LOOSE dd2% a25->a16', {
        **LOOSE_NORMAL,
        'InpAdaptiveNoiseDrawdownPct': '2.0',
        'InpAdaptiveNoiseDefMinDirRatio': '0.30',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
    }),
    ('AD_L25', 'AD-LOOSE dd2.5% a25->a16', {
        **LOOSE_NORMAL,
        'InpAdaptiveNoiseDrawdownPct': '2.5',
        'InpAdaptiveNoiseDefMinDirRatio': '0.30',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.16',
    }),
    # 更紧的防守态
    ('AD_L3a14', 'AD-LOOSE dd3% a25->a14', {
        **LOOSE_NORMAL,
        'InpAdaptiveNoiseDrawdownPct': '3.0',
        'InpAdaptiveNoiseDefMinDirRatio': '0.30',
        'InpAdaptiveNoiseDefMaxRangeATR': '0.14',
    }),
]

MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]
total = len(VARIANTS) * 2
print(f"\n{'='*70}")
print(f"  Adaptive v3: LOOSE normal (lb10/r20/a25), {len(VARIANTS)}v x 2m = {total} BTs")
print(f"  Target: 2505=$5K+ (non-triggered), 2605=profitable (triggered)")
print(f"{'='*70}")

set_files = {}
for key, label, ov in VARIANTS:
    set_files[key] = make_set(f'ad3_{key}', ov, base='v11xau-qs3.set')

results = {}
done = 0
for vkey, vlabel, ov in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1
        key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<42} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'ad3_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=$ {r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:
            print('FAILED')

# ===== 汇总 =====
ref_loose_25 = results.get('REF_LOOSE_2505', {}).get('pnl', 0)
ref_best_25 = results.get('REF_BEST_2505', {}).get('pnl', 0)

print(f"\n{'='*120}")
print(f"  ADAPTIVE v3 RESULTS — LOOSE normal baseline")
print(f"  REF_LOOSE: 2505=${ref_loose_25:,.0f} | REF_BEST_AD: 2505=${ref_best_25:,.0f}")
print(f"{'='*120}")
print(f"\n{'Variant':<42} {'2505 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | vsLOOSE25 | vsLOOSE26")
print('-' * 120)

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        dl25 = r25['pnl'] - ref_loose_25
        dl26 = r26['pnl'] - results.get('REF_LOOSE_2605', {}).get('pnl', 0)
        mark = ''
        if r26['pnl'] > 0:
            mark += ' [2605 PROFITABLE!]'
        if r25['pnl'] >= ref_loose_25 * 0.85:
            mark += ' [2505 preserved]'
        print(f"{vlabel:<42} {r25['count']:>5} {r25['daily']:>4.1f} {r25['pf']:>5.2f} "
              f"${r25['pnl']:>+9.2f} | {r26['count']:>5} {r26['daily']:>4.1f} {r26['pf']:>5.2f} "
              f"${r26['pnl']:>+9.2f} | ${dl25:>+8.0f} | ${dl26:>+8.2f}{mark}")

# 双月排名
print(f"\n--- Dual-Month Net Ranking (目标: 2505>$5K AND 2605>$0) ---")
for vkey, vlabel, _ in sorted(VARIANTS, key=lambda v: results.get(f'{v[0]}_2505', {}).get('pnl', 0) + results.get(f'{v[0]}_2605', {}).get('pnl', 0), reverse=True):
    r25 = results.get(f'{vkey}_2505', {}).get('pnl', -99999)
    r26 = results.get(f'{vkey}_2605', {}).get('pnl', -99999)
    net = r25 + r26
    flags = []
    if r26 > 0: flags.append('2605+')
    if r25 >= ref_loose_25 * 0.80: flags.append('2505=')
    print(f"  {vlabel:<42} Net=${net:>+9,.2f}  2505=${r25:>+9,.0f}  2605=${r26:>+9,.2f}  {' '.join(flags)}")

print(f"\n[DONE]")
