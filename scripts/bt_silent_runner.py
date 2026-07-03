"""Silent MT5 backtest runner: uses PowerShell to hide the terminal window."""
import os, subprocess, time, ctypes, platform, sys
from pathlib import Path

MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')

def is_windows():
    return platform.system() == 'Windows'

def run_backtest_hidden(
    mt5_home: Path = MT5_HOME,
    ini_path: str = None,
    method: str = 'powershell_hidden',
    timeout: int = 600,
    kill_first: bool = True,
) -> subprocess.Popen:
    """
    Run MT5 terminal64 backtest without window popping up.
    Methods:
      'powershell_hidden' — Start-Process -WindowStyle Hidden (best, no poll overhead)
      'win32_hide'       — Win32 FindWindow+ShowWindow after 200ms polling (reliable fallback)
      'minimized'        — Start-Process -WindowStyle Minimized (visible but not covering)
    """
    exe = str(mt5_home / 'terminal64.exe')
    args = f'/config:{ini_path}'

    if method == 'powershell_hidden':
        ps_cmd = (
            f"$p = Start-Process -FilePath '{exe}' "
            f"-ArgumentList '{args}' "
            f"-WindowStyle Hidden -PassThru; "
            f"Wait-Process -Id $p.Id; "
            f"exit $p.ExitCode"
        )
        return subprocess.Popen(
            ['powershell', '-NoProfile', '-Command', ps_cmd],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW)

    elif method == 'win32_hide':
        proc = subprocess.Popen(
            [exe, args],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Poll + hide window in background
        _hide_window_async(proc)
        return proc

    elif method == 'minimized':
        ps_cmd = (
            f"$p = Start-Process -FilePath '{exe}' "
            f"-ArgumentList '{args}' "
            f"-WindowStyle Minimized -PassThru; "
            f"Wait-Process -Id $p.Id; "
            f"exit $p.ExitCode"
        )
        return subprocess.Popen(
            ['powershell', '-NoProfile', '-Command', ps_cmd],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW)

    else:
        raise ValueError(f'Unknown method: {method}')


def _hide_window_async(proc):
    """Spawn a thread to poll for the MT5 window and hide it immediately."""
    import threading
    USER32 = ctypes.WinDLL('user32', use_last_error=True)
    SW_HIDE = 0

    def poller():
        t0 = time.time()
        while proc.poll() is None and time.time() - t0 < 30:
            hwnd = USER32.FindWindowW(None, 'MetaTrader 5')
            if hwnd:
                USER32.ShowWindow(hwnd, SW_HIDE)
                return
            time.sleep(0.2)

    t = threading.Thread(target=poller, daemon=True)
    t.start()


def wait_complete(proc, timeout=600):
    """Wait for process to finish, return elapsed seconds."""
    t0 = time.time()
    while proc.poll() is None:
        if time.time() - t0 > timeout:
            proc.kill()
            return time.time() - t0, False
        time.sleep(3)
    return time.time() - t0, True


# === Drop-in replacement for existing backtest runner ===
def create_silent_bt_runner(mt5_home=MT5_HOME, method='powershell_hidden'):
    """Factory: returns a function compatible with existing backtest scripts.

    Usage in any bt_*.py script:
        from bt_silent_runner import create_silent_bt_runner
        run_backtest = create_silent_bt_runner()
        proc = run_backtest('name', 'v11xau-xxx.set', '2026.05.01', '2026.05.31')
        elapsed, ok = wait_complete(proc)
    """
    from pathlib import Path as _P

    INI_DIR = _P(os.path.expandvars(
        r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\Tester'))

    def runner(name, set_name, date_from, date_to, deposit=200, symbol='XAUUSDm'):
        INI_DIR.mkdir(parents=True, exist_ok=True)
        ini_path = INI_DIR / 'backtest.ini'
        ini_path.write_text(
            f"[Common]\nLogin=\nServer=\n"
            f"[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\n"
            f"ExpertParameters={set_name}\n"
            f"Symbol={symbol}\nPeriod=M1\nModel=4\n"
            f"Optimization=0\nFromDate={date_from}\nToDate={date_to}\n"
            f"Deposit={deposit}\nCurrency=USD\nLeverage=2000\n"
            f"ExecutionMode=0\nShutdownTerminal=1\n"
            f"Report={name}\n", encoding='utf-8')

        # Kill existing MT5 first
        subprocess.run(["powershell","-NoProfile","-Command",
            "Get-Process -Name terminal64,metatester64 -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Path -and $_.Path.StartsWith('C:\\Program Files\\MetaTrader 5') } | "
            "Stop-Process -Force"], capture_output=True)
        time.sleep(4)

        return run_backtest_hidden(
            mt5_home=mt5_home,
            ini_path=str(ini_path),
            method=method)

    return runner


if __name__ == '__main__':
    """Quick smoke test: run 1 backtest silently."""
    runner = create_silent_bt_runner(method='powershell_hidden')
    print("Silent runner smoke test...", end=' ', flush=True)
    proc = runner('smoke_silent', 'v11xau-qs3.set', '2026.05.01', '2026.05.31')
    elapsed, ok = wait_complete(proc)
    htm = Path(os.path.expandvars(
        r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')) / 'smoke_silent.htm'
    result = htm.exists() and htm.stat().st_size > 1000
    print(f'{"OK" if result else "FAIL"} ({elapsed:.0f}s)')
    sys.exit(0 if result else 1)
