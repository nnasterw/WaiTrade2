"""Enumerate all windows created by terminal64 to find correct class name / title."""
import subprocess, ctypes, time, threading, os, sys
from pathlib import Path

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
INI_DIR = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')) / 'Tester'

# Write backtest .ini
INI_DIR.mkdir(parents=True, exist_ok=True)
ini = INI_DIR / 'backtest.ini'
ini.write_text("""[Common]
Login=
Server=
[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters=v11xau-qs3.set
Symbol=XAUUSDm
Period=M1
Model=4
Optimization=0
FromDate=2026.05.01
ToDate=2026.05.02
Deposit=200
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report=diag_window
""", encoding='utf-8')

# Kill existing
subprocess.run(["powershell","-NoProfile","-Command",
    "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Stop-Process -Force"],
    capture_output=True)
time.sleep(3)

# Launch backtest
print("Launching terminal64...")
proc = subprocess.Popen(
    [str(MT5_HOME / 'terminal64.exe'), f'/config:{ini}'],
    creationflags=subprocess.CREATE_NO_WINDOW)

# Enumerate windows for 5 seconds
found = set()
t0 = time.time()
while time.time() - t0 < 8 and proc.poll() is None:
    # Enumerate ALL top-level windows
    windows = []

    def enum_callback(hwnd, _):
        # Get class name
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        cls = buf.value

        # Get title
        buf2 = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf2, 256)
        title = buf2.value

        # Get process ID
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        # Get window style
        style = user32.GetWindowLongW(hwnd, -16)  # GWL_STYLE

        key = f"{hwnd}|{cls}|{title}"
        if key not in found:
            found.add(key)
            windows.append((hwnd, cls, title, pid.value, style))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

    # Check for MT5-related windows
    for hwnd, cls, title, pid, style in windows:
        is_visible = bool(style & 0x10000000)  # WS_VISIBLE
        # Filter: MT5-related class names or titles
        if any(kw in (cls + title).lower() for kw in ['metatrader', 'mt5', 'metaquote', 'terminal']):
            print(f'  [{pid}] cls="{cls}" title="{title[:60]}" visible={is_visible} hwnd={hwnd}')
            # Try to hide it
            if is_visible:
                user32.ShowWindow(hwnd, 0)  # SW_HIDE
                print(f'    -> HIDDEN')

    time.sleep(0.5)

print(f"\nEnumerated {len(found)} unique windows total")

# Kill terminal
subprocess.run(["powershell","-NoProfile","-Command",
    "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Stop-Process -Force"],
    capture_output=True)
print("Done")

