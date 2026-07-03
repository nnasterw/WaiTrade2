#!/usr/bin/env python3
"""Quick test: portable terminal backtest from D: drive."""
import sys, os
# Force portable mode
os.environ['MT5_HOME'] = 'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt'
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from bt_shared import *

print(f'MT5_TERMINAL={MT5_TERMINAL}')
print(f'MT5_DATA={MT5_DATA}')
print(f'terminal exe exists: {os.path.exists(MT5_TERMINAL)}')

BASE = {
    'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true',
    'InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5',
    'InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpDTPPartialPct':'50',
    'InpBreakevenR':'0.0','InpBreakevenLockR':'0.0',
    'InpSLBufferATR':'0.4','InpMaxPosMult':'2.0',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpAdaptiveNoiseDefMinDirRatio':'0.30',
    'InpAdaptiveNoiseDefMaxRangeATR':'0.16','InpAdaptiveNoiseRecoveryPct':'1.0',
}
sn = make_set('dtest', BASE, base='v11xau-qs3.set')
print(f'set file: {sn}')
print(f'Writing ini to: {MT5_DATA / "Tester"}')
kill_mt5()
r = run_bt_silent('dtest_drive', sn, '2026.05.01', '2026.05.03')  # 3-day mini test
if r:
    print(f'✅ 便携版回测成功!  3天结果: {r["count"]}T WR={r["wr"]:.1f}% PnL=${r["pnl"]:+.2f}')
    print(f'报告在: {MT5_DATA}/dtest_drive.htm')
else:
    print('❌ 回测失败')
    print(f'检查: {MT5_DATA}/Tester/logs/*.log')
print('DONE')
