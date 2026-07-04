# BTC 3+/周 + 93+ WFYS 攻关 - 最终报告 (2026-07-04)

## 目标
- BTC 策略 WFYS 93+ 
- 一周至少 3 单交易
- 使用 wf-yhcl 分析
- 根本性调整

## 现状分析
- **当前最佳: v11-btc1-trend111/112 (87.34, 研究版Live候选)**
- 交易数量: 117 笔 / 24 月 = **4.9 笔/月 = 1.1 笔/周**
- 目标 3 笔/周 = 12 笔/月 = **288 笔/24 月** (需要 2.5x)

## Round 1-4 实验结果 (新增 trend185-200, 16 个变体)

| 策略 | 变体 | 交易数 | 分数 | 周数 |
|------|------|--------|------|------|
| trend185 | reentry=1 | 117 | 87.34 | 1.1 |
| trend186 | HTF pullback | 487 | 62.78 | 4.7 |
| trend187 | 全面放宽 | 487 | 62.78 | 4.7 |
| trend188 | min_risk=3.0 | 117 | 87.34 | 1.1 |
| trend189 | reentry+max=8 | 117 | 87.34 | 1.1 |
| trend190 | reentry+max=10 | 117 | 87.34 | 1.1 |
| trend191 | Sweep确认 | 117 | 87.34 | 1.1 |
| trend192 | HTFPB+min_risk=3.5 | 516 | 70.95 | 5.0 |
| trend193 | M1 timeframe | 117 | 87.34 | 1.1 |
| trend194 | M3 timeframe | 117 | 87.34 | 1.1 |
| trend195 | 月利锁+HTFPB | 111 | 87.47 | 1.1 |
| trend196 | HTFPB+min_risk=4.0 | - | - | - |
| trend197 | HTFPB+bad_bounce HTFPB | 554 | 62.36 | 5.4 |
| trend198 | HTFPB+bad_bounce 多类型 | 483 | 80.22 | 4.7 |
| trend199 | HTFPB+FVG+bad_bounce | 186 | 35.68 | 1.8 |
| trend200 | HTFPB+FVG+Sweep+bad_bounce | 177 | 24.57 | 1.7 |

## 关键发现

### 1. OB 策略天然交易数量限制
- 趋势111 (OB only) 117 笔/24月 = 1.1/周
- OB 检测频率约 5/月, 每 OB 通常只入 1 次
- reentry/max_entries 调整无效 (OB 不重复入场)
- Timeframe (M1/M3/M5) 不影响 OB 检测数量
- 趋势195 (月利锁) 轻微提升 87.47 但交易数减少

### 2. 增加入场类型的代价
- HTF pullback: +370 笔 (5/周) 但 score → 62.78
- FVG: 大量低质量入场 → score → 24-35
- Sweep: 单独效果不大
- bad_bounce 对 HTFPB 也无效 (HTFPB 信号本身质量低)

### 3. 根本原因
- BTC OB 策略核心是约 120 笔优质交易
- HTFPB/FVG 等额外入场增加数量但稀释质量
- 87.34 是 OB 策略的参数优化上限
- 3+/周 + 93+ 需要根本性策略方向调整

## 结论

BTC OB 策略的 WFYS 评分上限是 **87.34** (trends 111/112), 交易数量约 1.1/周.

**3 笔/周 + 93+ 分** 需要:
1. 全新策略方向 (非 OB-based)
2. 多策略组合 (BTC OB + 其他信号源)
3. 不同时间周期或品种
4. 完全不同的策略基线 (如 v10_m3_* 家族)

当前 BTC OB 策略在 OB 检测和入场逻辑上已达到优化极限, 进一步提升需要策略层面的根本性重构, 而非参数调优或单点代码改造.

## 现状 (commit 1bc92d46)
- 分支: codex/btc-wfyc-88
- 16 个新策略变体 (trend185-200)
- 全部回测 + WFYS JSON 已推送
- 详细分析见本笔记
