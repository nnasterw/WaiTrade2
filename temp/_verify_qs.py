import sys, os

log_path = r'D:\Code\codexProject\WaiTrade2\temp\mt5_portable_xau_zd_qs\QS\MQL5\Logs\20260602.log'
try:
    raw = open(log_path, 'rb').read()
    text = raw.decode('utf-16-le', errors='ignore')
    lines = text.split('\n')

    # 找最后10行含关键信息的
    found = []
    for line in lines:
        if any(kw in line for kw in ['V11XAU', 'Magic=204', 'WaiTrade2 V', 'error', 'fail', 'PERIOD_M']):
            found.append(line.strip())

    print(f'日志总行数: {len(lines)}')
    print(f'匹配行数: {len(found)}')
    print('--- 最新10条 ---')
    for line in found[-10:]:
        print(line)

    # 检查是否有加载错误
    errors = [l for l in lines if 'error' in l.lower() or 'fail' in l.lower() or 'cannot' in l.lower()]
    if errors:
        print(f'--- 错误 ({len(errors)}条) ---')
        for e in errors[-5:]:
            print(e.strip())
except Exception as e:
    print(f'错误: {e}')
