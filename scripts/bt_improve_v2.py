#!/usr/bin/env python3
"""QS3 improvement v2: targeted hypotheses for 2605 profitability."""
import os, subprocess, time, re, sys, shutil
from pathlib import Path
from bt_shared import run_bt_silent, kill_mt5

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'
PROJECT = Path(__file__).resolve().parent.parent
PRESETS = PROJECT / 'mql5' / 'Presets'
MT5_PROFILES = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'

DEPOSIT = 200
MONTHS = [
    ('2505', '2025.05.01', '2025.05.31'),
    ('2605', '2026.05.01', '2026.05.31'),
]

# === Improved hypotheses based on Phase 1-2 data ===
VARIANTS = [
    # Baseline
    ('BL_OFF',   '基线QS3-OFF',  {}),
    ('BL_NOISE', '基线QS3+NOISE', {'InpEnableTickNoiseGate':'true','InpTickNoiseGateLookback':'30',
                                    'InpTickNoiseGateMinDirRatio':'0.35',
                                    'InpTickNoiseGateMaxRangeATR':'0.15',
                                    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5',
                                    'InpEnableDynamicSpread':'true','InpEnableMTF':'false'}),
    # H1: Block toxic hours (H00,H07,H12,H17,H18 UTC) — save ~$112 in 2605
    ('H1_NOISE', 'H1-禁有毒时段+NOISE', {'InpEnableTickNoiseGate':'true','InpTickNoiseGateLookback':'30',
                                          'InpTickNoiseGateMinDirRatio':'0.35',
                                          'InpTickNoiseGateMaxRangeATR':'0.15',
                                          'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5',
                                          'InpEnableDynamicSpread':'true','InpEnableMTF':'false',
                                          'InpNoEntryHours':'0,7,12,17,18'}),
    # H2: Block toxic hours on QS3 OFF (more aggressive — test if OFF can be saved)
    ('H2_OFF',   'H2-禁有毒时段OFF', {'InpNoEntryHours':'0,7,12,17,18'}),

    # H3: Cooldown after 3 consecutive losses (break MaxCL=9 streaks)
    ('H3_OFF',   'H3-连亏3冷2bar',  {'InpCooldownBars':'2'}),

    # H4: Reduce max entries per OB + reentry cooldown
    ('H4_OFF',   'H4-OB限3次+冷3分', {'InpMaxEntriesPerOB':'3','InpOBReentryCooldownMin':'3'}),

    # H5: Combined — block toxic hours + tighter entry control
    ('H5_OFF',   'H5-H2+H3+H4合体', {'InpNoEntryHours':'0,7,12,17,18',
                                      'InpCooldownBars':'2',
                                      'InpMaxEntriesPerOB':'3',
                                      'InpOBReentryCooldownMin':'3'}),

    # H6: H5 + NOISE (ultimate defense)
    ('H6_NOISE', 'H6-全防御+NOISE', {'InpNoEntryHours':'0,7,12,17,18',
                                      'InpCooldownBars':'2',
                                      'InpMaxEntriesPerOB':'3',
                                      'InpOBReentryCooldownMin':'3',
                                      'InpEnableTickNoiseGate':'true','InpTickNoiseGateLookback':'30',
                                      'InpTickNoiseGateMinDirRatio':'0.35',
                                      'InpTickNoiseGateMaxRangeATR':'0.15',
                                      'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5',
                                      'InpEnableDynamicSpread':'true','InpEnableMTF':'false'}),
]

def make_set(key, overrides):
    src = PRESETS / 'v11xau-qs3.set'
    dst = PRESETS / f'v11xau-{key}.set'
    lines = src.read_text(encoding='utf-8').splitlines()
    omap = dict(overrides)
    out = []
    for line in lines:
        if '=' in line:
            param = line.split('=')[0].strip()
            if param in omap:
                out.append(f'{param}={omap[param]}')
                del omap[param]
                continue
        out.append(line)
    for p, v in omap.items():
        out.append(f'{p}={v}')
    dst.write_text('\n'.join(out), encoding='utf-8')
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
total = len(VARIANTS) * len(MONTHS)
print(f"\n{'='*80}")
print(f"  QS3 改进 v2: {len(VARIANTS)}变体 x 2月 = {total}回测")
print(f"{'='*80}\n")

print("Generating .set variants...")
set_files = {}
for key, label, overrides in VARIANTS:
    set_files[key] = make_set(key, overrides)
    print(f"  {label:<30} -> {set_files[key]}")

results = {}
done = 0
for vkey, vlabel, _ in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1
        name = f'v2_{vkey}_{mkey}'
        key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<32} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt(name, set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            pnl_s = f'${r["pnl"]:+.2f}'
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL={pnl_s:>12}  day={r["daily"]:.1f}')
        else:
            print('FAILED')

# ===== SUMMARY =====
# Get baselines
base_off_25 = results.get('BL_OFF_2505', {})
base_off_26 = results.get('BL_OFF_2605', {})
base_n_25 = results.get('BL_NOISE_2505', {})
base_n_26 = results.get('BL_NOISE_2605', {})

print(f"\n{'='*80}")
print(f"  Results: 2505 vs 2605")
print(f"{'='*80}")

# Table header
hdr = f"{'Variant':<33} | {'2505 T':>6} {'day':>5} {'PF':>6} {'PnL':>10} | {'2605 T':>6} {'day':>5} {'PF':>6} {'PnL':>10} | {'d2505':>8} {'d2605':>8}"
print(f"\n{hdr}")
print('-' * 105)

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505', {})
    r26 = results.get(f'{vkey}_2605', {})

    is_noise = 'NOISE' in vkey
    base_pnl_25 = base_n_25.get('pnl', 0) if is_noise else base_off_25.get('pnl', 0)
    base_pnl_26 = base_n_26.get('pnl', 0) if is_noise else base_off_26.get('pnl', 0)

    d25 = (r25.get('pnl', 0) - base_pnl_25) if r25 else 0
    d26 = (r26.get('pnl', 0) - base_pnl_26) if r26 else 0

    ds25 = f'${d25:+.0f}' if r25 else 'N/A'
    ds26 = f'${d26:+.0f}' if r26 else 'N/A'

    # Warning if good month degraded >5% or bad month worsened
    warn = ''
    if r25 and base_pnl_25 > 0 and d25 < -abs(base_pnl_25)*0.05:
        warn += ' [!G]'
    if r26 and r26.get('pnl', 0) > 0:
        warn += ' [OK]'

    pnl25 = f'${r25["pnl"]:+.2f}' if r25 else 'N/A'
    pnl26 = f'${r26["pnl"]:+.2f}' if r26 else 'N/A'

    print(f'{vlabel:<33} | {r25.get("count",0):>6} {r25.get("daily",0):>4.1f} '
          f'{r25.get("pf",0):>5.2f} {pnl25:>10} | '
          f'{r26.get("count",0):>6} {r26.get("daily",0):>4.1f} '
          f'{r26.get("pf",0):>5.2f} {pnl26:>10} | '
          f'{ds25:>8} {ds26:>8}{warn}')

print(f"\n[DONE]  Key: [!G]=好月退化>5%  [OK]=坏月转正")
