#!/usr/bin/env python3
"""QS3噪声门控甜点扫描 — 寻找2505不退化+2605盈利的参数组合.
三线独立扫描: Lookback / MinDirRatio / MaxRangeATR.
固定: SL5(SLBuffer=0.5) + M2(MaxPosMult=2.0) + 噪音门控开启."""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

# ==== 固定基础 (所有变体共用) ====
NOISE_BASE = {
    'InpEnableTickNoiseGate': 'true',
    'InpEnableDynamicSpread': 'true',
    'InpMinSLSpreadMult': '5.0',
    'InpOBTouchConfirmTicks': '5',
    'InpEnableMTF': 'false',
}
SL5_M2 = {'InpSLBufferATR': '0.5', 'InpMaxPosMult': '2.0'}

# ==== 基线 ====
BASELINES = [
    ('REF_OFF',   'REF-QS3-OFF',              {}),
    ('REF_LOOSE', 'REF-SL5M2+NK(lb10/r20/r25)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '10',
        'InpTickNoiseGateMinDirRatio': '0.20',
        'InpTickNoiseGateMaxRangeATR': '0.25'}),
    ('REF_TIGHT', 'REF-SL5M2+NK(lb30/r35/r15)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '30',
        'InpTickNoiseGateMinDirRatio': '0.35',
        'InpTickNoiseGateMaxRangeATR': '0.15'}),
]

# ==== 线A: 扫描Lookback (固定 ratio=0.30, range=0.18) ====
LINE_A = [
    ('A1', 'A1-lb10(SL5M2+r30/r18)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '10',
        'InpTickNoiseGateMinDirRatio': '0.30',
        'InpTickNoiseGateMaxRangeATR': '0.18'}),
    ('A2', 'A2-lb15(SL5M2+r30/r18)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '15',
        'InpTickNoiseGateMinDirRatio': '0.30',
        'InpTickNoiseGateMaxRangeATR': '0.18'}),
    ('A3', 'A3-lb20(SL5M2+r30/r18)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.30',
        'InpTickNoiseGateMaxRangeATR': '0.18'}),
    ('A4', 'A4-lb25(SL5M2+r30/r18)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '25',
        'InpTickNoiseGateMinDirRatio': '0.30',
        'InpTickNoiseGateMaxRangeATR': '0.18'}),
    ('A5', 'A5-lb30(SL5M2+r30/r18)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '30',
        'InpTickNoiseGateMinDirRatio': '0.30',
        'InpTickNoiseGateMaxRangeATR': '0.18'}),
]

# ==== 线B: 扫描MinDirRatio (固定 lookback=20, range=0.18) ====
LINE_B = [
    ('B1', 'B1-r20(SL5M2+lb20/r18)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.20',
        'InpTickNoiseGateMaxRangeATR': '0.18'}),
    ('B2', 'B2-r25(SL5M2+lb20/r18)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.25',
        'InpTickNoiseGateMaxRangeATR': '0.18'}),
    ('B3', 'B3-r30(SL5M2+lb20/r18)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.30',
        'InpTickNoiseGateMaxRangeATR': '0.18'}),
    ('B4', 'B4-r35(SL5M2+lb20/r18)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.35',
        'InpTickNoiseGateMaxRangeATR': '0.18'}),
    ('B5', 'B5-r40(SL5M2+lb20/r18)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.40',
        'InpTickNoiseGateMaxRangeATR': '0.18'}),
]

# ==== 线C: 扫描MaxRangeATR (固定 lookback=20, ratio=0.30) ====
LINE_C = [
    ('C1', 'C1-a10(SL5M2+lb20/r30)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.30',
        'InpTickNoiseGateMaxRangeATR': '0.10'}),
    ('C2', 'C2-a14(SL5M2+lb20/r30)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.30',
        'InpTickNoiseGateMaxRangeATR': '0.14'}),
    ('C3', 'C3-a18(SL5M2+lb20/r30)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.30',
        'InpTickNoiseGateMaxRangeATR': '0.18'}),
    ('C4', 'C4-a22(SL5M2+lb20/r30)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.30',
        'InpTickNoiseGateMaxRangeATR': '0.22'}),
    ('C5', 'C5-a25(SL5M2+lb20/r30)', {**NOISE_BASE, **SL5_M2,
        'InpTickNoiseGateLookback': '20',
        'InpTickNoiseGateMinDirRatio': '0.30',
        'InpTickNoiseGateMaxRangeATR': '0.25'}),
]

ALL_VARIANTS = BASELINES + LINE_A + LINE_B + LINE_C
MONTHS = [('2505', '2025.05.01', '2025.05.31'), ('2605', '2026.05.01', '2026.05.31')]

total = len(ALL_VARIANTS) * 2
print(f"\n{'='*70}")
print(f"  QS3 噪声门控甜点扫描 — {len(ALL_VARIANTS)}变体 x 2月 = {total}次回测")
print(f"  固定: SLBuf=0.5ATR, MaxPosMult=2.0, 噪音门控+动态spread")
print(f"{'='*70}")

set_files = {}
for key, label, ov in ALL_VARIANTS:
    set_files[key] = make_set(f'nkss_{key}', ov, base='v11xau-qs3.set')

results = {}
done = 0
for vkey, vlabel, ov in ALL_VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1
        key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<42} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt_silent(f'nkss_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=${r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:
            print('FAILED')

# ===== 汇总 =====
ref_off = {m: results.get(f'REF_OFF_{m}', {}) for m in ['2505', '2605']}
ref_loose = {m: results.get(f'REF_LOOSE_{m}', {}) for m in ['2505', '2605']}

print(f"\n{'='*120}")
print(f"  QS3 噪声门控甜点扫描 — 结果")
print(f"{'='*120}")

# 基线对比
print(f"\n  --- 基线 ---")
print(f"  {'变体':<48} {'2505交易':>6} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605交易':>6} {'d':>4} {'PF':>5} {'PnL':>10}")
print(f"  {'-'*110}")
for vkey, vlabel, _ in ALL_VARIANTS[:3]:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        print(f"  {vlabel:<48} {r25['count']:>6} {r25['daily']:>4.1f} {r25['pf']:>5.2f} "
              f"${r25['pnl']:>+9.2f} | {r26['count']:>6} {r26['daily']:>4.1f} {r26['pf']:>5.2f} "
              f"${r26['pnl']:>+9.2f}")

# Line A: Lookback sweep
print(f"\n  --- 线A: Lookback扫描 (固定ratio=0.30, range=0.18) ---")
print(f"  {'变体':<48} {'2505T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'dREF_OFF25':>10} {'dREF_OFF26':>10}")
print(f"  {'-'*115}")
for vkey, vlabel, _ in ALL_VARIANTS[3:8]:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        d25 = r25['pnl'] - ref_off['2505'].get('pnl', 0)
        d26 = r26['pnl'] - ref_off['2605'].get('pnl', 0)
        mark = ' [2605+]' if r26['pnl'] > 0 else ''
        mark += ' [!G]' if ref_off['2505'].get('pnl', 0) > 0 and d25 < -abs(ref_off['2505']['pnl']) * 0.05 else ''
        print(f"  {vlabel:<48} {r25['count']:>5} {r25['daily']:>4.1f} {r25['pf']:>5.2f} "
              f"${r25['pnl']:>+9.2f} | {r26['count']:>5} {r26['daily']:>4.1f} {r26['pf']:>5.2f} "
              f"${r26['pnl']:>+9.2f} | ${d25:>+9.0f} ${d26:>+9.0f}{mark}")

# Line B: Ratio sweep
print(f"\n  --- 线B: MinDirRatio扫描 (固定lookback=20, range=0.18) ---")
print(f"  {'变体':<48} {'2505T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'dREF_OFF25':>10} {'dREF_OFF26':>10}")
print(f"  {'-'*115}")
for vkey, vlabel, _ in ALL_VARIANTS[8:13]:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        d25 = r25['pnl'] - ref_off['2505'].get('pnl', 0)
        d26 = r26['pnl'] - ref_off['2605'].get('pnl', 0)
        mark = ' [2605+]' if r26['pnl'] > 0 else ''
        mark += ' [!G]' if ref_off['2505'].get('pnl', 0) > 0 and d25 < -abs(ref_off['2505']['pnl']) * 0.05 else ''
        print(f"  {vlabel:<48} {r25['count']:>5} {r25['daily']:>4.1f} {r25['pf']:>5.2f} "
              f"${r25['pnl']:>+9.2f} | {r26['count']:>5} {r26['daily']:>4.1f} {r26['pf']:>5.2f} "
              f"${r26['pnl']:>+9.2f} | ${d25:>+9.0f} ${d26:>+9.0f}{mark}")

# Line C: RangeATR sweep
print(f"\n  --- 线C: MaxRangeATR扫描 (固定lookback=20, ratio=0.30) ---")
print(f"  {'变体':<48} {'2505T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'dREF_OFF25':>10} {'dREF_OFF26':>10}")
print(f"  {'-'*115}")
for vkey, vlabel, _ in ALL_VARIANTS[13:]:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    if r25 and r26:
        d25 = r25['pnl'] - ref_off['2505'].get('pnl', 0)
        d26 = r26['pnl'] - ref_off['2605'].get('pnl', 0)
        mark = ' [2605+]' if r26['pnl'] > 0 else ''
        mark += ' [!G]' if ref_off['2505'].get('pnl', 0) > 0 and d25 < -abs(ref_off['2505']['pnl']) * 0.05 else ''
        print(f"  {vlabel:<48} {r25['count']:>5} {r25['daily']:>4.1f} {r25['pf']:>5.2f} "
              f"${r25['pnl']:>+9.2f} | {r26['count']:>5} {r26['daily']:>4.1f} {r26['pf']:>5.2f} "
              f"${r26['pnl']:>+9.2f} | ${d25:>+9.0f} ${d26:>+9.0f}{mark}")

# 双月最佳排名
print(f"\n  --- 双月净合计排名 (目标: 2605>0且2505不退) ---")
dual = {}
for vkey, vlabel, _ in ALL_VARIANTS:
    r25 = results.get(f'{vkey}_2505', {}).get('pnl', -99999)
    r26 = results.get(f'{vkey}_2605', {}).get('pnl', -99999)
    if r25 > -99999 and r26 > -99999:
        net = r25 + r26
        dual[vkey] = (vlabel, net, r25, r26)
        ok2605 = ' ✅ 2605正' if r26 > 0 else ''
        ok2505 = ' 🟢 2505不退' if r25 >= ref_off['2505'].get('pnl', 0) * 0.90 else ''
        print(f"  {vlabel:<48} 合计${net:>+9.2f}  2505=${r25:>+,.0f}  2605=${r26:>+,.2f}{ok2605}{ok2505}")

print(f"\n[DONE]")
