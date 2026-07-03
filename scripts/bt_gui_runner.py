"""GUI回测运行器 — 不杀进程，不启动新终端，用已运行的MT5 GUI"""
import os, sys, time, ctypes, shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / 'scripts'))

user32 = ctypes.windll.user32
MT5_CLASS = 'MetaQuotes::MetaTrader::5.00'
VK_CONTROL = 0x11; VK_R = 0x52; VK_F5 = 0x74
SW_RESTORE = 9

def find_terminal(timeout=30):
    for i in range(timeout):
        hwnd = user32.FindWindowW(MT5_CLASS, None)
        if hwnd: return hwnd
        time.sleep(1)
    return 0

def send_keys(hwnd, vk, ctrl=False):
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    if ctrl:
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
        time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
    if ctrl:
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 2, 0)

def run_backtest_gui(name, set_name, date_from, date_to, deposit=200, timeout=300):
    from bt_shared import SYMBOL, parse_report

    print('  查找MT5终端窗口...')
    hwnd = find_terminal()
    if not hwnd:
        print('  X 找不到终端！请手动打开MT5')
        return None
    print(f'  找到终端窗口')

    # 找数据目录
    appdata = Path(os.environ['APPDATA']) / 'MetaQuotes' / 'Terminal'
    MT5_DATA = None
    for d in appdata.iterdir():
        if (d / 'MQL5' / 'Experts' / 'WaiTrade2' / 'WaiTrade_OB.ex5').exists():
            MT5_DATA = d
            break
    if not MT5_DATA:
        MT5_DATA = appdata / '3D2E4CE40359B023577FC9206E2DBC80'
    print(f'  数据目录: {MT5_DATA}')

    # 部署.set
    profiles = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
    profiles.mkdir(parents=True, exist_ok=True)
    src = PROJECT / 'mql5' / 'Presets' / set_name
    if src.exists():
        shutil.copy2(str(src), str(profiles / set_name))

    htm = MT5_DATA / f'{name}.htm'
    if htm.exists(): htm.unlink()

    # 写INI
    ini = MT5_DATA / 'Tester' / 'backtest.ini'
    ini.parent.mkdir(parents=True, exist_ok=True)
    ini.write_text(
        "[Common]\nLogin=\nServer=\n"
        "[Tester]\nExpert=WaiTrade2\\WaiTrade_OB\n"
        f"ExpertParameters={set_name}\n"
        f"Symbol={SYMBOL}\nPeriod=M1\nModel=4\n"
        "Optimization=0\n"
        f"FromDate={date_from}\nToDate={date_to}\n"
        f"Deposit={deposit}\nCurrency=USD\nLeverage=2000\n"
        "ExecutionMode=0\n"
        f"Report={name}\n", encoding='utf-8')

    # Ctrl+R -> 打开策略测试器
    print('  打开策略测试器 (Ctrl+R)...')
    send_keys(hwnd, VK_R, ctrl=True)
    time.sleep(3)

    # F5 -> 启动回测
    print('  启动回测 (F5)...')
    send_keys(hwnd, VK_F5)
    time.sleep(2)

    # 等待回测
    print(f'  等待回测 (最长{timeout}秒)...')
    t0 = time.time(); last = 0
    while time.time() - t0 < timeout:
        if htm.exists() and htm.stat().st_size > 1000:
            elapsed = time.time() - t0
            print(f'  完成！ ({elapsed:.0f}s)')
            time.sleep(0.5)
            return parse_report(htm)
        e = time.time() - t0
        if e - last > 15:
            print(f'  等待中... {e:.0f}s')
            last = e
        time.sleep(2)

    print(f'  超时 ({timeout}s)')
    return None

if __name__ == '__main__':
    from bt_shared import make_set
    REG3 = {'InpEnableTickNoiseGate':'true','InpEnableDynamicSpread':'true','InpMinSLSpreadMult':'5.0','InpOBTouchConfirmTicks':'5','InpDTPTriggerR':'1.0','InpDTPRetrace':'0.20','InpBreakevenR':'0.0','InpBreakevenLockR':'0.0','InpEnableMTF':'false','InpSLBufferATR':'0.4','InpMaxPosMult':'2.0','InpEnableLiquiditySweep':'true','InpEnableStateFilter':'true','InpEnableDoubleSweepConfirm':'true'}
    sn = make_set('gui-bt-2605', REG3)
    print(f'SET: {sn}')
    r = run_backtest_gui('gui_bt_2605', sn, '2026.05.01', '2026.05.31', timeout=300)
    if r:
        print(f'T={r["count"]} PnL=${r["pnl"]:.2f} WR={r["wr"]:.1f}% PF={r["pf"]:.2f}')
    else:
        print('FAILED')
