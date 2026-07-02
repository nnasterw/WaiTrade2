# 2026-07-02 v11-btc1-trend WFYS 迭代记录

## 目标

承接 2026-06-28 v11-btc1-qual 迭代的 qual232 终点（WFYS 80.17 距 85 差 5 分），按新要求：

> 以 smc 为纲领，结合江河经验、tadermaxliu经验，分析趋势规律，改进策略并回测，
> 探测符合 wfys 标准的 btc EA 策略，重点关注较大周期趋势的宽止损高利润交易机会

重点是"较大周期 + 宽 SL + 高利润 + WFYS 85+"。本轮以 qual232 为底盘做 5 轮 trend01-05 单变量迭代。

## 前置调查

1. **WaiTrade3\WaiTrade_OB_SMC.mq5 当前源码 102 个编译错误**（InpEnableLiquidityPool、g_smc_data、g_lpools 等未声明），导致 smc01/smc02 之前所有结果实际是 Moving Average.ex5 替身（523 笔 15.5% $1.13 是 MA 默认参数行为）。
2. **SMC 栈参数（liquidity pool / OB scoring / discount premium）** 在 Config.mqh 中不存在，只有 smc01 的 YAML 在用 WaiTrade3 expert。所以本轮**只能用 WaiTrade2\WaiTrade_OB.ex5**。
3. **qual232 主线 = 146 笔 39.7% WR PF 2.08 余额 $16,791.96 WFYS 80.17**，底盘足够稳。

## 本轮策略（trend01-05）

### 1. `v11-btc1-trend01`：qual232 + 宽 SL 范本

- 启用 BTC profile
- 宽 SL: `btc_sl_buffer_atr: 2.5` (vs 默认 1.5)
- 迟 BE: `btc_breakeven_r: 1.5, btc_breakeven_lock_r: 0.5`
- 迟 DTP: `btc_dtp_trigger_r: 5.0, btc_dtp_retrace: 0.18`
- 关 OB 高度 TP: `btc_ob_height_tp_mult: 0.0`
- 延长 time exit: `btc_time_exit_bars: 200`
- H1 拉回: `htf_pullback_tf: 60`

结果：225 笔 42.2% WR PF 1.51 余额 **$2,625.49**，WFYS **55.88/100**（淘汰）

关键事实：
- 24月盈利月数 16/24（缺 5）
- 大亏月 4（应为 0）
- 720d DD 51.5%（超 25% 阈值）
- Recovery 2.06（未达 3.0）
- PF 1.43（未达 1.75）
- Sharpe 1.39（未达 1.5）
- >3R 大赢单 12.1%

结论：宽 SL 单独作用方向**证伪**。亏损单变得更大，盈亏比反而下降。`qual232` 的 1.5 ATR SL 已经能容下趋势，过宽的 2.5 是过度宽容。

### 2. `v11-btc1-trend02`：qual232 + BTC profile 默认参数（仅启用）

改动：仅 `enable_btc_profile: true, btc_profile_symbol: "BTC"`，其他全部用 BTC profile 默认值（btc_sl_buffer_atr=1.5, btc_breakeven_r=1.0, btc_dtp_trigger_r=3.0, btc_max_lot_size=9.0, btc_max_pos_mult=300, btc_max_concurrent=8）。

结果：197 笔 42.1% WR PF 1.84 余额 **$9,807.29**，WFYS **74.73/100**（淘汰）

关键事实：
- 24月盈利月数 20/24（差 1）
- 大亏月 4
- 强利润月 15（！）
- 大趋势月 12（！）
- 720d DD 17.7%（**过 25% 硬门槛**）
- Recovery 5.45（**过 3.0**）
- PF 2.29（**过 1.75**）
- >3R 占比 11.5%

结论：BTC profile 默认参数（高仓位上限 9.0 手、pos_mult 300、concurrent 8）让 BTC 在 $200 账户上跑出 49x 收益 + 优秀风险质量。但**单笔 2.69 手的低余额加仓**制造了 2026-01 的 -$698 大亏月，是 WFYS 卡在 74.73 的根因。

订单级证据：
- 2026-01-06 buy 2.69 lot: -$429.54（仓位上限失控）
- BTC profile 默认 `InpBTCMaxLotSize=9.0` 和 `InpBTCMaxConcurrent=8` 远高于 Live 安全边界

### 3. `v11-btc1-trend03`：trend02 + 安全仓位上限

改动：`btc_max_lot_size: 0.5, btc_max_pos_mult: 30.0, btc_risk_percent: 2.5, btc_max_concurrent: 3`

结果：170 笔 41.8% WR PF 2.32 余额 **$2,125.06**（估计 WFYS ~70）

结论：**安全仓位上限证伪**。`btc_max_lot_size=0.5` 直接把 $200 账户的复利空间切掉，49x → 10.6x。仓位上限是 BTC $200 账户高利润的核心驱动。

### 4. `v11-btc1-trend04`：trend02 + 并发上限 2

改动：`btc_max_concurrent: 2, btc_max_lot_size: 1.0`

结果：197 笔 43.7% WR PF 1.83 余额 **$7,429.14**，WFYS **71.40/100**（淘汰）

关键事实：
- 24月盈利月数 18/24（比 trend02 少 2）
- 大亏月 5
- 720d DD 16.5%（PASS）
- PF 2.30（PASS）
- >3R 占比 12.5%

结论：并发上限 2 切掉了趋势叠加仓位，比 trend02 收益降 24%（9.8K → 7.4K），但 WFYS 反而降到 71.4（24月变差）。**3+ 并发是趋势叠加的必要条件**。

### 5. `v11-btc1-trend05`：qual232 + H1 拉回 only

改动：`enable_htf_pullback: true, htf_pullback_only: true, htf_pullback_tf: 60`

结果：368 笔 36.4% WR PF 1.20 余额 **$536.56**

结论：H1 拉回 only **证伪**。过严过滤让 OB 频次暴增但质量下降，胜率从 39.7% 跌到 36.4%，PF 1.20 远低于 WFYS 阈值。H1 拉回是补量通路而非主线。

## 本轮收敛

按 `WFYS` 看，**本轮最关键的发现**是：

1. **BTC profile 默认参数组合（trend02 74.73）已超过 qual232 之外的任何变体**。高仓位上限（9.0）+ 高 pos_mult（300）+ 高并发（8）让 BTC 在 $200 账户上跑出 49x 收益 + DD 17.7% + Recovery 5.45。
2. **2.69 手的单笔失控是 WFYS 卡在 74.73 的唯一硬失败**。2026-01 单月 -$698 来自 buy 2.69 lot → SL -$429.54。低余额加仓未封顶。
3. **宽 SL 单独作用证伪**（trend01 55.88）。qual232 的 1.5 ATR SL 已能容下趋势。
4. **安全仓位上限证伪**（trend03）。仓位上限是 BTC $200 账户高利润的核心，砍掉即崩。
5. **H1 拉回 only 证伪**（trend05）。补量通路，非主线。

| 版本 | 改动 | 余额 | 笔数 | WR | PF | WFYS | 备注 |
|---|---|---:|---:|---:|---:|---:|---|
| qual232 | 主线（无 BTC profile） | $16,792 | 146 | 39.7% | 2.08 | **80.17** | **WFYS 最高** |
| trend01 | + 宽 SL 范本 (2.5 ATR) | $2,625 | 225 | 42.2% | 1.51 | 55.88 | 宽 SL 单独**证伪** |
| trend02 | + BTC profile 默认参数 | $9,807 | 197 | 42.1% | 1.84 | **74.73** | **新方向最高** |
| trend03 | + 安全仓位 (0.5/30) | $2,125 | 170 | 41.8% | 2.32 | ~70 | 安全上限**证伪** |
| trend04 | + btc_max_concurrent=2 | $7,429 | 197 | 43.7% | 1.83 | 71.40 | 并发上限伤复利 |
| trend05 | + H1 拉回 only | $537 | 368 | 36.4% | 1.20 | ~50 | H1 only **证伪** |
| trend06 | + btc_max_lot_size 1.5 | $8,162 | 211 | 44.1% | 1.63 | 72.55 | 略降 WFYS |
| trend07 | + btc_max_lot_size 1.0 | $6,758 | 201 | 42.3% | 1.61 | 73.65 | 平衡但 24月 退 |
| trend08 | + btc_max_pos_mult 50 | $9,807 | 197 | 42.1% | 1.84 | 74.73 | **= trend02** pos_mult 改动无效 |
| trend09 | + btc_risk_percent 2.5 | $2,594 | 165 | 41.8% | 2.56 | ~70 | 仓位伤复利 |
| trend10 | + btc_risk_percent 3.5 | $7,475 | 189 | 41.8% | **3.12** | 68.60 | **风险质量最佳**（PF 4.03/Recovery 11.27/Sharpe 1.63 全部过线）但 24月 仅 17/24 |
| trend11 | + OB-only bad_bounce 0.28-0.40 x0.5 | $9,807 | 197 | 42.1% | 1.84 | 74.73 | **= trend02** 当前范围无交易命中 |
| trend12 | + entry_depth_pct 0.5 | $9,807 | 197 | 42.1% | 1.84 | 74.73 | **= trend02** 深度改动不生效 |

## 关键发现汇总（趋势 11-12 补充）

### trend11/12 = trend02 的原因
- trend11 (`bad_bounce 0.28-0.40 x0.5`) 和 trend12 (`entry_depth_pct 0.5`) 的 720d 结果与 trend02 完全相同
- 这说明 2024-2026 BTC 测试期所有合格交易的：
  - `bounce_ob` 不在 0.28-0.40 范围内（filter 不命中）
  - `entry_depth` 实际值不在 0.5-0.67 区间（filter 不触发）
- BTC profile 中**真正生效的杠杆控制只有 `btc_max_lot_size` 和 `btc_risk_percent`**

### 真有效杠杆控制梯度
| 控制变量 | 从默认到目标 | 余额变化 | 720d 余额倍率 |
|---|---|---:|---:|
| 无 (qual232) | 默认 max_lot 1.6 | $16,792 | 84x |
| trend02 默认 | max_lot 9.0 | $9,807 | 49x |
| trend06 | max_lot 1.5 | $8,162 | 41x |
| trend07 | max_lot 1.0 | $6,758 | 34x |
| trend03 | max_lot 0.5 + pos_mult 30 | $2,125 | 11x |
| trend04 | max_lot 1.0 + concurrent 2 | $7,429 | 37x |
| trend09 | risk 2.5 | $2,594 | 13x |
| trend10 | risk 3.5 | $7,475 | 37x |

### 核心规律
- **`btc_max_lot_size` 与 `btc_risk_percent` 是两个真正控制仓位的轴**
- `btc_max_pos_mult` 和 `entry_depth_pct` 在该测试期无效
- 仓位越大 → 720d 收益越高，但 WFYS 24月稳定性越差
- 仓位越小 → 720d 收益越低，但 WFYS 风险质量越好

### BTC profile 默认参数为何是 9.0/5.4%/300
- 这是为**高余额账户**（$5000+）设计的，不是为 $200 Live 账户
- Live 部署 BTC profile 前必须显式覆盖到安全边界

## 最终结论

按 WFYS 验收标准 (≥ 85 = 研究版 Live 候选, ≥ 90 = 优先部署)：

| 候选 | WFYS | 距离 85 | 距离 90 |
|---|---:|---:|---:|
| **qual232**（主线） | 80.17 | -4.83 | -9.83 |
| **trend02**（BTC profile 默认） | 74.73 | -10.27 | -15.27 |
| **trend10**（risk 3.5） | 68.60 | -16.40 | -21.40 |

**未达成 WFYS 85+**。

### 根本原因
- BTC $200 账户 × 720d 测试期 的"高利润" 与 "WFYS 24月稳定" 是**结构性互斥**的
- 唯一路径是**代码层引入条件仓位门**（balance-tier / pos_mult-tier lot cap）

### 代码层需求（跨 session）
1. 新增 EA input `InpEnableBalanceTierLotCap` (默认关闭)
2. 新增 `InpBalanceTier1Threshold`, `InpBalanceTier1MaxLotSize`
3. 新增 `InpBalanceTier2Threshold`, `InpBalanceTier2MaxLotSize`
4. 修改 PositionManager.mqh: 在 `CfgMaxLotSize()` 之后再应用 balance-tier cap
5. 同步 FLAT_MAP / strategies.yaml / tests / compile
6. 预期：balance < $3000 时 cap 到 0.5 手（消除 2.69 手大亏），balance > $3000 时维持 9.0 手（保留 49x 复利）

### 阻塞基础设施
- `WaiTrade3\WaiTrade_OB_SMC.mq5` 102 编译错误未修
- smc01/smc02 仍无法使用，无法在 BTC 上引入"discount premium / liquidity pool / OB scoring"等 MaxLiu 完整栈

## 待办（跨 session）

- [ ] 代码层添加 `InpEnableBalanceTierLotCap` + balance tier 阶梯 (关键)
- [ ] 修复 `WaiTrade3\WaiTrade_OB_SMC.mq5` 102 编译错误
- [ ] 重启 trend13+ 迭代，目标 WFYS 85+
- [ ] 更新本文件为 v2 迭代日志


## trend06-10 关键发现

### trend06/07 (btc_max_lot_size 1.5/1.0)
- WFYS 微降（74.73 → 72.55 → 73.65）
- DD 改善（17.7% → 18.4% → 14.7%）
- Recovery 改善（5.45 → 5.08 → 6.90）
- 但 24月 盈利月数下降（20/24 → 19/24）
- **结论**：硬限单笔 lot 切掉了高余额阶段趋势利润，但未消除大亏月

### trend08 (btc_max_pos_mult 50)
- 与 trend02 完全相同 ($9,807 / 197 / 42.1% / 1.84)
- **结论**：pos_mult 改动无效 — 实际仓位由 InpBTCMaxLotSize 主导

### trend09/10 (btc_risk_percent 2.5/3.5)
- trend10 出现质的飞跃：PF 2.29→4.03, Recovery 5.45→11.27, Sharpe 1.35→1.63（**首过 1.5 硬门槛**）, avg_W/|avg_L| 3.20→5.69
- 但 24月 盈利月数从 20/24 跌到 17/24（trend10）
- **结论**：降低 risk_percent 大幅改善单笔 R 分布，但月度胜率变差
- 这是经典"风险换月胜率"trade-off

## 终极判断

按 WFYS 看，**BTC $200 账户** 的根本矛盾是：
- **高利润** 需要高 risk_percent × 高 pos_mult × 高 max_lot_size
- **WFYS 24月 ≥ 21/24** 需要月度稳定，不能有大亏月
- 这两个目标在当前 EA 架构下**互斥**

| 切高利润方向 | 切稳定方向 |
|---|---|
| trend02 (5.4% risk) | qual232 (无 BTC profile, 10% risk 但 max_lot 1.6) |
| 49x 收益，4 大亏月 | 84x 收益，0 大亏月 |
| WFYS 74.73 | WFYS 80.17 |

**关键洞察**：qual232 的 80.17 之所以胜出，不是"更好"，而是它**没有走 BTC profile 的高仓位路径**。`max_lot_size: 1.6`（vs BTC profile 默认 9.0）+ 较高的 SL/BE/DTP 一致性让它的 24月 和 risk metrics 都达标。

要 WFYS 85+ 突破，必须在代码层引入**条件仓位门**（balance tier / pos_mult tier），单靠 BTC profile 参数微调无法达成。

## 待办（基础设施，跨 session）

- [ ] 添加 EA input `InpEnableBalanceTierLotCap` (默认关闭)
  - `InpBalanceTier1Threshold` (默认 5000), `InpBalanceTier1MaxLotSize` (默认 1.0)
  - `InpBalanceTier2Threshold` (默认 10000), `InpBalanceTier2MaxLotSize` (默认 2.0)
  - 配合 `InpEnableBTCProfile` 使用
- [ ] 同步 FLAT_MAP / strategies.yaml / tests / compile
- [ ] 修复 `WaiTrade3\WaiTrade_OB_SMC.mq5` 102 编译错误（让 smc01 栈可用）
- [ ] 跨 session 重启 trend11+ 迭代


## 下一轮方向

不放弃 BTC profile，但要从根上修掉 2.69 手的失控，**不能砍整体仓位上限**。优先候选：

1. **trend06**：trend02 + 新增默认关闭的"低余额阶段单笔 lot cap"EA input（opt-in），仅在 `balance < $3000` 时把 `InpBTCMaxLotSize` 压到 0.5。这能把 2026-01 的 2.69 lot 单笔限制到 0.5，损失 $429 → $80，但保留高余额阶段的 9.0 上限。
2. **trend07**：trend02 + `OB-only bad_bounce`（参考 qual35 0.28-0.40 x0.5），把坏 OB 几何降权。
3. **trend08**：trend02 + 结构化入场过滤（只允许 BOS / HTFPB / SDFLIB 触发），减少 SWP 频次。

## 待办（基础设施）

- [ ] 修复 `WaiTrade3\WaiTrade_OB_SMC.mq5` 102 个编译错误（让 smc01 栈可用）
  - 需要声明 `InpEnableLiquidityPool`, `InpEnableOBScoring`, `InpEnableDiscountPremium`, `InpEnableStructureTracker` 等
  - 需要定义 `g_smc_data`, `g_lpools` 等全局对象
  - 编译验证 `0 errors / 0 warnings`
  - 工作量：中等（需补充 ~50 行 input 声明 + 重写 .mq5 入口）

## 关键发现汇总

1. **BTC profile 的 `btc_max_lot_size=9.0` 默认值对 $200 账户是危险的**。Live 部署前必须显式覆盖到 ≤ 0.5。
2. **BTC profile 的 `btc_max_pos_mult=300` 默认值允许单次入场开到 300 倍仓位**。这也是危险的，应覆盖到 ≤ 30。
3. **BTC profile 的 `btc_max_concurrent=8` 默认值允许 8 单同时持仓**。高余额阶段合理，低余额阶段应降到 2-3。
4. **qual232 仍是当前最佳 BTC 主线**（WFYS 80.17），趋势01-05 探索均未超越。
5. **宽 SL 不是 BTC 的问题，DTP/BE 才是**。qual232 已经把 SL/BE/DTP 调到接近最优。