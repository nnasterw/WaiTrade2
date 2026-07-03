# 2026-05-25 v11a portfolio risk audit

## 背景

目标仍是 BTC 720 天 MT5 Strategy Tester CLI 结果驱动：日均开单数 > 4、总盈利 > 90000u、每个月盈利。当前最强组合命名为 `v11a`，包含 R224/R225/R226/R211M/R213D/R216M/R227 七条腿，均为同一个 `WaiTrade_OB` EA 的不同参数实例，共用账户级 shared monthly guard。

## v11a 当前表现

- `results/backtest/portfolio_v11a_preflight_20260525.md`
  - proxy total = 321956.95
  - daily = 10.98
  - bad months = 0
- `results/backtest/portfolio_v11a_source_risk_20260525.md`
  - R224: 97659.77, 0 negative months
  - R225: 90433.50, 2 negative months, worst 2025-10 -3489.62
  - R226: 42901.73, 5 negative months, worst 2026-01 -590.58
  - R227: 90593.22, 3 negative months, worst 2026-03 -38.72
  - R211M/R213D/R216M are small patch legs, not main profit drivers

## 组合风险判断

组合确实会合并劣势，不应把多腿理解成天然稳健。v11a 能过目标，是因为坏月没有同步爆发，并且 shared guard/drop filters 把 3/5/10/11/12 等坏簇限制住。最弱月集中在早期低余额月份和 2026-03：

- 2024-11: +74.67, 靠 profit_target_3% 提前停手
- 2026-03: +186.67, 由 R216M/R211M 补丁腿抵消 R227 的小幅负贡献
- 2026-05: +2965.85, 主要由 R227 提供

## Leave-one-out / sensitivity 结论

`results/backtest/portfolio_v11a_sensitivity_20260525.md`:

- drop R225: 3 bad months, total 59063.85, 失败
- scale R225 <= 0.5: 2 bad months，失败
- drop R216M: 1 bad month，2026-03 -19.67，失败
- drop R224/R226/R227: 仍 0 bad months，但收益和日均明显下降
- drop R211M/R213D: 仍 0 bad months，影响很小

结论：R225 与 R216M 是保月度为正的关键腿；R224/R227 是主收益腿；R226 提供收益但负月最多；R211M/R213D 更像微补丁。

## 重要发现：降权不能只缩仓位

直接把主腿 scale 下调会让 2026-03 重新变成坏月。原因不是简单的腿失效，而是绝对余额阈值耦合：

- v11a 的高余额坏簇过滤使用 `min_start=50000/100000`
- 降权后账户余额路径变低
- 原本应该触发的高余额 3/5 月 drop filters 不再触发
- 坏簇重新进入，尤其是 2026-03

验证：在缩放仓位的同时同步缩放余额阈值，低暴露候选恢复 0 坏月。

`results/backtest/portfolio_v11b_scale025_threshold025_candidate_20260525.md`:

- R224=0.25, R225=0.75, R226=0.25, R211M=1, R213D=0, R216M=1, R227=0.25
- balance_threshold_factor=0.25
- proxy total = 126023.44
- daily = 10.96
- bad months = 0
- weakest = 2024-11 +38.13

这是 v11b 候选方向，但不是最终策略。scale 是 CSV proxy 快筛，不是 live-ready MT5 参数；必须把缩放落实为策略参数并跑 720 天 MT5 Real Ticks，再做 preflight/stress/shared-return/no-entry runtime guard 审计。

## 下一步

1. 将 v11b 候选转成真实策略参数：优先通过 `risk_percent` 或 `fixed_lot/max_lot` 等 EA 参数缩放，而不是只在 CSV 上乘 PnL。
2. 同步重标定所有余额阈值：drop filters、monthly guard、context filters、profit target max/min balance。
3. 跑 MT5 720 天 Real Ticks，生成真实 `.trades.csv`。
4. 对真实 CSV 重新跑 proxy/stress/shared-return/source-risk/sensitivity。
5. 只有真实 MT5 结果仍满足三目标，才考虑把 v11b 固化为正式方案。
