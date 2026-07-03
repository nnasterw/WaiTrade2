"""Quick FVG diagnostic — single month with debug logging."""
import os, json, time, sys
from pathlib import Path
os.environ['MT5_HOME'] = 'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_xau'
PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / 'scripts'))
from bt_shared import run_bt_silent, make_set

NOISE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5'}
H5 = {'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0'}
S2 = {**NOISE, 'InpEnableMTF':'false', 'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0', **H5}
SWP = {**S2, 'InpEnableLiquiditySweep':'true', 'InpEnableStateFilter':'true'}
REGIME_BOTH = {**SWP, 'InpEnableDoubleSweepConfirm':'true',
    'InpDoubleSweepWindowBars':'20', 'InpDoubleSweepOnlyDefensive':'true',
    'InpAdaptiveNoiseDefBoostMult':'0.7', 'InpAdaptiveNoiseDrawdownPct':'3.0',
    'InpDoubleSweepRegimePosMult':'0.6', 'InpDoubleSweepDTPTriggerR':'0.5'}

# Relaxed FVG with debug
FVG = {
    'InpEnableFVG':'true','InpFVGLookbackBars':'50',
    'InpFVGMinGapATR':'0.04','InpFVGMaxGapATR':'1.00',
    'InpFVGMaxAgeBars':'120','InpFVGTimeoutMin':'360',
    'InpFVGRequireRangeBoundary':'false',
    'InpFVGEnableFadeEntry':'true',
    'InpFVGFadeMinRiskSpreadRatio':'2.0','InpFVGFadeMaxEntryOffsetR':'2.0',
    'InpFVGFadePosMult':'0.8','InpFVGFadeMaxLotSize':'0.03','InpFVGFadeTPMult':'1.5',
    'InpEnableEntryDebug':'true',
}

overrides = dict(REGIME_BOTH)
overrides.update(FVG)
set_name = make_set('fvg-diag-2603', overrides)
print(f'SET: {set_name}')
t0 = time.time()
r = run_bt_silent('fvg_diag_2603', set_name, '2026.03.01', '2026.03.31', timeout=300)
print(f'Time: {time.time()-t0:.0f}s')
if r:
    print(f'Trades={r["count"]} PnL=${r["pnl"]:+.2f} WR={r["wr"]:.1f}% PF={r["pf"]:.2f}')
else:
    print('FAILED')
