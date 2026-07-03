#!/usr/bin/env python3
"""QS3 v3: Fine-tune noise gate strictness + P1 SL buffer for dual-month profit."""
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
MONTHS = [('2505','2025.05.01','2025.05.31'),('2605','2026.05.01','2026.05.31')]

# Base NOISE params
NOISE_BASE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
              'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpEnableMTF':'false'}

VARIANTS = [
    # Reference baselines
    ('REF_OFF', 'REF-QS3-OFF', {}),
    ('REF_N30', 'REF-NOISE(lb30/r35)', {**NOISE_BASE,
        'InpTickNoiseGateLookback':'30','InpTickNoiseGateMinDirRatio':'0.35',
        'InpTickNoiseGateMaxRangeATR':'0.15'}),

    # === Noise strictness sweep ===
    # Looser: lookback 15, ratio 0.25
    ('N_L15R25', 'N-lb15r025', {**NOISE_BASE,
        'InpTickNoiseGateLookback':'15','InpTickNoiseGateMinDirRatio':'0.25',
        'InpTickNoiseGateMaxRangeATR':'0.20'}),
    # Mid-loose: lookback 20, ratio 0.30
    ('N_L20R30', 'N-lb20r030', {**NOISE_BASE,
        'InpTickNoiseGateLookback':'20','InpTickNoiseGateMinDirRatio':'0.30',
        'InpTickNoiseGateMaxRangeATR':'0.18'}),
    # Tighter: lookback 30, ratio 0.45
    ('N_L30R45', 'N-lb30r045', {**NOISE_BASE,
        'InpTickNoiseGateLookback':'30','InpTickNoiseGateMinDirRatio':'0.45',
        'InpTickNoiseGateMaxRangeATR':'0.12'}),

    # === P1 (SL buf 0.5) + Noise sweep ===
    ('P1N_L15', 'P1(SL.5)+N-lb15r25', {**NOISE_BASE,
        'InpTickNoiseGateLookback':'15','InpTickNoiseGateMinDirRatio':'0.25',
        'InpTickNoiseGateMaxRangeATR':'0.20','InpSLBufferATR':'0.5'}),
    ('P1N_L20', 'P1(SL.5)+N-lb20r30', {**NOISE_BASE,
        'InpTickNoiseGateLookback':'20','InpTickNoiseGateMinDirRatio':'0.30',
        'InpTickNoiseGateMaxRangeATR':'0.18','InpSLBufferATR':'0.5'}),
    ('P1N_L30', 'P1(SL.5)+N-lb30r35', {**NOISE_BASE,
        'InpTickNoiseGateLookback':'30','InpTickNoiseGateMinDirRatio':'0.35',
        'InpTickNoiseGateMaxRangeATR':'0.15','InpSLBufferATR':'0.5'}),
    ('P1N_T45', 'P1(SL.5)+N-lb30r45', {**NOISE_BASE,
        'InpTickNoiseGateLookback':'30','InpTickNoiseGateMinDirRatio':'0.45',
        'InpTickNoiseGateMaxRangeATR':'0.12','InpSLBufferATR':'0.5'}),
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
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows_raw = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    pending = []; trades = []
    for row_html in rows_raw:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html)
        if len(cells) != 13: continue
        ct = cells[3].strip()
        if ct == 'balance': continue
        io = cells[4].strip()
        try: pnl = float(cells[10].strip().replace(' ','').replace(',',''))
        except: pnl = 0.0
        if io == 'in': pending.append(1)
        elif io == 'out' and pending: pending.pop(0); trades.append(pnl)
    wins = [t for t in trades if t>0]; losses = [t for t in trades if t<0]
    gw = sum(wins) if wins else 0; gl = abs(sum(losses)) if losses else 0
    return {'count':len(trades),'pnl':sum(trades),'wins':len(wins),'losses':len(losses),
            'wr':len(wins)/len(trades)*100 if trades else 0,
            'pf':gw/gl if gl>0 else (999 if gw>0 else 0),'daily':len(trades)/31}

# ===== MAIN =====
total = len(VARIANTS) * 2
print(f"\n{'='*80}")
print(f"  QS3 v3: Noise strictness sweep x P1 SL buffer ({total} backtests)")
print(f"{'='*80}\n")

set_files = {}
for key, label, overrides in VARIANTS:
    set_files[key] = make_set(key, overrides)

results = {}
done = 0
for vkey, vlabel, _ in VARIANTS:
    for mkey, mfrom, mto in MONTHS:
        done += 1
        key = f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<28} {mkey} ', end='', flush=True)
        kill_mt5()
        r = run_bt(f'v3_{vkey}_{mkey}', set_files[vkey], mfrom, mto)
        results[key] = r
        if r:
            print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                  f'PnL=${r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else: print('FAILED')

# ===== SUMMARY =====
ref_off25 = results.get('REF_OFF_2505',{})
ref_off26 = results.get('REF_OFF_2605',{})
ref_n25 = results.get('REF_N30_2505',{})
ref_n26 = results.get('REF_N30_2605',{})

print(f"\n{'='*80}")
print(f"  Results: 好月2505 vs 坏月2605 — Noise松紧度+P1扫描")
print(f"{'='*80}")
print(f"\n{'Variant':<30} | {'2505 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'d2505':>8} {'d2605':>8}")
print('-'*110)

for vkey, vlabel, _ in VARIANTS:
    r25 = results.get(f'{vkey}_2505',{})
    r26 = results.get(f'{vkey}_2605',{})
    if not r25 or not r26: continue

    is_off = vkey == 'REF_OFF'
    is_noise_ref = vkey == 'REF_N30'

    if is_off:
        base25, base26 = ref_off25.get('pnl',0), ref_off26.get('pnl',0)
    elif is_noise_ref:
        base25, base26 = ref_n25.get('pnl',0), ref_n26.get('pnl',0)
    else:
        base25, base26 = ref_n25.get('pnl',0), ref_n26.get('pnl',0)  # compare vs NOISE baseline

    d25 = r25['pnl'] - base25
    d26 = r26['pnl'] - base26

    warn = ''
    if base25 > 0 and d25 < -abs(base25)*0.05: warn += ' [!G]'
    if r26['pnl'] > 0: warn += ' [+2605]'

    print(f'{vlabel:<30} | {r25["count"]:>5} {r25["daily"]:>4.1f} {r25["pf"]:>5.2f} ${r25["pnl"]:>+9.2f} | '
          f'{r26["count"]:>5} {r26["daily"]:>4.1f} {r26["pf"]:>5.2f} ${r26["pnl"]:>+9.2f} | '
          f'${d25:>+7.0f} ${d26:>+8.2f}{warn}')

print(f"\n[DONE]  [!G]=好月退化>5%  [+2605]=坏月盈利")
