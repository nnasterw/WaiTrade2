"""Shared utilities: silent MT5 backtest runner.
1ms sync polling catches MT5 window by class name, hides <1 frame (<16ms).
Background thread continues at 100ms/1s. No ctypes callbacks.

Data directory selection (priority):
  $MT5_HOME → portable terminal at that path (self-contained)
  $MT5_DATA → explicit data directory override
  default   → installed terminal at C:\Program Files + %APPDATA%"""
import os, subprocess, time, re, shutil, ctypes, threading
from pathlib import Path

# 便携版终端优先(通过环境变量)
_MT5_HOME_ENV = os.environ.get('MT5_HOME', '')
_MT5_DATA_ENV = os.environ.get('MT5_DATA', '')

if _MT5_HOME_ENV:
    # 便携模式: 所有数据在终端目录内部
    MT5_HOME = Path(_MT5_HOME_ENV)
    MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
    MT5_DATA = MT5_HOME
elif _MT5_DATA_ENV:
    # 仅数据目录覆盖(使用已安装终端)
    MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
    MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
    MT5_DATA = Path(_MT5_DATA_ENV)
else:
    # 默认: 已安装终端 + %APPDATA%
    MT5_HOME = Path(r'C:\Program Files\MetaTrader 5')
    MT5_TERMINAL = str(MT5_HOME / 'terminal64.exe')
    MT5_DATA = Path(os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'))
PROJECT = Path(__file__).resolve().parent.parent
PRESETS = PROJECT / 'mql5' / 'Presets'
MT5_PROFILES = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
DEPOSIT = 200
SYMBOL = 'XAUUSDm'

_user32 = ctypes.WinDLL('user32', use_last_error=True)
SW_HIDE = 0
# MT5 window classes — main window + dialog. Must catch ALL.
MT5_CLASSES = ['MetaQuotes::MetaTrader::5.00', '#32770']


def kill_mt5():
    # Only kill metatester64 (tester agent), NOT terminal64 (live connection).
    # Killing terminal64 disconnects Exness, breaking Model 4 backtests.
    subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-Process -Name metatester64 -ErrorAction SilentlyContinue | "
        "Stop-Process -Force"], capture_output=True)
    time.sleep(4)


def _hide_all():
    """Enumerate ALL MT5 windows (all classes, all siblings) and hide each.
    Returns count of windows found."""
    count = 0
    for cls in MT5_CLASSES:
        hwnd = _user32.FindWindowW(cls, None)
        while hwnd:
            _user32.ShowWindow(hwnd, SW_HIDE)
            _user32.SetWindowPos(hwnd, 0, -10000, -10000, 0, 0, 0x0001 | 0x0004)
            count += 1
            hwnd = _user32.FindWindowExW(0, hwnd, cls, None)
    return count


def _poller(proc):
    """Background thread: persistent hiding at 100ms/1s.
    NEVER stops — MT5 can create new windows at any time."""
    t0 = time.time()
    while proc.poll() is None:
        _hide_all()
        time.sleep(0.1 if time.time() - t0 < 10 else 1.0)


def run_backtest_hidden(ini_path):
    """Launch backtest. Main thread 1ms polls for 3s (catches initial windows),
    background thread continues at 100ms/1s (catches late-created windows).
    CRITICAL: does NOT break on first find — MT5 creates 3+ windows sequentially."""
    cmd = [MT5_TERMINAL]
    if _MT5_HOME_ENV:  # 便携模式需显式/portable
        cmd.append('/portable')
    cmd.append(f'/config:{ini_path}')
    proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)

    # Phase 1: Main thread, 1ms polling for 3 seconds.
    # Keeps polling even after finding windows — MT5 creates them sequentially.
    t0 = time.time()
    while time.time() - t0 < 3.0:
        _hide_all()
        time.sleep(0.001)

    # Phase 2: Background continued hiding
    threading.Thread(target=_poller, args=(proc,), daemon=True).start()
    return proc


def run_bt_silent(name, set_name, date_from, date_to, ini_dir=None, deposit=DEPOSIT):
    """Run single backtest silently. Returns parsed dict or None."""
    if ini_dir is None:
        ini_dir = MT5_DATA / 'Tester'
    ini_dir.mkdir(parents=True, exist_ok=True)
    ini_path = ini_dir / 'backtest.ini'
    ini_path.write_text(
        "[Common]\nLogin=\nServer=\n"
        "[Tester]\nExpert=WaiTrade2\WaiTrade_OB\n"
        f"ExpertParameters={set_name}\n"
        f"Symbol={SYMBOL}\nPeriod=M1\nModel=4\n"
        "Optimization=0\n"
        f"FromDate={date_from}\nToDate={date_to}\n"
        f"Deposit={deposit}\nCurrency=USD\nLeverage=2000\n"
        "ExecutionMode=0\nShutdownTerminal=1\n"
        f"Report={name}\n", encoding='utf-8')

    htm = MT5_DATA / f'{name}.htm'
    if htm.exists():
        htm.unlink()

    proc = run_backtest_hidden(str(ini_path))
    t0 = time.time()
    while True:
        # 检查报告已生成(主要完成信号)
        if htm.exists() and htm.stat().st_size > 1000:
            time.sleep(0.5)  # 等待文件写入完成
            # 杀掉残留进程(metatester64可能仍在运行)
            kill_mt5()
            break
        # 父进程(terminal64)退出但报告未生成 → 继续等待子进程(metatester64)
        if proc.poll() is not None:
            # 等待额外60秒给metatester64完成
            if time.time() - t0 > 120:
                break
        if time.time() - t0 > 600:
            kill_mt5()
            return None
        time.sleep(2)

    if htm.exists() and htm.stat().st_size > 1000:
        return parse_report(htm)
    return None


def make_set(variant_key, overrides_dict, base='v11xau-qs3.set'):
    """Create variant .set and copy to MT5 Tester profiles."""
    src = PRESETS / base
    dst_name = f'{base.replace(".set","")}-{variant_key}.set'
    dst = PRESETS / dst_name
    lines = src.read_text(encoding='utf-8').splitlines()
    omap = dict(overrides_dict)
    out = []
    for line in lines:
        if '=' in line:
            param = line.split('=')[0].strip()
            if param in omap:
                out.append(f'{param}={omap[param]}')
                del omap[param]
                continue
        out.append(line)
    for p, v in omap.items():
        out.append(f'{p}={v}')
    dst.write_text('\n'.join(out), encoding='utf-8')
    MT5_PROFILES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(dst), str(MT5_PROFILES / dst_name))
    return dst_name


def parse_report(htm_path):
    """Parse MT5 HTML report into {count, pnl, wins, losses, wr, pf, daily}."""
    html = htm_path.read_bytes().decode('utf-16-le', errors='replace')
    rows = re.findall(r'<tr bgcolor="[^"]*" align=right>(.*?)</tr>', html, re.DOTALL)
    pending = []
    trades = []
    for r in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r)
        if len(cells) != 13:
            continue
        if cells[3].strip() == 'balance':
            continue
        io = cells[4].strip()
        try:
            pnl = float(cells[10].strip().replace(' ', '').replace(',', ''))
        except ValueError:
            pnl = 0.0
        if io == 'in':
            pending.append(1)
        elif io == 'out' and pending:
            pending.pop(0)
            trades.append(pnl)
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    gw = sum(wins) if wins else 0
    gl = abs(sum(losses)) if losses else 0
    return {
        'count': len(trades), 'pnl': sum(trades),
        'wins': len(wins), 'losses': len(losses),
        'wr': len(wins) / len(trades) * 100 if trades else 0,
        'pf': gw / gl if gl > 0 else (999 if gw > 0 else 0),
        'daily': len(trades) / 31,
    }
