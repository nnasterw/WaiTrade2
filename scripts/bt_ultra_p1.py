#!/usr/bin/env python3
"""Ultra analysis: P1 strategy — noise/tick/resonance/OB structural filters.
Goal: decouple noise filtering from market regime. Test structural vs tick-level filters."""
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

SL5 = {'InpSLBufferATR':'0.5', 'InpMaxPosMult':'2.0'}

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
    ('REF_OFF',  'REF-QS3OFF', {}),
    ('REF_P1',   'REF-P1(SL5+NK20+M2)', {**SL5, **NK_L20}),

    # === LINE A: Structural OB quality filters (NO noise gate) ===
    # Higher OB body requirement + stronger OB
    ('A1_OBQ',   'A1-SL5+OB强质', {**SL5,
        'InpMinOBBodyPct':'60','InpMinOBStrength':'0.7'}),
    # + Bounce confirmation
    ('A2_OBB',   'A2-SL5+OB强质+Bounce确认', {**SL5,
        'InpMinOBBodyPct':'60','InpMinOBStrength':'0.7',
        'InpBounceConfirmBars':'1'}),
    # + Touch confirmation
    ('A3_OBT',   'A3-SL5+OB强质+Touch5', {**SL5,
        'InpMinOBBodyPct':'60','InpMinOBStrength':'0.7',
        'InpOBTouchConfirmTicks':'5','InpMinSLSpreadMult':'5.0'}),

    # === LINE B: HTF trend filter strengthening (NO noise gate) ===
    # Stronger counter-trend dampening
    ('B1_HTF',   'B1-SL5+HTF强衰减', {**SL5,
        'InpHTFNetPushCounterMult':'0.3',
        'InpHTFNetPushMinATR':'0.5'}),
    # + Block counter-trend entirely
    ('B2_HTF0',  'B2-SL5+HTF禁逆势', {**SL5,
        'InpHTFNetPushCounterMult':'0.0'}),
    # + Require stronger alignment
    ('B3_HTFA',  'B3-SL5+HTF强对齐', {**SL5,
        'InpHTFNetPushAlignedMult':'1.5',
        'InpHTFNetPushNeutralMult':'0.7',
        'InpHTFNetPushCounterMult':'0.3'}),

    # === LINE C: Light noise + HTF combo ===
    ('C1_NH',    'C1-SL5+轻噪(lb10)+HTF强', {**SL5, **NK_L10,
        'InpHTFNetPushCounterMult':'0.3'}),
    ('C2_NH2',   'C2-SL5+轻噪(lb15)+HTF强', {**SL5, **NK_L15,
        'InpHTFNetPushCounterMult':'0.3'}),
    ('C3_NH3',   'C3-SL5+轻噪(lb15)+HTF禁逆势', {**SL5, **NK_L15,
        'InpHTFNetPushCounterMult':'0.0'}),

    # === LINE D: Adaptive noise — loose noise + structural backup ===
    ('D1_LOOSE', 'D1-SL5+超轻噪(lb10)', {**SL5, **NK_L10}),
    ('D2_LOOS2', 'D2-SL5+超轻噪(lb10)+Touch10', {**SL5, **NK_L10,
        'InpOBTouchConfirmTicks':'10'}),
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
print(f"  ULTRA P1: structural vs tick filters ({len(VARIANTS)}var x 2mo = {total}BT)")
print(f"{'='*80}")

for key,label,ov in VARIANTS: make_set(key,ov)

results={};done=0
for vkey,vlabel,_ in VARIANTS:
    for mkey,mfrom,mto in MONTHS:
        done+=1;key=f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<42} {mkey} ',end='',flush=True)
        kill_mt5()
        r=run_bt(f'up1_{vkey}_{mkey}',f'v11xau-{vkey}.set',mfrom,mto)
        results[key]=r
        if r:print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                    f'PnL=${r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:print('FAILED')

# ===== SUMMARY =====
ref_off_25=results.get('REF_OFF_2505',{});ref_off_26=results.get('REF_OFF_2605',{})
ref_p1_25=results.get('REF_P1_2505',{});ref_p1_26=results.get('REF_P1_2605',{})

print(f"\n{'='*90}")
print(f"  RESULTS — 2505 must not degrade from P1(+$236), 2605 must be profitable")
print(f"{'='*90}")
print(f"\n{'Line':<5} {'Variant':<44} {'2505 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'vsP1_25':>8} {'vsP1_26':>8}")
print('-'*120)

best_net = -999999
best_key = None

for vkey,vlabel,_ in VARIANTS:
    r25=results.get(f'{vkey}_2505',{});r26=results.get(f'{vkey}_2605',{})
    if not r25 or not r26: continue
    d25=r25['pnl']-ref_p1_25.get('pnl',0)
    d26=r26['pnl']-ref_p1_26.get('pnl',0)
    warn=''
    if d25<-abs(ref_p1_25.get('pnl',1))*0.05:warn+=' [!G]'
    if r26['pnl']>0:warn+=' [OK]'

    net=r25['pnl']+r26['pnl']
    if net>best_net and r26['pnl']>0:best_net=net;best_key=vkey

    # Determine line
    line=vkey.split('_')[0] if '_' in vkey else vkey[:2]
    print(f'{line:<5} {vlabel:<44} {r25["count"]:>5} {r25["daily"]:>4.1f} {r25["pf"]:>5.2f} '
          f'${r25["pnl"]:>+9.2f} | {r26["count"]:>5} {r26["daily"]:>4.1f} {r26["pf"]:>5.2f} '
          f'${r26["pnl"]:>+9.2f} | ${d25:>+7.0f} ${d26:>+8.2f}{warn}')

print(f"\n  Best dual-month: {best_key} (net=${best_net:.2f})")
print(f"\n[DONE]  [!G]=2505 degraded  [OK]=2605 profitable")
