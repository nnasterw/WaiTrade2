#!/usr/bin/env python3
import yaml, subprocess, sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# D1: Bounce gradient
d1_tests = {
    'v11xau-qs3-d1a': dict(risk_percent=1.5, max_pos_mult=2.0, max_lot_size=3.0, max_concurrent=5,
        max_entries_per_ob=5, bounce_pct=0.22, bounce_sweet_min_pct=0.26,
        outside_bounce_sweet_mult=0.5, min_risk_spread_ratio=3.0, version='V11XAU-QS3-D1A',
        magic_number=204879, description="D1A弱反弹:bounce0.22"),
    'v11xau-qs3-d1b': dict(risk_percent=1.5, max_pos_mult=2.0, max_lot_size=3.0, max_concurrent=5,
        max_entries_per_ob=5, bounce_pct=0.30, bounce_sweet_min_pct=0.35,
        outside_bounce_sweet_mult=0.4, min_risk_spread_ratio=3.0, version='V11XAU-QS3-D1B',
        magic_number=204878, description="D1B中反弹:bounce0.30"),
    'v11xau-qs3-d1c': dict(risk_percent=1.5, max_pos_mult=2.0, max_lot_size=3.0, max_concurrent=5,
        max_entries_per_ob=5, bounce_pct=0.40, bounce_sweet_min_pct=0.40,
        outside_bounce_sweet_mult=0.3, min_risk_spread_ratio=3.0, version='V11XAU-QS3-D1C',
        magic_number=204877, description="D1C强反弹:bounce0.40"),
}

# D2: OB freshness (MaxOBAgeBarsTF)
d2_tests = {
    'v11xau-qs3-d2a': dict(risk_percent=1.5, max_pos_mult=2.0, max_lot_size=3.0, max_concurrent=5,
        max_entries_per_ob=5, bounce_pct=0.22, bounce_sweet_min_pct=0.30,
        outside_bounce_sweet_mult=0.4, min_risk_spread_ratio=3.0,
        max_ob_age_bars_tf=120, version='V11XAU-QS3-D2A', magic_number=204876,
        description="D2A OB2h新鲜"),
    'v11xau-qs3-d2b': dict(risk_percent=1.5, max_pos_mult=2.0, max_lot_size=3.0, max_concurrent=5,
        max_entries_per_ob=5, bounce_pct=0.22, bounce_sweet_min_pct=0.30,
        outside_bounce_sweet_mult=0.4, min_risk_spread_ratio=3.0,
        max_ob_age_bars_tf=180, version='V11XAU-QS3-D2B', magic_number=204875,
        description="D2B OB3h新鲜"),
    'v11xau-qs3-d2c': dict(risk_percent=1.5, max_pos_mult=2.0, max_lot_size=3.0, max_concurrent=5,
        max_entries_per_ob=5, bounce_pct=0.22, bounce_sweet_min_pct=0.30,
        outside_bounce_sweet_mult=0.4, min_risk_spread_ratio=3.0,
        max_ob_age_bars_tf=240, version='V11XAU-QS3-D2C', magic_number=204874,
        description="D2C OB4h新鲜"),
}

# D3: Touch limit
d3_tests = {
    'v11xau-qs3-d3': dict(risk_percent=1.5, max_pos_mult=2.0, max_lot_size=3.0, max_concurrent=5,
        max_entries_per_ob=2, bounce_pct=0.30, bounce_sweet_min_pct=0.35,
        outside_bounce_sweet_mult=0.4, min_risk_spread_ratio=3.0,
        max_counter_risk_atr=0.5, version='V11XAU-QS3-D3', magic_number=204873,
        description="D3触碰上限2(H2A+max2)"),
}

# D6: H2A micro-tune
d6_tests = {
    'v11xau-qs3-d6': dict(risk_percent=1.5, max_pos_mult=2.0, max_lot_size=3.0, max_concurrent=5,
        max_entries_per_ob=2, bounce_pct=0.30, bounce_sweet_min_pct=0.35,
        outside_bounce_sweet_mult=0.4, min_risk_spread_ratio=3.0,
        max_counter_risk_atr=0.5, max_ob_age_bars_tf=180, ob_reentry_cooldown_min=5,
        version='V11XAU-QS3-D6', magic_number=204872,
        description="D6 H2A微调:age180+touch2+cooldown5"),
}

all_tests = [('D1', d1_tests), ('D2', d2_tests), ('D3', d3_tests), ('D6', d6_tests)]
windows = [("2026.06.02", "2026.06.03", "0602"), ("2025.05.28", "2025.05.30", "0529")]

for group_name, tests in all_tests:
    print(f"\n{'='*60}")
    print(f"  {group_name}")
    print(f"{'='*60}")

    # Add to YAML
    with open(ROOT / 'config' / 'strategies.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    for name, params in tests.items():
        base = dict(config['v11xau-qs'])
        base.update(params)
        config[name] = base

    with open(ROOT / 'config' / 'strategies.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'yaml_to_set.py'), '--all'],
                   capture_output=True, cwd=str(ROOT))

    for name in tests:
        for date_from, date_to, label in windows:
            print(f"  [{name} {label}] ", end='', flush=True)
            result = subprocess.run([
                sys.executable, str(ROOT / 'scripts' / 'mt5_backtest_win.py'),
                '--strategy', name, '--symbol', 'XAUUSDm',
                '--from', date_from, '--to', date_to,
                '--model', '4', '--timeout', '300',
            ], capture_output=True, text=True, cwd=str(ROOT))
            m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', result.stdout + result.stderr)
            if m:
                t = m.group(1); wr = m.group(2); bal = m.group(3)
                days = 2 if '0529' in label else 1
                dt = f"{int(t)//days}/天"
                print(f"\r  {name:<20} {label}: {dt:>6} {wr:>6}% ${bal:>10}")
            else:
                print(f"\r  {name:<20} {label}: FAILED")

# Cleanup: remove test strategies
with open(ROOT / 'config' / 'strategies.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
for tests in [d1_tests, d2_tests, d3_tests, d6_tests]:
    for name in tests:
        config.pop(name, None)
with open(ROOT / 'config' / 'strategies.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
