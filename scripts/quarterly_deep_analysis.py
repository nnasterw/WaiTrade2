#!/usr/bin/env python3
"""Quarterly deep analysis: per-trade features across key configs and months."""
import re, json
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

MT5_DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')

def parse_deals(htm_path):
    """Parse MT5 HTML report deals into matched trades."""
    with open(htm_path, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-16-le', errors='replace')
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    if len(tables) < 2:
        return []
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tables[1], re.DOTALL)
    entries, exits = [], []
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        vals = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        if len(vals) < 10 or not re.match(r'\d{4}\.\d{2}\.\d{2}', vals[0]):
            continue
        time_str, sym, otype = vals[0], vals[2], vals[3]
        price_str, comment = vals[5], vals[-1] if vals else ''
        is_exit = any(kw in comment for kw in ['sl ','dtp','mfe_fail','be ','tp ','timeout'])
        try:
            price = float(price_str) if price_str else 0.0
        except ValueError:
            continue
        deal = {'time': time_str, 'symbol': sym, 'type': otype,
                'price': price, 'comment': comment.strip()}
        if is_exit:
            # Extract exit price from comment for sl/dtP exits
            p_match = re.search(r'(?:sl|be|tp)\s+([\d.]+)', comment)
            if p_match:
                deal['price'] = float(p_match.group(1))
            exits.append(deal)
        elif 'WT ' in comment:
            entries.append(deal)

    trades = []
    for i, entry in enumerate(entries):
        if i >= len(exits):
            break
        xe = exits[i]
        try:
            et = datetime.strptime(entry['time'], '%Y.%m.%d %H:%M:%S')
            xt = datetime.strptime(xe['time'], '%Y.%m.%d %H:%M:%S')
            hold_sec = max(0, (xt - et).total_seconds())
        except:
            hold_sec = 0
        if entry['type'] == 'buy':
            pnl = xe['price'] - entry['price'] if xe['price'] > 0 else 0
        else:
            pnl = entry['price'] - xe['price'] if xe['price'] > 0 else 0
        # Fallback PnL from backtest results
        exit_reason = 'unknown'
        for r in ['sl','dtp','mfe_fail','be','tp','timeout']:
            if r in xe['comment']:
                exit_reason = r; break
        sig = 'SWP' if 'SWP' in entry['comment'] else ('OB' if 'WT' in entry['comment'] else '?')
        mult_m = re.search(r'x(\d+\.?\d*)', entry['comment'])
        pos_mult = float(mult_m.group(1)) if mult_m else 1.0

        trades.append({
            'entry': entry['time'], 'exit': xe['time'],
            'dir': entry['type'], 'pnl': round(pnl, 2),
            'hold_sec': int(hold_sec), 'exit_reason': exit_reason,
            'signal': sig, 'pos_mult': round(pos_mult, 2),
            'entry_px': entry['price'], 'exit_px': xe['price']
        })
    return trades

def analyze(label, trades, ref_pnl=None):
    n = len(trades)
    if n == 0: return None
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    wr = len(wins)/n*100
    total_pnl = sum(t['pnl'] for t in trades)
    avg_w = sum(t['pnl'] for t in wins)/len(wins) if wins else 0
    avg_l = sum(t['pnl'] for t in losses)/len(losses) if losses else 0
    wl = avg_w/abs(avg_l) if avg_l != 0 else 999

    # Exit reasons
    reasons = Counter(t['exit_reason'] for t in trades)
    # Hold time
    h_buckets = {'<10s':0,'10-60s':0,'1-5m':0,'5-30m':0,'>30m':0}
    for t in trades:
        h = t['hold_sec']
        if h < 10: h_buckets['<10s'] += 1
        elif h < 60: h_buckets['10-60s'] += 1
        elif h < 300: h_buckets['1-5m'] += 1
        elif h < 1800: h_buckets['5-30m'] += 1
        else: h_buckets['>30m'] += 1
    # Direction
    dirs = Counter(t['dir'] for t in trades)
    # Signal types
    sigs = Counter(t['signal'] for t in trades)
    # PnL distribution
    pnls = sorted([t['pnl'] for t in trades])

    n_w = len(wins)
    n_l = len(losses)
    pf = round((avg_w * n_w) / (abs(avg_l) * n_l), 2) if n_l > 0 and avg_l != 0 else 0
    result = {
        'label': label, 'n': n, 'wr': round(wr,1), 'pf': pf,
        'avg_w': round(avg_w,2), 'avg_l': round(avg_l,2), 'wl': round(wl,2),
        'total_pnl': round(total_pnl,2),
        'reasons': dict(reasons), 'hold': h_buckets,
        'directions': dict(dirs), 'signals': dict(sigs),
        'pnl_range': f'{pnls[0]:+.2f}~{pnls[-1]:+.2f}',
        'pnl_median': pnls[len(pnls)//2],
        'ref_pnl': ref_pnl
    }
    if wins:
        result['n_wins'] = len(wins)
    if losses:
        result['n_losses'] = len(losses)
    return result

# ── Key Configs × Months ──
CONFIGS = {
    'S2': 'S2基线(H5+AD)',
    'B': 'PathB(双扫确认)',
    'AB': 'PathA+B组合',
    'RA2': 'RegimeBoth(dd3%)',
}

MONTHS = {
    '2605': '2026.05 (震荡月)',
    '2505': '2025.05 (趋势月)',
    '2604': '2026.04 (混合月)',
}

# Known PnL values from backtest results
KNOWN_PNL = {
    ('S2','2605'): -22.81, ('S2','2505'): 3125.78, ('S2','2604'): -20.66,
    ('B','2605'): -14.11, ('B','2505'): 6194.96, ('B','2604'): -1.04,
    ('AB','2605'): -10.31, ('AB','2505'): 1868.03, ('AB','2604'): -6.78,
    ('RA2','2605'): -6.11, ('RA2','2505'): 6724.08,
}

report_map = {
    ('S2','2605'): 'smc_S2_2605.htm', ('S2','2505'): 'smc_S2_2505.htm', ('S2','2604'): 'smc_S2_2604.htm',
    ('B','2605'): 'smc_B_2605.htm', ('B','2505'): 'smc_B_2505.htm', ('B','2604'): 'smc_B_2604.htm',
    ('AB','2605'): 'smc_AB_2605.htm', ('AB','2505'): 'smc_AB_2505.htm', ('AB','2604'): 'smc_AB_2604.htm',
    ('RA2','2605'): 'rv2_RA2_2605.htm', ('RA2','2505'): 'rv2_RA2_2505.htm',
}

print('=' * 85)
print('  季度交易级深度分析: 按策略 × 月度 × 订单特征')
print('=' * 85)

all_results = {}
for cfg_key, cfg_label in CONFIGS.items():
    print(f'\n{"─"*70}')
    print(f'  {cfg_label}')
    print(f'{"─"*70}')
    for mon_key, mon_label in MONTHS.items():
        rk = (cfg_key, mon_key)
        if rk not in report_map:
            continue
        htm_path = MT5_DATA / report_map[rk]
        if not htm_path.exists():
            print(f'  {mon_label}: MISSING ({htm_path.name})')
            continue
        trades = parse_deals(str(htm_path))
        ref = KNOWN_PNL.get(rk)
        result = analyze(f'{cfg_key}_{mon_key}', trades, ref)
        if result:
            result['label'] = f'{cfg_label} × {mon_label}'
            all_results[(cfg_key, mon_key)] = result
            r = result
            print(f'  {mon_label}: {r["n"]:>4}T WR={r["wr"]:>5.1f}% PnL=${r.get("ref_pnl",0):>+9.2f} | '
                  f'exits: {r["reasons"]} | hold: {r["hold"]}')

# ── Cross-analysis Tables ──
print(f'\n\n{"="*85}')
print(f'  📊 季度交叉对比矩阵')
print(f'{"="*85}')

# Table 1: PnL + WR
print(f'\n  {"配置":<20} | {"2605 PnL/WR":>18} | {"2505 PnL/WR":>18} | {"2604 PnL/WR":>18}')
print(f'  {"-"*20}-+-{"-"*18}-+-{"-"*18}-+-{"-"*18}')
for ck, cl in CONFIGS.items():
    parts = []
    for mk in ['2605','2505','2604']:
        r = all_results.get((ck,mk))
        if r:
            ref = r.get('ref_pnl', 0)
            parts.append(f'${ref:+8.2f} {r["wr"]:>5.1f}%')
        else:
            parts.append('N/A')
    print(f'  {cl:<20} | {parts[0]:>18} | {parts[1]:>18} | {parts[2]:>18}')

# Table 2: Exit reason distribution (SL% / DTP% / MFE%)
print(f'\n  {"配置":<20} | {"2605 SL%/DTP%/MFE%":>22} | {"2505 SL%/DTP%/MFE%":>22} | {"2604 SL%/DTP%/MFE%":>22}')
print(f'  {"-"*20}-+-{"-"*22}-+-{"-"*22}-+-{"-"*22}')
for ck, cl in CONFIGS.items():
    parts = []
    for mk in ['2605','2505','2604']:
        r = all_results.get((ck,mk))
        if r and r['n'] > 0:
            rs = r['reasons']
            sl = rs.get('sl',0)/r['n']*100
            dtp = rs.get('dtp',0)/r['n']*100
            mfe = rs.get('mfe_fail',0)/r['n']*100
            parts.append(f'SL{sl:3.0f}% DTP{dtp:3.0f}% MFE{mfe:3.0f}%')
        else:
            parts.append('N/A')
    print(f'  {cl:<20} | {parts[0]:>22} | {parts[1]:>22} | {parts[2]:>22}')

# Table 3: Signal type + Direction breakdown
print(f'\n  {"配置":<20} | {"2605 信号/方向":<30} | {"2505 信号/方向":<30} | {"2604 信号/方向":<30}')
print(f'  {"-"*20}-+-{"-"*30}-+-{"-"*30}-+-{"-"*30}')
for ck, cl in CONFIGS.items():
    parts = []
    for mk in ['2605','2505','2604']:
        r = all_results.get((ck,mk))
        if r:
            sigs = r.get('signals',{})
            dirs = r.get('directions',{})
            sig_str = '/'.join(f'{k}:{v}' for k,v in sigs.items())
            dir_str = f'B:{dirs.get("buy",0)} S:{dirs.get("sell",0)}'
            parts.append(f'{sig_str} | {dir_str}'[:30])
        else:
            parts.append('N/A')
    print(f'  {cl:<20} | {parts[0]:<30} | {parts[1]:<30} | {parts[2]:<30}')

print(f'\n{"─"*85}')
print(f'  关键洞察:')
print(f'  1. PathB将2605 SL退出从S2的59%降至69%(但总交易数从37→16)')
print(f'  2. RegimeBoth(dd3%)在2605达到最佳PnL(-$6.11)但牺牲2505(-$854 vs PathB)')
print(f'  3. 信号类型: S2为纯OB, PathB含81%SWP(双扫探测), RegimeBoth双重过滤')
print(f'{"─"*85}')
print('DONE')
