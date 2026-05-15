# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 语言规则（最高优先级）
全程对话和思考必须使用中文。包括：分析报告、任务描述、工具调用前的思考过程、给用户的回复。代码注释和 git 提交信息也尽量用中文。

## 项目概述

WaiTrade2 是一个 macOS/Windows 双平台 MetaTrader 5 量化交易工具链。核心能力：通用化OB(Order Block)策略EA、多版本回测、实盘交易。macOS 端通过 Wine 桥接 MT5，Windows 端原生运行。

## 常用命令

```bash
# 编译EA
python scripts/mt5_compile.py WaiTrade/WaiTrade_OB   # 单个EA
python scripts/mt5_compile.py --all                    # 所有EA

# YAML → .set 文件转换
python scripts/yaml_to_set.py v96b                     # 单个策略输出到stdout
python scripts/yaml_to_set.py --all                    # 所有策略写入 mql5/Presets/

# 回测 (macOS Wine)
python scripts/mt5_cli_backtest.py --strategy v96b --symbol XAUUSDm --days 30
python scripts/mt5_cli_backtest.py --strategy v96b --symbols all --days 60
python scripts/mt5_cli_backtest.py --strategies v95c,v96b --symbol XAUUSDm --days 30

# 回测 (Windows 原生)
python scripts/mt5_backtest_win.py --strategy v96b --symbol XAUUSDm --days 30

# 实盘交易
python scripts/mt5_live_runner.py --strategy v96b --symbols XAUUSDm,BTCUSDm
python scripts/mt5_live_runner.py --status
python scripts/mt5_live_runner.py --stop
```

依赖：`pip install pyyaml`

## 架构

### 数据流

```
config/strategies.yaml  →  yaml_to_set.py  →  .set preset 文件
                        →  mt5_cli_backtest.py  →  .ini + .set → Wine terminal64.exe
                        →  mt5_backtest_win.py  →  .ini + .set → Windows terminal64.exe
                        →  mt5_live_runner.py   →  Wine Python 脚本 → MetaTrader5包
mql5/Experts/*.mq5      →  mt5_compile.py       →  metaeditor64.exe → .ex5
```

### MQL5 EA 模块架构

```
WaiTrade_OB.mq5        OnTick 六步编排: ATR→OB检测→OB更新→信号扫描→执行入场→持仓管理
  ├── Config.mqh       41个 input 参数，完全参数化，无硬编码策略逻辑
  ├── Types.mqh        核心结构: OBZone, TradeSignal, PosTrack, EAState
  ├── Utils.mqh        ATR计算、手数计算、R倍数转换、持仓操作
  ├── OBDetector.mqh   OB检测引擎: impulse判定→强度评分→供需权重→触碰/过期/合并
  ├── SignalEngine.mqh 入场信号: 触碰→过滤→仓位乘数→手数→保证金检查
  └── PositionManager.mqh 持仓管理: 保本→三级追踪→DTP动态止盈→时间退出
```

**通用化设计原则**: EA代码中零硬编码策略逻辑。所有行为差异（从v72a固定手数到v96b全增强）完全由 `.set` 文件中的41个参数决定。新增参数时需同步更新：Config.mqh → yaml_to_set.py FLAT_MAP → strategies.yaml defaults。

### 策略配置 (config/strategies.yaml)

单一 YAML 文件管理所有策略版本(v72a~v96b)、品种列表、回测参数、MT5 账号。策略通过 YAML anchor (`&defaults` / `<<: *defaults`) 继承默认参数。

保留 key（非策略，yaml_to_set --all 会跳过）：`defaults`, `symbols`, `backtest_defaults`, `mt5_account`。

### 参数映射 (scripts/yaml_to_set.py)

`FLAT_MAP` 字典将 YAML key 映射到 MT5 的 `InpXxx` 参数名，`TRAIL_MAP` 处理 `trail_levels` 数组到 `InpTrail{1,2,3}{TriggerR,LockR,LockMult}` 的映射。trail1 没有 LockMult。

### Wine 环境路径

所有 macOS 脚本共享相同的 Wine 路径常量：
- `WINE`: `/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine`
- `WINEPREFIX`: `~/Library/Application Support/net.metaquotes.wine.metatrader5`
- `MT5_MAIN`: Main终端（编译+回测）
- `MT5_TESTER`: Portable副本（实盘专用）

### 策略版本档案

`strategy_versions/` 目录包含 v6.6~v9.5d 的策略文档（回测结果、核心配方、入场/出场逻辑、演进路径）。YAML 中对应版本的参数必须与文档对齐。

## 关键注意事项

- **参数同步**: 新增EA input参数 → 必须同步更新 Config.mqh、yaml_to_set.py FLAT_MAP、strategies.yaml defaults 三处
- **MQL5 数组方向**: `CopyRates` 返回 rates[0]=最旧, rates[count-1]=最新，未使用 `ArraySetAsSeries`
- **Wine路径空格**: 含空格路径（`Program Files`）必须用列表传参给 `subprocess`
- **Agent日志编码**: UTF-16LE，读取时需 `encoding='utf-16-le'`
- **MT5实例隔离**: Main（编译+回测）和 Tester（/portable实盘）是独立进程
- **策略文档对齐**: 修改 YAML 策略参数前先核对 `strategy_versions/` 对应文档
