#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure ASCII compact chart - one row per strategy w/ spark bars"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

P25 = {
    'QS3':[23.86,211.33,66.93,4586.72,2351.44],
    'Q2':[39.94,176.73,117.96,1648.91,1013.65],
    'QS4':[11.42,107.04,48.81,1056.30,667.14],
    'NOI':[-2.79,-19.96,24.46,320.72,26.80],
}
P26 = {
    'QS3':[-31.93,-156.88,-180.72,-142.76,-199.01],
    'Q2':[26.75,-198.50,-172.90,-198.02,-197.92],
    'QS4':[5.85,-149.26,-159.48,-116.64,-169.32],
    'NOI':[223.43,56.19,-97.27,-7.06,-36.09],
}

SYM = [('QS3','o'),('Q2','*'),('QS4','#'),('NOI','.')]
M = ['Jan','Feb','Mar','Apr','May']
# 8-level ASCII bar
BAR = ' _.*=#@8'

def draw(data, title):
    all_v = [v for row in data.values() for v in row]
    lo, hi = min(all_v), max(all_v)
    rng = hi - lo if hi != lo else 1

    print(f"\n  {title}")
    print(f"  {'─'*78}")
    print(f"         Bar       Jan      Feb      Mar      Apr      May      Total")
    print(f"  {'─'*78}")
    for key, sym in SYM:
        vs = data.get(key, [])
        total = sum(vs)
        bars = ''.join(BAR[min(7, max(0, int((v-lo)/rng*7)))] for v in vs)
        print(f"  {sym} {key:<4} {bars:>5}  {vs[0]:>+7,.0f} {vs[1]:>+7,.0f} {vs[2]:>+7,.0f} {vs[3]:>+7,.0f} {vs[4]:>+7,.0f}  ${total:>+7,.0f}")
    print(f"  {'─'*78}")
    print(f"  Bar: ' '=min {BAR[7]}=max  (${lo:+,.0f} ~ ${hi:+,.0f})")

draw(P25, "2025 PnL ($200)")
draw(P26, "2026 PnL ($200)")
