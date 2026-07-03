#!/usr/bin/env python3
"""
Top-5策略 × 24个月全量回测 + 月度明细汇总
策略选择依据: 24月验证数据 + 2605震荡月表现 + 长期盈利率
"""
import sys, calendar, json, time, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bt_shared import *

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

# ── Top 5 策略定义 ──
# 选择逻辑:
# 1. S2基线 — 生产基准, 对照
# 2. PathB原版 — 首个全月超越基线的SMC突破
# 3. PathB+decay0.7 — 最佳平衡(2605:-$12.46, 2505:+$7.6K)
# 4. RegimeBoth(dd3%) — 最佳2605: -$6.11, 85%月盈利率
# 5. PathB+decay0.5 — 更强衰减, 震荡月保护

STRATEGIES = [
    ('S2',    'S2基线(H5+AD)',            S2),
    ('PATHB', 'PathB 双扫确认',           {**SWP, 'InpEnableDoubleSweepConfirm':'true',
                                             'InpDoubleSweepWindowBars':'20',
                                             'InpDoubleSweepOnlyDefensive':'true'}),
    ('BD07',  'PathB+decay0.7(最佳平衡)',  {**SWP, 'InpEnableDoubleSweepConfirm':'true',
                                             'InpDoubleSweepWindowBars':'20',
                                             'InpDoubleSweepOnlyDefensive':'true',
                                             'InpAdaptiveNoiseDefBoostMult':'0.7'}),
    ('REG3',  'RegimeBoth d3%(最佳震荡)',   {**SWP, 'InpEnableDoubleSweepConfirm':'true',
                                             'InpDoubleSweepWindowBars':'20',
                                             'InpDoubleSweepOnlyDefensive':'true',
                                             'InpAdaptiveNoiseDefBoostMult':'0.7',
                                             'InpAdaptiveNoiseDrawdownPct':'3.0',
                                             'InpDoubleSweepRegimePosMult':'0.6',
                                             'InpDoubleSweepDTPTriggerR':'0.5'}),
    ('BD05',  'PathB+decay0.5(激进防御)',  {**SWP, 'InpEnableDoubleSweepConfirm':'true',
                                             'InpDoubleSweepWindowBars':'20',
                                             'InpDoubleSweepOnlyDefensive':'true',
                                             'InpAdaptiveNoiseDefBoostMult':'0.5'}),
]

# 24个月: 2024.06 ~ 2026.05
MONTHS = []
for y in [2024, 2025, 2026]:
    end_m = 13 if y < 2026 else 6
    for m in range(1, end_m):
        if y == 2024 and m < 6: continue
        last_day = calendar.monthrange(y, m)[1]
        MONTHS.append((f'{y%100:02d}{m:02d}', f'{y}.{m:02d}.01', f'{y}.{m:02d}.{last_day}'))

total = len(STRATEGIES) * len(MONTHS)
print(f'Top-5 × 24月 = {total} BTs (C:终端, Model 4)')
print(f'策略: {", ".join(s[1] for s in STRATEGIES)}')
print(f'月份: {MONTHS[0][0]} ~ {MONTHS[-1][0]}')
print()

# 创建.set文件
set_names = {}
for skey, slabel, cfg in STRATEGIES:
    sn = make_set(f'top5_{skey}', cfg, base='v11xau-qs3.set')
    set_names[skey] = sn
print('.set files ready\n')

# 进度追踪
SAVE_PATH = Path('temp/top5_24m.json')
results = {}
if SAVE_PATH.exists():
    try: results = json.loads(SAVE_PATH.read_text())
    except: pass

done = 0; t0_total = time.time()
cleanup_counter = 0  # 每10个BT清理一次C:盘报告

for mkey, mfrom, mto in MONTHS:
    for skey, slabel, cfg in STRATEGIES:
        key = f'{skey}_{mkey}'
        if key in results and results[key] and results[key].get('count', -1) >= 0:
            done += 1; continue

        print(f'[{done+1:>3}/{total}] {slabel:<25} {mkey} ', end='', flush=True)
        kill_mt5()
        time.sleep(2)
        t0 = time.time()
        name = f'top5_{skey}_{mkey}'
        r = run_bt_silent(name, set_names[skey], mfrom, mto, timeout=300)
        elapsed = time.time() - t0

        if r:
            results[key] = {'count':r['count'],'wr':r['wr'],'pf':r['pf'],'pnl':r['pnl']}
            print(f'{r["count"]:>4}T WR={r["wr"]:>5.1f}% PnL=${r["pnl"]:>+9.2f} ({elapsed:.0f}s)')
        else:
            results[key] = None
            print(f'FAILED ({elapsed:.0f}s)')

        done += 1; cleanup_counter += 1

        # 每10个BT清理一次HTML报告, 防止C:盘满
        if cleanup_counter >= 10:
            cleanup_counter = 0
            htm_dir = MT5_DATA
            for f in htm_dir.glob('top5_*.htm'):
                try: f.unlink()
                except: pass
            if done % 20 == 0:
                SAVE_PATH.write_text(json.dumps(results))
                elapsed_total = time.time() - t0_total
                eta = elapsed_total/done*(total-done) if done else 0
                print(f'  [Progress: {done}/{total} ({done/total*100:.0f}%) ETA {eta/60:.0f}min]')

# 最终保存
SAVE_PATH.write_text(json.dumps(results))

# ── 生成汇总表格 ──
print(f'\n\n{"="*140}')
print(f'  Top-5 策略 × 24月 全量回测汇总')
print(f'{"="*140}')

# 表头
header = f'  {"Month":>6} |'
for skey, slabel, _ in STRATEGIES:
    header += f' {slabel:>28} |'
print(header)
sep = f'  {"-"*6}-+-' + '-+-'.join(['-'*28 for _ in STRATEGIES]) + '-|'
print(sep)

# 数据行 + 统计
stats = {skey: {'pnl':0,'trades':0,'win_months':0,'loss_months':0,'n':0,'wr_sum':0}
         for skey,_,_ in STRATEGIES}
running = {skey:0 for skey,_,_ in STRATEGIES}
peak = {skey:0 for skey,_,_ in STRATEGIES}
mdd = {skey:0 for skey,_,_ in STRATEGIES}

for mkey, mfrom, mto in MONTHS:
    line = f'  {mkey:>6} |'
    for skey, slabel, _ in STRATEGIES:
        r = results.get(f'{skey}_{mkey}')
        if r and r.get('count', -1) >= 0:
            line += f' ${r["pnl"]:>+8.2f} {r["wr"]:>5.1f}% {r["count"]:>5}T PF={r["pf"]:>.2f} |'
            stats[skey]['pnl'] += r['pnl']
            stats[skey]['trades'] += r['count']
            stats[skey]['n'] += 1
            stats[skey]['wr_sum'] += r['wr']
            if r['pnl'] > 0: stats[skey]['win_months'] += 1
            else: stats[skey]['loss_months'] += 1
            running[skey] += r['pnl']
            if running[skey] > peak[skey]:
                peak[skey] = running[skey]
            dd = peak[skey] - running[skey]
            if dd > mdd[skey]:
                mdd[skey] = dd
        else:
            line += f' {"N/A":>28} |'
    print(line)

# 统计行
print(sep)
total_line = f'  {"TOTAL":>6} |'
for skey, slabel, _ in STRATEGIES:
    s = stats[skey]
    if s['n'] > 0:
        avg_wr = s['wr_sum']/s['n']
        total_line += f' ${s["pnl"]:>+9.0f} WR{avg_wr:>.0f}% {s["trades"]:>5}T {s["win_months"]}W/{s["loss_months"]}L |'
    else:
        total_line += f' {"N/A":>28} |'
print(total_line)

# 月均行
avg_line = f'  {"月均":>6} |'
for skey, slabel, _ in STRATEGIES:
    s = stats[skey]
    if s['n'] > 0:
        avg_line += f' ${s["pnl"]/s["n"]:>+8.0f} 盈{s["win_months"]}/{s["n"]}月 |'
    else:
        avg_line += f' {"N/A":>28} |'
print(avg_line)

# 最大回撤行
mdd_line = f'  {"MDD":>6} |'
for skey, slabel, _ in STRATEGIES:
    if mdd[skey] > 0:
        mdd_line += f' ${mdd[skey]:>+10.0f} (${peak[skey]:>.0f}峰)       |'
    else:
        mdd_line += f' {"N/A":>28} |'
print(mdd_line)

print(f'\n  总耗时: {(time.time()-t0_total)/60:.1f}min  |  数据: {SAVE_PATH}')
print('DONE')
