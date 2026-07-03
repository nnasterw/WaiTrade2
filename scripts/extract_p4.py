#!/usr/bin/env python3
"""Parse Phase 4: 2026 5-month MTF comparison."""
from pathlib import Path
import re, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_results import extract, max_consecutive

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')

MONTHS = ['jan', 'feb', 'mar', 'apr', 'may']
MONTH_LABELS = {'jan':'1月','feb':'2月','mar':'3月','apr':'4月','may':'5月'}

print(f"\n{'Month':<6} | {'OFF Trades':>10} | {'OFF Net$':>10} | {'OFF Bal':>10} | {'OFF PF':>7} | "
      f"{'ALL Trades':>10} | {'ALL Net$':>10} | {'ALL Bal':>10} | {'ALL PF':>7} | "
      f"{'Trade -%':>8} | {'Net Delta':>10}")
print("-" * 130)

totals_off = {'trades': 0, 'pnl': 0.0}
totals_all = {'trades': 0, 'pnl': 0.0}

for m in MONTHS:
    r_off = extract(DATA / f'p4_{m}_off.htm')
    r_all = extract(DATA / f'p4_{m}_all.htm')

    t_off = int(r_off.get('total_out_trades', 0))
    t_all = int(r_all.get('total_out_trades', 0))
    n_off = float(r_off.get('total_pnl', 0))
    n_all = float(r_all.get('total_pnl', 0))
    b_off = r_off.get('balance', '?')
    b_all = r_all.get('balance', '?')
    pf_off = r_off.get('pf', '?')
    pf_all = r_all.get('pf', '?')

    trade_pct = (1 - t_all/t_off)*100 if t_off > 0 else 0
    net_delta = n_all - n_off

    totals_off['trades'] += t_off
    totals_off['pnl'] += n_off
    totals_all['trades'] += t_all
    totals_all['pnl'] += n_all

    label = MONTH_LABELS[m]
    print(f'{label:<6} | {t_off:>10} | {n_off:>10.2f} | {b_off:>10} | {pf_off:>7} | '
          f'{t_all:>10} | {n_all:>10.2f} | {b_all:>10} | {pf_all:>7} | '
          f'{trade_pct:>7.1f}% | {net_delta:>+10.2f}')

# Totals
print("-" * 130)
print(f'{"合计":<6} | {totals_off["trades"]:>10} | {totals_off["pnl"]:>10.2f} | {"":>10} | {"":>7} | '
      f'{totals_all["trades"]:>10} | {totals_all["pnl"]:>10.2f} | {"":>10} | {"":>7} | '
      f'{(1-totals_all["trades"]/totals_off["trades"])*100:>7.1f}% | {totals_all["pnl"]-totals_off["pnl"]:>+10.2f}')

# Also detailed table
print(f"\n{'Month':<6} {'Config':<6} {'Trades':>6} {'W':>4} {'L':>4} {'WR%':>7} {'Net$':>8} {'Bal':>10} {'PF':>6} {'AvgW':>7} {'AvgL':>7} {'MaxCL':>6}")
print("-"*100)
for m in MONTHS:
    for cfg in ['off', 'all']:
        r = extract(DATA / f'p4_{m}_{cfg}.htm')
        label = f'{MONTH_LABELS[m]} {cfg}'
        print(f'{label:<12} {r.get("total_out_trades","?"):>6} {r.get("wins","?"):>4} {r.get("losses","?"):>4} '
              f'{r.get("win_rate","?"):>7} {r.get("total_pnl","?"):>8} {r.get("balance","?"):>10} '
              f'{r.get("pf","?"):>6} {r.get("avg_win","?"):>7} {r.get("avg_loss","?"):>7} {r.get("max_consecutive_losses","?"):>6}')
