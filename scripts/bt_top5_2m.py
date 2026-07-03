"""Top5策略 × 2月(2505+2605) 回测对比 — 验证当前.ex5盈利能力"""
import os, sys, json, time, shutil
from pathlib import Path

os.environ['MT5_HOME'] = 'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_xau'
PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / 'scripts'))

# ★ 确保.ex5是最新的
EX5_SRC = PROJECT / 'mql5' / 'Experts' / 'WaiTrade2' / 'WaiTrade_OB.ex5'
EX5_DST = Path(os.environ['MT5_HOME']) / 'MQL5' / 'Experts' / 'WaiTrade2' / 'WaiTrade_OB.ex5'
EX5_DST.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(str(EX5_SRC), str(EX5_DST))
print(f'[部署] .ex5: {EX5_DST.stat().st_size} bytes\n')

from bt_shared import run_bt_silent, make_set

# ── 5策略精确参数 (同 bt_top5_24m.py) ──
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

STRATEGIES = [
    ('S2',    'S2基线(H5+AD)',            S2),
    ('PATHB', 'PathB双扫确认',           {**SWP, 'InpEnableDoubleSweepConfirm':'true',
                                             'InpDoubleSweepWindowBars':'20',
                                             'InpDoubleSweepOnlyDefensive':'true'}),
    ('BD07',  'PathB+decay0.7',          {**SWP, 'InpEnableDoubleSweepConfirm':'true',
                                             'InpDoubleSweepWindowBars':'20',
                                             'InpDoubleSweepOnlyDefensive':'true',
                                             'InpAdaptiveNoiseDefBoostMult':'0.7'}),
    ('REG3',  'RegimeBoth d3%',          {**SWP, 'InpEnableDoubleSweepConfirm':'true',
                                             'InpDoubleSweepWindowBars':'20',
                                             'InpDoubleSweepOnlyDefensive':'true',
                                             'InpAdaptiveNoiseDefBoostMult':'0.7',
                                             'InpAdaptiveNoiseDrawdownPct':'3.0',
                                             'InpDoubleSweepRegimePosMult':'0.6',
                                             'InpDoubleSweepDTPTriggerR':'0.5'}),
    ('BD05',  'PathB+decay0.5',          {**SWP, 'InpEnableDoubleSweepConfirm':'true',
                                             'InpDoubleSweepWindowBars':'20',
                                             'InpDoubleSweepOnlyDefensive':'true',
                                             'InpAdaptiveNoiseDefBoostMult':'0.5'}),
]

MONTHS = [
    ('2505', '2025.05.01', '2025.05.31'),  # 趋势月 (original: S2 +$3.6K, REG3 FAIL)
    ('2605', '2026.05.01', '2026.05.31'),  # 震荡月 (original: REG3 -$6, S2 -$23)
]

# Load original results
orig_data = {}
top5_path = PROJECT / 'temp' / 'top5_24m.json'
if top5_path.exists():
    orig_data = json.loads(top5_path.read_text())

print('=' * 100)
print('  Top5 策略 × 2505(趋势月) + 2605(震荡月) 盈利能力验证')
print('  基线: top5_24m.json | 当前: 最新.ex5 (FVG已修复, FVG默认关闭)')
print('=' * 100)

results = {}
for mk, mfrom, mto in MONTHS:
    y, m = mk[:2], mk[2:]
    print(f'\n{"="*100}')
    print(f'  20{y}.{m} ({mfrom} ~ {mto})')
    print(f'{"="*100}')
    print(f'  {"策略":<20} {"笔数":>6} {"PnL":>10} {"WR":>7} {"PF":>6} {"原PnL":>10} {"状态":>8}')
    print(f'  {"-"*70}')

    for skey, sname, soverrides in STRATEGIES:
        set_name = make_set(f'top5-2m-{skey}-{mk}', dict(soverrides))
        print(f'  {sname:<20} ...', end=' ', flush=True)
        t0 = time.time()
        r = run_bt_silent(f'top5_2m_{skey}_{mk}', set_name, mfrom, mto, timeout=300)
        elapsed = time.time() - t0
        results[f'{skey}_{mk}'] = r

        # Original
        orig_key = f'{skey}_{mk}'
        orig = orig_data.get(orig_key)
        orig_str = f'${orig["pnl"]:+.0f}' if orig and orig.get('count',0) > 0 else ('FAIL' if orig is None else '$0(防守)')

        if r:
            status = 'OK' if r['pnl'] > 0 else ('WARN' if r['pnl'] > -50 else 'LOSS')
            print(f'\r  {sname:<20} {r["count"]:>6} ${r["pnl"]:>+9.2f} {r["wr"]:>6.1f}% {r["pf"]:>5.2f} {orig_str:>10} {status:>8}')
        else:
            print(f'\r  {sname:<20} {"FAILED":>6} {"—":>10} {"—":>7} {"—":>6} {orig_str:>10}   TO')

# ── Summary ──
print(f'\n{"="*100}')
print(f'  汇总: 2505 vs 2605 跨周期对比')
print(f'{"="*100}')

for mk, _, _ in MONTHS:
    y, m = mk[:2], mk[2:]
    print(f'\n[20{y}.{m}]')
    print(f'  {"策略":<20} {"本次":>12} {"原始":>12} {"变化":>10}')
    for skey, sname, _ in STRATEGIES:
        r = results.get(f'{skey}_{mk}')
        orig = orig_data.get(f'{skey}_{mk}')
        cur_pnl = r['pnl'] if r else None
        orig_pnl = orig['pnl'] if orig and orig.get('count',0) > 0 else None
        cur_s = f'${cur_pnl:+.0f}' if cur_pnl is not None else 'FAIL'
        orig_s = f'${orig_pnl:+.0f}' if orig_pnl is not None else ('FAIL' if orig is None else '$0')
        if cur_pnl is not None and orig_pnl is not None:
            delta = cur_pnl - orig_pnl
            d = f'{delta:+.0f}' if abs(delta) > 0.5 else '='
        else:
            d = 'N/A'
        print(f'  {sname:<20} {cur_s:>12} {orig_s:>12} {d:>10}')
