# CLAUDE.md

WaiTrade2 是 Windows MT5 量化工具链：参数化 OB/SMC EA、MT5 CLI 回测、Live 部署与策略迭代。

## 铁律（不可违反）

1. 全程中文交流；代码注释和 git 提交信息也尽量中文。
2. 所有 SMC/ICT 策略概念统一用中文表示（订单块=OB、流动性扫损=sweep、结构突破等）。
3. "回测"只指 MT5 Strategy Tester CLI（`terminal64.exe /config:`）；Python 只能称为模拟。
4. 默认初始资金 `$200`；MT5 可信标准是 **Model 4 / Real Ticks**。Model 0 = 幻觉。
5. 回测命令优先 `--background --brief`；禁止整份读取原始 Agent 日志。
6. 默认只推送 WaiTrade2：`git@github.com:nnasterw/WaiTrade2.git`。
7. 不 revert 用户或他人改动；不提交大数据文件。
8. **回测前必须先跑策略检查**：`python scripts/check_strategy_consistency.py <策略名>`，无 ERROR 才可回测。
9. **回测 BarTF 必须匹配 Live BarTF**：`Period=` 由策略 `bar_period_min`/`bar_tf` 自动推导，禁用人工覆盖。
10. **编译后必须部署.ex5到MT5数据目录**：`metaeditor64.exe` 输出.ex5到项目目录，但 `terminal64.exe` 回测从 `%APPDATA%/MetaQuotes/Terminal/.../MQL5/Experts/` 加载。编译后必须 `cp project/ex5 → MT5_DATA/ex5`，否则回测用的是旧版！（2026-06-07血训：11轮220+次回测因未部署.ex5而全部测试旧代码）
11. **Live 必须开启 `InpEnableEntryDebug=true`**；出场诊断仅调试时临时开。
11. **禁止 Live 热替换策略版本**（共享 OB 缓存 → 行为不可预测）；换版本必须重启 EA。
12. **部署后必须验证 EA 日志**：确认 `InpVersion` 匹配、无 `.set` 加载错误、`Magic` 唯一。
13. 重大发现/事故必须更新策略迭代规范：`research/notes/2026-06-02_strategy_iteration_spec.md`。

## 项目结构

```
temp/
├── mt5_portable_xau_zd_qs/     # XAU Live (QS趋势 + ZD振荡)
├── mt5_portable_v11a/          # BTC 7流组合 Live
└── mt5_portable_bt/            # 日常隔离回测 (不影响Live)
mql5/
├── Experts/WaiTrade2/           # EA 主入口 WaiTrade_OB.mq5
├── Include/WaiTrade2/           # 13个.mqh模块 (Config/Signal/Position等)
└── Presets/                     # 848个活跃策略 .set 文件
scripts/                         # 47个 Python 工具脚本
config/
├── strategies.yaml              # 策略定义 (YAML锚点继承)
└── portfolio_schedules.yaml     # 投资组合调度
results/
├── backtest/                    # 回测结果 (.txt/.csv)
└── live/                        # Live 部署记录
research/notes/                  # 策略研究笔记 (76篇)
```

## Live 部署（Exness-MT5Trial5, 账号 277656700）

| 腿 | 终端 | 品种/TF | 策略版本 | Magic | 风险 |
|----|------|---------|----------|-------|:---:|
| QS | `temp/...QS/` | XAUUSDm M1 | V11XAU-QS3 | 204897 | 1.5% |
| ZD | `temp/...ZD/` | XAUUSDm M3 | V11XAU-ZD | 204558 | 2% |

**当前 QS3 参数（720d 最优）**：BE=0.5/0.4, SL buffer=0.3 ATR, 无 VSL。
QS3 v1 是已验证的 720d 最优配置（$282,617），改动 BE 或启用 VSL 均会降低长期收益。

## 常用命令

```bash
# 编译 + 自动部署到D:盘 + 项目目录
python scripts/compile_and_deploy.py

# 生成 .set
python scripts/yaml_to_set.py v11xau-qs3 -o mql5/Presets/v11xau-qs3.set
python scripts/yaml_to_set.py --all

# 策略一致性检查（回测前必跑）
python scripts/check_strategy_consistency.py v11xau-qs3
python scripts/check_strategy_consistency.py --brief

# MT5 回测 — D:盘便携终端（推荐, 所有数据在D:）
export MT5_HOME="D:/Code/codexProject/WaiTrade2/temp/mt5_portable_xau"
python scripts/mt5_backtest_win.py --strategy v11xau-qs3 --symbol XAUUSDm --days 30
python scripts/mt5_backtest_win.py --strategy v11xau-qs3 --symbol XAUUSDm --from 2024.06.08 --to 2026.06.01

# MT5 回测 — C:盘已安装终端（兜底, 需Exness在线）
python scripts/mt5_backtest_win.py --strategy v11xau-qs3 --symbol XAUUSDm --days 30

# MT5 回测（macOS Wine）
python scripts/mt5_cli_backtest.py --background --brief --strategy v11xau-qs3 --symbol XAUUSDm --days 30

# 低 token 分析
python scripts/backtest_digest.py --report results/backtest/xxx.txt --brief
python scripts/backtest_digest.py --report results/backtest/xxx.txt --export-csv --brief
python scripts/trade_cluster_summary.py --csv results/backtest/xxx.trades.csv --top 8

# 测试
python -m pytest tests/ -q --ignore=tests/test_token_efficient_outputs.py
```

依赖：`pip install pyyaml pytest`。注意 Python 3.8 兼容性（不支持 `list[str]` 语法、f-string 内不支持反斜杠）。

## 关键路径

- 策略配置：`config/strategies.yaml`
- YAML→SET 映射：`scripts/yaml_to_set.py` 的 `FLAT_MAP`
- 回测脚本：`scripts/mt5_backtest_win.py`（主）、`scripts/mt5_cli_backtest.py`（macOS Wine）
- EA 源码：`mql5/Experts/WaiTrade2/WaiTrade_OB.mq5` + `mql5/Include/WaiTrade2/*.mqh`
- 策略检查：`scripts/check_strategy_consistency.py`
- 迭代规范：`research/notes/2026-06-02_strategy_iteration_spec.md`
- VSL 诊断：`research/notes/2026-06-02_vsl_diagnosis_journal.md`
- **D:盘便携回测终端**：`temp/mt5_portable_xau/`（1.4G, 含完整tick数据+会话缓存）
  - 设置 `$MT5_HOME` 后自动路由
  - `bt_shared.py` 支持 `$MT5_HOME`/`$MT5_DATA` 环境变量
  - 编译部署：`python scripts/compile_and_deploy.py`
  - **注意**：需要 Exness 在线连接才能跑 Model 4 回测；断开时 fallback 到 Model 0
- **D:盘 Live 终端**：`temp/mt5_portable_v11a/`（BTC）、`temp/mt5_portable_xau_zd_qs/`（XAU）

## 工作流

```text
strategies.yaml → check_strategy_consistency.py（必跑）
  → yaml_to_set.py → mql5/Presets/*.set
  → mt5_backtest_win.py → MT5 terminal64.exe /config:
  → results/backtest/*.txt → backtest_digest.py
```

`WaiTrade_OB.mq5` tick 流程：ATR/行情 → OB检测 → 市场状态 → OB更新 → 信号扫描 → 入场 → 持仓同步 → 持仓管理。

## 改参数同步

新增 EA input 必须同步 5 个文件：

1. `mql5/Include/WaiTrade2/Config.mqh` — input 变量声明 + 访问器函数
2. `scripts/yaml_to_set.py` 的 `FLAT_MAP` — YAML key → InpXxx 映射
3. `config/strategies.yaml` 的 `defaults` — 默认值
4. `tests/test_mt5_common.py` — 测试用例
5. 编译验证（Windows 下需手动用 metaeditor64.exe 编译）

每个 `.set` 必须显式写入所有 input；`InpBarTF` 用数字：`1=M1, 5=M5, 60=H1`。

## Live 参数安全边界（$200 账户）

| 参数 | 上限 | 原因 |
|------|:---:|------|
| `max_lot_size` | 0.1 | $200 账户 0.1 手 XAU ≈ $450 风险 |
| `max_pos_mult` | 5.0 | 防深度入场 boost 失控 |
| `max_concurrent` | 5 | 同时持仓不超 5 单 |
| `max_entries_per_ob` | 5 | 同一 OB 最多 5 次入场 |
| `ob_reentry_cooldown_min` | ≥3 | 至少 3 分钟冷却 |
| `cooldown_bars` | ≥1 | 至少 1 根 K 线全局冷却 |

## Live 部署检查清单

- [ ] EA 编译 0 errors 0 warnings
- [ ] 720 天回测通过（Model 4, Real Ticks）
- [ ] 回测 `Period=` 匹配策略 `bar_tf`
- [ ] `.set` 文件在 MT5 可访问路径
- [ ] `startup.ini` 指向正确的 `.set` 文件名
- [ ] EA 启动后检查日志：`InpVersion` 匹配、无 `.set` 加载错误码 [2]、`Magic` 唯一
- [ ] `InpEnableEntryDebug=true` 已开启
- [ ] 多实例 terminal64.exe 各自独立复制
- [ ] 禁止 Live 热替换策略版本（必须重启 EA）

## VSL 诊断结论（2026-06-02）

经过 5 版 VSL 迭代（券商 SL → lot 修复 → K 线收盘 → 秒级确认 → BE 互杀），结论：

1. **BE=0.5/0.4 是 720d 最优**——BE 锁是"亏损转换器"（-1R→+0.4R），关闭会破坏复利（$282K→$124K）
2. **VSL_5s（秒级确认）是唯一有效 VSL**——720d $224K（v1 的 79%），但 $200 账户 lot 已最小化，TP 补偿不生效
3. **VSL+BE 互杀**——VSL 救活的交易被 BE 锁在 0.4R 立即又杀掉
4. **改进方向在入口质量，不在出口机制**——VSL/分级 BE/软止损均无法超越 v1
5. VSL 基础设施保留在代码中（`CheckVirtualSLBreach`、`InpVirtualSLBreachSec` 等），等账户规模增长后可重新评估

## 高危坑

- **回测 Period ≠ Live BarTF**：回测脚本必须从策略取 Period，禁止硬编码。
- **.set 加载失败 → EA 默认参数裸奔**：部署后必须检查日志确认 InpVersion。
- **不同版本热替换**：共享 OB 缓存 + 不同参数 → 必须重启。
- **多实例 terminal64.exe**：同一 exe 只能一个 /portable 实例。
- **代码未编译进 .ex5 就测试**——所有"结果"都是幻觉。必须确认 .ex5 包含新函数。
- BTC 百分比限价容差失真 → 用 spread 相关绝对容差。
- Model 0 幻觉严重；Real Ticks 才可信。
- M1 小 risk 易被 spread 杀死；BE 太近被 tick 噪音秒扫。
- Trail 过早截断大赢；简单 BE + DTP 常更稳。
- OB 核心区间用实体，不用影线。
- 负余额解析必须支持负号。
- 小资金参数失控：`max_pos_mult=200` + boost → 仓位瞬间 x2.6。
- Python 3.8：不支持 `list[str]` 语法、f-string 内反斜杠、`date | None` 联合类型。
