#!/usr/bin/env python3
"""QS3 pos_mult boost fix: cap InpBoostIn1HOB + InpDeepEntryBoost + InpMaxPosMult."""
import os, subprocess, time, re, shutil
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

NOISE_BASE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
              'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpEnableMTF':'false'}

VARIANTS = [
    # Baselines
    ('REF_OFF', 'REF-QS3-OFF', {}),
    ('REF_N',   'REF-QS3+NOISE(lb20r30)', {**NOISE_BASE,
        'InpTickNoiseGateLookback':'20','InpTickNoiseGateMinDirRatio':'0.30',
        'InpTickNoiseGateMaxRangeATR':'0.18'}),

    # === P0: Boost dampening (fix the inverted multiplier) ===
    # P0a: Halve both boost factors
    ('B_HALF', 'P0a-半boost(H1:1.0+DE:0.75)', {
        'InpBoostIn1HOB':'1.0','InpDeepEntryBoost':'0.75'}),
    # P0b: Disable boosts entirely (flat position sizing)
    ('B_FLAT', 'P0b-全平仓(boost全禁)', {
        'InpBoostIn1HOB':'0.0','InpDeepEntryBoost':'0.0','InpMaxPosMult':'1.0'}),
    # P0c: Cap max multiplier at 2.0
    ('B_CAP2', 'P0c-MaxMult上限2.0', {
        'InpMaxPosMult':'2.0'}),

    # === P1: SL buffer (already proven) ===
    ('SL5', 'P1-SLbuf0.5', {'InpSLBufferATR':'0.5'}),

    # === P0+P1 combos ===
    ('B_HALF_SL5', 'P0a+SL5', {
        'InpBoostIn1HOB':'1.0','InpDeepEntryBoost':'0.75','InpSLBufferATR':'0.5'}),
    ('B_CAP2_SL5', 'P0c+SL5', {
        'InpMaxPosMult':'2.0','InpSLBufferATR':'0.5'}),

    # === P0+P1+NOISE (loose) ===
    ('B_HALF_N_SL5', 'P0a+NOISE(lb20)+SL5', {**NOISE_BASE,
        'InpTickNoiseGateLookback':'20','InpTickNoiseGateMinDirRatio':'0.30',
        'InpTickNoiseGateMaxRangeATR':'0.18',
        'InpBoostIn1HOB':'1.0','InpDeepEntryBoost':'0.75','InpSLBufferATR':'0.5'}),
    ('B_CAP2_N_SL5', 'P0c+NOISE(lb20)+SL5', {**NOISE_BASE,
        'InpTickNoiseGateLookback':'20','InpTickNoiseGateMinDirRatio':'0.30',
        'InpTickNoiseGateMaxRangeATR':'0.18',
        'InpMaxPosMult':'2.0','InpSLBufferATR':'0.5'}),
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
    html=htm_path.read_bytes().decode('utf-16-le',errors='replace')
    rows=re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>',html,re.DOTALL)
    pending=[];trades=[]
    for r in rows:
        cells=re.findall(r'<td[^>]*>(.*?)</td>',r)
        if len(cells)!=13: continue
        if cells[3].strip()=='balance': continue
        try:pnl=float(cells[10].strip().replace(' ','').replace(',',''))
        except:pnl=0.0
        if cells[4].strip()=='in':pending.append(1)
        elif cells[4].strip()=='out' and pending:pending.pop(0);trades.append(pnl)
    w=[t for t in trades if t>0];l=[t for t in trades if t<0]
    gw=sum(w)if w else 0;gl=abs(sum(l))if l else 0
    return{'count':len(trades),'pnl':sum(trades),'wins':len(w),'losses':len(l),
           'wr':len(w)/len(trades)*100 if trades else 0,
           'pf':gw/gl if gl>0 else(999 if gw>0 else 0),'daily':len(trades)/31}

# ===== MAIN =====
total=len(VARIANTS)*2
print(f"\n{'='*80}")
print(f"  QS3 pos_mult fix: {len(VARIANTS)} variants x 2 months = {total} BTs")
print(f"{'='*80}\n")

for key,label,ov in VARIANTS:
    make_set(key,ov)

results={}
done=0
for vkey,vlabel,_ in VARIANTS:
    for mkey,mfrom,mto in MONTHS:
        done+=1;key=f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<35} {mkey} ',end='',flush=True)
        kill_mt5()
        r=run_bt(f'pmf_{vkey}_{mkey}',f'v11xau-{vkey}.set',mfrom,mto)
        results[key]=r
        if r:print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  PnL=${r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:print('FAILED')

# ===== SUMMARY =====
ref_off25=results.get('REF_OFF_2505',{})
ref_off26=results.get('REF_OFF_2605',{})
ref_n25=results.get('REF_N_2505',{})
ref_n26=results.get('REF_N_2605',{})

print(f"\n{'='*80}")
print(f"  Results: pos_mult fix — keep 2505 profit + make 2605 profitable")
print(f"{'='*80}")
print(f"\n{'Variant':<38} | {'2505 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'d2505':>8} {'d2605':>8}")
print('-'*115)

for vkey,vlabel,_ in VARIANTS:
    r25=results.get(f'{vkey}_2505',{});r26=results.get(f'{vkey}_2605',{})
    if not r25 or not r26: continue
    is_off=vkey=='REF_OFF';is_nref=vkey=='REF_N'
    if is_off:base25,base26=ref_off25.get('pnl',0),ref_off26.get('pnl',0)
    elif is_nref:base25,base26=ref_n25.get('pnl',0),ref_n26.get('pnl',0)
    else:
        # Compare OFF variants vs OFF baseline, NOISE variants vs NOISE baseline
        if 'N_' in vkey or '_N_' in vkey:base25,base26=ref_n25.get('pnl',0),ref_n26.get('pnl',0)
        else:base25,base26=ref_off25.get('pnl',0),ref_off26.get('pnl',0)
    d25=r25['pnl']-base25;d26=r26['pnl']-base26
    warn=''
    if base25>0 and d25<-abs(base25)*0.05:warn+=' [!G]'
    if r26['pnl']>0:warn+=' [OK]'
    print(f'{vlabel:<38} | {r25["count"]:>5} {r25["daily"]:>4.1f} {r25["pf"]:>5.2f} ${r25["pnl"]:>+9.2f} | '
          f'{r26["count"]:>5} {r26["daily"]:>4.1f} {r26["pf"]:>5.2f} ${r26["pnl"]:>+9.2f} | '
          f'${d25:>+7.0f} ${d26:>+8.2f}{warn}')

print(f"\n[DONE]  [!G]=good month degraded  [OK]=bad month profitable")
