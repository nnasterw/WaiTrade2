import os, subprocess, time, re
from pathlib import Path

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
MT5_DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
INI_DIR = MT5_DATA / 'Tester'

os.makedirs(INI_DIR, exist_ok=True)
(INI_DIR/'backtest.ini').write_text("""[Common]
Login=
Server=
[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters=V11XAU-QS3.set
Symbol=XAUUSDm
Period=M1
Model=4
Optimization=0
FromDate=2024.06.01
ToDate=2026.05.31
Deposit=300
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report=p18_qs3_check
""", encoding='utf-8')

subprocess.run(['powershell','-NoProfile','-Command',
    'Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | '
    'Where-Object { $_.Path -and $_.Path.StartsWith(\'C:\\Program Files\\MetaTrader 5\') } | '
    'Stop-Process -Force'], capture_output=True)
time.sleep(4)

ini = INI_DIR / 'backtest.ini'
print("Running QS3 720-day...", end='', flush=True)
proc = subprocess.Popen([MT5_TERMINAL, f'/config:{ini}'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
t0 = time.time()
while proc.poll() is None:
    if time.time()-t0 > 600: proc.kill(); break
    if int(time.time()-t0) % 20 == 0: print('.', end='', flush=True)
    time.sleep(5)
print(f' ({time.time()-t0:.0f}s)')

htm = MT5_DATA / 'p18_qs3_check.htm'
if htm.exists():
    raw = htm.read_bytes()
    html = raw.decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    trades = [float(re.findall(r'<td[^>]*>(.*?)</td>', r)[10].strip()) for r in rows
              if len(re.findall(r'<td[^>]*>(.*?)</td>', r)) == 13
              and re.findall(r'<td[^>]*>(.*?)</td>', r)[3] != 'balance'
              and re.findall(r'<td[^>]*>(.*?)</td>', r)[4].strip() == 'out']
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    gw = sum(wins) if wins else 0
    gl = abs(sum(losses)) if losses else 0
    pf = gw/gl if gl > 0 else 0
    wr = len(wins)/len(trades)*100 if trades else 0
    print(f'\nQS3 720d: {len(trades)}T, WR={wr:.1f}%, PF={pf:.2f}, PnL=${sum(trades):.2f}, Bal=${300+sum(trades):.2f}')
    print(f'Commit said: QS3 = $313K')
    ratio = (300+sum(trades)) / 313000
    print(f'Our result / Commit result = {ratio:.1%}')
else:
    print("FAILED - no report")
