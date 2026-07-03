# 最深回调止损(DP-SL) + OB质量过滤 研究结论

日期: 2026-06-04 | 相关: D4/D5/D7 系列回测

## 核心发现

1. **DP-SL 是 OB 质量过滤的关键补偿机制**：D3 ($154K) → D5B ($265K) = +72%
2. **DP-SL buffer 甜点 = 0.5**（XAU $0.5 ≈ 5 pip）：0.3 太紧/0.7 太宽
3. **MaxCounterRiskATR=0.5 是不可放松的坏日子防线**
4. **短窗口（1-2天）结果不可信**：D7D 双窗口最佳但 720d 输 D5B $53K
5. **D5B 为当前最佳候选**：$265K, 60.6% WR, 比基线少 21% 收益但风险指标全面提升

## 待探索改进方向

### 1. 自适应 DP-SL buffer
- 震荡市（ADX<20）：buffer 加宽到 0.7
- 趋势市（ADX>30）：buffer 缩窄到 0.3
- 预期收益：震荡市多赚 + 趋势市少亏

### 2. 多时间框架 OB 结构确认
- 入场前验证 H1/H4 OB 方向一致性
- 只在 HTF 同向 OB 存在时入场
- 预期：减少假突破中的入场

### 3. 适度提高风险参数
- D5B 更高 WR (60.6% vs 57.7%) 可承受更多风险
- risk_percent 1.5% → 2.0% 可接近基线收益
- 需验证回撤控制

### 4. EntryDepthFilger 放松
- 当前 entry_depth_pct=0.67 + filter=true
- 放松到 0.50 或关闭 depth filter 可回收更多交易
- 需配合 DP-SL 验证

## 最佳策略参数 (D5B)

```yaml
bounce_pct: 0.30
bounce_sweet_min_pct: 0.35
outside_bounce_sweet_mult: 0.4
max_counter_risk_atr: 0.5
max_entries_per_ob: 2
enable_deepest_pullback_sl: true
deepest_pullback_buffer: 0.5
```

## 720d 排名

| 排名 | 策略 | 交易 | WR | 余额 |
|:---:|------|-----:|:--:|-----:|
| 1 | QS3 基线 | 7,065 | 57.7% | $336K |
| 2 | D5B H2A+DP0.5 | 5,065 | 60.6% | $265K |
| 3 | D5C b0.40+DP0.5 | 5,475 | 56.0% | $213K |
| 4 | D7D H2A+DP0.7 | 4,450 | 59.1% | $212K |
