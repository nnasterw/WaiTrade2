# BTC 两腿策略优化 — Handoff 文档
**日期**：2026-05-30
**项目**：`/Users/wen/Projects/ClaudeCode/WaiTrade2`
**目标**：BTC 两腿策略，24 个月独立测试每月 ≥50% 盈利，720 天顺序复利 >$500,000

---

## 当前最优状态（已验证）

### 两腿配置
| 腿 | 策略名 | Magic | 核心特性 |
|----|--------|-------|---------|
| 高频腿 | v11btc-r234 | 204806 | M5 j2 OB + DTP2.5/0.20 + H14屏蔽 + D1 SELL屏蔽 + neutral=1.1 |
| 牛市腿 | v11btc-h4 | 204807 | H4 OB + state_filter禁用 + D1推进aligned=2.0 |

### 关键参数（v11btc-r234）

```
htf_net_push_tf: 1440 (D1)
htf_net_push_bars: 5
htf_net_push_min_atr: 2.0
htf_net_push_neutral_mult: 1.1
htf_net_push_sell_counter_scale: 0.0  ← D1 SELL逆势屏蔽
low_risk_hours: 14                     ← UTC 14:00 低仓
low_risk_hour_mult: 0.0
enable_state_filter: true
dtp_trigger_r: 2.5 / dtp_retrace: 0.20
risk_percent: 6.5%
bounce_pct: 0.30
```

### ⚠️ 当前脏状态（需要清理）
`config/strategies.yaml` 里 v11btc-r234 有两个测试参数需要处理：
```yaml
enable_htf_vol_block: true
htf_vol_block_atr_mult: 0.1   # 极低阈值（测试用），尚未生效
htf_vol_block_tf: 240
```
这是一个**未完成的实验**，代码已写入但效果为零（原因未查明）。

---

## 月独立测试结果（24个月，$200起步，≥$300=通过）

**通过月（14/24）**：
```
Jul24 r234 $385  | Aug24 h4 $554   | Nov24 h4 $853   | Jan25 h4 $1448
Feb25 r234 $416  | Jun25 r234 $387 | Aug25 r234 $730 | Sep25 r234 $305
Oct25 r234 $300  | Nov25 r234 $1387| Dec25 r234 $503 | Jan26 h4  $324
Mar26 r234 $342  | Apr26 r234 $507
```

**最接近失败月**：Jul25（差$24）、Jun24（差$25）

**核心瓶颈月（r234亏损，h4也差）**：
- Sep24: r234=$50，h4=-$16（穿仓）
- Oct24: r234=$89，h4=$152
- Nov24: r234=$118，h4=$853（h4通过）
- Dec24: r234=$133，h4=-$37（穿仓）
- Jan26: r234=$76，h4=$324（h4通过）
- Feb26: r234=$81，h4=0笔

---

## 720d 顺序复利
- **r234 单腿 720d = $70,528**（MT5 Model4 实测，2024.06.09~2026.05.30）
- h4 单腿 720d 穿仓（不可单独跑顺序复利）
- **目标 $500k+ 未达到**，差距约 7×

### 720d 关键路径分析
```
Jun24($275)→Jul24($529)→[Sep24-Dec24 崩到$23]→[慢慢恢复]→
Aug25($643)→Nov25($10,198)→Dec25($25,648)→[Jan26-Feb26跌到$4k]→Apr26($17k)
```
**修复 Sep24-Dec24（保底$200）= 估算 720d 提升到 $1.6M**

---

## 本次会话穷尽的改进方向（全部失败）

| 方向 | 结果 | 根本原因 |
|------|------|---------|
| 时段屏蔽 H07/H13 | 破坏 pos_mult 路径 | j2 路径依赖 |
| D1 推进参数 (min_atr/bars) | 无效或更差 | Sep24 不在 D1 路径中 |
| sell_pos_mult=0 全局禁空 | Feb25 崩$114, Nov25 崩$323 | SELL 是核心盈利来源 |
| no_entry_hours=7 | 大量月份 0 笔 | 破坏 pos_mult 积累序列 |
| monthly_loss_stop 30%/15% | 完全无效 | j2 亏损来自已持仓止损 |
| max_lot_size=3 | 720d=$20k | 截断高余额盈利月 |
| fixed_lot_sizing_balance=200 | 720d=$6k | 截断 pos_mult 月内复利 |
| H1(60) 净推进 | 720d=$27k | Sep25 退步，整体更差 |
| EMA 趋势追踪 (M5 突破) | 亏损 | M5 R/R 差，噪音多 |
| risk_percent 7.5%/8.0% | 净零 | Jul25+ 但 Oct25- |
| H4 波动率屏蔽 (进行中) | 尚未生效 | 代码问题待查 |

---

## 待完成：H4 波动率屏蔽调试

### 代码实现
- `Config.mqh`：新增 `InpEnableHTFVolBlock/ATRMult/TF/Period`（行 85 附近）
- `SignalEngine.mqh`：ScanSignals 函数入口（行 1730 附近），H4 ATR > M5 ATR × 阈值时 `return 0`
- `yaml_to_set.py`：FLAT_MAP 已加入 4 个映射
- `strategies.yaml` defaults：`enable_htf_vol_block: false` 等

### 当前问题
启用后（阈值 0.1）Sep24 结果完全不变（17 笔/$50）。代码逻辑：
```cpp
if(CopyRates(symbol, htfTF, 1, needed, htfRates) >= needed) {
    // 计算 H4 ATR
    if(htf_atr > InpHTFVolBlockATRMult * state.atr_value)
        return 0;
}
```
**怀疑原因**：
1. CopyRates 在 tester 中失败（返回 <needed）
2. H4 ATR / M5 ATR 比值计算的量纲不匹配

### 调试步骤
1. 在代码中加 `Print` 输出 `htf_atr`、`state.atr_value`、CopyRates 返回值
2. 确认比值是否真的 > 0.1
3. 如有效，找最优阈值（目标：Sep24/Jan26 改善，好月不退步）

---

## 新增代码（本次会话，已提交）

| 文件 | 变更 | commit |
|------|------|--------|
| Config.mqh + TradeOps.mqh | InpFixedLotSizingBalance（月初lot基准重置） | d36df08 |
| Config.mqh + SignalEngine.mqh + WaiTrade_OB.mq5 | InpEnableEMATrend（EMA趋势追踪，默认关闭） | c1f99b0 |
| Config.mqh + SignalEngine.mqh | InpEnableHTFVolBlock（H4波动屏蔽，实验中） | 未提交 |

---

## 铁律（绝对禁止）
- ❌ 月份过滤（任何基于特定月份/季节的规则）
- ❌ 历史拟合（用历史知道的"哪些月份坏"来设规则）
- ✅ 所有改进必须基于当前 tick 可观测的实时指标

---

## 建议下次会话步骤

**立即任务**：
1. 清理脏状态：恢复 `enable_htf_vol_block: false`（或完成调试）
2. 确认 r234 月独立 14/24 基线完整

**继续探索**（若 H4 波动屏蔽调试有效）：
1. 在代码加 Print 确认 H4 ATR 实际值
2. 找最优阈值，全量 24 月测试
3. 运行 720d，验证是否超过 $200k

**备选方向**（若波动屏蔽无效）：
- H4 级别趋势追踪（在 H4 OB 方向上追单，非 M5 级别）
- 直接接受 14/24 + $70k 作为最终答案

---

*详细历史实验记录见：`progress.txt`（最后几节）*
*两腿最终配置见：`memory/btc-2leg-final.md`*
