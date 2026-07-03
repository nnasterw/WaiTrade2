#!/usr/bin/env python3
"""D1-D6 tests: add to YAML -> gen set -> run -> remove"""
import subprocess, sys, re, yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / 'config' / 'strategies.yaml'

base_params = {
    'risk_percent': 1.5, 'max_pos_mult': 2.0, 'max_lot_size': 3.0,
    'max_concurrent': 5, 'max_entries_per_ob': 5,
    'bounce_pct': 0.22, 'bounce_sweet_min_pct': 0.30,
    'outside_bounce_sweet_mult': 0.4, 'min_risk_spread_ratio': 3.0,
}

tests = [
    # D1: Bounce gradient
    ('D1A', 'bounce0.22', dict(bounce_pct=0.22, bounce_sweet_min_pct=0.26, outside_bounce_sweet_mult=0.5)),
    ('D1B', 'bounce0.30', dict(bounce_pct=0.30, bounce_sweet_min_pct=0.35, outside_bounce_sweet_mult=0.4)),
    ('D1C', 'bounce0.40', dict(bounce_pct=0.40, bounce_sweet_min_pct=0.40, outside_bounce_sweet_mult=0.3)),
    # D2: OB freshness
    ('D2A', 'age2h', dict(max_ob_age_bars_tf=120)),
    ('D2B', 'age3h', dict(max_ob_age_bars_tf=180)),
    ('D2C', 'age4h', dict(max_ob_age_bars_tf=240)),
    # D3: Touch limit
    ('D3', 'h2a+touch2', dict(bounce_pct=0.30, bounce_sweet_min_pct=0.35, outside_bounce_sweet_mult=0.4,
                                max_counter_risk_atr=0.5, max_entries_per_ob=2)),
    # D6: H2A micro-tune
    ('D6', 'h2a-micro', dict(bounce_pct=0.30, bounce_sweet_min_pct=0.35, outside_bounce_sweet_mult=0.4,
                              max_counter_risk_atr=0.5, max_entries_per_ob=2,
                              max_ob_age_bars_tf=180, ob_reentry_cooldown_min=5)),
]

windows = [("2026.06.02", "2026.06.03", "0602"), ("2025.05.28", "2025.05.30", "0529")]

# Load YAML
with open(YAML_PATH, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Add test strategies
for label, desc, overrides in tests:
    name = f'v11xau-qs3-{label.lower()}'
    params = dict(base_params)
    params.update(overrides)
    params['version'] = f'V11XAU-QS3-{label}'
    params['description'] = f'{label}:{desc}'
    params['magic_number'] = 204800 + len(config)
    config[name] = params

# Save YAML
with open(YAML_PATH, 'w', encoding='utf-8') as f:
    yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

# Generate .set files
subprocess.run([sys.executable, str(ROOT / 'scripts' / 'yaml_to_set.py'), '--all'],
               capture_output=True, cwd=str(ROOT))

# Run tests
for label, desc, overrides in tests:
    name = f'v11xau-qs3-{label.lower()}'
    for date_from, date_to, wlabel in windows:
        result = subprocess.run([
            sys.executable, str(ROOT / 'scripts' / 'mt5_backtest_win.py'),
            '--strategy', name, '--symbol', 'XAUUSDm',
            '--from', date_from, '--to', date_to,
            '--model', '4', '--timeout', '300',
        ], capture_output=True, text=True, cwd=str(ROOT))
        m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', result.stdout + result.stderr)
        if m:
            days = 2 if '0529' in wlabel else 1
            dt = int(m.group(1)) // days
            print(f"{label:<6} {wlabel}: {dt:>3}t/d {m.group(2):>5}% ${float(m.group(3)):>10.2f}")
        else:
            print(f"{label:<6} {wlabel}: FAILED")

# Cleanup: remove test strategies
with open(YAML_PATH, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
for label, _, _ in tests:
    config.pop(f'v11xau-qs3-{label.lower()}', None)
with open(YAML_PATH, 'w', encoding='utf-8') as f:
    yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
