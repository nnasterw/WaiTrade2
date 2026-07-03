#!/usr/bin/env python3
"""Direct .set manipulation for D1-D6 tests - bypasses YAML"""
import subprocess, sys, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SET_DIR = ROOT / 'mql5' / 'Presets'
BASE_SET = SET_DIR / 'V11XAU-QS3.set'

def make_set(name, magic, version, desc, **overrides):
    """Copy base QS3 set and override params"""
    dst = SET_DIR / f'{name}.set'
    content = BASE_SET.read_text(encoding='utf-8')
    content = content.replace('InpVersion=V11XAU-QS3', f'InpVersion={version}')
    content = content.replace('InpMagicNumber=204897', f'InpMagicNumber={magic}')
    for key, val in overrides.items():
        old = f'{key}='
        # Find existing line
        for line in content.split('\n'):
            if line.startswith(old):
                content = content.replace(line, f'{key}={val}')
                break
        else:
            # Add new param
            content += f'\n{key}={val}\n'
    dst.write_text(content)

def run_bt(name, date_from, date_to):
    result = subprocess.run([
        sys.executable, str(ROOT / 'scripts' / 'mt5_backtest_win.py'),
        '--strategy', name, '--symbol', 'XAUUSDm',
        '--from', date_from, '--to', date_to,
        '--model', '4', '--timeout', '300',
    ], capture_output=True, text=True, cwd=str(ROOT))
    m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', result.stdout + result.stderr)
    return (int(m.group(1)), float(m.group(2)), float(m.group(3))) if m else None

# D1: Bounce gradient
print("="*60)
print("  D1: Bounce Gradient")
print("="*60)
d1 = [
    ('V11XAU-QS3-D1A', 204879, dict(InpBouncePct='0.22', InpBounceSweetMinPct='0.26', InpOutsideBounceSweetMult='0.5')),
    ('V11XAU-QS3-D1B', 204878, dict(InpBouncePct='0.30', InpBounceSweetMinPct='0.35', InpOutsideBounceSweetMult='0.4')),
    ('V11XAU-QS3-D1C', 204877, dict(InpBouncePct='0.40', InpBounceSweetMinPct='0.40', InpOutsideBounceSweetMult='0.3')),
]
for ver, mag, params in d1:
    name = f'v11xau-qs3-{ver.split("-")[-1].lower()}'
    make_set(name, mag, ver, '', **params)

for ver, mag, params in d1:
    name = f'v11xau-qs3-{ver.split("-")[-1].lower()}'
    r0602 = run_bt(name, '2026.06.02', '2026.06.03')
    r0529 = run_bt(name, '2025.05.28', '2025.05.30')
    print(f"  {name}: 0602={r0602[0]}t/{r0602[1]}%/${r0602[2]}" if r0602 else f"  {name}: 0602=FAIL")
    print(f"  {name}: 0529={r0529[0]}t/{r0529[1]}%/${r0529[2]}" if r0529 else f"  {name}: 0529=FAIL")

# D2: OB freshness
print("\n" + "="*60)
print("  D2: OB Freshness")
print("="*60)
for age, label in [(120,'2h'), (180,'3h'), (240,'4h')]:
    name = f'v11xau-qs3-d2{label}'
    make_set(name, 204875, f'V11XAU-QS3-D2-{label}', '', InpMaxOBAgeBarsTF=str(age))
    r0602 = run_bt(name, '2026.06.02', '2026.06.03')
    r0529 = run_bt(name, '2025.05.28', '2025.05.30')
    print(f"  {name}: 0602={r0602[0]}t/{r0602[1]}%/${r0602[2]}" if r0602 else f"  {name}: 0602=FAIL")
    print(f"  {name}: 0529={r0529[0]}t/{r0529[1]}%/${r0529[2]}" if r0529 else f"  {name}: 0529=FAIL")

# D3: Touch limit (H2A + touch=2)
print("\n" + "="*60)
print("  D3: Touch Limit (H2A+max2)")
print("="*60)
make_set('v11xau-qs3-d3', 204873, 'V11XAU-QS3-D3', '',
    InpBouncePct='0.30', InpBounceSweetMinPct='0.35', InpOutsideBounceSweetMult='0.4',
    InpMaxCounterRiskATR='0.5', InpMaxEntriesPerOB='2')
r0602 = run_bt('v11xau-qs3-d3', '2026.06.02', '2026.06.03')
r0529 = run_bt('v11xau-qs3-d3', '2025.05.28', '2025.05.30')
print(f"  D3: 0602={r0602[0]}t/{r0602[1]}%/${r0602[2]}" if r0602 else "  D3: 0602=FAIL")
print(f"  D3: 0529={r0529[0]}t/{r0529[1]}%/${r0529[2]}" if r0529 else "  D3: 0529=FAIL")

# D6: H2A micro-tune
print("\n" + "="*60)
print("  D6: H2A Micro-tune (age=180+touch=2+cooldown=5)")
print("="*60)
make_set('v11xau-qs3-d6', 204872, 'V11XAU-QS3-D6', '',
    InpBouncePct='0.30', InpBounceSweetMinPct='0.35', InpOutsideBounceSweetMult='0.4',
    InpMaxCounterRiskATR='0.5', InpMaxEntriesPerOB='2',
    InpMaxOBAgeBarsTF='180', InpOBReentryCooldownMin='5')
r0602 = run_bt('v11xau-qs3-d6', '2026.06.02', '2026.06.03')
r0529 = run_bt('v11xau-qs3-d6', '2025.05.28', '2025.05.30')
print(f"  D6: 0602={r0602[0]}t/{r0602[1]}%/${r0602[2]}" if r0602 else "  D6: 0602=FAIL")
print(f"  D6: 0529={r0529[0]}t/{r0529[1]}%/${r0529[2]}" if r0529 else "  D6: 0529=FAIL")
