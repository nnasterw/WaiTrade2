# AGENTS.md

WaiTrade2 是 macOS/Windows 双平台 MT5 量化工具链：参数化 OB/SMC EA、MT5 CLI 回测、Live 部署与策略迭代。

## 必守规则

- 全程中文交流；代码注释和 git 提交信息也尽量中文。
- 所有smc等策略相关概念，统一用中文表示
- “回测”只指 MT5 Strategy Tester CLI：`terminal64.exe /config:`；Python 只能称为模拟。
- 默认初始资金 `$200`；MT5 可信标准是 Model 4 / Real Ticks。
- 回测命令优先 `--background --brief`；禁止整份读取原始 Agent 日志。
- 默认只推送 WaiTrade2：`git@github.com:nnasterw/WaiTrade2.git`。
- 一个 MT5 账号只能部署一个 EA；多品种/多腿组合必须在同一 EA 配置内用 profile/selector 实现。
- 不 revert 用户或他人改动；不提交大数据文件。

## 常用命令

```bash
# 编译 / 生成 set
python3 scripts/mt5_compile.py WaiTrade2/WaiTrade_OB
python3 scripts/yaml_to_set.py --all

# MT5 回测
python3 scripts/mt5_cli_backtest.py --background --brief --strategy v11_single_selector --symbol XAUUSDm --days 30
python3 scripts/mt5_cli_backtest.py --background --brief --strategies s1,s2 --symbol XAUUSDm --from 2025.04.01 --to 2025.05.01
python3 scripts/mt5_backtest_win.py --strategy v11_single_selector --symbol XAUUSDm --days 30

# Live
python3 scripts/mt5_live_runner.py --strategy v11_single_selector --symbols XAUUSDm,BTCUSDm
python3 scripts/mt5_live_runner.py --status

# 低 token 分析
python3 scripts/backtest_digest.py --report results/backtest/xxx.txt --brief
python3 scripts/backtest_digest.py --report results/backtest/xxx.txt --export-csv --brief
python3 scripts/trade_cluster_summary.py --csv results/backtest/xxx.trades.csv --top 8

# 测试
python3 -m pytest tests/ -q
```

依赖：`pip install pyyaml pytest`。

## 关键路径

- 策略配置：`config/strategies.yaml`
- YAML 映射：`scripts/yaml_to_set.py`
- 回测脚本：`scripts/mt5_cli_backtest.py`、`scripts/mt5_backtest_win.py`
- EA：`mql5/Experts/WaiTrade2/WaiTrade_OB.mq5`、`mql5/Include/WaiTrade2/*.mqh`
- 结果与记录：`results/backtest/`、`research/notes/`

## 工作流

```text
config/strategies.yaml -> yaml_to_set.py -> mql5/Presets/*.set
  -> mt5_cli_backtest.py / mt5_backtest_win.py
  -> MT5 terminal64.exe /config:
  -> results/backtest/*.txt + digest/trades.csv
```

`WaiTrade_OB.mq5` tick 流程：ATR/行情 -> OB检测 -> 市场状态 -> OB更新 -> 信号扫描 -> 入场 -> 持仓同步 -> 持仓管理。

## 改参数同步

新增或修改 EA input 必须同步：

1. `mql5/Include/WaiTrade2/Config.mqh`
2. `scripts/yaml_to_set.py` 的 `FLAT_MAP`
3. `config/strategies.yaml` 的 `defaults`
4. 对应测试，通常是 `tests/test_mt5_common.py`
5. 编译验证：`python3 scripts/mt5_compile.py WaiTrade2/WaiTrade_OB`

每个 `.set` 必须显式写入所有 input；`InpBarTF` 用数字：`1=M1, 5=M5, 60=H1`。

## 回测纪律

- **铁律：回测 BarTF 必须匹配 Live BarTF**。回测 `Period=` 由策略 `bar_period_min`/`bar_tf` 自动推导，禁用人工覆盖。
- 先用 `backtest_digest.py`、`backtest_ledger.py` 或 `trade_cluster_summary.py` 提炼日志。
- 关键结果单独复跑，并校验品种、日期、策略版本标记、**BarTF**。
- macOS MT5 `/config:` 路径必须使用 Windows 反斜杠。
- 回测和 Live 的入场价、offset、SL、TP、DTP、timeout、并发、cooldown、去重逻辑必须等效。

## 策略纪律

- 新策略写入 `config/strategies.yaml` 并用 MT5 CLI 验证。
- 重大结论写入 `research/notes/`。
- **策略迭代规范**：`research/notes/2026-06-02_strategy_iteration_spec.md` — 部署前必读。
- 不信任 WR > 80% 的异常结果，必须查成交假设、缓存、日志匹配和日期窗口。
- 不做具体月份过滤作为最终通用策略；月份只能用于诊断。
- XAU/BTC 分开调参；加密通常需要更大 SL、timeout、BE、DTP 尺度。

### Live 参数安全边界（$200 账户）

| 参数 | 上限 | 原因 |
|------|:---:|------|
| `max_lot_size` | 0.1 | $200 账户 0.1 手 XAU ≈ $450 风险 |
| `max_pos_mult` | 5.0 | 防深度入场 boost 失控 |
| `max_concurrent` | 5 | 同时持仓不超 5 单 |
| `max_entries_per_ob` | 5 | 同一 OB 最多 5 次入场 |
| `ob_reentry_cooldown_min` | ≥3 | 至少 3 分钟冷却 |
| `cooldown_bars` | ≥1 | 至少 1 根 K 线全局冷却 |

### Live 部署检查清单

- [ ] EA 编译 0 errors 0 warnings
- [ ] 720 天回测通过（Model 4, Real Ticks）
- [ ] 回测 `Period=` 匹配策略 `bar_tf`（不等于 Live BarTF = 致命 Bug）
- [ ] `.set` 文件在 MT5 可访问路径
- [ ] `startup.ini` 指向正确的 `.set` 文件名
- [ ] EA 启动后检查日志 `InpVersion` 匹配预期
- [ ] `InpEnableEntryDebug=true` 已开启
- [ ] 禁止 Live 热替换策略版本（必须重启 EA）

## 高危坑

- BTC 百分比限价容差会失真，应使用 spread 相关绝对容差。
- Model 0 幻觉严重；Real Ticks 才可信。
- M1 小 risk 容易被 spread 杀死；BE 太近会被 tick 噪音秒扫。
- Trail 过早会截断大赢；简单 BE + DTP 常更稳。
- OB 核心区间用实体，不用影线。
- 负余额解析必须支持负号。
