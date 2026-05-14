"""Parse MT5 HTML backtest report v2"""
import re

path = r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\wt_V96b_XAUUSDm_30d_v2.htm'

with open(path, 'r', encoding='utf-16-le', errors='replace') as f:
    content = f.read()

text = re.sub(r'<[^>]+>', '|', content)
text = re.sub(r'\|+', '|', text)
text = re.sub(r'\s+', ' ', text)

labels = {
    'Total Net Profit': 'TotalNetProfit',
    'Gross Profit': 'GrossProfit',
    'Gross Loss': 'GrossLoss',
    'Profit Factor': 'ProfitFactor',
    'Expected Payoff': 'ExpectedPayoff',
    'Recovery Factor': 'RecoveryFactor',
    'Sharpe Ratio': 'SharpeRatio',
    'Balance Drawdown Absolute': 'AbsDrawdown',
    'Balance Drawdown Maximal': 'MaxDrawdown',
    'Balance Drawdown Relative': 'RelDrawdown',
    'Total Trades': 'TotalTrades',
    'Short Trades': 'ShortTrades',
    'Long Trades': 'LongTrades',
    'Profit Trades': 'ProfitTrades',
    'Loss Trades': 'LossTrades',
    'Initial Deposit': 'Deposit',
    'Bars': 'Bars',
    'Ticks': 'Ticks',
    'Modeling Quality': 'Quality',
}

print("=" * 60)
print("V96b XAUUSDm 30d M1 Backtest (CORRECTED params)")
print("time_exit_bars=12, time_decay_tp=true, dtp_trigger=1.5R")
print("=" * 60)

for label, key in labels.items():
    escaped = re.escape(label)
    pat = re.compile(escaped + r'.*?([-]?\$?[\d,]+\.?\d*%?)', re.IGNORECASE)
    m = pat.search(text)
    if m:
        print(f"  {label}: {m.group(1)}")
