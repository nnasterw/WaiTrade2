# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 语言规则（最高优先级）
全程对话和思考必须使用中文。包括：分析报告、任务描述、工具调用前的思考过程、给用户的回复。代码注释和 git 提交信息也尽量用中文。

## 默认推送目标
代码改动默认推送到 **WaiTrade2** (`https://github.com/nnasterw/WaiTrade2`)。仅当改动涉及 WaiTrade 项目的核心 live 代码时，同时推送 WaiTrade (`github.com:nnasterw/WaiTrade`)。

## 关键术语
- **"回测"统一指MT5 Strategy Tester CLI回测** (`terminal64.exe /config:` 启动)
- Python回测 (tick_backtest_v2_parallel.py / backtest_unified.py) 称为"Python模拟"，不算回测
- 初始资金 $200，和live账户对齐

## 项目概述

WaiTrade2 是一个 macOS/Windows 双平台 MetaTrader 5 量化交易工具链。核心能力：通用化OB(Order Block)策略EA、多版本回测、实盘交易。macOS 端通过 Wine 桥接 MT5，Windows 端原生运行。

## 常用命令

```bash
# === 编译EA ===
python scripts/mt5_compile.py WaiTrade/WaiTrade_OB   # 单个EA
python scripts/mt5_compile.py --all                    # 所有EA

# === YAML → .set 文件转换 ===
python scripts/yaml_to_set.py v96b                     # 单个策略输出到stdout
python scripts/yaml_to_set.py --all                    # 所有策略写入 mql5/Presets/

# === MT5 Strategy Tester 回测 ===
# macOS Wine
python scripts/mt5_cli_backtest.py --strategy v96b --symbol XAUUSDm --days 30
python scripts/mt5_cli_backtest.py --strategy v96b --symbols all --days 60
python scripts/mt5_cli_backtest.py --strategies v95c,v96b --symbol XAUUSDm --days 30
# Windows 原生
python scripts/mt5_backtest_win.py --strategy v96b --symbol XAUUSDm --days 30
python scripts/mt5_backtest_win.py --strategy v96b --symbols all --days 30

# === EA Live 部署 (macOS Wine) ===
python scripts/mt5_live_runner.py --strategy v96b_live --symbols XAUUSDm,BTCUSDm
python scripts/mt5_live_runner.py --strategy v96b_live --symbols all
python scripts/mt5_live_runner.py --status
python scripts/mt5_live_runner.py --stop

# === 测试 ===
python -m pytest tests/ -v                  # 全部测试
python -m pytest tests/test_mt5_common.py   # 单个文件
```

依赖：`pip install pyyaml pytest`

## 架构

### 数据流

```
config/strategies.yaml  →  yaml_to_set.py  →  .set preset 文件
                        →  mt5_cli_backtest.py  →  .ini + .set → Wine terminal64.exe
                        →  mt5_backtest_win.py  →  .ini + .set → Windows terminal64.exe
                        →  mt5_live_runner.py   →  .chr profile + EA → Wine MT5 终端
mql5/Experts/*.mq5      →  mt5_compile.py       →  metaeditor64.exe → .ex5
```

### MQL5 EA 模块架构

```
WaiTrade_OB.mq5        OnTick 六步编排: ATR→OB检测→OB更新→信号扫描→执行入场→持仓管理
  ├── Config.mqh       41个 input 参数，完全参数化，无硬编码策略逻辑
  ├── Types.mqh        核心结构: OBZone, TradeSignal, PosTrack, EAState
  ├── Utils.mqh        转发头文件，包含以下三个子模块:
  │   ├── MathUtils.mqh   纯计算: CalcATR, PriceToR, RToPrice, GetWorkTF
  │   ├── TradeOps.mqh    MT5交易: CalcLotSize, GetSpread, ModifySL, ClosePosition, CountPositions
  │   └── BarTracker.mqh  新bar检测: IsNewBar
  ├── OBDetector.mqh   OB检测+生命周期: 检测/评分/合并/状态更新/MarkZoneUsed/Update1HAlignment
  ├── SignalEngine.mqh 入场信号: 链式过滤器(IsZoneTouched→DoubleTouchFilter→OffsetGuard→SpreadRatio→MinRisk→CalcEntryLot)
  └── PositionManager.mqh 持仓管理: 保本→三级追踪→DTP动态止盈→时间退出
```

**通用化设计原则**: EA代码中零硬编码策略逻辑。所有行为差异（从v72a固定手数到v96b全增强）完全由 `.set` 文件中的41个参数决定。新增参数时需同步更新：Config.mqh → yaml_to_set.py FLAT_MAP → strategies.yaml defaults。

### Python 脚本模块

```
scripts/
  mt5_common.py          共享模块: 配置加载/策略解析/日志解析/统计计算/报告格式化
  yaml_to_set.py         YAML→.set转换 + NON_STRATEGY_KEYS/FLAT_MAP/TRAIL_MAP 定义
  mt5_compile.py         EA编译: 源码同步→metaeditor64编译→Tester同步
  mt5_cli_backtest.py    macOS Wine 回测 (引用 mt5_common)
  mt5_backtest_win.py    Windows 原生回测 (引用 mt5_common)
  mt5_live_runner.py     EA Live 部署: 生成.chr profile→编译EA→启动Wine MT5终端
tests/
  test_mt5_common.py     纯函数测试 (27 cases): 日志解析/统计/策略解析/报告
strategy_versions/       各版本规格文档 (v6.6~v9.6b)
```

**当前Live: V96b-Live** — V96b参数调优版, EA直接在Wine MT5中运行
**MT5 Strategy Tester回测** — terminal64.exe /config: 启动, .set文件控制EA参数

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

## 核心纪律 (血泪教训)

### 1. 回测必须贴近live，否则毫无意义
- 入场价用实际可执行的价格（confirm_price+spread），不用虚假容差
- 限价单容差不能用百分比（BTC $80k的0.1%=$80，但risk只有$10）
- 出场检查频率和live对齐（1s采样）
- 前瞻偏差: trend_1h shift(1), entry_ns从bar结束开始
- **每次改动必须同时检查回测和live是否对齐**, 不允许只改一侧
- 信号去重: 回测(bar,direction) vs live(ob_key+5min窗口) — 逻辑必须等效
- 出场: 回测ExitEngine和live manage_positions必须用相同的trailing/DTP/time_exit逻辑
- 并发限制: 回测max_concurrent和live position_limit必须同等效果
- 回测默认加 entry_offset_r=0.2 + sl_slippage_mult=1.5 模拟live真实条件
- **回测提速优化禁止偏离live执行路径** — 任何"解耦""近似""跳过"都可能引入系统性偏差
  - 安全: 共享信号生成、跳过无信号空闲tick、Cython编译核心循环
  - 危险: 入场/出场解耦(忽略并发/cooldown路径依赖)、向量化出场(精度损失+两套代码)

### 2. 每次调研结论必须记录
- 调研结论 → `research/notes/` 目录
- 重大发现 → 更新此文件
- 不信任WR>80%的回测 — 必须深究成交假设

### 3. 版本迭代强制检查
新版本上线前必须：
1. `config/strategies.yaml` 添加版本定义
2. 回测验证 (统一Runner逐tick模式)
3. `simulate_live_strategy.py` 更新并PASS
4. 所有信号dict字段有对应的消费代码
5. 不假设"和旧版一样" — 逐项检查
6. 生成对应版本文件，放在`strategy_versions/`下

### 4. MQL5 Preset规范
- 每个.set文件必须显式设置所有Config.mqh的input参数, 不依赖默认值
- 新增Config参数后, 所有现有.set文件必须补上该参数
- InpBarTF用数字(1=M1, 5=M5), InpVersion用策略名标识

### 5. 大文件禁止提交git
data/cache, data/preprocessed, *.npz, *.parquet → .gitignore
误提交后必须 git reset --soft 重建commit

## 关键注意事项

- **参数同步**: 新增EA input参数 → 必须同步更新 Config.mqh、yaml_to_set.py FLAT_MAP、strategies.yaml defaults 三处
- **MQL5 数组方向**: `CopyRates` 返回 rates[0]=最旧, rates[count-1]=最新，未使用 `ArraySetAsSeries`
- **Wine路径空格**: 含空格路径（`Program Files`）必须用列表传参给 `subprocess`
- **Agent日志编码**: UTF-16LE，读取时需 `encoding='utf-16-le'`
- **MT5实例隔离**: Main（编译+回测）和 Tester（/portable实盘）是独立进程
- **策略文档对齐**: 修改 YAML 策略参数前先核对 `strategy_versions/` 对应文档

## 策略配置 (可插拔)

新增策略只需修改 `config/strategies.yaml`:
```bash
python scripts/yaml_to_set.py --all                                    # 生成所有.set
python scripts/mt5_cli_backtest.py --strategy v96b_live --symbols all --days 30  # 回测
python scripts/mt5_live_runner.py --strategy v96b_live --symbols all    # Live部署
```

## 历史教训 (记录防重犯)

| 教训 | 详情 |
|------|------|
| 限价单容差 | 0.1%=BTC$80, 回测WR86%→精确后19%。用spread×N绝对值 |
| post_confirm追价 | 30s后市价offset 20R+, live WR22%。改为confirm入场 |
| pos_mult双重乘 | engine的pos_mult+回测的dt_addon叠加=13.5x。分开处理 |
| time_exit×5 | 固定×5min, 1m策略多算5倍持仓时间。改为×bar_period_min |
| consolidate放宽SL | 合并时SL距离×3=R含义变化。改为只合并仓位不改SL |
| Live主循环300s | 1m策略5分钟才检查一次=错过大量信号。改为1s |
| Live信号重复入场 | executed_keys未更新→同OB无限入场→418单全损。加ob_entered+5min窗口去重 |
| Live并发失效 | SL秒触发→持仓消失→重开。加60s速率限制(最多2次) |
| Live无风险熔断 | 6品种×70次=840%敞口→全损。加session_loss 10%熔断 |
| 快速模式回测对比 | fast模式信号99笔vs tick模式1835笔, 对比结论完全失真。只用tick模式 |
| 回测不模拟live条件 | 理想回测和live差距60%+。加entry_offset_r和sl_slippage_mult |
| **MT5 /config: 反斜杠** | terminal64.exe 的 /config: 参数必须用 Windows 反斜杠(`\`)。正斜杠被解析为命令行开关, 路径截断。用 Python `os.path.join` 天然生成反斜杠 |
| **WaiTrade2 config 错位** | WaiTrade2 的 strategies.yaml 和原始 WaiTrade 是两个独立文件。修改策略参数时必须双项目同步, 否则回测和 live 参数不一致 (上次: time_exit 999 vs 12) |

## 当前改进方向

### P0 — 进行中
- V9.5d策略验证 (A路线: 宽trail+高位75%锁利)
- Live-回测Gap消除 (offset/slippage/去重对齐)
- Live bug修复验证 (OB去重+速率限制+熔断)

### P1 — 待验证
- OB有效性分级 (新生→已验证→强效→衰退)
- 对面OB止盈
- 信号评分系统

### P2 — 探索
- 环境自适应 (ATR比值)
- 失败OB学习
- 金字塔加仓
