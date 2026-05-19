# Handoff: v10 FAGE策略迭代 — 2026-05-19

**仓库**: `git@github.com:nnasterw/WaiTrade2.git` (main, 有大量未提交改动)
**工作目录**: `/Users/wen/Projects/ClaudeCode/WaiTrade2`

---

## 目标

设计v10策略满足：WR>70% + PF(盈亏比)>2 + 日均>3 + **余额>$6719(v10a)**

## 当前状态：三指标已达标，余额未超v10a

### 最佳达标策略

| 策略 | WR% | PF | 日均 | 余额 |
|------|-----|-----|------|------|
| `v10_fage_dtp7_r15_bh1` | 71.1% | 2.01 | 3.3 | **$5802** ← 达标最高余额 |
| `v10_fage_dtp8_r20` | 71.1% | 2.05 | 3.3 | $4370 |
| `v10_fage_d9r15bh1_c4` | 70.7% | 2.24 | 3.3 | $4486 |
| `v10_fage_dtp10_r20` | 71.4% | 2.43 | 3.3 | $3627 |

### 接近但未达标（余额最高）

| 策略 | WR% | PF | 日均 | 余额 |
|------|-----|-----|------|------|
| `v10_fage_d7r15bh1_c4` | 70.4% | 1.81 | 3.3 | **$6571** ← 差v10a仅$148 |
| `v10_fage_dtp7_r20` | 70.7% | 1.98 | 3.3 | $5838 |

### 基线对比

| 策略 | WR% | PF | 日均 | 余额 |
|------|-----|-----|------|------|
| v10a (TDMFE-C3) | 50% | ~1.75 | 3.7 | $6719 |
| v10a_c3_fage (Codex) | ~50% | ~1.83 | 3.5 | $7537 |

## 核心发现

### 结构性矛盾

**DTP越高 → PF越高 → 余额越低**

原因：高DTP阈值让大量中等赢家（3-7R浮盈）无法触发DTP，回落到BE出场（0.08R），WR虚高但绝对利润低。v10a的DTP2R能及时捕获2-5R赢家，虽WR低但每笔赢单贡献大。

### FAGE核心配方

```yaml
# 入场
bar_period_min: 3                    # M3
enable_entry_engine: true             # tick级bounce确认
structure_break_bars: 3              # 结构突破确认
no_entry_hours: "0,9,12,17,18"       # 时段过滤
no_buy_hours: "1,6,8,10,23"          # 做多时段过滤
no_sell_hours: "6,16,20,22"          # 做空时段过滤
filter_cont_age_min_bars: 40         # FAGE: 延续OB年龄40-79非深位过滤
filter_cont_age_max_bars: 79
filter_cont_non_deep_only: true
ds_weight: false                     # 关闭DS权重

# 出场（DTP7R15BH1版本 = $5802）
breakeven_r: 0.25
breakeven_lock_r: 0.08
dtp_trigger_r: 7.0
dtp_retrace: 0.15
filter_buy_no_h1_min_pos_mult: 4.0   # 做多非H1高仓位降权
filter_buy_no_h1_max_pos_mult: 8.0
filter_buy_no_h1_pos_mult: 0.40
```

### 已验证无效的方向

- HTF目标（大周期OB对齐看远目标）→ 伤害WR和PF
- 强弱转换出场（区分回调/反转）→ PF从2.01降到1.26
- 阶梯DTP → PF1.49-1.56，不如单级DTP
- 高BE锁利（0.4R/0.5R）→ WR暴跌到60%
- MFE fail叠加DTP → 无额外增益

## 未提交的改动

- `config/strategies.yaml` — 追加~60个FAGE系列策略定义
- `mql5/Include/WaiTrade2/Config.mqh` — `InpOBHeightTPMult`参数
- `mql5/Include/WaiTrade2/SignalEngine.mqh` — `CalcOBHeightTP()`函数 + TP逻辑集成
- `scripts/yaml_to_set.py` — `ob_height_tp_mult` FLAT_MAP映射
- `scripts/mt5_cli_backtest.py` — wineserver kill加try/except
- `mql5/Presets/V10-FAGE-*.set` — ~40个preset文件
- `results/backtest/v10_fage_*.txt` — 回测结果
- `research/notes/2026-05-18_v10_xau_development.md` — 今天早些时候的Round1-7结论

## 下一步方向

### 方向A：突破余额瓶颈（推荐）

当前$5802→$6719+的路线：
1. **DTP partial close at 2R**：到2R时先平50%锁利（确保中等赢家贡献利润），余仓用DTP7R跑远。但之前测试partial伤害WR——需要在FAGE+BH1过滤下重测。
2. **双层出场**：非H1对齐单用DTP2R快出（贡献利润），H1对齐单用DTP7R跑远（贡献PF）。需要EA新增按条件切换出场的逻辑。
3. **多品种组合**：XAU用DTP7(WR71/PF2/$5802) + XAG/EUR补余额。

### 方向B：接受当前结果定版

`v10_fage_dtp7_r15_bh1` 三指标全部达标，可以正式定版为v10。余额$5802虽低于v10a但盈利指标更健康（v10a的WR50%/PF1.75不满足用户目标）。

## MT5回测注意事项

- wineserver路径有bug（`/wine`→`/wineserver`替换错误），已加try/except跳过
- wineserver被kill后MT5丢失登录session报"account not specified"——**不能kill wineserver**
- Tester缓存有时导致结果不变——需先确认MT5确实启动了新回测（检查agent日志时间戳）

## 关键文件索引

| 文件 | 用途 |
|------|------|
| `research/notes/2026-05-18_v10_xau_development.md` | 完整v10迭代记录 |
| `config/strategies.yaml` 末尾 | FAGE系列~60个策略 |
| `mql5/Presets/V10-FAGE-*.set` | 对应preset文件 |
| `results/backtest/v10_fage_*.txt` | 回测结果 |

## 建议技能

- `/wf-improve-strategy` — 继续优化
- `/goal` — 若需重定义目标（如放弃余额>v10a约束）
