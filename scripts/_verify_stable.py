#!/usr/bin/env python3
"""Single-day backtest verification on D: portable terminal."""
import sys, os
os.environ['MT5_HOME'] = 'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt'
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

BASE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
    'InpTickNoiseGateLookback':'10','InpTickNoiseGateMinDirRatio':'0.20',
    'InpTickNoiseGateMaxRangeATR':'0.25',
}
PB07 = {**BASE,
    'InpEnableLiquiditySweep':'true', 'InpEnableStateFilter':'true',
    'InpEnableDoubleSweepConfirm':'true', 'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true', 'InpAdaptiveNoiseDefBoostMult':'0.7',
}

print(f'Terminal: {MT5_TERMINAL}')
print(f'Data dir: {MT5_DATA}')
print()

for label, f, t in [('test_260601', '2026.06.01', '2026.06.01'),
                     ('test_260605', '2026.06.05', '2026.06.05'),
                     ('test_260529', '2026.05.29', '2026.05.29')]:
    print(f'Testing {label} ({f} -> {t})...', end=' ', flush=True)
    sn = make_set(f'stable_{label}', PB07, base='v11xau-qs3.set')
    kill_mt5()
    r = run_bt_silent(f'stable_{label}', sn, f, t)
    if r:
        htm = MT5_DATA / f'stable_{label}.htm'
        print(f'{r["count"]:>4}T WR={r["wr"]:>5.1f}% PnL=${r["pnl"]:>+9.2f}')
        print(f'  Report: {htm} ({htm.stat().st_size/1024:.0f}KB)')
    else:
        print('FAILED')
    print()

# Final verification
print('=== 验证 ===')
print(f'MT5_TERMINAL exists: {os.path.exists(MT5_TERMINAL)}')
print(f'MT5_DATA dir: {MT5_DATA}')
print(f'Reports in MT5_DATA: {len(list(Path(str(MT5_DATA)).glob("stable_*.htm")))}')
print('DONE')
