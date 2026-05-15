# Handoff: WaiTrade2 策略进化全景

**日期**: 2026-05-15
**仓库**: `git@github.com:nnasterw/WaiTrade2.git` (main)
**工作目录**: `/Users/wen/Projects/ClaudeCode/WaiTrade2`

---

## 项目结构

```
WaiTrade2/
├── config/strategies.yaml       ← 所有策略参数
├── mql5/                        ← 当前EA源码（WaiTrade2版）
├── mql5_original/               ← 原始盈利EA源码备份（Trade版）
├── scripts/
│   ├── mt5_cli_backtest.py      ← macOS Wine回测管理器
│   ├── mt5_compile.py           ← EA编译器
│   ├── mt5_live_runner.py       ← Live EA部署
│   ├── yaml_to_set.py           ← YAML→.set参数转换
│   └── mt5_common.py            ← 共享模块
├── strategy_versions/           ← 策略文档
├── results/backtest/            ← 回测报告
└── CLAUDE.md                    ← 项目完整指引
```

## 两个EA版本

| | Trade版（正确） | WaiTrade2版（信号问题） |
|---|---|---|
| **源码** | `mql5_original/` | `mql5/` |
| **.ex5** | ~68KB | ~45KB |
| **架构** | EntryEngine状态机 | SignalEngine直接判定 |
| **Real Ticks** | 142笔/49%WR | 360笔/47%WR |

**回测和Live应使用同一个Trade版EA(.ex5)**。

## 回测流水线关键点

- **Model 4 (Real Ticks)** — 唯一标准
- **bars=300** — 从5000优化，不影响结果
- **terminal.ini日期缓存** — 必须patch_terminal_ini_dates()覆盖
- **kill_mt5()** — 必须先关GUI再启动/config:
- **编译路径**: `Z:\tmp\...\WaiTrade_OB.mq5` + WaiTrade/子目录
- **ModifySL修复**: 跳过新旧SL相同的修改（否则311MB日志）
- **每tick CopyRates** — 和Live对齐，不用static缓存

## 策略进化

```
v9.5c → v9.6b → v9.7a → v9.8 → v9.7b(ExpX) ← 当前最优
```

### v97b (ExpX定版) — Real Ticks唯一盈利策略

```
30天: 8笔 | 62.5%WR | 盈亏比2.64 | $200→$221 (+10.5%)
```

核心: min_score=4 + bounce=60% + 并发1 + DTP 3.0R + 势态过滤

### 关键认知

1. Model 0回测不可信（低spread幻觉）
2. Real Ticks下只有低频大R能盈利
3. 盈亏比>2.0是生命线
4. WaiTrade2版EA缺少Trade版的bounce状态机等5个过滤机制

## 下一步

1. 90天+多品种验证v97b
2. bounce 60→50%增加交易量(22笔/月仍盈利)
3. Live部署验证
4. WaiTrade2 EA移植Trade版机制

## 建议技能

- `/wf-improve-strategy` — 策略优化
- `/diagnose` — EA/编译问题
- `/tdd` — 代码移植
