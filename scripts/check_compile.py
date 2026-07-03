with open('D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt/compile_mtf.log', 'rb') as f:
    data = f.read()
text = data.decode('utf-16-le', errors='replace')
for line in text.split('\n'):
    low = line.lower()
    if 'error' in low or 'warning' in low or 'result' in low:
        print(line.strip())
