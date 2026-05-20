# MT5 后台回测指南

日期: 2026-05-20
状态: 已实现并验证

## 功能

macOS Wine回测支持后台模式 — MT5窗口不弹到前台，不抢焦点，可在后台静默运行。

## 使用方法

```bash
# 加 --background 或 --bg 即可
python scripts/mt5_cli_backtest.py --background --strategy v99g1 --symbol XAUUSDm --days 30
python scripts/mt5_cli_backtest.py --bg --strategies v99g1,v99j1 --symbols all --days 90

# 不加则保持原有前台模式（窗口弹出）
python scripts/mt5_cli_backtest.py --strategy v99g1 --symbol XAUUSDm --days 30
```

## 原理

使用Wine虚拟桌面功能，MT5 GUI渲染到一个不可见的Wine容器中：

```
前台模式: wine terminal64.exe /config:backtest.ini
后台模式: wine explorer /desktop=backtest,800x600 terminal64.exe /config:backtest.ini
```

### 进程流程

```
启动:
  wine explorer /desktop=backtest,800x600 terminal64.exe /config:...
  ├── explorer.exe (虚拟桌面管理器，不会自动退出)
  └── terminal64.exe (MT5主进程)
      └── metatester64.exe (实际计算Agent)

等待:
  监控 terminal64.exe/metatester64.exe 进程退出
  （不监控explorer.exe — 它是桌面管理器永远不退出）

清理:
  pkill terminal64/metatester64/explorer
  wineserver -k (杀掉完整Wine进程树)
```

## 性能

| 模式 | XAU 7天 | XAU 180天 |
|------|---------|----------|
| 前台 | ~30s | ~3min |
| 后台 | ~30s | ~3min |

无性能损失。虚拟桌面只影响GUI渲染目标，不影响计算。

## 注意事项

1. **仅macOS/Wine版支持** — Windows版已有`CREATE_NO_WINDOW`但MT5仍弹窗，需另外方案
2. **explorer孤儿进程** — `kill_mt5()`已包含`pkill explorer.exe /desktop` + `wineserver -k`
3. **首次运行需tick数据** — 如果缓存为空，后台模式仍需连网下载tick数据（通过代理）
4. **`--background`不显示在`--help`中** — 因为是Wine专属参数，在argparse之前手动消费

## Windows后台方案（待实现）

```python
# STARTUPINFO隐藏窗口
si = subprocess.STARTUPINFO()
si.dwFlags = subprocess.STARTF_USESHOWWINDOW
si.wShowWindow = 0  # SW_HIDE
proc = subprocess.Popen(cmd, startupinfo=si)
```

需实测MT5是否会在启动后自行`ShowWindow(SW_SHOW)`覆盖。
