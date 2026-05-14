import sys

log_path = r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\logs\20260514.log'
with open(log_path, 'r', encoding='utf-16-le', errors='replace') as f:
    for line in f:
        low = line.lower()
        if any(k in low for k in ['tester', 'config', 'strategy', 'startup', 'expert', 'waitrade', 'error', 'fail']):
            print(line.rstrip())
