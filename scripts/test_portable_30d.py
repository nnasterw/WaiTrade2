#!/usr/bin/env python3
"""Verify portable terminal with 30-day backtest."""
import os, sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
os.environ['MT5_HOME'] = r'D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt'

from bt_shared import *

print(f'=== Portable 30d Backtest ===')
print(f'MT5_TERMINAL: {MT5_TERMINAL}')
print(f'MT5_DATA: {MT5_DATA}')

# Standard S2 config, 30 days May 2026
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
}
sn = make_set('p30d', cfg, base='v11xau-qs3.set')
kill_mt5()

# Time the backtest
import time
t0 = time.time()
r = run_bt_silent('p30d_2605', sn, '2026.05.01', '2026.05.31')
elapsed = time.time() - t0

if r:
    print(f'\n✅ SUCCESS ({elapsed:.0f}s)')
    print(f'   Trades: {r["count"]}  WR: {r["wr"]:.1f}%  PF: {r["pf"]:.2f}  PnL: ${r["pnl"]:+.2f}')
    # Verify all data is on D:
    htm = MT5_DATA / 'p30d_2605.htm'
    print(f'   Report: {htm} ({"D:" if str(htm).startswith("D:") else "C:"})')
else:
    print(f'\n❌ FAILED ({elapsed:.0f}s)')
