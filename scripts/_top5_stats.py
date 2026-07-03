"""Compute 6-metric stats from top5_24m.json"""
import json, sys
from pathlib import Path

data = json.loads(Path('temp/top5_24m.json').read_text())
strategies = [
    ('S2',     'S2基线(H5+AD)'),
    ('PATHB',  'PathB 双扫确认'),
    ('BD07',   'PathB+decay0.7(最佳平衡)'),
    ('REG3',   'RegimeBoth d3%(最佳震荡)'),
    ('BD05',   'PathB+decay0.5(激进防御)'),
]
DAYS = 730  # 2024.06.01 - 2026.05.31

for sk, sl in strategies:
    total_trades = 0
    total_pnl = 0.0
    wr_w = 0.0
    pf_w = 0.0
    win_m = 0; loss_m = 0; zero_m = 0; fail_m = 0
    running = 200.0; peak = 200.0; mdd = 0.0
    months_data = []

    for mk in sorted([k for k in data if k.startswith(sk + '_')]):
        r = data[mk]
        mkey = mk.split('_')[1]
        if r is None:
            fail_m += 1
            months_data.append((mkey, None))
            continue
        c = r['count']
        if c == 0:
            zero_m += 1
            months_data.append((mkey, 0))
            continue
        total_trades += c
        pnl = r['pnl']
        total_pnl += pnl
        wr_w += r['wr'] * c
        pf_w += r['pf'] * c
        running += pnl
        if running > peak:
            peak = running
        dd = peak - running
        if dd > mdd:
            mdd = dd
        if pnl > 0:
            win_m += 1
        else:
            loss_m += 1
        months_data.append((mkey, pnl))

    if total_trades > 0:
        wr = wr_w / total_trades
        pf = pf_w / total_trades
    else:
        wr = 0; pf = 0

    valid = win_m + loss_m
    daily_t = total_trades / DAYS
    daily_p = total_pnl / DAYS
    final = 200 + total_pnl

    print(f'--- {sl} ---')
    print(f'日均交易={daily_t:.2f}')
    print(f'胜率={wr:.1f}%')
    print(f'PF={pf:.2f}')
    print(f'净盈亏=${total_pnl:,.0f}')
    print(f'最终余额=${final:,.0f}')
    print(f'初始=$200')
    print(f'盈月={win_m} 亏月={loss_m} 零交易={zero_m} 失败={fail_m}')
    print(f'MDD=${mdd:,.0f} 峰值=${peak:,.0f}')
    print(f'有效月={valid}')
    print()

    # Monthly detail
    line = '|'
    for mk, p in months_data:
        if p is None:
            line += ' N/A |'
        else:
            line += f' ${p:>+8,.0f} |'
    print(f'月度PnL: {line}')
    print()
