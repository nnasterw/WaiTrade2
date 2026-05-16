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
WaiTrade_OB.mq5        OnTick 八步编排: ATR→OB检测→市场状态→OB更新→信号扫描→执行入场→持仓同步→持仓管理
  ├── Config.mqh       58个 input 参数，完全参数化，无硬编码策略逻辑
  ├── Types.mqh        核心结构: OBZone, TradeSignal, PosTrack, EAState(含market_state/target_price)
  ├── Utils.mqh        转发头文件，包含以下三个子模块:
  │   ├── MathUtils.mqh     纯计算: CalcATR, PriceToR, RToPrice, GetWorkTF
  │   ├── TradeOps.mqh      MT5交易: CalcLotSize, GetSpread, ModifySL(重试), ClosePosition, CountPositions
  │   └── BarTracker.mqh    新bar检测: IsNewBar
  ├── MarketState.mqh  [v9.8势] M15 swing HH/HL结构→趋势/震荡判定 + 对面swing目标位
  ├── ScoreEngine.mqh  [v9.8位] 6项评分(动能/初期/空间/共振/接近/确认)→仓位乘数映射
  ├── DecayDetector.mqh [v9.8动] M1动能衰减(3bar二推不破/吞没+追随)→直接平仓
  ├── OBDetector.mqh   OB检测+生命周期: 检测/评分/合并/状态更新/MarkZoneUsed/Update1HAlignment
  ├── SignalEngine.mqh 入场信号: 态过滤→链式过滤器→评分系统→震荡态swing TP
  └── PositionManager.mqh 持仓管理: 态感知BE/DTP参数→保本→追踪→DTP→动能衰减→超时
```

**8-Gap 信号质量修复（内置于OBDetector/SignalEngine）**:
1. OB用K线实体(open/close)，不含影线
2. Displacement需突破前3根高/低点
3. K线实体占比>=50%
4. 23:00-06:00不建OB
5. strength<0.5不入场
6. 动态TTL
7. risk>3×ATR不入场
8. 逆势+risk>1.5ATR不入场

**EntryEngine 状态机（v99核心入场逻辑）**:
触及OB → 等bounce(ob_height×bounce_pct反弹) → offset guard → 入场

**通用化设计原则**: EA代码中零硬编码策略逻辑。所有行为差异完全由 `.set` 文件中的参数决定。新增参数时需同步更新：Config.mqh → yaml_to_set.py FLAT_MAP → strategies.yaml defaults。

### 品种参数矩阵（关键认知）

| 参数 | 贵金属(v99g1) | 加密(v99j1) | 倍数 |
|------|-------------|------------|------|
| 时间框架 | M5 | M30 | 6× |
| SL buffer | 0.10 ATR | 1.50 ATR | 15× |
| BE触发 | 1.0R | 2.0R | 2× |
| DTP触发 | 2.0R | 3.0R | 1.5× |
| timeout | 90min | 720min | 8× |

每个品种需要独立参数。加密需要全方位放大。

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
  test_mt5_common.py     39个pytest: 日志解析/统计/策略解析/报告/参数映射
strategy_versions/       各版本规格文档 (v6.6~v9.9)
mql5_original/           Trade版EA源码备份（参考用）
```

**定版策略: v99g1** (贵金属+外汇 M5) + **v99j1** (加密货币 M30)
**MT5 Strategy Tester回测** — Model 4 (Real Ticks) 唯一标准

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
python scripts/yaml_to_set.py --all                                              # 生成所有.set
python scripts/mt5_cli_backtest.py --strategy v99g1 --symbols XAUUSDm --days 90   # 回测
python scripts/mt5_live_runner.py --strategy v99g1 --symbols XAUUSDm,XAGUSDm,EURUSDm  # Live
python scripts/mt5_live_runner.py --strategy v99j1 --symbols BTCUSDm,ETHUSDm      # 加密Live
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
| **Model 0 幻觉** | Model 0: $121K利润 → Model 4: 亏80%。Real Ticks是唯一可信标准 |
| **M1 spread杀手** | M1 OB risk=3-5pt, spread/risk=6-10% → 结构性亏损。M5=1.5%, M30=5% |
| **负余额解析bug** | 正则不匹配负数→爆仓显示$200"持平"。已修复: `-?[\d.]+` |
| **BE绝对距离** | BE0.2R在M1=1pt被tick秒扫。BE1.0R在M5=10pt远超噪音 |
| **Trail伤害大赢** | trail在0.3R退出中断DTP2R+大赢。简单BE+DTP优于复杂trail |
| **OB含影线** | OB用high/low(含影线)→SL设在价格到过的位置→必被刺破。改用实体 |
| **Tester缓存** | 批量回测可能复用缓存结果(显示相同数据)。关键结果需单独跑验证 |

## 当前改进方向

### 已完成 ✅
- 8-Gap 信号质量修复
- EntryEngine tick级bounce确认
- M5/M30 时间框架发现
- v99g1(贵金属$842/+321%) + v99j1(加密$677/+238%)
- 20轮210+策略变体测试

### P0 — Live部署验证
- v99g1 Live: XAU+XAG+EUR
- v99j1 Live: BTC+ETH
- 720天长期验证

### P1 — 更多品种
- GBPJPY (14笔/PF1.84 样本太少)
- USTEC (PF0.99 接近持平)
- SOL (M30/H1 探索)

### P2 — 架构改进
- Trade版EA的Classify分级移植
- Liquidity sweep检测
- 多策略组合运行
