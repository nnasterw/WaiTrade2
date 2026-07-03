import sys
with open(sys.argv[1],'r',encoding='utf-8',errors='replace') as f:
    for line in f:
        line=line.replace('�','')
        if any(kw in line for kw in ['赢单特征','亏单特征','最优组合','MFE分布','出场原因','转亏为盈','全共振','若只做','WR=','PnL=','Q2 2026','笔交易']):
            print(line.rstrip())
