#!/usr/bin/env python3
"""WFYS 统一验收评分脚本."""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path
from statistics import median, pstdev
from typing import Dict, Iterable, List, Optional, Tuple

from mt5_common import parse_backtest_report_content


ROOT = Path(__file__).resolve().parent.parent


SPECS = {
    'default': {
        'profit_return_24m_great': 20.0,
        'profit_return_720d_great': 10.0,
    },
    'xau': {
        'profit_return_24m_great': 150.0,
        'profit_return_720d_great': 120.0,
    },
    'btc': {
        'profit_return_24m_great': 12.0,
        'profit_return_720d_great': 10.0,
    },
}


HARD_GATES = {
    'profitable_months_min': 22,  # v2.0: 21->22
    'loss_months_max': 2,  # v2.0: 3->2
    'big_loss_months_max': 0,
    'big_loss_monthly_dd_pct': 0.20,
    'max_loss_vs_initial_capital': 1.0,
    'median_monthly_return_min': 0.03,
    'strong_month_return_min': 0.25,
    'trend_month_return_min': 0.55,
    'strong_month_count_min': 3,
    'trend_month_count_min': 1,
    'top3_concentration_max': 0.60,
    'top5_concentration_max': 0.75,
    'max_drawdown_pct_max': 0.25,
    'recovery_factor_min': 3.0,
    'profit_factor_min': 1.75,
    'sharpe_min': 1.5,
    'sortino_min': 2.0,
    'calmar_min': 1.2,
    'avg_win_loss_min': 1.35,
    'big_win_ratio_min': 0.20,
    'micro_win_ratio_max': 0.55,
    # WFYS v2.0: 3 new 720d hard gates
    'weekly_trades_min': 2.0,    # v2.0: week avg >= 2 trades
    'win_rate_min': 0.35,           # v2.0: win rate >= 35%
    'avg_win_loss_v2_min': 3.0,    # v2.0: avg_W/|avg_L| >= 3.0
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='WFYS 统一验收评分')
    parser.add_argument('--monthly-csv', required=True, help='720d 拆分 24 月 CSV (trades.csv 按 close_time 归类 PnL, v1.0 标准; v2.0 24独立月回测已回退)')
    parser.add_argument('--continuous-report', required=True, help='720d 聚合 txt 报告')
    parser.add_argument('--trades-csv', required=True, help='720d 明细成交 CSV，优先使用 backtest_digest 导出的 .trades.csv')
    parser.add_argument('--strategy-prefix', help='对比 CSV 时使用的策略前缀，例如 v12xau1')
    parser.add_argument('--spec', default='default', choices=sorted(SPECS.keys()), help='WFYS-Spec')
    parser.add_argument('--deposit', type=float, help='覆盖初始资金；默认从报告或 24月 CSV 推断')
    parser.add_argument('--json-out', help='写出 JSON 结果')
    return parser.parse_args()


def _parse_dt(text: str) -> Optional[datetime]:
    if not text:
        return None
    text = text.strip()
    for fmt in (
        '%Y.%m.%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y.%m.%d',
        '%Y-%m-%d',
        '%Y-%m',
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _month_key(dt: datetime) -> str:
    return dt.strftime('%Y-%m')


def _month_iter(date_from: datetime, date_to: datetime) -> Iterable[str]:
    year = date_from.year
    month = date_from.month
    while (year, month) <= (date_to.year, date_to.month):
        yield '%04d-%02d' % (year, month)
        month += 1
        if month > 12:
            month = 1
            year += 1


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(',', '')
    try:
        return float(text)
    except ValueError:
        return None


def _safe_ratio(num: float, den: float) -> Optional[float]:
    if den is None or abs(den) < 1e-12:
        return None
    return num / den


def _linear_score(value: Optional[float], low: float, high: float, points: float) -> float:
    if value is None:
        return 0.0
    if high <= low:
        return float(points if value >= high else 0.0)
    clipped = min(max(value, low), high)
    return float(points) * (clipped - low) / (high - low)


def _reverse_linear_score(value: Optional[float], high: float, low: float, points: float) -> float:
    if value is None:
        return 0.0
    if high <= low:
        return float(points if value <= low else 0.0)
    clipped = min(max(value, low), high)
    return float(points) * (high - clipped) / (high - low)


def _weekly_trade_score(value):
    """周单数阶梯式评分 (v2.2 三档).

    < 2.0  -> 0 分 (不达硬门槛)
    2.0-3.0 -> 1 分 (及格)
    3.0-4.0 -> 2 分 (良好)
    >= 4.0 -> 3 分 (优秀)

    与硬门槛 weekly_trades_min=2.0 配套: 不达 2.0 直接淘汰, 但阶梯式评分
    让 2-3 (及格) / 3-4 (良好) / >=4 (优秀) 拉开差距.
    """
    if value is None:
        return 0.0
    if value >= 4.0:
        return 3.0
    if value >= 3.0:
        return 2.0
    if value >= 2.0:
        return 1.0
    return 0.0


def _fmt_pct(value: Optional[float], digits: int = 1) -> str:
    if value is None:
        return 'N/A'
    return ('%.' + str(digits) + 'f%%') % (value * 100.0)


def _fmt_num(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return 'N/A'
    return ('%.' + str(digits) + 'f') % value


def load_monthly_rows(path: Path, strategy_prefix: Optional[str]) -> List[Dict[str, object]]:
    rows = []
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        is_compare = 'type' in fieldnames and 'period' in fieldnames

        if is_compare:
            if not strategy_prefix:
                raise ValueError('对比 CSV 必须提供 --strategy-prefix')
            for row in reader:
                if row.get('type') != 'month':
                    continue
                rows.append({
                    'month': row.get('period'),
                    'profit': _to_float(row.get('%s_profit' % strategy_prefix)),
                    'balance': _to_float(row.get('%s_balance' % strategy_prefix)),
                    'trades': _to_float(row.get('%s_trades' % strategy_prefix)),
                    'wr': _to_float(row.get('%s_wr' % strategy_prefix)),
                    'pf': _to_float(row.get('%s_pf' % strategy_prefix)),
                })
        else:
            for row in reader:
                month = row.get('month') or row.get('period')
                if not month:
                    continue
                rows.append({
                    'month': month,
                    'profit': _to_float(row.get('net') or row.get('profit')),
                    'balance': _to_float(row.get('balance')),
                    'trades': _to_float(row.get('trades')),
                    'wr': _to_float(row.get('wr')),
                    'pf': _to_float(row.get('pf')),
                })

    rows = [r for r in rows if r['month']]
    rows.sort(key=lambda item: item['month'])
    if len(rows) != 24:
        raise ValueError('720d 拆分 24 月 CSV (trades.csv 按 close_time 归类 PnL, v1.0 标准; v2.0 24独立月回测已回退) 需要正好 24 条月度记录，当前=%s' % len(rows))
    return rows


def infer_monthly_deposit(rows: List[Dict[str, object]]) -> Optional[float]:
    for row in rows:
        profit = row.get('profit')
        balance = row.get('balance')
        if profit is not None and balance is not None:
            return float(balance) - float(profit)
    return None


def load_report_meta(path: Path) -> Dict[str, object]:
    content = path.read_text(encoding='utf-8')
    parsed = parse_backtest_report_content(content)
    if not parsed:
        raise ValueError('无法解析 720d 聚合报告: %s' % path)
    return parsed


def load_trades(path: Path) -> List[Dict[str, object]]:
    trades = []
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pnl = _to_float(row.get('pnl_proxy') or row.get('pnl'))
            if pnl is None:
                continue
            exit_time = row.get('close_time') or row.get('exit_time') or row.get('time')
            exit_dt = _parse_dt(exit_time)
            if exit_dt is None:
                continue
            trades.append({
                'exit_dt': exit_dt,
                'pnl': pnl,
                'r': _to_float(row.get('r')),
            })
    trades.sort(key=lambda item: item['exit_dt'])
    if not trades:
        raise ValueError('成交 CSV 无有效交易: %s' % path)
    return trades


def compute_monthly_metrics(rows: List[Dict[str, object]], deposit: float) -> Dict[str, object]:
    returns = []
    profits = []
    positive_profits = []
    profitable_months = 0
    loss_months = 0
    big_loss_months = 0
    strong_months = 0
    trend_months = 0
    total_trades = 0
    max_loss_vs_initial = 0.0

    # 动态权益口径 (fix 2026-07-04): spec 定义 月亏损/月初余额 / 月盈利>25% 都以月初余额为分母
    # 原代码用初始 deposit 作分母, 对 $200 起步但已盈利到 $8K 的账户
    # 会把所有亏损月误判为大亏月 (单月亏 -$160 / $200 = -80% > 20%)
    # 修复: 用月初余额 (= 上月结束余额) 重新计算 month_return
    start_balance = deposit
    for row in rows:
        profit = float(row['profit'] or 0.0)
        end_balance = float(row['balance'] or 0.0)
        if start_balance > 0:
            month_return = profit / start_balance
        elif deposit > 0:
            month_return = profit / deposit
        else:
            month_return = 0.0
        # 单月亏损绝对保护仍按 spec 用初始资金 (防止前期暴赚掩盖后期失控)
        if deposit > 0:
            month_return_vs_initial = profit / deposit
        else:
            month_return_vs_initial = 0.0
        returns.append(month_return)
        profits.append(profit)
        total_trades += int(row.get('trades') or 0)
        if profit > 0:
            profitable_months += 1
            positive_profits.append(profit)
        elif profit < 0:
            loss_months += 1
            if abs(month_return) > HARD_GATES['big_loss_monthly_dd_pct']:
                big_loss_months += 1
            max_loss_vs_initial = max(max_loss_vs_initial, abs(month_return_vs_initial))
        if month_return > HARD_GATES['strong_month_return_min']:
            strong_months += 1
        if month_return > HARD_GATES['trend_month_return_min']:
            trend_months += 1
        # 月末余额推到下月作为月初余额
        if end_balance > 0:
            start_balance = end_balance
        elif profit != 0:
            start_balance = start_balance + profit

    total_profit = sum(profits)
    total_return = total_profit / deposit if deposit else 0.0
    sorted_positive = sorted(positive_profits, reverse=True)
    top3_ratio = _safe_ratio(sum(sorted_positive[:3]), total_profit)
    top5_ratio = _safe_ratio(sum(sorted_positive[:5]), total_profit)

    return {
        'month_count': len(rows),
        'total_profit': total_profit,
        'total_return': total_return,
        'profitable_months': profitable_months,
        'loss_months': loss_months,
        'big_loss_months': big_loss_months,
        'strong_months': strong_months,
        'trend_months': trend_months,
        'median_monthly_return': median(returns),
        'top3_concentration': top3_ratio,
        'top5_concentration': top5_ratio,
        'total_trades': total_trades,
        'max_loss_vs_initial': max_loss_vs_initial,
    }


def compute_continuous_metrics(
    trades: List[Dict[str, object]],
    deposit: float,
    date_from: datetime,
    date_to: datetime,
    days: int,
) -> Dict[str, object]:
    balance = deposit
    peak = deposit
    max_dd_abs = 0.0
    max_dd_pct = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    win_pnls = []
    loss_pnls = []
    monthly_pnls = dict((month_key, 0.0) for month_key in _month_iter(date_from, date_to))

    for trade in trades:
        pnl = float(trade['pnl'])
        if pnl > 0:
            gross_profit += pnl
            win_pnls.append(pnl)
        elif pnl < 0:
            gross_loss += abs(pnl)
            loss_pnls.append(abs(pnl))
        balance += pnl
        if balance > peak:
            peak = balance
        dd_abs = peak - balance
        dd_pct = _safe_ratio(dd_abs, peak) or 0.0
        if dd_abs > max_dd_abs:
            max_dd_abs = dd_abs
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
        monthly_pnls[_month_key(trade['exit_dt'])] = monthly_pnls.get(_month_key(trade['exit_dt']), 0.0) + pnl

    final_balance = balance
    net_profit = final_balance - deposit
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    recovery = net_profit / max_dd_abs if max_dd_abs > 0 else float('inf')
    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else None
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else None
    avg_win_loss = _safe_ratio(avg_win or 0.0, avg_loss or 0.0)

    month_returns = []
    start_balance = deposit
    for month_key in _month_iter(date_from, date_to):
        pnl = monthly_pnls.get(month_key, 0.0)
        if start_balance > 0:
            month_returns.append(pnl / start_balance)
        else:
            month_returns.append(0.0)
        start_balance += pnl

    sharpe = compute_sharpe(month_returns)
    sortino = compute_sortino(month_returns)
    calmar = compute_calmar(deposit, final_balance, days, max_dd_pct)

    return {
        'final_balance': final_balance,
        'net_profit': net_profit,
        'net_return': net_profit / deposit if deposit else 0.0,
        'profit_factor': profit_factor,
        'max_drawdown_abs': max_dd_abs,
        'max_drawdown_pct': max_dd_pct,
        'recovery_factor': recovery,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'avg_win_loss': avg_win_loss,
        'monthly_returns': month_returns,
        'sharpe': sharpe,
        'sortino': sortino,
        'calmar': calmar,
        'trade_count': len(trades),
    }


def compute_sharpe(returns: List[float]) -> Optional[float]:
    if not returns:
        return None
    mean_ret = sum(returns) / len(returns)
    vol = pstdev(returns) if len(returns) > 1 else 0.0
    if vol <= 1e-12:
        return None if mean_ret <= 0 else float('inf')
    return mean_ret / vol * math.sqrt(12.0)


def compute_sortino(returns: List[float]) -> Optional[float]:
    if not returns:
        return None
    mean_ret = sum(returns) / len(returns)
    downside = [min(r, 0.0) for r in returns]
    downside_sq = sum(r * r for r in downside) / len(downside)
    downside_dev = math.sqrt(downside_sq)
    if downside_dev <= 1e-12:
        return None if mean_ret <= 0 else float('inf')
    return mean_ret / downside_dev * math.sqrt(12.0)


def compute_calmar(deposit: float, final_balance: float, days: int, max_dd_pct: float) -> Optional[float]:
    if deposit <= 0 or final_balance <= 0 or days <= 0 or max_dd_pct <= 1e-12:
        return None
    annual_return = (final_balance / deposit) ** (365.0 / float(days)) - 1.0
    return annual_return / max_dd_pct


def compute_r_metrics(trades: List[Dict[str, object]]) -> Dict[str, object]:
    valid_r = [float(t['r']) for t in trades if t.get('r') is not None]
    if not valid_r:
        return {
            'has_r_metrics': False,
            'big_win_ratio': None,
            'micro_win_ratio': None,
        }

    win_rs = [r for r in valid_r if r > 0]
    if not win_rs:
        return {
            'has_r_metrics': True,
            'big_win_ratio': 0.0,
            'micro_win_ratio': 0.0,
        }

    big_wins = len([r for r in win_rs if r > 3.0])
    micro_wins = len([r for r in win_rs if r < 0.5])
    return {
        'has_r_metrics': True,
        'big_win_ratio': big_wins / float(len(win_rs)),
        'micro_win_ratio': micro_wins / float(len(win_rs)),
        # v2.0: 720d hard gates support
        'win_count': len(win_rs),
        'loss_count': len(valid_r) - len(win_rs),
        'total_count': len(valid_r),
        'win_rate': len(win_rs) / float(len(valid_r)) if valid_r else 0.0,
    }


def evaluate_hard_gates(metrics: Dict[str, object]) -> Tuple[Dict[str, bool], List[str]]:
    month = metrics['monthly']
    cont = metrics['continuous']
    r_metrics = metrics['r_metrics']

    gates = {
        '24月盈利月数': month['profitable_months'] >= HARD_GATES['profitable_months_min'],
        '亏损月数量': month['loss_months'] <= HARD_GATES['loss_months_max'],
        '大亏月': month['big_loss_months'] <= HARD_GATES['big_loss_months_max'],
        '单月亏损绝对保护': month['max_loss_vs_initial'] <= HARD_GATES['max_loss_vs_initial_capital'],
        '月收益中位数': month['median_monthly_return'] >= HARD_GATES['median_monthly_return_min'],
        '强利润月数量': month['strong_months'] >= HARD_GATES['strong_month_count_min'],
        '大趋势月数量': month['trend_months'] >= HARD_GATES['trend_month_count_min'],
        'Top3集中度': (month['top3_concentration'] is not None and month['top3_concentration'] <= HARD_GATES['top3_concentration_max']),
        'Top5集中度': (month['top5_concentration'] is not None and month['top5_concentration'] <= HARD_GATES['top5_concentration_max']),
        '720d最大回撤': cont['max_drawdown_pct'] <= HARD_GATES['max_drawdown_pct_max'],
        '720dRecovery': cont['recovery_factor'] >= HARD_GATES['recovery_factor_min'],
        '720dPF': cont['profit_factor'] >= HARD_GATES['profit_factor_min'],
        'Sharpe': cont['sharpe'] is not None and cont['sharpe'] >= HARD_GATES['sharpe_min'],
        'Sortino': cont['sortino'] is not None and cont['sortino'] >= HARD_GATES['sortino_min'],
        'Calmar': cont['calmar'] is not None and cont['calmar'] >= HARD_GATES['calmar_min'],
        'avg_W/|avg_L|': cont['avg_win_loss'] is not None and cont['avg_win_loss'] >= HARD_GATES['avg_win_loss_min'],
        '>3R大赢单占比': r_metrics['big_win_ratio'] is not None and r_metrics['big_win_ratio'] >= HARD_GATES['big_win_ratio_min'],
        '<0.5R微利单占比': r_metrics['micro_win_ratio'] is not None and r_metrics['micro_win_ratio'] <= HARD_GATES['micro_win_ratio_max'],
        # WFYS v2.0: 3 new 720d gates (from continuous_report)
        '720d周均单数': cont['trade_count'] is not None and (cont['trade_count'] / 103.0) >= HARD_GATES['weekly_trades_min'],
        '720d胜率': r_metrics.get('win_rate') is not None and r_metrics['win_rate'] >= HARD_GATES['win_rate_min'],
        '720d盈亏比': cont.get('avg_win_loss') is not None and cont['avg_win_loss'] >= HARD_GATES['avg_win_loss_v2_min'],
    }
    failures = [name for name, ok in gates.items() if not ok]
    if not r_metrics['has_r_metrics']:
        failures.append('缺少R倍数列，无法完成R结构验收')
    return gates, failures


def score_metrics(metrics: Dict[str, object], spec_name: str) -> Dict[str, object]:
    spec = SPECS[spec_name]
    month = metrics['monthly']
    cont = metrics['continuous']
    r_metrics = metrics['r_metrics']

    stability_parts = {
        '24月盈利月数': _linear_score(month['profitable_months'], 18.0, 24.0, 10.0),
        '亏损月控制': max(0.0, 8.0 - 2.0 * month['loss_months']),
        '利润集中度': (
            _reverse_linear_score(month['top3_concentration'], 1.0, 0.50, 6.0) +
            _reverse_linear_score(month['top5_concentration'], 1.0, 0.65, 6.0)
        ),
    }

    profit_parts = {
        '24月总收益能力': _linear_score(month['total_return'], 0.0, spec['profit_return_24m_great'], 12.0),
        '720d净利能力': _linear_score(cont['net_return'], 0.0, spec['profit_return_720d_great'], 10.0),
        '强利润月/大趋势月': min(
            8.0,
            _linear_score(month['strong_months'], 0.0, 5.0, 5.0) +
            _linear_score(month['trend_months'], 0.0, 2.0, 3.0)
        ),
    }

    risk_ratio_score = 0.0
    risk_ratio_score += _linear_score(cont['sharpe'], 0.0, 3.0, 1.0)
    risk_ratio_score += _linear_score(cont['sortino'], 0.0, 4.0, 1.0)
    risk_ratio_score += _linear_score(cont['calmar'], 0.0, 3.0, 1.0)
    risk_parts = {
        '720d回撤': _reverse_linear_score(cont['max_drawdown_pct'], 0.40, 0.18, 8.0),
        'Recovery Factor': _linear_score(cont['recovery_factor'], 0.0, 5.0, 7.0),
        'Profit Factor': _linear_score(cont['profit_factor'], 0.0, 2.10, 5.0),
        # v2.2: 周单数改为阶梯式分级 (及格/良好/优秀)
        '周单数分级': _weekly_trade_score(cont['trade_count'] / 103.0 if cont['trade_count'] else 0.0),
        '720d胜率': _linear_score(r_metrics.get('win_rate', 0.0), 0.20, 0.50, 1.0),  # v2.2: 2->1 分 (腾给周单数分级)
        '720d盈亏比': _linear_score(cont['avg_win_loss'], 0.0, 6.0, 1.0),
    }

    trend_parts = {
        'avg_W/|avg_L|': _linear_score(cont['avg_win_loss'], 0.0, 1.60, 5.0),
        '>3R大赢单占比': _linear_score(r_metrics['big_win_ratio'], 0.0, 0.50, 6.0),
        '<0.5R微利单占比': _reverse_linear_score(r_metrics['micro_win_ratio'], 0.70, 0.40, 4.0),
    }

    module_scores = {
        '稳定性': sum(stability_parts.values()),
        '利润能力': sum(profit_parts.values()),
        '风险质量': sum(risk_parts.values()),
        '趋势利润结构': sum(trend_parts.values()),
    }

    drags = []
    for group_name, parts in (
        ('稳定性', stability_parts),
        ('利润能力', profit_parts),
        ('风险质量', risk_parts),
        ('趋势利润结构', trend_parts),
    ):
        for part_name, part_score in parts.items():
            if group_name == '稳定性':
                max_score = {'24月盈利月数': 10.0, '亏损月控制': 8.0, '利润集中度': 12.0}[part_name]
            elif group_name == '利润能力':
                max_score = {'24月总收益能力': 12.0, '720d净利能力': 10.0, '强利润月/大趋势月': 8.0}[part_name]
            elif group_name == '风险质量':
                max_score = {'720d回撤': 8.0, 'Recovery Factor': 7.0, 'Profit Factor': 5.0, '周单数分级': 3.0, '720d胜率': 1.0, '720d盈亏比': 1.0}[part_name]
            else:
                max_score = {'avg_W/|avg_L|': 5.0, '>3R大赢单占比': 6.0, '<0.5R微利单占比': 4.0}[part_name]
            drags.append({
                'name': '%s/%s' % (group_name, part_name),
                'loss': max_score - part_score,
            })

    drags.sort(key=lambda item: item['loss'], reverse=True)

    return {
        'modules': module_scores,
        'total_score': sum(module_scores.values()),
        'top_drags': [item['name'] for item in drags[:3]],
    }


def classify_result(hard_failures: List[str], total_score: float) -> str:
    if hard_failures:
        return '淘汰'
    if total_score < 80.0:
        return '继续研究'
    if total_score < 85.0:
        return '观察级候选'
    if total_score < 90.0:
        return '研究版Live候选'
    return '优先部署级候选'


def build_result(
    monthly_rows: List[Dict[str, object]],
    report_meta: Dict[str, object],
    trades: List[Dict[str, object]],
    deposit: float,
    spec_name: str,
) -> Dict[str, object]:
    date_from = datetime.strptime(report_meta['date_from'], '%Y.%m.%d')
    date_to = datetime.strptime(report_meta['date_to'], '%Y.%m.%d')
    days = int(report_meta['days'])

    metrics = {
        'monthly': compute_monthly_metrics(monthly_rows, deposit),
        'continuous': compute_continuous_metrics(trades, deposit, date_from, date_to, days),
        'r_metrics': compute_r_metrics(trades),
    }
    hard_gates, hard_failures = evaluate_hard_gates(metrics)
    score = score_metrics(metrics, spec_name)
    grade = classify_result(hard_failures, score['total_score'])

    return {
        'spec': spec_name,
        'deposit': deposit,
        'period': {
            'date_from': report_meta['date_from'],
            'date_to': report_meta['date_to'],
            'days': days,
        },
        'metrics': metrics,
        'hard_gates': hard_gates,
        'hard_failures': hard_failures,
        'score': score,
        'grade': grade,
    }


def render_result(result: Dict[str, object]) -> str:
    metrics = result['metrics']
    month = metrics['monthly']
    cont = metrics['continuous']
    r_metrics = metrics['r_metrics']
    lines = []

    lines.append('WFYS 硬门槛')
    hard_names = [
        '24月盈利月数', '亏损月数量', '大亏月', '单月亏损绝对保护', '月收益中位数',
        '强利润月数量', '大趋势月数量', 'Top3集中度', 'Top5集中度',
        '720d最大回撤', '720dRecovery', '720dPF', 'Sharpe', 'Sortino', 'Calmar',
        'avg_W/|avg_L|', '>3R大赢单占比', '<0.5R微利单占比',
    ]
    for name in hard_names:
        ok = result['hard_gates'].get(name, False)
        lines.append('- %s: %s' % (name, 'PASS' if ok else 'FAIL'))

    lines.append('')
    lines.append('WFYS 评分')
    lines.append('- 稳定性: %s/30' % _fmt_num(result['score']['modules']['稳定性']))
    lines.append('- 利润能力: %s/30' % _fmt_num(result['score']['modules']['利润能力']))
    lines.append('- 风险质量: %s/25' % _fmt_num(result['score']['modules']['风险质量']))
    lines.append('- 趋势利润结构: %s/15' % _fmt_num(result['score']['modules']['趋势利润结构']))
    lines.append('- 总分: %s/100' % _fmt_num(result['score']['total_score']))

    lines.append('')
    lines.append('WFYS 结论')
    lines.append('- 等级: %s' % result['grade'])
    lines.append('- 硬失败原因: %s' % ('; '.join(result['hard_failures']) if result['hard_failures'] else '无'))
    lines.append('- 主要拖累项: %s' % ('; '.join(result['score']['top_drags']) if result['score']['top_drags'] else '无'))

    lines.append('')
    lines.append('关键指标')
    lines.append('- 24月盈利月数: %s/24' % month['profitable_months'])
    lines.append('- 亏损月数: %s' % month['loss_months'])
    lines.append('- 大亏月数: %s' % month['big_loss_months'])
    lines.append('- 强利润月数: %s' % month['strong_months'])
    lines.append('- 大趋势月数: %s' % month['trend_months'])
    lines.append('- 月收益中位数: %s' % _fmt_pct(month['median_monthly_return']))
    lines.append('- Top3集中度: %s' % _fmt_pct(month['top3_concentration']))
    lines.append('- Top5集中度: %s' % _fmt_pct(month['top5_concentration']))
    lines.append('- 24月总收益率: %s' % _fmt_pct(month['total_return']))
    lines.append('- 720d净收益率: %s' % _fmt_pct(cont['net_return']))
    lines.append('- 720d最大回撤: %s' % _fmt_pct(cont['max_drawdown_pct']))
    lines.append('- Recovery Factor: %s' % _fmt_num(cont['recovery_factor']))
    lines.append('- Profit Factor: %s' % _fmt_num(cont['profit_factor']))
    lines.append('- Sharpe: %s' % _fmt_num(cont['sharpe']))
    lines.append('- Sortino: %s' % _fmt_num(cont['sortino']))
    lines.append('- Calmar: %s' % _fmt_num(cont['calmar']))
    lines.append('- avg_W/|avg_L|: %s' % _fmt_num(cont['avg_win_loss']))
    lines.append('- >3R大赢单占比: %s' % _fmt_pct(r_metrics['big_win_ratio']))
    lines.append('- <0.5R微利单占比: %s' % _fmt_pct(r_metrics['micro_win_ratio']))
    return '\n'.join(lines)


def main() -> int:
    args = _parse_args()
    monthly_rows = load_monthly_rows(Path(args.monthly_csv), args.strategy_prefix)
    report_meta = load_report_meta(Path(args.continuous_report))
    deposit = float(args.deposit) if args.deposit is not None else float(report_meta.get('deposit') or infer_monthly_deposit(monthly_rows) or 0.0)
    if deposit <= 0:
        raise SystemExit('无法推断初始资金，请显式传 --deposit')
    trades = load_trades(Path(args.trades_csv))
    result = build_result(monthly_rows, report_meta, trades, deposit, args.spec)
    text = render_result(result)
    print(text)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
