#!/usr/bin/env python3
"""实验：验证熔断参数对2026-05回测的影响"""
import subprocess, sys, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SET_DIR = Path.home() / 'AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Profiles/Tester'
INI_DIR = Path.home() / 'AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/Tester'
MT5 = r'C:\Program Files\MetaTrader 5\terminal64.exe'

# Create test .set: v1 params + circuit breakers ALL disabled (0)
src = ROOT / 'mql5/Presets/V12XAU-ZD2.set'
dst = SET_DIR / 'V12XAU-ZD2-TEST2.set'
shutil.copy(src, dst)

content = dst.read_text()
content = content.replace(
    'InpMonthlyEarlyLossStopPct=0.0\nInpMonthlyEarlyLossStopMinBalance=0.0',
    'InpMonthlyEarlyLossStopPct=0.0\nInpConsecutiveLossCooldown=0\nInpConsecutiveLossCooldownMin=30\nInpDailyLossStopPct=0.0\nInpMonthlyEarlyLossStopMinBalance=0.0')
content = content.replace('InpVersion=V12XAU-ZD2', 'InpVersion=V12XAU-ZD2-TEST2')
content = content.replace('InpMagicNumber=205100', 'InpMagicNumber=205998')
dst.write_text(content)

# Verify
print("Test params in set file:")
for line in dst.read_text().split('\n'):
    if 'ConsecutiveLoss' in line or 'DailyLossStop' in line or 'VirtualSLConsecutive' in line:
        print(f"  {line}")

# Create ini
ini = INI_DIR / 'backtest.ini'
ini.write_text(f"""[Common]
Login=
Server=

[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters=V12XAU-ZD2-TEST2.set
Symbol=XAUUSDm
Period=M5
Model=4
Optimization=0
FromDate=2026.05.01
ToDate=2026.05.31
Deposit=200
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report=V12XAU-ZD2-TEST2
""")

# Kill any running MT5
subprocess.run(['powershell', '-Command',
    'Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | Stop-Process -Force'],
    capture_output=True, shell=True)
import time
time.sleep(3)

# Run MT5
print("\nStarting MT5 backtest...")
proc = subprocess.Popen([MT5, f'/config:{ini}'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE)

start = time.time()
while proc.poll() is None:
    elapsed = time.time() - start
    if elapsed > 300:
        proc.kill()
        print("Timeout!")
        break
    if int(elapsed) % 15 == 0:
        print(f"  waiting... {int(elapsed)}s")
    time.sleep(5)

print(f"MT5 exited after {int(time.time()-start)}s, returncode={proc.returncode}")

# Try to find and parse the report
time.sleep(2)
results_dir = ROOT / 'results/backtest'
reports = list(results_dir.glob('*TEST2*.txt'))
if not reports:
    reports = list(results_dir.glob('*V12XAU-ZD2-TEST2*'))

if reports:
    report = max(reports, key=lambda p: p.stat().st_mtime)
    text = report.read_text(encoding='utf-8')
    m = re.search(r'XAUUSDm\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+.*?\$([\d.]+)', text)
    if m:
        print(f"\nRESULT: {m.group(1)} trades, WR {m.group(2)}%, Balance \${m.group(3)}")
    else:
        print(f"Report found but couldn't parse: {text[:300]}")
else:
    print("No report generated")
    # Try agent log
    agent_logs = list(Path.home().glob('AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/Tester/Agent-127.0.0.1-3000/logs/*.log'))
    if agent_logs:
        log = max(agent_logs, key=lambda p: p.stat().st_mtime)
        print(f"Agent log: {log}")
        try:
            raw = log.read_bytes()
            text = raw.decode('utf-16-le', errors='ignore')
            # Look for final results
            for line in text.split('\n')[-30:]:
                if 'balance' in line.lower() or 'profit' in line.lower() or 'trades' in line.lower():
                    print(line[:200])
        except:
            pass
