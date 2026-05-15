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

## Project Overview

WaiTrade — MT5/Exness OB回踩自动交易框架。1m/5m Order Block 入场 + trailing止损 + 动态止盈。

## Commands

```bash
# === Live 交易 (V96b) ===
# 单品种
PYTHONUTF8=1 python -u scripts/mt5_demo_trading.py --profile v96b --symbols XAUUSDm --live --loop

# 12品种（V96b标准品种集）
PYTHONUTF8=1 python -u scripts/mt5_demo_trading.py --profile v96b \
  --symbols "XAUUSDm,BTCUSDm,ETHUSDm,AUDUSDm,EURUSDm,GBPUSDm,USDJPYm,USDCHFm,NZDUSDm,USDCADm,GBPJPYm,EURJPYm" \
  --live --loop

# 测试连接（不发单）
PYTHONUTF8=1 python scripts/mt5_demo_trading.py --profile v96b --symbols XAUUSDm --connect-only

# === MT5 Strategy Tester 回测 ===
cd D:/Code/codexProject/WaiTrade2/WaiTrade2
python temp/run_backtest.py                          # 单品种快速回测
python scripts/mt5_backtest_win.py --strategy v96b --symbols all --days 30  # 全品种回测

# === Python 模拟 ===
BT_STRATEGIES=v95c python research/tick_backtest_v2_parallel.py
python research/backtest_unified.py
```

## Architecture

```
config/strategies.yaml       ← 策略参数统一定义 (live+回测共用)
src/strategy/                ← 统一策略模块 (live+回测共用)
  ob_signals.py                OB信号生成核心 V7.0-V8.4 (generate_ob_signals_v84)
  engine.py                    策略定义/加载/信号生成/trailing
  data_provider.py             数据源接口 (BacktestDataProvider/LiveDataProvider)
  entry_engine.py              入场状态机 (bounce→confirm→offset guard)
  exit_engine.py               出场逻辑 (SL/trailing/DTP/time_tp)
  position_sizer.py            仓位计算 (min_risk/1H boost/ds加权)
  trade_recorder.py            订单记录 (Backtest内存/Live CSV)
  runner.py                    统一主循环 (逐tick/快速两种模式)
scripts/
  mt5_demo_trading.py          Live执行 (V7+ profiles)
  strategy_v7_v8.py            → shim, re-exports from src/strategy/ob_signals.py
research/
  backtest_unified.py          统一回测入口
  tick_backtest_v2_parallel.py 旧回测 (向量化, 仍可用)
  preprocess_ticks.py          tick预处理
strategy_versions/             各版本规格文档
```

**当前Live: V96b** — M1+二推不破+BE0.2R+DTP1.5R+3xBoost, 12品种
**MT5 Strategy Tester回测** — terminal64.exe /config: 启动, .set文件控制EA参数
**统一Runner回测** — 逐tick模拟, 1s出场采样, 和live完全相同执行路径

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
3. 生成对于版本文件，放在`strategy_versions/`下

### 4. MQL5 Preset规范
- 每个.set文件必须显式设置所有Config.mqh的input参数, 不依赖默认值
- 新增Config参数后, 所有现有.set文件必须补上该参数
- InpBarTF用数字(1=M1, 5=M5), InpVersion用策略名标识

### 5. 大文件禁止提交git
data/cache, data/preprocessed, *.npz, *.parquet → .gitignore
误提交后必须 git reset --soft 重建commit

## 策略配置 (可插拔)

新增策略只需修改 `config/strategies.yaml`:
```bash
BT_STRATEGIES=v95c python research/tick_backtest_v2_parallel.py  # 旧回测
BT_STRATEGY=v95c python research/backtest_unified.py              # 新回测
python scripts/mt5_demo_trading.py --profile v95c --loop          # Live
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
