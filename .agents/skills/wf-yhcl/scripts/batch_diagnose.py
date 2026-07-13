#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""batch_diagnose.py: 三层诊断路由 (L1 WFYS / L2 月度 digest / L3 坏月深度诊断)

设计:
  L1 (默认): 24 月 PnL 聚合 + WFYS 评分 + 异常检测
  L2 (默认启用): 24 月逐月 digest + red flag 标识
  L3 (opt-in): 仅坏月订单级诊断 + 根因匹配 + 可证伪假说

数据流:
  24 月 .txt 汇总  -> L1  -> aggregate_months() -> WFYS
  24m .trades.csv  -> L2  -> 按 date 过滤 -> monthly digest
  24m .trades.csv  -> L3  -> 按 date 过滤坏月 -> 深度诊断
"""
import sys
import csv
import json
import argparse
import statistics
from pathlib import Path
from datetime import datetime

# 复用 L1 函数（避免 copy-paste）
sys.path.insert(0, str(Path(__file__).parent))
import wfys_l1 as L1

ROOT = L1.ROOT
RESULTS_DIR = L1.RESULTS_DIR
DIAGNOSE_DIR = RESULTS_DIR.parent / 'diagnose'


# ===== 数据加载 =====

def find_24m_trades_csv(strategy, symbol, explicit_path=None):
    """找 24m 聚合 trades.csv；Manifest 显式证据路径优先。"""
    if explicit_path:
        explicit = Path(explicit_path)
        return explicit if explicit.exists() else None
    matches = sorted(RESULTS_DIR.glob(strategy + '_*.trades.csv'))
    for m in matches:
        if symbol.lower() in m.name.lower():
            return m
    return matches[-1] if matches else None


def load_trades(csv_path):
    """读 24m trades.csv 返回 list[dict]"""
    if not csv_path or not csv_path.exists():
        return []
    with csv_path.open('r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def group_by_month(trades):
    """按 date 前缀 (YYYY-MM) 分组"""
    groups = {}
    for t in trades:
        d = (t.get('date') or '').strip()
        if not d or len(d) < 7:
            continue
        month = d[:7]
        groups.setdefault(month, []).append(t)
    return groups


# ===== L2: 月度 digest =====

EXIT_FIELDS = ('reason',)
TRADE_FIELDS_FOR_DIGEST = ('pnl_proxy', 'duration_min', 'reason', 'r', 'dir', 'bounce_ob')


def safe_float(v, default=0.0):
    try:
        return float(v) if v not in ('', None) else default
    except (ValueError, TypeError):
        return default


def safe_int(v, default=0):
    try:
        return int(float(v)) if v not in ('', None) else default
    except (ValueError, TypeError):
        return default


def month_digest(month, trades):
    """单月 digest: net/trades/WR/med-hold/top-exit/OB-score/flag"""
    if not trades:
        return None
    pnls = [safe_float(t.get('pnl_proxy')) for t in trades]
    holds = [safe_float(t.get('duration_min')) for t in trades]
    rs = [safe_float(t.get('r')) for t in trades]
    scores = [safe_float(t.get('bounce_ob')) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    wr = (len(wins) / len(pnls) * 100) if pnls else 0
    reasons = [t.get('reason', '') for t in trades if t.get('reason')]
    top_exit = ''
    if reasons:
        top_exit = max(set(reasons), key=reasons.count)
    sl_count = sum(1 for r in reasons if 'sl' in r.lower())
    sl_heavy = sl_count > len(trades) * 0.5
    flag = 'ok'
    if sum(pnls) < 0:
        flag = 'loss'
    elif sl_heavy:
        flag = 'sl-heavy'
    elif wr < 30:
        flag = 'low-wr'
    return {
        'month': month,
        'trades': len(trades),
        'net': sum(pnls),
        'wr': wr,
        'med_hold': statistics.median(holds) if holds else 0,
        'top_exit': top_exit,
        'ob_score': statistics.median(scores) if scores else 0,
        'flag': flag,
    }


def level2_monthly_digest(strategy, symbol, monthly_l1, trades_csv=None):
    """L2: 24 月逐月 digest + red flag 列表"""
    csv_path = find_24m_trades_csv(strategy, symbol, trades_csv)
    if not csv_path:
        return None, 'no 24m trades.csv found'
    trades = load_trades(csv_path)
    if not trades:
        return None, 'empty trades.csv'
    groups = group_by_month(trades)
    digests = []
    for month in sorted(groups.keys()):
        d = month_digest(month, groups[month])
        if d:
            digests.append(d)
    red_flags = [d for d in digests if d['flag'] in ('loss', 'sl-heavy', 'low-wr')]
    return {
        'csv_path': str(csv_path),
        'digests': digests,
        'red_flags': red_flags,
        'total_months': len(digests),
    }, None


def compact_l2_output(l2_data, strategy):
    """L2 stdout 输出 (~20 行)"""
    print('=== L2: ' + strategy + ' 月度 digest ===')
    print('Month     Net      Trades  WR    MedHold  TopExit  BounceOB  Flag')
    for d in l2_data['digests']:
        print('{:<9} {:>+7.1f}  {:>5}   {:>4.0f}% {:>5.1f}m  {:>8}  {:>5.2f}     {}'.format(
            d['month'], d['net'], d['trades'], d['wr'],
            d['med_hold'], d['top_exit'][:8], d['ob_score'], d['flag']))
    print()
    rf = l2_data['red_flags']
    if rf:
        print('Red Flags: {} / {} 月'.format(len(rf), l2_data['total_months']))
        for d in rf[:5]:
            print('  {} {}: net={:+.1f} WR={:.0f}% med_hold={:.1f}m top_exit={}'.format(
                d['month'], d['flag'], d['net'], d['wr'],
                d['med_hold'], d['top_exit']))
    else:
        print('Red Flags: 0 (策略月度健康)')
    return rf


# ===== L3: 坏月深度诊断 =====

HOLD_BUCKETS = [(0, 1, '<1m'), (1, 5, '1-5m'),
                (5, 30, '5-30m'), (30, 600, '>30m')]


def bucketize_hold(minutes):
    for lo, hi, label in HOLD_BUCKETS:
        if lo <= minutes < hi:
            return label
    return '>30m'


def level3_loss_diagnosis(strategy, symbol, l2_data):
    """L3: 仅坏月订单级深度诊断"""
    if not l2_data or not l2_data['red_flags']:
        return None
    csv_path = Path(l2_data['csv_path'])
    trades = load_trades(csv_path)
    groups = group_by_month(trades)
    bad_months = {d['month']: d for d in l2_data['red_flags']}
    diagnoses = {}
    for month in sorted(bad_months.keys()):
        if month not in groups:
            continue
        m_trades = groups[month]
        pnls = [safe_float(t.get('pnl_proxy')) for t in m_trades]
        holds = [safe_float(t.get('duration_min')) for t in m_trades]
        rs = [safe_float(t.get('r')) for t in m_trades]
        scores = [safe_float(t.get('bounce_ob')) for t in m_trades]
        # 出仓分布
        reasons = [t.get('reason', '') for t in m_trades if t.get('reason')]
        reason_dist = {}
        for r in reasons:
            reason_dist[r] = reason_dist.get(r, 0) + 1
        # 时长桶
        hold_dist = {}
        for h in holds:
            b = bucketize_hold(h)
            hold_dist[b] = hold_dist.get(b, 0) + 1
        # R 分布
        r_dist = {'<0.3R': 0, '0.3-1R': 0, '1-2R': 0, '>2R': 0}
        for r in rs:
            if r < 0.3:
                r_dist['<0.3R'] += 1
            elif r < 1.0:
                r_dist['0.3-1R'] += 1
            elif r < 2.0:
                r_dist['1-2R'] += 1
            else:
                r_dist['>2R'] += 1
        # OB score vs WR
        if scores:
            med_score = statistics.median(scores)
        else:
            med_score = 0
        # 方向偏差
        buy_pnls = [safe_float(t.get('pnl_proxy')) for t in m_trades
                    if t.get('dir', '').lower() == 'buy']
        sell_pnls = [safe_float(t.get('pnl_proxy')) for t in m_trades
                     if t.get('dir', '').lower() == 'sell']
        diagnoses[month] = {
            'month': month,
            'trades': len(m_trades),
            'net': sum(pnls),
            'wr': (sum(1 for p in pnls if p > 0) / len(pnls) * 100) if pnls else 0,
            'reason_dist': reason_dist,
            'hold_dist': hold_dist,
            'r_dist': r_dist,
            'med_bounce_ob': med_score,
            'buy_pnl': sum(buy_pnls),
            'sell_pnl': sum(sell_pnls),
            'med_hold': statistics.median(holds) if holds else 0,
        }
    return diagnoses


def compact_l3_output(diagnoses, strategy):
    """L3 stdout 输出 (每个坏月 5-10 行)"""
    if not diagnoses:
        print('L3: 无坏月，跳过深度诊断')
        return
    print('=== L3: ' + strategy + ' 坏月诊断 ({} 月) ==='.format(len(diagnoses)))
    for month, d in diagnoses.items():
        print()
        print('[{}] {} 笔, 净 {:+.2f}, WR {:.0f}%'.format(
            d['month'], d['trades'], d['net'], d['wr']))
        print('  出仓: {}'.format(
            ' | '.join('{}:{}'.format(k, v) for k, v in
                       sorted(d['reason_dist'].items(), key=lambda x: -x[1])[:4])))
        print('  时长: {}'.format(
            ' | '.join('{}:{}'.format(k, v) for k, v in d['hold_dist'].items())))
        print('  R倍数: {}'.format(
            ' | '.join('{}:{}'.format(k, v) for k, v in d['r_dist'].items())))
        print('  BounceOB: {:.2f} | 买 {:+.1f} 卖 {:+.1f}'.format(
            d['med_bounce_ob'], d['buy_pnl'], d['sell_pnl']))


# ===== 领域规则匹配 (P3) =====

DOMAIN_RULES = [
    {
        'id': 'sl_heavy_noise',
        'pattern': lambda d: d.get('reason_dist', {}).get('sl', 0) > d['trades'] * 0.5,
        'label': 'Tick 噪音秒杀',
        'action': '加大 InpSLBufferATR 或启用 InpBounceConfirmBars',
        'expected': 'SL 占比 50%+  预期改善 30-50%',
    },
    {
        'id': 'short_hold_loser',
        'pattern': lambda d: d.get('hold_dist', {}).get('<1m', 0) > d['trades'] * 0.4,
        'label': '微持仓高频亏损',
        'action': '加 InpBounceConfirmBars 强制 K 线确认',
        'expected': '<1m 亏损占比 40%+  预期砍半',
    },
    {
        'id': 'low_ob_quality',
        'pattern': lambda d: d.get('med_bounce_ob', 1) < 0.20,
        'label': '低 BounceOB 主导',
        'action': '提 InpMinOBStrength 阈值 (注: bounce_ob<0.20)',
        'expected': '过滤 ~30% 劣质信号',
    },
    {
        'id': 'micro_wins_only',
        'pattern': lambda d: d.get('r_dist', {}).get('<0.3R', 0) > d['trades'] * 0.5
                          and d.get('r_dist', {}).get('>2R', 0) == 0,
        'label': '盈利单全为微盈',
        'action': '修 DTP (提 InpDTPTriggerR 到 1.5+)',
        'expected': 'DTP 改善 0.3R->1.0R 级别盈利',
    },
    {
        'id': 'direction_bias',
        'pattern': lambda d: abs(d.get('buy_pnl', 0) - d.get('sell_pnl', 0)) > abs(d.get('net', 1)) * 1.5,
        'label': '单边方向系统性亏损',
        'action': '检查 H4 方向锁 / 双向 OB 评分',
        'expected': '拦截逆势单边',
    },
]


def match_domain_rules(diagnoses):
    """匹配领域规则 -> 根因 + 假说"""
    findings = []
    for month, d in diagnoses.items():
        for rule in DOMAIN_RULES:
            try:
                if rule['pattern'](d):
                    findings.append({
                        'month': month,
                        'rule_id': rule['id'],
                        'label': rule['label'],
                        'action': rule['action'],
                        'expected': rule['expected'],
                    })
            except Exception:
                pass
    return findings


def compact_findings(findings):
    """L3 末尾根因 + 可证伪假说"""
    if not findings:
        print()
        print('根因: 未匹配到内置领域规则 (策略可能健康, 或规则需扩展)')
        return
    print()
    print('=== 根因 + 可证伪假说 ===')
    by_rule = {}
    for f in findings:
        by_rule.setdefault(f['rule_id'], []).append(f)
    for rid, fs in by_rule.items():
        rule = next((r for r in DOMAIN_RULES if r['id'] == rid), None)
        if not rule:
            continue
        months = ', '.join(f['month'] for f in fs)
        print('[{}] {} ({} 月)'.format(rule['label'], len(fs), months))
        print('  行动: {}'.format(rule['action']))
        print('  预期: {}'.format(rule['expected']))


# ===== 自动升级 + 建议 (P4) =====

def l1_suggestions(l1_summary, l2_data):
    """L1 末尾输出 '建议升级' (基于 0702/0703 实战经验)"""
    print()
    print('=== 触发建议 ===')
    if l1_summary['loss_months'] >= 5:
        print('发现 {}/{} 亏损月 (>20%) -- 建议 --level=3 诊断坏月根因'.format(
            l1_summary['loss_months'], l1_summary['period_months']))
    elif l1_summary['loss_months'] >= 3:
        print('发现 {} 亏损月 -- --level=2 已默认启用, 查看 red flags'.format(
            l1_summary['loss_months']))
    else:
        print('亏损月 < 3, 策略月度表现健康, 无需 L3')
    if l2_data and len(l2_data.get('red_flags', [])) >= 3:
        print('L2 标识 {} 个 red flag 月 -- 建议 --level=3'.format(
            len(l2_data['red_flags'])))


# ===== Markdown 落盘 (P5) =====

def save_markdown(strategy, symbol, level, l1_summary, l2_data, l3_diag, findings):
    """落盘 results/diagnose/<strategy>_<level>_<date>.md"""
    DIAGNOSE_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime('%Y%m%d')
    out = DIAGNOSE_DIR / '{}_{}_L{}_{}.md'.format(strategy, symbol, level, today)
    lines = ['# {} 诊断报告 (L{}, {})\n'.format(
        strategy, level, datetime.now().strftime('%Y-%m-%d'))]
    # L1 部分
    lines.append('## WFYS 摘要\n')
    lines.append('- 24m: {}/{} 盈利, {} 亏损, {} 零'.format(
        l1_summary['profit_months'], l1_summary['period_months'],
        l1_summary['loss_months'], l1_summary['zero_months']))
    lines.append('- 总收益: ${:.2f} ({:.1f}%)'.format(
        l1_summary['total_profit'], l1_summary['return_pct']))
    lines.append('- 最终余额: ${:.2f}'.format(l1_summary['final_balance']))
    lines.append('- 笔数: {}, 中位月: ${:.2f}\n'.format(
        l1_summary['total_trades'], l1_summary['median_monthly_pnl']))
    # L2 部分
    if l2_data and level >= 2:
        lines.append('\n## 月度 digest\n')
        lines.append('| Month | Net | Trades | WR | MedHold | TopExit | BounceOB | Flag |')
        lines.append('|---|---:|---:|---:|---:|---|---:|---|')
        for d in l2_data['digests']:
            lines.append('| {} | {:+.1f} | {} | {:.0f}% | {:.1f}m | {} | {:.2f} | {} |'.format(
                d['month'], d['net'], d['trades'], d['wr'], d['med_hold'],
                d['top_exit'][:8], d['ob_score'], d['flag']))
        if l2_data['red_flags']:
            lines.append('\n### Red Flags\n')
            for d in l2_data['red_flags']:
                lines.append('- **{}** {}: net={:+.1f} WR={:.0f}% med_hold={:.1f}m'.format(
                    d['month'], d['flag'], d['net'], d['wr'], d['med_hold']))
    # L3 部分
    if l3_diag and level >= 3:
        lines.append('\n## 坏月深度诊断\n')
        for month, d in l3_diag.items():
            lines.append('\n### {}\n'.format(month))
            lines.append('- 笔数: {}, 净 {:+.2f}, WR {:.0f}%'.format(
                d['trades'], d['net'], d['wr']))
            lines.append('- 出仓: ' + ', '.join(
                '{}:{}'.format(k, v) for k, v in
                sorted(d['reason_dist'].items(), key=lambda x: -x[1])))
            lines.append('- 时长: ' + ', '.join(
                '{}:{}'.format(k, v) for k, v in d['hold_dist'].items()))
            lines.append('- BounceOB: {:.2f} | 买 {:+.1f} 卖 {:+.1f}'.format(
                d['med_bounce_ob'], d['buy_pnl'], d['sell_pnl']))
        if findings:
            lines.append('\n## 根因 + 可证伪假说\n')
            for f in findings:
                lines.append('- **{}** ({})'.format(f['label'], f['month']))
                lines.append('  - 行动: {}'.format(f['action']))
                lines.append('  - 预期: {}'.format(f['expected']))
    out.write_text('\n'.join(lines), encoding='utf-8')
    return out


# ===== 路由 =====

def main():
    parser = argparse.ArgumentParser(description='三层诊断路由 (L1/L2/L3)')
    parser.add_argument('strategy', help='策略名')
    parser.add_argument('symbol', help='品种')
    parser.add_argument('start_date', help='YYYY.MM.DD')
    parser.add_argument('end_date', help='YYYY.MM.DD')
    parser.add_argument('deposit', type=float, help='初始资金')
    parser.add_argument('--level', type=int, default=2, choices=[1, 2, 3],
                        help='诊断深度: 1=WFYS, 2=月 digest, 3=坏月诊断 (默认 2)')
    parser.add_argument('--skip-backtest', action='store_true', help='兼容参数；现在默认不回测')
    parser.add_argument('--run-monthly-backtests', action='store_true', help='显式运行旧版独立月回测（不推荐）')
    parser.add_argument('--no-md', action='store_true', help='不落盘 Markdown')
    parser.add_argument('--json', help='WFYS 结果落 JSON')
    parser.add_argument('--trades-csv', help='Manifest 指定的 720d trades.csv')
    args = parser.parse_args()

    # ===== L1: WFYS =====
    if args.run_monthly_backtests and not args.skip_backtest:
        months = L1.generate_monthly_dates(args.start_date, args.end_date)
        print('Running {} monthly backtests...'.format(len(months)))
        ok = 0
        for date_from, date_to, label in months:
            print('  [{}] {} ~ {}...'.format(label, date_from, date_to),
                  end=' ', flush=True)
            if L1.run_backtest(args.strategy, args.symbol, date_from, date_to,
                               4, 600):
                ok += 1
                print('done')
            else:
                print('failed (skip)')
        print('回测: {}/{} 成功\n'.format(ok, len(months)))

    print('Aggregating 24-month results...')
    monthly_l1 = L1.aggregate_months(args.strategy, args.deposit)
    if not monthly_l1:
        print('ERROR: no monthly results')
        sys.exit(1)
    L1.write_24m_csv(args.strategy, monthly_l1, args.deposit)
    l1_summary = L1.compute_wfys_summary(monthly_l1, args.deposit)
    L1.compact_wfys_output(l1_summary, args.strategy)

    # L1 -> L2 自动升级建议
    l1_suggestions(l1_summary, None)

    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(l1_summary, f, indent=2, ensure_ascii=False)
        print('JSON: {}'.format(args.json))

    # ===== L2: 月度 digest =====
    l2_data = None
    l3_diag = None
    findings = None
    if args.level >= 2:
        print('\nL2: 月度 digest ...')
        l2_data, err = level2_monthly_digest(args.strategy, args.symbol, monthly_l1, args.trades_csv)
        if err:
            print('  WARN: {}'.format(err))
        else:
            compact_l2_output(l2_data, args.strategy)

    # ===== L3: 坏月深度诊断 =====
    if args.level >= 3 and l2_data and l2_data['red_flags']:
        print('\nL3: 坏月深度诊断 ...')
        l3_diag = level3_loss_diagnosis(args.strategy, args.symbol, l2_data)
        compact_l3_output(l3_diag, args.strategy)
        findings = match_domain_rules(l3_diag)
        compact_findings(findings)
    elif args.level >= 3:
        print('\nL3: 无 red flag, 跳过')

    # ===== Markdown 落盘 =====
    if not args.no_md:
        md = save_markdown(args.strategy, args.symbol, args.level,
                           l1_summary, l2_data, l3_diag, findings)
        print('\nMarkdown: {}'.format(md))


if __name__ == '__main__':
    main()
