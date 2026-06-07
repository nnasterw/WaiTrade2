#!/usr/bin/env python3
"""Use C: terminal, D: reports. Best of both worlds."""
import sys, os
# Force C: terminal (which has Exness connection), D: report output
os.environ['MT5_DATA'] = 'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_xau'
# Remove MT5_HOME to use installed (C:) terminal
if 'MT5_HOME' in os.environ: del os.environ['MT5_HOME']
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

BASE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
}
PB07 = {**BASE,
    'InpEnableLiquiditySweep':'true', 'InpEnableStateFilter':'true',
    'InpEnableDoubleSweepConfirm':'true', 'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true', 'InpAdaptiveNoiseDefBoostMult':'0.7',
}

print(f'Terminal: {MT5_TERMINAL}')
print(f'Data dir (reports): {MT5_DATA}')
print()

result = None
for label, f, t in [('d0529', '2025.05.29', '2025.05.29')]:
    print(f'Testing {label} ({f})...', end=' ', flush=True)
    sn = make_set(f'dr_{label}', PB07, base='v11xau-qs3.set')
    kill_mt5()
    r = run_bt_silent(f'dr_{label}', sn, f, t)
    result = r
    if r:
        htm = MT5_DATA / f'dr_{label}.htm'
        print(f'{r["count"]:>4}T WR={r["wr"]:>5.1f}% PnL=${r["pnl"]:>+9.2f}')
        print(f'  Report: {htm} ({htm.stat().st_size/1024:.0f}KB)')
    else:
        print('FAILED')

if result:
    print(f'\nC: terminal + D: report   ✅ 稳定运行')
else:
    print(f'\n仍然失败 — 问题在Exness连接, 非文件路径')
print('DONE')
