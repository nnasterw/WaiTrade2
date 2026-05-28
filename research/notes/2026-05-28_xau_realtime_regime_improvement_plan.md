# 2026-05-28 XAU 实时行情切换改进计划

## 背景

当前目标不是离线挑选每个月的最优腿，而是让同一个 XAU EA 在连续实盘中根据行情实时切换趋势腿/震荡腿，并尽量满足账户余额每月增长 35%。

上一轮 `v11xau1` 的核心问题已经被 2026-04 的 Model4 单月回测复现：

| 策略 | 窗口 | 初始资金 | Model | 余额 | 结论 |
|---|---|---:|---:|---:|---|
| `v11_single_selector` | 2026.04.01~2026.05.01 | 200 | 4 | 307.22 | 达标 |
| `v11xau1` | 2026.04.01~2026.05.01 | 200 | 4 | 217.03 | 不达标 |
| `v11xau_r39_range_lot5` | 2026.04.01~2026.05.01 | 200 | 4 | 218.98 | 不达标 |

这说明 2026-04 不是完全不可交易，而是 `v11xau1` 的实时切换和参数组合没有复刻 `v11_single_selector` 在该月的盈利结构。

## 对当前疑问的修正

### 1. 月初 5 天交易反馈不适合作为实盘切换机制

这个判断是对的。月初 5 天反馈只能作为离线诊断基准，不能作为最终实盘机制，原因：

- 实盘是连续时间序列，不会天然按自然月重启。
- 行情状态可能在月中切换，月初判断会迟钝。
- 交易反馈依赖策略先试错，强趋势可能错过早段，震荡月可能先付出较大探测成本。
- 交易反馈混入了执行质量、点差、持仓管理，不是纯行情状态。

保留方式：月初 5 天 selector 继续作为“对照组”和标签来源，用来训练/验证实时行情分类器，而不是直接部署为实盘规则。

### 2. 实时 HTF 形态应从单条件改为状态机

当前 `UseXAUTrendProfile()` 只看：

- H1 最近 3 根净推进是否超过 `0.45 ATR`
- H4 最近 12 根区间是否超过 `4 ATR`

这太粗，会把“高波动震荡”误判为趋势，也会在短暂冲刺后频繁切换。改进方向是做实时状态机：

| 状态 | 含义 | 默认腿 |
|---|---|---|
| `TREND_STRONG` | 单边推进，回撤浅，突破后延续 | 趋势腿 |
| `TREND_WEAK` | 有推进但效率不足，趋势腿降仓或观望 | 趋势低仓 |
| `RANGE_CLEAN` | 高低点来回、扫流动性后回归 | 震荡腿 |
| `RANGE_NOISY` | 波动大但无方向，坏簇多 | 震荡低仓或禁入 |
| `TRANSITION` | 状态刚切换，信号不稳定 | 暂停/小仓 |

建议新增实时特征，而不是只依赖净推进：

- 趋势效率：`abs(close - open) / sum(abs(bar_close - prev_close))`
- 趋势净推进：H1/H4 多窗口 `net_atr`
- 区间扩张：H4 range ATR，但必须结合趋势效率，否则会误判震荡扩张
- 高低点结构：HH/HL 或 LL/LH 连续性
- 回撤深度：推进后的回撤是否小于某个 ATR 比例
- 突破延续：突破前高/前低后 N 根内是否继续收在突破方向
- 震荡回归：扫高/扫低后是否快速回到区间中位
- 波动噪音：wick 占比、反向 bar 比例、交替方向次数
- 执行环境：spread/risk、滑点 proxy、tick volume 或真实成交量可用性

### 3. 动态窗口缓存是必要的

当前 `Cfg*()` 多处直接调用 `UseXAUTrendProfile()`，会造成几个问题：

- 同一 tick 内不同模块可能重复计算并得到不同结果。
- 入场用趋势参数，后续持仓管理可能又按震荡参数处理。
- `CopyRates()` 高频调用浪费，并增加状态抖动。

建议实现 `XAURegimeCache`：

```text
OnTick
  -> 若新 M1/H1/H4 bar 或缓存过期，更新实时特征
  -> 计算 trend_score / range_score / noise_score
  -> 通过滞后阈值和最短持有时间更新 regime_state
  -> 本 tick 所有 Cfg*() 只读取缓存状态
```

关键参数：

| 参数 | 建议初值 | 说明 |
|---|---:|---|
| `xau_regime_update_tf` | 1 | M1 新 bar 更新一次 |
| `xau_regime_min_hold_bars` | 5 | 避免频繁跳变 |
| `xau_regime_switch_margin` | 0.15 | 趋势/震荡分数差距足够才切 |
| `xau_regime_transition_cooldown` | 3 | 切换后几根 bar 降仓/禁入 |
| `xau_regime_entry_lock` | true | 持仓按入场状态管理 |

入场时必须记录 `entry_regime`，后续 BE/TP/DTP/timeout/加仓都使用入场状态，而不是当前状态。

### 4. tick/bar 级坏簇研究要升级

下一轮坏簇不再按月份筛，而是按“入场瞬间的实时状态快照”聚类。需要在逐单 CSV 增加字段：

```text
regime_state
trend_score
range_score
noise_score
h1_net_atr_3
h1_eff_12
h4_range_atr_12
h4_eff_12
hhll_score
breakout_follow
sweep_revert_score
spread_risk
entry_profile
manage_profile
regime_age_bars
transition_bars
```

坏簇研究优先回答：

1. 趋势腿亏损是否集中在 `high_range_atr + low_efficiency`，即高波动震荡误判。
2. 震荡腿亏损是否集中在 `high_efficiency + breakout_follow`，即真趋势里逆势接刀。
3. 2026-04 中 `v11xau1` 为什么少了 `v11_single_selector` 的关键 market_close 大赢单。
4. 频繁切换是否导致同一笔交易入场和管理 profile 不一致。
5. 高仓位亏损是否集中在 transition 状态。

建议先做三个对照窗口：

| 窗口 | 原因 |
|---|---|
| 2026-04 | `v11_single_selector` 达标，`v11xau1` 不达标 |
| 2025-04 | 趋势强月，趋势腿必须能吃满 |
| 2024-09 | 最薄安全垫月，不能过拟合强月 |

### 5. 结果证据链必须修复

已发现同名报告存在污染风险：

- `results/backtest/v11xau1_20240606_20260526_20260528.txt` 当前为 0 笔、余额 200。
- 同名 `.md/.trades.csv` 仍残留旧的 1800 笔、余额 50616 信息。
- ledger 如果只扫 `.txt`，digest 如果不校验 freshness，就会产生互相矛盾的证据。

修复计划：

1. 报告文件名加入 `symbol/deposit/model/run_id`，避免同日同策略覆盖。
   - 例：`v11xau1_XAUUSDm_20260401_20260501_d200_m4_20260528_123045.txt`
2. digest 生成 `.md/.trades.csv` 时写入源 txt 的 `mtime/size/sha1`。
3. ledger 构建时若发现同 stem 的 `.md/.csv` 元信息不匹配，标记 stale，不参与结论。
4. ledger 选择记录时必须支持过滤 `deposit=200`、`model=4`、`symbol=XAUUSDm`。
5. `monthly_start_matrix.py` 和 `xau_dual_selector_eval.py` 必须优先选择满足 `model=4/deposit=200` 的报告，而不是只取余额最高。
6. 对旧报告缺少 `模型: 4` 的情况，标记 `model_unverified`，不能作为最终达标证据。

完成标准：

- 任一策略同窗口重复回测，不会覆盖旧报告。
- `.txt/.md/.csv` 不一致时，脚本输出明确错误。
- audit 不再把 `$593.64` 初始资金报告用于 `$200` 月度目标。

### 6. 月盈率目标是账户余额每月 35%，需要目标驱动风险容量

如果目标严格定义为“账户真实余额每月增长 35%”，固定手数上限和固定风险百分比最终会失败。原因是余额越大，同样市场机会带来的绝对收益占余额比例越低。

所以不能只做固定 `monthly_lot_sizing_base`。那只等价于“操作资金保持小余额，超额外部累计”，不等价于同一账户余额月增 35%。

需要新增目标驱动仓位模块：

```text
month_start_balance = 月初余额
target_balance = month_start_balance * 1.35
remaining_profit = target_balance - equity
remaining_days = 月内剩余天数
expected_edge = 当前 regime 的滚动期望 R/天
required_risk_dollars = remaining_profit / expected_edge
dynamic_risk_percent = required_risk_dollars / equity
最终风险 = clamp(dynamic_risk_percent, base_risk, max_target_risk)
```

还必须受这些硬约束限制：

- 最大单笔风险百分比
- 最大总浮亏风险
- 最大手数
- 保证金占用
- 连续亏损降档
- spread/risk 不足时禁止加风险
- 噪音状态禁止加风险

候选参数：

| 参数 | 建议初值 | 说明 |
|---|---:|---|
| `target_monthly_profit_pct` | 35 | 目标月收益 |
| `target_risk_enable` | true | 开启目标驱动风险 |
| `target_risk_max_percent` | 8 | 单笔风险上限，先保守 |
| `target_total_open_risk_pct` | 20 | 总持仓风险上限 |
| `target_min_edge_r_per_day` | 2 | 低于该滚动边际不追目标 |
| `target_noise_risk_mult` | 0 | 噪音状态禁止加风险 |
| `target_transition_risk_mult` | 0.25 | 状态切换期降仓 |
| `target_drawdown_cut_pct` | 8 | 月内回撤后关闭追目标 |

可证伪标准：

- 如果开启目标驱动风险后强趋势月收益显著提高，但弱震荡月回撤失控，则说明风险提升缺少 regime 保护。
- 如果强趋势月无法提高收益，说明瓶颈在信号频率/手数/保证金，不在 risk percent。
- 如果月月 35% 需要超过可接受回撤或保证金，目标应被标记为风险不可行，而不是继续调参制造幻觉。

## 改进假设

### H1：当前 HTF 触发把高波动震荡误判为趋势

预测：加入趋势效率和震荡噪音过滤后，2026-04 不应触发趋势腿，余额应接近 `v11_single_selector` 的 307.22。

最小实验：

```bash
python3 scripts/mt5_cli_backtest.py --background --brief --strategy v11xau1_eff_filter --symbol XAUUSDm --from 2026.04.01 --to 2026.05.01 --deposit 200 --timeout 900 --model 4
```

### H2：profile 反复计算导致入场和持仓管理不一致

预测：引入 tick/bar 缓存和入场 profile 锁定后，同窗口交易数和关键大赢单应更稳定，2026-04 不再丢失 4/14~4/16 的盈利结构。

最小实验：

```bash
python3 scripts/mt5_cli_backtest.py --background --brief --strategy v11xau1_regime_cache --symbol XAUUSDm --from 2026.04.01 --to 2026.05.01 --deposit 200 --timeout 900 --model 4
```

### H3：实时切换需要滞后和 transition 降仓

预测：加入最短持有 bars 和 transition cooldown 后，弱月回撤降低；强趋势月不应明显损失收益。

验证窗口：

```bash
python3 scripts/mt5_cli_backtest.py --background --brief --strategies v11xau1_regime_cache,v11xau1_hysteresis --symbol XAUUSDm --from 2026.04.01 --to 2026.05.01 --deposit 200 --timeout 900 --model 4
python3 scripts/mt5_cli_backtest.py --background --brief --strategies v11xau1_regime_cache,v11xau1_hysteresis --symbol XAUUSDm --from 2025.04.01 --to 2025.05.01 --deposit 200 --timeout 900 --model 4
```

### H4：账户余额 35% 需要目标驱动风险，而不是固定 lot cap

预测：目标驱动风险会在强边际状态提高收益，但在 2026-04 这类噪音状态不应加仓。

验证窗口：

```bash
python3 scripts/mt5_cli_backtest.py --background --brief --strategy v11xau1_target_risk --symbol XAUUSDm --from 2025.04.01 --to 2025.05.01 --deposit 200 --timeout 900 --model 4
python3 scripts/mt5_cli_backtest.py --background --brief --strategy v11xau1_target_risk --symbol XAUUSDm --from 2026.04.01 --to 2026.05.01 --deposit 200 --timeout 900 --model 4
```

### H5：证据链污染会误导优化方向

预测：修复报告 run_id 和 freshness 后，audit 会暴露更多真实缺口，但结论更可靠。

验证命令：

```bash
python3 scripts/xau_goal_audit.py --refresh-ledger --available-to 2026.05.26 --details --commands
```

## 实施计划

### P0：证据链修复

目标：先保证以后每条结论可追溯。

- 修改报告命名，加入 symbol/deposit/model/run_id。
- digest 写入源报告 sha1/mtime/size。
- ledger 加 `--required-deposit`、`--required-model` 过滤。
- monthly/audit/select 脚本禁止混用不同 deposit/model。
- 增加测试覆盖 stale md/csv、重复报告、不同 deposit 选择。

### P1：实时状态缓存与profile锁定

目标：不改变策略逻辑，先消除抖动。

- 新增 `XAURegimeState` 缓存结构。
- `OnTick()` 新 bar 时更新一次。
- 所有 `Cfg*()` 读取缓存状态，不直接调用 `UseXAUTrendProfile()`。
- 入场记录 `entry_regime`，持仓管理按入场 regime。
- digest CSV 输出 `entry_regime/manage_regime`。

### P2：实时行情分类器

目标：替代单一 HTF 触发。

- 增加趋势效率、噪音、突破延续、扫流动性回归等特征。
- 设计 `trend_score/range_score/noise_score`。
- 加滞后阈值、最短持有 bars、transition cooldown。
- 先跑 2026-04、2025-04、2024-09 三窗口。

### P3：tick/bar 坏簇研究

目标：找到可迁移的实时坏簇。

- CSV 增加 regime 快照字段。
- 对比强趋势、弱趋势、干净震荡、噪音震荡。
- 输出每个特征桶的 R、胜率、交易数。
- 将坏簇转成单变量实验，不直接上组合。

### P4：目标驱动风险容量

目标：在账户余额增长后仍有机会冲击月增 35%。

- 实现 target risk pressure。
- 引入最大风险、最大手数、最大保证金、回撤熔断。
- 只在高 edge 状态加风险，噪音/transition 禁止加风险。
- 用 200、1000、5000、20000、50000 初始资金做同窗口压力测试。

### P5：完整验收

目标：证明不是单窗口过拟合。

最小验收集：

| 类型 | 窗口 |
|---|---|
| 震荡弱月 | 2026-04、2026-05 |
| 趋势强月 | 2025-04、2025-10 |
| 薄安全垫月 | 2024-09、2024-12 |
| 连续长窗 | 2024.06.06~2026.05.26 |

最终验收：

```bash
python3 scripts/mt5_cli_backtest.py --background --brief --strategy <candidate> --symbol XAUUSDm --from 2024.06.06 --to 2026.05.26 --deposit 200 --timeout 1800 --model 4
python3 scripts/xau_goal_audit.py --refresh-ledger --available-to 2026.05.26 --details --commands
```

## 当前优先级

1. 先修证据链，否则所有优化都可能被旧报告污染。
2. 再做实时状态缓存和入场 profile 锁定，这是低风险基础设施。
3. 然后用 2026-04 验证实时分类器，目标先让 `v11xau1` 不低于 `v11_single_selector`。
4. 最后才做目标驱动风险容量，因为它会显著放大亏损，必须依赖可靠 regime。

