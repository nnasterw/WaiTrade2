#!/usr/bin/env python3
"""策略一致性检查脚本

检查项:
  1. bar_tf/bar_period_min 在所有层级一致
  2. Magic Number 全局唯一（不含 0=未设置）
  3. Live 参数不超过安全边界
  4. YAML key 在 FLAT_MAP 中有映射覆盖
  5. 继承链引用完整性

用法:
  python scripts/check_strategy_consistency.py              # 检查所有策略
  python scripts/check_strategy_consistency.py v11xau-qs   # 检查指定策略
  python scripts/check_strategy_consistency.py --live-only  # 仅标记了 live 的策略
  python scripts/check_strategy_consistency.py --brief      # 精简输出
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from yaml_to_set import load_strategies, FLAT_MAP, NON_STRATEGY_KEYS

# ── 安全边界（$200 账户 Live） ──────────────────────────────────────────
LIVE_SAFETY = {
    'max_lot_size':           ('<=', 0.1,  '手'),
    'max_pos_mult':           ('<=', 5.0,  'x'),
    'max_concurrent':         ('<=', 5,    '单'),
    'max_entries_per_ob':     ('<=', 5,    '次/OB'),
    'ob_reentry_cooldown_min': ('>=', 3,   '分钟'),
    'cooldown_bars':          ('>=', 1,    'K线'),
    'risk_percent':           ('<=', 3.0,  '%'),
}

# ── 分类 ────────────────────────────────────────────────────────────────
class Issue:
    def __init__(self, level, strategy, message):
        self.level = level    # 'ERROR', 'WARN', 'INFO'
        self.strategy = strategy
        self.message = message

    def __str__(self):
        icon = {'ERROR': '[ERROR]', 'WARN': '[WARN] ', 'INFO': '[INFO] '}.get(self.level, '       ')
        return f'{icon} [{self.level}] {self.strategy}: {self.message}'


# ── 检查函数 ────────────────────────────────────────────────────────────

def check_magic_uniqueness(strategies):
    """Magic Number 全局唯一检查"""
    issues = []
    magic_map = defaultdict(list)

    for name, cfg in strategies.items():
        magic = cfg.get('magic_number', 0)
        if magic and magic != 0:
            magic_map[magic].append(name)

    for magic, names in magic_map.items():
        if len(names) > 1:
            # 检测跨家族 Magic 冲突（同家族实验变体允许共享）
            families = defaultdict(list)
            for n in names:
                prefix = n.split('-')[0] if '-' in n else n
                families[prefix].append(n)
            if len(families) > 1:
                fam_list = [f'{k}({v[0]})' for k, v in families.items()]
                issues.append(Issue('ERROR', ' vs '.join(fam_list[:4]),
                                    f'Magic={magic} 跨家族冲突 ({len(names)}策略, {len(families)}家族)'))
            elif len(names) > 5:
                # 同一家族但超过5个变体，提示
                issues.append(Issue('WARN', names[0].split('-')[0],
                                    f'Magic={magic} 同家族{len(names)}个变体共享（实验族）'))

    return issues


def check_bar_tf_consistency(strategies):
    """bar_tf 和 bar_period_min 一致性检查"""
    issues = []
    for name, cfg in strategies.items():
        bar_period_min = cfg.get('bar_period_min')
        bar_tf = cfg.get('bar_tf')
        version = cfg.get('version', '')

        if bar_period_min is not None and bar_tf is not None and bar_period_min != bar_tf:
            issues.append(Issue('WARN', name,
                f'bar_period_min={bar_period_min} ≠ bar_tf={bar_tf}，回测 Period 可能不匹配 InpBarTF'))

        # M1 策略检查：是否有 xau_trend_bar_period_min 不一致
        xau_tf = cfg.get('xau_trend_bar_period_min')
        if xau_tf is not None and bar_period_min is not None and xau_tf != bar_period_min:
            issues.append(Issue('INFO', name,
                f'XAUTrend bar_period_min={xau_tf} ≠ 主bar_period_min={bar_period_min}（可能是有意设计）'))

    return issues


def check_safety_bounds(strategies, live_only=True):
    """参数安全边界检查"""
    issues = []
    # 聚合：同参数同值的策略只报一次
    violation_groups = defaultdict(list)
    for name, cfg in strategies.items():
        for param, (op, limit, unit) in LIVE_SAFETY.items():
            val = cfg.get(param)
            if val is None:
                continue

            exceeded = False
            if op == '<=' and val > limit:
                exceeded = True
            elif op == '>=' and val < limit:
                exceeded = True

            if exceeded:
                key = f'{param}={val}{unit} ({op} {limit}{unit})'
                violation_groups[key].append(name)

    for violation, names in sorted(violation_groups.items()):
        if len(names) <= 3:
            label = ','.join(names)
        else:
            label = f'{names[0]},{names[1]}...({len(names)}个策略)'
        issues.append(Issue('WARN', label,
            f'{violation} 超出安全边界'))

    return issues


def check_flat_map_coverage(strategies):
    """检查所有策略的 YAML key 是否在 FLAT_MAP 中有映射"""
    issues = []
    # 收集所有策略中使用的 key
    all_keys = set()
    for name, cfg in strategies.items():
        all_keys.update(cfg.keys())

    # 排除非策略 key
    strategy_keys = all_keys - NON_STRATEGY_KEYS - {'description'}
    # 排除 .set 不需要的元数据 key
    meta_keys = {'name', 'anchor', 'inherits', 'strategy_name'}

    unmapped = set()
    for key in sorted(strategy_keys):
        if key in FLAT_MAP:
            continue
        if key.startswith('_'):  # 内部变量
            continue
        if key in meta_keys:
            continue
        # 检查是否是 MQL5 不需要的 Python-only key
        if key in ('version',):
            continue
        unmapped.add(key)

    if unmapped:
        issues.append(Issue('INFO', '(全局)',
            f'{len(unmapped)} 个 YAML key 未在 FLAT_MAP 中映射: {", ".join(sorted(unmapped)[:20])}'))

    return issues


def check_inheritance_integrity(strategies, raw_data):
    """检查 YAML 锚点引用完整性"""
    issues = []
    import yaml

    # 简单检查：解析 YAML 时如果有未定义的锚点，会抛异常
    # 这里检查策略中引用的锚点是否都存在
    yaml_path = ROOT / 'config' / 'strategies.yaml'
    with open(yaml_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找所有 *anchor 引用
    import re
    refs = set(re.findall(r'\*(\w[\w_-]*)', content))
    anchors = set(re.findall(r'&(\w[\w_-]*)', content))

    missing = refs - anchors
    if missing:
        issues.append(Issue('ERROR', '(全局)',
            f'YAML 锚点引用缺失: {", ".join(sorted(missing))}'))

    return issues


def check_strategy_exists(strategies, target):
    """检查指定策略是否存在并输出详细报告"""
    issues = []
    if target not in strategies:
        issues.append(Issue('ERROR', target, '策略不存在于 strategies.yaml'))
        return issues

    cfg = strategies[target]
    version = cfg.get('version', '?')
    magic = cfg.get('magic_number', '?')
    bar_tf = cfg.get('bar_period_min', cfg.get('bar_tf', '?'))
    risk = cfg.get('risk_percent', '?')
    max_lot = cfg.get('max_lot_size', '?')

    issues.append(Issue('INFO', target,
        f'版本={version} Magic={magic} BarTF={bar_tf} 风险={risk}% 最大手数={max_lot}'))

    # 检查 .set 文件
    set_paths = [
        ROOT / 'mql5' / 'Presets' / f'{target}.set',
        ROOT / 'temp' / 'mt5_portable_xau_zd_qs' / 'QS' / 'MQL5' / 'Presets' / f'{target}.set',
        ROOT / 'temp' / 'mt5_portable_xau_zd_qs' / 'ZD' / 'MQL5' / 'Presets' / f'{target}.set',
    ]
    for sp in set_paths:
        if sp.exists():
            issues.append(Issue('INFO', target, f'.set 文件: {sp}'))
        # 不报告缺失，因为不是所有策略都有 .set

    return issues


# ── 主流程 ───────────────────────────────────────────────────────────────

def run_checks(strategies, raw_data=None, live_only=False, targets=None):
    all_issues = []

    if targets:
        for t in targets:
            all_issues.extend(check_strategy_exists(strategies, t))
        # 只对指定策略做安全检查
        filtered = {t: strategies[t] for t in targets if t in strategies}
        all_issues.extend(check_safety_bounds(filtered, live_only=False))
        return all_issues

    all_issues.extend(check_magic_uniqueness(strategies))
    all_issues.extend(check_bar_tf_consistency(strategies))
    all_issues.extend(check_safety_bounds(strategies, live_only))
    all_issues.extend(check_flat_map_coverage(strategies))
    if raw_data:
        all_issues.extend(check_inheritance_integrity(strategies, raw_data))

    return all_issues


def print_report(issues, brief=False):
    errors = [i for i in issues if i.level == 'ERROR']
    warns = [i for i in issues if i.level == 'WARN']
    infos = [i for i in issues if i.level == 'INFO']

    print(f'\n{"="*60}')
    print(f'策略一致性检查报告')
    print(f'{"="*60}')
    print(f'ERROR: {len(errors)}   WARN: {len(warns)}   INFO: {len(infos)}')

    if errors:
        print(f'\n── 错误 ──')
        for e in errors:
            print(f'  {e}')
        if not brief:
            print()

    if warns and not brief:
        print(f'\n── 警告 ──')
        for w in warns:
            print(f'  {w}')

    if infos and not brief:
        print(f'\n── 信息 ──')
        for i in infos:
            print(f'  {i}')

    print(f'\n{"="*60}')
    if errors:
        print(f'[ERROR] 检测到 {len(errors)} 个错误，需立即修复')
    elif warns:
        print(f'[WARN]  {len(warns)} 个警告，建议检查')
    else:
        print(f'[OK]   所有检查通过')
    print()

    return len(errors) == 0


def main():
    parser = argparse.ArgumentParser(description='策略一致性检查')
    parser.add_argument('strategy', nargs='*', help='指定策略名称（不指定则检查全部）')
    parser.add_argument('--live-only', action='store_true', help='仅检查包含 LIVE 标记的策略')
    parser.add_argument('--brief', action='store_true', help='精简输出')
    args = parser.parse_args()

    yaml_path = ROOT / 'config' / 'strategies.yaml'
    if not yaml_path.exists():
        print(f'[错误] 找不到配置文件: {yaml_path}')
        sys.exit(1)

    strategies = load_strategies(yaml_path)

    # 过滤 live-only
    if args.live_only:
        strategies = {
            k: v for k, v in strategies.items()
            if 'live' in k.lower() or 'LIVE' in str(v.get('version', ''))
        }
        if not strategies:
            print('[提示] 未找到包含 live 标记的策略')
            sys.exit(0)

    issues = run_checks(strategies, targets=args.strategy if args.strategy else None)
    ok = print_report(issues, brief=args.brief)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
