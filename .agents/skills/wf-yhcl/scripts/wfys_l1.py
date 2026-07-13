#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wfys_l1.py: L1 WFYS 评分函数库

被 batch_diagnose.py 通过 `import wfys_l1 as L1` 引用。
功能: 24 月回测串行 + 聚合 + WFYS 评分 + 精简输出。

集成 10 个改进点:
  1. 批量 digest 缓存: aggregate_months() 单次扫 24 月 .txt
  2. 批量 WFYS 计算: compute_wfys_summary() 一次性 sum/median
  3. 失败不重试: run_backtest() 失败返回 False 立即跳过
  4. wfys_score 简输出: compact_wfys_output() 6 行硬编码
  5. MT5 后台批跑单实例: run_backtest 串行, 避免端口冲突
  6. backtest_digest 批量模式: aggregate_months 替代逐月 digest
  7. make_24m 直接拼 CSV: write_24m_csv() 不依赖外部 backtest_digest
  8. WFYS 结果缓存: --json 落盘可重复读
  9. 变体筛选前置: --skip-backtest 选项, 已有 24m 数据时跳过回测
  10. 半自动批跑脚本: batch_diagnose.py 核心驱动
"""
import re
import sys
import json
import csv
import subprocess
from pathlib import Path
from datetime import datetime
from calendar import monthrange

from _project import ROOT
RESULTS_DIR = ROOT / 'results' / 'backtest'


def read_text_auto(p):
    """GBK/UTF-8 自动检测(MT5 .txt 是 GBK 编码, PowerShell 写入可能 UTF-8)"""
    raw = Path(p).read_bytes()
    for enc in ('utf-8-sig', 'utf-8', 'gb18030', 'gbk', 'cp936'):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', errors='replace')


def run_backtest(strategy, symbol, date_from, date_to, model, timeout):
    """运行单次回测, 失败返回 False(失败不重试 - 改进点 #3)"""
    cmd = [sys.executable, str(ROOT / 'scripts' / 'mt5_backtest_win.py'),
           '--strategy', strategy, '--symbol', symbol,
           '--from', date_from, '--to', date_to,
           '--model', str(model), '--timeout', str(timeout)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                encoding='utf-8', errors='replace',
                                timeout=timeout + 60)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def generate_monthly_dates(start_str, end_str):
    """生成 (from, to, label) 月度日期三元组"""
    sd = datetime.strptime(start_str, '%Y.%m.%d')
    ed = datetime.strptime(end_str, '%Y.%m.%d')
    months = []
    cur = sd
    while cur <= ed:
        last_day = monthrange(cur.year, cur.month)[1]
        month_end = cur.replace(day=last_day)
        if month_end > ed:
            month_end = ed
        months.append((cur.strftime('%Y.%m.%d'),
                       month_end.strftime('%Y.%m.%d'),
                       '{}-{:02d}'.format(cur.year, cur.month)))
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1, day=1)
        else:
            cur = cur.replace(month=cur.month + 1, day=1)
    return months


def parse_monthly_result(txt_path, deposit):
    """解析单月回测 .txt: 失败/无数据返回 None"""
    if not txt_path.exists():
        return None
    content = read_text_auto(txt_path)
    fail_markers = ('\\u56de\\u6d4b\\u5931\\u8d25', '\\u65e0\\u6570\\u636e',
                    'timeout', 'ERROR', 'No data')
    for m in fail_markers:
        if m in content:
            return None
    match = re.search(
        r'BTCUSDm\s+(\d+)\s+[\d.]+\s+[\d.]+%?\s+[\d.%inf-]+\s+N/A\s+\$?([\d.,-]+)',
        content)
    if not match:
        return None
    try:
        balance = float(match.group(2).replace(',', ''))
    except ValueError:
        return None
    return {
        'profit': balance - deposit,
        'trades': int(match.group(1)),
        'balance': balance,
    }


def aggregate_months(strategy, deposit):
    """优先读取最新 720d trades.csv 拆分出的 24m CSV；不默认重跑独立月。"""
    monthly_csvs = sorted(
        RESULTS_DIR.glob(strategy + '*closetime_24m.csv'),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if monthly_csvs:
        monthly = []
        with monthly_csvs[0].open(encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                try:
                    monthly.append({
                        'month': row['month'],
                        'profit': float(row.get('net', 0) or 0),
                        'balance': float(row.get('balance', 0) or 0),
                        'trades': int(float(row.get('trades', 0) or 0)),
                    })
                except (KeyError, TypeError, ValueError):
                    continue
        if monthly:
            return monthly

    files = sorted(RESULTS_DIR.glob(strategy + '_*.txt'))
    monthly = []
    for f in files:
        parts = f.name.replace('.txt', '').split('_')
        if len(parts) < 4:
            continue
        start_date, end_date = parts[1], parts[2]
        if len(start_date) != 8 or len(end_date) != 8:
            continue
        try:
            sd = datetime.strptime(start_date, '%Y%m%d')
            ed = datetime.strptime(end_date, '%Y%m%d')
            days = (ed - sd).days + 1
        except ValueError:
            continue
        if not (28 <= days <= 31):
            continue
        result = parse_monthly_result(f, deposit)
        if result is None:
            continue
        monthly.append({
            'month': start_date[:4] + '-' + start_date[4:6],
            'profit': result['profit'],
            'balance': result['balance'],
            'trades': result['trades'],
        })
    return monthly

def write_24m_csv(strategy, monthly, deposit):
    """直接拼 24m CSV(make_24m 不依赖外部 backtest_digest - 改进点 #7)"""
    if not monthly:
        return None
    output = RESULTS_DIR / (strategy + '_BTCUSDm_24m_' + datetime.now().strftime('%Y%m%d') + '.csv')
    monthly.sort(key=lambda x: x['month'])
    with output.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['month', 'net', 'balance', 'trades', 'wins', 'wr'])
        bal = deposit
        for m in monthly:
            bal += m['profit']
            w.writerow([m['month'], '{:.2f}'.format(m['profit']),
                        '{:.2f}'.format(bal), m['trades'], 0, '0.0'])
    return output


def compute_wfys_summary(monthly, deposit):
    """一次性 WFYS 计算(批量 WFYS - 改进点 #2)"""
    if not monthly:
        return None
    total_profit = sum(m['profit'] for m in monthly)
    final_balance = deposit + total_profit
    profit_months = sum(1 for m in monthly if m['profit'] > 0)
    loss_months = sum(1 for m in monthly if m['profit'] < 0)
    zero_months = sum(1 for m in monthly if m['profit'] == 0)
    total_trades = sum(m['trades'] for m in monthly)
    sorted_profits = sorted([m['profit'] for m in monthly])
    median_monthly = sorted_profits[len(monthly) // 2]
    return {
        'period_months': len(monthly),
        'profit_months': profit_months,
        'loss_months': loss_months,
        'zero_months': zero_months,
        'total_profit': total_profit,
        'final_balance': final_balance,
        'return_pct': (total_profit / deposit) * 100 if deposit else 0,
        'total_trades': total_trades,
        'median_monthly_pnl': median_monthly,
        'wfys_estimate_pct': (profit_months / len(monthly)) * 100,
    }


def compact_wfys_output(summary, strategy):
    """精简 WFYS 输出(6 行 - 改进点 #4)"""
    print('=== ' + strategy + ' WFYS Summary ===')
    print('24m: {}/{} 盈利, {} 亏损, {} 零'.format(
        summary['profit_months'], summary['period_months'],
        summary['loss_months'], summary['zero_months']))
    print('24m 总收益: ${:.2f} ({:.1f}%)'.format(
        summary['total_profit'], summary['return_pct']))
    print('24m 最终余额: ${:.2f}'.format(summary['final_balance']))
    print('24m 笔数: {}'.format(summary['total_trades']))
    print('24m 中位月: ${:.2f}'.format(summary['median_monthly_pnl']))
    print('24m 利润月占比: {:.1f}%'.format(summary['wfys_estimate_pct']))
    return summary
