#!/usr/bin/env python3
"""QS3 improvement tests: P0-BE / P1-SL / combined, on 2505+2605."""
import os, subprocess, time, re, sys, shutil
from pathlib import Path
from collections import defaultdict
from bt_shared import run_bt_silent, kill_mt5

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'
PROJECT = Path(__file__).resolve().parent.parent
PRESETS = PROJECT / 'mql5' / 'Presets'

DEPOSIT = 200
TESTS = [
    ('2505', '2025.05.01', '2025.05.31'),
    ('2605', '2026.05.01', '2026.05.31'),
]

# Variants: each is (key, label, param_overrides)
VARIANTS = [
    ('QS3_base',    'QS3-OFF(基线)',  {}),
    ('QS3_NOISE',   'QS3+NOISE(基线)', {'InpEnableTickNoiseGate':'true',
                                        'InpTickNoiseGateLookback':'30',
                                        'InpTickNoiseGateMinDirRatio':'0.35',
                                        'InpTickNoiseGateMaxRangeATR':'0.15',
                                        'InpMinSLSpreadMult':'5.0',
                                        'InpOBTouchConfirmTicks':'5',
                                        'InpEnableDynamicSpread':'true',
                                        'InpEnableMTF':'false'}),
    # P0: BE推后
    ('QS3_BE80',    'P0-BE0.8/0.6',   {'InpBreakevenR':'0.8','InpBreakevenLockR':'0.6'}),
    ('QS3_N_BE80',  'P0-N+BE0.8/0.6', {'InpBreakevenR':'0.8','InpBreakevenLockR':'0.6',
                                        'InpEnableTickNoiseGate':'true',
                                        'InpTickNoiseGateLookback':'30',
                                        'InpTickNoiseGateMinDirRatio':'0.35',
                                        'InpTickNoiseGateMaxRangeATR':'0.15',
                                        'InpMinSLSpreadMult':'5.0',
                                        'InpOBTouchConfirmTicks':'5',
                                        'InpEnableDynamicSpread':'true',
                                        'InpEnableMTF':'false'}),
    # P1: SL缓冲加大
    ('QS3_SL50',    'P1-SLbuf0.5',     {'InpSLBufferATR':'0.5'}),
    # P0+P1 combined
    ('QS3_BE80SL50','P0+P1合体',       {'InpBreakevenR':'0.8','InpBreakevenLockR':'0.6',
                                        'InpSLBufferATR':'0.5'}),
    ('QS3_N_BE80SL50','P0+P1+NOISE',   {'InpBreakevenR':'0.8','InpBreakevenLockR':'0.6',
                                        'InpSLBufferATR':'0.5',
                                        'InpEnableTickNoiseGate':'true',
                                        'InpTickNoiseGateLookback':'30',
                                        'InpTickNoiseGateMinDirRatio':'0.35',
                                        'InpTickNoiseGateMaxRangeATR':'0.15',
                                        'InpMinSLSpreadMult':'5.0',
                                        'InpOBTouchConfirmTicks':'5',
                                        'InpEnableDynamicSpread':'true',
                                        'InpEnableMTF':'false'}),
]

MT5_PROFILES = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'

def make_set(base_name, key, overrides):
    """Create variant .set from base QS3, overwriting specified params."""
    src = PRESETS / 'v11xau-qs3.set'
    dst = PRESETS / f'v11xau-{key}.set'
    base_lines = src.read_text(encoding='utf-8').splitlines()
    override_map = dict(overrides)
    out = []
    for line in base_lines:
        if '=' in line:
            param = line.split('=')[0].strip()
            if param in override_map:
                out.append(f'{param}={override_map[param]}')
                del override_map[param]
                continue
        out.append(line)
    # Append any new params not in base
    for param, val in override_map.items():
        out.append(f'{param}={val}')
    dst.write_text('\n'.join(out), encoding='utf-8')
    # Copy to MT5 profiles
    MT5_PROFILES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(dst), str(MT5_PROFILES / f'v11xau-{key}.set'))
    return f'v11xau-{key}.set'

# kill_mt5 from bt_shared

def run_bt(name, set_name, df, dt):
    return run_bt_silent(name, set_name, df, dt, deposit=DEPOSIT)

def parse_report(htm_path):
    from bt_shared import parse_report as _pr
    return _pr(htm_path)

# ===== MAIN =====
print(f"\n{'='*80}")
print(f"  QS3 改进验证: 8变体 × 2月份 = 16个回测")
print(f"{'='*80}\n")

# Generate all .set files
print("生成 .set 变体...")
set_files = {}
for key, label, overrides in VARIANTS:
    fname = make_set('v11xau-qs3', key, overrides)
    set_files[key] = fname
    print(f"  {label:<18} → {fname}")

# Run all backtests
results = {}
total = len(VARIANTS) * len(TESTS)
done = 0
for vkey, vlabel, _ in VARIANTS:
    for mkey, mfrom, mto in TESTS:
        done += 1
        name = f'imp_{vkey}_{mkey}'
        key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<22} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt(name, set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=${r["pnl"]:>+8.2f}  (日{r["daily"]:.1f})')
        else:
            print('FAILED')

# ===== SUMMARY =====
print(f"\n{'='*80}")
print(f"  对比汇总: 2505(好月) vs 2605(坏月)")
print(f"{'='*80}")

# Baselines
base_off_25 = results.get('QS3_base_2505', {})
base_off_26 = results.get('QS3_base_2605', {})
base_n_25 = results.get('QS3_NOISE_2505', {})
base_n_26 = results.get('QS3_NOISE_2605', {})

print(f"\n{'变体':<22} | {'2505 交易':>6} {'日单':>5} {'PF':>6} {'PnL':>10} | {'2605 交易':>6} {'日单':>5} {'PF':>6} {'PnL':>10} | {'2605改善':>10}")
print('-' * 95)

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})
    imp = ''
    if r25 and r26:
        # Improvement = delta in 2605 minus relative degradation in 2505
        # Simplified: just show 2605 PnL difference from baseline
        base_pnl_26 = base_off_26.get('pnl', 0) if 'NOISE' not in vkey else base_n_26.get('pnl', 0)
        base_pnl_25 = base_off_25.get('pnl', 0) if 'NOISE' not in vkey else base_n_25.get('pnl', 0)
        delta_26 = r26['pnl'] - base_pnl_26
        delta_25 = r25['pnl'] - base_pnl_25
        imp = f'${delta_26:+.2f}'
        if abs(delta_25) > abs(base_pnl_25)*0.1 and delta_25 < 0:
            imp += ' ⚠️好月退化'

    print(f'{vlabel:<22} | {r25.get("count",0):>6} {r25.get("daily",0):>5.1f} '
          f'{r25.get("pf",0):>5.2f} ${r25.get("pnl",0):>+9.2f} | '
          f'{r26.get("count",0):>6} {r26.get("daily",0):>5.1f} '
          f'{r26.get("pf",0):>5.2f} ${r26.get("pnl",0):>+9.2f} | '
          f'{imp:>10}')

print(f"\n[DONE]")
