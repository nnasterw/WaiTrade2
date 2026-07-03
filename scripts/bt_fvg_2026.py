"""FVG 2026震荡月对比回测: 基准 vs FVG启用
比较同一基准策略在FVG开启/关闭时在2601-2605的表现差异。
"""
import os, json, time, sys, shutil
from pathlib import Path

os.environ['MT5_HOME'] = 'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_xau'
PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / 'scripts'))

# ★ 确保便携终端使用最新编译的.ex5
EX5_SRC = PROJECT / 'mql5' / 'Experts' / 'WaiTrade2' / 'WaiTrade_OB.ex5'
EX5_DST = Path(os.environ['MT5_HOME']) / 'MQL5' / 'Experts' / 'WaiTrade2' / 'WaiTrade_OB.ex5'
EX5_DST.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(str(EX5_SRC), str(EX5_DST))
print(f'[部署] .ex5 → {EX5_DST} ({EX5_DST.stat().st_size} bytes)')

from bt_shared import run_bt_silent, make_set, parse_report

# ── 精确复刻 bt_top5_24m.py 的 RegimeBoth d3% 参数 ──
BASE_SET = 'v11xau-qs3.set'
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
# RegimeBoth d3% — top5_24m #1策略的精确参数
REGIME_BOTH = {**SWP, 'InpEnableEntryEngine':'false',  # 统一直接入场路径
    'InpEnableDoubleSweepConfirm':'true',
    'InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true',
    'InpAdaptiveNoiseDefBoostMult':'0.7',
    'InpAdaptiveNoiseDrawdownPct':'3.0',
    'InpDoubleSweepRegimePosMult':'0.6',
    'InpDoubleSweepDTPTriggerR':'0.5'}

# FVG额外参数 (叠加在基准之上)
FVG_OVERRIDES = {
    'InpEnableEntryEngine': 'false',  # ★ FVG需要直接入场路径(ScanSignals)
    'InpEnableFVG': 'true',
    'InpFVGLookbackBars': '50',
    'InpFVGMinGapATR': '0.04',       # 放宽: 0.06→0.04, 捕获更小的缺口
    'InpFVGMaxGapATR': '1.00',       # 放宽: 0.60→1.00
    'InpFVGMaxAgeBars': '120',       # 放宽: 活的更久
    'InpFVGTimeoutMin': '360',
    'InpFVGRequireRangeBoundary': 'false',  # ★ 关掉区间边界要求, 允许趋势中途FVG
    'InpFVGEnableFadeEntry': 'true',
    'InpFVGFadeMinRiskSpreadRatio': '2.0',  # 放宽risk/spread
    'InpFVGFadeMaxEntryOffsetR': '5.0',     # 放宽偏移
    'InpFVGFadePosMult': '0.8',             # 提高仓位
    'InpFVGFadeMaxLotSize': '0.03',
    'InpFVGFadeTPMult': '1.5',
    'InpFVGNoEntryHours': '5,6,7',              # 避开伦敦开盘噪音时段
    'InpFVGRequireConfirmCandle': 'true',       # 回补后需同向确认K线
    'InpEnableEntryDebug': 'false',
}

MONTHS = [
    ('2601', '2026.01.01', '2026.01.31'),
    ('2602', '2026.02.01', '2026.02.28'),
    ('2603', '2026.03.01', '2026.03.31'),
    ('2604', '2026.04.01', '2026.04.30'),
    ('2605', '2026.05.01', '2026.05.31'),
]

RESULTS_FILE = PROJECT / 'temp' / 'fvg_2026_results.json'

def load_existing():
    """Load existing top5_24m results for comparison."""
    top5 = PROJECT / 'temp' / 'top5_24m.json'
    if top5.exists():
        return json.loads(top5.read_text())
    return {}

def run_one(overrides, tag, mkey, mfrom, mto):
    """Run single backtest. Returns dict or None."""
    set_name = make_set(f'fvg-{tag}-{mkey}', overrides, base=BASE_SET)
    print(f'  [{tag}] {mkey}: set={set_name} {mfrom}→{mto} ...', end=' ', flush=True)
    t0 = time.time()
    result = run_bt_silent(f'fvg_{tag}_{mkey}', set_name, mfrom, mto, timeout=300)
    elapsed = time.time() - t0
    if result:
        print(f'OK ({elapsed:.0f}s) T={result["count"]} PnL=${result["pnl"]:+.2f} WR={result["wr"]:.1f}% PF={result["pf"]:.2f}')
    else:
        print(f'FAILED ({elapsed:.0f}s)')
    return result

def main():
    existing = load_existing()
    results = {}

    print('=' * 80)
    print('  FVG 2026震荡月对比回测')
    print('  基准: RegimeBoth d3% | 对比: +FVG震荡Fade入场')
    print('=' * 80)
    print()

    for mkey, mfrom, mto in MONTHS:
        print(f'--- {mkey} ({mfrom} ~ {mto}) ---')

        # 基准 (FVG关闭, 精确RegimeBoth参数)
        base_overrides = dict(REGIME_BOTH)
        base_overrides['InpEnableFVG'] = 'false'
        base_overrides['InpFVGEnableFadeEntry'] = 'false'
        base_r = run_one(base_overrides, 'base', mkey, mfrom, mto)
        results[f'base_{mkey}'] = base_r

        # FVG启用 (叠加在RegimeBoth之上)
        fvg_overrides = dict(REGIME_BOTH)
        fvg_overrides.update(FVG_OVERRIDES)
        fvg_r = run_one(fvg_overrides, 'fvg', mkey, mfrom, mto)
        results[f'fvg_{mkey}'] = fvg_r

        # 加载现有RegimeBoth结果做参考
        reg3_key = f'REG3_{mkey}'
        reg3 = existing.get(reg3_key)
        if reg3:
            print(f'  [参考RegimeBoth] T={reg3["count"]} PnL=${reg3["pnl"]:+.2f} WR={reg3["wr"]:.1f}% PF={reg3["pf"]:.2f}')
        else:
            print(f'  [参考RegimeBoth] {reg3_key}: FAILED/无数据')
        print()

        # Save intermediate
        RESULTS_FILE.write_text(json.dumps(results, indent=2))

    # ── Summary ──
    print('=' * 80)
    print('  汇总对比')
    print('=' * 80)
    print(f'{"月份":<8} {"基准T":>6} {"基准PnL":>10} {"基准WR":>7} {"FVG_T":>6} {"FVG_PnL":>10} {"FVG_WR":>7} {"RegimeBoth":>12}')
    print('-' * 72)

    total_base_t = 0; total_base_pnl = 0.0
    total_fvg_t = 0; total_fvg_pnl = 0.0

    for mkey, _, _ in MONTHS:
        base_r = results.get(f'base_{mkey}')
        fvg_r = results.get(f'fvg_{mkey}')
        reg3 = existing.get(f'REG3_{mkey}')

        base_t = base_r['count'] if base_r else 0
        base_pnl = base_r['pnl'] if base_r else 0
        base_wr = f'{base_r["wr"]:.1f}%' if base_r else 'FAIL'
        fvg_t = fvg_r['count'] if fvg_r else 0
        fvg_pnl = fvg_r['pnl'] if fvg_r else 0
        fvg_wr = f'{fvg_r["wr"]:.1f}%' if fvg_r else 'FAIL'
        reg3_pnl = f'${reg3["pnl"]:+.0f}' if reg3 else ('FAIL' if reg3 is None else '0def')

        total_base_t += base_t
        total_base_pnl += base_pnl
        total_fvg_t += fvg_t
        total_fvg_pnl += fvg_pnl

        print(f'20{mkey[:2]}.{mkey[2:]} {base_t:>6} ${base_pnl:>+9.2f} {base_wr:>7} {fvg_t:>6} ${fvg_pnl:>+9.2f} {fvg_wr:>7} {reg3_pnl:>12}')

    print('-' * 72)
    print(f'{"合计":<8} {total_base_t:>6} ${total_base_pnl:>+9.2f} {"":>7} {total_fvg_t:>6} ${total_fvg_pnl:>+9.2f}')
    print()
    print(f'FVG增量: ${total_fvg_pnl - total_base_pnl:+.2f} ({(total_fvg_pnl - total_base_pnl) / abs(total_base_pnl) * 100 if total_base_pnl != 0 else 0:.1f}%)')
    print(f'结果已保存: {RESULTS_FILE}')

if __name__ == '__main__':
    main()
