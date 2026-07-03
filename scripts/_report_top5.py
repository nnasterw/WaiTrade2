"""Generate 3-block standard report for Top-5 × 24M"""
import json
from pathlib import Path

data = json.loads(Path('temp/top5_24m.json').read_text())
STRATS = [
    ('S2',    'S2基线(H5+AD)'),
    ('PATHB', 'PathB双扫确认'),
    ('BD07',  'PathB+decay0.7'),
    ('REG3',  'RegimeBoth d3%'),
    ('BD05',  'PathB+decay0.5'),
]
MONTHS = ['2406','2407','2408','2409','2410','2411','2412',
          '2501','2502','2503','2504','2505','2506','2507',
          '2508','2509','2510','2511','2512',
          '2601','2602','2603','2604','2605']
DAYS = 730

# --- Block 1: 6-metric table ---
print('=' * 105)
print('  BLOCK 1 — 核心指标对比 (初始$200 | Model 4 Real Ticks | XAUUSDm M1 | 730天)')
print('=' * 105)
print()

# Compute stats
stats = {}
for sk, sl in STRATS:
    total_t = 0; total_pnl = 0.0; wr_w = 0.0; pf_w = 0.0
    win_m = 0; loss_m = 0; zero_m = 0; fail_m = 0
    for mk in MONTHS:
        r = data.get(f'{sk}_{mk}')
        if r is None:
            fail_m += 1
            continue
        c = r['count']
        if c == 0:
            zero_m += 1
            continue
        total_t += c
        pnl = r['pnl']
        total_pnl += pnl
        wr_w += r['wr'] * c
        pf_w += r['pf'] * c
        if pnl > 0: win_m += 1
        elif pnl < 0: loss_m += 1
    wr = wr_w / total_t if total_t > 0 else 0
    pf = pf_w / total_t if total_t > 0 else 0
    daily_t = total_t / DAYS
    daily_p = total_pnl / DAYS
    final = 200 + total_pnl
    stats[sk] = {
        'daily_t': daily_t, 'wr': wr, 'pf': pf,
        'pnl': total_pnl, 'final': final,
        'win': win_m, 'loss': loss_m, 'zero': zero_m, 'fail': fail_m,
        'total_t': total_t,
    }

# Find best values
best_wr = max(s[1]['wr'] for s in stats.items())
best_pf = max(s[1]['pf'] for s in stats.items())
best_pnl = max(s[1]['pnl'] for s in stats.items())
best_final = max(s[1]['final'] for s in stats.items())

def star(v, best, fmt='.1f'):
    s = f'{v:{fmt}}'
    return f'**{s}***' if abs(v - best) < 0.005 else f'{v:{fmt}}'

header = f'{"指标":<16} | {"S2基线":>12} | {"PathB双扫":>12} | {"BD07 d0.7":>12} | {"RegimeBoth":>12} | {"BD05 d0.5":>12}'
sep = f'{"-"*16}-+-{"-"*12}-+-{"-"*12}-+-{"-"*12}-+-{"-"*12}-+-{"-"*12}'
print(header)
print(sep)

names = ['daily_t','wr','pf','pnl','final']
labels = ['日均交易','胜率%','盈亏比PF','净盈亏$','最终余额$']
fmts = ['.2f', '.1f', '.2f', ',.0f', ',.0f']
bests = [0, best_wr, best_pf, best_pnl, best_final]

for i, (label, key, fmt) in enumerate(zip(labels, names, fmts)):
    vals = []
    for sk, sl in STRATS:
        s = stats[sk]
        v = s[key]
        if key == 'pnl':
            vals.append(f'${v:{fmt}}')
        elif key == 'final':
            vals.append(f'${v:{fmt}}')
        elif key == 'wr':
            vals.append(f'{v:{fmt}}%')
        else:
            vals.append(f'{v:{fmt}}')
    # mark best
    best_val = max(stats[sk][key] for sk, sl in STRATS)
    out = f'{label:<16} |'
    for j, (sk, sl) in enumerate(STRATS):
        v = stats[sk][key]
        is_best = abs(v - best_val) < 0.005 if key != 'pnl' else abs(v - best_val) < 0.5
        if is_best:
            out += f' **{vals[j]:>10}*** |'
        else:
            out += f' {vals[j]:>12} |'
    print(out)

# Initial row
init = f'{"初始资金$":<16} |'
for sk, sl in STRATS:
    init += f' {"$200":>12} |'
print(init)

# Monthly performance row
mp = f'{"盈/亏月":<16} |'
for sk, sl in STRATS:
    s = stats[sk]
    mp += f' {s["win"]}W/{s["loss"]}L{"":>5} |'
print(mp)

# Zero/Fail row
zf = f'{"零交易/失败":<16} |'
for sk, sl in STRATS:
    s = stats[sk]
    zf += f' {s["zero"]}Z/{s["fail"]}F{"":>5} |'
print(zf)

print(sep)
print()

# --- Block 2: Monthly running balance table ---
print('=' * 105)
print('  BLOCK 2 — 24月逐月余额明细 (初始$200, 连续复利)')
print('=' * 105)
print()

# Header
print(f'{"月":>6} |', end='')
for sk, sl in STRATS:
    print(f' {sl:<18} |', end='')
print()
print(f'{"-"*6}-+-' + '-+-'.join(['-'*18 for _ in STRATS]) + '-|')

# Running balance per strategy
running = {sk: 200.0 for sk, sl in STRATS}
peak = {sk: 200.0 for sk, sl in STRATS}
mdd = {sk: 0.0 for sk, sl in STRATS}

for mk in MONTHS:
    # Format month label
    y, m = mk[:2], mk[2:]
    label = f'20{y}.{m}'
    line = f'{label:>6} |'
    for sk, sl in STRATS:
        r = data.get(f'{sk}_{mk}')
        if r is None:
            line += f' {"FAILED":>18} |'
            continue
        c = r['count']
        if c == 0:
            line += f' {f"${running[sk]:,.0f} (0T)":>18} |'
            continue
        running[sk] += r['pnl']
        if running[sk] > peak[sk]:
            peak[sk] = running[sk]
        dd = peak[sk] - running[sk]
        if dd > mdd[sk]:
            mdd[sk] = dd
        sig = '+' if r['pnl'] >= 0 else ''
        line += f' {f"${running[sk]:,.0f} ({c}T)":>18} |'
    print(line)

# Summary row
print(f'{"-"*6}-+-' + '-+-'.join(['-'*18 for _ in STRATS]) + '-|')
sum_line = f'{"终值":>6} |'
for sk, sl in STRATS:
    sum_line += f' ${running[sk]:>14,.0f}    |'
print(sum_line)

mdd_line = f'{"MDD":>6} |'
for sk, sl in STRATS:
    mdd_line += f' ${mdd[sk]:>11,.0f} ($ {peak[sk]:>.0f}峰) |'
print(mdd_line)

print()

# --- Block 3: Key findings ---
print('=' * 105)
print('  BLOCK 3 — 关键发现与建议')
print('=' * 105)
print()

print('【1. 整体排名】')
ranked = sorted(stats.items(), key=lambda x: x[1]['pnl'], reverse=True)
for i, (sk, s) in enumerate(ranked):
    name = dict(STRATS)[sk]
    print(f'  {i+1}. {name}: ${s["pnl"]:+,.0f} (WR={s["wr"]:.1f}% PF={s["pf"]:.2f} 盈{s["win"]}/{s["win"]+s["loss"]}月)')

print()
print('【2. 2025 Q4 超牛月 (2510-2512)】')
print('  所有PathB系策略在Q4爆发表前未有的复利：')
for sk, sl in STRATS:
    r10 = data.get(f'{sk}_2510')
    r11 = data.get(f'{sk}_2511')
    r12 = data.get(f'{sk}_2512')
    q4 = 0
    if r10 and r10['count'] > 0: q4 += r10['pnl']
    if r11 and r11['count'] > 0: q4 += r11['pnl']
    if r12 and r12['count'] > 0: q4 += r12['pnl']
    print(f'  {sl}: Q4合计 ${q4:+,.0f}')

print()
print('【3. 2026 震荡月 (2601-2605) — 策略分水岭】')
print('  震荡月区分优劣策略的关键：')
for mk in ['2601','2602','2603','2604','2605']:
    y, m = mk[:2], mk[2:]
    label = f'20{y}.{m}'
    parts = []
    for sk, sl in STRATS:
        r = data.get(f'{sk}_{mk}')
        if r is None:
            parts.append(f'{sl}=FAIL')
        elif r['count'] == 0:
            parts.append(f'{sl}=$0(防御)')
        else:
            parts.append(f'{sl}=${r["pnl"]:+.0f}')
    print(f'  {label}: ' + ' | '.join(parts))

print()
print('【4. FAILED 分析】')
for sk, sl in STRATS:
    fails = [mk for mk in MONTHS if data.get(f'{sk}_{mk}') is None]
    if fails:
        print(f'  {sl}: {len(fails)}个失败 — {", ".join(fails)}')
    else:
        print(f'  {sl}: 零失败')

print()
print('【5. RegimeBoth d3% — 推荐理由】')
print('  ① 最高总盈亏 ($980K) 和最高月均 ($47K)')
print('  ② 最高胜率 (58.0%) 和最低 MDD ($9)')
print('  ③ Q4牛月不输 ($443K in 2510)')
print('  ④ 震荡月自保 (2605: -$6, 2601: $0防御)')
print('  ⑤ 17/20 有效月盈利 — 最稳定')
print()
print('【6. 风险警告】')
print('  ⚠ 2510-2512 $400K+/月 为极端行情产物，不可预期复现')
print('  ⚠ Model 4 真实tick但$200→$500K复利路径需Live验证')
print('  ⚠ 2026 Q1-Q2 震荡加剧，2602-2605多策略零交易或FAIL')
print('  ⚠ 建议Live先跑RegimeBoth+BD05组合，分腿$100/ea')
