import re
for log in [
    'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_xau/Tester/logs/20260607.log',
    'D:/Code/codexProject/WaiTrade2/temp/mt5_portable_xau/logs/20260607.log',
]:
    print(f'\n=== {log} ===')
    try:
        text = open(log, 'rb').read().decode('utf-16-le', errors='replace')
        for l in text.split('\n')[-20:]:
            lc = re.sub(r'[^\x20-\x7E\[\]\{\}\(\)\<\>\=\:\;\,\.\/\\\\]', '', l).strip()
            if lc: print(lc[:150])
    except FileNotFoundError:
        print('NOT FOUND')
