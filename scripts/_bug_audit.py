#!/usr/bin/env python3
"""Static audit: find bugs in the recent SMC improvements."""
import re
from pathlib import Path

ROOT = Path('D:/Code/codexProject/WaiTrade2/mql5/Include/WaiTrade2')
SE = ROOT / 'SignalEngine.mqh'
CONFIG = Path('D:/Code/codexProject/WaiTrade2/mql5/Include/WaiTrade2/Config.mqh')
EE = ROOT / 'EntryEngine.mqh'
PM = ROOT / 'PositionManager.mqh'
YTS = Path('D:/Code/codexProject/WaiTrade2/scripts/yaml_to_set.py')
SY = Path('D:/Code/codexProject/WaiTrade2/config/strategies.yaml')

def read(f):
    return f.read_text('utf-8', errors='replace')

issues = []

# 1. Check forward declarations completeness
se_text = read(SE)
config_text = read(CONFIG)

# Functions defined in SignalEngine.mqh (non-inline)
funcs_in_se = set(re.findall(r'^bool (\w+)\(', se_text, re.MULTILINE))
funcs_in_se |= set(re.findall(r'^double (\w+)\(', se_text, re.MULTILINE))
funcs_in_se |= set(re.findall(r'^int (\w+)\(', se_text, re.MULTILINE))

# Forward declarations in Config.mqh
fwd_decls = set(re.findall(r'^(bool|double|int) (\w+)\(\);', config_text, re.MULTILINE))
fwd_fn = {fn for _, fn in fwd_decls}

# These should be in Config.mqh as forward declarations
needs_fwd = {'IsAdaptiveNoiseGateDefensive', 'IsATRLowVolRegime', 'IsDoubleSweepRegime',
             'CfgTickNoiseGateMinDirRatio', 'CfgTickNoiseGateMaxRangeATR',
             'CfgAdaptiveBoostIn1HOB', 'CfgAdaptiveDeepEntryBoost', 'CfgAdaptiveMaxPosMult'}

missing_fwd = needs_fwd - fwd_fn
if missing_fwd:
    issues.append(('CRIT', f'缺少前向声明: {missing_fwd}'))

# 2. Check yaml_to_set.py mappings
yts_text = read(YTS)
yaml_keys = set(re.findall(r'"(enable_mitigation_entry|mitigation_entry_max_bars|mitigation_entry_only_range|mitigation_entry_only_defensive|mitigation_entry_signal_types|enable_double_sweep_confirm|double_sweep_window_bars|double_sweep_only_defensive|double_sweep_block_sweep_entry|double_sweep_dtp_trigger_r|double_sweep_regime_pos_mult)"', yts_text))
input_params = set(re.findall(r'Inp(EnableMitigationEntry|MitigationEntryMaxBars|MitigationEntryOnlyRange|MitigationEntryOnlyDefensive|MitigationEntrySignalTypes|EnableDoubleSweepConfirm|DoubleSweepWindowBars|DoubleSweepOnlyDefensive|DoubleSweepBlockSweepEntry|DoubleSweepDTPTriggerR|DoubleSweepRegimePosMult)', config_text))
yts_inp = set(re.findall(r'Inp(\w+)', yts_text))

for inp in input_params:
    if f'Inp{inp}' not in yts_inp:
        issues.append(('WARN', f'yaml_to_set.py 缺少映射: Inp{inp}'))

# 3. Check strategies.yaml defaults
sy_text = read(SY)
for key in ['enable_mitigation_entry', 'mitigation_entry_max_bars', 'mitigation_entry_only_range',
            'mitigation_entry_only_defensive', 'mitigation_entry_signal_types',
            'enable_double_sweep_confirm', 'double_sweep_window_bars', 'double_sweep_only_defensive',
            'double_sweep_block_sweep_entry', 'double_sweep_dtp_trigger_r', 'double_sweep_regime_pos_mult']:
    if key not in sy_text:
        issues.append(('WARN', f'strategies.yaml 缺少默认值: {key}'))

# 4. Check initialization of EntryMonitor new fields in AddEntryMonitor
ee_text = read(EE)
for field in ['mitigation_bounce_time', 'mitigation_far_price']:
    if f'{field}' not in ee_text:
        issues.append(('INFO', f'EntryMonitor.{field} 可能未正确初始化'))

# 5. Check if g_mitigation_market_state is properly set before use
if 'g_mitigation_market_state = 0' not in ee_text:
    issues.append(('INFO', 'g_mitigation_market_state 初始值未定义'))

# 6. Check strategies.yaml vs yaml_to_set.py key alignment
for key in yaml_keys:
    if key not in sy_text:
        issues.append(('WARN', f'strategies.yaml 缺少键: {key}'))

# 7. Check compile log
print("="*60)
print("BUG AUDIT RESULTS")
print("="*60)

if not issues:
    print("\n✅ 未发现明显bug")
else:
    for level, msg in issues:
        prefix = {'CRIT': '🔴', 'WARN': '🟡', 'INFO': '🔵'}
        print(f'\n{prefix.get(level, "⚪")} [{level}] {msg}')

# 8. Check the critical state pollution: HTF zones overwriting regime state
wm5_text = Path('D:/Code/codexProject/WaiTrade2/mql5/Experts/WaiTrade2/WaiTrade_OB.mq5').read_text('utf-8', errors='replace')
# Count PassDoubleSweepConfirm call sites
ps_count = wm5_text.count('PassDoubleSweepConfirm')
print(f'\n📊 PassDoubleSweepConfirm 调用次数: {ps_count}')
# Check if HTF path calls it
htf_call = 'PassDoubleSweepConfirm(g_htf_zones' in wm5_text
if htf_call:
    print('🔴 发现: HTF路径调用PassDoubleSweepConfirm，可能覆盖主通道体制状态')
    # Show where
    for i, line in enumerate(Path('D:/Code/codexProject/WaiTrade2/mql5/Experts/WaiTrade2/WaiTrade_OB.mq5').read_text('utf-8', errors='replace').split('\n')):
        if 'PassDoubleSweepConfirm(g_htf_zones' in line:
            print(f'  位置: 行{i+1}: {line.strip()[:100]}')

# 9. Check for the yaml_to_set InpMapping name vs Config.h name
print("\n📊 Input参数存在性验证:")
for inp in ['InpDoubleSweepDTPTriggerR', 'InpDoubleSweepRegimePosMult',
            'InpEnableMitigationEntry', 'InpEnableDoubleSweepConfirm']:
    if inp in config_text:
        val_match = re.search(rf'{inp}\s*= (\S+)', config_text)
        default_val = val_match.group(1) if val_match else '?'
        in_yaml = inp in yts_text
        in_sy = inp not in yts_text  # yaml uses different keys
        print(f'  {inp} (default={default_val}) → yaml_to_set: {"YES" if in_yaml else "NO"}')

print('\nDONE')
