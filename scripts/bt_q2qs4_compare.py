#!/usr/bin/env python3
"""Q2/QS4 vs QS3 — new .ex5, 2505+2605, OFF+NOISE comparison."""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NK = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
      'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpEnableMTF':'false',
      'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
      'InpTickNoiseGateMaxRangeATR':'0.25'}

SL5_M2 = {'InpSLBufferATR':'0.5','InpMaxPosMult':'2.0'}

TESTS = [
    ('Q2_OFF',   'Q2-OFF',  'v11xau-qs2.set', {}),
    ('Q2_NOISE', 'Q2+NOISE','v11xau-qs2.set', {**NK, **SL5_M2}),
    ('QS3_OFF',  'QS3-OFF', 'v11xau-qs3.set', {}),
    ('QS3_NOISE','QS3+NOISE','v11xau-qs3.set', {**NK, **SL5_M2}),
    ('QS4_OFF',  'QS4-OFF', 'v11xau-qs4.set', {}),
    ('QS4_NOISE','QS4+NOISE','v11xau-qs4.set', {**NK, **SL5_M2}),
]

MONTHS = [('2505','2025.05.01','2025.05.31'),('2605','2026.05.01','2026.05.31')]

total = len(TESTS) * 2
print(f"\n{'='*65}")
print(f"  Q2/QS3/QS4 OFF+NOISE — 新ex5 — 2505+2605 ({total}BT)")
print(f"{'='*65}")

set_files = {}
for key, label, base, ov in TESTS:
    set_files[key] = make_set(f'cmp_{key}', ov, base=base)

results = {}; done = 0
for vkey, vlabel, base, ov in TESTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1; key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<15} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'cmp_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r: print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  PnL=${r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else: print('FAILED')

# ===== SUMMARY =====
print(f"\n{'='*70}")
print(f"  Q2 / QS3 / QS4 对比汇总 — 新ex5 — 2505+2605")
print(f"{'='*70}")

# Block 1: Indicators
print(f"\n  --- 2505 好月 ---")
print(f"  {'策略':<15} {'交易':>5} {'日单':>5} {'胜率':>6} {'PF':>6} {'净收益':>10} {'余额':>10}")
print(f"  {'-'*65}")
for vkey, vlabel, _, _ in TESTS:
    r = results.get(f'{vkey}_2505', {})
    if r:
        bal = 200 + r['pnl']
        mark = ' *' if vkey == max([k for k in results if '2505' in k], key=lambda k: results[k]['pnl']) else ''
        print(f"  {vlabel:<15} {r['count']:>5} {r['daily']:>4.1f} {r['wr']:>5.1f}% {r['pf']:>5.2f} ${r['pnl']:>+9,.2f} ${bal:>9,.0f}{mark}")

print(f"\n  --- 2605 坏月 ---")
print(f"  {'策略':<15} {'交易':>5} {'日单':>5} {'胜率':>6} {'PF':>6} {'净收益':>10} {'余额':>10}")
print(f"  {'-'*65}")
for vkey, vlabel, _, _ in TESTS:
    r = results.get(f'{vkey}_2605', {})
    if r:
        bal = 200 + r['pnl']
        mark = ' *' if r['pnl'] > 0 else ''
        print(f"  {vlabel:<15} {r['count']:>5} {r['daily']:>4.1f} {r['wr']:>5.1f}% {r['pf']:>5.2f} ${r['pnl']:>+9,.2f} ${bal:>9,.0f}{mark}")

# Block 2: Monthly balance (simplified — single month)
print(f"\n  --- 月份余额 ---")
print(f"  {'策略':<15} {'2505初始':>8} {'2505月末':>10} {'净利':>10} | {'2605初始':>8} {'2605月末':>10} {'净利':>10}")
print(f"  {'-'*70}")
for vkey, vlabel, _, _ in TESTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        b25 = 200 + r25['pnl']
        b26 = 200 + r26['pnl']
        print(f"  {vlabel:<15} ${200:>7} ${b25:>9,.0f} ${r25['pnl']:>+9,.0f} | ${200:>7} ${b26:>9,.0f} ${r26['pnl']:>+9,.0f}")

# Block 3: Conclusions
print(f"\n  --- 结论 ---")
best_25 = max([k for k in results if '2505' in k], key=lambda k: results[k]['pnl'])
best_26 = max([k for k in results if '2605' in k], key=lambda k: results[k]['pnl'])

vkey_to_label = {v[0]: v[1] for v in TESTS}
print(f"  2505最佳: {vkey_to_label[best_25]} (${results[best_25]['pnl']:,.0f})")
print(f"  2605最佳: {vkey_to_label[best_26]} (${results[best_26]['pnl']:,.2f})")

# Dual-month ranking
dual = {}
for vkey, vlabel, _, _ in TESTS:
    r25 = results.get(f'{vkey}_2505', {}).get('pnl', 0)
    r26 = results.get(f'{vkey}_2605', {}).get('pnl', 0)
    dual[vkey] = (vlabel, r25 + r26, r25, r26)

print(f"\n  双月净合计排名:")
for vkey, (vlabel, total, r25, r26) in sorted(dual.items(), key=lambda x: x[1][1], reverse=True):
    mark = ' ← 双月正' if total > 0 else ''
    print(f"    {vlabel:<15} ${total:>+9,.2f}  (2505=${r25:,.0f}  2605=${r26:,.2f}){mark}")

print(f"\n[DONE]")
