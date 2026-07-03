#!/usr/bin/env python3
"""Final verification: portable terminal backtest on D: drive."""
import sys, os
os.environ['MT5_HOME'] = 'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt'
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

print(f'MT5_TERMINAL={MT5_TERMINAL}')
print(f'MT5_DATA={MT5_DATA}')
print(f'Portable .ex5 exists: {os.path.exists(str(MT5_DATA) + "/MQL5/Experts/WaiTrade2/WaiTrade_OB.ex5")}')
print(f'Portable tick data: {os.path.exists(str(MT5_DATA) + "/bases/Exness-MT5Trial5/ticks/XAUUSDm")}')

BASE = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
}
sn = make_set('vportable', BASE, base='v11xau-qs3.set')
kill_mt5()
r = run_bt_silent('vportable_drive', sn, '2026.05.01', '2026.05.05')
if r:
    print(f'\nPORTABLE BT OK: {r["count"]}T WR={r["wr"]:.1f}% PnL=${r["pnl"]:+.2f}')
    # Check where report was written
    htm_path = MT5_DATA / 'vportable_drive.htm'
    print(f'Report: {htm_path} ({htm_path.stat().st_size/1024:.0f}KB)')
    log_dir = MT5_DATA / 'Tester' / 'logs'
    logs = list(log_dir.glob('*.log')) if log_dir.exists() else []
    print(f'Tester logs: {len(logs)} files')
else:
    print('PORTABLE BT FAILED')
    # Check errors
    tdir = MT5_DATA / 'Tester'
    if tdir.exists():
        logs = list((tdir / 'logs').glob('*.log')) if (tdir / 'logs').exists() else []
        for l in logs:
            print(f'  Log: {l} ({l.stat().st_size/1024:.0f}KB)')
print('DONE')
