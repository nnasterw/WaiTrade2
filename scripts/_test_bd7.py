#!/usr/bin/env python3
"""Test single BD7 backtest."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bt_shared import *

cfg = {
    'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    'InpEnableLiquiditySweep':'true','InpEnableStateFilter':'true',
    'InpEnableDoubleSweepConfirm':'true','InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true','InpAdaptiveNoiseDefBoostMult':'0.7',
}
sn = make_set('_test', cfg, base='v11xau-qs3.set')
kill_mt5()
r = run_bt_silent('_test_bd7', sn, '2025.05.01', '2025.05.31')
if r:
    print(f'OK: {r["count"]}T WR={r["wr"]:.1f}% PnL=${r["pnl"]:+.2f}')
else:
    print('FAILED')
