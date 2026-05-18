# WaiTrade2 使用指南

## 1. 环境准备

### macOS + Wine

MetaTrader 5.app 自带Wine环境，无需单独安装。

```bash
# 确认Wine可用
'/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine' --version
```

### Python (macOS端)

Python 3.10+ 用于运行回测/编译等脚本。

```bash
pip install pyyaml
```

### Wine Python + MetaTrader5包 (Live专用)

Live交易需要在Wine环境内安装Python和MetaTrader5包：

```bash
# Wine内Python路径
export WINEPREFIX="$HOME/Library/Application Support/net.metaquotes.wine.metatrader5"
export WINE='/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine'
$WINE "C:\Python\python.exe" -m pip install MetaTrader5
```

### MT5首次登录

首次连接需通过GUI操作：
1. 打开MetaTrader 5.app
2. 文件 -> 登录交易账户
3. 输入账号密码，配置代理服务器（如需要）
4. 登录成功后，后续脚本可自动连接

## 2. 项目结构

```
WaiTrade2/
├── config/
│   └── strategies.yaml      # 策略配置
├── mql5/
│   ├── Experts/             # EA源码 (.mq5)
│   └── Include/             # 公共头文件 (.mqh)
├── scripts/
│   ├── mt5_backtest.py      # 回测脚本
│   ├── mt5_compile.py       # EA编译
│   └── mt5_live.py          # Live交易
├── reports/                 # 回测报告输出
├── logs/                    # 运行日志
└── docs/
    └── USAGE.md
```

## 3. 策略配置

配置文件：`config/strategies.yaml`

```yaml
strategies:
  WaiTrade_OB:
    versions:
      v1:
        ea_path: WaiTrade2/WaiTrade_OB
        params:
          LotSize: 0.1
          StopLoss: 50
          TakeProfit: 100
      v2:
        ea_path: WaiTrade2/WaiTrade_OB
        params:
          LotSize: 0.2
          StopLoss: 40
          TakeProfit: 80
```

添加新策略版本：在对应策略下新增版本节点，指定EA路径和参数即可。

## 4. 回测

### 单品种回测

```bash
python scripts/mt5_backtest.py --strategy WaiTrade_OB --version v1 --symbol EURUSD --period H1 --from 2024.01.01 --to 2024.12.31
```

### 多品种回测

```bash
python scripts/mt5_backtest.py --strategy WaiTrade_OB --version v1 --symbols EURUSD,GBPUSD,USDJPY --period H1 --from 2024.01.01 --to 2024.12.31
```

### 多策略批量回测

```bash
python scripts/mt5_backtest.py --all --period H1 --from 2024.01.01 --to 2024.12.31
```

### 报告解读

回测报告输出到 `reports/` 目录，包含：
- 净利润、最大回撤、胜率
- 盈亏比、夏普率
- 逐笔交易记录

## 5. Live交易

### 启动

```bash
python scripts/mt5_live.py start --strategy WaiTrade_OB --version v1 --symbol EURUSD
```

### 查看状态

```bash
python scripts/mt5_live.py status
```

### 停止

```bash
python scripts/mt5_live.py stop --strategy WaiTrade_OB
```

### 日志位置

```
logs/live_WaiTrade_OB_EURUSD.log
```

## 6. EA编译

### 编译单个EA

```bash
python scripts/mt5_compile.py WaiTrade2/WaiTrade_OB
```

### 编译所有EA

```bash
python scripts/mt5_compile.py --all
```

### 源码同步说明

编译时自动执行：
1. 将 `mql5/Experts/` 和 `mql5/Include/` 同步到MT5 Main目录
2. 调用 metaeditor64.exe 编译
3. 将编译产物 (.ex5) 同步到MT5 Tester目录

只同步 `.mq5` 和 `.mqh` 文件，不影响MT5目录中的其他文件。

## 7. 常见问题

### Wine路径空格问题

MT5安装路径包含空格（`Program Files`），传递给Wine时需确保正确引用：

```python
# 正确：用列表传参，subprocess自动处理空格
cmd = [WINE, METAEDITOR, f'/compile:{win_path}', '/log']
subprocess.run(cmd, ...)

# 错误：拼字符串会导致路径断裂
os.system(f'{WINE} {METAEDITOR} ...')  # 不要这样做
```

### Agent日志UTF-16LE编码

MT5生成的日志文件使用UTF-16LE编码：

```python
with open(log_path, encoding='utf-16-le', errors='replace') as f:
    content = f.read()
```

### MT5代理配置

如果网络需要代理，在MT5 GUI中配置：
- 工具 -> 选项 -> 服务器
- 启用代理并填写地址/端口
- 代理设置保存在MT5配置中，脚本无需额外处理

### 进程冲突 (Main vs Tester)

MT5 Main实例和Tester实例可能冲突：
- 回测使用Tester实例（独立进程）
- Live交易使用Main实例
- 两者可同时运行，但不要同时对同一EA进行编译和回测
- 如遇锁文件错误，先关闭所有MT5进程再重试

```bash
# 查看MT5相关进程
ps aux | grep -i metatrader

# 强制关闭所有MT5进程（谨慎使用）
pkill -f metatrader
```
