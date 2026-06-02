import subprocess, os, sys, time

qs_dir = r'D:\Code\codexProject\WaiTrade2\temp\mt5_portable_xau_zd_qs\QS'
exe = os.path.join(qs_dir, 'terminal64.exe')
ini = os.path.join(qs_dir, 'v11xau_live_QS2_startup.ini')

cmd = [exe, '/portable', f'/config:{ini}']
print(f'启动 QS 终端: {cmd}')

os.chdir(qs_dir)
proc = subprocess.Popen(
    cmd,
    cwd=qs_dir,
    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
)
print(f'PID: {proc.pid}')
time.sleep(10)
print('已启动，检查进程...')
