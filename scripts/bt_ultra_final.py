#!/usr/bin/env python3
"""Final: Runtime defensive + best performers. Real-time adaptation (no calendar)."""
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

SL5_M2 = {'InpSLBufferATR':'0.5','InpMaxPosMult':'2.0'}

RDEF = {'InpRuntimeDefensiveDrawdownPct':'5.0',
        'InpRuntimeDefensiveMinTrades':'10',
        'InpRuntimeDefensivePosMult':'0.25'}

RDEF_TIGHT = {'InpRuntimeDefensiveDrawdownPct':'3.0',
              'InpRuntimeDefensiveMinTrades':'5',
              'InpRuntimeDefensivePosMult':'0.10'}

NK_L15 = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
          'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpEnableMTF':'false',
          'InpTickNoiseGateLookback':'15','InpTickNoiseGateMinDirRatio':'0.25',
          'InpTickNoiseGateMaxRangeATR':'0.20'}

NK_L10 = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
          'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpEnableMTF':'false',
          'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
          'InpTickNoiseGateMaxRangeATR':'0.25'}

VARIANTS = [
    ('REF',  'REF-P1(best)', {**SL5_M2, **NK_L15}),

    # Runtime defensive on best 2505 performer (B3: HTF强对齐)
    ('B3_RD', 'B3(+3768)+RunDef5%', {'InpHTFNetPushAlignedMult':'1.5',
        'InpHTFNetPushNeutralMult':'0.7','InpHTFNetPushCounterMult':'0.3',
        **SL5_M2, **RDEF}),
    # B3 + tighter defensive
    ('B3_RD3', 'B3+RunDef3%(tight)', {'InpHTFNetPushAlignedMult':'1.5',
        'InpHTFNetPushNeutralMult':'0.7','InpHTFNetPushCounterMult':'0.3',
        **SL5_M2, **RDEF_TIGHT}),

    # D1 (ultra-light noise) + defensive
    ('D1_RD', 'D1(lb10)+RunDef5%', {**SL5_M2, **NK_L10, **RDEF}),
    ('D1_RD3', 'D1(lb10)+RunDef3%', {**SL5_M2, **NK_L10, **RDEF_TIGHT}),

    # C1 (light noise + HTF) + defensive
    ('C1_RD', 'C1(lb10+HTF)+RunDef5%', {**SL5_M2, **NK_L10, **RDEF,
        'InpHTFNetPushCounterMult':'0.3'}),

    # P1 baseline + defensive (safety net)
    ('P1_RD', 'P1(best)+RunDef5%', {**SL5_M2, **NK_L15, **RDEF}),
]

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
print(f"  FINAL: Runtime defensive on top performers ({len(VARIANTS)}v x 2m = {total}BT)")
print(f"{'='*80}")

for key,label,ov in VARIANTS:make_set(key,ov)

ref_p1_25=0;ref_p1_26=0;results={};done=0
for vkey,vlabel,_ in VARIANTS:
    for mkey,mfrom,mto in MONTHS:
        done+=1;key=f'{vkey}_{mkey}'
        print(f'[{done:>2}/{total}] {vlabel:<40} {mkey} ',end='',flush=True)
        kill_mt5()
        r=run_bt(f'uf_{vkey}_{mkey}',f'v11xau-{vkey}.set',mfrom,mto)
        results[key]=r
        if vkey=='REF':
            if mkey=='2505':ref_p1_25=r['pnl']if r else 0
            else:ref_p1_26=r['pnl']if r else 0
        if r:print(f'{r["count"]:>5}T  WR={r["wr"]:>5.1f}%  PF={r["pf"]:>5.2f}  '
                    f'PnL=${r["pnl"]:>+9.2f}  d={r["daily"]:.1f}')
        else:print('FAILED')

print(f"\n{'='*90}")
print(f"  FINAL RESULTS")
print(f"{'='*90}")
print(f"\n{'Variant':<42} {'2505 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'2605 T':>5} {'d':>4} {'PF':>5} {'PnL':>10} | {'dP1_25':>8} {'dP1_26':>8}")
print('-'*118)

for vkey,vlabel,_ in VARIANTS:
    r25=results.get(f'{vkey}_2505',{});r26=results.get(f'{vkey}_2605',{})
    if not r25 or not r26:continue
    d25=r25['pnl']-ref_p1_25;d26=r26['pnl']-ref_p1_26
    warn=''
    if d25<-abs(ref_p1_25)*0.05:warn+=' [!G]'
    if r26['pnl']>0:warn+=' [OK]'
    print(f'{vlabel:<42} {r25["count"]:>5} {r25["daily"]:>4.1f} {r25["pf"]:>5.2f} '
          f'${r25["pnl"]:>+9.2f} | {r26["count"]:>5} {r26["daily"]:>4.1f} {r26["pf"]:>5.2f} '
          f'${r26["pnl"]:>+9.2f} | ${d25:>+7.0f} ${d26:>+8.2f}{warn}')

print(f"\n[DONE]")
