import re
f=open('D:/Code/codexProject/WaiTrade2/temp/mt5_portable_xau/Tester/logs/20260607.log','rb')
raw=f.read()
text=raw.decode('utf-16-le',errors='replace')
for l in text.split('\n')[-20:]:
    lc=re.sub(r'[^\x20-\x7E\[\]\{\}\(\)\<\>\=\:\;\,\.\/\\\\]','',l).strip()
    if lc: print(lc[:150])
