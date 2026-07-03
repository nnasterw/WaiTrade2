#!/usr/bin/env python3
"""Adaptive noise gate simulation: B3(HTF strong align) + noise gate variants.
Also test core fix: set InpMaxPosMult to 1.0 (flat) to fix inverted multiplier."""
import os, subprocess, time, re, shutil
from pathlib import Path
from bt_shared import run_bt_silent, kill_mt5

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
INI_DIR = MT5_DATA / 'Tester'
PROJECT = Path(__file__).resolve().parent.parent; PRESETS = PROJECT / 'mql5' / 'Presets'
MT5_PROFILES = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
DEPOSIT = 200
MONTHS = [('2505','2025.05.01','2025.05.31'),('2605','2026.05.01','2026.05.31')]

# Base protections
SL5  = {'InpSLBufferATR':'0.5'}
M1   = {'InpMaxPosMult':'1.0'}  # FLAT — fix inverted multiplier
M15  = {'InpMaxPosMult':'1.5'}  # soft cap

# HTF B3 alignment params
HTF_B3 = {'InpHTFNetPushAlignedMult':'1.5','InpHTFNetPushNeutralMult':'0.7',
          'InpHTFNetPushCounterMult':'0.3'}

# Noise gate levels
NK0  = {}  # no noise gate
NK_L15 = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
          'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpEnableMTF':'false',
          'InpTickNoiseGateLookback':'15','InpTickNoiseGateMinDirRatio':'0.25',
          'InpTickNoiseGateMaxRangeATR':'0.20'}
NK_L20 = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
          'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpEnableMTF':'false',
          'InpTickNoiseGateLookback':'20','InpTickNoiseGateMinDirRatio':'0.30',
          'InpTickNoiseGateMaxRangeATR':'0.18'}
NK_L10 = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
          'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpEnableMTF':'false',
          'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
          'InpTickNoiseGateMaxRangeATR':'0.25'}

VARIANTS = [
    # === BASELINES ===
    ('REF_B3',  'REF-B3(HTF+SL5+M2)',  {**SL5, 'InpMaxPosMult':'2.0', **HTF_B3}),
    ('REF_P1',  'REF-P1(SL5+NK20+M2)', {**SL5, 'InpMaxPosMult':'2.0', **NK_L20}),

    # === LINE E: B3 + noise gate (adaptive emulation) ===
    ('E1', 'B3+NK10(超轻噪)+M2', {**SL5, 'InpMaxPosMult':'2.0', **HTF_B3, **NK_L10}),
    ('E2', 'B3+NK15(轻噪)+M2',   {**SL5, 'InpMaxPosMult':'2.0', **HTF_B3, **NK_L15}),
    ('E3', 'B3+NK20(中噪)+M2',   {**SL5, 'InpMaxPosMult':'2.0', **HTF_B3, **NK_L20}),

    # === LINE F: Flat multiplier (fix inverted boost) ===
    ('F1', 'B3+SL5+M1(全平仓)',    {**SL5, **M1, **HTF_B3}),
    ('F2', 'B3+SL5+M1.5',          {**SL5, **M15, **HTF_B3}),

    # === LINE G: Flat multiplier + noise gate ===
    ('G1', 'B3+SL5+M1+NK15',    {**SL5, **M1, **HTF_B3, **NK_L15}),
    ('G2', 'B3+SL5+M1+NK20',    {**SL5, **M1, **HTF_B3, **NK_L20}),
    ('G3', 'B3+SL5+M1.5+NK20',  {**SL5, **M15, **HTF_B3, **NK_L20}),
]

def merge(*dicts):
    r = {}
    for d in dicts: r.update(d)
    return r

def make_set(key, overrides):
    src = PRESETS / 'v11xau-qs3.set'
    dst = PRESETS / f'v11xau-{key}.set'
    lines = src.read_text(encoding='utf-8').splitlines()
    omap = dict(overrides); out = []
    for line in lines:
        if '=' in line:
            param = line.split('=')[0].strip()
            if param in omap:
                out.append(f'{param}={omap[param]}')
                del omap[param]; continue
        out.append(line)
    for p, v in omap.items(): out.append(f'{p}={v}')
    dst.write_text('\n'.join(out), encoding='utf-8')
    MT5_PROFILES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(dst), str(MT5_PROFILES / f'v11xau-{key}.set'))
    return f'v11xau-{key}.set'

# kill_mt5 from bt_shared

def run_bt(name, set_name, df, dt):
    return run_bt_silent(name, set_name, df, dt, deposit=DEPOSIT)

def parse_report(htm_path):
    html=htm_path.read_bytes().decode('utf-16-le',errors='replace')
    rows=re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>',html,re.DOTALL)
    pending=[];trades=[]
    for r in rows:
        cells=re.findall(r'<td[^>]*>(.*?)</td>',r)
        if len(cells)!=13:continue
        if cells[3].strip()=='balance':continue
        try:pnl=float(cells[10].strip().replace(' ','').replace(',',''))
        except:pnl=0.0
        if cells[4].strip()=='in':pending.append(1)
        elif cells[4].strip()=='out' and pending:pending.pop(0);trades.append(pnl)
    w=[t for t in trades if t>0];l=[t for t in trades if t<0]
    gw=sum(w)if w else 0;gl=abs(sum(l))if l else 0
    return{'count':len(trades),'pnl':sum(trades),'wins':len(w),'losses':len(l),
           'wr':len(w)/len(trades)*100 if trades else 0,
           'pf':gw/gl if gl>0 else(999 if gw>0 else 0),'daily':len(trades)/31}

total=len(VARIANTS)*2
print(f"\n{'='*80}")
print(f"  ADAPTIVE SIM: B3+Noise {len(VARIANTS)}v x 2m = {total}BT")
print(f"{'='*80}")

for key,label,ov in VARIANTS:make_set(key,ov)

ref_b3_25=0;ref_b3_26=0;ref_p1_25=0;ref_p1_26=0;results={};done=0
for vkey,vlabel,_ in VARIANTS:
    for mkey,mfrom,mto in MONTHS:
        done+=1;key=f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<35} {mkey} ',end='',flush=True)
        kill_mt5()
        r=run_bt(f'as_{vkey}_{mkey}',f'v11xau-{vkey}.set',mfrom,mto)
        results[key]=r
        if vkey=='REF_B3':
            if mkey=='2505':ref_b3_25=r['pnl']if r else 0
            else:ref_b3_26=r['pnl']if r else 0
        if vkey=='REF_P1':
            if mkey=='2505':ref_p1_25=r['pnl']if r else 0
            else:ref_p1_26=r['pnl']if r else 0
        if r:print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                    f'PnL=${r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:print('FAILED')

print(f"\n{'='*90}")
print(f"  RESULTS — B3+Noise Adaptive Emulation")
print(f"{'='*90}")
print(f"\n{'Line':<5} {'Variant':<37} {'2505 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'dP1_25':>8} {'dP1_26':>8} {'dB3_25':>8} {'dB3_26':>8}")
print('-'*125)

best_dual=0;best_key=None
for vkey,vlabel,_ in VARIANTS:
    r25=results.get(f'{vkey}_2505',{});r26=results.get(f'{vkey}_2605',{})
    if not r25 or not r26:continue
    dp1_25=r25['pnl']-ref_p1_25;dp1_26=r26['pnl']-ref_p1_26
    db3_25=r25['pnl']-ref_b3_25;db3_26=r26['pnl']-ref_b3_26
    warn=''
    if r26['pnl']>0:warn+=' [2605+]'
    net=r25['pnl']+r26['pnl']

    line=vkey.split('_')[0] if '_' in vkey else vkey[:2]
    print(f'{line:<5} {vlabel:<37} {r25["count"]:>5} {r25["daily"]:>4.1f} {r25["pf"]:>5.2f} '
          f'${r25["pnl"]:>+9.2f} | {r26["count"]:>5} {r26["daily"]:>4.1f} {r26["pf"]:>5.2f} '
          f'${r26["pnl"]:>+9.2f} | ${dp1_25:>+7.0f} ${dp1_26:>+8.2f} '
          f'${db3_25:>+7.0f} ${db3_26:>+8.2f}{warn}')

print(f"\n[DONE]")
