#!/usr/bin/env python3
"""Test fresh portable terminal instance."""
import sys, os
# Point to NEW portable terminal
os.environ['MT5_HOME'] = 'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_xau'
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
print(f'Data: {MT5_DATA}')
print()

for label, f, t in [('new_test1', '2026.06.01', '2026.06.01'),
                     ('new_test2', '2026.06.05', '2026.06.05')]:
    print(f'{label} ({f})...', end=' ', flush=True)
    sn = make_set(f'new_{label}', PB07, base='v11xau-qs3.set')
    kill_mt5()
    r = run_bt_silent(f'new_{label}', sn, f, t)
    if r:
        htm = MT5_DATA / f'new_{label}.htm'
        print(f'{r["count"]:>4}T WR={r["wr"]:>5.1f}% PnL=${r["pnl"]:>+9.2f}')
        print(f'  Report: {htm} ({htm.stat().st_size/1024:.0f}KB)' if htm.exists() else '  Report: MISSING')
    else:
        print('FAILED')

print('\n=== 验证 ===')
print(f'Log size: {sum(f.stat().st_size for f in Path(str(MT5_DATA)).rglob("*.log") if f.is_file())/1024/1024:.0f}MB')
print('DONE')
