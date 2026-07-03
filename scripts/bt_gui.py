"""GUI回测: 通过窗口消息触发已运行MT5的策略测试器。
替代 bt_shared.run_bt_silent — 解决 terminal64 /config: 路径损坏问题。

前提: MT5已启动, 策略测试器已打开(Ctrl+R), Expert/Symbol/Period已选好。
      只需每次替换.set文件, 发F5启动回测。
"""
import ctypes, time, shutil, os
from pathlib import Path

user32 = ctypes.windll.user32

PROJECT = Path(__file__).resolve().parent.parent
PRESETS = PROJECT / 'mql5' / 'Presets'

# MT5数据目录 — C:盘安装终端(默认)
MT5_DATA = Path(os.path.expandvars(
    os.environ.get('MT5_DATA',
    r'%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')))

# ── 窗口操作 ─────────────────────────────────────────────────
VK_F5 = 0x74
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101

def find_tester():
    """查找MT5策略测试器子窗口"""
    main = user32.FindWindowW('MetaQuotes::MetaTrader::5.00', None)
    if not main: return None

    # 枚举所有子孙窗口找Tester面板
    found = []
    def enum_children(hwnd, depth=0):
        if depth > 5: return
        child = user32.FindWindowExW(hwnd, 0, None, None)
        while child:
            buf = ctypes.create_unicode_buffer(128)
            user32.GetClassNameW(child, buf, 128)
            cls = buf.value
            user32.GetWindowTextW(child, buf, 128)
            title = buf.value
            if 'tester' in title.lower() or 'strategy' in title.lower() or cls == 'SysTabControl32':
                found.append((child, cls, title))
            enum_children(child, depth+1)
            child = user32.FindWindowExW(hwnd, child, None, None)
    enum_children(main)
    return found

def send_f5():
    """发送F5到MT5窗口启动/重启回测"""
    main = user32.FindWindowW('MetaQuotes::MetaTrader::5.00', None)
    if not main:
        print('ERROR: MT5 not running')
        return False
    user32.SetForegroundWindow(main)
    time.sleep(0.15)
    user32.PostMessageW(main, WM_KEYDOWN, VK_F5, 0)
    time.sleep(0.05)
    user32.PostMessageW(main, WM_KEYUP, VK_F5, 0)
    return True

# ── .set管理 ─────────────────────────────────────────────────
def deploy_set(set_name, overrides, base='v11xau-qs3.set'):
    """生成.set并部署到MT5数据目录"""
    src = PRESETS / base
    dst_name = f'{base.replace(".set","")}-{set_name}.set'
    dst_project = PRESETS / dst_name

    lines = src.read_text(encoding='utf-8').splitlines()
    omap = dict(overrides)
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
    dst_project.write_text('\n'.join(out), encoding='utf-8')

    # 复制到MT5数据目录
    profiles = MT5_DATA / 'MQL5' / 'Profiles' / 'Tester'
    profiles.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(dst_project), str(profiles / dst_name))
    return dst_name

# ── 回测运行 ─────────────────────────────────────────────────
def run_gui_bt(name, set_overrides, timeout=300):
    """运行一次GUI回测:
    1. 生成.set → 部署到MT5
    2. 发送F5启动回测
    3. 等待HTML报告生成
    返回 parse_report 结果或 None
    """
    from bt_shared import parse_report

    # 1. 部署.set
    set_name = deploy_set(name, set_overrides)
    print(f'  .set={set_name} → 请在MT5策略测试器选择此文件', flush=True)

    # 2. 清除旧报告
    htm = MT5_DATA / f'{name}.htm'
    if htm.exists():
        htm.unlink()

    # 3. 启动回测
    if not send_f5():
        return None
    print(f'  F5 sent, waiting for report...', end=' ', flush=True)

    # 4. 等待报告
    t0 = time.time()
    while time.time() - t0 < timeout:
        if htm.exists() and htm.stat().st_size > 1000:
            time.sleep(1)
            print(f'OK({time.time()-t0:.0f}s)')
            return parse_report(htm)
        time.sleep(2)

    print(f'TIMEOUT')
    return None

# ── CLI ──────────────────────────────────────────────────────
if __name__ == '__main__':
    print('MT5 GUI 回测工具')
    print(f'数据目录: {MT5_DATA}')
    print()
    windows = find_tester()
    if windows:
        print(f'MT5已运行, 找到 {len(windows)} 个相关窗口')
    else:
        print('WARNING: MT5未运行或策略测试器未打开')
