# 2026-05-23: V11 Round66/67 sweep 上下文过滤与隔离

## 背景

Round65 显示 R45/R65 的高频来源主要来自 loose sweep 支路，但直接混入 R63 主腿会污染账户路径：好窗口可以接近日均 8，但坏窗口 `2026-01~03` 仍低于 R63，并且好窗口也出现 stopout/路径问题。因此本轮新增 sweep-only 上下文过滤，先用分段窗口验证，不进入 720 天全窗。

## 新增参数

新增参数默认关闭，不改变旧策略行为：

- `sweep_allow_hours` / `InpSweepAllowHours`：仅允许指定小时的 sweep。
- `sweep_no_hours` / `InpSweepNoHours`：禁止指定小时的 sweep。
- `sweep_bad_risk_min/max/mult` / `InpSweepBadRisk*`：只对 sweep 的风险区间降权或过滤。

同步位置：

- `mql5/Include/WaiTrade2/Config.mqh`
- `mql5/Include/WaiTrade2/SignalEngine.mqh`
- `scripts/yaml_to_set.py`
- `config/strategies.yaml` defaults
- `tests/test_mt5_common.py`

验证：

- `python -m pytest tests/test_mt5_common.py -q`：68 passed。
- MetaEditor 编译：0 errors / 0 warnings。
- `python scripts/yaml_to_set.py --all`：可生成 R66/R67 preset。

## 分段结果

| 策略 | 思路 | 2025-08~12 交易/日均/PF/余额 | 2026-01~03 交易/日均/PF/余额 | 结论 |
|---|---|---|---|---|
| `v11_r66_j2_swp_hour_only` | R65 loose sweep，只允许 12/13/14/15/20/23 点 | 521 / 3.4 / 0.96 / -$320.68 | 未跑 | allowlist 过度砍频且亏损 |
| `v11_r66_j2_swp_hour_risk` | hour_only + risk150-200 降到0.35 | 516 / 3.4 / 0.91 / -$317.49 | 未跑 | 风险软切无帮助 |
| `v11_r66_j2_swp_no_weak_hours` | R65 loose sweep，禁 0/8/10 点 | 1762 / 11.6 / 0.87 / $3856.99 | 227 / 2.6 / 0.62 / $105.94 | 保频但坏窗口仍差，低于 R63 的 $156.35 |
| `v11_r67_j2_swp_only_no_weak_hours` | R66 no_weak_hours + `liquidity_sweep_only=true` | 557 / 3.7 / 1.42 / $426.82 | 未跑 | sweep 单独不提供高频/高利润，不值得继续 |

## 结论

- “只保留 digest 中看起来好的小时”是假设失败：交易数从 R65/R66 混合版的高频状态砍到约 3.4 单/日，并且好窗口直接亏损。
- “去掉明显弱小时 0/8/10”能保留频率，好窗口达到 11.6 单/日，但坏窗口完全复现 R65 loose001 的弱结果（227 单、$105.94），没有修复 `2026-01~03`。
- sweep-only 隔离显示：关闭常规 OB 后，好窗口只剩 557 单、日均 3.7、余额 $426.82；说明 R66 的高频和利润不是 sweep 独立贡献，而是常规 OB + sweep 混合路径共同形成。
- R66/R67 均不进入 720 天全窗。继续在 sweep 小时上雕刻收益很低；更可能的方向是识别“坏环境下主 OB 天然失效”的 regime，而不是把 sweep 当作独立补频源。

## 工具链发现

Windows Tester 当天日志超过 1.3GB，`mt5_backtest_win.py` / `backtest_digest.py` 的整日志读取会造成每次解析 2.5GB+ 内存峰值。后续继续实验前，应优先做本次运行日志偏移或流式解析，否则反馈环会被日志 IO 拖慢。

## 2026-05-23 后续：日志反馈环修复与 Round68

### 反馈环修复

为避免 Windows 回测每轮解析 1.3GB+ 当天日志，已增强反馈环：

- `scripts/mt5_backtest_win.py`：启动 MT5 前记录 Tester 日志 offset，MT5 结束后优先只解析本次新增日志段；匹配失败时再回退整日志解析。
- `scripts/backtest_digest.py`：新增 `--log-tail-mb N`，可只读取日志末尾 N MB；同时修复 UTF-16LE 尾部读取时被 UTF-8 误解码成空字节乱码的问题。
- 测试：`python -m pytest tests/test_mt5_common.py -q`，70 passed。
- 实测：`v11_r63_j2_shallow_g30neg` 的 `2026.03.01~2026.03.08` 小窗口，MT5 12s、总命令 18s 完成；digest 使用 `--log-tail-mb 128` 在约 4s 内完成逐单匹配。

### Round68

基于 `v11_r63_j2_shallow_g30neg`，只禁用 sweep 的坏小时，不影响常规 OB：

- `v11_r68_j2_r63_no_swp_12_13_14_23`
- 参数：`sweep_no_hours: "12,13,14,23"`

分段结果：

| 策略 | 窗口 | 交易 | 日均 | 胜率 | PF | 余额 | 结论 |
|---|---|---:|---:|---:|---:|---:|---|
| `v11_r63_j2_shallow_g30neg` | 2026-01~03 | 183 | 2.1 | 约42% | 0.77 | $156.35 | 对照 |
| `v11_r68_j2_r63_no_swp_12_13_14_23` | 2026-01~03 | 102 | 1.1 | 40.2% | 0.79 | $111.46 | 失败，低于 R63 |

Digest 结论：

- R68 虽然减少了 sweep 交易，但坏窗口并未改善，反而从 $156.35 降到 $111.46。
- 亏损主体转移到常规 OB：`sig:ob` 75 笔，净 -10.90R；`sig:sweep` 27 笔，净 -1.25R。
- 主要坏簇包括 `sig:ob | hour:15 | risk:400+ | cp:-1.5~-1.0 | exit:sl`，以及 `hour:15`、`risk:150-200`、`cp:<=-1.5` 等。
- 结论：坏窗口不是“少数 sweep 小时”问题，而是整体 market regime 下 OB/sweep 都容易退化。下一步应做 regime/context guard，而不是继续按 sweep 小时硬过滤。
