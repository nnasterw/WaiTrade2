#!/usr/bin/env python3
"""Comprehensive re-test with CORRECT ex5. 2505 + 2605 + 2604.
Tests: decay levels, MTF variants, adaptive combos, OB cooldown, cooldown bars."""
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

NOISE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5'}

H5_EXIT = {'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0'}

def s2_base(**kw):
    """S2: H5+AD-LOOSE with configurable overrides."""
    return {**NOISE, 'InpEnableMTF':'false',
        'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
        'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
        'InpTickNoiseGateMaxRangeATR':'0.25',
        'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
        'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
        **H5_EXIT, **kw}

def s2_mtf(**kw):
    """S2 with MTF enabled + HTF filter baseline."""
    return s2_base(InpEnableMTF='true',
        InpEnableHTFNetPushFilter='true',InpHTFNetPushTF='15',
        InpHTFNetPushBars='4',InpHTFNetPushMinATR='0.50',
        InpHTFNetPushAlignedMult='1.0',InpHTFNetPushNeutralMult='1.0',
        InpHTFNetPushCounterMult='1.0', **kw)

VARIANTS = [
    # === BASELINES ===
    ('S1','S1-H5+LOOSE(noAD,SL=0.5)',s2_base(InpSLBufferATR='0.5',
        InpAdaptiveNoiseDrawdownPct='0.0')),
    ('S2','S2-H5+AD(SL=0.4,dd3%)',s2_base()),
    ('S2M','S2+MTF',s2_mtf()),

    # === DEFENSIVE DECAY LEVELS (the key parameter!) ===
    ('D7','S2+decay=0.7',s2_base(InpAdaptiveNoiseDefBoostMult='0.7')),
    ('D5','S2+decay=0.5',s2_base(InpAdaptiveNoiseDefBoostMult='0.5')),
    ('D3','S2+decay=0.3',s2_base(InpAdaptiveNoiseDefBoostMult='0.3')),

    # === ADAPTIVE NEUTRAL (confirmed working) ===
    ('AN0','S2+MTF+AdaptN0',s2_mtf(InpAdaptiveNoiseDefNeutralMult='0.0')),
    ('AN5','S2+MTF+AdaptN0.5',s2_mtf(InpAdaptiveNoiseDefNeutralMult='0.5')),

    # === ADAPTIVE OB COOLDOWN (confirmed working) ===
    ('AO5','S2+MTF+OBcd5',s2_mtf(InpAdaptiveNoiseDefOBReentryCd='5')),
    ('AO10','S2+MTF+OBcd10',s2_mtf(InpAdaptiveNoiseDefOBReentryCd='10')),

    # === COMBO: decay + MTF + Neutral ===
    ('C1','S2+MTF+decay0.7+AdaptN0',s2_mtf(
        InpAdaptiveNoiseDefBoostMult='0.7',InpAdaptiveNoiseDefNeutralMult='0.0')),
    ('C2','S2+MTF+decay0.5+AdaptN0',s2_mtf(
        InpAdaptiveNoiseDefBoostMult='0.5',InpAdaptiveNoiseDefNeutralMult='0.0')),

    # === DEFENSIVE COOLDOWN ===
    ('CD20','S2+MTF+DefCooldown20',s2_mtf(InpAdaptiveNoiseDefCooldownBars='20')),
    ('CD30','S2+MTF+DefCooldown30',s2_mtf(InpAdaptiveNoiseDefCooldownBars='30')),
]

MONTHS = [('2505','2025.05.01','2025.05.31'),
           ('2605','2026.05.01','2026.05.31'),
           ('2604','2026.04.01','2026.04.30')]

total = len(VARIANTS)*len(MONTHS)
print(f'{len(VARIANTS)}v x {len(MONTHS)}m = {total} BTs (NEW ex5)')
done=0
results={}

for vkey,vlabel,base in VARIANTS:
    sn = make_set(f'rr_{vkey}', base, base='v11xau-qs3.set')
    for mkey,mfrom,mto in MONTHS:
        done+=1; key=f'{vkey}_{mkey}'
        print(f'[{done:>3}/{total}] {vlabel:<35} {mkey} ',end='',flush=True)
        kill_mt5()
        r=run_bt_silent(f'rr_{vkey}_{mkey}',sn,mfrom,mto)
        results[key]=r
        if r: print(f'{r["count"]:>4}T WR={r["wr"]:>5.1f}% PF={r["pf"]:>5.2f} PnL=${r["pnl"]:>+9.2f}')
        else: print('FAILED')

# SUMMARY
print(f"\n{'='*120}")
ref_s1_25 = results.get('S1_2505',{}).get('pnl',0)
ref_s2_25 = results.get('S2_2505',{}).get('pnl',0)
ref_s2_26 = results.get('S2_2605',{}).get('pnl',0)
print(f"  RE-RUN RESULTS (NEW ex5)")
print(f"  S1: 2505=${ref_s1_25:,.0f} | S2 ref: 2505=${ref_s2_25:,.0f} 2605=${ref_s2_26:,.2f}")
print(f"{'='*120}")

for month in ['2505','2605','2604']:
    print(f"\n=== {month} ===")
    print(f"  {'Config':<35} {'T':>4} {'WR':>5} {'PF':>5} {'PnL':>10} | vsS2_25 | vsS2_26")
    for vkey,vlabel,_ in VARIANTS:
        r=results.get(f'{vkey}_{month}',{})
        if r:
            d25 = r['pnl']-ref_s2_25 if month=='2505' else 0
            d26 = r['pnl']-ref_s2_26 if month=='2605' else 0
            vs = ''
            if month=='2605' and r['pnl']>ref_s2_26: vs=f' +{r["pnl"]-ref_s2_26:+.2f}'
            if month=='2605' and r['pnl']>0: vs+=' ✅'
            print(f"  {vlabel:<35} {r['count']:>4} {r['wr']:>4.1f}% {r['pf']:>4.2f} ${r['pnl']:>+9.2f}{vs}")

print(f"\n[DONE]")
