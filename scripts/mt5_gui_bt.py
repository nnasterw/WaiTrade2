"""MT5 GUI 策略测试器自动化 — 通过 Win32 API 操控已打开的 MT5 终端
解决 terminal64 /config: 路径损坏问题。需要 MT5 已启动且策略测试器已打开。
"""
import ctypes
import time
import subprocess
import os
from pathlib import Path

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ── 窗口查找 ─────────────────────────────────────────────────
def find_window(title_contains, class_name=None):
    """查找包含指定标题的顶层窗口"""
    hwnd = user32.FindWindowW(class_name, None)
    while hwnd:
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if title_contains.lower() in buf.value.lower():
            return hwnd
        hwnd = user32.FindWindowExW(0, hwnd, class_name, None)
    return None

def find_child(hwnd_parent, title_contains=None, class_name=None):
    """查找子窗口"""
    hwnd = user32.FindWindowExW(hwnd_parent, 0, class_name, None)
    while hwnd:
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if title_contains is None or title_contains.lower() in buf.value.lower():
            return hwnd
        hwnd = user32.FindWindowExW(hwnd_parent, hwnd, class_name, None)
    return None

def find_all_children(hwnd_parent, max_depth=3):
    """枚举所有子窗口"""
    results = []
    def _enum(hwnd, depth):
        if depth > max_depth: return
        child = user32.FindWindowExW(hwnd, 0, None, None)
        while child:
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(child, buf, 256)
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(child, cls_buf, 256)
            results.append((child, cls_buf.value, buf.value))
            _enum(child, depth + 1)
            child = user32.FindWindowExW(hwnd, child, None, None)
    _enum(hwnd_parent, 0)
    return results

# ── 窗口操作 ─────────────────────────────────────────────────
BM_CLICK = 0x00F5
WM_COMMAND = 0x0111
WM_SETTEXT = 0x000C
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D
VK_F5 = 0x74  # Start hotkey in MT5

def click_button(hwnd):
    """发送按钮点击消息"""
    user32.SendMessageW(hwnd, BM_CLICK, 0, 0)

def send_key(hwnd, vk_code):
    """发送键盘消息"""
    user32.PostMessageW(hwnd, WM_KEYDOWN, vk_code, 0)
    time.sleep(0.05)
    user32.PostMessageW(hwnd, WM_KEYUP, vk_code, 0)

# ── 策略测试器操作 ───────────────────────────────────────────
def find_tester_window():
    """查找 MT5 策略测试器窗口"""
    # MT5 主窗口
    main = find_window('MetaTrader 5', 'MetaQuotes::MetaTrader::5.00')
    if not main:
        print('ERROR: MT5 not running')
        return None

    # 策略测试器可能在主窗口内或独立窗口
    children = find_all_children(main, max_depth=4)
    tester = None
    for hwnd, cls, title in children:
        if 'tester' in title.lower() or 'strategy' in title.lower():
            tester = hwnd
            break

    if not tester:
        # 尝试独立的 Tester 窗口
        tester = find_window('Strategy Tester')

    return tester

def get_tester_buttons(tester_hwnd):
    """获取策略测试器的控件"""
    children = find_all_children(tester_hwnd, max_depth=5)
    buttons = []
    for hwnd, cls, title in children:
        if 'Button' in cls:
            buttons.append((hwnd, cls, title))
    return buttons

def click_start_backtest():
    """在策略测试器中点击 Start 按钮"""
    tester = find_tester_window()
    if not tester:
        print('ERROR: Strategy Tester not open. Press Ctrl+R in MT5 first.')
        return False

    # 策略测试器中 F5 = Start
    user32.SetForegroundWindow(tester)
    time.sleep(0.2)
    send_key(tester, VK_F5)
    print('Start sent (F5)')
    return True

def wait_for_backtest(data_dir, report_name, timeout=300):
    """等待回测 HTML 报告生成"""
    report_path = Path(data_dir) / f'{report_name}.htm'
    t0 = time.time()
    while time.time() - t0 < timeout:
        if report_path.exists() and report_path.stat().st_size > 1000:
            time.sleep(1)  # 等文件写完
            return True
        time.sleep(2)
    return False

# ── 主入口 ───────────────────────────────────────────────────
def run_gui_backtest(data_dir, report_name, timeout=300):
    """运行一次 GUI 回测: 点 Start → 等报告

    前提: MT5 已启动, 策略测试器已打开, .set/品种/周期/日期已配置好
    """
    print(f'Starting GUI backtest: {report_name}')
    if not click_start_backtest():
        return None

    if wait_for_backtest(data_dir, report_name, timeout):
        print(f'Report generated: {report_name}.htm')
        return str(Path(data_dir) / f'{report_name}.htm')
    else:
        print(f'Timeout waiting for report')
        return None

# ── CLI ──────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python mt5_gui_bt.py <report_name> [data_dir]')
        print('  report_name: name for the HTML report file')
        print('  data_dir: MT5 data directory (default: env MT5_DATA or C: default)')
        print()
        print('Prerequisites:')
        print('  1. MT5 running with Strategy Tester open (Ctrl+R)')
        print('  2. Expert, symbol, period, dates, .set already configured')
        sys.exit(1)

    report_name = sys.argv[1]
    data_dir = sys.argv[2] if len(sys.argv) > 2 else os.environ.get(
        'MT5_DATA',
        os.path.expandvars(r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
    )

    result = run_gui_backtest(data_dir, report_name)
    if result:
        print(f'SUCCESS: {result}')
    else:
        print('FAILED')
        sys.exit(1)
