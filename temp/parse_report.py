"""Parse MT5 HTML backtest report (UTF-16LE)"""
import re

path = r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\wt_V96b_XAUUSDm_30d.html'

with open(path, 'r', encoding='utf-16-le', errors='replace') as f:
    content = f.read()

# Remove tags
text = re.sub(r'<[^>]+>', '|', content)
text = re.sub(r'\|+', '|', text)
text = re.sub(r'\s+', ' ', text)

# Find known MT5 report labels
labels = {
    'Expert': 'Expert',
    'Symbol': 'Symbol',
    'Period': 'Period',
    'Initial Deposit': 'Deposit',
    'Leverage': 'Leverage',
    'Modeling Quality': 'Quality',
    'Bars': 'Bars in test',
    'Ticks': 'Ticks modelled',
    'Total Net Profit': 'TotalNetProfit',
    'Gross Profit': 'GrossProfit',
    'Gross Loss': 'GrossLoss',
    'Profit Factor': 'ProfitFactor',
    'Expected Payoff': 'ExpectedPayoff',
    'Recovery Factor': 'RecoveryFactor',
    'Sharpe Ratio': 'SharpeRatio',
    'AHPR': 'AHPR',
    'GHPR': 'GHPR',
    'Balance Drawdown Absolute': 'AbsDrawdown',
    'Balance Drawdown Maximal': 'MaxDrawdown',
    'Balance Drawdown Relative': 'RelDrawdown',
    'Total Trades': 'TotalTrades',
    'Short Trades': 'ShortTrades',
    'Long Trades': 'LongTrades',
    'Profit Trades': 'ProfitTrades',
    'Loss Trades': 'LossTrades',
    'Largest profit trade': 'BestTrade',
    'Largest loss trade': 'WorstTrade',
    'Average profit trade': 'AvgProfitTrade',
    'Average loss trade': 'AvgLossTrade',
    'Maximum consecutive wins': 'MaxConsecWins',
    'Maximum consecutive losses': 'MaxConsecLosses',
    'Maximal consecutive profit': 'MaxConsecProfit',
    'Maximal consecutive loss': 'MaxConsecLoss',
}

# Print raw values by searching for known patterns
print("=" * 60)
print("V96b XAUUSDm 30天 M1 回测报告")
print("=" * 60)

# Extract specific data
data = {}
for label, key in labels.items():
    # Try to find label followed by a number
    # Use regex: label followed by anything, then a number with optional sign/$
    escaped = re.escape(label)
    pat = re.compile(escaped + r'.*?([-]?\$?[\d,]+\.?\d*%?)', re.IGNORECASE)
    m = pat.search(text)
    if m:
        data[key] = m.group(1)
        print(f"  {label}: {m.group(1)}")

# Try broader search for items not found
more_items = [
    ('deal', 'TotalDeals'),
    ('balance drawdown', 'BalDD'),
]
for needle, key in more_items:
    if key not in data:
        pat = re.compile(re.escape(needle) + r'.*?([-]?\$?[\d,]+\.?\d*%?)', re.IGNORECASE)
        m = pat.search(text)
        if m:
            data[key] = m.group(1)
            print(f"  {needle}: {m.group(1)}")

# Print full report text as fallback (non-gibberish parts)
print("\n--- Raw text extract (first 2000 chars of non-garbage) ---")
# Filter for ASCII + common Chinese chars
clean = ''.join(c for c in text if ord(c) < 0x4e00 or 0x9fff >= ord(c) >= 0x4e00)
print(clean[:2000])
