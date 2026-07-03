"""FVG 优化实验矩阵 — 5个独立实验 × 5个月 = 25次回测
基于多维分析的最优候选参数组合。
"""
import os, json, time, sys, shutil
from pathlib import Path

os.environ['MT5_HOME'] = 'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_xau'
PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / 'scripts'))

# ★ 确保最新.ex5部署
EX5_SRC = PROJECT / 'mql5' / 'Experts' / 'WaiTrade2' / 'WaiTrade_OB.ex5'
EX5_DST = Path(os.environ['MT5_HOME']) / 'MQL5' / 'Experts' / 'WaiTrade2' / 'WaiTrade_OB.ex5'
EX5_DST.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(str(EX5_SRC), str(EX5_DST))
print(f'[部署] .ex5 → {EX5_DST} ({EX5_DST.stat().st_size} bytes)')

from bt_shared import run_bt_silent, make_set

# ═══════════════════════════════════════════════════════════════════
# 基础参数 (同 bt_fvg_2026.py)
# ═══════════════════════════════════════════════════════════════════
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
REGIME_BOTH = {**SWP, 'InpEnableEntryEngine':'false',
    'InpEnableDoubleSweepConfirm':'true','InpDoubleSweepWindowBars':'20',
    'InpDoubleSweepOnlyDefensive':'true','InpAdaptiveNoiseDefBoostMult':'0.7',
    'InpAdaptiveNoiseDrawdownPct':'3.0','InpDoubleSweepRegimePosMult':'0.6',
    'InpDoubleSweepDTPTriggerR':'0.5'}

FVG_BASE = {
    'InpEnableEntryEngine': 'false',
    'InpEnableFVG': 'true',
    'InpFVGLookbackBars': '50',
    'InpFVGMinGapATR': '0.04',
    'InpFVGMaxGapATR': '1.00',
    'InpFVGMaxAgeBars': '120',
    'InpFVGTimeoutMin': '360',
    'InpFVGRequireRangeBoundary': 'false',
    'InpFVGEnableFadeEntry': 'true',
    'InpFVGFadeMinRiskSpreadRatio': '2.0',
    'InpFVGFadeMaxEntryOffsetR': '5.0',
    'InpFVGFadePosMult': '0.8',
    'InpFVGFadeMaxLotSize': '0.03',
    'InpFVGFadeTPMult': '1.5',
}

MONTHS = [
    ('2601', '2026.01.01', '2026.01.31'),
    ('2602', '2026.02.01', '2026.02.28'),
    ('2603', '2026.03.01', '2026.03.31'),
    ('2604', '2026.04.01', '2026.04.30'),
    ('2605', '2026.05.01', '2026.05.31'),
]

# ═══════════════════════════════════════════════════════════════════
# 实验定义
# ═══════════════════════════════════════════════════════════════════

EXPERIMENTS = {
    # ── 实验A: 时段过滤 ─────────────────────────────────
    'A1_golden_hours': {
        'desc': '仅02:00 UTC交易 (双向盈利时段)',
        'overrides': {
            'InpEntryMonths': '',  # 所有月份
            'InpNoEntryHours': '0,1,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23',
        },
        'cfg_overrides': {}  # need code change: allow only hour=2
    },
    'A2_no_toxic': {
        'desc': '禁止05:00-08:00 UTC (消除-$563损失)',
        'overrides': {
            'InpNoEntryHours': '5,6,7,8',
        },
    },
    'A3_asia_session': {
        'desc': '仅00:00-03:00 UTC (亚洲盘)',
        'overrides': {
            'InpNoEntryHours': '4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23',
        },
    },

    # ── 实验B: 仓位乘数 ─────────────────────────────────
    'B1_pos04': {
        'desc': 'FVG固定pos_mult=0.4 (甜蜜点)',
        'overrides': {
            'InpFVGFadePosMult': '0.4',
        },
    },
    'B2_pos08_nocap': {
        'desc': 'FVG pos_mult=0.8 + 跳过全局乘数衰减',
        'overrides': {
            'InpFVGFadePosMult': '0.8',
            # 需要代码改动: FVG不走全局乘数链
            # 临时方案: 设置极宽的MaxPosMult
            'InpMaxPosMult': '10.0',
            'InpAdaptiveNoiseDefBoostMult': '1.0',  # 不衰减
            'InpDoubleSweepRegimePosMult': '1.0',   # 不衰减
        },
    },

    # ── 实验C: 方向过滤 ─────────────────────────────────
    'C1_h1_aligned': {
        'desc': 'FVG方向必须对齐1H OB方向',
        'overrides': {
            'InpFVGRequireRangeBoundary': 'true',  # 启用区间边界
            'InpEnableStateFilter': 'true',
        },
        # 需代码改动: CheckFVGEntry中 trade_dir强制=zone.direction当H1对齐时
    },
    'C2_only_range_fade': {
        'desc': '仅在震荡市(market_state=0)做Fade',
        'overrides': {
            'InpFVGRequireRangeBoundary': 'true',
        },
        # 需代码改动: 趋势市跳过FVG
    },

    # ── 实验D: 连续亏损熔断 ─────────────────────────────
    'D1_consecutive_stop': {
        'desc': '连续亏损5次→暂停FVG直到下个交易日',
        'overrides': {},
        # 需代码改动: 添加s_fvg_consecutive_losses全局计数器
    },

    # ── 实验E: 间隙质量过滤 ─────────────────────────────
    'E1_quality_gate': {
        'desc': 'FVG最小间隙0.05 ATR + 强度≥2.0',
        'overrides': {
            'InpFVGMinGapATR': '0.05',
        },
    },
    'E2_large_gap_only': {
        'desc': '仅交易大间隙FVG (≥0.08 ATR)',
        'overrides': {
            'InpFVGMinGapATR': '0.08',
        },
    },
}

RESULTS_FILE = PROJECT / 'temp' / 'fvg_experiments.json'

def run_experiment(exp_name, exp_def, mkey, mfrom, mto):
    """Run single experiment × month backtest."""
    overrides = dict(REGIME_BOTH)
    overrides.update(FVG_BASE)
    overrides.update(exp_def.get('overrides', {}))

    set_name = make_set(f'fvg-exp-{exp_name}-{mkey}', overrides)
    print(f'  [{exp_name}] {mkey}: {set_name} ...', end=' ', flush=True)
    t0 = time.time()
    result = run_bt_silent(f'fvg_exp_{exp_name}_{mkey}', set_name, mfrom, mto, timeout=300)
    elapsed = time.time() - t0
    if result:
        print(f'OK ({elapsed:.0f}s) T={result["count"]} PnL=${result["pnl"]:+.2f} WR={result["wr"]:.1f}% PF={result["pf"]:.2f}')
    else:
        print(f'FAILED ({elapsed:.0f}s)')
    return result

def main():
    results = {}

    # Load existing baseline for comparison
    existing = {}
    top5 = PROJECT / 'temp' / 'fvg_2026_results.json'
    if top5.exists():
        existing = json.loads(top5.read_text())

    print('=' * 90)
    print('  FVG 优化实验矩阵 — 5实验 × 5月 = 25次回测')
    print('=' * 90)

    # First, run baseline (FVG + standard params) for reference
    print('\n[基线] FVG标准参数 (作为对照)')
    base_results = {}
    for mkey, mfrom, mto in MONTHS:
        key = f'baseline_{mkey}'
        if key in existing:
            r = existing[key]
            print(f'  [baseline] {mkey}: (cached) T={r["count"]} PnL=${r["pnl"]:+.2f}')
            base_results[key] = r
        else:
            # Read from fvg_fvg report
            r = run_experiment('baseline', {}, mkey, mfrom, mto)
            base_results[key] = r
        results[key] = base_results.get(key)

    # Now run each experiment
    for exp_name, exp_def in EXPERIMENTS.items():
        # Check if experiment needs code changes
        if exp_def.get('cfg_overrides') or '需代码改动' in exp_def.get('desc', ''):
            print(f'\n[跳过] {exp_name}: {exp_def["desc"]} — 需代码改动')
            continue

        print(f'\n[{exp_name}] {exp_def["desc"]}')
        for mkey, mfrom, mto in MONTHS:
            r = run_experiment(exp_name, exp_def, mkey, mfrom, mto)
            results[f'{exp_name}_{mkey}'] = r

        # Save intermediate
        RESULTS_FILE.write_text(json.dumps(results, indent=2, default=str))

    # ── Summary ──
    print('\n' + '=' * 90)
    print('  实验汇总')
    print('=' * 90)

    # Collect experiment names that were run
    run_exps = [k for k in EXPERIMENTS if not ('需代码改动' in EXPERIMENTS[k].get('desc',''))]

    header = f'{"实验":<20} {"2601":>12} {"2602":>12} {"2603":>12} {"2604":>12} {"2605":>12} {"合计":>12}'
    print(header)
    print('-' * (20 + 12*6))

    # Baseline row
    bl_pnls = []
    for mk in MONTHS:
        r = base_results.get(f'baseline_{mk}')
        bl_pnls.append(r['pnl'] if r else 0)
    print(f'{"基线(FVG标准)":<20} ' + ' '.join(f'${p:>+10.0f} ' for p in bl_pnls) + f' ${sum(bl_pnls):>+10.0f}')

    # Experiment rows
    for exp_name in run_exps:
        pnls = []
        for mk in MONTHS:
            r = results.get(f'{exp_name}_{mk}')
            pnls.append(r['pnl'] if r else 0)
        delta = sum(pnls) - sum(bl_pnls)
        print(f'{exp_name:<20} ' + ' '.join(f'${p:>+10.0f} ' for p in pnls) + f' ${sum(pnls):>+10.0f} (Δ{delta:+.0f})')

    print(f'\n结果已保存: {RESULTS_FILE}')

if __name__ == '__main__':
    main()
